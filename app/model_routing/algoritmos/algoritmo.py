
import time
import streamlit as st
from app.model_routing.algoritmos import fuerza_bruta, genetico

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