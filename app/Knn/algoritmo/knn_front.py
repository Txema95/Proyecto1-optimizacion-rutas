import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.figure_factory as ff
from sklearn.preprocessing import StandardScaler
from sklearn.neighbors import NearestNeighbors
from sklearn.cluster import KMeans
import os
import glob

# Configuración de la página
st.set_page_config(
    page_title="K-NN para Optimización de Rutas",
    page_icon="🚚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Título principal
st.title("🚚 K-NN para Optimización de Rutas de Entrega")
st.markdown("---")

class VisualizadorKNNStreamlit:
    def __init__(self):
        self.datasets = {}
        self.df_seleccionado = None
        self.resultados_clustering = None
        
    def cargar_datasets(self):
        """Carga los datasets disponibles"""
        with st.spinner("Buscando datasets..."):
            archivos_knn = glob.glob("app/data/knn_dataset*.csv")
            archivos_knn.extend(glob.glob("knn_dataset*.csv"))
            
            if not archivos_knn:
                st.error("❌ No se encontraron archivos knn_dataset*.csv")
                st.info("Ejecuta primero el script de preparación de datos")
                return False
            
            for archivo in archivos_knn:
                nombre = os.path.basename(archivo).replace('.csv', '')
                try:
                    df = pd.read_csv(archivo)
                    self.datasets[nombre] = df
                except Exception as e:
                    st.warning(f"Error cargando {archivo}: {e}")
            
            return len(self.datasets) > 0
    
    def sidebar_seleccion_datos(self):
        """Sidebar para seleccionar dataset y parámetros"""
        with st.sidebar:
            st.header("⚙️ Configuración")
            
            # 1. Seleccionar dataset
            if self.datasets:
                dataset_opciones = list(self.datasets.keys())
                dataset_seleccionado = st.selectbox(
                    "Selecciona el dataset:",
                    options=dataset_opciones,
                    index=0
                )
                
                # Mostrar información del dataset
                df = self.datasets[dataset_seleccionado]
                with st.expander("📊 Información del Dataset"):
                    st.write(f"**Filas:** {len(df):,}")
                    st.write(f"**Columnas:** {len(df.columns)}")
                    st.write("**Columnas disponibles:**")
                    for col in df.columns:
                        st.write(f"- {col}")
                
                self.df_seleccionado = df
                
                # 2. Seleccionar variables para visualización
                st.subheader("📈 Variables para Visualización")
                
                # Variables numéricas
                columnas_numericas = df.select_dtypes(include=[np.number]).columns.tolist()
                excluir = ['PedidoID', 'ProductoID', 'LineaPedidoID', 'index']
                columnas_numericas = [c for c in columnas_numericas if c not in excluir]
                
                if len(columnas_numericas) >= 2:
                    col1, col2 = st.columns(2)
                    with col1:
                        eje_x = st.selectbox(
                            "Eje X:",
                            options=columnas_numericas,
                            index=0
                        )
                    with col2:
                        eje_y = st.selectbox(
                            "Eje Y:",
                            options=columnas_numericas,
                            index=min(1, len(columnas_numericas)-1)
                        )
                else:
                    eje_x = columnas_numericas[0] if columnas_numericas else None
                    eje_y = columnas_numericas[0] if columnas_numericas else None
                
                # 3. Parámetros de K-NN
                st.subheader("🎯 Parámetros K-NN")
                n_clusters = st.slider(
                    "Número de clusters:",
                    min_value=2,
                    max_value=10,
                    value=5
                )
                
                n_vecinos = st.slider(
                    "Número de vecinos (K-NN):",
                    min_value=3,
                    max_value=15,
                    value=5
                )
                
                # 4. Color por
                st.subheader("🎨 Color por")
                color_opciones = ['cluster'] + columnas_numericas
                color_por = st.selectbox(
                    "Color por variable:",
                    options=color_opciones,
                    index=0
                )
                
                # 5. Botón para aplicar K-NN
                aplicar_knn = st.button(
                    "🔍 Aplicar K-NN y Clustering",
                    type="primary",
                    use_container_width=True
                )
                
                return {
                    'dataset': dataset_seleccionado,
                    'eje_x': eje_x,
                    'eje_y': eje_y,
                    'n_clusters': n_clusters,
                    'n_vecinos': n_vecinos,
                    'color_por': color_por,
                    'aplicar_knn': aplicar_knn
                }
            
            return None
    
    def aplicar_knn(self, n_clusters=5, n_vecinos=5):
        """Aplica K-NN y clustering al dataset seleccionado"""
        if self.df_seleccionado is None:
            return None
        
        with st.spinner("Aplicando K-NN y clustering..."):
            df = self.df_seleccionado.copy()
            
            # Seleccionar columnas numéricas
            columnas_numericas = df.select_dtypes(include=[np.number]).columns.tolist()
            excluir = ['PedidoID', 'ProductoID', 'LineaPedidoID', 'index']
            features = [c for c in columnas_numericas if c not in excluir]
            
            if len(features) < 2:
                st.error("Se necesitan al menos 2 variables numéricas")
                return None
            
            # Normalizar datos
            scaler = StandardScaler()
            X = df[features].fillna(df[features].mean())
            X_normalized = scaler.fit_transform(X)
            
            # K-NN: Encontrar vecinos
            knn = NearestNeighbors(n_neighbors=min(n_vecinos, len(X_normalized)-1))
            knn.fit(X_normalized)
            distances, indices = knn.kneighbors(X_normalized)
            
            # K-Means clustering
            kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
            clusters = kmeans.fit_predict(X_normalized)
            
            # Calcular métricas
            from sklearn.metrics import silhouette_score
            silhouette = silhouette_score(X_normalized, clusters)
            
            # Crear DataFrame con resultados
            df_resultado = df.copy()
            df_resultado['cluster'] = clusters
            df_resultado['distancia_promedio_vecinos'] = distances.mean(axis=1)
            
            # Guardar resultados
            self.resultados_clustering = {
                'df': df_resultado,
                'clusters': clusters,
                'kmeans': kmeans,
                'silhouette': silhouette,
                'features': features,
                'indices_vecinos': indices,
                'distancias_vecinos': distances
            }
            
            return self.resultados_clustering
    
    def visualizar_mapa_puntos(self, eje_x, eje_y, color_por='cluster'):
        """Visualización principal: Mapa de puntos interactivo"""
        if self.resultados_clustering is None:
            st.warning("Primero aplica K-NN en la sidebar")
            return
        
        df = self.resultados_clustering['df']
        
        # Crear figura Plotly
        if color_por == 'cluster':
            color_col = 'cluster'
            color_discrete_map = None
            color_continuous_scale = px.colors.qualitative.Set3
        else:
            color_col = color_por
            color_discrete_map = None
            color_continuous_scale = 'Viridis'
        
        fig = px.scatter(
            df,
            x=eje_x,
            y=eje_y,
            color=color_col,
            hover_data=df.columns.tolist(),
            title=f"Mapa de Pedidos - {eje_x} vs {eje_y}",
            color_continuous_scale=color_continuous_scale,
            color_discrete_sequence=px.colors.qualitative.Set3,
            height=600
        )
        
        # Mejorar tooltip
        fig.update_traces(
            hovertemplate="""
            <b>Pedido ID:</b> %{customdata[0]}<br>
            <b>Cluster:</b> %{marker.color}<br>
            <b>""" + eje_x + ":</b> %{x:.2f}<br>" +
            "<b>" + eje_y + ":</b> %{y:.2f}<br>" +
            "<extra></extra>"
        )
        
        # Añadir cuadrícula y mejorar diseño
        fig.update_layout(
            xaxis_title=eje_x,
            yaxis_title=eje_y,
            hovermode='closest',
            showlegend=True,
            legend_title="Clusters" if color_por == 'cluster' else color_por,
            plot_bgcolor='rgba(240, 240, 240, 0.8)',
            paper_bgcolor='rgba(255, 255, 255, 0.9)',
            font=dict(size=12)
        )
        
        # Mostrar en Streamlit
        st.plotly_chart(fig, use_container_width=True)
        
        # Mostrar información del punto seleccionado
        st.subheader("🔍 Información Detallada de Puntos")
        col1, col2 = st.columns(2)
        
        with col1:
            cluster_seleccionado = st.selectbox(
                "Filtrar por cluster:",
                options=sorted(df['cluster'].unique()),
                format_func=lambda x: f"Cluster {x}"
            )
        
        with col2:
            # Mostrar estadísticas del cluster seleccionado
            df_cluster = df[df['cluster'] == cluster_seleccionado]
            st.metric(
                f"Pedidos en Cluster {cluster_seleccionado}",
                f"{len(df_cluster)}",
                f"{len(df_cluster)/len(df)*100:.1f}% del total"
            )
        
        # Tabla con pedidos del cluster seleccionado
        with st.expander(f"📋 Ver pedidos del Cluster {cluster_seleccionado}"):
            columnas_interes = ['PedidoID', eje_x, eje_y, 'cluster']
            if 'distancia_km' in df.columns:
                columnas_interes.append('distancia_km')
            if 'Caducidad' in df.columns:
                columnas_interes.append('Caducidad')
            
            st.dataframe(
                df_cluster[columnas_interes],
                use_container_width=True,
                height=300
            )
    
    def visualizar_vecinos_cercanos(self, pedido_id=None):
        """Visualiza los vecinos más cercanos de un pedido"""
        if self.resultados_clustering is None:
            return
        
        st.subheader("👥 Vecinos Más Cercanos (K-NN)")
        
        df = self.resultados_clustering['df']
        
        # Seleccionar pedido
        if 'PedidoID' in df.columns:
            pedidos_disponibles = df['PedidoID'].unique()
            
            col1, col2 = st.columns([2, 1])
            with col1:
                pedido_seleccionado = st.selectbox(
                    "Selecciona un pedido:",
                    options=pedidos_disponibles[:50],  # Limitar a 50 para rendimiento
                    index=0
                )
            
            with col2:
                n_vecinos_mostrar = st.slider("N° vecinos a mostrar:", 3, 10, 5)
            
            # Encontrar índice del pedido
            idx_pedido = df[df['PedidoID'] == pedido_seleccionado].index[0]
            
            # Obtener vecinos
            indices_vecinos = self.resultados_clustering['indices_vecinos'][idx_pedido]
            distancias_vecinos = self.resultados_clustering['distancias_vecinos'][idx_pedido]
            
            # Crear tabla de vecinos
            vecinos_data = []
            for i, (idx_vecino, distancia) in enumerate(zip(indices_vecinos[1:n_vecinos_mostrar+1], 
                                                           distancias_vecinos[1:n_vecinos_mostrar+1])):
                vecino_info = {
                    'N°': i+1,
                    'PedidoID': df.iloc[idx_vecino]['PedidoID'] if 'PedidoID' in df.columns else idx_vecino,
                    'Cluster': df.iloc[idx_vecino]['cluster'],
                    'Distancia': f"{distancia:.4f}",
                    'Misma Ruta': '✅' if df.iloc[idx_vecino]['cluster'] == df.iloc[idx_pedido]['cluster'] else '❌'
                }
                vecinos_data.append(vecino_info)
            
            # Mostrar tabla
            df_vecinos = pd.DataFrame(vecinos_data)
            st.dataframe(df_vecinos, use_container_width=True)
            
            # Gráfico de conexiones
            fig = go.Figure()
            
            # Punto central (pedido seleccionado)
            fig.add_trace(go.Scatter(
                x=[0],
                y=[0],
                mode='markers',
                marker=dict(size=20, color='red'),
                name='Pedido Seleccionado',
                hoverinfo='text',
                text=f"Pedido {pedido_seleccionado}<br>Cluster: {df.iloc[idx_pedido]['cluster']}"
            ))
            
            # Vecinos
            for i, idx_vecino in enumerate(indices_vecinos[1:n_vecinos_mostrar+1]):
                angulo = 2 * np.pi * i / n_vecinos_mostrar
                x = np.cos(angulo)
                y = np.sin(angulo)
                
                mismo_cluster = df.iloc[idx_vecino]['cluster'] == df.iloc[idx_pedido]['cluster']
                color = 'green' if mismo_cluster else 'blue'
                
                fig.add_trace(go.Scatter(
                    x=[x],
                    y=[y],
                    mode='markers',
                    marker=dict(size=15, color=color),
                    name=f'Vecino {i+1}',
                    hoverinfo='text',
                    text=f"Pedido: {df.iloc[idx_vecino]['PedidoID'] if 'PedidoID' in df.columns else idx_vecino}<br>Cluster: {df.iloc[idx_vecino]['cluster']}<br>Distancia: {distancias_vecinos[i+1]:.4f}"
                ))
                
                # Línea de conexión
                fig.add_trace(go.Scatter(
                    x=[0, x],
                    y=[0, y],
                    mode='lines',
                    line=dict(color='gray', width=1, dash='dash'),
                    showlegend=False,
                    hoverinfo='none'
                ))
            
            fig.update_layout(
                title=f"Vecinos más cercanos del Pedido {pedido_seleccionado}",
                xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                showlegend=True,
                height=400
            )
            
            st.plotly_chart(fig, use_container_width=True)
    
    def mostrar_metricas_clusters(self):
        """Muestra métricas de calidad de los clusters"""
        if self.resultados_clustering is None:
            return
        
        st.subheader("📊 Métricas de Calidad de Clusters")
        
        df = self.resultados_clustering['df']
        silhouette = self.resultados_clustering['silhouette']
        
        # Métricas en columnas
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Silhouette Score", f"{silhouette:.3f}")
        
        with col2:
            n_clusters = len(df['cluster'].unique())
            st.metric("Número de Clusters", n_clusters)
        
        with col3:
            st.metric("Total de Pedidos", len(df))
        
        with col4:
            cluster_balance = df['cluster'].value_counts().std() / df['cluster'].value_counts().mean()
            st.metric("Balance de Clusters", f"{cluster_balance:.3f}")
        
        # Distribución de clusters
        st.subheader("📈 Distribución de Pedidos por Cluster")
        
        cluster_dist = df['cluster'].value_counts().sort_index()
        
        fig_dist = px.bar(
            x=[f"Cluster {i}" for i in cluster_dist.index],
            y=cluster_dist.values,
            labels={'x': 'Cluster', 'y': 'Número de Pedidos'},
            color=cluster_dist.values,
            color_continuous_scale='Blues'
        )
        
        fig_dist.update_traces(
            hovertemplate="<b>%{x}</b><br>Pedidos: %{y}<br><extra></extra>",
            text=cluster_dist.values,
            textposition='outside'
        )
        
        fig_dist.update_layout(
            xaxis_title="Cluster",
            yaxis_title="Número de Pedidos",
            showlegend=False
        )
        
        st.plotly_chart(fig_dist, use_container_width=True)
        
        # Matriz de características por cluster
        st.subheader("🎯 Características Promedio por Cluster")
        
        if 'distancia_km' in df.columns and 'Caducidad' in df.columns:
            features_avg = df.groupby('cluster')[['distancia_km', 'Caducidad']].mean().reset_index()
            
            fig_heatmap = ff.create_annotated_heatmap(
                z=features_avg[['distancia_km', 'Caducidad']].values.T,
                x=[f"Cluster {i}" for i in features_avg['cluster']],
                y=['Distancia (km)', 'Caducidad (días)'],
                colorscale='RdBu',
                annotation_text=features_avg[['distancia_km', 'Caducidad']].values.T.round(1),
                showscale=True
            )
            
            fig_heatmap.update_layout(
                title="Promedio de Características por Cluster",
                height=300
            )
            
            st.plotly_chart(fig_heatmap, use_container_width=True)
    
    def generar_reportes_descarga(self):
        """Genera archivos para descargar"""
        if self.resultados_clustering is None:
            return
        
        st.subheader("💾 Descargar Resultados")
        
        df = self.resultados_clustering['df']
        
        col1, col2 = st.columns(2)
        
        with col1:
            # CSV con clusters
            csv_clusters = df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Descargar Datos con Clusters (CSV)",
                data=csv_clusters,
                file_name="pedidos_con_clusters.csv",
                mime="text/csv",
                use_container_width=True
            )
        
        with col2:
            # Reporte resumido
            if 'PedidoID' in df.columns:
                reporte = df.groupby('cluster').agg({
                    'PedidoID': 'count',
                    'distancia_km': 'mean' if 'distancia_km' in df.columns else None,
                    'Caducidad': 'mean' if 'Caducidad' in df.columns else None
                }).reset_index()
                reporte.columns = ['Cluster', 'N_Pedidos', 'Distancia_Promedio', 'Caducidad_Promedio']
                
                csv_reporte = reporte.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Descargar Reporte de Clusters (CSV)",
                    data=csv_reporte,
                    file_name="reporte_clusters.csv",
                    mime="text/csv",
                    use_container_width=True
                )

