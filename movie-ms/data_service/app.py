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
    return r.json

