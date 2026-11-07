from collections import deque


def bfs_search(graphe, start, goal):
    """Parcours en largeur : minimise le nombre de rues traversées, pas la distance."""
    from . import reconstruire_chemin

    file = deque([start])
    vus = {start}
    noeud_d_origine = {}
    explores = []

    while file:
        current = file.popleft()
        explores.extend((noeud_d_origine.get(current, current), current))

        if current == goal:
            break

        for voisin, _, _, _ in graphe.voisins(current):
            if voisin not in vus:
                vus.add(voisin)
                noeud_d_origine[voisin] = current
                file.append(voisin)

    return {"chemin": reconstruire_chemin(noeud_d_origine, start, goal), "explores": explores}
