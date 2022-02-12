#!/usr/bin/env bash

help="Usage: 
    ./this_script IP"
eval "$(docopts -A args -h "$help" : "$@")"
source ~/.colors
PORT=22
IP=${args[IP]}

# for ii in {41..100}; do echo "10.30.74.$(( $ii+30 ))   FEMNIST-worker$ii agent$ii\n" >> hosts-fedscale; done
# rm -f /tmp/hosts; for ii in {87..93}; do echo "FEMNIST-worker$ii 10.30.74.$(( $ii+30 )) " >> /tmp/hosts; done
# while read p; do op-run-server fed.medium Ubuntu-18-04.3 etesami-key default $p; done < /tmp/hosts
# for ii in `seq 41 100`; do echo "agent${ii}" >> /tmp/hosts; done

HOSTS="
\n
127.0.0.1 localhost\n\n
10.30.74.150   H-F-S-150 server\n
10.30.74.151   H-F-W-151 agent151\n
"

SSH_KEY=`sudo cat ~/.ssh/id_rsa.pub`

ssh -i ~/.ssh/id_rsa_client1 -oStrictHostKeyChecking=no -p$PORT \
        ubuntu@$IP "bash -c 'mkdir -p ~/.ssh && chmod 700 ~/.ssh && \
                    echo $SSH_KEY | tee -a ~/.ssh/authorized_keys > /dev/null'"

green "\nAdding hosts to /etc/hosts"
echo -e $HOSTS | ssh -oStrictHostKeyChecking=no -p$PORT ubuntu@$IP "sudo bash -c 'cat | tee /etc/hosts > /dev/null'"

green "\nRunning batch commands and install conda"
scp -P$PORT -oStrictHostKeyChecking=no ../ntp.patch ubuntu@$IP:/tmp
scp -P$PORT -oStrictHostKeyChecking=no ~/Anaconda3-2020.11-Linux-x86_64.sh ubuntu@$IP:~

## ssh -oStrictHostKeyChecking=no -p$PORT \
##         ubuntu@$IP "sudo bash -c 'cd ~/FedScale && git reset --hard && git pull'"

ssh -oStrictHostKeyChecking=no -p$PORT \
        ubuntu@$IP "sudo bash -c 'apt-get update && apt-get install ntp python3-pip -yqq && 
                patch -u /etc/ntp.conf -i /tmp/ntp.patch && \
                sudo service ntp restart && \
                git clone -b horizontal-fl https://github.com/Alexjsenn/FedScale.git && \
                cd /home/ubuntu/FedScale && chmod +x ./install.sh && ./install.sh && \
                chmod +x ./install2.sh && ./install2.sh && \
                chown -Rf ubuntu:ubuntu /home/ubuntu/*
                '"
                

# ssh -oStrictHostKeyChecking=no -p$PORT \
#         ubuntu@$IP "sudo bash -c 'cd /home/ubuntu/FedScale/dataset && \
#                 chmod +x download.sh && \
#                 ./download.sh -f
#                 '"

ssh -oStrictHostKeyChecking=no -p$PORT \
        ubuntu@$IP "sudo bash -c 'chown -Rf ubuntu:ubuntu /home/ubuntu/*'"

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