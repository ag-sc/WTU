#!/usr/bin/env python

import sys, io, os
from itertools import islice
from multiprocessing import Pool
import json
from json.decoder import JSONDecodeError

from wtu.table import Table
from wtu.task.literalnormalization import LiteralNormalization
from wtu.task.entitylinking import EntityLinking
from wtu.task.languagedetection import LanguageDetection
from wtu.task.literallinking import LiteralLinking

# utility function (print message to STDERR and exit)
def die(message, return_code=1):
    print(message, file=sys.stderr)
    sys.exit(return_code)

def read_chunks(fh, chunk_size):
    while True:
        lines = list(islice(fh, chunk_size))
        if not lines:
            break
        yield lines

def process_line(json_line):
    try:
        table_data = json.loads(json_line)

        # create Table object from 'relation' field
        if 'relation' in table_data and len(table_data['relation']) > 0:
            # create table object from table_data
            table = Table(table_data)

            # run scheduled tasks
            for task in tasks_scheduled:
                if not task.run(table):
                    return None
            else:
                # output annotated table as json
                return json.dumps(table.dump())
        else:
            return None

    # ignore JSON decoding errors
    except JSONDecodeError:
        return None

def main():
    # we need at least one command line argument
    if len(sys.argv) < 2:
        die('usage: {:s} <config file>'.format(sys.argv[0]))

    # get config file name from command line arguments
    # and prepare `config'
    config_file_name = sys.argv[1]
    config = {}

    # read JSON formatted configuration from the config file
    with io.open(config_file_name, 'r') as config_fh:
        try:
            config = json.load(config_fh)
        except:
            die('Failed to read config file "{:s}". Malformed JSON!'.format(config_file_name))

    # known tasks and their names
    tasks_available = {
        task_cls.__name__: task_cls
        for task_cls in [LanguageDetection, LiteralNormalization, EntityLinking, LiteralLinking]
    }

    # initialize list of tasks scheduled to be run
    global tasks_scheduled
    tasks_scheduled = []

    # get tasks from configuration
    for task_description in config['tasks']:
        if 1 <= len(task_description) <= 2:
            if len(task_description) < 2:
                task_description.append({})

            task_name, task_args = task_description
            task = tasks_available[task_name](**task_args)
            tasks_scheduled.append(task)
        else:
            print('Invalid task', task_description)
            sys.exit(1)

    # number of processes to spawn
    # defaults to number of CPUs in the system
    # can be overridden unsing the config file's 'n_processes' key
    n_processes = os.cpu_count()
    if n_processes is None:
        n_processes = 1
    if 'n_processes' in config:
        n_processes = config['n_processes']

    # number of input lines to hold in memory at any time
    # defaults to ten per processes
    # can be overridden using the config files 'chunk_size' key
    chunk_size = 10 * n_processes
    if 'chunk_size' in config:
        chunk_size = config['chunk_size']

    # start processing JSON from STDIN
    # using a pool of worker processes
    with Pool(processes=n_processes) as pool:
        # input data encoding is broken (utf-8 with the occasional latin-1 thrown in)
        # -> ignore encoding errors
        with io.open(sys.stdin.fileno(), 'r', encoding='utf-8', errors='ignore') as stdin:
            # read JSON data line-by-line
            for chunk in read_chunks(stdin, chunk_size):
                for line in pool.map(process_line, chunk):
                    if line is not None:
                        print(line)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        die('Keyboard Interrupt!')
