import pandas as pd
import streamlit as st

def main():

    
    st.set_page_config(page_title="Gestor de rutas", layout="wide")

    # ----------------- DATA DE EJEMPLO -----------------
    pedidos_hoy = pd.DataFrame(
        {
            "Pedido": [101, 102, 103, 104],
            "Cliente": ["ACME", "Foo Bar", "Lopez", "Martinez"],
            "Dirección": ["C/ A 1", "C/ B 2", "C/ C 3", "C/ D 4"],
        }
    )

    paradas_ruta = [
        "R1 → N (2 kg)",
        "R1M → L (6 kg)",
        "R2 → P (7 kg)",
    ]

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
                height:300px;            /* prueba 200 para que se note el scroll */
                overflow-y: auto;
                padding-right:10px;
                border: 1px solid #ddd;
                border-radius: 10px;
            ">
            """

        for i, row in pedidos_hoy.iterrows():
            lista_html += f"""
            <div style="
                border:1px solid #ccc;
                border-radius:8px;
                padding:10px;
                margin-bottom:10px;
                background:#fafafa;
            ">
                <b>Pedido:</b> {row['Pedido']}<br>
                <b>Cliente:</b> {row['Cliente']}<br>
                <b>Dirección:</b> {row['Dirección']}
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
                <p>Aquí podrías poner un mapa, un gráfico o cualquier visualización.</p>
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
        for p in paradas_ruta:
            st.write("•", p)







if __name__ == "__main__":
    main()
    