
import heapq

def heuristic(a,b):
    return abs(a[0]-b[0])+abs(a[1]-b[1])


def voisins(grid, node):
    x, y = node
    résultat = []

    haut    = (x, y-1)
    bas     = (x, y+1)
    gauche  = (x-1, y)
    droite  = (x+1, y)

    for voisin in [haut, bas, gauche, droite]:
        vx, vy = voisin
        if 0 <= vy < len(grid) and 0 <= vx < len(grid[vy]):    # on check que le voisin est bien dans la grid
            if grid[vy][vx] != "X":                            # et on vérifie que c'est pas une valeur pas atteignable
                résultat.append(voisin)

    return résultat

def astar_search(grid, start, goal):
    open_list = []
    heapq.heappush(open_list, (0, start))
    close_list = set()
    noeud_d_origine = {}
    coût_total = {start: 0}

    while open_list:
        tuple_retourne = heapq.heappop(open_list)
        priorite = tuple_retourne[0]
        current = tuple_retourne[1]
        if current == goal:
            close_list.add(current)
            break

        for voisin in voisins(grid, current):
            if voisin in close_list:
                continue

            nouveau_coût = coût_total[current] + 1

            if voisin not in coût_total or nouveau_coût < coût_total[voisin]:
                coût_total[voisin] = nouveau_coût
                noeud_d_origine[voisin] = current
                priorité = nouveau_coût + heuristic(voisin, goal)
                heapq.heappush(open_list, (priorité, voisin))

    # on remonte de goal à start en suivant noeud_d_origine
    chemin = []
    current = goal
    while current != start:
        chemin.append(current)
        current = noeud_d_origine[current]

    chemin.append(start)
    chemin.reverse()
    return chemin


