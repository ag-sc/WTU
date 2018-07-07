import io, sys, json
from json.decoder import JSONDecodeError
from wtu.table import Table
# bokeh

from bokeh.core.properties import value
from bokeh.io import show, output_file
from bokeh.models import ColumnDataSource
from bokeh.plotting import figure, save
from bokeh.transform import dodge

import collections as cl

# Searches for literal links
def getLiteral(cell, col, i):
    c = ""

    task = 'LiteralLinking'
    feat = 'property_uri'
    new_set = 'preprocessing'

    if col[i]:
        # extract resource uri from annotation as literal
        gold_uri = col[i][0][feat]

        preprocessing = cell.find_annotations(anno_task=task)
        if preprocessing:
            # extract resource uris and frequencies
            preprocessing_uris = {annotation[feat] for annotation in preprocessing}

            # check if our annotations also include the gold annotation
            if gold_uri in preprocessing_uris and gold_uri in props:
                c = gold_uri
    else:
        c = "ng"
    return c

# Searches for entity links
def getEntity(cell):
    c = ""

    task = 'EntityLinking'
    feat = 'resource_uri'
    gold_set = 'gold-v2'
    new_set = 'preprocessing'

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
def makeHist(tab, ana, key_list):
    for k in key_list.keys():
        if ana[k] in tab[k] and ana[key_list[k]]:
            tab[k][ana[k]] = tab[k][ana[k]] + 1 
        elif ana[key_list[k]]:
            tab[k][ana[k]] = 1

    return tab



# Looks if a label is already in the list of lables and adds it if not
def createLbl(lbl, ana, key_list):
    for k in key_list.keys():
        if ana[k] not in lbl:
            lbl = lbl + [ana[k]]
    return lbl



# Analyses a row/colum and return the results
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

    global num_found
    global found_tables

    tabel_local_row = {'m':{0:0}, 'm_el':{0:0}, 'm_ll':{0:0}}
    tabel_local_col = {'m':{0:0}, 'm_el':{0:0}, 'm_ll':{0:0}}
    lbl_row_local = []
    lbl_col_local = []

    for i in range(0, len(table[0])):
       ana = analyze([row[i] for row in table]) 

       tabel_local_col = makeHist(tabel_local_col, ana, key_list)
       hist_col      = makeHist(hist_col, ana, key_list)
       lbl_row       = createLbl(lbl_row, ana, key_list)
       lbl_row_local = createLbl(lbl_row_local, ana, key_list)

    for row in table:
       ana = analyze(row) 

       tabel_local_row = makeHist(tabel_local_row, ana, key_list)
       hist_row    = makeHist(hist_row, ana, key_list)
       lbl_col     = createLbl(lbl_col, ana, key_list)
       lbl_col_local = createLbl(lbl_col_local, ana, key_list)

    
    # Graph for every table
    plt_bar(tabel_local_row, lbl_col_local, 'Overall number of rows with this number of empty cells', str('Number of empty cells in a row for tabel' + str(num_tabel)), str('hists/rows_table'+ str(num_tabel) + '.html'), 600, '#Missing Annotations in row', '#How often this amount is missing')
    plt_bar(tabel_local_col, lbl_row_local, 'Overall number of col with this number of empty cells', str('Number of empty cells in a col for tabel' + str(num_tabel)), str('hists/col_table'+ str(num_tabel) + '.html'), 600, '#Missing Annotations in row', '#How often this amount is missing')


