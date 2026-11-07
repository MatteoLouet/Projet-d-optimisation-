
from grid import load_grid
from algorithms.greedy import greedy_search
from algorithms.astar import astar_search

# chargement de la grille
print("entrez 1 2 ou 3 selon la grille que vous voulez étudier")
num_grid = int(input())
if num_grid==1:
    grid, start, goal = load_grid("../grid_datasets/grid1.txt")
elif num_grid==2:
    grid, start, goal = load_grid("../grid_datasets/grid2.txt")
else:
    grid, start, goal = load_grid("../grid_datasets/grid3.txt")

print("Depart :", start)
print("Arrivée :", goal)
print()

# algo glouton
path_greedy = greedy_search(grid, start, goal)
print("Chemin du glouton :", path_greedy)
print("Longueur :", len(path_greedy), "cases")
print()

# algo A*
path_astar = astar_search(grid, start, goal)
print("Chemin de A* :", path_astar)
print("Longueur :", len(path_astar), "cases")
print()

# comparaison
if len(path_astar) < len(path_greedy):
    print("A* a trouvé un meilleur chemin")
elif len(path_astar) == len(path_greedy):
    print("Les deux algos ont trouve un chemin de meme longueur")
else:
    print("Le glouton a trouvé un meilleur chemin")
