import constantes as CONST
import requests
import pandas as pd
import numpy as np
def get_matrices(df_pedidos_con_destinos):
    locations = df_pedidos_con_destinos[['longitude', 'latitude']].values.tolist()
    n_nodes = len(locations)
    matriz_distancias, matriz_tiempos = obtener_matriz_distancias_tiempos_ors(locations, CONST.ORS_API_KEY, CONST.ORS_URL)
    if matriz_distancias and matriz_tiempos:
        # Obtener los nombres de los nodos para las etiquetas de fila y columna
        names = df_pedidos_con_destinos['nombre_completo'].tolist()

        # Crear el DataFrame de Pandas
        df_distance_matrix = pd.DataFrame(matriz_distancias, index=names, columns=names)
        df_time_matrix = pd.DataFrame(matriz_tiempos, index=names, columns=names)

        # Redondear las distancias a un decimal
        df_distance_matrix = df_distance_matrix.round(2)
        df_time_matrix = df_time_matrix.round(2)

        print("\n\n#####################################################")
        print("## 🗺️ MATRIZ DE DISTANCIAS POR CARRETERA (EN KM) 🗺️ ##")
        print("#####################################################")
        
        
        # Manejo de casos especiales (Islas)
        print("\n--- NOTA IMPORTANTE SOBRE NODOS AISLADOS (ISLAS) ---")
        print("Las APIs de enrutamiento terrestre (como ORS) fallan o devuelven 'NaN' (Not a Number)")
        print("cuando no hay una ruta continua por carretera.")
        print(f"Verifica las filas/columnas de: {names[3]} (Palma) y {names[6]} (Las Palmas).")
        print("Deberás asignar un costo manual (distancia_terrestre + costo_ferry) a estos enlaces si quieres incluirlos en tu VRP.")
        return df_distance_matrix, df_time_matrix
    else:
        print("❌ No se pudo generar la matriz. Verifica tu API Key y la conexión a internet.")
        return None
    

def obtener_matriz_distancias_tiempos_ors(locations, api_key, url):
    """
    Realiza la llamada a la API de OpenRouteService para obtener la matriz de distancias por carretera.
    """
    headers = {
        'Authorization': api_key,
        'Content-Type': 'application/json'
    }

    # El payload (cuerpo) de la solicitud
    payload = {
        'locations': locations,
        'metrics': ['distance', 'duration'],  # Queremos distancia (por defecto en metros)
        'units': 'km'             # Pedimos que las unidades sean km
    }

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        response.raise_for_status() # Lanza una excepción para códigos de error HTTP (4xx o 5xx)

        data = response.json()
        
        # 'distances' es la clave que contiene la matriz
        matrix_distance_km = data.get('distances') 
        matrix_time_km = ((np.array(data.get('durations')))/3600).tolist()  # Convertir segundos a horas

        if matrix_distance_km and matrix_time_km:
            return matrix_distance_km, matrix_time_km
        else:
            # Manejar errores de ORS que pueden tener código 200 pero fallar internamente
            if 'error' in data:
                 print(f"Error de ORS: {data['error']['message']}")
            return None

    except requests.exceptions.RequestException as e:
        print(f"Error de conexión con la API: {e}")
        return None
