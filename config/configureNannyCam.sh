#! /bin/bash


# Update
sudo apt-get update && sudo apt-get -y upgrade 

# Install dig
sudo apt-get -y install dnsutils
 
# Install python packages twisted picamera
sudo apt-get -y install python-twisted python-picamera

# Install nmap -- because...
sudo apt-get -y install nmap

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
echo "@reboot nannyCamClient" >> ~/.crontab.curr
crontab ~/.crontab.curr
popd

# Reboot
sudo reboot
