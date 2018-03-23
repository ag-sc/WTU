# WTU

WTU - Web Table Understanding

## Synopsis

*(You may need to configure your environment first, according to
[Requirements](#requirements))*

Run example (read input from `STDIN`, write output to `STDOUT`):

	$ ./wtu.py config/example.conf < data/example/in/us_presidents.json

or (read all files in `data/example/in`, write output to new files in
`data/example/out`):

	$ ./process_dir config/example.conf data/example/in data/example/out

## Requirements

* python 3.6+
* python `virtualenv`
* python modules listed in `requirements.txt`

### `virtualenv`

Setup `virtualenv`, activate and install python modules:

	$ python -m venv venv                     # setup virtualenv
	$ source ./venv/bin/activate              # enter virtualenv
    (venv) $ pip install -r requirements.txt  # install required modules

The `nltk.corpus.stopwords` module may need to additional corpora files to work:

	(venv) $ python
	>>> import nltk
	>>> nltk.download('stopwords')

Now your environment is setup to run the code. To leave the `virtualenv` type

	(venv) $ deactivate

# `wtu.py`

`wtu.py` is the main script. It reads table data formatted as JSON from `STDIN`,
runs a series of configurable tasks on each table (each adding their own
annotations/hypotheses about the table's contents) and outputs the now annotated
table data to `STDOUT`.

## Data structure

### Tables

Each input table is represented by a single line of JSON, consisting of a
dictionary with (at least) one key `relation` holding the table's cell contents
as a list of lists (list of columns):

**Example:** *(single line of JSON broken into multiple lines for better
readability)*

This JSON...

```json
{
	"relation": [
		[ "foo", "1", "2", "3" ],
		[ "bar", "one", "two", "three" ],
		[ "baz", "alpha", "bravo", "charlie" ]
	]
}
```

...represents this table

| foo |  bar  |   baz   |
|-----|-------|---------|
|  1  |  one  |  alpha  |
|  2  |  two  |  bravo  |
|  3  | three | charlie |

### Annotations

Annotations are added on cell-, column-, row- or table-level and stored in the
`annotations` field.

**Example:** *(single line of JSON broken into multiple lines for better
readability)*

This JSON...

```json
{
	"relation": [
		[ "foo", "1", "2", "3" ],
		[ "bar", "one", "two", "three" ],
		[ "baz", "alpha", "bravo", "charlie" ]
	],
	"annotations": {
		"0:1": [
			{
				"source": "LiteralNormalization",
				"type": "numeric",
				"number": 1
			}
		],
		"2:3": [
			{
				"source": "EntityLinking",
				"uri": "http://dbpedia.org/resource/Charlie_(band)",
				"frequency": 1
			}
		]
	}
}
```

...annotates the cell in the first column, second row (index `0:1`) with a
`LiteralNormalization` hypothesis and the cell in the third column, fourth row
(index `2:3`) with a `EntityLinking` hypothesis.

column-, row- and table-level annotations are stored the same way with the keys
`n:` (`n`-th column), `:m` (`m`-th row) and `:` (whole table) respectively.

### Configuration

Which tasks are run with an invocation of `wtu.py` is determined by a
configuration file that is passed as the first command line argument to
`wtu.py`.

**Example:**

	$ ./wtu.py config/example.conf < some_input_data.json

contents of `config/example.conf`:

```json
{
	"tasks": [
		["LanguageDetection", {
			"top_n": 3
		}],
		["LiteralNormalization"],
		["EntityLinking", {
			"backend": ["csv", {
				"index_file": "index/entity_linking/example.csv"
			}],
			"top_n": 3
		}]
	]
}
```

This configuration schedules three tasks to be run on each input table from
`some_input_data.json`: `LanguageDetection`, `LiteralNormalization` and
`EntityLinking`. Each task can be parameterized. For example `LanguageDetection`
and `EntityLinking` both receive a parameter `top_n` specifying the maximum
number of results they should return (number of annotations). In addition to
this, `EntityLinking` is also configured to use the `csv` backend, which in turn
is configured to load its index from `index/entity_linking/example.csv`.

# `process_dir`

`process_dir` is a wrapper around `wtu.py` that makes it easier to process whole
directories of input data and save the results to disk.

**Example:**

	$ ./process_dir config/example.conf data/example/in data/example/out

reads all files from `data/example/in`, runs an instance of `wtu.py` on each of
them (configured via `config/example.conf`) and writes the (`gzip`ed) output to
new files in `data/example/out`.

## Input formats

`process_dir` supports the following input file formats:

* `*.json`

  plain JSON files, each containing one ore more tables (e.g. the example file
	`data/example/in/us_presidents.json`)
* `*.json.gz`

  `gzip`ed JSON files (e.g. `process_dir`'s own output files)
* `*.tar.gz`

  `gzip`ed JSON files in a `gzip`ed `tar` archive (e.g. the files in the
	[WDC Web Table Corpus](http://webdatacommons.org/webtables/2015/downloadInstructions.html))

other files are ignored.
