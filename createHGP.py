
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
                          + y + ' ?p2 ' + x + ' .}}'}

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

                    # parse the table from the json
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

                        # initialize hypothethis graph pattern (hgp) as empty list
                        hgp = []
                        # Entity-Dictionnairy that indicates which entity has which blank-node. key:entity-uri, value: blankNode
                        eDict = {}
                        # Entity-Was-Dict that indicates which blank-node belongs to which entity-uri. key:blankNode and value:entity
                        eWasDict = {}
                        # Literal-Dictionnairy key:literal+type and value:blankNode
                        lDict = {}
                        # Literal-Was-Dict key:blankNode and value:literal+type
                        lWasDict = {}
                        # indexing of the blank nodes
                        nodeNo = 1
                        # dict that indicates which uri in which col occured: key:entity-Uri, value:list of colidx
                        eColDict = {}



                        ####################################################################
                        # EL
                        for cell in row:

                            # fill entity dictionnairies also with the "literal"@en
                            literal = '\"' + str(cell.content) + '\"@en'
                            if literal not in lDict.keys():
                                bNodeL = '_:b' + str(nodeNo)
                                nodeNo += 1
                                lDict[literal] = bNodeL
                                eWasDict[bNodeL] = literal

                            # append to hgp:  l(=literal)   ex:col   c (= col number)
                            bNodeL = lDict[literal]
                            c = '\"' + str(cell.col_idx) + '\"^^<http://www.w3.org/2001/XMLSchema#int>'
                            hgp.extend(bNodeL + '\t' + '<http://example.org/column>' + '\t' + c + ' .\n')  # 1


                            for annotation in cell.find_annotations(anno_source='preprocessing', anno_task='EntityLinking'):

                                e = '<' + annotation['resource_uri'] + '>'

                                #save which entity-annotation occurred in which column
                                if e in eColDict:
                                    listOfColIdx = eColDict[e]
                                    listOfColIdx.append(cell.col_idx)
                                    eColDict[e] = listOfColIdx
                                else:
                                    eColDict[e] = [cell.col_idx]

                                #fill the dictionnairies in which the blank_nodes for entities are encoded and decoded
                                if e not in eDict.keys():
                                    bNodeE = '_:b' + str(nodeNo)
                                    nodeNo += 1
                                    eDict[e] = bNodeE
                                    eWasDict[bNodeE] = e

                                    # rdf-type for EL
                                    typeUris = send_sparql_request_type(e)
                                    for uri in typeUris:
                                        uri = '<'+uri+'>'
                                        hgp.extend(eDict[e] + '\t' + '<http://www.w3.org/1999/02/22-rdf-syntax-ns#type>' + '\t' + uri + ' .\n') #2



                                # append to hgp:  e  rdfs:label   l
                                bNodeL = lDict[literal]
                                hgp.extend(bNodeE + '\t' + '<http://www.w3.org/2000/01/rdf-schema#label>' + '\t' + bNodeL + ' .\n') #3






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

                                if annotation['index_value'] not in lDict.keys():
                                    bNode = '_:b' + str(nodeNo)
                                    nodeNo += 1
                                    lDict[annotation['index_value']] = bNode
                                    lWasDict[bNode] = l

                                hgp.extend(ebNode + '\t' + p + '\t' + lDict[annotation['index_value']] + ' .\n') #4
                                # for every LL-annotation in the row, add the triple (l, ex:column, c) to hgp
                                c = '\"' + str(cell.col_idx) + '\"^^<http://www.w3.org/2001/XMLSchema#int>'
                                hgp.extend(lDict[annotation['index_value']] + '\t' + '<http://example.org/column>' + '\t' + c + ' .\n') #5


                        ####################################################################
                        # create (e1 p e2)
                        # find out for which entity-combis a dbpedia request will be sent: only for those entities/uris, which were not annotated in the same column
                        interesting_entity_combis = []

                        # start with all combis (e1,e2) where  e=<uri>
                        all_entity_combis = list(itertools.combinations(eColDict.keys(), r=2))  # [A,B,C,D] -> [(A,B), (A,C), (A,D), (B,C), (B,D), (C,D)]
                        for combi in all_entity_combis:
                            colidx_e1 = eColDict[combi[0]]
                            colidx_e2 = eColDict[combi[1]]

                            if not list(set(colidx_e1).intersection(colidx_e2)): # combi[0]=e1 and combi[1]=e2 are not annotations in the same cell
                                interesting_entity_combis.append(combi)

                        # check for all combis with itself [(A,A), (B,B), (C,C), (D,D)]
                        for e, colidx in eColDict.items():
                            if (len(colidx)>1): # check if uri was annotated in more than one column
                                interesting_entity_combis.append((e,e))



                        # send dbpedia requests for the intersting combis and add the results to the hgp
                        for combi in interesting_entity_combis:
                            e1 = combi[0]
                            e2 = combi[1]
                            # add triples of the form (e1 p e2) to hgp
                            list_of_triples = send_sparql_request_entities(e1, e2)
                            if list_of_triples:
                                #replace e1,e2 with their blank nodes
                                list_of_triples = [triple.replace(e1, eDict[e1]).replace(e2, eDict[e2]) for triple in list_of_triples]
                                hgp.extend(list_of_triples)



                        ####################################################################
                        # create entity-was     _:b1 ex:was <uri>/label
                        for key in eWasDict.keys():
                            e = eWasDict[key]
                            bNode = key
                            hgp.extend(bNode + '\t' + '<http://example.org/was>' + '\t' + e + ' .\n') #8


                        ####################################################################
                        # create literal-was     _:b1 ex:was <uri>
                        for key in lWasDict.keys():
                            l = lWasDict[key]
                            bNode = key
                            hgp.extend(bNode + '\t' + '<http://example.org/was>' + '\t' + l + ' .\n') #9


                        ####################################################################
                        # save HGP in file (1 HGP for each row in each table)
                        fileName = 'Table_' + str(tableNo) + '_Row_' + str(row.row_idx) + '_HG.txt'
                        outFile = open(fileName, 'w')
                        outFile.writelines(hgp)
                        outFile.close()


                    tableNo+=1





