from flask import Flask, request, abort, render_template, make_response
import json, requests
from StringIO import StringIO
from time import sleep

try:
    from metatool import metatool
except ImportError:
    import metatool

try:
    from metatool import viz
except ImportError:
    import viz

try:
    from metatool import config
except ImportError:
    import config

try:
    from metatool import models
except ImportError:
    import models

try:
    from metatool import generate_test_data
except ImportError:
    import generate_test_data

app = Flask(__name__)

@app.route("/")
def index():
    return render_template('index.html', baseurl=config.BASE_URL)

@app.route("/validate", methods=["POST", "GET"])
def validate():
    mt = request.values.get("modeltype")
    f = None
    
    if request.method == "POST":
        f = request.files.get("model")
    elif request.method == "GET":
        url = request.values.get("url")
        resp = requests.get(url)
        f = StringIO(resp.text)
    
    fieldsets = metatool.validate_model(mt, f)
    html = metatool.fieldsets_to_html(fieldsets)
    return render_template("results.html", tables=html, baseurl=config.BASE_URL)

@app.route("/cerifeye", methods=["POST", "GET"])
def cerifeye():
    mt = request.values.get("modeltype")
    f = None
    
    if request.method == "POST":
        f = request.files.get("model")
    elif request.method == "GET":
        url = request.values.get("url")
        resp = requests.get(url)
        f = StringIO(resp.text)
    
    nodes = viz.get_nodes(mt, f)
    return render_template("cerifview.html", nodes=json.dumps(nodes), baseurl=config.BASE_URL)
    
@app.route("/visualise", methods=["POST", "GET"])
def visualise():
    mt = request.values.get("modeltype")
    f = None
    
    if request.method == "POST":
        f = request.files.get("model")
    elif request.method == "GET":
        url = request.values.get("url")
        resp = requests.get(url)
        f = StringIO(resp.text)
    
    nodes = viz.get_nodes(mt, f)
    return render_template("viz.html", nodes=json.dumps(nodes), baseurl=config.BASE_URL)

@app.route("/acat", methods=["GET"])
def acat_facetview():
    return render_template("acat_search.html", es_host=config.ES_HOST, es_index='acat')

@app.route("/aggregate/publications", methods=["GET"])
def publications_facetview():
    return render_template("aggregate_publications.html", es_host=config.ES_HOST, es_index='ukriss')

@app.route("/aggregate/publications/generate", methods=["GET"])
@app.route("/aggregate/publications", methods=["POST"])
def generate_publications():

    # make sure index is created and has right mappings
    init_status_code = models.Publication.initialise_index()
    if init_status_code != 200:
        return '''Elasticsearch has a problem initialising the {0} index, it returned a {1} HTTP status code.
Check the elasticsearch log for exceptions.'''.format(models.Publication.es_index, init_status_code)

    how_many = 1000
    generate_test_data.generate_and_index(how_many)

    models.Publication.refresh()
    sleep(1) # give ES a bit of time to do the refresh

    return "Generated {0} publication records".format(how_many)

if __name__ == "__main__":
    app.run(host='0.0.0.0', debug=True, port=5005)
