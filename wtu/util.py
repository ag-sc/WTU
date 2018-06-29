class URI:
    prefix = {
        'dbpedia': 'http://dbpedia.org/page/',
        'dbr': 'http://dbpedia.org/resource/',
        'dbo': 'http://dbpedia.org/ontology/',
        'rdfs': 'http://www.w3.org/2000/01/rdf-schema#',
        'xsd': 'http://www.w3.org/2001/XMLSchema#',
        'dt': 'http://dbpedia.org/datatype/',
    }

    def __init__(self, prefix, suffix):
        if prefix in URI.prefix:
            self.prefix = prefix
        else:
            raise Exception('Unknown prefix "{:s}"!'.format(prefix))

        self.suffix = suffix

    @classmethod
    def parse(cls, uri, fallback_prefix=None):
        if uri.startswith('http://'):
            for prefix_short, prefix_long in URI.prefix.items():
                if uri.startswith(prefix_long):
                    suffix = uri.replace(prefix_long, '')
                    return URI(prefix_short, suffix)
            else:
                raise Exception('Unknown prefix in "{:s}"!'.format(uri))
        else:
            if ':' in uri:
                prefix, suffix = uri.split(':', 1)
                if prefix in URI.prefix:
                    return URI(prefix, suffix)

            if fallback_prefix is None:
                raise Exception('Ambiguous URI "{:s}"!'.format(uri))
            else:
                return URI(fallback_prefix, uri)

    def __str__(self):
        return self.short()

    def short(self):
        return '{:s}:{:s}'.format(self.prefix, self.suffix)

    def long(self):
        return '{:s}{:s}'.format(
            URI.prefix[self.prefix], self.suffix
        )
