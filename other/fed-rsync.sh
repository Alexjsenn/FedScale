#!/usr/bin/env bash

help="Usage: 
    ./this_script --data MIN MAX
    ./this_script --core MIN MAX"
eval "$(docopts -A args -h "$help" : "$@")"
# source ~/.colors
PORT=22


MIN=${args[MIN]}
MAX=${args[MAX]}
if [[ ${args[--core]} == 'true' ]]; then
    for ii in `seq $MIN $MAX`; do
        echo "Copying core to agent$ii ..."
        AGENT="10.30.74.${ii}"

        # rsync --rsync-path 'sudo -u root rsync' -ar \
        #     ~/FedScale/core/argParser.py ubuntu@${AGENT}:~/FedScale/core/argParser.py &
        (rsync -e "ssh -oStrictHostKeyChecking=no" -ar \
            --exclude=*logs --exclude=*logging --exclude=*.pyc --exclude=*.pyx --exclude=__pycache__ --exclude=dataset \
            --delete --info=progress2 ~/FedScale/ ubuntu@${AGENT}:~/FedScale &)
        # (rsync -ar --info=progress2 --exclude=*.pyc --exclude=*.so --exclude=*.pyx --exclude=__pycache__ \
        #      ~/anaconda3/envs/fedscale/lib/python3.6/site-packages/PIL/ \
        #     ${AGENT}:~/anaconda3/envs/fedscale/lib/python3.6/site-packages/PIL &)
    done
elif [[ ${args[--data]} == 'true' ]]; then
    for ii in `seq $MIN $MAX`; do
        AGENT="10.30.74.${ii}"
        echo "Copying data to 10.30.74.$ii ..."

        (rsync -e "ssh -oStrictHostKeyChecking=no" -ar \
            --delete --info=progress2 ~/FedScale/dataset/data/cifar100 ${AGENT}:~/FedScale/dataset/data/ &)

    done
fi

