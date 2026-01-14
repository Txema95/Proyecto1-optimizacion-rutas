import pandas as pd
import numpy as np
from app.constantes import ORIGEN as mataro

CAPACIDAD_MAX = 500

def preparar_unidades_de_carga(df):
    registros_finales = []
    
    for _, fila in df.iterrows():
        cantidad_total = fila['Cantidad']
        
        # Generar camiones llenos (Directos)
        while cantidad_total >= CAPACIDAD_MAX:
            nuevo_reg = fila.copy()
            nuevo_reg['Cantidad'] = CAPACIDAD_MAX
            nuevo_reg['Es_Resto'] = False
            registros_finales.append(nuevo_reg)
            cantidad_total -= CAPACIDAD_MAX
        
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
    idx_orig = mapping[id_origen]
    idx_dest = mapping[destino_id]
    
    # Consultamos los valores de IDA
    dist_ida = matriz_km[idx_orig][idx_dest]
    tiempo_ida = matriz_tiempo[idx_orig][idx_dest]
    
    return dist_ida, tiempo_ida

def pedidos_restantes(df):
    return df[df['Es_Resto'] == True]



# Ejecución
#df_preparado = preparar_unidades_de_carga(df_final)

# Separación para el modelo
#df_directos = df_preparado[df_preparado['Es_Resto'] == False]
#df_sobrantes = df_preparado[df_preparado['Es_Resto'] == True].reset_index(drop=True)