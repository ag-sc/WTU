from abc import ABCMeta, abstractmethod
from wtu.table import Table

class Task(metaclass=ABCMeta):
    @abstractmethod
    def run(self, table: Table) -> None:
        pass
