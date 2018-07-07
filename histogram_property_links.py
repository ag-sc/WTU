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
def setProperties(cell, col, i):
    global hist_props
    global used_props

    if col[i]:
        gold_uri = col[i][0]['property_uri']

        if gold_uri in hist_props['gold'].keys():
            hist_props['gold'][gold_uri] = hist_props['gold'][gold_uri] + 1
        else:
            hist_props['gold'][gold_uri] = 1

        if gold_uri not in used_props:
            used_props = used_props + [gold_uri]

        preprocessing = cell.find_annotations(anno_task='LiteralLinking')

        if preprocessing:
            # extract resource uris and frequencies
            preprocessing_uris = {annotation['property_uri'] for annotation in preprocessing}

            for p in preprocessing_uris:
                if p in hist_props['pre']:
                    hist_props['pre'][p] = hist_props['pre'][p] + 1
                else:
                    hist_props['pre'][p] = 1


# Makes a single plot in d new file for a given data set
def plt_bar(hist_tabel, used, ylabel, xlabel, filename, wigth, xl, yl):
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

hist_props = {'gold':{}, 'pre':{}}
used_props = []

num_tabel = 0

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
                                setProperties(cell, col, i)

                num_tabel += 1

            # ignore json decoding errors
            except JSONDecodeError:
                pass


    # Plot Propertys
    plt_bar(hist_props, used_props, 'Properties', 'Occurences', 'hists/01_props_ov.html', 3000, '#Missing PropertyLinks', 'Property')

if __name__ == "__main__":
    main()
