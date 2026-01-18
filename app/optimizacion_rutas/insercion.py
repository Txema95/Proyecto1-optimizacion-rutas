def tsp_insercion(destinos, df_matriz):
    """
    Índices: enteros (0, 24, 37...)
    Columnas: strings ('0', '24', '37'...)
    """
    if not destinos:
        return [0, 0], 0.0
    
    if len(destinos) == 1:
        tiempo = df_matriz.loc[0, str(destinos[0])] * 2  # ← fila 0, columna string
        return [0, destinos[0], 0], tiempo
    
    if len(destinos) == 2:
        d1, d2 = destinos[0], destinos[1]
        
        # Opción 1: 0 → d1 → d2 → 0
        tiempo1 = (df_matriz.loc[0, str(d1)] +  # ← fila 0, columna string
                  df_matriz.loc[d1, str(d2)] +  # ← fila entero, columna string
                  df_matriz.loc[d2, '0'])       # ← fila entero, columna '0'
        
        # Opción 2: 0 → d2 → d1 → 0  
        tiempo2 = (df_matriz.loc[0, str(d2)] + 
                  df_matriz.loc[d2, str(d1)] + 
                  df_matriz.loc[d1, '0'])
        
        if tiempo1 <= tiempo2:
            return [0, d1, d2, 0], tiempo1
        else:
            return [0, d2, d1, 0], tiempo2
    
    # Ordenar destinos por cercanía a Mataró
    destinos_ordenados = sorted(destinos, 
                                key=lambda x: df_matriz.loc[0, str(x)])  # ← fila 0, columna string
    
    # Ruta inicial con los 2 más cercanos a Mataró
    d1, d2 = destinos_ordenados[0], destinos_ordenados[1]
    
    # Probar ambas orientaciones
    tiempo_ruta1 = df_matriz.loc[0, str(d1)] + df_matriz.loc[d1, str(d2)]
    tiempo_ruta2 = df_matriz.loc[0, str(d2)] + df_matriz.loc[d2, str(d1)]
    
    if tiempo_ruta1 <= tiempo_ruta2:
        ruta = [0, d1, d2, 0]
        tiempo_total = tiempo_ruta1 + df_matriz.loc[d2, '0']  # ← columna '0'
    else:
        ruta = [0, d2, d1, 0]
        tiempo_total = tiempo_ruta2 + df_matriz.loc[d1, '0']
    
    # Insertar los destinos restantes
    for destino in destinos_ordenados[2:]:
        mejor_posicion = None
        menor_incremento = float('inf')
        
        for i in range(1, len(ruta) - 1):
            antes = ruta[i - 1]
            despues = ruta[i]
            
            # Tiempo actual: antes → despues
            tiempo_actual = df_matriz.loc[antes, str(despues)]
            
            # Tiempo nuevo: antes → destino → despues
            tiempo_nuevo = (df_matriz.loc[antes, str(destino)] + 
                          df_matriz.loc[destino, str(despues)])
            
            incremento = tiempo_nuevo - tiempo_actual
            
            if incremento < menor_incremento:
                menor_incremento = incremento
                mejor_posicion = i
        
        # Insertar en la mejor posición
        ruta.insert(mejor_posicion, destino)
        tiempo_total += menor_incremento
    
    return ruta, tiempo_total

def tsp_insercion_mejor_inicio(destinos, df_matriz):
    """
    Versión mejorada: prueba diferentes destinos iniciales.
    Trabaja con enteros para filas, strings para columnas.
    """
    if len(destinos) <= 2:
        return tsp_insercion(destinos, df_matriz)
    
    mejor_ruta = None
    menor_tiempo = float('inf')
    
    # Probar empezar con cada par de destinos (usando enteros)
    for i in range(len(destinos)):
        for j in range(i + 1, len(destinos)):
            # Crear lista con este par como primeros (enteros)
            destinos_reordenados = [destinos[i], destinos[j]]
            destinos_reordenados.extend(
                [d for d in destinos if d not in (destinos[i], destinos[j])]
            )
            
            # Llamar a tsp_insercion con enteros
            ruta, tiempo = tsp_insercion(destinos_reordenados, df_matriz)
            
            if tiempo < menor_tiempo:
                menor_tiempo = tiempo
                mejor_ruta = ruta
    
    return mejor_ruta, menor_tiempo

# Función auxiliar para debug
def mostrar_ruta_detallada(ruta, df_matriz):
    """Muestra detalles de una ruta con tiempos entre nodos."""
    if not ruta or len(ruta) < 2:
        print("Ruta vacía o inválida")
        return
    
    tiempo_total = 0
    print("\nDetalles de la ruta:")
    
    for i in range(len(ruta) - 1):
        origen = ruta[i] if ruta[i] != 0 else '0'
        destino = ruta[i + 1] if ruta[i + 1] != 0 else '0'
        
        tiempo = df_matriz.loc[str(origen), str(destino)]
        tiempo_total += tiempo
        
        print(f"  {origen} → {destino}: {tiempo:.2f}h")
    
    print(f"\nTiempo total: {tiempo_total:.2f}h")
    return tiempo_total