# Makes a single plot in d new file for a given data set
def plt_bar(hist_tabel, lbl_list, ylabel, xlabel, filename, wigth, xl, yl):
    w = 0.2

    output_file(filename)

    palette = ["#c9d9d3", "#718dbf", "#e84d60"]

    od = cl.OrderedDict(sorted(hist_tabel['m'].items()))
    el = cl.OrderedDict(sorted(hist_tabel['m_el'].items()))
    ll = cl.OrderedDict(sorted(hist_tabel['m_ll'].items()))

    odl = [od[l] if l in od else 0 for l in sorted(lbl_list)]
    ell = [el[l] if l in el else 0 for l in sorted(lbl_list)]
    lll = [ll[l] if l in ll else 0 for l in sorted(lbl_list)] 
    num = [str(s) for s in sorted(lbl_list)]

    d = {'num': num, 'Entity + Literal': odl, 'Entity': ell, 'Literal': lll}

    l = max(odl + ell + lll)

    p = figure(x_range=num, y_range=(0,l+(l/4)), plot_height=350, plot_width=wigth, toolbar_location=None, tools="", x_axis_label=xl, y_axis_label=yl)

    p.vbar(x=dodge('num', -0.25, range=p.x_range), top='Entity + Literal', width=0.1, source=d,
       color="#c9d9d3", legend=value("Entity + Literal"))

    p.vbar(x=dodge('num',  0.0,  range=p.x_range), top='Entity', width=0.1, source=d,
       color="#718dbf", legend=value("Entity"))

    p.vbar(x=dodge('num',  0.25, range=p.x_range), top='Literal', width=0.1, source=d,
       color="#e84d60", legend=value("Literal"))

    #p.x_range.range_padding = 0.1
    p.xgrid.grid_line_color = None
    p.legend.orientation = "horizontal"
    p.legend.location = "top_left"

    save(p)

# Makes a single plot in d new file for a given data set
def plt_bar2(hist_tabel, used, ylabel, xlabel, filename, wigth, xl, yl):
    w = 0.2
    output_file(filename)

    gold = hist_tabel['gold']
    pre = hist_tabel['pre']
    
    up = [u.replace('http://dbpedia.org/ontology/', '') for u in used]

    goldl = [gold['http://dbpedia.org/ontology/'+l] if 'http://dbpedia.org/ontology/'+l in gold.keys() else 0 for l in up]
    prel  = [pre['http://dbpedia.org/ontology/'+l]  if 'http://dbpedia.org/ontology/'+l in pre.keys()  else 0 for l in up]

    data = {'up': up, 'Gold': goldl, 'Preprocessing': prel}

    source = ColumnDataSource(data=data)

    p = figure(x_range=up, plot_height=800, plot_width=wigth, toolbar_location=None, tools="",x_axis_label=xl, y_axis_label=yl)

    p.vbar(x=dodge('up', -0.25, range=p.x_range), top='Gold', width=0.2, source=data, color="#c9d9d3", legend=value("Gold"))

    p.vbar(x=dodge('up',  0.0,  range=p.x_range), top='Preprocessing', width=0.2, source=data, color="#718dbf", legend=value("Preprocessing"))


    p.x_range.range_padding = 0.1
    p.xgrid.grid_line_color = None
    p.xaxis.major_label_orientation = 1
    p.legend.orientation = "horizontal"
    p.legend.location = "top_left"

    save(p)

props = [l.strip('\n') for l in io.open('properties_to_consider.txt', 'r', encoding='utf-8', errors='ignore')]

key_list = {'m':'ng', 'm_el':'ng_el', 'm_ll':'ng_ll'}

# row_missing, row_missing_el, row_missing_ll
hist_row = {'m':{0:0}, 'm_el':{0:0}, 'm_ll':{0:0}}

# col_missing, col_missing_el, col_missing_ll
hist_col = {'m':{0:0}, 'm_el':{0:0}, 'm_ll':{0:0}}

num_tabel = 0
num_found = 0
found_tables = []

# Lables for colums
lbl_col = []
# Lables for rows
lbl_row = []

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
                                r = r + [[getEntity(cell)] + [getLiteral(cell, col, i)]]
                                i += 1
                        if r:
                            t = t + [r]
                
                if t:
                    analyzeTable(t)
                num_tabel += 1

            # ignore json decoding errors
            except JSONDecodeError:
                pass

    # Create histogramm for rows
    plt_bar(hist_row, lbl_col, 'Overall number of rows ', 'Number of empty cells in a row', 'hists/01_ov_rows.html', 4000, '#Missing Annotations in row', '#How often this amount is missing')

    # Create histogramm columns
    plt_bar(hist_col, lbl_row, 'Overall number of cols', 'Number of empty cells in a col', 'hists/01_ov_cols.html', 4000, '#Missing Annotations in column', '#How often this amount is missing')

if __name__ == "__main__":
    main()
