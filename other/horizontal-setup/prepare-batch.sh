#!/bin/bash


SCREENNAME="prepare-new"
screen -dmS $SCREENNAME


for ii in {151}; do
    WINDOW="agent"$ii
    echo $WINDOW
    screen -S $SCREENNAME -X screen -t $WINDOW
    screen -S $SCREENNAME -p $WINDOW -X stuff \
    "~/FedScale/other/prepare-agents.sh 10.30.74.$ii ^M"
done