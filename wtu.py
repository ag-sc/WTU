#!/usr/bin/env python

import sys, io
import json
from json.decoder import JSONDecodeError

from wtu.table import Table
from wtu.task.literalnormalization import LiteralNormalization
from wtu.task.entitylinking import EntityLinking, EntityLinkingBackendSQLite

tasks = [
    LiteralNormalization(),
    EntityLinking(
        EntityLinkingBackendSQLite('el.db')
    ),
]

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

                for task in tasks:
                    task.run(table)

                # output annotated table as json
                print(json.dumps(table.dump()))

        # ignore JSON decoding errors
        except JSONDecodeError:
            pass
