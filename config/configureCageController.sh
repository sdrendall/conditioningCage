#! /bin/bash

# Update
sudo apt-get update && sudo apt-get -y upgrade 

# Install dig, ntp and nmap
sudo apt-get -y install dnsutils nmap ntp
 
# Install packages for video and networking
sudo apt-get -y install python-twisted python-picamera gpac

# Add some directories that are used
pushd ~
mkdir code logs timelapse
popd

# Add runClient to /usr/bin
pushd ~/code/conditioningCage/bashScripts
for client in nannyCamClient cageClient;
do
    chmod 755 $client
    sudo ln $client /usr/bin
done
popd

# Set up fstab
pushd ~/code/conditioningCage/config
echo "//research.files.med.harvard.edu/genetics/GrayLabPis /media/HMSGenetics cifs credentials=/home/pi/.smbcredentials,iocharset=utf8,sec=ntlm 0 0" | sudo tee --append /etc/fstab

# Set up Cron
cat crontab.base > ~/.crontab.curr
echo "@reboot cageClient" >> ~/.crontab.curr
crontab ~/.crontab.curr

# Add rsa keys
if [ ! -d "~/.ssh" ]
    then
    mkdir ~/.ssh
fi

cat pubRsaKey_sam >> ~/.ssh/authorized_keys
cat pubRsaKey_ccws >> ~/.ssh/authorized_keys
popd

echo "Configuration Complete!  Please Reboot.  Ensure that .smbcredentials has been properly copied to the home folder"
