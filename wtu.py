#!/usr/bin/env python

import sys, io
import json
from json.decoder import JSONDecodeError

from wtu.table import Table
from wtu.task.literalnormalization import LiteralNormalization
from wtu.task.entitylinking import EntityLinking
from wtu.task.languagedetection import LanguageDetection

# utility function (print message to STDERR and exit)
def die(message, return_code=1):
    print(message, file=sys.stderr)
    sys.exit(return_code)

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
        for task_cls in [LanguageDetection, LiteralNormalization, EntityLinking]
    }

    # initialize list of tasks scheduled to be run
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

    # start processing JSON from STDIN
    # input data encoding is broken (utf-8 with the occasional latin-1 thrown in)
    # -> ignore encoding errors
    with io.open(sys.stdin.fileno(), 'r', encoding='utf-8', errors='ignore') as stdin:
        # read JSON data line-by-line
        for json_line in stdin:
            try:
                table_data = json.loads(json_line)

                # create Table object from 'relation' field
                if 'relation' in table_data and len(table_data['relation']) > 0:
                    # create table object from table_data
                    table = Table(table_data)

                    # run scheduled tasks
                    for task in tasks_scheduled:
                        if not task.run(table):
                            break
                    else:
                        # output annotated table as json
                        print(json.dumps(table.dump()))

            # ignore JSON decoding errors
            except JSONDecodeError:
                pass

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        die('Keyboard Interrupt!')
