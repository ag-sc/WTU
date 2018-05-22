from abc import ABCMeta, abstractmethod
from typing import Any, Callable, Dict, Generic, Iterator, List, Optional, Tuple, Type, TypeVar

class Table:
    def __init__(self, table_data: Dict) -> None:
        self.table_data = table_data

        if 'annotations' not in self.table_data:
            self.table_data['annotations'] = {}

        self.num_cols = len(self.table_data['relation'])
        self.num_rows = len(self.table_data['relation'][0])

    @property
    def relation(self):
        return self.table_data['relation']

    @property
    def _annotations(self):
        return self.table_data['annotations']

    @property
    def annotations(self):
        anno_idx = ':'

        if anno_idx not in self.table_data['annotations']:
            self.table_data['annotations'][anno_idx] = []

        return self.table_data['annotations'][anno_idx]

    def dump(self) -> Dict:
        # clean annotations
        self.table_data['annotations'] = {
            k: v
            for k, v in self.table_data['annotations'].items()
            if len(v)
        }

        return self.table_data

    def cells(self, *conditions: Callable[['TableCell'], bool]) -> 'TableCellSet':
        return TableCellSet(self, *conditions)

    def columns(self, *conditions: Callable[['TableColumn'], bool]) -> 'TableColumnSet':
        return TableColumnSet(self, *conditions)

    def rows(self, *conditions: Callable[['TableRow'], bool]) -> 'TableRowSet':
        return TableRowSet(self, *conditions)

I_T = TypeVar('I_T')
E_T = TypeVar('E_T')
S_T = TypeVar('S_T')

class QueryResult(Generic[I_T]):
    def __init__(self, parent_set: 'QueryableSet', idx: I_T) -> None:
        self.parent_set = parent_set
        self.idx = idx

    @property
    def my_data(self) -> Any:
        return self.parent_set.data(self.idx)

    def find_annotations(self, anno_source=None, anno_task=None, anno_type=None):
        return [
            annotation
            for annotation in self.annotations
            if (anno_source is None or annotation['source'] == anno_source) and
            (anno_task is None or annotation['task'] == anno_task) and
            (anno_type is None or annotation['type'] == anno_type)
        ]

class QueryableSet(Generic[S_T, E_T, I_T], metaclass=ABCMeta):
    def __init__(self, data_source: S_T, element_type: Type[E_T], *conditions: Callable[[E_T], bool]) -> None:
        self.data_source = data_source
        self.element_type = element_type
        self.conditions = conditions

    @abstractmethod
    def indices(self) -> Iterator[I_T]:
        pass

    @abstractmethod
    def data(self, idx: I_T) -> Any:
        pass

    def __getitem__(self, idx: I_T) -> E_T:
        return self.element_type(self, idx)

    def __iter__(self) -> Iterator[E_T]:
        for idx in self.indices():
            element = self[idx]
            if all(map(lambda condition: condition(element), self.conditions)):
                yield element

class TableCell(QueryResult[Tuple[int, int]]):
    def __init__(self, parent_set: 'TableCellSet', idx: Tuple[int, int]) -> None:
        super().__init__(parent_set, idx)

    @property
    def col_idx(self):
        return self.idx[0]

    @property
    def row_idx(self):
        return self.idx[1]

    @property
    def content(self) -> str:
        return self.my_data['content']

    @property
    def annotations(self) -> List[Dict]:
        return self.my_data['annotations']

class TableCellSet(QueryableSet[Table, TableCell, Tuple[int, int]]):
    def __init__(self, table: Table, *conditions: Callable[[TableCell], bool]) -> None:
        super().__init__(table, TableCell, *conditions)
        self.table = table

    def indices(self) -> Iterator[Tuple[int, int]]:
        for col_idx in range(self.table.num_cols):
            for row_idx in range(self.table.num_rows):
                yield (col_idx, row_idx)

    def data(self, idx: Tuple[int, int]) -> Any:
        col_idx, row_idx = idx
        anno_idx = '{:d}:{:d}'.format(col_idx, row_idx)
        if anno_idx not in self.table._annotations:
            self.table._annotations[anno_idx] = []

        return {
            'content': self.table.relation[col_idx][row_idx],
            'annotations': self.table._annotations[anno_idx],
        }

    def where(self, *conditions: Callable[[TableCell], bool]) -> 'TableCellSet':
        return TableCellSet(self.table, *self.conditions, *conditions)

class TableColumn(TableCellSet, QueryResult[int]):
    def __init__(self, parent_set: 'TableColumnSet', col_idx: int) -> None:
        TableCellSet.__init__(self, parent_set.table)
        QueryResult.__init__(self, parent_set, col_idx)
        self.col_idx = col_idx

    def indices(self) -> Iterator[Tuple[int, int]]:
        for row_idx in range(self.table.num_rows):
            yield (self.col_idx, row_idx)

    @property
    def annotations(self) -> List[Dict]:
        return self.my_data['annotations']

class TableColumnSet(QueryableSet[Table, TableColumn, int]):
    def __init__(self, table: Table, *conditions: Callable[[TableColumn], bool]) -> None:
        super().__init__(table, TableColumn, *conditions)
        self.table = table

    def indices(self) -> Iterator[int]:
        return iter(range(self.table.num_cols))

    def data(self, col_idx: int) -> List[str]:
        anno_idx = '{:d}:'.format(col_idx)
        if anno_idx not in self.table._annotations:
            self.table._annotations[anno_idx] = []

        return {
            'column': self.table.relation[col_idx],
            'annotations': self.table._annotations[anno_idx],
        }

    def where(self, *conditions: Callable[[TableColumn], bool]) -> 'TableColumnSet':
        return TableColumnSet(self.table, *self.conditions, *conditions)

class TableRow(TableCellSet, QueryResult[int]):
    def __init__(self, parent_set: 'TableRowSet', row_idx: int) -> None:
        TableCellSet.__init__(self, parent_set.table)
        QueryResult.__init__(self, parent_set, row_idx)
        self.row_idx = row_idx

    def indices(self) -> Iterator[Tuple[int, int]]:
        for col_idx in range(self.table.num_cols):
            yield (col_idx, self.row_idx)

    @property
    def annotations(self) -> List[Dict]:
        return self.my_data['annotations']

class TableRowSet(QueryableSet[Table, TableRow, int]):
    def __init__(self, table: Table, *conditions: Callable[[TableRow], bool]) -> None:
        super().__init__(table, TableRow, *conditions)
        self.table = table

    def indices(self) -> Iterator[int]:
        return iter(range(self.table.num_rows))

    def data(self, row_idx: int) -> List[str]:
        anno_idx = ':{:d}'.format(row_idx)
        if anno_idx not in self.table._annotations:
            self.table._annotations[anno_idx] = []

        return {
            'row': [ col[row_idx] for col in self.table.relation ],
            'annotations': self.table._annotations[anno_idx],
        }

    def where(self, *conditions: Callable[[TableRow], bool]) -> 'TableRowSet':
        return TableRowSet(self.table, *self.conditions, *conditions)
