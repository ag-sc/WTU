import re
from wtu.table import Table
from wtu.task import Task

class DateParser:
    month_name = {
        'January':    1,
        'February':   2,
        'March':      3,
        'April':      4,
        'May':        5,
        'June':       6,
        'July':       7,
        'August':     8,
        'September':  9,
        'October':   10,
        'November':  11,
        'December':  12,
        'Jan':        1,
        'Feb':        2,
        'Mar':        3,
        'Apr':        4,
        'May':        5,
        'Jun':        6,
        'Jul':        7,
        'Aug':        8,
        'Sep':        9,
        'Oct':       10,
        'Nov':       11,
        'Dec':       12,
    }
    day_of_month_pattern = '(?P<day_of_month>[12][0-9]|3[01]|0?[1-9])'
    month_pattern = '(?P<month>1[012]|0?[0-9])'
    year_pattern = '(?P<year>[0-9]{4})'

    def __init__(self):
        self.month_name_pattern = (
            '(?P<month_name>' +
            '|'.join(self.month_name.keys())
            + ')'
        )

        self.notations = [
            # 2017-06-08, 2017/06/08...
            {
                'name': 'YYYY-MM-DD',
                'pattern': re.compile(
                    '^' +
                    '[/.-]'.join([
                        self.year_pattern,
                        self.month_pattern,
                        self.day_of_month_pattern
                    ]) +
                    '$'
                ),
            },
            # Jan 1, 2016; December 24 1990
            {
                'name': 'Mon DD, YYYY',
                'pattern': re.compile(
                    '^' +
                    '\s+'.join([
                        self.month_name_pattern,
                        self.day_of_month_pattern + '\s*,?',
                        self.year_pattern
                    ]) +
                    '$'
                ),
            },
            # 19.02.2017, 24/5/1999, ...
            {
                'name': 'DD.MM.YYYY',
                'pattern': re.compile(
                    '^' +
                    '[/.-]'.join([
                        self.day_of_month_pattern,
                        self.month_pattern,
                        self.year_pattern
                    ]) +
                    '$'
                ),
            },
            # 02.19.2017, 5/24/1999, ...
            {
                'name': 'MM.DD.YYYY',
                'pattern': re.compile(
                    '^' +
                    '[/.-]'.join([
                        self.month_pattern,
                        self.day_of_month_pattern,
                        self.year_pattern
                    ]) +
                    '$'
                ),
            },
            # 21. March 2001, 14 Apr 2017, ...
            {
                'name': 'DD. Mon YYYY',
                'pattern': re.compile(
                    '^' +
                    '\s+'.join([
                        self.day_of_month_pattern + '\.?',
                        self.month_name_pattern,
                        self.year_pattern
                    ]) +
                    '$'
                ),
            },
        ]

    def parse(self, string):
        hypos = []
        for notation in self.notations:
            match = notation['pattern'].match(string)
            if match:
                date_parts = match.groupdict()
                if not 'month' in date_parts:
                    if 'month_name' in date_parts:
                        date_parts['month'] = self.month_name[
                            date_parts['month_name']
                        ]
                for key in ['year', 'month', 'day_of_month']:
                    if key in date_parts:
                        date_parts[key] = int(date_parts[key])
                    else:
                        date_parts[key] = None
                hypos.append(date_parts)
        return hypos

