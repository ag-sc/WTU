from abc import ABCMeta, abstractmethod
import sqlite3
import io, csv
from operator import itemgetter
from collections import defaultdict

from wtu.task import Task
from wtu.table import Table

class EntityLinking(Task):
    backends_available = {}

    @classmethod
    def register_backend(cls, name, backend):
        cls.backends_available[name] = backend

    def __init__(self, backend, top_n=3):
        self.top_n = top_n

        # instantiate backend
        backend_name, backend_args = backend
        self.backend = EntityLinking.backends_available[backend_name](**backend_args)

    def run(self, table: Table) -> None:
        # get cells that do not have a 'LiteralNormalization' annotation
        # FIXME: cellset conditions like this should be moved to the `table' module
        cellset = table.cells(
            lambda cell:
                len(list(
                    annotation
                    for annotation in cell.annotations
                    if annotation['source'] == 'LiteralNormalization'
                )) == 0
        )

        # iterate over all cells
        for cell in cellset:
            # query the backend for mentions of the cell's content
            query_res = self.backend.query(cell.content)

            # get top <n> results (weighted by frequency of occurrence)
            top_n_res = sorted(
                query_res,
                key=itemgetter(1),
                reverse=True
            )[:self.top_n]

            # sum all frequencies to normalize the individual frequencies
            frequency_sum = sum(
                map(itemgetter(1), top_n_res)
            )

            # add annotations for each identified entity
            for entity in top_n_res:
                uri, frequency = entity
                normalized_frequency = frequency/frequency_sum

                cell.annotations.append({
                    'type': 'resource',
                    'source': 'EntityLinking',
                    'uri': uri,
                    'frequency': normalized_frequency,
                })

# EntityLinkingBackend interface
class EntityLinkingBackend(metaclass=ABCMeta):
    # EntityLinkingBackend's must implement a `query' method
    @abstractmethod
    def query(self, mention): pass

# SQLite backend
class EntityLinkingBackendSQLite(EntityLinkingBackend):
    def __init__(self, db_file):
        # sqlite database file
        self.db_file = db_file

        # connect to database
        self.connection = sqlite3.connect(self.db_file)
        self.cursor = self.connection.cursor()

        # run this query against the database for each invocation
        # of the `query' method
        self.select_stmnt = 'SELECT uri, frequency FROM `resource` WHERE mention = ?'

    def query(self, mention):
        # execute query
        self.cursor.execute(self.select_stmnt, (mention,))

        # return all matching datasets
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

# register backends with the EntityLinking main class
EntityLinking.register_backend('csv', EntityLinkingBackendCSV)
EntityLinking.register_backend('sqlite', EntityLinkingBackendSQLite)
