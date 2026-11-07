"""
Serveur de l'application : python app/server.py  puis ouvrir http://localhost:5050
"""

import json
import threading
import time
import urllib.parse
import urllib.request

from flask import Flask, Response, jsonify, request, send_from_directory

from algorithmes import ALGOS
from graphe import MODES, Graphe

app = Flask(__name__, static_folder="static", static_url_path="/static")
app.json.sort_keys = False   # garder l'ordre Dijkstra, A*, Glouton, BFS

_graphes = {}
_reseaux_json = {}
_verrou = threading.Lock()


def graphe(mode):
    with _verrou:
        if mode not in _graphes:
            _graphes[mode] = Graphe(mode)
        return _graphes[mode]


@app.get("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.get("/api/reseau/<mode>")
def reseau(mode):
    if mode not in MODES:
        return jsonify(erreur="mode inconnu"), 404
    if mode not in _reseaux_json:
        g = graphe(mode)
        _reseaux_json[mode] = json.dumps({
            "mode": mode,
            "noeuds": g.noeuds_plats(),
            "rues": g.rues,
            "nb_noeuds": g.nb_noeuds,
            "nb_aretes": g.nb_aretes,
        }, separators=(",", ":"))
    return Response(_reseaux_json[mode], mimetype="application/json")


@app.get("/api/geocode")
def geocode():
    q = request.args.get("q", "").strip()
    if len(q) < 3:
        return jsonify([])
    params = urllib.parse.urlencode({
        "q": q, "format": "json", "limit": 6, "countrycodes": "fr",
        "viewbox": "2.224,48.902,2.470,48.815", "bounded": 1,
    })
    req = urllib.request.Request(
        f"https://nominatim.openstreetmap.org/search?{params}",
        headers={"User-Agent": "projet-optimisation-efrei/1.0", "Accept-Language": "fr"},
    )
    try:
        with urllib.request.urlopen(req, timeout=8) as r:
            data = json.load(r)
    except Exception as e:  # réseau indisponible, quota...
        return jsonify(erreur=str(e)), 502
    return jsonify([
        {"nom": d["display_name"], "lat": float(d["lat"]), "lon": float(d["lon"])}
        for d in data
    ])


@app.post("/api/calcul")
def calcul():
    p = request.get_json(force=True)
    mode = p.get("mode", "pied")
    if mode not in MODES:
        return jsonify(erreur="mode inconnu"), 400
    g = graphe(mode)
    start = g.noeud_le_plus_proche(*p["depart"])
    goal = g.noeud_le_plus_proche(*p["arrivee"])

    resultats = {}
    for cle, algo in ALGOS.items():
        t0 = time.perf_counter()
        r = algo["fonction"](g, start, goal)
        duree_ms = (time.perf_counter() - t0) * 1000
        longueur, temps = g.mesures_chemin(r["chemin"])
        resultats[cle] = {
            "nom": algo["nom"],
            "trouve": bool(r["chemin"]),
            "calcul_ms": round(duree_ms, 1),
            "nb_explores": len(r["explores"]) // 2,
            "nb_rues": max(len(r["chemin"]) - 1, 0),
            "distance_m": round(longueur, 1),
            "temps_s": round(temps, 1),
            "explores": r["explores"],
            "geometrie": g.geometrie_chemin(r["chemin"]),
        }

    return jsonify({
        "mode": mode,
        "critere": g.critere,
        "depart": [float(g.lon[start]), float(g.lat[start])],
        "arrivee": [float(g.lon[goal]), float(g.lat[goal])],
        "resultats": resultats,
    })


if __name__ == "__main__":
    # précharge les réseaux en arrière-plan pour que l'appli réponde vite
    threading.Thread(target=lambda: [graphe(m) for m in MODES], daemon=True).start()
    app.run(host="127.0.0.1", port=5050, debug=False, threaded=True)
