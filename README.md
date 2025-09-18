# -_frontend_python_-flask-_series_peliculas_microservicios .

<img width="203" height="193" alt="image" src="https://github.com/user-attachments/assets/acd0ce8a-579d-497b-a76e-797430d0bb13" />

<img width="2556" height="1079" alt="image" src="https://github.com/user-attachments/assets/cabcec7d-22cf-49f5-9d99-72a95b069c21" />

<img width="2551" height="1079" alt="image" src="https://github.com/user-attachments/assets/4a460647-3819-4520-be76-5e6ec7f79ddd" />
    
<img width="2550" height="1079" alt="image" src="https://github.com/user-attachments/assets/3b7fe2e5-0088-40dc-892f-2d75bccae456" />

<img width="2551" height="1079" alt="image" src="https://github.com/user-attachments/assets/926be751-40e9-422b-b4f3-00be4c320eb1" />

<img width="2554" height="1079" alt="image" src="https://github.com/user-attachments/assets/d1f15d15-736a-438e-814b-e429208e15b1" />

<img width="2552" height="1079" alt="image" src="https://github.com/user-attachments/assets/a4aae67f-4631-4c9b-9132-135d9ecbdb4a" />

# 🎬 Frontend en Python (Flask) para Series y Películas con Microservicios
este proyecto implementa una arquitectura **microservicio simple** para consultar películas y series desde APIs públicas .  
el sistema se compone de :
- **data-service (Flask)**: Proxy/adapter que consume la API externa (ej. TMDb) y normaliza la respuesta, con cache en memoria .
- **frontend (Flask + Jinja2)**: Interfaz web que consume el data-service y muestra resultados (búsqueda, detalles) .
- **docker-compose**: Orquestación de ambos servicios .
- **Plantillas HTML (Bootstrap + Jinja2)**: Interfaz básica pero funcional .

---

## 🏗️ Arquitectura

