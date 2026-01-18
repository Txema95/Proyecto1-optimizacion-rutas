import streamlit as st
import pandas as pd
from app.algoritmos import genetico
import app.model_routing.generar_matriz_distancias_tiempos as dist_tiempos
import app.algoritmos.algoritmo as algoritmo
df_pedidos_con_destinos = pd.read_csv("app/data/pedidos_con_destinos.csv")

def obtener_matriz_distancias_tiempos(df):
    return dist_tiempos.get_matrices(df)

def obtener_pedidos_y_ejecutar_algoritmo():
    
    duplicados = df_pedidos_con_destinos.duplicated(subset=['DestinoEntregaID'], keep='first')
    # 2. Guardamos los duplicados en un nuevo DataFrame por si acaso
    df_duplicados = df_pedidos_con_destinos[duplicados].copy()
    # 3. Limpiamos el DataFrame original
    df_pedidos_con_destinos.drop_duplicates(subset=['DestinoEntregaID'], keep='first', inplace=True)

    ruta_temp = df_pedidos_con_destinos['nombre_completo'].tolist()#ejemplo = ['Barcelona', 'Girona', 'Palma', 'Tarragona', 'Lleida', 'Las Palmas'....]
    
    #st.dataframe(df_pedidos_con_destinos)
    df_matriz_distancias, df_matriz_tiempos, mapping = dist_tiempos.get_matrices(df_pedidos_con_destinos)
    #st.dataframe(df_matriz_distancias)
    #st.dataframe(df_matriz_tiempos)
    ruta_temp = list(df_matriz_tiempos)
    #algoritmousar_fuerza_bruta(df_matriz_distancias)
    algoritmo.usar_genetica(ruta_temp, df_matriz_tiempos)
    
def obtener_pedidos_productos_y_fechas():
    if(df_pedidos_con_destinos.empty==False):        
        df_lineas_pedidos = pd.read_csv("app/data/lineaspedidos.csv")
        #df_lineas_pedidos['Cantidad'] = df_lineas_pedidos['Cantidad']*10
        df_productos = pd.read_csv("app/data/productos.csv")
        df_final = (df_pedidos_con_destinos
            .merge(df_lineas_pedidos, on="PedidoID", how="inner")
            .merge(df_productos, on="ProductoID", how="inner"))
        df_final = df_final.drop(["nombre_completo","distancia_km","latitude","longitude","LineaPedidoID","Nombre","PrecioVenta"], axis=1)

        # 1. Convertir a formato fecha (si no lo está ya)
        df_final['FechaPedido'] = pd.to_datetime(df_final['FechaPedido'])

        # 2. Fecha Inicio Fabricación (Día después del pedido)
        df_final['FechaInicioFab'] = df_final['FechaPedido'] + pd.to_timedelta(1, unit='D')

        # 3. Fecha Fin Fabricación (Disponibilidad para envío)
        # Sumamos el tiempo medio a partir del inicio de la fabricación
        df_final['FechaFinFabricacion'] = df_final['FechaInicioFab'] + pd.to_timedelta(df_final['TiempoFabricacionMedio'], unit='D')
        
        # 4. Fecha de Caducidad (Según regla 2.2.1)
        # Fecha Caducidad = Fecha Pedido + Tiempo Fabricación + Días Caducidad
        # Nota: Aquí el enunciado no menciona el "día de espera", 
        # pero por coherencia lógica, la caducidad suele contar desde que el producto existe.
        df_final['FechaCaducidad'] = df_final['FechaPedido'] + pd.to_timedelta(df_final['TiempoFabricacionMedio'], unit='D') + pd.to_timedelta(df_final['Caducidad'], unit='D')
        

        
        # Nuevo orden de tabla
        #nuevo_orden = ['PedidoID', 'ProductoID', 'Cantidad', 'TiempoFabricacionMedio', 'Caducidad', 'DestinoEntregaID', 'FechaPedido','FechaInicioFab', 'FechaFinFabricacion', 'FechaCaducidad']
        #df_final = df_final[nuevo_orden]
        #df_pedidos_ia = df_pedidos_ia[nuevo_orden]

        st.dataframe(df_final)

def genetica_por_camion(destinos_cluster, matriz_tiempos):
    return genetico.algoritmo_genetico_por_camion(destinos_cluster, matriz_tiempos)

def quitar_outlayer(camion,df_matriz_tiempos):
    outlyer = max(camion, key=lambda p: df_matriz_tiempos[0][p['DestinoEntregaID']])
    camion.remove(outlyer)
    return outlyer, camion


if __name__ == "__main__":
    st.title("Model 1 Routing Analysis")
    #obtener_pedidos_y_ejecutar_algoritmo()
    obtener_pedidos_productos_y_fechas()