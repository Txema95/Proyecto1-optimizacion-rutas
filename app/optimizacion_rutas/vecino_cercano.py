def tsp_vecino_mas_cercano(destinos, df_matriz):
    """
    Heurística: siempre elige el destino más cercano.
    Rápido pero no garantiza óptimo.
    
    Args:
        destinos: Lista de IDs de destino
        df_matriz: DataFrame con tiempos
        
    Returns:
        tuple: (ruta_completa, tiempo_total)
    """
    if not destinos:
        return [0, 0], 0.0
    
    # Copiar lista de destinos no visitados
    no_visitados = destinos.copy()
    ruta = [0]  # Empezar en Mataró
    tiempo_total = 0
    actual = 0  # Posición actual (Mataró)
    
    while no_visitados:
        # Encontrar el destino no visitado más cercano
        mas_cercano = None
        menor_distancia = float('inf')
        
        for destino in no_visitados:
            distancia = df_matriz.loc[actual, str(destino)]
            if distancia < menor_distancia:
                menor_distancia = distancia
                mas_cercano = destino
        
        # Mover al destino más cercano
        tiempo_total += menor_distancia
        ruta.append(mas_cercano)
        no_visitados.remove(mas_cercano)
        actual = mas_cercano
    
    # Regresar a Mataró
    tiempo_total += df_matriz.loc[actual, 0]
    ruta.append(0)
    
    return ruta, tiempo_total

def tsp_vecino_mas_cercano_mejor_inicio(destinos, df_matriz):
    if not destinos:
        return [0, 0], 0.0
    
    mejor_ruta_global = None
    menor_tiempo_global = float('inf')
    
    for primer_destino in destinos:
        no_visitados = [d for d in destinos if d != primer_destino]
        ruta = [0, primer_destino]  # Mataró como 0 (entero)
        tiempo_total = df_matriz.loc[0, str(primer_destino)]  # ← fila 0, columna string
        actual = primer_destino  # entero
        
        while no_visitados:
            # Encontrar el destino no visitado más cercano
            mas_cercano = None
            menor_distancia = float('inf')
            
            for destino in no_visitados:
                distancia = df_matriz.loc[actual, str(destino)]  # ← fila entero, columna string
                if distancia < menor_distancia:
                    menor_distancia = distancia
                    mas_cercano = destino
            
            tiempo_total += menor_distancia
            ruta.append(mas_cercano)
            no_visitados.remove(mas_cercano)
            actual = mas_cercano
        
        # Regresar a Mataró (columna '0')
        tiempo_total += df_matriz.loc[actual, '0']  # ← fila entero, columna '0'
        ruta_completa = ruta + [0]
        
        if tiempo_total < menor_tiempo_global:
            menor_tiempo_global = tiempo_total
            mejor_ruta_global = ruta_completa
    
    return mejor_ruta_global, menor_tiempo_global