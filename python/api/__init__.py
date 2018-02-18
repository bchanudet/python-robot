import flask, json


app = flask.Flask(__name__)

@app.route("/")
def index():
    return "Hello World!"


app.run(debug=True)

