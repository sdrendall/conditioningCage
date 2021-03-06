#! /bin/bash

# Script to be called by cron to push videos to research.files

# Important Addresses
geneticsFS=/media/HMSGenetics
VIDEO_DEST=$geneticsFS/incomingVideos/$HOSTNAME

syncToServer() {
    # Requires root privledges
    sudo rsync -aqz --remove-source-files --log-file=$log ~/fc_videos/*.mp4 $VIDEO_DEST
}

syncVideos() {
        # Check if FS is mounted (should be a better way)
    if [ -d "$geneticsFS/incomingVideos" ];
    then 
        # Check if target dir exists
        if [ -d "$VIDEO_DEST" ];
        then
            syncToServer
        else
            sudo mkdir $VIDEO_DEST
            syncToServer
        fi
    fi
}

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

mountFS
syncVideos
unmountFS
