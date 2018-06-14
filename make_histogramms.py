import io, sys, json
from json.decoder import JSONDecodeError
from wtu.table import Table

from matplotlib.pyplot import *
import matplotlib.pyplot as plt
import collections as cl


# Searches for literal links
def getLiteral(new_set, cell):
    c = ""
    task = 'LiteralLinking'
    feat = 'property_uri'

    gold = cell.find_annotations(anno_task=task)

    if gold:
        # extract resource uri from annotation as literal
        gold_uri = gold[0][feat]

        preprocessing = cell.find_annotations(anno_source=new_set,anno_task=task)
        # extract resource uris and frequencies
        preprocessing_uris = {annotation[feat] for annotation in preprocessing}

        # check if our annotations also include the gold annotation
        if gold_uri in preprocessing_uris and gold_uri in props:
            c = gold_uri
    else:
        c = "ng"
    return c

# Searches for entity links
def getEntity(gold_set, new_set, cell):
    c = ""
    task = 'EntityLinking'
    feat = 'resource_uri'

    gold = cell.find_annotations(anno_source=gold_set,anno_task=task)

    if gold:
        # extract resource uri from annotation as entity
        gold_uri = gold[0][feat]
        preprocessing = cell.find_annotations(anno_source=new_set,anno_task=task)

        # extract resource uris and frequencies
        preprocessing_uris = {
            annotation[feat]: annotation['frequency']
            for annotation in preprocessing
        }

        # check if our annotations also include the gold annotation
        if gold_uri in preprocessing_uris:
            c = gold_uri    
    else:
        c = "ng"
    return c


# Creates the histogramm for after a new table was analysed
def makeHist(tab, ana, key_list, s):
    for k in key_list.keys():
        if ana[k] in tab[k] and ana[key_list[k]] and ana[k] < s:
            tab[k][ana[k]] = tab[k][ana[k]] + 1 
        elif ana[key_list[k]] and ana[k] < s:
            tab[k][ana[k]] = 1

    return tab



# Looks if a label is already in the list of lables and adds it if not
def createLbl(lbl, ana, key_list,s):
    for k in key_list.keys():
        if ana[k] not in lbl and ana[k] < s:
            lbl = lbl + [ana[k]]

    return lbl



# Analyses a row/colum and returns the results
def analyze(line):
    res = {'m':0, 'm_el':0, 'm_ll':0, 'ng':False, 'ng_el':False, 'ng_ll':False}

    for cell in line: 
        if cell[0] is '' and cell[1] is '' :
            res['m'] += 1
        if cell[0] is '':
            res['m_el'] += 1
        if cell[1] is '':
            res['m_ll'] += 1

        if cell[0] is not 'ng' and cell[1] is not 'ng':
            res['ng'] = True
        if cell[0] is not 'ng':
            res['ng_el'] = True
        if cell[1] is not 'ng':
            res['ng_ll'] = True

    return res


# Analyses the table and adds the result to the overall results
def analyzeTable(table):
    global hist_row
    global hist_col

    global lbl_col
    global lbl_row

    key_list = {'m':'ng', 'm_el':'ng_el', 'm_ll':'ng_ll'}
    tabel_local = {'m':{0:0}, 'm_el':{0:0}, 'm_ll':{0:0}}
    lbl_row_local = []

    for i in range(1, len(table[0])):
       ana = analyze([row[i-1] for row in table]) 

       hist_col = makeHist(hist_col, ana, key_list, 61)
       lbl_row = createLbl(lbl_row, ana, key_list, len(table[0]))
       lbl_row_local = createLbl(lbl_row_local, ana, key_list, len(table[0]))

    for row in table:
       ana = analyze(row) 

       tabel_local = makeHist(tabel_local, ana, key_list, len(row))
       hist_row    = makeHist(hist_row, ana, key_list, len(row))
       lbl_col = createLbl(lbl_col, ana, key_list,  61)

    # Graph for every table
    #fig, ax = plt.subplots(figsize=(20,12))

    #plt_bar(ax, cl.OrderedDict(sorted(tabel_local['m'].items())), 
                #cl.OrderedDict(sorted(tabel_local['m_el'].items())), 
                #cl.OrderedDict(sorted(tabel_local['m_ll'].items())))

    #fig = plt.gcf()

    #plt.xticks(range(len(lbl_row_local)), sorted(lbl_row_local))

    #ax.set_ylabel('Overall number of rows with this number of empty cells')
    #ax.set_xlabel('Number of empty cells in a row')

    #plt.savefig(str('table'+ str(num_tabel) + '_new.png'))
    #plt.close()


