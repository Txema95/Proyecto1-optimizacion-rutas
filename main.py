import pandas as pd
import streamlit as st
import app.model_optimizer.main_model2 as modelRepartoProductos
import app.model_routing.main_model1 as modelRouting
from app.constantes import FECHA_SIMULACION as fecha_simulacion, ORIGEN as mataro




#Esta funcion limpia los nombres de las columnas
def limpiar_columnas(df):
    df.columns = (
        df.columns
        .str.replace("'", "")      # quita la comilla inicial
        .str.replace('"', "")      # por si acaso
        .str.replace("\ufeff", "") # BOM invisible
        .str.strip()               # quita espacios
    )
    return df

def revisar_datos():

    # ----------------- CARGAR Y LIMPIAR DATOS -----------------
    #pedidos = limpiar_columnas(pd.read_csv("../app/data/pedidos.csv", sep=";"))
    #clientes = limpiar_columnas(pd.read_csv("../app/data/clientes.csv", sep=";"))
    #destinos = limpiar_columnas(pd.read_csv("../app/data/destinos.csv", sep=";"))
    #lineaspedidos = limpiar_columnas(pd.read_csv("../app/data/lineaspedidos.csv", sep=";"))
    #productos = limpiar_columnas(pd.read_csv("../app/data/productos.csv", sep=";"))
    #provincias = limpiar_columnas(pd.read_csv("../app/data/provincias.csv", sep=";"))
    # ----------------- CARGAR Y LIMPIAR DATOS -----------------
    df_pedidos_con_destinos = pd.read_csv("app/data/pedidos_con_destinos.csv")
    if(df_pedidos_con_destinos.empty==False):        
        df_lineas_pedidos = pd.read_csv("app/data/lineaspedidos.csv")
        #df_lineas_pedidos['Cantidad'] = df_lineas_pedidos['Cantidad']*10
        df_productos = pd.read_csv("app/data/productos.csv")
        df_final = (df_pedidos_con_destinos
            .merge(df_lineas_pedidos, on="PedidoID", how="inner")
            .merge(df_productos, on="ProductoID", how="inner"))
        #df_final = df_final.drop(["nombre_completo","distancia_km","latitude","longitude","LineaPedidoID","Nombre","PrecioVenta"], axis=1)
        df_final = df_final.drop(["distancia_km","LineaPedidoID","Nombre","PrecioVenta"], axis=1)

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
        # 5. Agrupamos por destino y fecha en la que terminan de fabricarse
        # (Asumimos que productos listos el mismo día para el mismo sitio se pueden juntar)
        df_agrupado = df_final.groupby(['DestinoEntregaID', 'FechaFinFabricacion', 'nombre_completo', 'latitude','longitude']).agg({
            'Cantidad': 'sum',
            'FechaCaducidad': 'min', # El camión debe cumplir la caducidad más estricta
            'ProductoID': lambda x: ', '.join(x.astype(str).unique()), # Concatena IDs únicos
            
        }).reset_index()
        
        
        return  df_agrupado
    
def get_matrices_distancia_tiempo_mapping(df):
    df_geo = df[['DestinoEntregaID', 'latitude', 'longitude','nombre_completo']].drop_duplicates('DestinoEntregaID')

    df_matriz_distancias, df_matriz_tiempos, mapping = modelRouting.obtener_matriz_distancias_tiempos(df_geo)
    return df_matriz_distancias, df_matriz_tiempos, mapping

def obtener_pedidos_entregables(df, fecha_simulacion, dias_vista):
    fecha_hoy = pd.to_datetime(fecha_simulacion)
    fecha_limite = fecha_hoy + pd.to_timedelta(dias_vista, unit='D')
    
    # 1. Filtramos pedidos que se fabrican como máximo en los próximos X días
    # 2. Y que no hayan caducado para la fecha de salida prevista
    mask = (df['FechaFinFabricacion'] <= fecha_limite) & \
           (df['FechaCaducidad'] > fecha_hoy)
    
    return df[mask].copy()

def procesar_directos_con_matriz(df_directos_hoy, matriz_km, matriz_tiempo,mapping):
    resultados_directos = []
    
    for _, fila in df_directos_hoy.iterrows():
        destino_id = fila['DestinoEntregaID']
        
        # Consultamos nuestra matriz local (sin APIs)
        dist_ida, tiempo_ida = modelRepartoProductos.procesar_pedidos_directos(destino_id, matriz_km, matriz_tiempo,mapping)
        
        # El camión va y vuelve vacío
        dist_total = dist_ida * 2
        
        resultados_directos.append({
            #'PedidoID': fila['PedidoID'],
            'DestinoID': destino_id,
            'Cantidad': fila['Cantidad'],
            'Productos': fila['ProductoID'],
            'Distancia_Km_Total': round(dist_total, 2),
            'Tiempo_Llegada_H': round(tiempo_ida, 2),
            'FechaSalida': fila['FechaFinFabricacion'],
            'FechaCaducidad': fila['FechaCaducidad']
        })
    
    return pd.DataFrame(resultados_directos)

