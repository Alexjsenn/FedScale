#!/usr/bin/env bash

help="Usage: 
    ./this_script IP"
eval "$(docopts -A args -h "$help" : "$@")"
source ~/.colors
PORT=22
IP=${args[IP]}

# for ii in {41..100}; do echo "10.30.72.$(( $ii+30 ))   fedscale-agent$ii agent$ii\n" >> hosts-fedscale; done
# rm -f /tmp/hosts; for ii in {87..93}; do echo "fedscale-agent$ii 10.30.72.$(( $ii+30 )) " >> /tmp/hosts; done
# while read p; do op-run-server fed.medium Ubuntu-18-04.3 etesami-key default $p; done < /tmp/hosts
# for ii in `seq 41 100`; do echo "agent${ii}" >> /tmp/hosts; done

HOSTS="
\n
127.0.0.1 localhost\n\n
10.30.72.19   fedscale-server server\n
10.30.72.28   fedscale-agent1 agent1\n
10.30.72.29   fedscale-agent2 agent2\n
10.30.72.30   fedscale-agent3 agent3\n
10.30.72.31   fedscale-agent4 agent4\n
10.30.72.32   fedscale-agent5 agent5\n
10.30.72.33   fedscale-agent6 agent6\n
10.30.72.34   fedscale-agent7 agent7\n
10.30.72.38   fedscale-agent8 agent8\n
10.30.72.39   fedscale-agent9 agent9\n
10.30.72.40   fedscale-agent10 agent10\n
10.30.72.41   fedscale-agent11 agent11\n
10.30.72.42   fedscale-agent12 agent12\n
10.30.72.43   fedscale-agent13 agent13\n
10.30.72.44   fedscale-agent14 agent14\n
10.30.72.45   fedscale-agent15 agent15\n
10.30.72.46   fedscale-agent16 agent16\n
10.30.72.47   fedscale-agent17 agent17\n
10.30.72.48   fedscale-agent18 agent18\n
10.30.72.49   fedscale-agent19 agent19\n
10.30.72.50   fedscale-agent20 agent20\n
10.30.72.51   fedscale-agent21 agent21\n
10.30.72.52   fedscale-agent22 agent22\n
10.30.72.53   fedscale-agent23 agent23\n
10.30.72.54   fedscale-agent24 agent24\n
10.30.72.55   fedscale-agent25 agent25\n
10.30.72.56   fedscale-agent26 agent26\n
10.30.72.57   fedscale-agent27 agent27\n
10.30.72.58   fedscale-agent28 agent28\n
10.30.72.59   fedscale-agent29 agent29\n
10.30.72.60   fedscale-agent30 agent30\n
10.30.72.61   fedscale-agent31 agent31\n
10.30.72.62   fedscale-agent32 agent32\n
10.30.72.63   fedscale-agent33 agent33\n
10.30.72.64   fedscale-agent34 agent34\n
10.30.72.65   fedscale-agent35 agent35\n
10.30.72.66   fedscale-agent36 agent36\n
10.30.72.67   fedscale-agent37 agent37\n
10.30.72.68   fedscale-agent38 agent38\n
10.30.72.69   fedscale-agent39 agent39\n
10.30.72.70   fedscale-agent40 agent40\n
10.30.72.71   fedscale-agent41 agent41\n
10.30.72.72   fedscale-agent42 agent42\n
10.30.72.73   fedscale-agent43 agent43\n
10.30.72.74   fedscale-agent44 agent44\n
10.30.72.75   fedscale-agent45 agent45\n
10.30.72.76   fedscale-agent46 agent46\n
10.30.72.77   fedscale-agent47 agent47\n
10.30.72.78   fedscale-agent48 agent48\n
10.30.72.79   fedscale-agent49 agent49\n
10.30.72.80   fedscale-agent50 agent50\n
10.30.72.81   fedscale-agent51 agent51\n
10.30.72.82   fedscale-agent52 agent52\n
10.30.72.83   fedscale-agent53 agent53\n
10.30.72.84   fedscale-agent54 agent54\n
10.30.72.85   fedscale-agent55 agent55\n
10.30.72.86   fedscale-agent56 agent56\n
10.30.72.87   fedscale-agent57 agent57\n
10.30.72.88   fedscale-agent58 agent58\n
10.30.72.89   fedscale-agent59 agent59\n
10.30.72.90   fedscale-agent60 agent60\n
10.30.72.91   fedscale-agent61 agent61\n
10.30.72.92   fedscale-agent62 agent62\n
10.30.72.93   fedscale-agent63 agent63\n
10.30.72.94   fedscale-agent64 agent64\n
10.30.72.95   fedscale-agent65 agent65\n
10.30.72.96   fedscale-agent66 agent66\n
10.30.72.97   fedscale-agent67 agent67\n
10.30.72.98   fedscale-agent68 agent68\n
10.30.72.99   fedscale-agent69 agent69\n
10.30.72.100   fedscale-agent70 agent70\n
10.30.72.101   fedscale-agent71 agent71\n
10.30.72.102   fedscale-agent72 agent72\n
10.30.72.103   fedscale-agent73 agent73\n
10.30.72.104   fedscale-agent74 agent74\n
10.30.72.105   fedscale-agent75 agent75\n
10.30.72.106   fedscale-agent76 agent76\n
10.30.72.107   fedscale-agent77 agent77\n
10.30.72.108   fedscale-agent78 agent78\n
10.30.72.109   fedscale-agent79 agent79\n
10.30.72.110   fedscale-agent80 agent80\n
10.30.72.111   fedscale-agent81 agent81\n
10.30.72.112   fedscale-agent82 agent82\n
10.30.72.113   fedscale-agent83 agent83\n
10.30.72.114   fedscale-agent84 agent84\n
10.30.72.115   fedscale-agent85 agent85\n
10.30.72.116   fedscale-agent86 agent86\n
10.30.72.117   fedscale-agent87 agent87\n
10.30.72.118   fedscale-agent88 agent88\n
10.30.72.119   fedscale-agent89 agent89\n
10.30.72.120   fedscale-agent90 agent90\n
10.30.72.121   fedscale-agent91 agent91\n
10.30.72.122   fedscale-agent92 agent92\n
10.30.72.123   fedscale-agent93 agent93\n
10.30.72.124   fedscale-agent94 agent94\n
10.30.72.125   fedscale-agent95 agent95\n
10.30.72.126   fedscale-agent96 agent96\n
10.30.72.127   fedscale-agent97 agent97\n
10.30.72.128   fedscale-agent98 agent98\n
10.30.72.129   fedscale-agent99 agent99\n
10.30.72.130   fedscale-agent100 agent100\n
"

