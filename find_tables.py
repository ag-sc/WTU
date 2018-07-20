import io, sys, json
from json.decoder import JSONDecodeError
from wtu.table import Table

import collections as cl

# Searches for literal links without gold comparison
def getLiteral_ng(cell):
    preprocessing = cell.find_annotations(anno_task='LiteralLinking')

    return list(set([annotation['property_uri'].replace('http://dbpedia.org/ontology/', '') for annotation in preprocessing]))

# Searches for entity links without gold comparison
def getEntity_ng(cell):
    preprocessing = cell.find_annotations(anno_source='preprocessing',anno_task='EntityLinking')
    return [annotation['resource_uri'].replace('http://dbpedia.org/resource/', '') for annotation in preprocessing]



def analyzeTable(table, g_col): 
    global num_found
    global found_tables
    global found_tables_with_rows

    
    el_list = {}
    ll_list = {}
    keys = [[]]

    for i in range(0, len(table[0])):
       col = [row[i] for row in table]

       el = sorted([j for j in range(0,len(col)) if col[j][0] not in keys])
       ll = sorted([j for j in range(0,len(col)) if col[j][1] not in keys])
       
       if el:
           el_list[i] = el

       if ll:
           ll_list[i] = ll
       
    res_table = {}
    found_el = []

    for e in el_list.keys():
       for l in ll_list.keys():
           res = list(set(el_list[e]) & set(ll_list[l]))
           tmp = str("(el:" + str(e) + "; ll:" + str(l)+")")
           res_table[tmp] = res
       for ee in el_list.keys():
           res = list(set(el_list[e]) & set(el_list[ee]))
           tmp = str("(el:" + str(e) + "; el:" + str(ee)+")")
           if str("(el:" + str(ee) + "; el:" + str(e)+")") not in res_table.keys() and e is not ee:
               res_table[tmp] = res

    s = 'TABLE ' + str(num_tabel) + ": Length = " + str(len(table[0])) + '\nFound column pairs:  '
    
    res_rows = []
    keys = []
    res_cols = []

    for i in res_table.keys():
        if len(res_table[i]) > 10:
            s = s + str(i) + " "
            keys = keys + [str(i)]
            res_cols = list(set(res_cols + [i[4]] + [i[10]]))
            if not res_rows:
                res_rows = res_table[i]
            if res_table[i]:
                res_rows = list(set(res_rows) & set(res_table[i]))

    if res_rows and (len(res_rows)/len(table)) > 0.25 and len(keys) > 1:
        found_tables = found_tables + [num_tabel]
        num_found = num_found + 1
        res_rows = sorted(res_rows)
        print(s)
        print("Keys Entity:        ", el_list.keys(), "\nKeys Literals:      ", ll_list.keys())
        print("Row Numbers:        ", res_rows)
        print("Col Numbers:        ", sorted(res_cols))
        print("Col Label:          ", [g_col[i][0]['property_uri'].replace("http://dbpedia.org/ontology/", "") if str(g_col[i][0]['property_uri']) not in 'http://www.w3.org/2000/01/rdf-schema#label' else 'label' for i in range(0,len(g_col)) if g_col[i] and str(i) in res_cols], "\n")
        #print("Col Label:          ", [g_col[i][0]['property_uri'] for i in range(0,len(g_col)) if g_col[i] and str(i) in res_cols], "\n")
        printTableWithSelRows(table, res_rows, sorted(res_cols))
        #printTable(table)
        print("\n")

        found_tables_with_rows = found_tables_with_rows + [{num_tabel:sorted(res_rows)}]

def printTableWithSelRows(t, rows, cols):
    print("Table:")
    for i in range(0, len(t)):
        if i in rows:
            r = []
            for j in range(0, len(t[0])):
                if str(j) in cols:
                    r = r + [t[i][j]]
            print(i , ": ", r)
    print('')

def printTable(t):
    print("Table Num:" , num_tabel)
    for e in t:
        print(e)
    print('')

num_tabel = 0
num_found = 0
found_tables = []

found_tables_with_rows = []

def main():
    global num_tabel
    with io.open(sys.stdin.fileno(), 'r', encoding='utf-8', errors='ignore') as stdin:
        for json_line in stdin:
            try:
                table_data = json.loads(json_line)
                table = Table(table_data)

                t = []
                
                col = [c.find_annotations(anno_task = 'PropertyLinking') for c in table.columns()]

                for row in table.rows():
                    
                    if row.find_annotations(anno_source = 'preprocessing', anno_task='EntityLinking') is not []:
                        i = 0
                        r = []
                        for cell in row:
                            if col[i]:
                                r = r + [[getEntity_ng(cell)]+[getLiteral_ng(cell)]]
                                i += 1
                        if r:
                            t = t + [r]
                
                if t :
                    analyzeTable(t, col)

                num_tabel += 1

            except JSONDecodeError:
                pass

    print("Found Tables: ", found_tables, ", Number: ", num_found, "\n")
    print(found_tables_with_rows)

if __name__ == "__main__":
    main()
