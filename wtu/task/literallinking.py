from abc import ABCMeta, abstractmethod
from collections import defaultdict
import io, csv
import Levenshtein
import re
import string

from wtu.task import Task
from wtu.table import Table

# utility functions

# remove any punctuation characters rom the input string
#
# >>> print(string.punctuation)
# !"#$%&'()*+,-./:;<=>?@[\]^_`{|}~
def string_remove_punctuation(the_string):
    return the_string.translate(str.maketrans('', '', string.punctuation))

# remove parentheses and their contents
def string_remove_parens(the_string):
    return re.sub(r'\([^)]*\)', '', the_string)

# Levenshtein similarity. Between 0 and 1
# 0: completely differnt
# 1: identical
def metric_levenshtein_similarity(str_a, str_b):
    edit_distance = Levenshtein.distance(str_a, str_b)
    max_len = max(len(str_a), len(str_b))
    return 1 - edit_distance/max_len

# difference between two numbers. Between 0 and 1
# 0: completely different
# 1: identical
def metric_weighted_difference(num_a, num_b):
    if num_a == num_b:
        return 1.0
    elif num_a != 0 and num_b != 0:
        high, low = max(num_a, num_b), min(num_a, num_b)
        return 1 - abs((high-low)/high)
    else:
        return 0.0

