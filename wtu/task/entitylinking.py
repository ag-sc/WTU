from abc import ABCMeta, abstractmethod
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
        cellset = table.cells()

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
                map(itemgetter(1), query_res)
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

        return True

# EntityLinkingBackend interface
class EntityLinkingBackend(metaclass=ABCMeta):
    # EntityLinkingBackend's must implement a `query' method
    @abstractmethod
    def query(self, mention): pass

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
