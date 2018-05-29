
import io, sys, json
from json.decoder import JSONDecodeError

from wtu.table import Table

total_amount_columns = 0
total_same_uri = 0
total_other_uri = 0
total_no_gold_uri = 0
total_no_LL_annos = 0
table_no = 1


# returns the most frequent URI of all cells in the column (empty str if no URIs in any cells in the column)
def naiveMaximum(column) -> str:

    # find all LiteralLinking-annotations in our column for each cell
    pl_annotations = []
    for cell in column:
        for elem in cell.find_annotations(anno_task='LiteralLinking'):
            pl_annotations.append(elem)

    # collect all property-uris from all the LiteralLinking-annotations
    property_uris = []
    for annotation in pl_annotations:
        uri = annotation['property_uri']
        property_uris.append(uri)

    # find out which uri does occur most in all the property_uris
    counter = {}
    for uri in property_uris:
        if (uri in counter):
            counter[uri] = (counter.get(uri)) + 1
        else:
            counter[uri] = 1

    sorted_uris = (sorted(counter.items(), key=lambda x: x[1]))[::-1] # uri with highest value first
    print('list of our uris: ' + str(sorted_uris))

    try:
        most_freq_uri = max(counter, key=counter.get)  # the uri with the highest value
        print('most_freq_uri: ' + most_freq_uri)
    except:
        most_freq_uri = ''  # it means: counter was empty <= property_uris was empty <= we did not have any LL-annos in any of the cells
        print("column has gold-uri, but we don't have any LL-annotations for any cell in this column.")

    return most_freq_uri



# read from stdin, ignore encoding errors
with io.open(sys.stdin.fileno(), 'r', encoding='utf-8', errors='ignore') as stdin:

    # iterate over input. Each line represents one table
    for json_line in stdin:
        try:
            # parse json
            table_data = json.loads(json_line)
            # create Table object to work with
            table = Table(table_data)

            table_amount_columns = 0
            column_same_uri = 0
            column_other_uri = 0
            column_has_no_gold_uri = 0
            column_has_no_LL_anno = 0

            print('-------------------------------------------------------------------------\n')
            print('TABLE BEGIN - Table '+ str(table_no) + '   total rows: '+str(table.num_rows)+ '   total cols: '+str(table.num_cols) +'\n')

            for column in table.columns():

                print('\n COLUMN BEGIN - Col '+ str(column.col_idx))
                table_amount_columns += 1
                total_amount_columns += 1

                # get the gold-property-annotation of the current column
                gold_uri=''
                for annotation in column.annotations:
                    if (annotation['task']=='PropertyLinking' and annotation['source']=='gold-v2'):
                        gold_uri = annotation['property_uri']


                print('gold_uri: ' + gold_uri)

                # if no gold_uri was found, move to the next column
                if(gold_uri == ''):
                    column_has_no_gold_uri += 1
                    total_no_gold_uri+=1
                    print('No gold-uri to compare with.')
                    continue

                most_freq_uri = naiveMaximum(column)

                # insert an annotation with that most frequent uri to the current column
                if(most_freq_uri != ''): column.annotations.append({'source': 'evaluation', 'task': 'PropertyLinking', 'property_uri': most_freq_uri})

                # compare the gold-annotation-uri to our most_freq_uri
                if(most_freq_uri == gold_uri):
                    total_same_uri+=1
                    column_same_uri+=1
                elif(most_freq_uri == ''):
                    #column has gold-uri, but we don't have any LL-annotations for any cell in this column
                    total_no_LL_annos+=1
                    column_has_no_LL_anno+=1
                else:
                    total_other_uri+=1
                    column_other_uri+=1


            print('\nTABLE END - Table '+ str(table_no) + '\n')
            table_no+=1




        # ignore json decoding errors
        except JSONDecodeError: pass

        print(
            '-----',
            'column_same_uri = ' + str(column_same_uri) + '/' + str(table_amount_columns),
            'column_other_uri = ' + str(column_other_uri) + '/' + str(table_amount_columns),
            'column_has_no_gold_uri = ' + str(column_has_no_gold_uri) + '/' + str(table_amount_columns),
            'column_has_no_LL_anno = ' + str(column_has_no_LL_anno) + '/' + str(table_amount_columns),
            '-----',
            sep='\n'
        )


    print(
        '',
        '-------------------------------------------------------------------------',
        '-------------------------------------------------------------------------',
        'total_same_uri = ' + str(total_same_uri) + '/' + str(total_amount_columns),
        'total_other_uri = ' + str(total_other_uri) + '/' + str(total_amount_columns),
        'total_no_gold_uri = ' + str(total_no_gold_uri) + '/' + str(total_amount_columns),
        'total_no_LL_annos = ' + str(total_no_LL_annos) + '/' + str(total_amount_columns),
        '-------------------------------------------------------------------------',
        '-------------------------------------------------------------------------',
        sep='\n'
    )





