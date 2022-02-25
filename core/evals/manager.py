# Submit job to the remote cluster

import yaml
import sys
import time
import random
import os, subprocess
import pickle, datetime
from math import floor
from functools import reduce

def load_yaml_conf(yaml_file):
    with open(yaml_file) as fin:
        data = yaml.load(fin, Loader=yaml.FullLoader)
    return data

def process_cmd(yaml_file):

    yaml_conf = load_yaml_conf(yaml_file)

    ps_ips, worker_ips, total_ps_gpus, total_worker_gpus = [], [], [], []
    cmd_script_list = []

    for ip_gpu in yaml_conf['ps_ips']:
        ip, gpu_list = ip_gpu.strip().split(':')
        ps_ips.append(ip)
        total_ps_gpus.append(eval(gpu_list))

    for ip_gpu in yaml_conf['worker_ips']:
        ip, gpu_list = ip_gpu.strip().split(':')
        worker_ips.append(ip)
        total_worker_gpus.append(eval(gpu_list))

    time_stamp = datetime.datetime.fromtimestamp(time.time()).strftime('%m%d_%H%M%S')
    running_vms = set()
    job_name = 'kuiper_job'
    log_path = './logs'
    submit_user = f"{yaml_conf['auth']['ssh_user']}@" if len(yaml_conf['auth']['ssh_user']) else ""

    base_ps_port = random.randint(1000, 59900)
    base_manager_port = random.randint(1000, 59900)

    total_ps_gpu_processes =  sum([sum(x) for x in total_ps_gpus])
    total_worker_gpu_processes =  sum([sum(x) for x in total_worker_gpus])

    if (total_worker_gpu_processes % total_ps_gpu_processes != 0):
        print("WARNING: Total worker gpus can not be equally distributed among parameter servers. Ensure number of worker gpus present is a mutiple of the number of parameter server gpus present.")
        return

    worker_processes_per_ps_processes = floor(total_worker_gpu_processes/total_ps_gpu_processes)
    worker_ips_and_processes = yaml_conf['worker_ips']

    def ip_gpu_to_repeated_ip_list(str):
        ip, gpu = str.strip().split(":")
        sublist = []
        for i in range(int(gpu.strip("[]"))):
            sublist.append(ip)
        return sublist

    def take_chunks(list, sublist_length):
        for i in range(0, len(list), sublist_length):
            yield list[i:i+sublist_length]

    worker_rank_ips = \
        list( \
            map( \
                lambda x : ":".join([str(x[0] + 1),x[1]]), \
                list( \
                    enumerate( \
                        reduce( \
                            list.__add__,
                            list(\
                                map(\
                                    ip_gpu_to_repeated_ip_list, \
                                    worker_ips_and_processes \
                                ) \
                            ) \
                        ) \
                    ) \
                ) \
            ) \
        )

    executor_configs = \
        list(\
            map( \
                lambda sublist : "=".join(sublist), \
                take_chunks( \
                    worker_rank_ips, \
                    worker_processes_per_ps_processes \
                ) \
            ) \
        )

    job_confs = []
    ps_port = base_ps_port
    manager_port = base_manager_port

    for ps_ip, gpu in zip(ps_ips, total_ps_gpus):
        for _ in range(gpu[0]):
            job_conf = {'time_stamp':time_stamp,
                        'ps_ip':ps_ip,
                        'ps_port':ps_port,
                        'manager_port':manager_port
                        }
            for conf in yaml_conf['job_conf']:
                job_conf.update(conf)
            job_confs.append(job_conf)
            ps_port += 1
            manager_port += 1

    setup_cmd = ''
    if yaml_conf['setup_commands'] is not None:
        setup_cmd += (yaml_conf['setup_commands'][0] + ' && ')
        for item in yaml_conf['setup_commands'][1:]:
            setup_cmd += (item + ' && ')

    cmd_sufix = f" "


    conf_scripts = []
    for job_conf in job_confs:
        conf_script = ''
        for conf_name in job_conf:
            conf_script = conf_script + f' --{conf_name}={job_conf[conf_name]}'
            if conf_name == "job_name":
                job_name = job_conf[conf_name]
            if conf_name == "log_path":
                log_path = os.path.join(job_conf[conf_name], 'log', job_name, time_stamp)
        conf_scripts.append(conf_script)

    with open(f"{job_name}_logging", 'wb') as fout:
        pass

    # =========== Submit job to parameter servers ============
    ps_rank_id = 1
    for ps_ip, gpu in zip(ps_ips, total_ps_gpus):
        running_vms.add(ps_ip)
        
        print(f"Starting aggregators on {ps_ip}...")
        for cuda_id in range(len(gpu)):
            for _  in range(gpu[cuda_id]):
                conf_script = conf_scripts[ps_rank_id - 1]
                ps_cmd = f" python {yaml_conf['exp_path']}/{yaml_conf['aggregator_entry']} {conf_script} --this_rank={ps_rank_id} --num_executors={worker_processes_per_ps_processes} --num_aggregators={total_ps_gpus[0][0]} --executor_configs={executor_configs[ps_rank_id - 1]}"
                ps_rank_id += 1

                with open(f"{job_name}_logging", 'a') as fout:
                    subprocess.Popen(f'ssh -oStrictHostKeyChecking=no {submit_user}{ps_ip} "{setup_cmd} {ps_cmd}"',
                                    shell=True, stdout=fout, stderr=fout)

    time.sleep(3)
    # =========== Submit job to each worker ============
    rank_id = 1
    ps_fulfilled = 0
    for worker, gpu in zip(worker_ips, total_worker_gpus):
        running_vms.add(worker)
        print(f"Starting workers on {worker} ...")

        for cuda_id in range(len(gpu)):
            for _ in range(gpu[cuda_id]):
                conf_script = conf_scripts[ps_fulfilled]
                worker_cmd = f" python {yaml_conf['exp_path']}/{yaml_conf['executor_entry']} {conf_script} --this_rank={rank_id} --num_executors={worker_processes_per_ps_processes} --cuda_device=cuda:{cuda_id} "
                
                if ((rank_id) % worker_processes_per_ps_processes == 0):
                    ps_fulfilled += 1

                rank_id += 1

                with open(f"{job_name}_logging", 'a') as fout:
                    #time.sleep(2)
                    subprocess.Popen(f'ssh -oStrictHostKeyChecking=no {submit_user}{worker} "{setup_cmd} {worker_cmd}"',
                                    shell=True, stdout=fout, stderr=fout)

    # dump the address of running workers
    current_path = os.path.dirname(os.path.abspath(__file__))
    job_name = os.path.join(current_path, job_name)
    with open(job_name, 'wb') as fout:
        job_meta = {'user':submit_user, 'vms': running_vms}
        pickle.dump(job_meta, fout)

    print(f"Submitted job, please check your logs $HOME/{job_conf['model']}/{time_stamp} for status")

def terminate(job_name):

    current_path = os.path.dirname(os.path.abspath(__file__))
    job_meta_path = os.path.join(current_path, job_name)

    if not os.path.isfile(job_meta_path):
        print(f"Fail to terminate {job_name}, as it does not exist")

    with open(job_meta_path, 'rb') as fin:
        job_meta = pickle.load(fin)

    for vm_ip in job_meta['vms']:
        # os.system(f'scp shutdown.py {job_meta["user"]}{vm_ip}:~/')
        print(f"Shutting down job on {vm_ip}")
        with open(f"{job_name}_logging", 'a') as fout:
            subprocess.Popen(f'ssh -oStrictHostKeyChecking=no {job_meta["user"]}{vm_ip} "python {current_path}/shutdown.py {job_name}"',
                            shell=True, stdout=fout, stderr=fout)

        # _ = os.system(f"ssh -oStrictHostKeyChecking=no {job_meta['user']}{vm_ip} 'python {current_path}/shutdown.py {job_name}'")

if sys.argv[1] == 'submit':
    process_cmd(sys.argv[2])
elif sys.argv[1] == 'stop':
    terminate(sys.argv[2])
else:
    print("Unknown cmds ...")


