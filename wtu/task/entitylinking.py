from abc import ABCMeta, abstractmethod
import io, csv
from operator import itemgetter
from collections import defaultdict
import Levenshtein

from wtu.task import Task
from wtu.table import Table
from wtu.util import URI

# Levenshtein similarity. Between 0 and 1
# 0: completely differnt
# 1: identical
def levenshtein_similarity(str_a, str_b):
    edit_distance = Levenshtein.distance(str_a, str_b)
    max_len = max(len(str_a), len(str_b))
    return 1 - edit_distance/max_len

class EntityLinking(Task):
    backends_available = {}

    @classmethod
    def register_backend(cls, name, backend):
        cls.backends_available[name] = backend

    def __init__(self, backend, top_n=3, fuzzy=None):
        self.top_n = top_n
        self.fuzzy = fuzzy
        if self.fuzzy is None:
            self.fuzzy = [False, 1]

        # instantiate backend
        backend_name, backend_args = backend
        self.backend = EntityLinking.backends_available[backend_name](**backend_args)

    def run(self, table: Table) -> None:
        cellset = table.cells()

        if 'headerRowIndex' in table.table_data:
            header_row_index = table.table_data['headerRowIndex']
            if header_row_index != -1:
                cellset = cellset.where(lambda cell: cell.row_idx != header_row_index)

        # iterate over all cells
        for cell in cellset:
            # query the backend for mentions of the cell's content
            query_res = self.backend.query(cell.content)

            if self.fuzzy[0] and len(query_res) == 0:
                query_res = self.backend.fuzzy_search(cell.content, fuzzy_cutoff=self.fuzzy[1])

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
                    'source': 'preprocessing',
                    'task': 'EntityLinking',
                    'type': 'resource',
                    'resource_uri': uri.long(),
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
                uri = URI.parse(uri, 'dbr')
                self.index[mention.lower()].append((uri, int(frequency)))

    def query(self, mention):
        mention = mention.lower()

        try:
            return self.index[mention]
        except KeyError:
            return []

    def fuzzy_search(self, mention, fuzzy_cutoff=1):
        mention = mention.lower()
        res = []

        for index_mention, index_data in self.index.items():
            if levenshtein_similarity(mention, index_mention) >= fuzzy_cutoff:
                res.extend(index_data)

        return res

# register backends with the EntityLinking main class
EntityLinking.register_backend('csv', EntityLinkingBackendCSV)
