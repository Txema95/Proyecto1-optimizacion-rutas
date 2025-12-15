import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

#Conectar archivo base de datos
import os
import sys

import folium


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
    db= database()
    
    
    st.set_page_config(page_title="Gestor de rutas", layout="wide")

    # ----------------- CARGAR DATOS -----------------
    pedidos = limpiar_columnas(db.select_all('Pedidos'))
    clientes = limpiar_columnas(db.select_all('Clientes'))
    destinos = limpiar_columnas(db.select_all('Destinos'))
    lineaspedidos = limpiar_columnas(db.select_all('LineasPedido'))
    productos = limpiar_columnas(db.select_all('Productos'))
    provincias = limpiar_columnas(db.select_all('Provincias'))
    
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
                precioTotalProducto = float(r["PrecioVenta"]) * float(r["Cantidad"])
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

        m = folium.Map(location=[41.3874, 2.1686], zoom_start=12)
        folium.Marker([41.3874, 2.1686], popup="Barcelona").add_to(m)

        st_folium(m, width=700, height=500)
        
        
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
    
    
    