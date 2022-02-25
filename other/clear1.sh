#!/usr/bin/env bash

help="Usage: 
    ./this_script IP"
eval "$(docopts -A args -h "$help" : "$@")"
PORT=22
IP=${args[IP]}

# AGENT_NUMS="1 2 3 4 5 6 7 9 10 11 13 14 17 18 19 20 21 22 23 24"
#AGENT_NUMS=`seq 9 26`
ssh -oStrictHostKeyChecking=no  -o ConnectTimeout=5 ${IP} ps -aux | grep FedScale | awk '{print $2}'

# for NUM in $AGENT_NUMS; do
#     echo agent-${NUM}
#     #echo "$CMD"
#     #ssh agent-${NUM} "cat >> .ssh/authorized_keys" < agent-pubkeys
#     echo ""
# done