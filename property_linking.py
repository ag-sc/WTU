
import io, sys, json
from json.decoder import JSONDecodeError

from wtu.table import Table

total_amount_columns = 0
total_same_uri = 0
total_other_uri_NOT_IN_list = 0
total_other_uri_IN_list = 0
total_no_gold_uri = 0
total_no_LL_annos = 0
total_gold_uri_not_valid = 0
table_no = 0






def naiveMaximumCountMissingLLAnnos(column) -> (str, dict):
    '''

    :param column:
    :return:
    '''

    # find all LiteralLinking-annotations in our column for each cell, also find if no LL exists
    pl_annotations = []
    for cell in column:
        cellAnnotations = cell.find_annotations(anno_source='preprocessing', anno_task='LiteralLinking')
        if cellAnnotations:
            pl_annotations.extend(cellAnnotations)
        else:
            pl_annotations.append('noLLAnno') # no LL

    # collect all property-uris from all the LiteralLinking-annotations
    property_uris = []
    for annotation in pl_annotations:
        if(annotation == 'noLLAnno'):
            property_uris.append('noLLAnno')
        else:
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

    most_freq_uri = max(counter, key=counter.get)  # the uri with the highest value
    print('most_freq_uri: ' + most_freq_uri)

    return (most_freq_uri, counter)








# returns:
# str: the most frequent URI of all cells in the column (empty str if no URIs in any cells in the column),
# dict: key: all URIs we made in this column, value: amount of their occurrence
def naiveMaximum(column) -> (str, dict):

    # find all LiteralLinking-annotations in our column for each cell
    pl_annotations = []
    for cell in column:
        pl_annotations.extend(cell.find_annotations(anno_source='preprocessing', anno_task='LiteralLinking'))

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

    return (most_freq_uri, counter)




# read from stdin, ignore encoding errors
with io.open(sys.stdin.fileno(), 'r', encoding='utf-8', errors='ignore') as stdin:

    # read the URIs and save in list. only if the gold URI is a URI from the list, then compare to our found annotation/URI.
    with open('properties_to_consider.txt') as f:
        uris_from_file = f.readlines()
    uris_from_file = [uri.strip('\n') for uri in uris_from_file]

    # iterate over input. Each line represents one table
    for json_line in stdin:
        try:
            # parse json
            table_data = json.loads(json_line)
            # create Table object to work with
            table = Table(table_data)

            table_amount_columns = 0
            column_same_uri = 0
            column_other_uri_NOT_IN_list = 0
            column_other_uri_IN_list = 0
            column_has_no_gold_uri = 0
            column_has_no_LL_anno = 0
            column_gold_uri_not_valid = 0

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

                # if the gold_uri is not in the list of valid uris, move to the next column
                if(gold_uri not in uris_from_file):
                    column_gold_uri_not_valid += 1
                    total_gold_uri_not_valid +=1
                    print('Gold-uri is not valid.')
                    continue


                myTuple = naiveMaximumCountMissingLLAnnos(column) # or: naiveMaximum(column)
                most_freq_uri = myTuple[0]
                ourURIs = myTuple[1]

                # for future: insert an annotation with that most frequent uri to the current column
                # if(most_freq_uri != ''): column.annotations.append({'source': 'evaluation', 'task': 'PropertyLinking', 'property_uri': most_freq_uri})


                # compare the gold-annotation-uri to our most_freq_uri
                if(most_freq_uri == gold_uri):
                    total_same_uri+=1
                    column_same_uri+=1
                elif(most_freq_uri == ''):
                    #column has gold-uri, but we don't have any LL-annotations for any cell in this column
                    total_no_LL_annos+=1
                    column_has_no_LL_anno+=1
                elif(most_freq_uri == 'noLLAnno'):
                    # column has gold-uri, and our most frequent uri was that we don't have a uri
                    total_no_LL_annos += 1
                    column_has_no_LL_anno += 1
                else:
                    if (gold_uri in ourURIs.keys()):
                        print('We also have annotated some of our cells in this column with that gold-uri. But its not the most frequent one.')
                        print('It occurred only '+ str(ourURIs[gold_uri]) + '/'+ str(sum(ourURIs.values())) + ' times in our annotations.' )
                        total_other_uri_IN_list+=1
                        column_other_uri_IN_list+=1
                    else:
                        print('The gold URI is not even within any of our cell-annotations in this column.')
                        total_other_uri_NOT_IN_list+=1
                        column_other_uri_NOT_IN_list+=1


            print('\nTABLE END - Table '+ str(table_no) + '\n')
            table_no+=1




        # ignore json decoding errors
        except JSONDecodeError: pass

        print(
            '-----',
            'column_same_uri = ' + str(column_same_uri) + '/' + str(table_amount_columns),
            'column_other_uri_NOT_IN_list = ' + str(column_other_uri_NOT_IN_list) + '/' + str(table_amount_columns),
            'column_other_uri_IN_list = ' + str(column_other_uri_IN_list) + '/' + str(table_amount_columns),
            'column_has_no_gold_uri = ' + str(column_has_no_gold_uri) + '/' + str(table_amount_columns),
            'column_has_no_LL_anno = ' + str(column_has_no_LL_anno) + '/' + str(table_amount_columns),
            'column_gold_uri_not_valid = ' + str(column_gold_uri_not_valid) + '/' + str(table_amount_columns),
            '-----',
            sep='\n'
        )


    print(
        '',
        '-------------------------------------------------------------------------',
        '-------------------------------------------------------------------------',
        'total_no_gold_uri = ' + str(total_no_gold_uri) + '/' + str(total_amount_columns),
        'total_gold_uri_not_valid = ' + str(total_gold_uri_not_valid) + '/' + str(total_amount_columns),
        'rest = '+ str( total_amount_columns - total_no_gold_uri - total_gold_uri_not_valid )+ '/' + str(total_amount_columns),
        '-----------------------------------------------',
        'total_same_uri = ' + str(total_same_uri) + '/' + str(total_amount_columns - total_no_gold_uri - total_gold_uri_not_valid),
        'total_other_uri_NOT_IN_list = ' + str(total_other_uri_NOT_IN_list) + '/' + str(total_amount_columns - total_no_gold_uri - total_gold_uri_not_valid),
        'total_other_uri_IN_list = ' + str(total_other_uri_IN_list) + '/' + str(total_amount_columns - total_no_gold_uri - total_gold_uri_not_valid),
        'total_no_LL_annos = ' + str(total_no_LL_annos) + '/' + str(total_amount_columns - total_no_gold_uri - total_gold_uri_not_valid),

        '-------------------------------------------------------------------------',
        '-------------------------------------------------------------------------',
        sep='\n'
    )





