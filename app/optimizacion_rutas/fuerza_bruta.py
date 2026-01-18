import itertools

def tsp_fuerza_bruta(destinos, df_matriz):
    """
    Encuentra la ruta óptima exacta usando fuerza bruta.
    Índices: enteros (0, 24, 37...)
    Columnas: strings ('0', '24', '37'...)
    """
    if not destinos:
        return [0, 0], 0.0
    
    # Si solo hay un destino
    if len(destinos) == 1:
        tiempo = df_matriz.loc[0, str(destinos[0])] * 2  # ← columna string
        return [0, destinos[0], 0], tiempo
    
    mejor_ruta = None
    menor_tiempo = float('inf')
    
    # Probar todas las permutaciones posibles
    for perm in itertools.permutations(destinos):
        tiempo_total = 0
        
        # Tiempo desde Mataró (fila 0) al primer destino (columna string)
        tiempo_total += df_matriz.loc[0, str(perm[0])]  # ← fila 0, columna 'destino'
        
        # Tiempo entre destinos consecutivos (ambos enteros en filas)
        for i in range(len(perm) - 1):
            tiempo_total += df_matriz.loc[perm[i], str(perm[i + 1])]  # ← fila entero, columna string
        
        # Tiempo del último destino de vuelta a Mataró (columna '0')
        tiempo_total += df_matriz.loc[perm[-1], '0']  # ← fila entero, columna '0'
        
        # Actualizar si encontramos mejor ruta
        if tiempo_total < menor_tiempo:
            menor_tiempo = tiempo_total
            mejor_ruta = perm
    
    # Convertir a lista y agregar Mataró al inicio y final
    ruta_completa = [0] + list(mejor_ruta) + [0]
    
    return ruta_completa, menor_tiempo

def calcular_tiempo_ruta(ruta, df_matriz):
    """Calcula el tiempo total de una ruta."""
    tiempo_total = 0
    for i in range(len(ruta) - 1):
        tiempo_total += df_matriz.loc[ruta[i], str(ruta[i + 1])]
    return tiempo_total