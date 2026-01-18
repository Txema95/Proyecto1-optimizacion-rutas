import pandas as pd
import streamlit as st
from streamlit_folium import st_folium
import openrouteservice
import app.constantes as CONST
import os
import sys
import folium
import server 


# Conexion con openroute para calcular rutas
#OPENROUTER_API_KEY = "eyJvcmciOiI1YjNjZTM1OTc4NTExMTAwMDFjZjYyNDgiLCJpZCI6Ijk5MjU0MTEzN2M4ODRiYjM5YzkyODFlNWRjZDRlOWY0IiwiaCI6Im11cm11cjY0In0="
client = openrouteservice.Client(key=CONST.ORS_API_KEY)




# Ruta ABSOLUTA a la raíz del proyecto (carpeta PROYECTO1-OPTIMIZACION-RUTAS)
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from app.database import database




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




def main():

    #Creamos el objeto de la base de datos
    
    # db= database()
    st.set_page_config(page_title="Gestor de rutas", layout="wide")
    
    
    # ----------------- LAYOUT -----------------
    st.title("Proyecto 1: Optimizacion de Rutas")

    col_left, col_middle, col_right = st.columns([1, 2, 1])

        
    camiones = server.obtener_camiones()
    
    # ----------------- CARGAR DATOS -----------------
    pedidos = limpiar_columnas(pd.read_csv("app/data/pedidos.csv", sep=";"))
    clientes = limpiar_columnas(pd.read_csv("app/data/clientes.csv", sep=";"))
    destinos = limpiar_columnas(pd.read_csv("app/data/destinos.csv", sep=";"))
    lineaspedidos = limpiar_columnas(pd.read_csv("app/data/lineaspedidos.csv", sep=";"))
    productos = limpiar_columnas(pd.read_csv("app/data/productos.csv", sep=";"))

    provincias = limpiar_columnas(pd.read_csv("app/data/provincias.csv", sep=";"))
    
    
    '''
    # info a mostrar
        Id pedido
        FechaPedido
        Productos
            Producto
            Cantidad
            Fecha caducidad
            Precio
        Cliente
        Nombre destino
    print(pedidos.columns)
    print(clientes.columns)'''



    
    
    # pedidos_full = (
    #     pedidos
    #     .merge(clientes, on="ClienteID")
    #     .merge(destinos, left_on="DestinoEntregaID", right_on="DestinoID")
    # )  
    # lineas_full = (
    #     lineaspedidos
    #     .merge(productos, on="ProductoID")  # añade el nombre del producto, etc.
    # )
    # detalle = lineas_full.merge(
    #     pedidos_full[["PedidoID", "FechaPedido", "nombre", "nombre_completo"]],
    #     on="PedidoID"
    # )
    

    # grupos = detalle.groupby("PedidoID")


    
    # -------- COLUMNA IZQUIERDA (Pedidos) --------
    
    with col_left:
        st.subheader("Lista de pedidos")
        st.markdown("---")
        


        
        # Construimos Todo el HTML en una sola variable
        lista_html = """
            <div style="
                height:600px;
                overflow-y: auto;
                padding-right:10px;
                border: 1px solid #ddd;
                border-radius: 10px;
            ">
            """
            
        # Añadimos el html de los pedidos
        grupos = camiones[0]
        for pedido_id, rows in grupos:
            
            # Datos únicos del pedido
            cliente = rows["nombre"].iloc[0]
            destino = rows["nombre_completo"].iloc[0]
            productos_html = ""
            
            precioTotal = 0
            diaMinCaducidad = rows['Caducidad'].iloc[0]
            for _, r in rows.iterrows():
            
                if diaMinCaducidad > r['Caducidad']:
                    diaMinCaducidad = r['Caducidad']
            
            
                productos_html += f"""<li>
                    <details style="margin-top:8px;">
                    <summary>
                    <b>{r['Nombre']}:</b></summary>
                    <ul>
                """
                precioTotalProducto = float(r["PrecioVenta"].replace(",", ".")) * float(r["Cantidad"])
                productos_html += f"<li><b>Cantidad: </b>{r['Cantidad']}</li>"
                productos_html += f"<li><b>Precio total: </b>{precioTotalProducto}€</li>"
                productos_html += f"<li><b>Dias en caducar: </b>{r['Caducidad']}</li>"
                precioTotal += precioTotalProducto
                
                productos_html += """
                    </ul>
                    </details>
                    </li>"""

            
            
            
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
                <details style="margin-top:8px;">
                <summary><b>Productos ({len(rows)}):</b></summary>
                    <ul>
                        {productos_html}
                    </ul>
                </details>
                <b>Precio total:</b> {precioTotal}€ <br>
                <b>Dia minimo de caducidad:</b> {diaMinCaducidad} dias<br>
                
            </div>
            """

        lista_html += "</div>"

        st.markdown(lista_html, unsafe_allow_html=True)
        


    # -------- COLUMNA MEDIO (mapa) --------
    with col_middle:
        st.title("Mapa de rutas")
        


        
        
        ubicaciones = [
            {"nombre": "Barcelona", "lat": 41.3874, "lon": 2.1686},
            {"nombre": "Madrid",    "lat": 40.4168, "lon": -3.7038},
            {"nombre": "Valencia",  "lat": 39.4699, "lon": -0.3763},
        ]
        
        coords = [(c["lon"], c["lat"]) for c in ubicaciones]

        

        route = client.directions(
            coordinates=coords,
            profile="driving-car",
            format="geojson"
        )

        # ORS devuelve geometry en (lon, lat). Folium necesita (lat, lon).
        line_lonlat = route["features"][0]["geometry"]["coordinates"]
        line_latlon = [(lat, lon) for lon, lat in line_lonlat]

        # Centro del mapa
        start_lat, start_lon = line_latlon[0]
        m = folium.Map(location=[start_lat, start_lon], zoom_start=13)
        
        points_latlon = [(lat, lon) for lon, lat in coords]

        for i, p in enumerate(points_latlon):
            folium.Marker(
                location=p,
                popup= ubicaciones[i]["nombre"],
                icon=folium.Icon(color="blue" if i not in (0, len(points_latlon)-1) else "red")
            ).add_to(m)
        

        # Marcadores inicio/fin
        # folium.Marker(line_latlon[0], popup="Inicio").add_to(m)
        # folium.Marker(line_latlon[-1], popup="Fin").add_to(m)

        # Ruta
        folium.PolyLine(line_latlon, weight=5, opacity=0.8).add_to(m)

        summary = route["features"][0]["properties"]["summary"]

        km = summary["distance"] / 1000

        
        badge = f"""
        <div style="
            position: fixed;
            top: 20px; left: 20px;
            z-index: 9999;
            font-size: 28px;
            font-weight: 800;
            background: rgba(255,255,255,0.6);
            padding: 6px 10px;
            border-radius: 10px;
            ">
            Km: {km:.2f}
            </div>
            """
        m.get_root().html.add_child(folium.Element(badge))
        st_folium(m, width=700, height=500)
        
        
        
        '''
        

        m = folium.Map(location=[41.3874, 2.1686], zoom_start=12)

        
        
        
        
        
        puntos = [
            [41.3874, 2.1686],  # Barcelona
            [41.3809, 2.1228],  # ejemplo punto 2
            [41.4036, 2.1744],  # ejemplo punto 3
        ]

        m = folium.Map(location=puntos[0], zoom_start=12)

        # marcadores (opcional)
        for p in puntos:
            folium.Marker(p).add_to(m)

        # la ruta (línea)
        folium.PolyLine(puntos, weight=5, opacity=0.8).add_to(m)

        m.save("ruta.html")
        
        
        folium.Marker([41.3874, 2.1686], popup="Barcelona").add_to(m)

        st_folium(m, width=700, height=500)
        '''
        
        
        
        
        
        
        
        
        
        
        '''
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
        )'''




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
    
    
    