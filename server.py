import pandas as pd
import streamlit as st
import app.model_optimizer.main_model2 as modelRepartoProductos
import app.model_routing.main_model1 as modelRouting
from app.camiones.Camiones import Camion 
from app.constantes import FECHA_SIMULACION as fecha_simulacion, ORIGEN as mataro, CAPACIDAD_MAXIMA
import time
import matplotlib.pyplot as plt
import plotly.express as px



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

def pedidos_con_fecha_entrga():

    df_pedidos_con_destinos = pd.read_csv("app/data/pedidos_con_destinos.csv")
    if(df_pedidos_con_destinos.empty==False):        
        df_lineas_pedidos = pd.read_csv("app/data/lineaspedidos.csv")
        df_productos = pd.read_csv("app/data/productos.csv")
        df_final = (df_pedidos_con_destinos
            .merge(df_lineas_pedidos, on="PedidoID", how="inner")
            .merge(df_productos, on="ProductoID", how="inner"))
        df_final = df_final.drop(["distancia_km","LineaPedidoID"], axis=1)

        # 1. Convertir a formato fecha (si no lo está ya)
        df_final['FechaPedido'] = pd.to_datetime(df_final['FechaPedido'])

        # 2. Fecha Inicio Fabricación (Día después del pedido)
        df_final['FechaInicioFab'] = df_final['FechaPedido'] + pd.to_timedelta(1, unit='D')

        # 3. Fecha Fin Fabricación (Disponibilidad para envío)
        # Sumamos el tiempo medio a partir del inicio de la fabricación
        df_final['FechaFinFabricacion'] = df_final['FechaInicioFab'] + pd.to_timedelta(df_final['TiempoFabricacionMedio'], unit='D')
        
        # 4. Fecha de Caducidad 
        # Fecha Caducidad = Fecha Pedido + Tiempo Fabricación + Días Caducidad
        # Nota: Aquí el enunciado no menciona el "día de espera", 
        # pero por coherencia lógica, la caducidad suele contar desde que el producto existe.
        df_final['FechaCaducidad'] = df_final['FechaFinFabricacion'] + pd.to_timedelta(df_final['Caducidad'], unit='D')
        df_final['CantidadesIndividuales'] = df_final['Cantidad']
        df_agrupado = df_final.groupby(['FechaFinFabricacion','DestinoEntregaID']).agg({
            'Cantidad': 'sum',
            'CantidadesIndividuales': lambda x: ', '.join(x.astype(str)),
            'latitude': 'first',
            'longitude': 'first',
            'nombre_completo': 'first',
            'FechaCaducidad': 'min', # El camión debe cumplir la caducidad más estricta
            'ProductoID': lambda x: ', '.join(x.astype(str).unique()), # Concatena IDs únicos
            'Nombre': lambda x: ', '.join(x.astype(str).unique()), # Concatena IDs únicos
            'PrecioVenta': lambda x: ', '.join(x.astype(str).unique()), # Concatena IDs únicos
            'Caducidad': lambda x: ', '.join(x.astype(str).unique()), # Concatena IDs únicos
                        
        }).reset_index()
        
        df_agrupado.sort_values(by=['FechaFinFabricacion'], inplace=True)
        
        return  df_agrupado

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
        df_final['FechaCaducidad'] = df_final['FechaFinFabricacion'] + pd.to_timedelta(df_final['Caducidad'], unit='D')
        # 5. Agrupamos por destino y fecha en la que terminan de fabricarse
        # (Asumimos que productos listos el mismo día para el mismo sitio se pueden juntar)
        df_agrupado = df_final.groupby(['DestinoEntregaID', 'FechaFinFabricacion', 'nombre_completo', 'latitude','longitude']).agg({
            'Cantidad': 'sum',
            'FechaCaducidad': 'min', # El camión debe cumplir la caducidad más estricta
            'ProductoID': lambda x: ', '.join(x.astype(str).unique()), # Concatena IDs únicos            
        }).reset_index()
        
        
        df_agrupado.sort_values(by=['FechaFinFabricacion'], inplace=True)
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
    #mask = (df['FechaFinFabricacion'] <= fecha_limite) & \
    #       (df['FechaCaducidad'] > fecha_hoy)
    mask = (df['FechaFinFabricacion'] == fecha_hoy)
    
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

def obtener_camiones():
    #agrupamos pedidos por fecha de fabricación (pedidos listos para enviar) y destino
    df_pedidos = pedidos_con_fecha_entrga()
    #obtenemos los pedidos listos para entrar en la fecha_simulacion
    
    df_pedidos.to_csv("productos_fabricados.csv", index=False)    
    if 'fecha_usuario' in st.session_state:
        fecha = str(st.session_state.fecha_usuario)
    else:
        fecha = fecha_simulacion
    df_pedidos_entregables = obtener_pedidos_entregables(df_pedidos, fecha,1)    
    #existe algun pedido que de por si llene un camion? -> prepara_unidades_de_carga -> si es_resto=false ese pedido se puede enviar a su destino
    df_pedidos_entregables = modelRepartoProductos.preparar_unidades_de_carga(df_pedidos_entregables)
    #obtenemos matrices de tiempo y distancia
    df_matriz_distancias, df_matriz_tiempos, mapping = get_matrices_distancia_tiempo_mapping(df_pedidos_entregables)
    #obtenemos pedidos es_resto = false -> pedidos para enviar directamente
    df_pedidos_directos = modelRepartoProductos.pedidos_directos(df_pedidos_entregables, fecha_simulacion)
    #obtenemos pedidos es_resto = true -> pedidos para optimizar
    pedidos_restantes = modelRepartoProductos.pedidos_restantes(df_pedidos_entregables, fecha_simulacion)
    #sacar los outlayers de nuestros pedidos (aquellos cuyas rutas al destino sean mayor de una jornada laboral)
    pedidos_restantes, outlayers = modelRepartoProductos.obtener_outlayers(pedidos_restantes, df_matriz_tiempos)
    #obtener K o num camiones
    if(pedidos_restantes.empty == False):
        camiones = modelRepartoProductos.ejecutar_kmeans(pedidos_restantes, esOutlayer=False)
        #calculamos mejor ruta de destinos por camion
        flota_camiones = []
        llenar_flota_camiones(camiones,flota_camiones,df_matriz_tiempos,esOutlayer=False,esDirecto=False)
        if(df_pedidos_directos.empty == False):
            llenar_flota_camiones(df_pedidos_directos,flota_camiones,df_matriz_tiempos,esOutlayer=False,esDirecto=True)            
        if(len(outlayers)>0):        
            camiones = modelRepartoProductos.ejecutar_kmeans(outlayers,esOutlayer = True)
            llenar_flota_camiones(camiones,flota_camiones,df_matriz_tiempos,esOutlayer=True,esDirecto=False)
        print("FLOTA DE CAMIONES LLENA!")
    else:
        flota_camiones = []
    return flota_camiones
