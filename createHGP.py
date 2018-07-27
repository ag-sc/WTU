
import io, sys, json
from json.decoder import JSONDecodeError
import itertools
import requests

from wtu.table import Table



def send_sparql_request_entities(x:str, y:str)->list:
    '''
    Sends sparql request to DBpedia.
    :param x: uri as string with brackets: <URI>
    :param y: uri as string with brackets: <URI>
    :return: list that includes the formatted triples x,p,y. If no p was found for x,y or error occurred then return empty list
    '''
    try:
        param = {'format': 'text/ntriples', # gives answer in right format: "<Uri1>\t<Uri2>\t<Uri3> .\n" etc.
                 'query': 'construct {' \
                          + x + ' ?p1 ' + y + ' . ' \
                          + y + ' ?p2 ' + x + ' .} \
                          where {{ '\
                          + x + ' ?p1 ' + y + ' .} \
                          UNION { '\
                          + y + ' ?p2 ' + y + ' .}}'}
        response = requests.get('https://dbpedia.org/sparql', params=param)

        if (response.text == '# Empty NT\n'):
            return []
        else:
            response_triples = response.text.splitlines(True)
            # dont return the wikiPageWikiLink relations
            response_triples = [triple for triple in response_triples if 'wikiPageWikiLink' not in triple]
            return response_triples

    except Exception as e:
        print('\n Error in sending/receiving sparql request: \n x = ' + x + '\n y = ' + y + '\n Errormessage: \n' + e + '\n')
        return []



def send_sparql_request_type(x:str)->list:
    '''
    :param x: uri of entity of which you want to have the types in Brackets <URI>
    :return: list with each entry is a ntriple of which the last one is interesting
    '''
    try:
        param = {'format': 'text/csv',
                 'query': 'select * where { ' + x + ' rdf:type ?type . filter(regex(?type, \"dbpedia.org\")) filter(!regex(?type, \"yago\"))}'
                 }
        response = requests.get('https://dbpedia.org/sparql', params=param)


        if (response.text == '\"type\"\n'): return []
        else:
            responseList = response.text.splitlines(True)
            del responseList[0] #delete the first element '"type"\n'
            # delete the first char: " and the last 2 chars: "\n
            responseList = [elem[1:-2] for elem in responseList]
            return responseList

    except Exception as e:
        print('\n  Error while requesting a type from dbpedia: \n entity = '+ x +'\n Error message: \n' + e + '\n')
        return []



# read relevant tables/rows from json file
# {
#    "<table number>": [<row number>, <row number>, ...],
#    ...
# }
relevant_tables = {}
if len(sys.argv) >= 2:
    with io.open(sys.argv[1], 'r') as relevant_tables_fh:
        try:
            relevant_tables = json.load(relevant_tables_fh)
        except:
            print('Failed to read relevant tables file!')

