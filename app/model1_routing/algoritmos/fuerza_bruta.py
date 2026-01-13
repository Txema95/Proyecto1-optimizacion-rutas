import pandas as pd
from itertools import permutations
from constantes import ORIGEN as mataro

def calcular(df_matriz_distancias):
    origen_fijo = mataro['nombre_completo']
    # Los puntos a permutar son todos los demás
    puntos_intermedios = [d for d in df_matriz_distancias.columns.values if d != origen_fijo]

    # 3. Generar todas las rutas y calcular sus distancias
    resultados = []

    # Generar todas las permutaciones de los puntos intermedios
    # ¡Cuidado! Para 10 destinos, N! = 3,628,800. Para más, se vuelve lento.
    for p in permutations(puntos_intermedios):
        # La ruta completa incluye el origen al principio y al final
        ruta_completa_paradas = [origen_fijo] + list(p)
        
        # Calcular la distancia de esta ruta
        distancia = calcular_distancia_ruta(ruta_completa_paradas, df_matriz_distancias, origen_fijo)
        print(f"Ruta: {' -> '.join(ruta_completa_paradas)} | Distancia: {distancia} km")
        # Almacenar el resultado
        resultados.append({
            "ruta": " -> ".join(ruta_completa_paradas),
            "distancia": distancia
        })

    # Convertir a DataFrame para fácil manejo y ordenamiento
    df_resultados = pd.DataFrame(resultados)

    # Ordenar por distancia, de la más corta a la más larga
    df_resultados_ordenado = df_resultados.sort_values(by="distancia", ascending=True)

    # 4. Mostrar las mejores 10 rutas (o todas si son menos de 10)
    print(f"--- Las {min(10, len(df_resultados_ordenado))} Mejores Rutas (Iniciando en {origen_fijo}) ---")
    print(df_resultados_ordenado.head(10).to_string(index=False))

    return df_resultados_ordenado

def calcular_distancia_ruta(ruta, df_matriz_distancias, origen):
    """
    Calcula la distancia total de una ruta cíclica.
    La ruta comienza en el 'origen', recorre los demás puntos y regresa al 'origen'.
    """
    distancia_total = 0
    # La ruta de viaje es la secuencia de paradas INTERNAS
    paradas_internas = list(ruta)
    
    # 1. Recorrer la ruta (e.g., Origen -> P1 -> P2)
    for i in range(len(paradas_internas) - 1):
        origen_actual = paradas_internas[i]
        destino_actual = paradas_internas[i+1]
        
        # Acceder a la distancia en el DataFrame: df.loc[origen, destino]
        distancia = df_matriz_distancias.loc[origen_actual, destino_actual]
        distancia_total += distancia
    
    # 2. Regreso al origen (e.g., P2 -> Origen)
    # Desde el último punto de la secuencia, de vuelta al punto de inicio.
    # ultimo_destino = paradas_internas[-1]
    # distancia_regreso = df_matriz_distancias.loc[ultimo_destino, origen]
    # distancia_total += distancia_regreso
    
    return distancia_total