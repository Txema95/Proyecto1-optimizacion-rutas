import pandas as pd
import numpy as np
from sklearn.cluster import KMeans

def crear_clusters_capitados(df, capacidad_max=500):
    # 1. Estimar cuántos camiones necesitamos
    total_carga = df['Cantidad'].sum()
    n_clusters = int(np.ceil(total_carga / capacidad_max)) + 1 # Un margen extra
    
    # 2. Clustering geográfico inicial
    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    df['cluster_inicial'] = kmeans.fit_predict(df[['latitude', 'longitude']])
    
    # 3. Refinar clusters para respetar la capacidad (Heurística Greedy)
    camiones = []
    pedidos_pendientes = df.sort_values(by='Cantidad', ascending=False).to_dict('records')
    
    while pedidos_pendientes:
        camion_actual = []
        capacidad_actual = 0
        indices_a_eliminar = []
        
        for i, pedido in enumerate(pedidos_pendientes):
            if capacidad_actual + pedido['Cantidad'] <= capacidad_max:
                camion_actual.append(pedido)
                capacidad_actual += pedido['Cantidad']
                indices_a_eliminar.append(i)
        
        # Eliminar pedidos asignados de la lista de pendientes
        for index in sorted(indices_a_eliminar, reverse=True):
            pedidos_pendientes.pop(index)
            
        camiones.append(camion_actual)
    
    return camiones


# Coordenadas de Mataró (Origen)
ORIGEN = {'lat': 41.5381, 'lon': 2.4447}

def preparar_datos(df):
    # Calculamos el ángulo respecto a Mataró para el "Sweep Algorithm"
    df['rel_lat'] = df['latitude'] - ORIGEN['lat']
    df['rel_lon'] = df['longitude'] - ORIGEN['lon']
    # Atan2 nos da el ángulo en radianes
    df['angulo'] = np.arctan2(df['rel_lat'], df['rel_lon'])
    return df

def asignar_camiones(df, capacidad_max=500):
    df = preparar_datos(df)
    # Ordenamos por ángulo para que el camión siga una ruta radial lógica
    df = df.sort_values('angulo').reset_index(drop=True)
    
    camiones = []
    camion_actual = []
    carga_actual = 0
    
    for _, pedido in df.iterrows():
        cantidad_pedido = pedido['Cantidad']
        
        # ¿Cabe en el camión actual?
        if carga_actual + cantidad_pedido <= capacidad_max:
            camion_actual.append(pedido.to_dict())
            carga_actual += cantidad_pedido
        else:
            # El camión está lleno, cerramos este grupo y empezamos uno nuevo
            camiones.append(camion_actual)
            camion_actual = [pedido.to_dict()]
            carga_actual = cantidad_pedido
            
    # Añadir el último camión si tiene pedidos
    if camion_actual:
        camiones.append(camion_actual)
        
    
    return camiones

# Límite de tiempo en minutos (8 horas)
MAX_TIEMPO_HOUR = 8.0 

def asignar_camiones_con_tiempo(df, matriz_tiempos, capacidad_max=500):
    df = preparar_datos(df)
    # 1. Ordenar por ángulo (Sweep)
    df = df.sort_values('angulo').reset_index(drop=True)
    
    camiones = []
    camion_actual = []
    carga_actual = 0
    tiempo_ruta_actual = 0
    ultimo_punto = 0  # Índice de Mataró en tu matriz
    
    for _, pedido in df.iterrows():
        id_pedido = pedido['DestinoEntregaID']
        cantidad_pedido = pedido['Cantidad']
        
        # Simular tiempo: De donde estamos al pedido + Regreso a Mataró (0)
        tiempo_ir = matriz_tiempos[ultimo_punto][id_pedido]
        tiempo_volver_base = matriz_tiempos[id_pedido][0]
        
        # Estimación conservadora del tiempo total si añadiéramos este pedido
        posible_tiempo_total = tiempo_ruta_actual + tiempo_ir + tiempo_volver_base
        
        # VALIDACIÓN DOBLE: Capacidad y Tiempo
        if (carga_actual + cantidad_pedido <= capacidad_max) and (posible_tiempo_total <= MAX_TIEMPO_HOUR):
            camion_actual.append(pedido.to_dict())
            carga_actual += cantidad_pedido
            tiempo_ruta_actual += tiempo_ir
            ultimo_punto = id_pedido
        else:
            # Si no cabe por peso o tiempo, el camión vuelve a base y cerramos
            camiones.append(camion_actual)
            
            # Reset para el nuevo camión
            camion_actual = [pedido.to_dict()]
            carga_actual = cantidad_pedido
            # El tiempo del nuevo camión empieza con el trayecto Base -> Primer Pedido
            tiempo_ruta_actual = matriz_tiempos[0][id_pedido]
            ultimo_punto = id_pedido
            
    if camion_actual:
        camiones.append(camion_actual)
        
    return camiones
import pandas as pd
import numpy as np
from sklearn.cluster import KMeans

def kmeans_logistica_robusto(df, capacidad_max, max_iter_balance=50):
    # 1. Preparación y cálculo de K 
    total_carga = df['Cantidad'].sum() 
    k = int(np.ceil(total_carga / capacidad_max)) + 1
    
    # 2. K-Means inicial rápido
    coords = df[['latitude', 'longitude']].values
    kmeans = KMeans(n_clusters=k, random_state=42, n_init=10).fit(coords)
    df['cluster'] = kmeans.labels_
    
    # 3. Reequilibrio con límite de iteraciones
    for _ in range(max_iter_balance):
        clusters_excedidos = []
        for cid in range(k):
            if df[df['cluster'] == cid]['Cantidad'].sum() > capacidad_max:
                clusters_excedidos.append(cid)
        
        if not clusters_excedidos:
            break # Todos los clusters cumplen la capacidad
            
        for cid in clusters_excedidos:
            # Obtener puntos del cluster excedido
            puntos_cluster = df[df['cluster'] == cid]
            # Identificar el punto que más "estorba" (el más lejano al centro)
            centroide = kmeans.cluster_centers_[cid]
            distancias = np.linalg.norm(puntos_cluster[['latitude', 'longitude']].values - centroide, axis=1)
            idx_a_mover = puntos_cluster.index[np.argmax(distancias)]
            
            # Buscar el cluster más cercano que TENGA ESPACIO
            mejor_vecino = -1
            menor_distancia = float('inf')
            
            for vecino_id in range(k):
                if vecino_id == cid: continue
                
                carga_vecino = df[df['cluster'] == vecino_id]['Cantidad'].sum()
                if carga_vecino + df.loc[idx_a_mover, 'Cantidad'] <= capacidad_max:
                    dist = np.linalg.norm(df.loc[idx_a_mover, ['latitude', 'longitude']].values - kmeans.cluster_centers_[vecino_id])
                    if dist < menor_distancia:
                        menor_distancia = dist
                        mejor_vecino = vecino_id
            
            if mejor_vecino != -1:
                df.at[idx_a_mover, 'cluster'] = mejor_vecino
            else:
                # Si no hay ningún vecino con espacio, forzamos la creación de un nuevo cluster (un nuevo camión)
                # Esto rompe el bucle infinito al añadir recursos
                k += 1
                df.at[idx_a_mover, 'cluster'] = k - 1
                # Recalcular centroides (simplificado)
                return kmeans_logistica_robusto(df, capacidad_max) 

    return df