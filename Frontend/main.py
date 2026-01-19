import pandas as pd
import streamlit as st
from streamlit_folium import st_folium
import openrouteservice
import app.constantes as CONST
import os
import sys
import folium
import server 
from datetime import date
import app.constantes as CONST 

# Conexion con openroute para calcular rutas
#OPENROUTER_API_KEY = "eyJvcmciOiI1YjNjZTM1OTc4NTExMTAwMDFjZjYyNDgiLCJpZCI6Ijk5MjU0MTEzN2M4ODRiYjM5YzkyODFlNWRjZDRlOWY0IiwiaCI6Im11cm11cjY0In0="
client = openrouteservice.Client(key=CONST.ORS_API_KEY)




# Ruta ABSOLUTA a la raíz del proyecto (carpeta PROYECTO1-OPTIMIZACION-RUTAS)
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from app.database import database

if 'camiones' not in st.session_state:
    st.session_state.camiones = []

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

def procesar_fecha():
    fecha = st.session_state.fecha_usuario
    st.toast(f"Cargando datos para el día: {fecha}")    
    st.session_state.camiones = server.obtener_camiones()
    if len(st.session_state.camiones)==0:
        st.error("No hay pedidos listos para enviar en la fecha seleccionada.")
# 2. Caché para la API de rutas (¡Muy importante!)
@st.cache_data
def obtener_ruta(coords):
    """Llamada a la API de OpenRouteService"""
    try:
        return client.directions(coordinates=coords, profile='driving-car', format='geojson')
    except Exception as e:
        st.error(f"Error en ruta: {e}")
        return None

def main():
    #Creamos el objeto de la base de datos    
    # db= database()
    st.set_page_config(
        page_title="IA Delivery SL - Optimización de Rutas",
        page_icon="🚚",
        layout="wide"
    )
    st.markdown("""
        <style>
        .camion-card {
            background-color: #f9f9f9;
            border-radius: 10px;
            padding: 20px;
            border-left: 5px solid #007bff;
            margin-bottom: 20px;
            box-shadow: 2px 2px 5px rgba(0,0,0,0.05);
        }
        .etiqueta {
            color: #555;
            font-size: 0.9em;
            font-weight: bold;
        }
        </style>
    """, unsafe_allow_html=True)
    with st.sidebar:
        st.header("Configuración de Flota")
        
        st.date_input(
            "Seleccione fecha de consulta:",
            value=date.today(),
            key="fecha_usuario",  # Es obligatorio para usar on_change
            on_change=procesar_fecha, # Referencia al método
            format="DD/MM/YYYY",
            help="Seleccione una fecha para sincronizar con el servidor de pedidos."
        )
        
        st.divider()
        st.info("Sede Central: Mataró, Barcelona")
    # ----------------- LAYOUT -----------------

    # --- CUERPO PRINCIPAL ---
    st.title("Distribución de Mercancías Perecederas")
    st.markdown("Optimización de rutas peninsulares.")

    # Separador visual
    st.divider()

    cargarHTML()
        
    
def cargarHTML():

    col_pedidos, col_mapa = st.columns([1.5, 4])

    # -------- COLUMNA IZQUIERDA (Pedidos) --------
    
    if 'camiones'  in st.session_state and len(st.session_state.camiones)>0:
        with col_pedidos:
            st.info("### 📋 Pedidos")
                  
            if 'camiones' not in st.session_state:
                st.session_state.camiones = []

            mostrar_listado_camiones()
            
        # -------- COLUMNA MEDIO (mapa) --------
        with col_mapa:
            st.warning("### 🗺️ Mapa de Distribución")
            colores = ['blue', 'green', 'purple', 'orange', 'darkred', 'cadetblue']
            if 'camiones'  in st.session_state and len(st.session_state.camiones)>0:                
                camiones = st.session_state.camiones
                rutas_definidas = []
                
                for i,camion in enumerate(camiones):
                    lista_coords_limpias = []
                    lista_coords_limpias.append([CONST.ORIGEN['longitude'], CONST.ORIGEN['latitude']])
                    for ruta in camion.ruta:
                        if ruta.empty == False:
                            lista_coords_limpias.append([float(ruta['longitude'].to_string(index=False)), float(ruta['latitude'].to_string(index=False))])
                        else:#solo tiene un destino
                             lista_coords_limpias.append([float(camion.pedidos[0]['longitude']), float(camion.pedidos[0]['latitude'])])
                        
                    if len(lista_coords_limpias) >= 2:
                        rutas_definidas.append({
                            "camion": f"Camión: {camion.id_camion+1}", # O el nombre que uses
                            "coords": lista_coords_limpias,
                            "color": colores[i % len(colores)]
                        })
                destinos = []
            else:
                destinos = [
                {"nombre": "Barcelona", "lat": 41.3874, "lon": 2.1686},
                {"nombre": "Madrid",    "lat": 40.4168, "lon": -3.7038},
                {"nombre": "Valencia",  "lat": 39.4699, "lon": -0.3763},
            ]
                

            m = folium.Map(location=[41.38, 2.16], zoom_start=8)
            todas_las_coordenadas = []
            for r in rutas_definidas:
                data_ruta = obtener_ruta(r["coords"])
                
                if data_ruta:
                    # Convertir GeoJSON (Lon, Lat) a Folium (Lat, Lon)
                    line_geom = data_ruta["features"][0]["geometry"]["coordinates"]
                    line_latlon = [[lat, lon] for lon, lat in line_geom]
                    todas_las_coordenadas.extend(line_latlon)
                    
                    # Añadir línea al mapa
                    folium.PolyLine(
                        line_latlon, 
                        color=r["color"], 
                        weight=5, 
                        tooltip=r["camion"]
                    ).add_to(m)

            # Ajustar el zoom automáticamente si hay rutas
            if todas_las_coordenadas:
                m.fit_bounds(todas_las_coordenadas)

            st_folium(m, width=800, height=600)

            

            
    else:
        with col_pedidos:
            st.info("### 📋 Pedidos")
            st.caption("La fecha seleccionada no tiene pedidos listos para enviar.")
            
        with col_mapa:
            st.warning("### 🗺️ Mapa de Distribución")
            st.markdown("""
            Esperando datos...  
            Una vez seleccionada la fecha, aquí se calculará:
            * La ruta de mínima distancia.
            * El reparto de carga por vehículo propio.
            """)
            # Imagen decorativa o esquema de flujo
            st.image("https://img.freepik.com/free-vector/delivery-logistics-concept-flat-design_23-2148249258.jpg", use_container_width=True)

       