# read from stdin, ignore encoding errors
with io.open(sys.stdin.fileno(), 'r', encoding='utf-8', errors='ignore') as stdin:

    tableNo = 0

    # iterate over input. Each line represents one table
    for json_line in stdin:

                    # skip irrelevant tables
                    if relevant_tables and str(tableNo) not in relevant_tables:
                        print('skipping table #{:d}'.format(tableNo))
                        tableNo += 1
                        continue

                    # parse json
                    table_data = json.loads(json_line)
                    # create Table object to work with
                    table = Table(table_data)

                    # create hgp for each row
                    for row in table.rows():

                        # skip irrelevant rows
                        if relevant_tables:
                            relevant_rows = relevant_tables[str(tableNo)]
                            if row.row_idx not in relevant_rows:
                                print('skipping row #{:d} in table #{:d}'.format(row.row_idx, tableNo))
                                continue

                        # initialize hypothethis graph pattern (hgp) as empty set/list
                        hgp = []
                        # Entity-Dictionnairy key:entity and value:blankNode
                        eDict = {}
                        # Entity-Was-Dict key:blankNode and value:entity
                        eWasDict = {}
                        # Literal-Dictionnairy key:literal+type and value:blankNode
                        lDict = {}
                        # Literal-Was-Dict key:blankNode and value:literal+type
                        lWasDict = {}
                        # indexing of the blank nodes
                        nodeNo = 1


                        ####################################################################
                        # EL
                        for cell in row:
                            for annotation in cell.find_annotations(anno_source='preprocessing', anno_task='EntityLinking'):

                                #fill the dictionnairies in whih the blank_nodes for entities are encoded and decoded
                                e = '<' + annotation['resource_uri'] + '>'
                                if e not in eDict.keys():
                                    bNodeE = '_:b' + str(nodeNo)
                                    nodeNo += 1
                                    eDict[e] = bNodeE
                                    eWasDict[bNodeE] = e

                                    # rdf-type for EL
                                    typeUris = send_sparql_request_type(e)
                                    for uri in typeUris:
                                        uri = '<'+uri+'>'
                                        hgp.append(eDict[e] + '\t' + '<http://www.w3.org/1999/02/22-rdf-syntax-ns#type>' + '\t' + uri + ' .\n') #2

                                # fill entity ditionnairies also with the "literal"@en
                                literal = '\"' + str(cell.content)+ '\"@en'
                                if literal not in lDict.keys():
                                    bNodeL = '_:b' + str(nodeNo)
                                    nodeNo += 1
                                    lDict[literal] = bNodeL
                                    eWasDict[bNodeL] = literal

                                    # append to hgp:  e  rdfs:label   l
                                    bNodeL = lDict[literal]
                                    hgp.append(bNodeE + '\t' + '<http://www.w3.org/2000/01/rdf-schema#label>' + '\t' + bNodeL + ' .\n') #3

                                    # append to hgp:  l(=literal)   ex:col   c (= col number)
                                    c = '\"' + str(cell.col_idx) + '\"^^<http://www.w3.org/2001/XMLSchema#int>'
                                    hgp.append(bNodeL + '\t' + '<http://example.org/column>' + '\t' + c + ' .\n') #1


                        ####################################################################
                        # LL
                        for cell in row:
                            for annotation in cell.find_annotations(anno_source='preprocessing', anno_task='LiteralLinking'):
                                # for every LL-annotation in the row, add the triple (e,p,l) to hgp / (bNode,p,l)
                                # e - entity/uri mentioned in the LL-hypothesis  (= references_el -> uri)
                                # bNode - e replaced by blank node
                                # p - property/uri mentioned in the LL-hypothesis
                                # l - literal (= indexvalue + indexType)

                                el_anno = table.get_annotation(annotation["references_el"])

                                e = '<' + el_anno['resource_uri'] + '>'
                                ebNode = eDict[e]
                                p = '<' + annotation['property_uri'] + '>'

                                if annotation['index_type'] == "":
                                    l = '\"' + str(annotation['index_value']) + '\"'
                                else:
                                    l = '\"' + str(annotation['index_value']) + '\"^^<' + annotation['index_type'] + '>'

                                if l not in lDict.keys():
                                    bNode = '_:b' + str(nodeNo)
                                    nodeNo += 1
                                    lDict[l] = bNode
                                    lWasDict[bNode] = l

                                # blank p blank
                                hgp.append(ebNode + '\t' + p + '\t' + lDict[l] + ' .\n') #4
                                # for every LL-annotation in the row, add the triple (l, ex:column, c) to hgp
                                c = '\"' + str(cell.col_idx) + '\"^^<http://www.w3.org/2001/XMLSchema#int>'
                                hgp.append(lDict[l] + '\t' + '<http://example.org/column>' + '\t' + c + ' .\n') #5


                        ####################################################################
                        # create (x p y)
                        entity_combis = list(itertools.combinations_with_replacement(eDict.keys(), r=2))  # [A,B,C,D] -> [(A,A), (A,B), (AC), (A,D), (B,B), (B,C), (B,D), (C,C), (C,D), (D,D)]

                        for combi in entity_combis:
                            x = combi[0]
                            y = combi[1]

                            # add triples of the form (x p y) to hgp
                            list_of_triples = send_sparql_request_entities(x, y)
                            if list_of_triples:
                                #replace x,y with blank node
                                list_of_triples = [triple.replace(x, eDict[x]).replace(y, eDict[y]) for triple in list_of_triples]
                                hgp.extend(list_of_triples)



                        ####################################################################
                        # create entity-was     _:b1 ex:was <uri>/label
                        for key in eWasDict.keys():
                            e = eWasDict[key]
                            bNode = key
                            hgp.append(bNode + '\t' + '<http://example.org/was>' + '\t' + e + ' .\n') #8


                        ####################################################################
                        # create literal-was     _:b1 ex:was <uri>
                        for key in lWasDict.keys():
                            l = lWasDict[key]
                            bNode = key
                            hgp.append(bNode + '\t' + '<http://example.org/was>' + '\t' + l + ' .\n') #9


                        ####################################################################
                        # save HGP in file (1 HGP for each row in each table)
                        fileName = 'Table_' + str(tableNo) + '_Row_' + str(row.row_idx) + '_HG.txt'
                        outFile = open(fileName, 'w')
                        outFile.writelines(hgp)
                        outFile.close()


                    tableNo+=1





