from wtu.task import Task
from wtu.table import Table

from nltk import wordpunct_tokenize
from nltk.corpus import stopwords

from operator import attrgetter, itemgetter

class LanguageDetection(Task):
    def __init__(self, top_n=3, additional_fields=[]):
        self.top_n = top_n
        self.additional_fields = additional_fields

    def run(self, table):
        # concatenate all cell's contents
        cell_content = ' '.join(
            map(
                attrgetter('content'),
                table.cells()
            )
        )
        input_string = cell_content
        # add text from additional fields
        for field_name in self.additional_fields:
            if field_name in table.table_data:
                input_string += table.table_data[field_name]

        # tokenize string and extract lower case words
        tokens = wordpunct_tokenize(input_string)
        words = [word.lower() for word in tokens]

        # iterate over all languages in nltk and match their stopwords
        # to the words in our input string.
        # larger intersection -> higher score
        languages_ratios = {}
        for language in stopwords.fileids():
            # the language's stopwords
            stopwords_set = set(stopwords.words(language))
            # our words
            words_set = set(words)
            # intersection between the sets
            common_elements = len(words_set.intersection(stopwords_set))
            if common_elements > 0:
                languages_ratios[language] = common_elements

        # get top <n> languages
        top_n_languages = sorted(
            languages_ratios.items(),
            key=itemgetter(1),
            reverse=True
        )[:self.top_n]

        # sum all language scores to normalize the individual scores
        language_score_sum = sum(
            map(itemgetter(1), top_n_languages)
        )

        # add annotations for each identified language
        for language in top_n_languages:
            language_name, language_score = language
            normalized_score = language_score/language_score_sum

            table.annotations.append({
                'source': 'LanguageDetection',
                'language': language_name,
                'score': normalized_score,
            })
