import streamlit as st
import pandas as pd
import numpy as np
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter
import time
import os

def calculate_coordinates(df_destinos):
    
    df_destinos['nombre_completo'] = df_destinos['nombre_completo'].str.replace('Destino ', "España, ")
    geolocator = Nominatim(user_agent="mi_aplicacion_rutas")
    geocode = RateLimiter(geolocator.geocode, min_delay_seconds=1)

    latitudes = []
    longitudes = []

    for index, row in df_destinos.iterrows():
        #if((row['latitude'].isna() or row['latitude']=="") and (row['longitude'].isna() or row['longitude']=="")):            
        #if (pd.isna(row['latitude']) or row['latitude'] == "") and (pd.isna(row['longitude']) or row['longitude'] == ""):
        location = geocode(row['nombre_completo'],featuretype="city")
        if location:
            latitudes.append(location.latitude)
            longitudes.append(location.longitude)
        else:
            latitudes.append(np.nan)
            longitudes.append(np.nan)
        time.sleep(1)  # Para respetar las políticas de uso de Nominatim

    df_destinos['latitude'] = latitudes
    df_destinos['longitude'] = longitudes

    return df_destinos    


def main():
    ORIGEN = 0
    if not os.path.exists("app/data/pedidos_con_destinos.csv"):            
        df_pedidos = pd.read_csv("app/data/pedidos.csv")
        df_destinos = pd.read_csv("app/data/destinos.csv")
        st.write("Calculating coordinates for destinos...")
        df_destinos = calculate_coordinates(df_destinos)
        st.write("Coordinates calculated")
        # Unir tablas usando left join
        df_pedidos_con_destinos = pd.merge(df_pedidos, df_destinos, 
        left_on='DestinoEntregaID', right_on='DestinoID', how='left')
        df_pedidos_con_destinos = df_pedidos_con_destinos.drop(["FechaPedido","provinciaID","ClienteID","coordenadas_gps","DestinoID"], axis=1)
    else:
        df_pedidos_con_destinos = pd.read_csv("app/data/pedidos_con_destinos.csv")
    
    #df_pedidos_con_destinos['distancia_km'] = pd.to_numeric(df_pedidos_con_destinos['distancia_km'], errors='coerce')
    df_pedidos_con_destinos['distancia_km'] = df_pedidos_con_destinos["distancia_km"].str.replace(",", ".", regex=False).astype(float)
    
    df_pedidos_con_destinos.to_csv("app/data/pedidos_con_destinos.csv", index=False)
    #else:
        #df_pedidos_con_destinos = pd.read_csv("app/data/pedidos_con_destinos.csv")



if __name__ == "__main__":        
    main()
