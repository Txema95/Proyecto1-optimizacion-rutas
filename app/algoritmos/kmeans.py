import pandas as pd
import numpy as np
from sklearn.cluster import KMeans
import numpy as np
from sklearn.discriminant_analysis import StandardScaler
from sklearn.preprocessing import StandardScaler

def refinar_clusters_lejanos(df, labels, coordenadas, origen, distancia_minima=0.8):
    """
    Subdivide solo los clusters cuyo centroide está lejos del origen
    
    origen: tuple (lat, lon) de Mataró
    distancia_minima: distancia mínima del centroide al origen para subdividir (en grados)
    """
    nuevos_labels = labels.copy()
    siguiente_label = labels.max() + 1
    origen_array = np.array(origen)
    
    for cluster_id in range(labels.max() + 1):
        mask = labels == cluster_id
        puntos_cluster = coordenadas[mask]
        
        # Calcular centroide del cluster
        centroide = puntos_cluster.mean(axis=0)
        
        # Distancia del centroide al origen
        distancia_al_origen = np.linalg.norm(centroide - origen_array)
        
        print(f"Cluster {cluster_id}: distancia al origen = {distancia_al_origen:.3f}°")
        
        # Solo subdividir si está lejos del origen
        if distancia_al_origen > distancia_minima:
            print(f"  → Subdividiendo cluster {cluster_id} (lejos del origen)")
            sub_kmeans = KMeans(n_clusters=2, random_state=42)
            sub_labels = sub_kmeans.fit_predict(puntos_cluster)
            
            print(f"  → Subgrupo 0: {(sub_labels==0).sum()} puntos")
            print(f"  → Subgrupo 1: {(sub_labels==1).sum()} puntos")
            
            indices_mask = np.where(mask)[0]
            for i, sub_label in enumerate(sub_labels):
                if sub_label == 1:
                    nuevos_labels[indices_mask[i]] = siguiente_label
            
            siguiente_label += 1
        else:
            print(f"  → Cluster {cluster_id} cerca del origen, no se subdivide")
    
    return nuevos_labels

def refinar_clusters_problematicos(df, labels, coordenadas, umbral_distancia=0.5):
    """
    Identifica clusters con alta dispersión y los subdivide
    """
    nuevos_labels = labels.copy()
    siguiente_label = labels.max() + 1
    
    for cluster_id in range(labels.max() + 1):
        mask = labels == cluster_id
        puntos_cluster = coordenadas[mask]
        n_puntos = len(puntos_cluster)
        
        # Calcular dispersión
        centroide = puntos_cluster.mean(axis=0)
        distancias = np.linalg.norm(puntos_cluster - centroide, axis=1)
        dispersion = distancias.mean()
        
        # DEBUG: Imprimir info del cluster
        print(f"Cluster {cluster_id}: {n_puntos} puntos, dispersión={dispersion:.3f}")
        
        # Si la dispersión es alta, subdividir
        if dispersion > umbral_distancia:
            print(f"  → Subdividiendo cluster {cluster_id}")
            sub_kmeans = KMeans(n_clusters=2, random_state=42)
            sub_labels = sub_kmeans.fit_predict(puntos_cluster)
            
            print(f"  → Subgrupo 0: {(sub_labels==0).sum()} puntos")
            print(f"  → Subgrupo 1: {(sub_labels==1).sum()} puntos")
            
            # Reasignar
            indices_mask = np.where(mask)[0]
            for i, sub_label in enumerate(sub_labels):
                if sub_label == 1:
                    nuevos_labels[indices_mask[i]] = siguiente_label
            
            siguiente_label += 1
    
    return nuevos_labels

def analizar_clusters(df, lat_col='latitude', lon_col='longitude', cluster_col='Camion_asignado'):
    analisis = []
    for c_id in df[cluster_col].unique():
        subset = df[df[cluster_col] == c_id]
        
        # Calcular el centroide del cluster
        centroide = subset[[lat_col, lon_col]].mean().values
        
        # Calcular distancias de cada punto a su centroide (Euclidiana simple)
        distancias = np.sqrt(
            (subset[lat_col] - centroide[0])**2 + 
            (subset[lon_col] - centroide[1])**2
        )
        
        analisis.append({
            'cluster_id': c_id,
            'distancia_max': distancias.max(),
            'distancia_media': distancias.mean(),
            'puntos': len(subset)
        })
    
    return pd.DataFrame(analisis)


