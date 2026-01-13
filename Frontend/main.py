import pandas as pd
import streamlit as st





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


    
    st.set_page_config(page_title="Gestor de rutas", layout="wide")

    # ----------------- CARGAR DATOS -----------------
    pedidos = limpiar_columnas(pd.read_csv("../app/data/pedidos.csv", sep=";"))
    clientes = limpiar_columnas(pd.read_csv("../app/data/clientes.csv", sep=";"))
    destinos = limpiar_columnas(pd.read_csv("../app/data/destinos.csv", sep=";"))
    lineaspedidos = limpiar_columnas(pd.read_csv("../app/data/lineaspedidos.csv", sep=";"))
    productos = limpiar_columnas(pd.read_csv("../app/data/productos.csv", sep=";"))
    provincias = limpiar_columnas(pd.read_csv("../app/data/Provincias.csv", sep=";"))
    
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
    
    
    