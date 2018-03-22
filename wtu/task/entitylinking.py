from abc import ABCMeta, abstractmethod
import sqlite3
import io, csv
from operator import itemgetter
from collections import defaultdict

from wtu.task import Task
from wtu.table import Table

class EntityLinking(Task):
    def __init__(self, backend, topn=3):
        self.backend = backend
        self.topn = topn

    def run(self, table: Table) -> None:
        cellset = table.cells(
            lambda cell:
                cell.content.isalpha()
        )

        for cell in cellset:
            query_res = self.backend.query(cell.content)

            for entity in sorted(query_res, key=itemgetter(1), reverse=True)[:self.topn]:
                cell.annotations.append({
                    'type': 'resource',
                    'source': 'EntityLinking',
                    'uri': entity[0],
                    'frequency': entity[1],
                })


class EntityLinkingBackend(metaclass=ABCMeta):
    @abstractmethod
    def query(self, mention): pass

class EntityLinkingBackendDict(EntityLinkingBackend):
    def __init__(self, dct):
        self.dct = dct

    def query(self, mention):
        res = []
        try:
            res = self.dct[mention]
        except KeyError:
            pass

        return res

class EntityLinkingBackendSQLite(EntityLinkingBackend):
    def __init__(self, db_file):
        self.db_file = db_file
        self.connection = sqlite3.connect(self.db_file)
        self.cursor = self.connection.cursor()
        self.select_stmnt = 'SELECT uri, frequency FROM `resource` WHERE mention = ?'

    def query(self, mention):
        self.cursor.execute(self.select_stmnt, (mention,))
        return self.cursor.fetchall()

# CSV backend
class EntityLinkingBackendCSV(EntityLinkingBackend):
    def __init__(self, index_file, delimiter='\t', quotechar=None):
        # index dictionary
        self.index = defaultdict(list)

        # read complete `index_file` into the index dictionary
        with io.open(index_file, 'r', encoding='utf-8', errors='ignore') as index_fh:
            csv_reader = csv.reader(index_fh, delimiter=delimiter, quotechar=quotechar)
            for row in csv_reader:
                mention, uri, frequency = row
                self.index[mention].append((uri, frequency))

    def query(self, mention):
        res = []
        try:
            res = [
                (entity[0], int(entity[1]))
                for entity in self.index[mention]
            ]
        except KeyError:
            pass

        return res
