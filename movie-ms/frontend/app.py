from flask import Flask, render_template, request, redirect, url_for
import os, requests
from dotenv import load_dotenv

load_dotenv()
DATA_HOST = os.getenv("DATA_SERVICE_HOST", "data-service")
DATA_PORT = os.getenv("DATA_SERVICE_PORT", "5000")
DATA_BASE = f"http://{DATA_HOST}:{DATA_PORT}"

app = Flask(__name__)

@app.route("/")
def index():
    q = request.args.get("q","")
    return render_template("index.html", q=q, results=None)

@app.route("/search")
def search():
    q = request.args.get("q","").strip()
    if not q: return redirect(url_for("index"))
    try:
        resp = requests.get(f"{DATA_BASE}/search", params={"q": q, "type":"multi"}, timeout=8)
        resp.raise_for_status()
        data = resp.json().get("data", [])
    except:
        data = []
    return render_template("results.html", query=q, results=data)

@app.route("/detail/<typ>/<int:item_id>")
def detail(typ, item_id):
    try:
        resp = requests.get(f"{DATA_BASE}/{typ}/{item_id}", timeout=8)
        resp.raise_for_status()
        data = resp.json().get("data")
    except:
        data = None
    return render_template("index.html", detail=data)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)