import os
import sqlite3
from flask import g, Flask, render_template
from bokeh.models import ColumnDataSource
from bokeh.plotting import figure
from bokeh.embed import components
from bokeh.transform import factor_cmap
from bokeh.palettes import Spectral6
from bokeh.resources import INLINE

app = Flask(__name__)
app.config.from_object(__name__)

app.config.update(dict(
    DATABASE=os.path.join(app.root_path, 'seba.db'),
    SECRET_KEY='development key',
    USERNAME='admin',
    PASSWORD='default'
))
app.config.from_envvar('MONITOR_SETTINGS', silent=True)

def connect_db():
    rv = sqlite3.connect(app.config['DATABASE'])
    rv.row_factory = sqlite3.Row
    return rv

@app.teardown_appcontext
def close_db(error):
    if hasattr(g, '_database'):
        g._database.close()

def get_db():
    if not hasattr(g, '_database'):
        g._database = connect_db()
    return g._database

@app.route('/')
def main():
    db = get_db()
    cur = db.execute('select id, name, starttimestamp, endtimestamp from experiment')
    experiments = cur.fetchall()
    return render_template('experiments_list.html', experiments=experiments)

@app.route('/experiment/<int:id>')
def experiment_detail(id):
    result = {}
    db = get_db()
    cur = db.execute('select id, experimentId, sequenceNumber, '
                     'startTimeStamp, endTimeStamp, perturbationId, success '
                     'from batch where experimentid=?', (id, ))
    result['batches'] = cur.fetchall()
    cur = db.execute('select id, name, experimentId, configuration from realization where '
                     'experimentid=?', (id, ))
    result['realizations'] = cur.fetchall()
    relations = ['Batch', 'Realization', 'Function',
                 'ControlDefinition']
    queries = ["select count(*) from {} where experimentId={}".format(table,
                                                                      id) for
               table in relations]
    new_queries = [db.execute(query).fetchall() for query in queries]
    counts = [elem[0][0] for elem in new_queries]
    source = ColumnDataSource(data=dict(elements=relations, counts=counts))
    p = figure(x_range=relations, title="Experiment overview")
    p.vbar(x='elements', top='counts', width=0.9, source=source,
           fill_color=factor_cmap('elements', palette=Spectral6,
                                  factors=relations))
    script, div = components(p)
    js_resources = INLINE.render_js()
    css_resources = INLINE.render_css()
    return render_template('experiment_detail.html', data=result,
                           script=script, div=div, js_resources=js_resources,
                           css_resources=css_resources)
