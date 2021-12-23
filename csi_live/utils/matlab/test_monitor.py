import time
import paramiko

# raspberry pi
# ssh = paramiko.SSHClient()
# ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
# ssh.connect('192.168.10.10', username='root', password='kali')

# nexus 6p
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.10.16', username='root', password='toor')

_,stdout,_ = ssh.exec_command('uname -a')
print(stdout.read())
_,stdout,_ = ssh.exec_command('hostname')
print(stdout.read())
_,stdout,_ = ssh.exec_command('whoami')
print(stdout.read())
_,stdout,_ = ssh.exec_command('echo $PATH')
print(stdout.read())

# raspberry pi

# print('resetting')
# ssh.exec_command('modprobe -r brcmfmac')
# time.sleep(1)
# ssh.exec_command('modprobe brcmfmac')
# time.sleep(1)
# ssh.exec_command('modprobe -r brcmfmac')
# time.sleep(1)
# ssh.exec_command('modprobe brcmfmac')
# time.sleep(1)

# print('upping wlan0')
# ssh.exec_command('ifconfig wlan0 up')
# _,stdout,_ = ssh.exec_command('ifconfig')
# print(stdout.read())

# -c100/80 -C 1 -N 1 -m dc:a6:32:99:e4:29
# _,stdout,_ = ssh.exec_command('nexutil -Iwlan0 -s500 -b -l34 -vauABEQAAAQDcpjKZ5CkAAAAAAAAAAAAAAAAAAAAAAAAAAA==')
# -c100/40 -C 1 -N 1 -m dc:a6:32:99:e4:29
_,stdout,_ = ssh.exec_command('nexutil -Iwlan0 -s500 -b -l34 -vZtgBEQAAAQDcpjKZ5CkAAAAAAAAAAAAAAAAAAAAAAAAAAA==')
print(stdout.read())
time.sleep(2)
ssh.exec_command('nexutil -m1')
time.sleep(2)
_,stdout,_ = ssh.exec_command('nexutil -k')
print(stdout.read())
_,stdout,_ = ssh.exec_command('nexutil -m')
print(stdout.read())

_,stdout,_ = ssh.exec_command('tcpdump -i wlan0 dst port 5500 -U -w - -c 20 2>/dev/null')
dump = stdout.read()
ssh.close()

with open('test_nexus.pcap', 'wb') as f:
   f.write(dump)
print(dump)

# with open('test_pi.pcap', 'wb') as f:
#    f.write(dump)
# print(dump)

# stdout._set_mode('b')
# for line in iter(stdout.readline, ""):
#         print(line, end="")

