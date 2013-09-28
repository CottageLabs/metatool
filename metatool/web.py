from flask import Flask, request, abort, render_template, make_response
import json
try:
    from metatool import metatool
except ImportError:
    import metatool

try:
    from metatool import viz
except ImportError:
    import viz

app = Flask(__name__)

@app.route("/")
def index():
    return render_template('index.html')

@app.route("/validate", methods=["POST"])
def validate():
    mt = request.values.get("modeltype")
    f = request.files.get("model")
    fieldsets = metatool.validate_model(mt, f)
    html = metatool.fieldsets_to_html(fieldsets)
    return render_template("results.html", tables=html)

@app.route("/visualise", methods=["POST"])
def visualise():
    mt = request.values.get("modeltype")
    f = request.files.get("model")
    nodes = viz.get_nodes(mt, f)
    return render_template("viz.html", nodes=json.dumps(nodes))

if __name__ == "__main__":
    app.run(host='0.0.0.0', debug=True, port=5005)
