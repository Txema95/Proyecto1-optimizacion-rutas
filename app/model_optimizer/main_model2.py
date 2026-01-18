import pandas as pd
import numpy as np
from app.constantes import ORIGEN as mataro, CAPACIDAD_MAXIMA
from app.algoritmos import algoritmo


def preparar_unidades_de_carga(df):
    registros_finales = []
    
    for _, fila in df.iterrows():
        cantidad_total = fila['Cantidad']
        
        # Generar camiones llenos (Directos)
        while cantidad_total >= CAPACIDAD_MAXIMA:
            nuevo_reg = fila.copy()
            nuevo_reg['Cantidad'] = CAPACIDAD_MAXIMA
            nuevo_reg['Es_Resto'] = False
            registros_finales.append(nuevo_reg)
            cantidad_total -= CAPACIDAD_MAXIMA
        
        # Generar el sobrante (Para la IA)
        if cantidad_total > 0:
            nuevo_reg = fila.copy()
            nuevo_reg['Cantidad'] = cantidad_total
            nuevo_reg['Es_Resto'] = True
            registros_finales.append(nuevo_reg)
            
    return pd.DataFrame(registros_finales)



def index_matriz(df):
    df_origen = df.copy()
    #df_origen = pd.concat([pd.DataFrame([mataro]), df_origen], ignore_index=True)
    # Mapeo: ID del destino -> Posición en la matriz
    return {id_dest: i for i, id_dest in enumerate(df_origen['DestinoEntregaID'])}

def pedidos_restantes(df, fecha):
    # Filtramos los que NO son resto (son camiones de 500 unidades exactas)
    # Y que ya están fabricados (pueden salir hoy)
    mask_directos = (df['Es_Resto'] == True) & \
                    (df['FechaFinFabricacion'] <= pd.to_datetime(fecha))
    return df[mask_directos].copy()

def pedidos_directos(df, fecha):
    # Filtramos los que NO son resto (son camiones de 500 unidades exactas)
    # Y que ya están fabricados (pueden salir hoy)
    mask_directos = (df['Es_Resto'] == False) & \
                    (df['FechaFinFabricacion'] <= pd.to_datetime(fecha))
    return df[mask_directos].copy()

def procesar_pedidos_directos(destino_id, matriz_km, matriz_tiempo,mapping):
    # El origen (Mataró) siempre suele ser el índice 0 o el ID 0 en tu mapeo
    id_origen = 0 
    
    # Obtenemos los índices de la matriz
    #idx_orig = mapping[id_origen]
    #idx_dest = mapping[destino_id]
    
    # Consultamos los valores de IDA
    dist_ida = matriz_km[id_origen][destino_id]
    tiempo_ida = matriz_tiempo[id_origen][destino_id]

    return dist_ida, tiempo_ida

def obtener_tiempo_desde_mataro(destino_id, matriz_tiempos):

    try:
        return matriz_tiempos[0][destino_id]
    except KeyError:
        # En caso de que el ID no esté en la matriz, marcamos como outlier por precaución
        return float('inf')
    
def obtener_outlayers(df_pedidos, df_matriz_tiempos):

    df_pedidos['tiempo_al_origen'] = df_pedidos['DestinoEntregaID'].apply(obtener_tiempo_desde_mataro, args=(df_matriz_tiempos,))

    # 3. Separamos los Outliers
    # Un pedido es outlier si el viaje de ida (o ida y vuelta) supera el límite
    mask_outliers = df_pedidos['tiempo_al_origen'] > 7.45
    # Nota: He usado limite_horas / 2 asumiendo que el camión debe IR y VOLVER. 
    # Si las 9h son solo de ida, usa: df_pedidos['tiempo_al_origen'] > limite_horas

    df_outliers = df_pedidos[mask_outliers].copy()
    df_actualizado = df_pedidos[~mask_outliers].copy()
    # Limpiamos columnas auxiliares si no las necesitas
    df_actualizado = df_actualizado.drop(columns=['tiempo_al_origen'])

    return df_actualizado, df_outliers

    outlayers = []
    
    for _, fila in df_pedidos.iterrows():
        destino_id = fila['DestinoEntregaID']
        tiempo_viaje = df_matriz_tiempos[0][destino_id]  # Suponiendo que el origen es el índice 0
        if tiempo_viaje > 8:  # Umbral de tiempo en minutos para considerar como outlayer
            outlayers.append(fila)
            df_pedidos = df_pedidos.drop(fila.name)
    return outlayers


def ejecutar_optimización_sobrantes(df_sobrantes, matriz_km, matriz_tiempo):
    algoritmo.usar_genetica_sobrantes(df_sobrantes, matriz_km, matriz_tiempo)

def ejecutar_kmeans(df,esOutlayer):
    return algoritmo.usar_kmeans(df,esOutlayer)
def ejecutar_kmeans_tiempos(df, matriz_tiempos):
    return algoritmo.usar_kmeans_tiempos(df, matriz_tiempos)

def ejecutar_kmeans_restringido(df, capacidad_max):
    return algoritmo.usar_kmeans_restringido(df, capacidad_max)
def clustering_por_tiempo_capacidad(df, matriz_tiempos):
    return algoritmo.clustering_por_tiempo_capacidad(df, matriz_tiempos)