def main():
    st.set_page_config(page_title="Gestor de rutas", layout="wide")
    df_pedidos = revisar_datos()
    df_pedidos_entregables = obtener_pedidos_entregables(df_pedidos, fecha_simulacion,2)
    df_pedidos_entregables = modelRepartoProductos.preparar_unidades_de_carga(df_pedidos_entregables)
    st.dataframe(df_pedidos_entregables)
    #mapping = modelRepartoProductos.index_matriz(df_pedidos_entregables)


    df_matriz_distancias, df_matriz_tiempos, mapping = get_matrices_distancia_tiempo_mapping(df_pedidos_entregables)
    #st.dataframe(df_matriz_distancias)
    st.dataframe(df_matriz_tiempos)
    #pedidos preparados para enviar en fecha_simulacion
    df_pedidos_directos = modelRepartoProductos.pedidos_directos(df_pedidos_entregables, fecha_simulacion)
    
    num_camiones_directos = (len(df_pedidos_directos))
    st.dataframe(df_pedidos_directos)
    resultados_directos = procesar_directos_con_matriz(df_pedidos_directos, df_matriz_distancias, df_matriz_tiempos,mapping)
    st.dataframe(resultados_directos)




    







def main_old():


    
    st.set_page_config(page_title="Gestor de rutas", layout="wide")

    # ----------------- CARGAR DATOS -----------------
    pedidos = limpiar_columnas(pd.read_csv("../app/data/pedidos.csv", sep=";"))
    clientes = limpiar_columnas(pd.read_csv("../app/data/clientes.csv", sep=";"))
    destinos = limpiar_columnas(pd.read_csv("../app/data/destinos.csv", sep=";"))
    lineaspedidos = limpiar_columnas(pd.read_csv("../app/data/lineaspedidos.csv", sep=";"))
    productos = limpiar_columnas(pd.read_csv("../app/data/productos.csv", sep=";"))
    provincias = limpiar_columnas(pd.read_csv("../app/data/provincias.csv", sep=";"))
    
    # info a mostrar
    '''
        Id pedido
        FechaPedido
        Productos
            Producto
            Cantidad
            Fecha caducidad
            Precio
        Cliente
        Nombre destino
    '''
    print(pedidos.columns)
    print(clientes.columns)


    
    
    pedidos_full = (
        pedidos
        .merge(clientes, on="ClienteID")
        .merge(destinos, left_on="DestinoEntregaID", right_on="DestinoID")
    )  
    lineas_full = (
        lineaspedidos
        .merge(productos, on="ProductoID")  # añade el nombre del producto, etc.
    )
    detalle = lineas_full.merge(
        pedidos_full[["PedidoID", "FechaPedido", "nombre", "nombre_completo"]],
        on="PedidoID"
    )
    

    grupos = detalle.groupby("PedidoID")


    # ----------------- LAYOUT -----------------
    st.title("Proyecto 1: Optimizacion de Rutas")

    col_left, col_middle, col_right = st.columns([1, 2, 1])

    # -------- COLUMNA IZQUIERDA (Pedidos) --------
    with col_left:
        st.subheader("Lista de pedidos")
        st.markdown("---")


        # st.dataframe(pedidos_hoy, use_container_width=True)
        
        # Construimos TODO el HTML en una sola variable
        lista_html = """
            <div style="
                height:600px;
                overflow-y: auto;
                padding-right:10px;
                border: 1px solid #ddd;
                border-radius: 10px;
            ">
            """
            
        # for i, row in detalle.iterrows():
        for pedido_id, rows in grupos:
            
            # Datos únicos del pedido
            cliente = rows["nombre"].iloc[0]
            destino = rows["nombre_completo"].iloc[0]
            
            productos_html = ""
            for _, r in rows.iterrows():
                productos_html += f"<li>{r['Nombre']}</li>"
            
            
            
            lista_html += f"""
            <div style="
                border:1px solid #ccc;
                border-radius:8px;
                padding:10px;
                margin-bottom:10px;
                background:#fafafa;
            ">
                <b>Pedido:</b> {pedido_id}<br>
                <b>Cliente:</b> {cliente}<br>
                <b>Dirección:</b> {destino}<br>
                <b>Producto:</b> 
                    <ul>
                        {productos_html}
                    </ul>
                
            </div>
            """

        lista_html += "</div>"

        st.markdown(lista_html, unsafe_allow_html=True)


    # -------- COLUMNA MEDIO (mapa) --------
    with col_middle:
        
        # Contenedor grande (mapa / visualización de ruta)
        st.markdown(
            """
            <div style="border:1px solid #ddd; border-radius:10px; padding:15px; margin:20px 0;">
                <h3 style="margin-top:0;">Mapa / Visualización de ruta</h3>
                <div class ="mapa">
                    <iframe src="https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d13330479.087522231!2d-17.586073735031245!3d35.3429504103601!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0xc42e3783261bc8b%3A0xa6ec2c940768a3ec!2zRXNwYcOxYQ!5e0!3m2!1ses!2ses!4v1765297531897!5m2!1ses!2ses" 
                        width="600" 
                        height="450" 
                        style="border:0;" 
                        allowfullscreen="" 
                        loading="lazy" 
                        referrerpolicy="no-referrer-when-downgrade">
                    </iframe>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


    # -------- COLUMNA DERECHA (contenido principal) --------
    with col_right:
        


        # Lista de paradas de la ruta (abajo)
        st.markdown(
            """
            <div style="border:1px solid #ddd; border-radius:10px; padding:15px;">
                <h3 style="margin-top:0;">Paradas de la ruta</h3>
            </div>
            """,
            unsafe_allow_html=True,
        )
        







if __name__ == "__main__":
    main()
    
    
    