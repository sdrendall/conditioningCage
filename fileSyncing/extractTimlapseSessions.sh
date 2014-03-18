#! /bin/bash

dumpPath=""
startPath=""

ensureDumpDir() {
    fullPath="$dumpPath/$1"
    if [! -d $fullPath]
        then
        mkdir $fullPath
    fi
}

relocateImages() {
    for im in *
    do
        
}

for pi in rasPis
do
    if [ -d $pi ]
        then
        pushd $pi
        ensureDumpDir $pi
        relocateImages $pi
        popd
    fi
done