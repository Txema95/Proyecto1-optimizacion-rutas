import app.constantes as CONST
import requests
import pandas as pd
import numpy as np
import time
def get_matrices(df_pedidos_con_destinos):
    
    df_pedidos_con_destinos = pd.concat([pd.DataFrame([CONST.ORIGEN]), df_pedidos_con_destinos], ignore_index=True)

    locations = df_pedidos_con_destinos[['longitude', 'latitude']].values.tolist()
    
    matriz_distancias, matriz_tiempos = obtener_matriz_total(locations)
    
    if len(matriz_distancias)>0  and len(matriz_tiempos)>0:
        # Obtener los nombres de los nodos para las etiquetas de fila y columna
        #names = df_pedidos_con_destinos['nombre_completo'].tolist()
        names = df_pedidos_con_destinos['DestinoEntregaID'].tolist()

        # Crear el DataFrame de Pandas
        df_distance_matrix = pd.DataFrame(matriz_distancias, index=names, columns=names)
        df_time_matrix = pd.DataFrame(matriz_tiempos, index=names, columns=names)

        # Redondear las distancias a un decimal
        df_distance_matrix = df_distance_matrix.round(2)
        df_time_matrix = df_time_matrix.round(2)

        print("\n\n#####################################################")
        print("## 🗺️ MATRIZ DE DISTANCIAS POR CARRETERA (EN KM) 🗺️ ##")
        print("#####################################################")
        
        mapping = {id_dest: i for i, id_dest in enumerate(df_pedidos_con_destinos['DestinoEntregaID'])}
        return df_distance_matrix, df_time_matrix, mapping
    else:
        print("❌ No se pudo generar la matriz. Verifica tu API Key y la conexión a internet.")
        return None
    
def obtener_matriz_total(locations):
    url = CONST.ORS_URL
    n = len(locations)
    MAX_SIZE = 50  # Límite de la API de ORS
    
    # 1. Calcular los rangos de los bloques
    # Si n=120, los indices serian [0, 50, 100, 120]
    indices = list(range(0, n, MAX_SIZE)) + [n]
    bloques_indices = [(indices[i], indices[i+1]) for i in range(len(indices)-1)]
    
    # Inicializar la matriz final con ceros (n x n)
    matriz_final_dist = np.zeros((n, n))
    matriz_final_dur = np.zeros((n, n))

    headers = {
        'Authorization': CONST.ORS_API_KEY,
        'Content-Type': 'application/json; charset=utf-8'
    }

    # 2. Doble bucle para llenar cada bloque de la matriz
    for i_start, i_end in bloques_indices:
        for j_start, j_end in bloques_indices:
            print(f"Calculando bloque: Origen[{i_start}:{i_end}] -> Destino[{j_start}:{j_end}]")
            
            body = {
                "locations": locations,
                "sources": list(range(i_start, i_end)),
                "destinations": list(range(j_start, j_end)),
                "metrics": ["distance", "duration"],
                'units': 'km'             # Pedimos que las unidades sean km
            }

            response = requests.post(url, json=body, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                # Colocar el bloque en la posición correcta de la matriz global
                matriz_final_dist[i_start:i_end, j_start:j_end] = data['distances']
                matriz_final_dur[i_start:i_end, j_start:j_end] = data['durations']
            else:
                print(f"Error en API: {response.text}")
            
            # Pausa para evitar el límite de "solicitudes por minuto" (Rate Limit)
            time.sleep(1.5)
    matriz_final_dur = np.round(matriz_final_dur / 3600, 2)

    return matriz_final_dist, matriz_final_dur
