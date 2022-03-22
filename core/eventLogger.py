import time

class Event(object):
    def __init__(self, type):
        self.type = type         # init, start_local_round, end_local_round, init_h_aggregation.... 
        self.stamp = time.time()

class EventLogger(object):
    def __init__(self):
        self.events = []

    def log(self, event):
        self.events.append(Event(event))