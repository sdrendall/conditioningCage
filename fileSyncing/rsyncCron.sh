#! /bin/bash

# Script to be called by cron on HIM022B raspberry pis to sync timelapses to the fileserver

#Some important names and places
macWorkstationIP=10.117.33.13
geneticsFS=/media/HMSGenetics
imageDest=$geneticsFS/incomingTimelapses/$HOSTNAME
logDest=$geneticsFS/incomingLogs/$HOSTNAME
log=~/.rsyncLog

# Functions to sync images
syncToMacThenServer() {
    rsync -aqz --log-file=$log ~/timelapse/*.jpg ccws@$macWorkstationIP:~/timelapses/$HOSTNAME
    sudo rsync -aqz --remove-source-files --log-file=$log ~/timelapse/*.jpg $imageDest
}

syncToMacOnly() {
    rsync -aqz --remove-source-files --log-file=$log ~/timelapse/*.jpg ccws@$macWorkstationIP:~/timelapses/$HOSTNAME
}

# Automation of sync commands, check appropriate directories
syncImages() {
    # Check if FS is mounted (should be a better way)
    if [ -d "$geneticsFS/incomingTimelapses" ];
    then 
        # Check if target dir exists
        if [ -d "$imageDest" ];
        then
            # sync to mac first, delete after syncing to server
            syncToMacThenServer
        else
            # make target directory if it isn't there
            sudo mkdir $imageDest
            syncToMacThenServer
        fi
     # Only sync to the Mac if the server can't be reached
     else
        syncToMacOnly
     fi
}


# Sync logs to server
syncLogs() {
    if [ ! -d "$logDest" ];
    then
        sudo mkdir $logDest
    fi
    sudo rsync -aqz --log-file=$log ~/logs/ $logDest
}

# Fcn to mount filesystem
mountFS() {
    if [ -d '/media/HMSGenetics/' ];
    then
        sudo mount /media/HMSGenetics/;
    else
        sudo mkdir /media/HMSGenetics/;
        sudo mount /media/HMSGenetics/;
    fi
}

unmountFS() {
    sudo umount /media/HMSGenetics/;
}

## MAIN -- Here's where the magic happens...
mountFS
syncImages
syncLogs
unmountFS