from abc import ABCMeta, abstractmethod
from collections import defaultdict
import io, csv
from operator import itemgetter
import Levenshtein

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
        self.numeric_diff_cutoff = 200
        self.string_edit_distance_cutoff = 50

    def match_numeric(self, literal_value, ln_number):
        try:
            literal_value = float(literal_value)
        except ValueError:
            return []

        if literal_value == ln_number:
            return ['numeric_exact']

        if literal_value != 0 and ln_number != 0:
            high, low = max(literal_value, ln_number), min(literal_value, ln_number)
            diff_percent = abs((high-low)/low*100)

            if diff_percent <= self.numeric_diff_cutoff:
                return ['numeric_diff={:.2f}%'.format(diff_percent)]

        return []

    def match_value_and_unit(self, literal_value, value, value_normalized):
        return [
            *self.match_numeric(literal_value, value),
            *['normalized_' + transf for transf in self.match_numeric(literal_value, value_normalized)]
        ]

    def match_date(self, literal_value, date_parts):
        # normalized the LN annotation's date to these formats
        # for comparison
        format_strings = {
            'date_normal': '{:04d}-{:02d}-{:02d}',
            'date_nozero': '{:d}-{:d}-{:d}',
        }

        matching_formats = []
        # iterate over all formats and try to match the literal_value
        # keep a record of all matching formats
        for format_name, format_string in format_strings.items():
            date_formatted = format_string.format(*date_parts)
            if date_formatted == literal_value:
                matching_formats.append(format_name)

        return matching_formats

    def match_string(self, literal_value, cell_content):
        if literal_value == cell_content:
            return ['string_exact']

        if literal_value.lower() == cell_content.lower():
            return ['string_ignore_case']

        edit_distance = Levenshtein.distance(
            literal_value.lower(),
            cell_content.lower()
        )
        max_str_len = max(len(literal_value), len(cell_content))
        edit_distance_percent = edit_distance*100/max_str_len

        if edit_distance_percent <= self.string_edit_distance_cutoff:
            return ['string_edit_distance={:.2f}%'.format(edit_distance_percent)]

    def match_properties(self, cell, properties):
        # find all LN annotations of the current cell
        ln_annos = cell.find_annotations(anno_source='LiteralNormalization')

        matching_properties = defaultdict(lambda : { 'index_value': None, 'transforms': [] })
        # iterate over all properties
        for property_uri, literal_type, literal_value in properties:
            # iterate over all LN annotations the cell might have
            # and try to match the 'normalized' versions of the cell's
            # content to a propertie's literal_value
            for ln_anno in ln_annos:
                ln_type = ln_anno['type']

                if ln_type == 'numeric':
                    matching_numeric = self.match_numeric(literal_value, ln_anno['number'])
                    if matching_numeric:
                        matching_properties[property_uri]['transforms'].extend(matching_numeric)
                        matching_properties[property_uri]['index_value'] = literal_value
                elif ln_type == 'value and unit':
                    matching_value_and_unit = self.match_value_and_unit(literal_value, ln_anno['value'], ln_anno['value_normalized'])
                    if matching_value_and_unit:
                        matching_properties[property_uri]['transforms'].extend(matching_value_and_unit)
                        matching_properties[property_uri]['index_value'] = literal_value
                elif ln_type == 'date':
                    matching_date_formats = self.match_date(literal_value, [
                        ln_anno[part] for part in [
                            'year', 'month', 'day_of_month'
                        ]]
                    )
                    if matching_date_formats:
                        matching_properties[property_uri]['transforms'].extend(matching_date_formats)
                        matching_properties[property_uri]['index_value'] = literal_value

            # just compare the cell's content as it is
            matching_string = self.match_string(literal_value, cell.content)
            if matching_string:
                matching_properties[property_uri]['transforms'].extend(matching_string)
                matching_properties[property_uri]['index_value'] = literal_value

        return matching_properties

    def run(self, table):
        # iterate over all rows
        for row in table.rows():
            # find all 'entity' cell in the current row
            el_cells = []
            for cell in row:
                el_annos = cell.find_annotations(anno_source='EntityLinking')
                if el_annos:
                    el_cells.append((cell, el_annos))

            # iterate over all 'entity' cells
            for el_cell, el_annos in el_cells:
                # iterate over all EL annotations of this cell
                for el_anno_idx, el_anno in enumerate(el_annos):
                    # query the backend for the set of this entitie's properties,
                    # skip this entity if there are none
                    properties = self.backend.query(el_anno['uri'])
                    if not properties:
                        continue

                    # iterate over all other cells in this row
                    # i.e. not the one containing the entity
                    for other_cell in row:
                        if other_cell.idx == el_cell.idx:
                            continue

                        # try to match the cell's content with one of
                        # the entity's properties
                        matching_properties = self.match_properties(other_cell, properties)
                        for matching_property, property_info in matching_properties.items():
                            other_cell.annotations.append({
                                'source': 'LiteralLinking',
                                'type': 'property',
                                'uri': matching_property,
                                'references_EL': '{:d}:{:d}/{:d}'.format(*el_cell.idx, el_anno_idx),
                                'transforms': property_info['transforms'],
                                'index_value': property_info['index_value'],
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
