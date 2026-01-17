
import time
import streamlit as st
from app.algoritmos import fuerza_bruta, genetico, kmeans

def usar_fuerza_bruta(df_matriz_distancias):
    start = time.time()
    with st.spinner("Calculando rutas...", show_time=True, width="content"):
        rutas = fuerza_bruta.calcular(df_matriz_distancias)
    elapsed = time.time() - start
    st.title(f"Rutas (calculado en {elapsed:.2f} segundos): ")    
    st.dataframe(rutas)
    st.title(f"Rutas generadas y guardadas en app/data/rutas.csv")    
    rutas.to_csv("app/data/rutas.csv", index=False)

def usar_genetica(ruta_temp, df_matriz_tiempos):
    genetico.ejecutar_ag_sin_vuelta(ruta_temp, df_matriz_tiempos)

def usar_genetica_sobrantes(df_sobrantes, matriz_km, matriz_tiempo):
    genetico.algoritmo_genetico(df_sobrantes, matriz_km, matriz_tiempo)

def usar_kmeans(df):    
    return kmeans.crear_clusters_capitados(df)
    #return kmeans.asignar_camiones(df)

def usar_kmeans_tiempos(df, matriz_tiempos):
    return kmeans.asignar_camiones_con_tiempo(df, matriz_tiempos)

def usar_kmeans_restringido(df, capacidad_max):
    return kmeans.kmeans_logistica_robusto(df, capacidad_max)