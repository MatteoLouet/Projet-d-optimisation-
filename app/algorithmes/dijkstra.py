import heapq


def dijkstra_search(graphe, start, goal):
    """A* sans heuristique : on explore par coût réel croissant (référence optimale)."""
    from . import reconstruire_chemin

    open_list = []
    heapq.heappush(open_list, (0.0, start))
    close_list = set()
    noeud_d_origine = {}
    coût_total = {start: 0.0}
    explores = []

    while open_list:
        coût_courant, current = heapq.heappop(open_list)
        if current in close_list:
            continue
        close_list.add(current)
        explores.extend((noeud_d_origine.get(current, current), current))

        if current == goal:
            break

        for voisin, coût, _, _ in graphe.voisins(current):
            if voisin in close_list:
                continue
            nouveau_coût = coût_courant + coût
            if voisin not in coût_total or nouveau_coût < coût_total[voisin]:
                coût_total[voisin] = nouveau_coût
                noeud_d_origine[voisin] = current
                heapq.heappush(open_list, (nouveau_coût, voisin))

    return {"chemin": reconstruire_chemin(noeud_d_origine, start, goal), "explores": explores}
