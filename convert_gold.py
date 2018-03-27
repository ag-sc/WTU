#!/usr/bin/env python

import sys, os, io, csv, json
from wtu.table import Table

if len(sys.argv) != 2:
    print('usage: {:s} <gold dir>'.format(sys.argv[0]))
    sys.exit()

# data directories
gold_dir = sys.argv[1]
classes_file = os.path.join(gold_dir, 'classes_GS.csv')
instance_dir = os.path.join(gold_dir, 'instance')
property_dir = os.path.join(gold_dir, 'property')
tables_dir = os.path.join(gold_dir, 'tables')

# load classes_file
classes = dict()
with io.open(classes_file, 'r') as classes_fh:
    classes_reader = csv.reader(classes_fh, delimiter=',', quotechar='"')
    for class_row in classes_reader:
        table_name_ext, class_name, class_uri = class_row
        table_name = table_name_ext.split('.')[0]
        classes[table_name] = (class_name, class_uri)

# iterate over all tables
for table_name_ext in os.listdir(tables_dir):
    table_file = os.path.join(tables_dir, table_name_ext)
    table_name = os.path.splitext(table_name_ext)[0]

    # read table data & create Table object
    with io.open(table_file, 'r', encoding='utf-8', errors='ignore') as table_fh:
        table_data = json.load(table_fh)
        table = Table(table_data)

    # add class annotation if available
    if table_name in classes:
        class_name, class_uri = classes[table_name]
        table.annotations.append({
            'source': 'gold-v2',
            'type': 'class',
            'class_name': class_name,
            'class_uri': class_uri
        })

    # add property annotations (columns)
    key_col_idx = None
    property_file = os.path.join(property_dir, table_name + '.csv')
    if os.path.isfile(property_file):
        col_set = table.columns()
        with io.open(property_file) as property_fh:
            property_reader = csv.reader(property_fh, delimiter=',', quotechar='"')
            for property_row in property_reader:
                # there is at least one malformed file in the gold standard
                # (two instead of three columns). The only thing we can do,
                # is skip these files.
                try:
                    property_uri, column_header, is_key_column, col_idx = property_row
                    col_idx = int(col_idx)
                    column = col_set[col_idx]

                    # property annotation
                    column.annotations.append({
                        'source': 'gold-v2',
                        'type': 'property',
                        'property_uri': property_uri
                    })

                    # key column annotation
                    if is_key_column == 'True':
                        key_col_idx = col_idx
                        column.annotations.append({
                            'source': 'gold-v2',
                            'type': 'key_column',
                        })

                except ValueError:
                    pass

    # add instance annotations
    if key_col_idx is not None:
        instance_file = os.path.join(instance_dir, table_name + '.csv')
        if os.path.isfile(instance_file):
            with io.open(instance_file) as instance_fh:
                instance_reader = csv.reader(instance_fh, delimiter=',', quotechar='"')
                for instance_row in instance_reader:
                    # again, skip malformed files
                    try:
                        resource_uri, value, row_idx = instance_row
                        row_idx = int(row_idx)
                        cell = table.cells()[(key_col_idx, row_idx)]

                        # instance annotation
                        cell.annotations.append({
                            'source': 'gold-v2',
                            'type': 'entity_linking',
                            'resource_uri': resource_uri
                        })

                    except ValueError:
                        pass

    # write annotated table to stdout, skip tables that did not
    # receive any annotation
    if len(table._annotations):
        print(json.dumps(table.dump()))
