import pickle
from eventLogger import EventType
from statistics import mean

def print_divider(str):
    print(f"\n~~~~~~~~~~~~ {str} ~~~~~~~~~~~~")

def runtime(events):
    return events[-1].stamp - events[0].stamp

def mean_time(start_event, end_event, events):
    round_events = list(filter(lambda event: event.type == start_event or 
        event.type == end_event, events))
    
    times = []
    while bool(round_events):
        if len(round_events) >= 2:
            if (round_events[0].type == start_event and 
                round_events[1].type == end_event):
                times.append(round_events[1].stamp - round_events[0].stamp)
        round_events.pop(0)

    if not bool(times): times = [0]
    return mean(times)

def mean_roundtime(events):
    return mean_time(EventType.start_round, EventType.end_round, events)

def mean_HA_roundtime(events):
    return mean_time(EventType.start_HAround, EventType.end_HAround, events)

def mean_HA_aggregation_time(events):
    return mean_time(EventType.start_HAaggregateProcess, EventType.end_HAaggregateProcess, events)

def mean_overall(agg_events, transform):
    data = []
    for agg in agg_events:
        data.append(transform(agg))
    if not bool(data): data = [0]
    return mean(data)


################################################################################
num_aggregators = 2
aggregator_events = []

for rank in range(1,num_aggregators+1):
    path = f"./evals/logs/femnist/0326_114256/aggregator/eventLoggerAgg{rank}"

    with open(path,'rb') as fin:
        aggregator_events.append(pickle.load(fin))

# Aggregator specific info, looking at aggregator 1
print_divider("Aggregator 1 Specific Information")
print(f"Total run time: {runtime(aggregator_events[0])}")
print(f"Average round time: {mean_roundtime(aggregator_events[0])}")
print(f"Average HA round time: {mean_HA_roundtime(aggregator_events[0])}")
print(f"Average HA aggregation time: {mean_HA_aggregation_time(aggregator_events[0])}")


# Mean stats for all aggregators
print_divider("Mean Aggregator Stats")
print(f"Average runtime: {mean_overall(aggregator_events, runtime)}")
print(f"Average round time: {mean_overall(aggregator_events, mean_roundtime)}")
print(f"Average HA round time: {mean_overall(aggregator_events, mean_HA_roundtime)}")
print(f"Average HA aggregation time: {mean_overall(aggregator_events, mean_HA_aggregation_time)}")
