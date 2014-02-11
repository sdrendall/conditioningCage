#! /bin/bash

# Update
sudo apt-get update && sudo apt-get -y upgrade 

# Install dig
sudo apt-get -y install dnsutils
 
# Install python packages twisted picamera
sudo apt-get -y install python-twisted python-picamera

# Install nmap -- because...
sudo apt-get -y install nmap

# ADD SCRIPTS TO CLONE GIT REPO, UNPACK TO IMPORTANT PLACES!!!