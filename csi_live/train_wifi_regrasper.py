#from envs.utils.csi_reader import *
import numpy as np
import pickle as pkl
from tqdm import tqdm

from absl import app
from absl import flags

import torch, torch.nn as nn
import torch.nn.functional as F
from sklearn.model_selection import train_test_split

FLAGS = flags.FLAGS
flags.DEFINE_integer('n_fft', 128, 'Number of fft_bins', lower_bound=1)
flags.DEFINE_integer('n_epochs', 500, 'Number of epochs to train model', lower_bound=1)

device = 'cuda:0' if torch.cuda.is_available() else 'cpu'
# 20Mhz -> n_fft = 64
# 40Mhz -> n_fft = 128
# 80Mhz -> n_fft = 256
def _subcarriers(n_fft):
    return np.array([x for x in range(-(n_fft//2),(n_fft//2))])

subcarriers = {
    64  : _subcarriers(64),
    128 : _subcarriers(128),
    256 : _subcarriers(256),
}


guard_bins = {
    64  :  np.array([x+32  for x in [-32,-31,-30,-29,-28,-27,0,27,28,29,30,31]]),
    128 :  np.array([x+64  for x in [-64,-63,-62,-61,-60,-59,-1,0,1,59,60,61,62,63]]),
    256 :  np.array([x+128 for x in [-128,-127,-126,-125,-124,-123,-1,0,1,123,124,125,126,127]]),
}

pilot_bins = {
    64  : np.array([x+32  for x in [-21,-7,7,21]]),
    128 : np.array([x+64  for x in [-53,-25,-11,11,25,53]]),
    256 : np.array([x+128 for x in [-103,-75,-39,-11,11,39,75,103]]),
}

data_bins = {
    64  : np.array([x for x in range(64) if x not in guard_bins[64] and x not in pilot_bins[64]]),
    128 : np.array([x for x in range(128) if x not in guard_bins[128] and x not in pilot_bins[128]]),
    256 : np.array([x for x in range(256) if x not in guard_bins[256] and x not in pilot_bins[256]]),
}

def get_quality(csi):
    """Quality metric for CSI array.

    Args:
        csi: An n_frames x b complex Numpy array of CSI values.

    Returns:
        Real number.
    """
    data_carriers = csi[:, data_bins[csi.shape[1]]]
    return np.mean(np.abs(data_carriers))

def get_spectrogram(csi):
    """Quality metric for CSI array.

    Args:
        csi: An n_frames x b complex Numpy array of CSI values.

    Returns:
        108 x 1 spectrogram of magnitude over all frequency bins. 
    """
    data_carriers = csi[:, data_bins[csi.shape[1]]]
    return np.mean(np.abs(data_carriers),0)

def create_rollouts(setting_name, n_experience = 200):
    with open("./data/"+setting_name+"/joint_positions.pkl","rb") as f:
        joint_positions = pkl.load(f)
    with open("./data/"+setting_name+"/actions.pkl","rb") as f:
        actions = pkl.load(f)

    rollouts = []
    for ind in range(n_experience - 1):
        curr_pose, next_pose = joint_positions[ind], joint_positions[ind+1]
        curr_csi, next_csi = np.load("./data/"+setting_name+"/"+str(ind)+".npy"), \
                             np.load("./data/"+setting_name+"/"+str(ind+1)+".npy")

        curr_spectrogram, next_spectrogram = get_spectrogram(curr_csi), get_spectrogram(next_csi)
        curr_quality, next_quality = get_quality(curr_csi), get_quality(next_csi)
        reward = next_quality - curr_quality
        
        success = int(reward > 0)
        action = actions[ind]
        
        rollout = [curr_pose, curr_spectrogram, action, reward, next_pose, next_spectrogram, success]
        rollouts.append(rollout)
    
    return rollouts

class WifiReGraspNet(nn.Module):

    def __init__(self, csi_dim = 108, pose_dim = 5, action_dim = 5, lrate = 1e-3):
        super(WifiReGraspNet, self).__init__()

        input_size = csi_dim + action_dim + pose_dim
        self.fc1 = nn.Linear(input_size,input_size) 
        self.fc2 = nn.Linear(input_size,50) 
        self.fc3 = nn.Linear(50, 10)
        self.fc4 = nn.Linear(10, 2)

        self.loss = nn.CrossEntropyLoss()
        self.optimizer = torch.optim.Adam(self.parameters(), lr=lrate, weight_decay=1e-3)
        self.to(device)

    def forward(self, curr_pose, csi_ip, action):
        all_input = torch.cat([csi_ip.float(),curr_pose.float(),action.float()], 1)
        x = F.relu(self.fc1(all_input))
        x = F.relu(self.fc2(x))
        x = F.relu(self.fc3(x))
        x = self.fc4(x)
        return x

    def step(self, train_loader, train=True):
        
        running_loss = 0.
        for batch in train_loader:   
            curr_pose, curr_csi, action, reward, next_pose, next_csi, success = batch 
            csi_ip = curr_csi
            predictions = self.forward(curr_pose.to(device), csi_ip.to(device), action.to(device))    
            if not train:
                self.eval()
            else:
                self.train()
            if len(predictions.shape) == 1:
                predictions = predictions.unsqueeze(0).to(device)
            loss = self.loss(predictions, success.to(device))
            running_loss += loss.item()
            if train:                
                self.optimizer.zero_grad()
                loss.backward()
                self.optimizer.step()
        if train:
            return running_loss
        else:
            return running_loss, predictions
    
    def infer(self, loader):
        #This utility should only be used during deployment. The loader should only have one batch. 
        for batch in loader:   
            curr_pose, curr_csi, action = batch 
            predictions = self.forward(curr_pose.to(device), curr_csi.to(device), action.to(device))
        return predictions

def train(all_rollouts, random_state, save_checkpoint=False):

    train_rollouts, val_rollouts = train_test_split(all_rollouts, test_size=0.25, random_state=random_state)    
    success = torch.tensor([a[-1] for a in all_rollouts]).to(device)
    train_success = torch.tensor([a[-1] for a in train_rollouts]).to(device)
    val_success = torch.tensor([a[-1] for a in val_rollouts]).to(device)

    print('Number of successful WiFi regrasps in entire data is',sum(success).item())
    grasp_net = WifiReGraspNet()
    train_loader = torch.utils.data.DataLoader(train_rollouts, batch_size = 64, shuffle = True)
    train_acc_loader = torch.utils.data.DataLoader(train_rollouts, batch_size = len(train_rollouts), shuffle = False)
    val_acc_loader = torch.utils.data.DataLoader(val_rollouts, batch_size = len(val_rollouts), shuffle = False)

    for epoch in tqdm(range(1,FLAGS.n_epochs+1)):
        running_loss = grasp_net.step(train_loader, train=True)
        print("Epoch ",epoch,"loss is ",running_loss)

        if epoch%10 == 0:
            train_loss, predictions = grasp_net.step(train_acc_loader, train=False)
            a = predictions.argmax(1)
            train_accuracy = torch.sum((train_success == a).int()).item()/len(train_rollouts)
            print("Train Accuracy is",train_accuracy)

            val_loss, predictions = grasp_net.step(val_acc_loader, train=False)
            a = predictions.argmax(1)
            val_accuracy = torch.sum((val_success == a).int()).item()/len(val_rollouts)
            print("Val Accuracy is",val_accuracy)

        if epoch%50 == 0 and save_checkpoint:
            torch.save({'epoch': epoch,
                        'model_state_dict': grasp_net.state_dict(),
                        'optimizer_state_dict': grasp_net.optimizer.state_dict(),
                        'loss': running_loss,}, "./checkpoints/regrasper_model_"+str(epoch)+'.pt')
    
    return train_accuracy, val_accuracy

def main(_):
    all_rollouts = []
    settings = ["bed_0","bed_1","bed_2","bed_3",
                "bed_0_big","bed_1_big","bed_2_big","bed_3_big",

                "desk_0","desk_1","desk_2","desk_3",
                "desk_0_big","desk_1_big","desk_2_big","desk_3_big",

                "kitchen_0","kitchen_1","kitchen_2","kitchen_3",
                "kitchen_0_big","kitchen_1_big","kitchen_2_big","kitchen_3_big"]

    for setting in tqdm(settings):
        if 'big' in setting:
            all_rollouts += create_rollouts(setting, 800)
        else:
            all_rollouts += create_rollouts(setting)

    save_checkpoint = True    
    ta, va = [], []
    for random_state in [42,27,94]: #Three random-states
        train_accuracy, val_accuracy = train(all_rollouts, random_state, save_checkpoint)
        ta.append(train_accuracy)
        va.append(val_accuracy)
        save_checkpoint = False
    
    print("Training stats",sum(ta)/3,np.std(ta))
    print("Validation stats",sum(va)/3,np.std(va))

if __name__ == '__main__':
    app.run(main)