def mostrar_productos_compactos(pedido):

    lista_ids = str(pedido['ProductoID']).split(', ')
    lista_nombres = pedido['Nombre'].split(', ')
    lista_precios = str(pedido['PrecioVenta']).split(', ')
    lista_caducidades = str(pedido['Caducidad']).split(', ')
    lista_cantidades = str(pedido['CantidadesIndividuales']).split(', ')

    for p_id, nom, pre, cad, cant in zip(lista_ids, lista_nombres, lista_precios,lista_caducidades, lista_cantidades):
        st.markdown(
            f"""
            <div style="
                border-bottom: 1px solid #ddd; 
                padding: 5px 0px; 
                margin-bottom: 5px;
            ">
                <div style="font-weight: bold; font-size: 0.9rem;">📦 {nom}</div>
                <div style="display: flex; justify-content: space-between; font-size: 0.8rem; color: #666;">
                    <span>Cant: {cant} uds.</span>
                    <span>Precio: {pre}€</span>
                </div>
            </div>
            """, 
            unsafe_allow_html=True
        )

@st.dialog("Detalle del Camión", width="large")
def mostrar_modal_detalle(camion, index):
    """Este es el modal que se abre al hacer clic en un camión"""
    porcentaje_carga = float(camion.peso_ocupado) / float(camion.peso_maximo)
    
    st.markdown(f"### 🚛 Camión #{index + 1}")
    ruta_str=""
    for ruta in camion.ruta:
        if(ruta.empty==False):
            nom_ruta = ruta['nombre_completo'].to_string(index=False).replace("Destino","")
        else:
            nom_ruta = camion.pedidos[0]['nombre_completo'].replace("Destino","")
        ruta_str +=f"- {nom_ruta} "
    st.markdown(f"**📍 Ruta:** {ruta_str}")
    st.divider()
    
    # --- MÉTRICAS DE CARGA ---
    col_a, col_b, col_c = st.columns(3)
    col_a.metric("Peso Ocupado", f"{camion.peso_ocupado} kg")
    col_b.metric("Capacidad Total", f"{camion.peso_maximo} kg")
    col_c.metric("Estado", f"{int(porcentaje_carga*100)}%")
    
    st.write("📊 **Progreso de carga:**")
    st.progress(porcentaje_carga)
    
    st.divider()
    
    # --- LISTADO DE PEDIDOS ---
    st.subheader(f"📦 Pedidos Asignados ({len(camion.pedidos)})")
    for idx, pedido in enumerate(camion.pedidos):
        with st.container(border=True):
            st.markdown(f"**Pedido #{pedido['DestinoEntregaID']} - {pedido['nombre_completo']}**")
            
            c1, c2, c3 = st.columns(3)
            c1.write(f"📅 **Fin Fab:** {pedido['FechaFinFabricacion']}")
            c2.write(f"⚠️ **Caducidad:** {pedido['FechaCaducidad']}")
            c3.write(f"🛒 **Total:** {pedido['Cantidad']} uds.")
            
            st.caption("🔍 Detalle de productos:")
            # Llamamos a tu función de productos compactos
            mostrar_productos_compactos(pedido)

def mostrar_listado_camiones():
    """Listado principal simplificado y clicable"""
    if 'camiones' not in st.session_state or not st.session_state.camiones or len(st.session_state.camiones)==0:
        st.info("No hay camiones disponibles.")
        return
    
    camiones = st.session_state.camiones

    st.subheader(f"🚚 Listado de Flota:\n\n {len(camiones)} Camiones")
    with st.container(height=600): # Altura fija para que no crezca infinitamente
        for i, camion in enumerate(camiones):
            # Usamos una columna para el texto y otra para el botón
            col_txt, col_btn = st.columns([3, 1])            
            with col_txt:
                st.markdown(f"**Camión #{i+1}**")
                ruta_str="Mataro "
                for ruta in camion.ruta:
                    if(ruta.empty==False):
                        nom_ruta = ruta['nombre_completo'].to_string(index=False).replace("Destino","")
                    else:
                        nom_ruta = camion.pedidos[0]['nombre_completo'].replace("Destino","")
                    ruta_str +=f"- {nom_ruta} "
                st.caption(f"📍 {ruta_str} \n\n Duración: {float(camion.tiempo_ruta)} H.")
            
            with col_btn:
                # El botón dispara el modal
                if st.button("Ver Detalle", key=f"btn_{i}", use_container_width=True):
                    mostrar_modal_detalle(camion, i)
            
            st.divider()




if __name__ == "__main__":
    main()
    
    
    