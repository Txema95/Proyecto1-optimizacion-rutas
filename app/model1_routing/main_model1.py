import streamlit as st
import pandas as pd
import generar_matriz_distancias_tiempos as dist_tiempos
import algoritmos.algoritmo as algoritmo
df_pedidos_con_destinos = pd.read_csv("app/data/pedidos_con_destinos.csv")

def obtener_pedidos_y_ejecutar_algoritmo():
    
    duplicados = df_pedidos_con_destinos.duplicated(subset=['DestinoEntregaID'], keep='first')
    # 2. Guardamos los duplicados en un nuevo DataFrame por si acaso
    df_duplicados = df_pedidos_con_destinos[duplicados].copy()
    # 3. Limpiamos el DataFrame original
    df_pedidos_con_destinos.drop_duplicates(subset=['DestinoEntregaID'], keep='first', inplace=True)

    ruta_temp = df_pedidos_con_destinos['nombre_completo'].tolist()#ejemplo = ['Barcelona', 'Girona', 'Palma', 'Tarragona', 'Lleida', 'Las Palmas'....]
    
    #st.dataframe(df_pedidos_con_destinos)
    df_matriz_distancias, df_matriz_tiempos = dist_tiempos.get_matrices(df_pedidos_con_destinos)
    #st.dataframe(df_matriz_distancias)
    #st.dataframe(df_matriz_tiempos)
    ruta_temp = list(df_matriz_tiempos)
    #algoritmousar_fuerza_bruta(df_matriz_distancias)
    algoritmo.usar_genetica(ruta_temp, df_matriz_tiempos)
    
def obtener_pedidos_productos_y_fechas():
    if(df_pedidos_con_destinos.empty==False):        
        df_lineas_pedidos = pd.read_csv("app/data/lineaspedidos.csv")
        df_productos = pd.read_csv("app/data/productos.csv")
        df_final = (df_pedidos_con_destinos
            .merge(df_lineas_pedidos, on="PedidoID", how="inner")
            .merge(df_productos, on="ProductoID", how="inner"))
        df_final = df_final.drop(["nombre_completo","distancia_km","latitude","longitude","LineaPedidoID","Nombre","PrecioVenta"], axis=1)

        # 1. Convertir a formato fecha (si no lo está ya)
        df_final['FechaPedido'] = pd.to_datetime(df_final['FechaPedido'])

        # 2. creamos fecha de fin fabricación
        df_final['FechaFinFabricacion'] = df_final['FechaPedido'] + pd.to_timedelta(df_final['TiempoFabricacionMedio'], unit='D')

        # 3. creamos fecha de caducidad
        # Usamos pd.to_timedelta para que pandas entienda que son "días"
        df_final['FechaCaducidad'] = df_final['FechaPedido'] + pd.to_timedelta(df_final['TiempoFabricacionMedio'], unit='D') + pd.to_timedelta(df_final['Caducidad'], unit='D')

        # Nuevo orden de tabla
        nuevo_orden = ['PedidoID', 'ProductoID', 'Cantidad', 'TiempoFabricacionMedio', 'Caducidad', 'DestinoEntregaID', 'FechaPedido', 'FechaFinFabricacion', 'FechaCaducidad']
        df_final = df_final[nuevo_orden]

        st.dataframe(df_final)
if __name__ == "__main__":
    st.title("Model 1 Routing Analysis")
    obtener_pedidos_y_ejecutar_algoritmo()
    #obtener_pedidos_productos_y_fechas()