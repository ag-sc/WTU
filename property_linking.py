
import io, sys, json
from json.decoder import JSONDecodeError
from wtu.table import Table

total_amount_columns = 0
same_uri_null = 0 # same property-uri occured in gold-v2 AND in our naive way to do property linking
same_uri = 0 #amount of: same property-uri occured in gold-v2 AND in our naive way to do property linking
other_uri = 0

# read from stdin, ignore encoding errors
with io.open(sys.stdin.fileno(), 'r', encoding='utf-8', errors='ignore') as stdin:
    # iterate over input. Each line represents one table
    for json_line in stdin:
        try:
            # parse json
            table_data = json.loads(json_line)
            # create Table object to work with
            table = Table(table_data)

            for column in table.columns():



                # find all LiteralLinking-annotations for each cell
                pl_annotations=[]
                for cell in column:
                    for elem in cell.find_annotations(anno_task='LiteralLinking'):
                        pl_annotations.append(elem)

                #collect all property-uris from all the LiteralLinking-annotations
                property_uris = []
                for annotation in pl_annotations:
                    uri = annotation['property_uri']
                    property_uris.append(uri)

                # find out which uri does occur most in all the property_uris
                counter={}
                for uri in property_uris:
                    if (uri in counter):
                        counter[uri] = (counter.get(uri))+1
                    else:
                        counter[uri] = 1
                try:
                    most_freq_uri = max(counter, key=counter.get) #the uri with the highest value
                except:
                    most_freq_uri = ''

                # insert an annotation with that most frequent uri to the current column
                if(most_freq_uri != ''): column.annotations.append({'source': 'evaluation', 'task': 'PropertyLinking', 'property_uri': most_freq_uri})



                # get the gold-property-annotation of the current column
                gold_uri=''
                for annotation in column.annotations:
                    if (annotation['task']=='PropertyLinking' and annotation['source']=='gold-v2'):
                        gold_uri = annotation['property_uri']

                # compare the gold-annotation-uri to our most_freq_uri
                if(most_freq_uri == '' and gold_uri == ''): same_uri_null+=1
                elif(most_freq_uri == gold_uri and most_freq_uri != ''): same_uri+=1
                else: other_uri+=1



                total_amount_columns+=1



        # ignore json decoding errors
        except JSONDecodeError:
            pass


    print(
        '---',
        'total_amount_columns = ' + str(total_amount_columns),
        'same_uri_null = ' + str(same_uri_null),
        'same_uri = ' +str(same_uri),
        'other_uri = ' + str(other_uri),
        sep='\n'
    )