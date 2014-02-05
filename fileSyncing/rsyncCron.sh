#! /bin/bash

# Script to be called by rsync on HIM022B raspberry pis to sync timelapses to the fileserver

macWorkstationIP=10.11.36.146
geneticsFS=/media/HMSGenetics
imageDest=$geneticsFS/SamRendall/conditioningCage/incomingTimelapses/$HOSTNAME
logDest=$geneticsFS/SamRendall/conditioningCage/incomingLogs/$HOSTNAME
log=~./rsyncLog

syncToMacThenServer() {
    rsync -avz --log-file=$log ~/timelapse/ hccworkstation@$macWorkstationIP: ~/timelapses/$HOSTNAME
    rsync -aqz --remove-source-files --log-file=$log ~/timelapse/ $imageDest
}

syncToMacOnly() {
    rsync -aqz --remove-source-files --log-file=$log rsync -aqz ~/timelapse/ hccworkstation@$macWorkstationIP: ~/timelapses/$HOSTNAME
}

# Fcn to sync files
syncImages() {
    # Check if FS is mounted (should be a better way)
    if [ -d "$geneticsFS/SamRendall" ];
    then 
        # Check if target dir exists
        if [ -d "$imageDest" ]
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
    rsync -avz --log-file=$log ~/logs/ $logDest

# Fcn to mount filesystem
mountFS() {
    if [ -d '/media/HMSGenetics/'];
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

