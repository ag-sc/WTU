#!/usr/bin/env python

import io, sys, json
from json.decoder import JSONDecodeError
from collections import Counter

from wtu.table import Table

gold_source = 'gold-v2'
preprocessing_source = 'preprocessing'

total_entities = 0
correct_at_k = Counter()
total_missed = 0
missed_no_anno = 0

missed_file = 'eva_prep.missed'
stats_file = 'eva_prep.stats'

# read from stdin, ignore encoding errors
with io.open(sys.stdin.fileno(), 'r', encoding='utf-8', errors='ignore') as stdin, \
io.open(missed_file, 'w') as missed_fh, io.open(stats_file, 'w') as stats_fh:
    # iterate over input. Each line represents one table
    for json_line in stdin:
        try:
            # parse json
            table_data = json.loads(json_line)
            # create Table object to work with
            table = Table(table_data)

            for cell in table.cells():
                gold_el = cell.find_annotations(
                    anno_source = gold_source,
                    anno_task = 'EntityLinking'
                )
                if gold_el:
                    total_entities += 1
                    gold_el = gold_el[0]
                    gold_uri = gold_el['resource_uri']

                    preprocessing_uris = [
                        el_anno['resource_uri'] for el_anno in
                        cell.find_annotations(
                            anno_source = preprocessing_source,
                            anno_task = 'EntityLinking'
                        )
                    ]

                    if gold_uri in preprocessing_uris:
                        for k in range(1, 101):
                            preprocessing_uris_at_k = preprocessing_uris[0:k]
                            if gold_uri in preprocessing_uris_at_k:
                                correct_at_k[k] += 1
                    else:
                        total_missed += 1
                        if len(preprocessing_uris) == 0:
                            missed_no_anno += 1
                        missed_fh.write('"{:s}" {:s} {:s}\n'.format(
                            cell.content,
                            gold_el['resource_uri'],
                            str(preprocessing_uris)
                        ))

        # ignore json decoding errors
        except JSONDecodeError:
            pass

    stats_fh.write('#total entities: {:d}\n#missed: {:d} ({:.2f}%)\n#no annotation: {:d} ({:.2f}%)\n\n'.format(
        total_entities,
        total_missed, total_missed * 100 / total_entities,
        missed_no_anno, missed_no_anno * 100 / total_missed
    ))

    for k, count in correct_at_k.items():
        stats_fh.write('recall@{:d}: {:.3f}\n'.format(
            k, count / total_entities
        ))
