from flask import Flask, request, abort, render_template, make_response
try:
    from metatool import metatool
except ImportError:
    import metatool

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

if __name__ == "__main__":
    app.run(host='0.0.0.0', debug=True, port=5005)
