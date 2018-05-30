#!/usr/bin/env python

import io, sys, json, csv
from json.decoder import JSONDecodeError

from wtu.table import Table
from wtu.util import URI

# utility function (print message to STDERR and exit)
def die(message, return_code=1):
    print(message, file=sys.stderr)
    sys.exit(return_code)

# usage
if len(sys.argv) != 6:
    die(
        'usage: {:s} <ARGS>\n\n'.format(sys.argv[0]) +
        'ARGS:\n' +
        '\t<gold annotated data>       \n' +
        '\t<EntityLinking index in>    \n' +
        '\t<LiteralLinking index in>   \n' +
        '\t<EntityLinking index out>   \n' +
        '\t<LiteralLinking index out>  \n')

# arguments
(
    gold_data_name,
    el_index_in_name, ll_index_in_name,
    el_index_out_name, ll_index_out_name
) = sys.argv[1:]

# read gold data, collect entities/properties
print('* reading gold annotated data from "{:s}"...'.format(gold_data_name))

gold_entities = set()
gold_properties = set()

with io.open(gold_data_name, 'r', encoding='utf-8', errors='ignore') as gold_data_fh:
    for table_json in gold_data_fh:
        try:
            table_data = json.loads(table_json)
            table = Table(table_data)

            # get EntityLinking annotations from cells
            for cell in table.cells():
                el_annotations = cell.find_annotations(
                    anno_source = 'gold-v2',
                    anno_task = 'EntityLinking'
                )
                for el_anno in el_annotations:
                    resource_uri = URI.parse(el_anno['resource_uri'], 'dbr')
                    gold_entities.add(resource_uri.short())

            # get PropertyLinking annotations from columns
            for column in table.columns():
                pl_annotations = column.find_annotations(
                    anno_source = 'gold-v2',
                    anno_task = 'PropertyLinking'
                )
                for pl_anno in pl_annotations:
                    property_uri = URI.parse(pl_anno['property_uri'])
                    gold_properties.add(property_uri.short())
        except JSONDecodeError:
            pass

# summary
print('  done. {:d} entities, {:d} properties.'.format(
    len(gold_entities), len(gold_properties)
))

# read EntityLinking index input and filter relevant lines
print('* reading entity linking index from "{:s}", writing to "{:s}"...'.format(
    el_index_in_name, el_index_out_name
))

el_index_lines_total = 0
el_index_lines_filtered = 0

with io.open(el_index_in_name, 'r', encoding='utf-8', errors='ignore') as el_index_in_fh, \
io.open(el_index_out_name, 'w') as el_index_out_fh:
    csv_reader = csv.reader(el_index_in_fh, delimiter='\t', quoting=csv.QUOTE_NONE)
    for el_index_row in csv_reader:
        if len(el_index_row) != 3:
            continue
        el_index_lines_total += 1
        index_entity = URI.parse(el_index_row[1], 'dbr').short()
        if index_entity in gold_entities:
            el_index_lines_filtered += 1
            el_index_row[1] = index_entity
            el_index_out_fh.write('\t'.join(el_index_row) + '\n')

# summary
print('  done. filtered {:d} lines from a total of {:d} lines ({:.2f}%).'.format(
    el_index_lines_filtered, el_index_lines_total,
    el_index_lines_filtered * 100 / el_index_lines_total
))

# read LiteralLinking index and filter relevant lines
print('* reading literal linking index from "{:s}", writing to "{:s}..."'.format(
    ll_index_in_name, ll_index_out_name
))

ll_index_lines_total = 0
ll_index_lines_filtered = 0

with io.open(ll_index_in_name, 'r', encoding='utf-8', errors='ignore') as ll_index_in_fh, \
io.open(ll_index_out_name, 'w') as ll_index_out_fh:
    csv_reader = csv.reader(ll_index_in_fh, delimiter='\t', quoting=csv.QUOTE_NONE)
    for ll_index_row in csv_reader:
        if len(ll_index_row) != 4:
            continue
        ll_index_lines_total += 1
        index_entity = URI.parse(ll_index_row[0], 'dbr').short()
        index_property = URI.parse(ll_index_row[1]).short()
        if index_entity in gold_entities and index_property in gold_properties:
            ll_index_lines_filtered += 1
            ll_index_row[0] = index_entity
            ll_index_row[1] = index_property
            ll_index_out_fh.write('\t'.join(ll_index_row) + '\n')

# summary
print('  done. filtered {:d} lines from a total of {:d} lines ({:.2f}%).'.format(
    ll_index_lines_filtered, ll_index_lines_total,
    ll_index_lines_filtered * 100 / ll_index_lines_total
))