def crear_clusters_capitados(df, esOutlayer, capacidad_max=1800):
    # 1. Estimar cuántos camiones necesitamos
    total_carga = df['Cantidad'].sum()
    n_clusters = int(np.ceil(total_carga / capacidad_max)) + 1 # Un margen extra
    
    # 2. Clustering geográfico inicial
    scaler = StandardScaler()
    coords_scaled = scaler.fit_transform(df[['latitude', 'longitude']])
    coords = df[['latitude', 'longitude']]
    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10).fit(coords)
    #df['Camion_asignado'] = kmeans.labels_
    #cluster_refinado = refinar_clusters_problematicos(df, kmeans.labels_, coords, umbral_distancia=0.8)
    origen_mataro = (41.5414, 2.4446)
    if(esOutlayer == False):
        labels = refinar_clusters_lejanos(df, kmeans.labels_, coords,origen_mataro, distancia_minima=3.0)
    else:
        labels = kmeans.labels_
    #kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10).fit_predict(coords_scaled)
    #df['Camion_asignado'] = kmeans
    #analisis = analizar_clusters(df)
    df['Camion_asignado'] = labels
    # clusters_a_dividir = analisis[analisis['distancia_max'] > UMBRAL_TOLERANCIA]['cluster_id'].tolist()
    # for c_id in clusters_a_dividir:
    #     subset_idx = df[df['Camion_asignado'] == c_id].index
    #     # Decidimos dinámicamente en cuántos dividir (ej: 2 o 3)
    #     n_subclusters = 3 if analisis.loc[analisis['cluster_id'] == c_id, 'distancia_max'].values[0] > 0.8 else 2
        
    #     sub_kmeans = KMeans(n_clusters=n_subclusters, random_state=42)
    #     df.loc[subset_idx, 'cluster_final'] = [
    #         f"{c_id}_{l}" for l in sub_kmeans.fit_predict(df.loc[subset_idx, coords.columns])
    #     ]
    # 3. Refinar clusters para respetar la capacidad (Heurística Greedy)
    camiones = []
    #pedidos_pendientes = df.sort_values(by='Cantidad', ascending=False).to_dict('records')
    pedidos_pendientes = df.sort_values(by='Camion_asignado').to_dict('records')
    # 1. Agrupamos los datos por camión
    # 1. Agrupar datos por camión
    camiones = {}
    for d in pedidos_pendientes:
        cid = d['Camion_asignado']
        if cid not in camiones:
            camiones[cid] = []
        camiones[cid].append(d)

    # 2. Identificar camiones con exceso y con espacio
    def obtener_totales():
        return {cid: sum(envio['Cantidad'] for envio in envios) for cid, envios in camiones.items()}

    totales = obtener_totales()
    
    # 3. Proceso de reasignación
    for cid_origen, total in totales.items():
        while total > capacidad_max:
            # Extraemos el último pedido del camión excedido
            pedido_a_mover = camiones[cid_origen].pop()
            cantidad_pedido = pedido_a_mover['Cantidad']
            total -= cantidad_pedido            
            # Buscamos un camión que tenga sitio
            movido = False
            # Ordenamos por los que tienen más espacio libre primero
            camiones_ordenados = sorted(camiones.keys(), key=lambda x: sum(p['Cantidad'] for p in camiones[x]))
            
            for cid_destino in camiones_ordenados:
                espacio_libre = capacidad_max - sum(p['Cantidad'] for p in camiones[cid_destino])
                if espacio_libre >= cantidad_pedido:
                    pedido_a_mover['Camion_asignado'] = cid_destino
                    camiones[cid_destino].append(pedido_a_mover)
                    movido = True
                    break
            
            if not movido:
                # Si no hay sitio en ningún camión, lo devolvemos al origen o marcamos error
                camiones[cid_origen].append(pedido_a_mover)
                print(f"Alerta: No hay espacio suficiente para el pedido de {pedido_a_mover['nombre_completo']}")
                break
            
            # Recalculamos totales para la siguiente iteración del while
            totales = obtener_totales()

    # 4. Generar el array final de camiones
    resultado_final = []
    for cid, envios in camiones.items():
        total_final = sum(e['Cantidad'] for e in envios)
        resultado_final.append({
            "camion_id": cid,
            "cantidad_total": total_final,
            "fecha_envio": [e['FechaFinFabricacion'] for e in envios],
            "destinos": [e['nombre_completo'] for e in envios],
            "valido": total_final <= capacidad_max,
            "pedidos": envios
        })
    
    return resultado_final
        

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


