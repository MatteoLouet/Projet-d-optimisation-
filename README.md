# Paris Pathfinding

Application web qui compare des algorithmes de plus court chemin (Dijkstra, A*, Glouton, BFS)
sur le vrai réseau de rues de Paris (OpenStreetMap), avec animation de l'exploration en direct.

## Lancer

```bash
python3 -m venv .venv
.venv/bin/pip install osmnx flask
.venv/bin/python app/graphe.py      # 1re fois : télécharge les réseaux (pied / vélo / voiture) dans data/
.venv/bin/python app/server.py      # puis ouvrir http://localhost:5050
```

## Organisation

- `app/algorithmes/` : les algos adaptés de `astar.py` / `greedy.py` (grille) au graphe des rues
- `app/graphe.py` : téléchargement OSM + conversion en liste d'adjacence, heuristique (vol d'oiseau)
- `app/server.py` : API Flask (`/api/reseau/<mode>`, `/api/geocode`, `/api/calcul`)
- `app/static/` : interface (carte deck.gl : rues en blanc sur fond noir, animation)

Coût des arêtes : distance (pied, vélo) ou temps de parcours (voiture).
