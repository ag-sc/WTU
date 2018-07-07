import io, sys, json
from json.decoder import JSONDecodeError
from wtu.table import Table

import collections as cl

# Searches for literal links without gold comparison
def getLiteral_ng(cell):
    preprocessing = cell.find_annotations(anno_task='LiteralLinking')
    return [annotation['property_uri'] for annotation in preprocessing]  

# Searches for entity links without gold comparison
def getEntity_ng(cell):
    preprocessing = cell.find_annotations(anno_source='preprocessing',anno_task='EntityLinking')
    return [annotation['resource_uri'] for annotation in preprocessing]



def analyzeTable(table): 
    global num_found
    global found_tables

    
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

    for i in res_table.keys():
        if len(res_table[i]) > 10:
            s = s + str(i) + " "
            keys = keys + [str(i)]
            if not res_rows:
                res_rows = res_table[i]
            if res_table[i]:
                res_rows = list(set(res_rows) & set(res_table[i]))

    if res_rows and (len(res_rows)/len(table)) > 0.25 and len(keys) > 1:
        found_tables = found_tables + [num_tabel]
        num_found = num_found + 1
        print(s)
        print("Keys Entity:        ", el_list.keys(), "\nKeys Literals:      ", ll_list.keys())
        print("Row Numbers:        ", res_rows)
        print()


num_tabel = 0
num_found = 0
found_tables = []

def printTable(t):
    print("Table Num:" , num_tabel)
    for e in t:
        print(e)
    print('')

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
                    
                    if row.find_annotations(anno_task='EntityLinking') is not []:
                        i = 0
                        r = []
                        for cell in row:
                            if col[i]:
                                r = r + [[getEntity_ng(cell)]+[ getLiteral_ng(cell)]]
                                i += 1
                        if r:
                            t = t + [r]
                
                if t :
                    #printTable(t)
                    analyzeTable(t)

                num_tabel += 1

            except JSONDecodeError:
                pass

    print("Found Tables: ", found_tables, ", Number: ", num_found)

if __name__ == "__main__":
    main()
