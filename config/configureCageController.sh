#! /bin/bash


# Update
sudo apt-get update && sudo apt-get -y upgrade 

# Install dig, ntp and nmap
sudo apt-get -y install dnsutils nmap ntp
 
# Install python packages twisted picamera
sudo apt-get -y install python-twisted python-picamera

# Add some directories that are used
pushd ~
mkdir code logs timelapse
popd

# ADD SCRIPTS TO CLONE GIT REPO, UNPACK TO IMPORTANT PLACES!!!
pushd ~/code
git clone https://github.com/sdrendall/conditioningCage
popd

# Add runClient to /usr/bin
pushd ~/code/conditioningCage/bashScripts
for client in nannyCamClient cageClient;
do
    chmod 755 $client
    sudo cp $client /usr/bin
done
popd

# Set up fstab
pushd ~/code/conditioningCage/config
cat smbcredentials > ~/.smbcredentials
echo "//research.files.med.harvard.edu/genetics/GrayLabPis /media/HMSGenetics cifs credentials=/home/pi/.smbcredentials,iocharset=utf8,sec=ntlm 0 0" | sudo tee --append /etc/fstab

# Set up Cron
cat crontab.base > ~/.crontab.curr
echo "@reboot cageClient" >> ~/.crontab.curr
crontab ~/.crontab.curr

# Add rsa keys
if [ ! -d "~/.ssh"]
    then
    mkdir ~/.ssh
fi
cat pubRsaKey_sam >> ~/.ssh/authorized_keys
cat pubRsaKey_hccws >> ~/.ssh/authorized_keys
popd   

# FIGURE OUT HOW TO ADD HMS MIRRORS FOR APTITUDE

# Reboot
sudo reboot