def obtener_vecinos_mas_cercanos(ultimo_destino_id, pendientes_df, matriz_tiempos):
    """
    ultimo_destino_id: El ID del último punto visitado.
    pendientes_df: DataFrame con los pedidos que aún no tienen camión.
    matriz_tiempos: Tu matriz de datos.
    """
    distancias = []
    
    for idx, fila in pendientes_df.iterrows():
        destino_id = fila['DestinoEntregaID']
        # Obtenemos el tiempo desde el último punto al vecino
        tiempo = matriz_tiempos[ultimo_destino_id][destino_id]
        distancias.append((destino_id, idx, tiempo))
    
    # Ordenamos por tiempo (el más cercano primero)
    distancias.sort(key=lambda x: x[2])
    
    # Devolvemos solo el ID y el índice del DataFrame para poder borrarlo luego
    return [(d[0], d[1]) for d in distancias]

def calcular_tiempo_estimado(ruta_ids, matriz_tiempos, id_origen=0):
    """
    ruta_ids: Lista de IDs que estamos probando para el cluster actual.
    """
    tiempo_total = 0
    # 1. Tiempo desde el Origen al primer destino
    tiempo_total += matriz_tiempos[id_origen][ruta_ids[0]]
    
    # 2. Tiempo entre paradas consecutivas
    for i in range(len(ruta_ids) - 1):
        tiempo_total += matriz_tiempos[ruta_ids[i]][ruta_ids[i+1]]
        # Añadimos un tiempo fijo de descarga (ej. 15 min = 0.25h)
        tiempo_total += 0.25
        
    # 3. Tiempo de regreso al Origen (Crítico para las 9 horas)
    tiempo_total += matriz_tiempos[ruta_ids[-1]][id_origen]
    
    return tiempo_total
def clustering_por_tiempo_capacidad(df_pedidos, matriz_tiempos, cap_max=1800, tiempo_max=9):
    pendientes = df_pedidos.copy()
    clusters = []
    
    while not pendientes.empty:
        # 1. Tomar una "semilla" (ej. el pedido con caducidad más próxima)
        semilla = pendientes.iloc[0]
        cluster_actual = [semilla['DestinoEntregaID']]
        carga_actual = semilla['Cantidad']
        
        pendientes = pendientes.drop(semilla.name)
        
        # 2. Intentar añadir vecinos cercanos en tiempo
        while True:
            ultimo_destino = cluster_actual[-1]
            # Buscamos en la matriz el destino más cercano al último añadido
            vecinos_ordenados = obtener_vecinos_mas_cercanos(ultimo_destino, pendientes, matriz_tiempos)
            
            se_añadio_alguno = False
            for vecino_id, fila_idx in vecinos_ordenados:
                cantidad_vecino = pendientes.loc[fila_idx, 'Cantidad']
                
                # VALIDACIÓN DE CAPACIDAD
                if carga_actual + cantidad_vecino <= cap_max:
                    # VALIDACIÓN DE TIEMPO (Estimación rápida ida-vuelta)
                    tiempo_estimado = calcular_tiempo_estimado(cluster_actual + [vecino_id], matriz_tiempos)
                    
                    if tiempo_estimado <= tiempo_max:
                        cluster_actual.append(vecino_id)
                        carga_actual += cantidad_vecino
                        pendientes = pendientes.drop(fila_idx)
                        se_añadio_alguno = True
                        break # Salir del for para buscar nuevo vecino desde este nuevo punto
            
            if not se_añadio_alguno:
                break # No caben más pedidos en este camión
                
        clusters.append(cluster_actual)
    
    return clusters