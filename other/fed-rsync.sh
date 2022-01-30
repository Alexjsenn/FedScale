#!/usr/bin/env bash

help="Usage: 
    ./this_script --data MIN MAX
    ./this_script --core MIN MAX"
eval "$(docopts -A args -h "$help" : "$@")"
source ~/.colors
PORT=22


MIN=${args[MIN]}
MAX=${args[MAX]}
if [[ ${args[--core]} == 'true' ]]; then
    for ii in `seq $MIN $MAX`; do
        green "Copying core to agent$ii ..."
        AGENT="agent${ii}"
        (rsync -ar \
            --exclude=*logs --exclude=*logging --exclude=*.pyc --exclude=*.pyx --exclude=__pycache__ --exclude=dataset \
            --delete --info=progress2 ~/FedScale/ ${AGENT}:~/FedScale &)
        (rsync -ar --info=progress2 --exclude=*.pyc --exclude=*.so --exclude=*.pyx --exclude=__pycache__ \
             ~/anaconda3/envs/fedscale/lib/python3.6/site-packages/PIL/ \
            ${AGENT}:~/anaconda3/envs/fedscale/lib/python3.6/site-packages/PIL &)
    done
elif [[ ${args[--data]} == 'true' ]]; then
    for ii in `seq $MIN $MAX`; do
        AGENT="agent${ii}"
        green "Copying data to agent$ii ..."
        (rsync -ar \
            --delete --info=progress2 ~/FedScale/dataset/data/FEMNIST ${AGENT}:~/FedScale/dataset/data/ &)
    done
fi

