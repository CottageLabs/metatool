from flask import Flask, request, abort, render_template, make_response
import json, requests
from StringIO import StringIO

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
    return render_template("acat_search.html", es_host=config.ES_HOST, es_index=config.ES_INDEX)

if __name__ == "__main__":
    app.run(host='0.0.0.0', debug=True, port=5005)
