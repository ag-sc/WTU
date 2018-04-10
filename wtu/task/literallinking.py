from abc import ABCMeta, abstractmethod
from collections import defaultdict
import io, csv
from operator import attrgetter

from wtu.task import Task
from wtu.table import Table

class LiteralLinking(Task):
    backends_available = {}

    @classmethod
    def register_backend(cls, name, backend):
        cls.backends_available[name] = backend

    def __init__(self, backend):
        # instantiate backend
        backend_name, backend_args = backend
        self.backend = LiteralLinking.backends_available[backend_name](**backend_args)

    def match_literal(self, ln_anno, properties):
        anno_type = ln_anno['type']
        matching_properties = []

        if anno_type == 'numeric':
            for property_uri, literal_type, literal_value in properties:
                try:
                    literal_value = float(literal_value)
                    if ln_anno['number'] == literal_value:
                        pass
                except ValueError:
                    pass

        elif anno_type == 'date':
            normalized_date = '{:d}-{:02d}-{:02d}'.format(
                ln_anno['year'], ln_anno['month'], ln_anno['day_of_month']
            )

            for property_uri, literal_type, literal_value in properties:
                if normalized_date == literal_value:
                    matching_properties.append(property_uri)

        elif anno_type == 'value and unit':
            for property_uri, literal_type, literal_value in properties:
                try:
                    literal_value = float(literal_value)
                    if ln_anno['value_normalized'] == literal_value:
                        matching_properties.append(property_uri)
                except ValueError:
                    pass

        return matching_properties

    def run(self, table):
        # iterate over all rows
        for row in table.rows():
            el_cells = []  # holds cells with EntityLinking annotations
            ln_cells = []  # holds cells with LiteralNormalization annotations

            # iterate ovell cell in row
            for cell in row:
                # if the cell has EntityLinking annotations add it to el_cells
                el_annos = cell.find_annotations(anno_source='EntityLinking')
                if el_annos:
                    el_cells.append((cell, el_annos))
                    continue # skip looking for LiteralNormalization annotations

                # if the cell has LiteralNormalization add it to ln_cells
                ln_annos = cell.find_annotations(anno_source='LiteralNormalization')
                if ln_annos:
                    ln_cells.append((cell, ln_annos))

            # proceed if the row has both cell with EL annotations and LN annotations
            if el_cells and ln_cells:
                for el_cell, el_annos in el_cells:
                    for el_anno_idx, el_anno in enumerate(el_annos):
                        properties = self.backend.query(el_anno['uri'])
                        for ln_cell, ln_annos in ln_cells:
                            for ln_anno_idx, ln_anno in enumerate(ln_annos):
                                for matching_property in self.match_literal(ln_anno, properties):
                                    ln_cell.annotations.append({
                                        'source': 'LiteralLinking',
                                        'type': 'property',
                                        'uri': matching_property,
                                        'references': {
                                            'EL': '{:d}:{:d}/{:d}'.format(*el_cell.idx, el_anno_idx),
                                            'LN': '{:d}:{:d}/{:d}'.format(*ln_cell.idx, ln_anno_idx),
                                        },
                                    })

        return True

class LiteralLinkingBackend(metaclass=ABCMeta):
    @abstractmethod
    def query(self, entity_uri):
        pass

class LiteralLinkingBackendCSV(LiteralLinkingBackend):
    def __init__(self, index_file, delimiter='\t', quotechar=None):
        # index dictionary
        self.index = defaultdict(list)

        # read complete `index_file` into the index dictionary
        with io.open(index_file, 'r', encoding='utf-8', errors='ignore') as index_fh:
            csv_reader = csv.reader(index_fh, delimiter=delimiter, quotechar=quotechar)
            for row in csv_reader:
                entity_uri, property_uri, literal_type, literal_value = row
                self.index[entity_uri].append((property_uri, literal_type, literal_value))

    def query(self, entity_uri):
        res = []
        try:
            res = self.index[entity_uri]
        except KeyError:
            pass

        return res

LiteralLinking.register_backend('csv', LiteralLinkingBackendCSV)