def main():
    """Función principal de la aplicación Streamlit"""
    
    # Inicializar visualizador
    visualizador = VisualizadorKNNStreamlit()
    
    # Cargar datasets
    if not visualizador.cargar_datasets():
        st.stop()
    
    # Sidebar
    config = visualizador.sidebar_seleccion_datos()
    
    if config and config['aplicar_knn']:
        # Aplicar K-NN
        resultados = visualizador.aplicar_knn(
            n_clusters=config['n_clusters'],
            n_vecinos=config['n_vecinos']
        )
        
        if resultados:
            # Layout principal
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.success(f"✅ K-NN aplicado exitosamente!")
                st.info(f"**Silhouette Score:** {resultados['silhouette']:.3f}")
            
            with col2:
                if st.button("🔄 Reiniciar Análisis", use_container_width=True):
                    st.rerun()
            
            # Tabs para diferentes visualizaciones
            tab1, tab2, tab3, tab4 = st.tabs([
                "🗺️ Mapa de Puntos", 
                "👥 Vecinos Cercanos", 
                "📊 Métricas", 
                "💾 Descargas"
            ])
            
            with tab1:
                visualizador.visualizar_mapa_puntos(
                    eje_x=config['eje_x'],
                    eje_y=config['eje_y'],
                    color_por=config['color_por']
                )
            
            with tab2:
                visualizador.visualizar_vecinos_cercanos()
            
            with tab3:
                visualizador.mostrar_metricas_clusters()
            
            with tab4:
                visualizador.generar_reportes_descarga()
        else:
            st.error("❌ Error al aplicar K-NN")
    else:
        # Pantalla inicial
        st.markdown("""
        ## 📋 Instrucciones:
        
        1. **Selecciona un dataset** en la barra lateral
        2. **Configura los parámetros** de K-NN
        3. **Haz clic en "Aplicar K-NN y Clustering"**
        4. **Explora los resultados** en las diferentes pestañas
        
        ### 🎯 Objetivo:
        Esta herramienta te ayuda a agrupar pedidos similares usando K-NN
        para optimizar las rutas de entrega de camiones.
        
        Los pedidos en el **mismo cluster** deberían ser entregados en la **misma ruta**.
        """)
        
        # Mostrar datasets disponibles
        with st.expander("📁 Datasets Disponibles", expanded=True):
            for nombre, df in visualizador.datasets.items():
                col1, col2, col3 = st.columns([3, 1, 1])
                with col1:
                    st.write(f"**{nombre}**")
                with col2:
                    st.write(f"{len(df):,} filas")
                with col3:
                    st.write(f"{len(df.columns)} columnas")

if __name__ == "__main__":
    # Instalar dependencias si no las tienes:
    # pip install streamlit plotly scikit-learn
    
    main()