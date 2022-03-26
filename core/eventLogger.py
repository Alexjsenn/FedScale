import time
from enum import Enum

class EventType(Enum):
    start_eventmonitor = 1
    start_aggregator = 2
    shutdown_aggregator = 3
    start_test = 4
    end_test = 5
    start_round = 6
    end_round = 7
    start_HAround = 8
    end_HAround = 9
    start_HAaggregateProcess = 10
    end_HAaggregateProcess = 11

class Event(object):
    def __init__(self, type):
        self.type = type         # init, start_local_round, end_local_round, init_h_aggregation.... 
        self.stamp = time.time()

    def __str__(self):
        return f"{self.stamp} - {EventType(self.type).name}"

class EventLogger(object):
    def __init__(self):
        self.events = []

    def log(self, event):
        self.events.append(Event(event))