import pickle
from eventLogger import Event

with open("./evals/logs/femnist/0321_235539/aggregator/eventLoggerAgg1",'rb') as fin:
    events = pickle.load(fin)

print(len(events))