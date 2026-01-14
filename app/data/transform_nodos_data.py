import pandas as pd
from pandas.api.types import is_string_dtype
import numpy as np
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter
import time
import os

def calculate_coordinates(df_destinos):
    # En lugar de solo reemplazar "Destino " por "España, "
    # Mejorar las queries para provincias específicas
    
    geolocator = Nominatim(user_agent="mi_aplicacion_rutas")
    geocode = RateLimiter(geolocator.geocode, min_delay_seconds=1)

    latitudes = []
    longitudes = []

    for index, row in df_destinos.iterrows():
        nombre = row['nombre_completo']
        
        # Construir query mejorada
        if "Vizcaya" in nombre:
            # Probamos diferentes formatos para Vizcaya
            queries = [
                "Vizcaya, España",
                "Bizkaia, Spain", 
                "Bilbao, España",
                "Provincia de Vizcaya, España"
            ]
        elif "Barcelona" in nombre:
            queries = ["Barcelona, España"]
        elif "La Rioja" in nombre:
    # Para La Rioja, usar la capital Logroño o formato específico
            queries = [
                "Logroño, España",
                "Provincia de La Rioja, España",
                "La Rioja, Spain"
            ]
        # Añadir más casos específicos si es necesario
        else:
            # Para otras provincias: quitar "Destino " y añadir ", España"
            provincia = nombre.replace("Destino ", "")
            queries = [f"{provincia}, España"]
        
        location = None
        for query in queries:
            try:
                location = geocode(query, featuretype="city", timeout=10)
                if location:
                    print(f"Encontrado: {query} → {location.address}")
                    break
            except Exception as e:
                print(f"Error con query '{query}': {e}")
                continue
        
        if location:
            latitudes.append(location.latitude)
            longitudes.append(location.longitude)
        else:
            print(f"No se encontró ubicación para: {nombre}")
            latitudes.append(np.nan)
            longitudes.append(np.nan)
        
        time.sleep(1)  # Respetar rate limit

    df_destinos['latitude'] = latitudes
    df_destinos['longitude'] = longitudes

    return df_destinos

def main():
    if not os.path.exists("app/data/pedidos_con_destinos.csv"):            
        df_pedidos = pd.read_csv("app/data/Pedidos.csv")
        df_destinos = pd.read_csv("app/data/Destinos.csv")
        print("Calculating coordinates for destinos...")
        df_destinos = calculate_coordinates(df_destinos)
        print("Coordinates calculated")
        # Unir tablas usando left join
        df_pedidos_con_destinos = pd.merge(df_pedidos, df_destinos, 
        left_on='DestinoEntregaID', right_on='DestinoID', how='left')
        df_pedidos_con_destinos = df_pedidos_con_destinos.drop(["provinciaID","ClienteID","coordenadas_gps","DestinoID"], axis=1)
    else:
        df_pedidos_con_destinos = pd.read_csv("app/data/pedidos_con_destinos.csv")
    
    #df_pedidos_con_destinos['distancia_km'] = pd.to_numeric(df_pedidos_con_destinos['distancia_km'], errors='coerce')
    if(is_string_dtype(df_pedidos_con_destinos["distancia_km"])):
        df_pedidos_con_destinos['distancia_km'] = df_pedidos_con_destinos["distancia_km"].str.replace(",", ".", regex=False).astype(float)
    
    df_pedidos_con_destinos.to_csv("app/data/pedidos_con_destinos.csv", index=False)

if __name__ == "__main__":        
    main()