SSH_KEY=`sudo cat ~/.ssh/id_rsa.pub`

ssh -i ~/.ssh/id_rsa_client1 -oStrictHostKeyChecking=no -p$PORT \
        ubuntu@$IP "bash -c 'mkdir -p ~/.ssh && chmod 700 ~/.ssh && \
                    echo $SSH_KEY | tee -a ~/.ssh/authorized_keys > /dev/null'"

green "\nAdding hosts to /etc/hosts"
echo -e $HOSTS | ssh -oStrictHostKeyChecking=no -p$PORT ubuntu@$IP "sudo bash -c 'cat | tee /etc/hosts > /dev/null'"

green "\nRuuning batch commands and install conda"
scp -P$PORT -oStrictHostKeyChecking=no ntp.patch ubuntu@$IP:/tmp
scp -P$PORT -oStrictHostKeyChecking=no ~/Anaconda3-2020.11-Linux-x86_64.sh ubuntu@$IP:~

## ssh -oStrictHostKeyChecking=no -p$PORT \
##         ubuntu@$IP "sudo bash -c 'cd ~/FedScale && git reset --hard && git pull'"

ssh -oStrictHostKeyChecking=no -p$PORT \
        ubuntu@$IP "sudo bash -c 'apt-get update && apt-get install ntp python3-pip -yqq && 
                patch -u /etc/ntp.conf -i /tmp/ntp.patch && \
                sudo service ntp restart && \
                git clone -b feature/savi https://github.com/etesami/FedScale.git && \
                cd /home/ubuntu/FedScale && chmod +x ./install.sh && ./install.sh && \
                chown -Rf ubuntu:ubuntu /home/ubuntu/*
                '"
# ssh -oStrictHostKeyChecking=no -p$PORT \
#         ubuntu@$IP "sudo bash -c 'rm -rf /home/ubuntu/FedScale/dataset && \
#                 mv /tmp/FedScale/dataset /home/ubuntu/FedScale/ && \
#                 chown -Rf ubuntu:ubuntu /home/ubuntu/*
#                 '"

# ssh -oStrictHostKeyChecking=no -p$PORT \
#         ubuntu@$IP "sudo bash -c 'mv /home/ubuntu/FedScale /tmp && \
#                 git clone -b feature/savi https://github.com/etesami/FedScale.git && \
#                 cd ~/FedScale && chmod +x ./install.sh && ./install.sh && mv /tmp/FedScale/dataset /home/ubuntu/FedScale
#                 '"

# docker build /home/ubuntu/examples/mnist-pytorch/ -t mnist-client:latest
 
# sudo docker-compose -f docker-compose.yaml -f extra-hosts.yaml up --build