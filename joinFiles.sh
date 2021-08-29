#!/bin/bash
PATH_=$1
INITPATH=$PWD
if [ -d "$PATH_" ]; then
    python3 generateFileList.py $PATH_
    cp file.txt "$PATH_"
    cd $PATH_
    ffmpeg -f concat -safe 0 -i file.txt -c copy -vcodec libx265 -vf fps=25,format=yuv420p out.mp4
    rm ./*.jpg
    rm file.txt
    if [[ ! -f out.mp4 ]]
    then
        cd $INITPATH
        rm -r $PATH_
    fi
fi