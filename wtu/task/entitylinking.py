from abc import ABCMeta, abstractmethod
import sqlite3
from operator import itemgetter

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
