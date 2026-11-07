"""
Chargement du réseau de rues de Paris (OpenStreetMap via osmnx) et conversion
en une structure compacte utilisable par nos algorithmes :

    - les noeuds sont numérotés de 0 à n-1 (indices)
    - adj[i] = liste de (j, cout, longueur_m, temps_s)
    - la fonction heuristique(i, j) donne une borne inférieure du coût de i à j

Pour la marche et le vélo, le coût d'une arête = sa longueur en mètres.
Pour la voiture, le coût = le temps de parcours en secondes (limites de vitesse).
"""

import math
import time
from pathlib import Path

import numpy as np
import osmnx as ox

DOSSIER_DATA = Path(__file__).resolve().parent.parent / "data"
LIEU = "Paris, France"

# mode -> (type de réseau osmnx, vitesse moyenne en km/h, critère)
MODES = {
    "pied":    {"reseau": "walk",  "vitesse_kmh": 5.0,  "critere": "distance"},
    "velo":    {"reseau": "bike",  "vitesse_kmh": 15.0, "critere": "distance"},
    "voiture": {"reseau": "drive", "vitesse_kmh": None, "critere": "temps"},
}

RAYON_TERRE = 6_371_000.0

SERVEURS_OVERPASS = [
    "https://overpass-api.de/api",
    "https://overpass.private.coffee/api",
    "https://maps.mail.ru/osm/tools/overpass/api",
]


def haversine(lon1, lat1, lon2, lat2):
    """Distance à vol d'oiseau en mètres entre deux points GPS."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = p2 - p1
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * RAYON_TERRE * math.asin(math.sqrt(a))


def telecharger(mode):
    """Télécharge (ou relit depuis le cache) le graphe osmnx du mode demandé."""
    DOSSIER_DATA.mkdir(exist_ok=True)
    chemin = DOSSIER_DATA / f"paris_{mode}.graphml"
    if chemin.exists():
        return ox.load_graphml(chemin)
    print(f"[graphe] téléchargement du réseau '{mode}' de Paris (peut prendre 1 à 3 min)...")
    G = None
    for essai in range(3):
        for url in SERVEURS_OVERPASS:
            ox.settings.overpass_url = url
            try:
                G = ox.graph_from_place(LIEU, network_type=MODES[mode]["reseau"], simplify=True)
                break
            except Exception as e:
                print(f"[graphe] échec sur {url} : {type(e).__name__}, on essaie le suivant")
        if G is not None:
            break
        time.sleep(10 * (essai + 1))
    if G is None:
        raise RuntimeError("Impossible de télécharger le réseau (serveurs Overpass indisponibles)")
    G = ox.add_edge_speeds(G)
    G = ox.add_edge_travel_times(G)
    ox.save_graphml(G, chemin)
    return G


class Graphe:
    def __init__(self, mode):
        self.mode = mode
        conf = MODES[mode]
        self.critere = conf["critere"]
        G = telecharger(mode)

        ids = list(G.nodes)
        self.index = {nid: i for i, nid in enumerate(ids)}
        self.lon = np.array([G.nodes[n]["x"] for n in ids], dtype=float)
        self.lat = np.array([G.nodes[n]["y"] for n in ids], dtype=float)
        n = len(ids)

        vitesse_ms = conf["vitesse_kmh"] / 3.6 if conf["vitesse_kmh"] else None
        meilleur = {}        # (i, j) -> (cout, longueur, temps, geometrie)
        vmax_kph = 1.0

        for u, v, data in G.edges(data=True):
            i, j = self.index[u], self.index[v]
            if i == j:
                continue
            longueur = float(data.get("length", 0.0))
            if vitesse_ms:
                temps = longueur / vitesse_ms
            else:
                temps = float(data.get("travel_time", longueur / (30 / 3.6)))
                vmax_kph = max(vmax_kph, float(data.get("speed_kph", 30)))
            cout = longueur if self.critere == "distance" else temps

            if "geometry" in data:
                geom = [(round(x, 6), round(y, 6)) for x, y in data["geometry"].coords]
            else:
                geom = [(round(self.lon[i], 6), round(self.lat[i], 6)),
                        (round(self.lon[j], 6), round(self.lat[j], 6))]

            if (i, j) not in meilleur or cout < meilleur[(i, j)][0]:
                meilleur[(i, j)] = (cout, longueur, temps, geom)

        self.adj = [[] for _ in range(n)]
        self.geom = {}
        for (i, j), (cout, longueur, temps, geom) in meilleur.items():
            self.adj[i].append((j, cout, longueur, temps))
            self.geom[(i, j)] = geom

        # heuristique : distance à vol d'oiseau (en m) ou temps minimal (en s)
        # à la vitesse max du réseau -> toujours admissible pour A*
        self.diviseur_h = 1.0 if self.critere == "distance" else vmax_kph / 3.6

        # rues pour le fond de carte (une seule fois par paire de noeuds)
        vues = set()
        self.rues = []
        for (i, j), (_, _, _, geom) in meilleur.items():
            cle = (min(i, j), max(i, j))
            if cle in vues:
                continue
            vues.add(cle)
            self.rues.append([c for xy in geom for c in (round(xy[0], 5), round(xy[1], 5))])

        self.nb_noeuds = n
        self.nb_aretes = len(meilleur)
        print(f"[graphe] {mode}: {n} noeuds, {self.nb_aretes} arêtes")

    # --- outils utilisés par les algorithmes -------------------------------
    def voisins(self, i):
        return self.adj[i]

    def heuristique(self, a, b):
        return haversine(self.lon[a], self.lat[a], self.lon[b], self.lat[b]) / self.diviseur_h

    def noeud_le_plus_proche(self, lat, lon):
        # distance équirectangulaire, suffisante à l'échelle de Paris
        dx = (self.lon - lon) * math.cos(math.radians(lat))
        dy = self.lat - lat
        return int(np.argmin(dx * dx + dy * dy))

    # --- export pour le navigateur -----------------------------------------
    def noeuds_plats(self):
        sortie = np.empty(2 * self.nb_noeuds)
        sortie[0::2] = np.round(self.lon, 6)
        sortie[1::2] = np.round(self.lat, 6)
        return sortie.tolist()

    def geometrie_chemin(self, chemin):
        coords = []
        for a, b in zip(chemin, chemin[1:]):
            g = self.geom[(a, b)]
            coords.extend(g if not coords else g[1:])
        if not coords and chemin:
            coords = [(self.lon[chemin[0]], self.lat[chemin[0]])]
        return [list(c) for c in coords]

    def mesures_chemin(self, chemin):
        longueur = temps = 0.0
        for a, b in zip(chemin, chemin[1:]):
            for j, _, l, t in self.adj[a]:
                if j == b:
                    longueur += l
                    temps += t
                    break
        return longueur, temps


if __name__ == "__main__":
    # python app/graphe.py  -> pré-télécharge les 3 réseaux
    for m in MODES:
        Graphe(m)
