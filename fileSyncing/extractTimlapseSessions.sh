#! /bin/bash

dumpPath="/home/sam/code/conditioningCage/fileSyncing"
startPath="/home/sam/code/conditioningCage/fileSyncing/test"

ensureDir() {
    if [ ! -d $1 ]
        then
        mkdir $1
    fi
}

relocateImages() {
    # Extract distinct timelapses
    for dateAndTimeStamp in $(ls *.jpg | cut -d'_' -f2,3 | sort | uniq)
    do
        currDumpDir="$1/$dateAndTimeStamp"
        ensureDir $currDumpDir 
        rsync -avz *$dateAndTimeStamp* $currDumpDir
    done
}

for pi in *
do
    if [ -d $pi ]
        then
        pushd $pi
        piDumpPath="$dumpPath/$pi"
        ensureDir $piDumpPath
        relocateImages $piDumpPath
        popd
    fi
done