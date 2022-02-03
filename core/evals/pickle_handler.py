import pickle
import os
import argparse
import matplotlib.pyplot as plt
import numpy as np

parser = argparse.ArgumentParser()

parser.add_argument("-a", "--a", dest = "a", default = True, help="All (print)")

args = parser.parse_args()

print( "Print all? {}".format(args.a))
if args.a == "False":
    var = input("Number of cifar100 logging folder: ")
    pickle_file = open("/home/ubuntu/FedScale/core/evals/logs/cifar100/"+ var +"/aggregator/testing_perf", "rb")
    objects = []
    while True:
        try:
            objects.append(pickle.load(pickle_file))
        except EOFError:
            break
    pickle_file.close()

    #print(objects[0]['perf'])
    epochs = 0
    loss = []
    top_five = []
    for key, value in objects[0]['perf'].items():
        print(key, value)
        loss.append(value['loss'])
        top_five.append(value['top_5'])
        epochs = epochs+1
    epochs_l = np.arange(1, epochs + 1)
    plt.figure(var + '_Loss')
    plt.title("Testing Performance; Loss")
    plt.plot(epochs_l, loss, label="Test")
    plt.xlabel("Epochs")
    plt.ylabel("Loss")
    plt.legend(loc='best')
    plt.savefig(var + '_Loss' + '.png')
    plt.figure(var + '_Acc')
    plt.title("Testing Performance; Accuracy")
    plt.plot(epochs_l,top_five, label="Test")
    plt.xlabel("Epochs")
    plt.ylabel("Accuracy")
    plt.legend(loc='best')
    plt.savefig(var + '_Acc' + '.png')
    
else:
    #need a list of all folders in /home/ubuntu/FedScale/core/evals/logs/cifar100
    cifar100_directory_contents = os.listdir("/home/ubuntu/FedScale/core/evals/logs/cifar100/")
    #print(cifar100_directory_contents)
    for experiment in cifar100_directory_contents:
        print("Experiment folder : {}".format(experiment))
        pickle_file = open("/home/ubuntu/FedScale/core/evals/logs/cifar100/"+ experiment +"/aggregator/testing_perf", "rb")
        objects = []
        while True:
            try:
                objects.append(pickle.load(pickle_file))
            except EOFError:
                break
        pickle_file.close()

        #print(objects[0]['perf'])
        epochs = 0
        loss = []
        top_five = []
        for key, value in objects[0]['perf'].items():
            print(key, value)
            loss.append(value['loss'])
            top_five.append(value['top_5'])
            epochs = epochs+1
        epochs_l = np.arange(1, epochs + 1)
        plt.figure(experiment + '_Loss')
        plt.title("Testing Performance; Loss")
        plt.plot(epochs_l, loss, label="Test")
        plt.xlabel("Epochs")
        plt.ylabel("Loss")
        plt.legend(loc='best')
        plt.savefig(experiment + '_Loss' + '.png')
        plt.figure(experiment + '_Acc')
        plt.title("Testing Performance; Accuracy")
        plt.plot(epochs_l, top_five, label="Test")
        plt.xlabel("Epochs")
        plt.ylabel("Accuracy")
        plt.legend(loc='best')
        plt.savefig(experiment + '_Acc' + '.png')