def obtener_rutas(rutas_id, pedidos):

    df_destinos = pd.read_csv("app/data/destinos.csv")
    destinos = []
    for ruta in rutas_id:
        destino = df_destinos.loc[df_destinos['DestinoID'] == ruta]
        for pedido in pedidos:
            if pedido['DestinoEntregaID'] == ruta:
                destino['latitude'] = pedido['latitude']
                destino['longitude'] = pedido['longitude']
        destinos.append(destino)
    return destinos

def llenar_flota_camiones (camiones,flota_camiones,df_matriz_tiempos,esOutlayer, esDirecto):
    
    for i,camion in enumerate(camiones): 
        destinos_cluster = [pedido['DestinoEntregaID'] for pedido in camion['pedidos']]
        if(len(destinos_cluster)>1 and esDirecto == False):
            mejor_ruta = modelRouting.genetica_por_camion(destinos_cluster, df_matriz_tiempos)
        else:
            mejor_ruta = (df_matriz_tiempos[0][camion['pedidos'][0]['DestinoEntregaID']],[int(camion['pedidos'][0]['DestinoEntregaID']),0])

                 

        camion_main = Camion(id_camion=camion['camion_id'],
            peso_maximo=int(CAPACIDAD_MAXIMA),
            peso_ocupado=camion['cantidad_total'],
            fecha_salida=camion['fecha_envio'],
            pedidos=camion['pedidos'],
            tiempo_ruta=round(float(mejor_ruta[0]),2),
            ruta=obtener_rutas(mejor_ruta[1], camion['pedidos']),
            dias_viaje=2 if esOutlayer == True else 1,
            es_especial= 1 if esOutlayer==True else 0)
        flota_camiones.append(camion_main)



def main():
    #df_pedidos = revisar_datos()
    df_pedidos = pedidos_con_fecha_entrga()
    df_pedidos.to_csv("productos_fabricados.csv", index=False)    
    df_pedidos_entregables = obtener_pedidos_entregables(df_pedidos, fecha_simulacion,1)
    df_pedidos_entregables = modelRepartoProductos.preparar_unidades_de_carga(df_pedidos_entregables)
    #mapping = modelRepartoProductos.index_matriz(df_pedidos_entregables)


    df_matriz_distancias, df_matriz_tiempos, mapping = get_matrices_distancia_tiempo_mapping(df_pedidos_entregables)
    #pedidos preparados para enviar en fecha_simulacion
    df_pedidos_directos = modelRepartoProductos.pedidos_directos(df_pedidos_entregables, fecha_simulacion)
    
    num_camiones_directos = (len(df_pedidos_directos))
    
    pedidos_restantes = modelRepartoProductos.pedidos_restantes(df_pedidos_entregables, fecha_simulacion)
    pedidos_restantes, outlayers = modelRepartoProductos.obtener_outlayers(pedidos_restantes, df_matriz_tiempos)
    inicio = time.time()
    camiones = modelRepartoProductos.ejecutar_kmeans(pedidos_restantes)

    #camiones = modelRepartoProductos.ejecutar_kmeans_tiempos(pedidos_restantes,df_matriz_tiempos)
    #camiones = modelRepartoProductos.clustering_por_tiempo_capacidad(pedidos_restantes, df_matriz_tiempos)
    outlayers = []
    for i, camion in enumerate(camiones):        
        destinos_cluster = [pedido['DestinoEntregaID'] for pedido in camion['pedidos']]
        mejor_ruta = modelRouting.genetica_por_camion(destinos_cluster, df_matriz_tiempos)
        # if(mejor_ruta[0]> 9):
        #     outlayer, camion = modelRouting.quitar_outlayer(camion,df_matriz_tiempos)            
        #     destinos_cluster = [pedido['DestinoEntregaID'] for pedido in camion['pedidos']]
        #     outlayers.append(outlayer)
        #     mejor_ruta = modelRouting.genetica_por_camion(destinos_cluster, df_matriz_tiempos)
    # modelRepartoProductos.ejecutar_optimización_sobrantes(pedidos_restantes, df_matriz_distancias, df_matriz_tiempos)
    pedidos_restantes.to_csv("app/data/pedidos_restantes_ia.csv", index=False)
    df_matriz_distancias.to_csv("app/data/matriz_distancias.csv", index=False)
    fin = time.time()
    tiempo_total = fin - inicio


if __name__ == "__main__":
    main()
    
    
    