```plaintext
movie-ms/
├─ data_service/
│  ├─ Dockerfile
│  ├─ app.py
│  ├─ requirements.txt
├─ frontend/
│  ├─ Dockerfile
│  ├─ app.py
│  ├─ requirements.txt
│  └─ templates/
│     ├─ index.html
│     └─ results.html
├─ docker-compose.yml
└─ .env.example

flujo:
El usuario busca una película/serie en el frontend .
El frontend hace la petición al data-service .
El data-service consulta TMDb (o fallback en APIs públicas) .

respuesta normalizada → enviada al frontend .
el frontend muestra resultados y detalles .

⚙️ Archivos y Código
.env.example
env

# si usas TMDB, pon tu API KEY aquí (recomendado) .
TMDB_API_KEY=your_tmdb_api_key_here

# puerto interno del data service .
DATA_SERVICE_HOST=data-service
DATA_SERVICE_PORT=5000
data_service/requirements.txt

txt
Flask==2.2.5
requests==2.31.0
python-dotenv==1.0.0
data_service/Dockerfile
dockerfile

FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py .
COPY .env .
CMD ["python", "app.py"]
data_service/app.py

python
from flask import Flask, jsonify, request
import os, time, requests
from dotenv import load_dotenv
from threading import Lock

load_dotenv()
TMDB_KEY = os.getenv("TMDB_API_KEY")
app = Flask(__name__)

# cache simple en memoria con TTL
_cache, _cache_lock = {}, Lock()
CACHE_TTL = 60 * 5  # 5 minutos

def set_cache(key, value):
    with _cache_lock:
        _cache[key] = (value, time.time())

def get_cache(key):
    with _cache_lock:
        item = _cache.get(key)
        if not item: return None
        value, ts = item
        if time.time() - ts > CACHE_TTL:
            del _cache[key]
            return None
        return value

def call_tmdb(path, params=None):
    base = "https://api.themoviedb.org/3"
    if params is None: params = {}
    params['api_key'] = TMDB_KEY
    r = requests.get(f"{base}{path}", params=params, timeout=10)
    r.raise_for_status()
    return r.json()

@app.route("/health")
def health():
    return jsonify({"status": "ok"})

@app.route("/search")
def search():
    q = request.args.get("q","").strip()
    type_ = request.args.get("type","multi")
    if not q: return jsonify({"error":"missing query 'q'"}), 400

    cache_key = f"search:{type_}:{q}"
    result = get_cache(cache_key)
    if result: return jsonify({"cached": True, "data": result})
    try:
        if TMDB_KEY:
            tm = call_tmdb(f"/search/{type_}", params={"query": q, "page":1, "include_adult": False})
            items = []
            for it in tm.get("results", []):
                items.append({
                    "id": it.get("id"),
                    "title": it.get("title") or it.get("name"),
                    "overview": it.get("overview"),
                    "type": "movie" if it.get("media_type","")=="movie" or it.get("title") else "tv",
                    "poster_path": f"https://image.tmdb.org/t/p/w300{it.get('poster_path')}" if it.get("poster_path") else None,
                    "release_date": it.get("release_date") or it.get("first_air_date")
                })
            set_cache(cache_key, items)
            return jsonify({"cached": False, "data": items})
        else:
            r = requests.get(f"https://api.sampleapis.com/movies/action", timeout=10)
            data = r.json()
            items = [ {"id": i.get("id", idx), "title": i.get("title") or i.get("name"), "overview": i.get("plot"), "type": "movie"} 
                      for idx,i in enumerate(data) if q.lower() in (i.get("title","") + i.get("name","")).lower() ]
            set_cache(cache_key, items)
            return jsonify({"cached": False, "data": items})
    except Exception as e:
        return jsonify({"error":"api error", "detail": str(e)}), 500

@app.route("/movie/<int:movie_id>")
def movie_detail(movie_id):
    cache_key = f"movie:{movie_id}"
    cached = get_cache(cache_key)
    if cached: return jsonify({"cached": True, "data": cached})
    try:
        data = call_tmdb(f"/movie/{movie_id}")
        out = {
            "id": data.get("id"),
            "title": data.get("title"),
            "overview": data.get("overview"),
            "poster": f"https://image.tmdb.org/t/p/w500{data.get('poster_path')}" if data.get("poster_path") else None,
            "genres": [g['name'] for g in data.get("genres",[])],
            "runtime": data.get("runtime"),
            "release_date": data.get("release_date")
        }
        set_cache(cache_key, out)
        return jsonify({"cached": False, "data": out})
    except Exception as e:
        return jsonify({"error":"failed", "detail": str(e)}), 500

@app.route("/tv/<int:tv_id>")
def tv_detail(tv_id):
    cache_key = f"tv:{tv_id}"
    cached = get_cache(cache_key)
    if cached: return jsonify({"cached": True, "data": cached})
    try:
        data = call_tmdb(f"/tv/{tv_id}")
        out = {
            "id": data.get("id"),
            "title": data.get("name"),
            "overview": data.get("overview"),
            "poster": f"https://image.tmdb.org/t/p/w500{data.get('poster_path')}" if data.get("poster_path") else None,
            "genres": [g['name'] for g in data.get("genres",[])],
            "seasons": data.get("seasons"),
            "first_air_date": data.get("first_air_date")
        }
        set_cache(cache_key, out)
        return jsonify({"cached": False, "data": out})
    except Exception as e:
        return jsonify({"error":"failed", "detail": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

frontend/requirements.txt
txt
Flask==2.2.5
requests==2.31.0
python-dotenv==1.0.0
frontend/Dockerfile
dockerfile

FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py .
COPY templates ./templates
COPY .env .
CMD ["python", "app.py"]

frontend/app.py
python
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

frontend/templates/index.html
html
<!doctype html>
<html lang="es">
  <head>
    <meta charset="utf-8">
    <title>Películas y Series - Frontend</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
  </head>
  <body class="p-4">
    <div class="container">
      <h1>Películas y Series</h1>
      <form method="get" action="/search" class="my-3">
        <div class="input-group">
          <input type="text" class="form-control" name="q" placeholder="Buscar título..." value="{{ q or '' }}">
          <button class="btn btn-primary" type="submit">Buscar</button>
        </div>
      </form>
      {% if detail %}
      <div class="card mb-3">
        <div class="row g-0">
          {% if detail.poster %}
          <div class="col-md-4">
            <img src="{{ detail.poster }}" class="img-fluid rounded-start" alt="poster">
          </div>
          {% endif %}
          <div class="col">
            <div class="card-body">
              <h5 class="card-title">{{ detail.title }}</h5>
              <p class="card-text">{{ detail.overview }}</p>
              {% if detail.genres %}<p><strong>Géneros:</strong> {{ detail.genres|join(', ') }}</p>{% endif %}
              {% if detail.release_date %}<p><strong>Fecha:</strong> {{ detail.release_date }}</p>{% endif %}
            </div>
          </div>
        </div>
      </div>
      {% endif %}
      <p class="text-muted">La UI consume un microservicio que accede a una API pública (TMDb o similar).</p>
    </div>
  </body>
</html>

frontend/templates/results.html
html
<!doctype html>
<html lang="es">
  <head>
    <meta charset="utf-8">
    <title>Resultados - {{ query }}</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
  </head>
  <body class="p-4">
    <div class="container">
      <a href="/" class="btn btn-link">&larr; Volver</a>
      <h2>Resultados para "{{ query }}"</h2>
      <div class="row">
        {% for r in results %}
        <div class="col-md-4 mb-3">
          <div class="card h-100">
            {% if r.poster_path %}
            <img src="{{ r.poster_path }}" class="card-img-top" alt="poster">
            {% endif %}
            <div class="card-body">
              <h5 class="card-title">{{ r.title }}</h5>
              <p class="card-text">{{ r.overview | default('Sin descripción')|truncate(150) }}</p>
              <a href="/detail/{{ r.type }}/{{ r.id }}" class="btn btn-sm btn-primary">Ver detalle</a>
            </div>
          </div>
        </div>
        {% endfor %}
      </div>
    </div>
  </body>
</html>

docker-compose.yml
yaml
version: "3.8"
services:
  data-service:
    build: ./data_service
    environment:
      - TMDB_API_KEY=${TMDB_API_KEY}
    ports:
      - "5000:5000"
    restart: unless-stopped

  frontend:
    build: ./frontend
    environment:
      - DATA_SERVICE_HOST=data-service
      - DATA_SERVICE_PORT=5000
    ports:
      - "8000:8000"
    depends_on:
      - data-service
    restart: unless-stopped

🔑 Cómo obtener una API Key de TMDb
registrate en TMDb .
en tu cuenta → Settings → API → crea una API Key gratuita .

coloca tu clave en .env como TMDB_API_KEY .

⚠️ Si no configuras clave, el servicio usa un fallback con SampleAPIs , aunque con datos mas limitados .

▶️ Instrucciones para ejecutar
bash
# 1. clona/copía la estructura y crea el archivo .env
cp .env.example .env

# 2. si tienes clave TMDb, edita .env y agrega tu TMDB_API_KEY

# 3. construye y levanta los servicios
docker-compose build
docker-compose up
Abrir en navegador:

frontend: http://localhost:8000

Data-service (API): http://localhost:5000/health

🚀 siguientes mejoras
añadir Redis como cache compartido .
paginacion, manejo de imagenes optimizadas y lazy loading . 

frontend SPA con React/Vue .
autenticacion de usuarios .
tests -> CI/CD .

variables de entorno seguras con docker secrets .

📚 referencias
TMDb API Docs
OMDb API
free Movie/Series DB (ejemplos en GitHub) .


