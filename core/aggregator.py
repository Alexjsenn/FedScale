# -*- coding: utf-8 -*-

from fl_aggregator_libs import *
from random import Random
from resource_manager import ResourceManager
import grpc
from concurrent import futures
import job_api_pb2_grpc
import job_api_pb2
import io
import torch
import pickle
import time
from math import floor
from eventLogger import EventLogger, EventType
import neptune.new as neptune
import psutil


MAX_MESSAGE_LENGTH = 50000000

class ExecutorConnections(object):
    """"Helps aggregator manage its grpc connection with executors."""

    class _ExecutorContext(object):
        def __init__(self, executorId):
            self.id = executorId
            self.address = None
            self.channel = None
            self.stub = None
            
    def __init__(self, config, base_port=50000):
        self.executors = {}
        self.base_port = base_port

        for rank_ip in config.split("="):
            rank, ip = rank_ip.split(':')
            executorId = int(rank)
            self.executors[executorId] = ExecutorConnections._ExecutorContext(executorId)
            self.executors[executorId].address = '{}:{}'.format(ip, self.base_port + executorId)

    def __len__(self):
        return len(self.executors)

    def __iter__(self):
        return iter(self.executors)

    def open_grpc_connection(self):
        for executorId in self.executors:
            logging.info('%%%%%%%%%% Opening grpc connection to ' + self.executors[executorId].address + ' %%%%%%%%%%')
            channel = grpc.insecure_channel(
                self.executors[executorId].address,
                options=[
                    ('grpc.max_send_message_length', MAX_MESSAGE_LENGTH),
                    ('grpc.max_receive_message_length', MAX_MESSAGE_LENGTH),
                ]
            )
            self.executors[executorId].channel = channel
            self.executors[executorId].stub = job_api_pb2_grpc.JobServiceStub(channel)

    def close_grpc_connection(self):
        for executorId in self.executors:
            logging.info(f'%%%%%%%%%% Closing grpc connection with {executorId} %%%%%%%%%%')
            self.executors[executorId].channel.close()

    def get_stub(self, executorId):
        return self.executors[executorId].stub


class AggregatorConnections(object):
    """"Helps aggregator manage its grpc connection with other aggregators (for horizontal FL)."""

    class _AggregatorContext(object):
        def __init__(self, aggregatorId):
            self.id = aggregatorId
            self.address = None
            self.channel = None
            self.stub = None
            
    def __init__(self, config, parent_rank, base_port=56000):
        self.parent_rank = parent_rank
        self.aggregators = {}
        self.base_port = base_port
        self.base_port = 56000

        for rank_ip in config.split("="):
            rank, ip = rank_ip.split(':')
            aggregatorId = int(rank)
            if (aggregatorId != parent_rank):
                self.aggregators[aggregatorId] = AggregatorConnections._AggregatorContext(aggregatorId)
                self.aggregators[aggregatorId].address = '{}:{}'.format(ip, self.base_port + aggregatorId)
    
    def __len__(self):
        return len(self.aggregators)

    def __iter__(self):
        return iter(self.aggregators)

    def open_grpc_connection(self):
        for aggregatorId in self.aggregators:
            logging.info(f'%%%%%%%%%% AGGREGATOR {self.parent_rank} Opening grpc connection to aggregator {self.aggregators[aggregatorId].address} %%%%%%%%%%')
            channel = grpc.insecure_channel(
                self.aggregators[aggregatorId].address,
                options=[
                    ('grpc.max_send_message_length', MAX_MESSAGE_LENGTH),
                    ('grpc.max_receive_message_length', MAX_MESSAGE_LENGTH),
                ]
            )
            self.aggregators[aggregatorId].channel = channel
            self.aggregators[aggregatorId].stub = job_api_pb2_grpc.HA_JobServiceStub(channel)

    def close_grpc_connection(self):
        for aggregatorId in self.aggregators:
            logging.info(f'%%%%%%%%%% Closing grpc connection with aggregator {aggregatorId} %%%%%%%%%%')
            self.aggregators[aggregatorId].channel.close()

    def get_stub(self, aggregatorId):
        return self.aggregators[aggregatorId].stub


