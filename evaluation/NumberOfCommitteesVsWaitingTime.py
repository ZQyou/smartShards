from src.util import make_intersecting_committees_on_host
from src.structures import Transaction
from src.SawtoothPBFT import sawtooth_container_log_to
from src.api.api_util import get_plain_test
from pathlib import Path
import time
from random import choice
import argparse
import requests
import socket

# defaults
NUMBER_OF_TX = 100
NUMBER_OF_EXPERIMENTS = 10
MIN = 10
MAX = 10
INTERSECTION = 1
OUTPUT_FILE = "SawtoothPBFTPerformanceGraph.csv"

# time between submissions NOTE: range will be min + 1 and max - 1
SUB_MIN = 2  # sec
SUB_MAX = 31

# const
IP_ADDRESS = "localhost"
URL_HOST = "http://{ip}:{port}"


# Opens the output file and writes the results in it for each data point
def make_graph_data(outfile: str, start_size: int, end_size: int, number_of_intersections: int, experiments: int,
                    total_tx: int):
    out = open(outfile, 'w')
    print("Outputting to {}".format(outfile))
    out.write("Committee size, avg waiting time (sec)\n")

    for committee_size in range(start_size, end_size + 1):
        print("---------------------------------------------------------------------------------------")
        print("Starting experiments for committee size {}".format(committee_size))
        avgs = get_avg_for(committee_size, number_of_intersections, experiments, total_tx)
        print("Experiments for committee size {} ended".format(committee_size))
        print("---------------------------------------------------------------------------------------")
        out.write("{s}, {w}\n".format(s=committee_size, w=avgs["waitingTime"]))
    out.close()


# runs each experiment and calc avgs (i.e. creates one data point)
# is responsible for creating and destroying peers
def get_avg_for(number_of_committees: int, number_of_intersections: int, experiments: int, total_tx: int):
    waiting_time = []

    for e in range(experiments):
        print("Setting up experiment {}".format(e))
        peers = make_intersecting_committees_on_host(number_of_committees, number_of_intersections)
        results = run_experiment(peers, total_tx)
        waiting_time += results["waitingTime"]
        print("Cleaning up experiment {}".format(e))
        del peers

    return {"waitingTime": sum(waiting_time) / len(waiting_time)}


# this is one experiment func collects raw data
def run_experiment(peers: dict, total_tx: int):
    print("Running", end='', flush=True)
    waiting_time = []
    submitted_tx = {}
    committee_ids = [peers[p].committee_id_a() for p in peers]
    committee_ids.extend([peers[p].committee_id_b() for p in peers])
    committee_ids = list(dict.fromkeys(committee_ids))
    number_of_submitted_tx = 0
    next_sub = time.time() + choice(range(SUB_MIN, SUB_MAX))

    while len(waiting_time) < total_tx:
        if time.time() > next_sub:
            print("submitting tx {}".format(number_of_submitted_tx))
            next_sub = time.time() + choice(range(SUB_MIN, SUB_MAX))
            tx = Transaction(quorum=choice(committee_ids),
                             key="tx_{}".format(number_of_submitted_tx),
                             value="{}".format(999))
            number_of_submitted_tx += 1
            submitted_tx[time.time()] = tx
            url = URL_HOST.format(ip=IP_ADDRESS, port=choice(list(peers.keys()))) + "/submit/"
            requests.post(url, json=tx.to_json())
        print(".", end=" ")
        check_submitted_tx(waiting_time, submitted_tx, list(peers.keys())[0])

    print()
    return {"waitingTime": waiting_time}


def check_submitted_tx(waiting, sub, port):
    url = URL_HOST.format(ip=IP_ADDRESS, port=port + "/get/")
    for tx in sub:
        if sub[tx].value == get_plain_test(requests.post(url, json=sub[tx].to_json())):
            waiting.append(tx - time.time())
            del sub[tx]


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Make a performance graph for SmartShardsPeer module. '
                                                 'Each data point is a committee size. Runs from a min committee size '
                                                 'to a max')
    parser.add_argument('-o', type=str,
                        help='File to output data (csv format)')
    parser.add_argument('-min', type=int,
                        help='Starting number of committees. Default {}'.format(MIN))
    parser.add_argument('-max', type=int,
                        help='Max committee size. Default {}'.format(MAX))
    parser.add_argument('-i', type=int,
                        help='Intersection between committees. Default {}'.format(INTERSECTION))
    parser.add_argument('-e', type=int,
                        help='Number of experiments to run per data point. Default {}'.format(NUMBER_OF_EXPERIMENTS))
    parser.add_argument('-t', type=int,
                        help='Total number of transactions to submit. Default {}'.format(NUMBER_OF_TX))
    args = parser.parse_args()

    output_file = Path(args.o) if args.o is not None else Path().home().joinpath(OUTPUT_FILE)
    while not output_file.exists():
        output_file.touch()

    experiments = NUMBER_OF_EXPERIMENTS if args.e is None else args.e
    total_tx = NUMBER_OF_TX if args.t is None else args.t
    starting_size = MIN if args.min is None or args.min < 5 else args.min
    ending_size = MAX if args.max is None else args.max
    number_of_intersections = INTERSECTION if args.i is None else args.i

    sawtooth_container_log_to(Path().home().joinpath('{}.SawtoothContainer.log'.format(__file__)))

    print("experiments:{e}, total_tx{t}".format(e=experiments, t=total_tx))

    make_graph_data(output_file, starting_size, ending_size, number_of_intersections, experiments, total_tx)
