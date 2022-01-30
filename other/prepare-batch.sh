#!/bin/bash


SCREENNAME="prepare-new"
screen -dmS $SCREENNAME


for ii in {1..2}; do
    WINDOW="agent"$ii
    echo $WINDOW
    screen -S $SCREENNAME -X screen -t $WINDOW
    screen -S $SCREENNAME -p $WINDOW -X stuff \
    "~/FedScale/other/prepare-agents.sh agent$ii ^M"
done