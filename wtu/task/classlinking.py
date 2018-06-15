from abc import ABCMeta, abstractmethod

import io, csv

from wtu.task import Task
from wtu.table import Table
from wtu.util import URI

class ClassLinking(Task):
    backends_available = {}

    @classmethod
    def register_backend(cls, name, backend):
        cls.backends_available[name] = backend

    def __init__(self, backend):
        backend_name, backend_args = backend
        self.backend = ClassLinking.backends_available[backend_name](**backend_args)

    def run(self, table):
        if 'headerRowIndex' in table.table_data:
            header_row_index = table.table_data['headerRowIndex']
            if header_row_index != -1:
                header_row = table.rows()[header_row_index]
                for cell in header_row:
                    class_uri = self.backend.query(cell.content)
                    if class_uri is not None:
                        class_uri = URI.parse(class_uri, 'dbo')
                        cell.annotations.append({
                            'source': 'preprocessing',
                            'task': 'ClassLinking',
                            'type': 'class',
                            'class_uri': class_uri.long(),
                        })

        return True

class ClassLinkingBackend(metaclass=ABCMeta):
    @abstractmethod
    def query(self, mention): pass

class ClassLinkingBackendCSV(ClassLinkingBackend):
    def __init__(self, index_file, delimiter='\t', quotechar=None):
        self.index = {}

        with io.open(index_file, 'r', encoding='utf-8', errors='ignore') as index_fh:
            csv_reader = csv.reader(index_fh, delimiter=delimiter, quotechar=quotechar)
            for row in csv_reader:
                mention, uri = row
                self.index[mention.lower()] = URI.parse(uri, 'dbo').short()

    def query(self, mention):
        mention = mention.lower()

        try:
            return self.index[mention]
        except KeyError:
            return None

ClassLinking.register_backend('csv', ClassLinkingBackendCSV)
