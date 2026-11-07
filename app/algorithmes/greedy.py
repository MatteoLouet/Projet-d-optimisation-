import heapq


def greedy_search(graphe, start, goal):
    from . import reconstruire_chemin

    open_list = []
    heapq.heappush(open_list, (graphe.heuristique(start, goal), start))
    close_list = set()
    noeud_d_origine = {}
    explores = []

    while open_list:
        _, current = heapq.heappop(open_list)
        if current in close_list:
            continue
        close_list.add(current)
        explores.extend((noeud_d_origine.get(current, current), current))

        if current == goal:
            break

        for voisin, _, _, _ in graphe.voisins(current):
            if voisin in close_list or voisin in noeud_d_origine:
                continue

            noeud_d_origine[voisin] = current

            # le glouton utilise uniquement h, sans tenir compte du coût réel
            priorité = graphe.heuristique(voisin, goal)
            heapq.heappush(open_list, (priorité, voisin))

    return {"chemin": reconstruire_chemin(noeud_d_origine, start, goal), "explores": explores}
