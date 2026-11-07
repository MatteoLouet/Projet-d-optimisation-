import heapq


def astar_search(graphe, start, goal):
    from . import reconstruire_chemin

    open_list = []
    heapq.heappush(open_list, (graphe.heuristique(start, goal), start))
    close_list = set()
    noeud_d_origine = {}
    coût_total = {start: 0.0}
    explores = []

    while open_list:
        priorité, current = heapq.heappop(open_list)
        if current in close_list:          # ancienne entrée devenue obsolète
            continue
        close_list.add(current)
        explores.extend((noeud_d_origine.get(current, current), current))

        if current == goal:
            break

        for voisin, coût, _, _ in graphe.voisins(current):
            if voisin in close_list:
                continue

            nouveau_coût = coût_total[current] + coût

            if voisin not in coût_total or nouveau_coût < coût_total[voisin]:
                coût_total[voisin] = nouveau_coût
                noeud_d_origine[voisin] = current
                # f = g + h
                priorité = nouveau_coût + graphe.heuristique(voisin, goal)
                heapq.heappush(open_list, (priorité, voisin))

    return {"chemin": reconstruire_chemin(noeud_d_origine, start, goal), "explores": explores}
