import streamlit as st
import pandas as pd
from constantes import ORIGEN as mataro
import generar_matriz_distancias_tiempos as dist_tiempos
import algoritmos.fuerza_bruta as fuerza_bruta
import time

def main():

    df_pedidos_con_destinos = pd.read_csv("app/data/pedidos_con_destinos.csv")
    df_pedidos_con_destinos = pd.concat([pd.DataFrame([mataro]), df_pedidos_con_destinos], ignore_index=True)
    st.title("Model 1 Routing Analysis")
    st.dataframe(df_pedidos_con_destinos)
    matriz_distancias, matriz_tiempos = dist_tiempos.get_matrices(df_pedidos_con_destinos)
    st.dataframe(matriz_distancias)
    st.dataframe(matriz_tiempos)
    

    
    start = time.time()

    with st.spinner("Calculando rutas...", show_time=True, width="content"):
        rutas = fuerza_bruta.calcular(matriz_distancias)

    elapsed = time.time() - start
    st.title(f"Rutas (calculado en {elapsed:.2f} segundos): ")
    
    st.dataframe(rutas)
    st.title(f"Rutas generadas y guardadas en app/data/rutas.csv")    
    rutas.to_csv("app/data/rutas.csv", index=False)


if __name__ == "__main__":        
    main()