class Aggregator(job_api_pb2_grpc.HA_JobServiceServicer):
    """This centralized aggregator collects training/testing feedbacks from executors"""
    def __init__(self, args):
        logging.info(f"Job args {args}")

        self.args = args
        self.device = args.cuda_device if args.use_cuda else torch.device('cpu')
        self.executors = ExecutorConnections(args.executor_configs, args.base_port)
        self.aggregators = AggregatorConnections(args.aggregator_configs, args.this_rank, args.base_port)
        self.log_summary = f"AGGREGATOR RANK {args.this_rank} - "

        # ======== env information ========
        self.this_rank = args.this_rank
        self.global_virtual_clock = 0.
        self.round_duration = 0.
        self.resource_manager = ResourceManager()
        self.client_manager = self.init_client_manager(args=args)
        self.grpc_server = None

        # ======== model and data ========
        self.model = None
        self.HA_models = []
        self.HA_models_recieved = 0

        # list of parameters in model.parameters()
        self.model_in_update = []
        self.last_global_model = []

        # ======== channels ========
        self.server_event_queue = {}
        self.client_event_queue = Queue()
        self.control_manager = None
        # event queue of its own functions
        self.event_queue = collections.deque()

        # ======== runtime information ========
        self.tasks_round = 0
        self.sampled_participants = []

        self.round_stragglers = []
        self.model_update_size = 0.

        self.collate_fn = None
        self.task = args.task
        self.epoch = 0

        self.start_run_time = time.time()
        self.client_conf = {}

        self.stats_util_accumulator = []
        self.loss_accumulator = []
        self.client_training_results = []

        self.eventLogger = EventLogger()

        # number of registered executors
        self.registered_executor_info = set()
        self.test_result_accumulator = []
        self.testing_history = {'data_set': args.data_set, 'model': args.model, 'sample_mode': args.sample_mode,
                        'gradient_policy': args.gradient_policy, 'task': args.task, 'perf': collections.OrderedDict()}
        

        # neptune logging
        self.Neptune = neptune.init(
            project="alexjsenn/HFL-Fedscale",
            api_token="eyJhcGlfYWRkcmVzcyI6Imh0dHBzOi8vYXBwLm5lcHR1bmUuYWkiLCJhcGlfdXJsIjoiaHR0cHM6Ly9hcHAubmVwdHVuZS5haSIsImFwaV9rZXkiOiJjZDUzNjRjZS1lYTVlLTQwODMtOWU0NS1jYmYyOGYzYTQ0MzUifQ==",  
        )
        self.Neptune["model/parameters"] = args

        # Network traffic variables
        self.backgroundSent = 0
        self.backgroundRecieved = 0



        # ======== Task specific ============
        self.imdb = None           # object detection

        super(Aggregator, self).__init__()


    def setup_env(self):
        self.setup_seed(seed=self.this_rank)

        # set up device
        if self.args.use_cuda and self.device == None:
            for i in range(torch.cuda.device_count()):
                try:
                    self.device = torch.device('cuda:'+str(i))
                    torch.cuda.set_device(i)
                    _ = torch.rand(1).to(device=self.device)
                    logging.info(f'End up with cuda device ({self.device})')
                    break
                except Exception as e:
                    assert i != torch.cuda.device_count()-1, 'Can not find available GPUs'

        self.init_control_communication(self.args.ps_ip, self.args.manager_port, self.executors)
        self.init_data_communication()
        self.optimizer = ServerOptimizer(self.args.gradient_policy, self.args, self.device)

    def setup_seed(self, seed=1):
        torch.manual_seed(seed)
        torch.cuda.manual_seed_all(seed)
        np.random.seed(seed)
        random.seed(seed)
        torch.backends.cudnn.deterministic = True


    def init_control_communication(self, ps_ip, ps_port, executors):
        # Create communication channel between aggregator and worker
        # This channel serves control messages
        logging.info(f"{self.log_summary} Start to initiate {ps_ip}:{ps_port} for control plane communication ...")

        dummy_que = {executorId:Queue() for executorId in executors}
        # create multiple queue for each aggregator_executor pair
        for executorId in executors:
            BaseManager.register('get_server_event_que'+str(executorId), callable=lambda: dummy_que[executorId])

        dummy_client_que = Queue()
        BaseManager.register('get_client_event', callable=lambda: dummy_client_que)

        self.control_manager = BaseManager(address=(ps_ip, ps_port), authkey=b'FLPerf')
        self.control_manager.start()

        #self.server_event_queue = torch.multiprocessing.Manager().dict()
        for executorId in self.executors:
            self.server_event_queue[executorId] = eval('self.control_manager.get_server_event_que'+str(executorId)+'()')

        self.client_event_queue = self.control_manager.get_client_event()


        self.grpc_server = grpc.server(
            futures.ThreadPoolExecutor(max_workers=30),
            options=[
                ('grpc.max_send_message_length', MAX_MESSAGE_LENGTH),
                ('grpc.max_receive_message_length', MAX_MESSAGE_LENGTH),
            ],
        )
        job_api_pb2_grpc.add_HA_JobServiceServicer_to_server(self, self.grpc_server)
        port = '[::]:{}'.format(56000 + self.this_rank)
        self.grpc_server.add_insecure_port(port)
        self.grpc_server.start()
        logging.info(f'{self.log_summary} Started GRPC server at {port}')


    def init_data_communication(self):
        #dist.init_process_group(self.args.backend, rank=self.this_rank, world_size=len(self.executors) + 1)
        pass

    def init_model(self):
        """Load model"""
        if self.args.task == "detection":
            cfg_from_file(self.args.cfg_file)
            np.random.seed(self.cfg.RNG_SEED)
            self.imdb, _, _, _ = combined_roidb("voc_2007_test", ['DATA_DIR', self.args.data_dir], server=True)

        return init_model()

    def init_client_manager(self, args):
        """
            Currently we implement two client managers:
            1. Random client sampler
                - it selects participants randomly in each round
                - [Ref]: https://arxiv.org/abs/1902.01046
            2. Oort sampler
                - Oort prioritizes the use of those clients who have both data that offers the greatest utility
                  in improving model accuracy and the capability to run training quickly.
                - [Ref]: https://www.usenix.org/conference/osdi21/presentation/lai
        """

        # sample_mode: random or kuiper
        client_manager = clientManager(args.sample_mode, args=args)

        return client_manager

    def load_client_profile(self, file_path):
        # load client profiles
        global_client_profile = {}
        if os.path.exists(file_path):
            with open(file_path, 'rb') as fin:
                # {clientId: [computer, bandwidth]}
                global_client_profile = pickle.load(fin)

        return global_client_profile

    def executor_info_handler(self, executorId, info):

        self.registered_executor_info.add(executorId)
        logging.info(f"{self.log_summary} Received executor {executorId} information, {len(self.registered_executor_info)}/{len(self.executors)}")
        # have collected all executors
        # In this simulation, we run data split on each worker, so collecting info from one executor is enough
        # Waiting for data information from executors, or timeout

        if len(self.registered_executor_info) == len(self.executors):
            client_traces = info['size']
            num_aggregators = info['num_aggregators']

            clients_per_aggr = floor(len(client_traces) / num_aggregators)

            start = (self.this_rank - 1) * clients_per_aggr
            end = self.this_rank * clients_per_aggr
            client_pool = client_traces[start:end]
            clientId = start + 1
            logging.info(f"{self.log_summary} With {num_aggregators} aggregators, for {clients_per_aggr} clients per aggregator, loading {len(client_pool)} client traces from {clientId} to {end}...")

            for _size in client_pool:
                # since the worker rankId starts from 1, we also configure the initial dataId as 1
                mapped_id = clientId%len(self.client_profiles) if len(self.client_profiles) > 0 else 1
                systemProfile = self.client_profiles.get(mapped_id, {'computation': 1.0, 'communication':1.0})
                self.client_manager.registerClient(executorId, clientId, size=_size, speed=systemProfile)
                self.client_manager.registerDuration(clientId, batch_size=self.args.batch_size,
                    upload_epoch=self.args.local_steps, upload_size=self.model_update_size, download_size=self.model_update_size)
                clientId += 1

            logging.info("{} Info of all feasible clients {}".format(self.log_summary, self.client_manager.getDataInfo()))

            # start to sample clients
            # self.round_completion_handler() removing this and calling it after connection to aggregators is finished


    def tictak_client_tasks(self, sampled_clients, num_clients_to_collect):
        """We try to remove dummy events as much as possible, by removing the stragglers/offline clients in overcommitment"""

        sampledClientsReal = []
        completionTimes = []
        completed_client_clock = {}
        # 1. remove dummy clients that are not available to the end of training
        for client_to_run in sampled_clients:
            client_cfg = self.client_conf.get(client_to_run, self.args)

            exe_cost = self.client_manager.getCompletionTime(client_to_run,
                                    batch_size=client_cfg.batch_size, upload_epoch=client_cfg.local_steps,
                                    upload_size=self.model_update_size, download_size=self.model_update_size)

            roundDuration = exe_cost['computation'] + exe_cost['communication']
            # if the client is not active by the time of collection, we consider it is lost in this round
            if self.client_manager.isClientActive(client_to_run, roundDuration + self.global_virtual_clock):
                sampledClientsReal.append(client_to_run)
                completionTimes.append(roundDuration)
                completed_client_clock[client_to_run] = exe_cost

        num_clients_to_collect = min(num_clients_to_collect, len(completionTimes))
        # 2. get the top-k completions to remove stragglers
        sortedWorkersByCompletion = sorted(range(len(completionTimes)), key=lambda k:completionTimes[k])
        top_k_index = sortedWorkersByCompletion[:num_clients_to_collect]
        clients_to_run = [sampledClientsReal[k] for k in top_k_index]

        dummy_clients = [sampledClientsReal[k] for k in sortedWorkersByCompletion[num_clients_to_collect:]]
        round_duration = completionTimes[top_k_index[-1]]

        return clients_to_run, dummy_clients, completed_client_clock, round_duration


    def run(self):
        self.eventLogger.log(EventType.start_aggregator)
        self.network_traffic()
        self.setup_env()
        self.model = self.init_model()
        for i in range(len(self.aggregators)):
            self.HA_models.append(init_model())
        self.save_last_param()

        self.model_update_size = sys.getsizeof(pickle.dumps(self.model))/1024.0*8. # kbits
        self.client_profiles = self.load_client_profile(file_path=self.args.device_conf_file)
        self.event_monitor()


    def select_participants(self, select_num_participants, overcommitment=1.3):
        return sorted(self.client_manager.resampleClients(int(select_num_participants*overcommitment), cur_time=self.global_virtual_clock))


    def client_completion_handler(self, results):
        """We may need to keep all updates from clients, if so, we need to append results to the cache"""
        # Format:
        #       -results = {'clientId':clientId, 'update_weight': model_param, 'moving_loss': epoch_train_loss,
        #       'trained_size': count, 'wall_duration': time_cost, 'success': is_success 'utility': utility}
        if self.args.gradient_policy in ['q-fedavg']:
            self.client_training_results.append(results)

        # Feed metrics to client sampler
        self.stats_util_accumulator.append(results['utility'])
        self.loss_accumulator.append(results['moving_loss'])

        self.client_manager.registerScore(results['clientId'], results['utility'], auxi=math.sqrt(results['moving_loss']),
                    time_stamp=self.epoch,
                    duration=self.virtual_client_clock[results['clientId']]['computation']+self.virtual_client_clock[results['clientId']]['communication']
                )

        device = self.device
        """
            [FedAvg] "Communication-Efficient Learning of Deep Networks from Decentralized Data". 
            H. Brendan McMahan, Eider Moore, Daniel Ramage, Seth Hampson, Blaise Aguera y Arcas. AISTATS, 2017
        """
        # Start to take the average of updates, and we do not keep updates to save memory
        # Importance of each update is 1/#_of_participants
        importance = 1./self.tasks_round
        sd = self.model.state_dict()
        if len(self.model_in_update) == 0:
            self.model_in_update = [True]

            for idx, param in enumerate(sd.values()):
                param.data = (torch.from_numpy(results['update_weight'][idx]).to(device=device)*importance).to(dtype=param.data.dtype)
        else: 
            for idx, param in enumerate(sd.values()):
                param.data +=(torch.from_numpy(results['update_weight'][idx]).to(device=device)*importance).to(dtype=param.data.dtype)
        self.model.load_state_dict(sd)

    def save_last_param(self):
        self.last_global_model = [param.data.clone() for param in self.model.parameters()]

    def round_weight_handler(self, last_model, current_model):
        if self.epoch > 1:
            self.optimizer.update_round_gradient(last_model, current_model, self.model)
            
    def round_completion_handler(self):
        self.global_virtual_clock += self.round_duration
        self.epoch += 1
        self.eventLogger.log(EventType.end_round)

        if self.epoch % self.args.decay_epoch == 0:
            self.args.learning_rate = max(self.args.learning_rate*self.args.decay_factor, self.args.min_learning_rate)

        # handle the global update w/ current and last
        self.round_weight_handler(self.last_global_model, [param.data.clone() for param in self.model.parameters()])

        avgUtilLastEpoch = sum(self.stats_util_accumulator)/max(1, len(self.stats_util_accumulator))
        # assign avg reward to explored, but not ran workers
        for clientId in self.round_stragglers:
            self.client_manager.registerScore(clientId, avgUtilLastEpoch,
                                    time_stamp=self.epoch,
                                    duration=self.virtual_client_clock[clientId]['computation']+self.virtual_client_clock[clientId]['communication'],
                                    success=False)

        avg_loss = sum(self.loss_accumulator)/max(1, len(self.loss_accumulator))
        logging.info(f"{self.log_summary} Wall clock: {round(self.global_virtual_clock)} s, Epoch: {self.epoch}, Planned participants: " + \
            f"{len(self.sampled_participants)}, Succeed participants: {len(self.stats_util_accumulator)}, Training loss: {avg_loss}")

        self.Neptune["train/epoch/loss"].log(avg_loss)


        # update select participants
        self.sampled_participants = self.select_participants(select_num_participants=len(self.executors), overcommitment=self.args.overcommitment)
        clientsToRun, round_stragglers, virtual_client_clock, round_duration = self.tictak_client_tasks(self.sampled_participants, len(self.executors))

        logging.info(f"{self.log_summary} Selected participants to run: {clientsToRun}:\n{virtual_client_clock}")

        # Issue requests to the resource manager; Tasks ordered by the completion time
        self.resource_manager.register_tasks(clientsToRun)
        self.tasks_round = len(clientsToRun)

        self.save_last_param()
        self.round_stragglers = round_stragglers
        self.virtual_client_clock = virtual_client_clock
        self.round_duration = round_duration
        self.model_in_update = []
        self.test_result_accumulator = []
        self.stats_util_accumulator = []
        self.client_training_results = []

        if self.epoch >= self.args.epochs:
            self.event_queue.append('stop')

        elif self.epoch % self.args.regional_interval == 0:
            logging.info(f"{self.log_summary} add HA to queue")
            self.event_queue.append('horizontal_update')
            if self.epoch % self.args.eval_interval == 0:
                self.event_queue.append('update_model')
                self.event_queue.append('test')
            else:
                self.event_queue.append('update_model')
                self.event_queue.append('start_round')

        elif self.epoch % self.args.eval_interval == 0:
            self.event_queue.append('update_model')
            self.event_queue.append('test')
        else:
            self.event_queue.append('update_model')
            self.event_queue.append('start_round')


    def testing_completion_handler(self, results):
        self.test_result_accumulator.append(results)

        # Have collected all testing results
        if len(self.test_result_accumulator) == len(self.executors):
            accumulator = self.test_result_accumulator[0]
            for i in range(1, len(self.test_result_accumulator)):
                if self.args.task == "detection":
                    for key in accumulator:
                        if key == "boxes":
                            for j in range(self.imdb.num_classes):
                                accumulator[key][j] = accumulator[key][j] + self.test_result_accumulator[i][key][j]
                        else:
                            accumulator[key] += self.test_result_accumulator[i][key]
                else:
                    for key in accumulator:
                        accumulator[key] += self.test_result_accumulator[i][key]
            if self.args.task == "detection":
                self.testing_history['perf'][self.epoch] = {'round': self.epoch, 'clock': self.global_virtual_clock,
                    'top_1': round(accumulator['top_1']*100.0/len(self.test_result_accumulator), 4),
                    'top_5': round(accumulator['top_5']*100.0/len(self.test_result_accumulator), 4),
                    'loss': accumulator['test_loss'],
                    'test_len': accumulator['test_len']
                    }
            else:
                self.testing_history['perf'][self.epoch] = {'round': self.epoch, 'clock': self.global_virtual_clock,
                    'top_1': round(accumulator['top_1']/accumulator['test_len']*100.0, 4),
                    'top_5': round(accumulator['top_5']/accumulator['test_len']*100.0, 4),
                    'loss': accumulator['test_loss']/accumulator['test_len'],
                    'test_len': accumulator['test_len']
                    }


            logging.info("{} FL Testing in epoch: {}, virtual_clock: {}, top_1: {} %, top_5: {} %, test loss: {:.4f}, test len: {}"
                    .format( self.log_summary, self.epoch, self.global_virtual_clock, self.testing_history['perf'][self.epoch]['top_1'],
                    self.testing_history['perf'][self.epoch]['top_5'], self.testing_history['perf'][self.epoch]['loss'],
                    self.testing_history['perf'][self.epoch]['test_len']))

            self.Neptune["train/epoch/accuracy"].log(self.testing_history['perf'][self.epoch]['top_1'])

            # Dump the testing result
            with open(os.path.join(logDir, 'testing_perf'), 'wb') as fout:
                pickle.dump(self.testing_history, fout)

            self.event_queue.append('start_round')

    def get_client_conf(self, clientId):
        # learning rate scheduler
        conf = {}
        conf['learning_rate'] = self.args.learning_rate
        return conf

    def event_monitor(self):
        logging.info(f"{self.log_summary} Start monitoring events ...")
        start_time = time.time()
        time.sleep(20)

        while time.time() - start_time < 2000:
            try:
                self.executors.open_grpc_connection()
                for executorId in self.executors:
                    response = self.executors.get_stub(executorId).ReportExecutorInfo(
                        job_api_pb2.ReportExecutorInfoRequest())
                    self.executor_info_handler(executorId, {"size": response.training_set_size, "num_aggregators": self.args.num_aggregators})
                break
                
            except Exception as e:
                self.executors.close_grpc_connection()
                logging.warning(f"{e}: Have not received executor information. This may due to slow data loading (e.g., Reddit)")
                time.sleep(30)

        logging.info(f"{self.log_summary} Have received all executor information")

        """TODO: fix"""
        while True:
            try:
                self.aggregators.open_grpc_connection()
                break

            except Exception as e:
                logging.error(e)
                self.aggregators.close_grpc_connection()
                time.sleep(10)

        logging.info(f"{self.log_summary} Have opened connection to all aggregators")
        self.round_completion_handler()

        while True:
            import threading
            self.eventLogger.log(EventType.start_eventmonitor)
            if len(self.event_queue) != 0:
                event_msg = self.event_queue.popleft()
                send_msg = {'event': event_msg}

                if event_msg == 'update_model':
                    self.eventLogger.log(EventType.start_round)
                    serialized_tensors = []
                    threads = []
                    # TODO: do serialization in parallel
                    for param in self.model.state_dict().values():
                        buffer = io.BytesIO()
                        torch.save(param.data.to(device='cpu'), buffer)
                        buffer.seek(0)
                        serialized_tensors.append(buffer.read())

                    update_model_request = job_api_pb2.UpdateModelRequest()

                    def executorUpdateRequest_delayed(executorId):
                        time.sleep(self.args.local_delay)
                        _ = self.executors.get_stub(executorId).UpdateModel(
                            job_api_pb2.UpdateModelRequest(serialized_tensor=param)
                                for param in serialized_tensors)

                    for executorId in self.executors:
                        thread = threading.Thread(target=executorUpdateRequest_delayed, args=[executorId])
                        thread.start()
                        threads.append(thread)

                    for thread in threads:
                        thread.join()

                elif event_msg == 'start_round':
                    threads = []

                    def executorTrainRequest_delayed(executorId, clientId, config):
                        time.sleep(self.args.local_delay)
                        _ = self.executors.get_stub(executorId).Train(
                                job_api_pb2.TrainRequest(
                                    client_id=clientId,
                                    serialized_train_config=pickle.dumps(config)))

                    for executorId in self.executors:
                        next_clientId = self.resource_manager.get_next_task()

                        if next_clientId is not None:
                            # TODO: Remove sending train request via server_event_queue
                            config = self.get_client_conf(next_clientId)
                            self.server_event_queue[executorId].put({'event': 'train', 'clientId':next_clientId, 'conf': config})

                            thread = threading.Thread(target=executorTrainRequest_delayed, args=[executorId, next_clientId, config])
                            thread.start()
                            threads.append(thread)

                    for thread in threads:
                        thread.join()

                elif event_msg == 'horizontal_update':
                    self.eventLogger.log(EventType.start_HAround)
                    HAstartTime = time.time()
                    serialized_tensors = []
                    threads = []
                    # TODO: do serialization in parallel

                    for param in self.model.state_dict().values():
                        #logging.info(f"{self.log_summary} serializing params {param.data}")
                        buffer = io.BytesIO()
                        torch.save(param.data.to(device='cpu'), buffer)
                        buffer.seek(0)
                        serialized_tensors.append(buffer.read())

                    path = os.path.join(logDir, f'GlobalModel_pre_ep{self.epoch}_Agg{self.this_rank}')
                    #torch.save(self.model, path)

                    def aggregatorUpdateRequest_delayed(aggregatorId):
                        time.sleep(self.args.backbone_delay)
                        _ = self.aggregators.get_stub(aggregatorId).HA_UpdateModel(
                            job_api_pb2.HA_UpdateModelRequest(serialized_tensor=param)
                                for param in serialized_tensors)

                    timeStart = time.time()
                    netStart = psutil.net_io_counters(pernic=True).get("eth0")

                    for aggregatorId in self.aggregators:
                        thread = threading.Thread(target=aggregatorUpdateRequest_delayed, args=[aggregatorId])
                        thread.start()
                        threads.append(thread)

                    for thread in threads:
                        thread.join()
                    
                    timeEnd = time.time()
                    netEnd = psutil.net_io_counters(pernic=True).get("eth0")

                    sentKbs = (netEnd[0] - netStart[0])/1024 - ((timeEnd-timeStart)*self.backgroundSent)
                    self.Neptune["HA/epoch/sentMb"].log(sentKbs/1024)
                    logging.info(f"{self.log_summary} Round {self.epoch}: horizontal aggregation sent {sentKbs}kb")
                    

                    while(self.HA_models_recieved != len(self.aggregators)):
                        time.sleep(0.1)

                    self.HA_aggregateModels()
                    self.HA_models_recieved = 0

                    HAendTime = time.time()
                    self.Neptune["HA/epoch/aggrTime"].log(HAendTime-HAstartTime)

                    
                        
                    self.eventLogger.log(EventType.end_HAround)

                elif event_msg == 'stop':
                    for executorId in self.executors:
                        _ = self.executors.get_stub(executorId).Stop(job_api_pb2.StopRequest())

                    self.stop()
                    break

                elif event_msg == 'test':
                    self.eventLogger.log(EventType.start_test)
                    threads = []
                    def executorTestRequest_delayed(executorId):
                        time.sleep(self.args.local_delay)
                        response = self.executors.get_stub(executorId).Test(job_api_pb2.TestRequest())
                        self.testing_completion_handler(pickle.loads(response.serialized_test_response))

                    for executorId in self.executors:
                        thread = threading.Thread(target=executorTestRequest_delayed, args=[executorId])
                        thread.start()
                        threads.append(thread)

                    for thread in threads:
                        thread.join()

                    self.eventLogger.log(EventType.end_test)

            elif not self.client_event_queue.empty():

                event_dict = self.client_event_queue.get()
                event_msg, executorId, results = event_dict['event'], event_dict['executorId'], event_dict['return']

                if event_msg != 'train_nowait':
                    logging.info(f"{self.log_summary} Round {self.epoch}: Receive (Event:{event_msg.upper()}) from (Executor:{executorId})")

                # collect training returns from the executor
                if event_msg == 'train_nowait':
                    # pop a new client to run
                    next_clientId = self.resource_manager.get_next_task()

                    if next_clientId is not None:
                        config = self.get_client_conf(next_clientId)
                        runtime_profile = {'event': 'train', 'clientId':next_clientId, 'conf': config}
                        self.server_event_queue[executorId].put(runtime_profile)


                elif event_msg == 'train':
                    # push training results
                    self.client_completion_handler(results)

                    if len(self.stats_util_accumulator) == self.tasks_round:
                        self.round_completion_handler()

                else:
                    logging.error("Unknown message types!")

            # execute every 100 ms
            time.sleep(0.1)

        self.executors.close_grpc_connection()
        self.aggregators.close_grpc_connection()
        self.grpc_server.stop(0)
        self.eventLogger.log(EventType.shutdown_aggregator)
        with open(os.path.join(logDir, f'eventLoggerAgg{self.this_rank}'), 'wb') as fout:
            pickle.dump(self.eventLogger.events, fout)


    def stop(self):
        logging.info(f"{self.log_summary} Terminating the aggregator ...")
        time.sleep(5)
        self.control_manager.shutdown()


    def HA_UpdateModel(self, request_iterator, context):
        """A GRPC function for JobService invoked by HA_UpdateModel request
        """
        logging.info(f'{self.log_summary} Recieved GRPC HA_UpdateModel request')
        self.HA_update_model_handler(request_iterator)
        time.sleep(self.args.backbone_delay)
        return job_api_pb2.HA_UpdateModelResponse()

    def HA_update_model_handler(self, request_iterator):
        self.HA_models[self.HA_models_recieved].to(device=self.device)
        sd = self.HA_models[self.HA_models_recieved].state_dict()
        for param, request in zip(sd.values(), request_iterator):
            buffer = io.BytesIO(request.serialized_tensor)
            buffer.seek(0)
            param.data = torch.load(buffer).to(device=self.device)

        self.HA_models[self.HA_models_recieved].load_state_dict(sd)

        path = os.path.join(logDir, f'GlobalModel_recievedby_ep{self.epoch}_Agg{self.this_rank}')
        #torch.save(self.HA_models[self.HA_models_recieved], path) 

        self.HA_models_recieved += 1     

        #for param in tmpModel.state_dict().values():    
        #    logging.info(f' eTOR {self.this_rank}: Deserializing {param.data}')
        
        #self.HA_models.append(tmpModel)


    def HA_aggregateModels(self):
        device = self.device
        self.eventLogger.log(EventType.start_HAaggregateProcess)

        """Using FEDAVG as performed above in client_completion_handler()"""
        importance = 1./(len(self.aggregators)+1)


        sd = self.model.state_dict()
        for param, update in zip(sd.values(), self.model.state_dict().values()):
            param.data = (update.data*importance).to(dtype=param.data.dtype)

        i = 0
        for model in self.HA_models:
            path = os.path.join(logDir, f'GlobalModel_HAmodel{i}_ep{self.epoch}_Agg{self.this_rank}')
            i+=1
            #torch.save(model, path)
            for param, update in zip(sd.values(), model.state_dict().values()):
                param.data += (update.to(device=device)*importance).to(dtype=param.data.dtype)

        self.model.load_state_dict(sd)
        # Dump the result for manual verification
        path = os.path.join(logDir, f'GlobalModel_post_ep{self.epoch}_Agg{self.this_rank}')
        #torch.save(self.model, path)
        self.eventLogger.log(EventType.end_HAaggregateProcess)

    def network_traffic(self):
        totSent = 0
        totRecieved = 0
        for i in range(5):
            before = psutil.net_io_counters(pernic=True).get("eth0")
            time.sleep(1)
            after = psutil.net_io_counters(pernic=True).get("eth0")
            totSent += (after[0] - before[0])/1024
            totRecieved += (after[1] - before[1])/1024
            time.sleep(1)

        self.backgroundSent = (totSent)/5 
        self.backgroundRecieved = (totRecieved)/5 
        logging.info(f"{self.log_summary} background network traffic is about {self.backgroundSent}kbps sent and {self.backgroundRecieved}kbps recieved")
        

if __name__ == "__main__":
    aggregator = Aggregator(args)
    aggregator.run()
