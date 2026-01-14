# Proyecto1-optimizacion-rutas

algoritmos a mirar:
    - Nearest Neighbor
    - Grafos (dijkstra?)

sphinx => libreria para hacer documentación


tenemos la matriz de nodos, hay que mirar que algoritmo usar para calcular las rutas posibles
    
    - FLOYD-WARSHALL?
    - OPTIMIZACIÓN MULTIOBJETIVA?
estamos usando un modelo de ia? 

ALGORITMOS GENETICOS para calcular rutas
tener en cuenta (problemas):
    - convergencia a las soluciones optimas => parametro de mutacion => hay que tener cuidad en no pasarse con el valor o quedarse corto (probabilidad de 1 a 10)
    - baja diversidad genetica =>
    - tiempo computacional

Parametros del algoritmo:
    - population size: 
    - numero de generaciones que queremos
    - selection rate
    - crossover rate: cuantas bifurcaciones del camino hacer
    - mutation rate
    - chromosome lenght
    
algoritmo de la reduccion de la dimensionalidad => ENCONTRAR LA MEJOR POBLACION INICIAL
    - PCA => elimina correlaciones o relaciones lineales en vectores
    - UMAP => reduce caracteristicas de los individuos
    - T-SNE
algoritmo de clustering => para definir grupos o clusters de ciudades => reducimos el espacio para hacer caminos mas cortos

PyGAD => librería que proporciona un marco sencillo y flexible para implementar algoritmos genéticos




corregir llamada al algoritmo genetico, mirar gemini. peta porque lee string en vez de indices