class LiteralLinking(Task):
    backends_available = {}

    @classmethod
    def register_backend(cls, name, backend):
        cls.backends_available[name] = backend

    def __init__(self, backend):
        # instantiate backend
        backend_name, backend_args = backend
        self.backend = LiteralLinking.backends_available[backend_name](**backend_args)

        # string transformations and metrics
        self.string_transformations = {
            'string_to_lowercase': lambda s: s.lower(),
            'string_remove_punctuation': string_remove_punctuation,
            'string_remove_parens': string_remove_parens,
        }
        self.string_metrics = {
            'levenshtein': metric_levenshtein_similarity,
        }
        self.string_transformation_seqs = [
            [], # identity/"do nothing"
            ['string_to_lowercase'],
            ['string_to_lowercase', 'string_remove_punctuation'],
            ['string_to_lowercase', 'string_remove_parens', 'string_remove_punctuation'],
        ]
        self.string_metric_cutoff_below = .5

        # date transformations
        self.date_transformations = {
            'date_normal': '{:04d}-{:02d}-{:02d}',
            'date_nozero': '{:d}-{:d}-{:d}',
        }

        # numeric metrics
        self.numeric_metrics = {
            'weighted_difference': metric_weighted_difference,
        }
        self.numeric_metric_cutoff_below = .5

    def match_numeric(self, property_value, number):
        try:
            property_value = float(property_value)
        except ValueError:
            return []

        metric_scores = {
            metric_name: metric(property_value, number)
            for metric_name, metric in self.numeric_metrics.items()
        }

        # only include transformations whose metric scores are above the threshold
        if any(map(lambda s: s >= self.numeric_metric_cutoff_below, metric_scores.values())):
            return [ (None, metric_scores) ]
        else:
            return []

    def match_value_unit(self, property_value, value, value_normalized):
        try:
            property_value = float(property_value)
        except ValueError:
            return []

        metric_scores = {
            metric_name: metric(property_value, value)
            for metric_name, metric in self.numeric_metrics.items()
        }
        transformations = []
        # only include transformations whose metric scores are above the threshold
        if any(map(lambda s: s >= self.numeric_metric_cutoff_below, metric_scores.values())):
            transformations = [ (None, metric_scores) ]

        # also try the normalized value
        if value_normalized != value:
            metric_scores = {
                metric_name: metric(property_value, value_normalized)
                for metric_name, metric in self.numeric_metrics.items()
            }
            if any(map(lambda s: s >= self.numeric_metric_cutoff_below, metric_scores.values())):
                transformations.append(
                    ('value_normalized', metric_scores)
                )

        return transformations

    def match_date(self, property_value, date_parts):
        transformations = []

        # subsequently convert the date to each of the patterns in 'self.date_transformations'
        # and compare the formatted date against the index value
        for transformation_name, transformation_pattern in self.date_transformations.items():
            transformed_date = transformation_pattern.format(
                date_parts['year'],
                date_parts['month'],
                date_parts['day_of_month']
            )
            if transformed_date == property_value:
                transformations.append((transformation_name, None))

        return transformations

    def match_string(self, property_value, cell_content):
        transformations = []
        previous_min_score = 0

        # try all transformation sequences
        for transformation_seq in self.string_transformation_seqs:
            transformed_cell_content = cell_content
            # apply all transformations in the transformation sequence
            for transformation_name in transformation_seq:
                transformation = self.string_transformations[transformation_name]
                transformed_cell_content = transformation(transformed_cell_content)

            # calculate metrics for the transformed string
            metric_scores = {
                metric_name: metric(property_value, transformed_cell_content)
                for metric_name, metric in self.string_metrics.items()
            }

            # if any of the metric's scores is above 'string_metric_cutoff_below' and also higher
            # than the minimal score from the previous transformation, add the transformation and
            # metric scores to the list of matching transformations
            if any(map(lambda s: s >= self.string_metric_cutoff_below and s > previous_min_score, metric_scores.values())):
                transformations.append((transformation_seq, metric_scores))
                previous_min_score = min(metric_scores.values())

        return transformations

    def match_properties(self, cell, properties):
        matching_properties = defaultdict(list)

        # iterate over all properties
        for property_uri, property_type, property_value in properties:
            for anno_idx, anno in enumerate(cell.annotations):
                # iterate over the cell's LiteralNormalization annotations (if it has any)
                # and use the normalized cell value for comparisons against the index
                if anno['task'] == 'LiteralNormalization':
                    ln_anno_idx = '{:d}:{:d}/{:d}'.format(*cell.idx, anno_idx)
                    ln_type = anno['type']
                    transformations = []

                    # distinguish between the different kinds of LiteralNormalization annotations
                    # and collect their transformations/metric scores

                    if ln_type == 'date':
                        date_parts = {
                            k: anno[k]
                            for k in ['year', 'month', 'day_of_month']
                        }
                        transformations = self.match_date(property_value, date_parts)

                    elif ln_type == 'numeric':
                        transformations = self.match_numeric(property_value, anno['number'])

                    elif ln_type == 'value and unit':
                        transformations = self.match_value_unit(property_value, anno['value'], anno['value_normalized'])

                    if transformations:
                        matching_properties[property_uri].append({
                            'references_ln': ln_anno_idx,
                            'transformations': transformations,
                            'index_value': property_value,
                        })

            # always do string comparison regardless of the existence of
            # any LiteralNormalization annotations
            string_transformations = self.match_string(property_value, cell.content)
            if string_transformations:
                matching_properties[property_uri].append({
                    'references_ln': None,
                    'transformations': string_transformations,
                    'index_value': property_value,
                })

        return matching_properties

    def run(self, table):
        # iterate over all rows
        for row in table.rows():
            # find all 'entity' cell in the current row
            el_cells = []
            for cell in row:
                el_annos = cell.find_annotations(anno_source='preprocessing', anno_task='EntityLinking')
                if el_annos:
                    el_cells.append((cell, el_annos))

            # iterate over all 'entity' cells
            for el_cell, el_annos in el_cells:
                # iterate over all EL annotations of this cell
                for el_anno_idx, el_anno in enumerate(el_annos):
                    # query the backend for the set of this entitie's properties,
                    # skip this entity if there are none
                    properties = self.backend.query(el_anno['resource_uri'])
                    if not properties:
                        continue

                    # iterate over all other cells in this row
                    # i.e. not the one containing the entity
                    for other_cell in row:
                        if other_cell.idx == el_cell.idx:
                            continue

                        # try to match the cell's content with one of
                        # the entity's properties
                        matching_properties = self.match_properties(other_cell, properties);
                        for property_uri, match_infos in matching_properties.items():
                            property_uri = 'http://dbpedia.org/ontology/' + property_uri.split(':')[-1]
                            for match_info in match_infos:
                                other_cell.annotations.append({
                                    'source': 'preprocessing',
                                    'task': 'LiteralLinking',
                                    'type': 'property',
                                    'property_uri': property_uri,
                                    'references_el': '{:d}:{:d}/{:d}'.format(*el_cell.idx, el_anno_idx),
                                    **match_info
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
