from flask import Flask, request
import json

from equipment_search import init, search_equipment

# creates a Flask application, named app
app = Flask(__name__, static_url_path='')

INDEX_PAGE = open('index.html', 'r').read()

@app.route('/', methods=['GET'])
def index_page():
    return INDEX_PAGE

@app.route('/search', methods=['POST'])
def search():
    results = search_equipment(json.loads(request.form["request"]))
    return json.dumps(results)

# run the application
if __name__ == "__main__":
    init()
    app.run(host='0.0.0.0')