# Makes a single plot in d new file for a given data set
def plt_bar(ax, od, el, ll):
    w = 0.2

    rects    = ax.bar([d       for d in od.keys()], od.values(), w, ecolor='green', label="Entity + Literal")
    rects_el = ax.bar([d + w   for d in el.keys()], el.values(), w, ecolor='blue', label="Entity")
    rects_ll = ax.bar([d + 2*w for d in ll.keys()], ll.values(), w, ecolor='violet', label="Literal ")

    legend()

    for rect in rects + rects_el + rects_ll:
        height = rect.get_height()
        ax.text(rect.get_x() + rect.get_width()/2., height + 0.05,'%d' % int(height),ha='center', va='bottom').set_fontsize(9)
    for item in ax.get_xticklabels() + ax.get_yticklabels():
        item.set_fontsize(12)



# Delets al columns that have no gold standart annotation
def delCols(table, col):
    for row in table:
        j = 0
        for i in range(0, len(col)):
            if col[i]:
                del row[j]
            else:
                j += 1
    return table



# Delets all rows that have no gold standart annotation
def delRows(t, row):
    for col in row:
        if col[0] != 'ng' or col[1] != 'ng':
            return t+[row]
    return t



# row_missing, row_missing_el, row_missing_ll
hist_row = {'m':{0:0}, 'm_el':{0:0}, 'm_ll':{0:0}}

# col_missing, col_missing_el, col_missing_ll
hist_col = {'m':{0:0}, 'm_el':{0:0}, 'm_ll':{0:0}}

#1?
num_tabel = 0

# Lables for colums
lbl_col = []
# Lables for rows
lbl_row = []

props = [l.strip('\n') for l in io.open('properties_to_consider.txt', 'r', encoding='utf-8', errors='ignore')]

def main():
    global num_tabel
    # read from stdin, ignore encoding errors
    with io.open(sys.stdin.fileno(), 'r', encoding='utf-8', errors='ignore') as stdin:
        # iterate over input. Each line represents one table
        for json_line in stdin:
            try:
                # parse json
                table_data = json.loads(json_line)
                # create Table object to work with
                table = Table(table_data)
                t = []
                delCol = [True] * table.num_cols
                for row in table.rows():
                    r = []
                    i = 0
                    for cell in row:
                        # get EntityLinkning annotation from Gold Standard for this cell
                        el = getEntity('gold-v2', 'preprocessing', cell)
                        ll = getLiteral('preprocessing', cell)
                        if el is not 'ng' or ll is not 'ng':
                           delCol[i] = False
                        r = r + [[el] + [ll]]
                        i += 1
                    t = delRows(t, r)
                t = delCols(t, delCol)
                #print(t)
                #print(delCol, "\n")
                if t != []:
                    analyzeTable(t)
                num_tabel += 1

            # ignore json decoding errors
            except JSONDecodeError:
                pass

    # Create histogramm 1
    fig, ax_row = plt.subplots(figsize=(20,12))

    plt_bar(ax_row, cl.OrderedDict(sorted(hist_row['m'].items())), 
                    cl.OrderedDict(sorted(hist_row['m_el'].items())), 
                    cl.OrderedDict(sorted(hist_row['m_ll'].items())))

    plt.xticks(range(len(lbl_col)), sorted(lbl_col))

    ax_row.set_ylabel('Overall number of rows with this number of empty cells')
    ax_row.set_xlabel('Number of empty cells in a row')

    fig = plt.gcf()

    plt.savefig('01_ov_rows.png')
    plt.close()


    # Create histogramm 2
    fig, ax_col = plt.subplots(figsize=(20,12))

    plt_bar(ax_col, cl.OrderedDict(sorted(hist_col['m'].items())), 
                    cl.OrderedDict(sorted(hist_col['m_el'].items())), 
                    cl.OrderedDict(sorted(hist_col['m_ll'].items())))

    plt.xticks(range(len(lbl_row)), sorted(lbl_row))

    ax_col.set_ylabel('Overall columns of rows with this number of empty cells')
    ax_col.set_xlabel('Number of columns with an empty cell')

    fig = plt.gcf()

    plt.savefig('01_ov_cols.png')
    plt.close()


if __name__ == "__main__":
    main()