class UnitParser:
    def __init__(self):
        self.numeric_parser = NumericParser()

        potential_number_pattern = "[+-]?[0-9., ]*[0-9]+[0-9., ]*"
        # Structure of physical quantities and their corresponding units.
        # Each unit defines a pattern that matches expressions of values
        # in this specific unit as well as a factor to calculate the value
        # expressed in the quantities' base unit.
        self.quantities = {
            "length": {
                "base_unit": "m",
                "units": {
                    "m": {
                        "pattern": re.compile(
                            "^(?P<value>" +
                            potential_number_pattern +
                            ")\s*(?P<unit>m(?:eters?)?)$"
                        ),
                        "factor": 1,
                        "data_type": "dbo:m",
                    },
                    "km": {
                        "pattern": re.compile(
                            "^(?P<value>" +
                            potential_number_pattern +
                            ")\s*(?P<unit>k(?:ilo\s*)?m(?:eters?)?)$"
                        ),
                        "factor": 1e3,
                        "data_type": "dbo:km",
                    },
                    "cm": {
                        "pattern": re.compile(
                            "^(?P<value>" +
                            potential_number_pattern +
                            ")\s*(?P<unit>c(?:enti\s*)?m(?:eters?)?)$"
                        ),
                        "factor": 1e-2,
                        "data_type": "dbo:cm",
                    },
                    # add more units here...
                    # "mm": {...},
                    # "inch": {...},
                    # ...
                },
            },
            "mass": {
                "base_unit": "kg",
                "units": {
                    "kg": {
                        "pattern": re.compile(
                            "^(?P<value>" +
                            potential_number_pattern +
                            ")\s*(?P<unit>k(?:ilo\s*)?g(?:ramm?s?)?)$"
                        ),
                        "factor": 1,
                        "data_type": "dbo:kg",
                    },
                    "t": {
                        "pattern": re.compile(
                            "^(?P<value>" +
                            potential_number_pattern +
                            ")\s*(?P<unit>t(?:onn?s)?)$"
                        ),
                        "factor": 1e3,
                        "data_type": "dbo:t",
                    },
                    "g": {
                        "pattern": re.compile(
                            "^(?P<value>" +
                            potential_number_pattern +
                            ")\s*(?P<unit>g(?:ramm?s?)?)$"
                        ),
                        "factor": 1e-3,
                        "data_type": "dbo:g",
                    },
                },
            },
            # add more physical quantities here...
            # "area": {...},
            # "velocity": {...},
            # ...
        }

    def parse(self, string):
        unit_hypos = []
        for quantity_name, quantity in self.quantities.items():
            for unit_name, unit in quantity["units"].items():
                m = unit["pattern"].match(string)
                if m:
                    values = self.numeric_parser.parse_number(m.group("value"))
                    for value in values:
                        value_normalized = value * unit["factor"]
                        unit_hypos.append({
                            "value": value,
                            "value_normalized": value_normalized,
                            "unit_name": unit_name,
                            "data_type": unit["data_type"],
                            "quantity_name": quantity_name,
                        })
        return unit_hypos

# identify numbers
class NumericParser:
    potential_number_pattern = re.compile('^(?P<number>[+-]?[0-9., ]*[0-9]+[0-9., ]*)$')

    def parse_number(self, string):
        string = string.replace(' ', '')
        commas = [m.start() for m in re.finditer(',', string)]
        dots = [m.start() for m in re.finditer('\.', string)]

        if len(commas) == 0 and len(dots) == 0:
            return [float(string)]

        if len(commas) >= 2 and len(dots) >= 2:
            return []

        if len(commas) >= 2:
            return [float(string.replace(',', ''))]

        if len(dots) >= 2:
            return [float(string.replace('.', '').replace(',', '.'))]

        if len(commas) == 1 and len(dots) == 1:
            if max(commas) > max(dots):
                return [float(string.replace('.', '').replace(',', '.'))]
            else:
                return [float(string.replace(',', ''))]

        return [
            float(string.replace(',', '')),
            float(string.replace('.', '').replace(',', '.'))
        ]

    def parse(self, string):
        potential_number = NumericParser.potential_number_pattern.match(string)
        if potential_number:
            return self.parse_number(potential_number.group('number'))
        else:
            return []

class LiteralNormalization(Task):
    def __init__(self):
        # instantiate parsers
        self.date_parser = DateParser()
        self.unit_parser = UnitParser()
        self.numeric_parser = NumericParser()

    def run(self, table: Table):
        cellset = table.cells()

        if 'headerRowIndex' in table.table_data:
            header_row_index = table.table_data['headerRowIndex']
            if header_row_index != -1:
                cellset = cellset.where(lambda cell: cell.row_idx != header_row_index)

        # iterate over all cells
        for cell in cellset:
            # always add a 'plain' annotation
            cell.annotations.append({
                'source': 'preprocessing',
                'task': 'LiteralNormalization',
                'type': 'plain',
                'string': cell.content,
            })

            # identify values with units
            unit_hypos = self.unit_parser.parse(cell.content)
            if unit_hypos:
                for unit_hypo in unit_hypos:
                    cell.annotations.append({
                        'source': 'preprocessing',
                        'task': 'LiteralNormalization',
                        'type': 'value and unit',
                        **unit_hypo
                    })
                continue

            # identify dates
            date_hypos = self.date_parser.parse(cell.content)
            if date_hypos:
                for date_hypo in date_hypos:
                    cell.annotations.append({
                        'source': 'preprocessing',
                        'task': 'LiteralNormalization',
                        'type': 'date',
                        **date_hypo
                    })
                continue

            # identify numbers
            numbers = self.numeric_parser.parse(cell.content)
            if numbers:
                for number in numbers:
                    cell.annotations.append({
                        'source': 'preprocessing',
                        'task': 'LiteralNormalization',
                        'type': 'numeric',
                        'number': number,
                    })
                continue

        return True
