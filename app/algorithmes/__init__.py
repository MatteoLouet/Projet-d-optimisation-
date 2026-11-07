"""
Algorithmes de plus court chemin adaptés au graphe des rues de Paris.

Ce sont les mêmes idées que astar.py / greedy.py (sur grille), mais :
  - les voisins viennent du graphe (graphe.voisins(noeud) -> (voisin, coût, ...))
  - le coût d'un déplacement n'est plus 1 mais la longueur (ou le temps) de la rue
  - l'heuristique est la distance à vol d'oiseau (Manhattan n'a pas de sens en GPS)

Chaque algorithme renvoie un dict :
    chemin   : liste des noeuds du départ à l'arrivée ([] si introuvable)
    explores : liste plate [parent0, noeud0, parent1, noeud1, ...] dans l'ordre
               où les noeuds sont sortis de la file -> sert à l'animation
"""

from .astar import astar_search
from .bfs import bfs_search
from .dijkstra import dijkstra_search
from .greedy import greedy_search

ALGOS = {
    "dijkstra": {"nom": "Dijkstra", "fonction": dijkstra_search},
    "astar":    {"nom": "A*",       "fonction": astar_search},
    "greedy":   {"nom": "Glouton",  "fonction": greedy_search},
    "bfs":      {"nom": "BFS",      "fonction": bfs_search},
}


def reconstruire_chemin(noeud_d_origine, start, goal):
    """On remonte de goal à start en suivant noeud_d_origine."""
    if goal != start and goal not in noeud_d_origine:
        return []
    chemin = []
    current = goal
    while current != start:
        chemin.append(current)
        current = noeud_d_origine[current]
    chemin.append(start)
    chemin.reverse()
    return chemin
