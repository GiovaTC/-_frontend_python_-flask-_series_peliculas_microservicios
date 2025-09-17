from flask import Flask, jsonify, request
import os, time, requests
from dotenv import load_dotenv
from threading import Lock

load_dotenv()
TMDB_KEY = os.getenv("TMDB_API_KEY")
app = Flask(__name__)

#cache simple en memoria con TTL
_cache, _cache_lock = {}, Lock()
CACHE_TTL =  60 * 5 # 5 minutos

def set_cache(key, value):
    with _cache_lock:
        _cache[key] = (value, time.time())

def get_cache(key):
    with _cache_lock:
        item = _cache.get(key)
        if not item: return None
        value, ts = item
        if time.time() - ts > CACHE_TTL:
            del_cache[key]
            return None
        return value

def call_tmdb(path, params=None):
    base="https://api.themoviedb.org/3"
    if params is None:params = {}
    params['api_key'] = TMDB_KEY
    r= requests.get(f"{base}{path}", params=params, timeout=10)
    r.raise_for_status()
    return r.json()

@app.route("/health")
def health():
    return jsonify({"status": "ok"})

@app.route("/search")
def search():
    q = request.args.get("q", "").strip()
    type_ = request.args.get("type","multi")
    if not q: return jsonify({"error":"missing query 'q"}), 400

    cache_key = f"search:{type_}:{q}"
    result = get_cache(cache_key)
    if result: return jsonify({"cached": True, "data": result})
    try:
        if  TMDB_KEY:
            tm= call_tmdb(f"/search/{type_}", params={"query":q, "page":1, "include_adult": False})
            items=[]
            for it in tm.get("results", []):
                items.append({
                    "id": it.get("id"),
                    "title": it.get("title") or it.get("name"),
                    "overview": it.get("overview"),
                    "type": "movie" if it.get("media_type","")=="movie" or it.get("title") else "tv",
                    "poster_path": f"https://image.tmdb.org/t/p/w300{it.get('poster_path')}" if it.get("poster_path") else None,
                    "release_date": it.get("release_data") or it.get("first_air_date")
                })
            set_cache(cache_key, items)
            return jsonify({"cached": False, "data": items})
        else:
            r= requests.get(f"https://api.sampleapis.com/movies/action", timeout= 10)
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
       

