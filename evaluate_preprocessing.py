#!/usr/bin/env python

import io, sys, json
from json.decoder import JSONDecodeError

from wtu.table import Table

# collect stats
num_tables = 0
total_entities = 0
total_correct = 0
total_only_one = 0
total_highest_freq = 0

# read from stdin, ignore encoding errors
with io.open(sys.stdin.fileno(), 'r', encoding='utf-8', errors='ignore') as stdin:
    # iterate over input. Each line represents one table
    for json_line in stdin:
        try:
            # parse json
            table_data = json.loads(json_line)
            # create Table object to work with
            table = Table(table_data)

            # collect stats
            num_tables += 1
            table_entities = 0
            table_correct = 0
            table_only_one = 0
            table_highest_freq = 0

            # iterate over all cells in the table
            for cell in table.cells():
                # get EntityLinkning annotation from Gold Standard for this cell
                gold_el = cell.find_annotations(
                    anno_source='gold-v2',
                    anno_task='EntityLinking'
                )
                if gold_el:
                    table_entities += 1
                    # extract resource uri from annotation
                    gold_uri = gold_el[0]['resource_uri']
                    # get EntityLinking annotations from our preprocessing
                    preprocessing_el = cell.find_annotations(
                        anno_source='preprocessing',
                        anno_task='EntityLinking'
                    )
                    # extract resource uris and frequencies
                    preprocessing_uris = {
                        annotation['resource_uri']: annotation['frequency']
                        for annotation in preprocessing_el
                    }

                    # check if our annotations also include the gold annotation
                    if gold_uri in preprocessing_uris:
                        table_correct += 1
                        print('Correctly identified "{:s}" as {:s}'.format(
                            cell.content, gold_uri
                        ))
                        # was it the only annotation?
                        if len(preprocessing_uris) == 1:
                            table_only_one += 1
                            print('  * It was the only annotation')
                        # had it the highest frequency?
                        elif max(preprocessing_uris, key=preprocessing_uris.get) == gold_uri:
                            table_highest_freq += 1
                            print('  * It had the highest frequency')

            # update stats
            total_entities += table_entities
            total_correct += table_correct
            total_only_one += table_only_one
            total_highest_freq += table_highest_freq

        # ignore json decoding errors
        except JSONDecodeError:
            pass

    print(
        '---',
        'entitties   : {:5d} ({:.2f}/tbl)'.format(total_entities, total_entities/num_tables),
        'correct     : {:5d} ({:.2f}/tbl)'.format(total_correct, total_correct/num_tables),
        'only one    : {:5d} ({:.2f}/tbl)'.format(total_only_one, total_only_one/num_tables),
        'highest freq: {:5d} ({:.2f}/tbl)'.format(total_highest_freq, total_highest_freq/num_tables),
        sep='\n'
    )
