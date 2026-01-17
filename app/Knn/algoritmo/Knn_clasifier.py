import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.neighbors import NearestNeighbors
from sklearn.cluster import KMeans, DBSCAN
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import silhouette_score, calinski_harabasz_score
import os
import glob

class SistemaKNNRutas:
    def __init__(self):
        self.datasets = {}
        self.resultados = {}
        
    def cargar_datasets(self, ruta="app/data"):
        """Carga todos los datasets preparados para K-NN"""
        print("=" * 70)
        print("📂 CARGANDO DATASETS PARA K-NN")
        print("=" * 70)
        
        # Buscar archivos knn_dataset*
        archivos_knn = glob.glob(f"{ruta}/knn_dataset*.csv")
        archivos_knn.extend(glob.glob("knn_dataset*.csv"))  # También en directorio actual
        
        if not archivos_knn:
            print("❌ No se encontraron archivos knn_dataset*.csv")
            print("   Ejecuta primero el script de preparación de datos")
            return False
        
        for archivo in archivos_knn:
            nombre = os.path.basename(archivo).replace('.csv', '')
            try:
                df = pd.read_csv(archivo)
                self.datasets[nombre] = df
                print(f"✓ {nombre}: {len(df)} filas, {len(df.columns)} columnas")
                print(f"  Columnas: {list(df.columns)}")
            except Exception as e:
                print(f"✗ Error cargando {archivo}: {e}")
        
        return len(self.datasets) > 0
    
    def preparar_datos_knn(self, df, columnas_features=None):
        """
        Prepara datos para K-NN:
        - Selecciona columnas numéricas
        - Maneja valores NaN
        - Normaliza datos
        """
        # Hacer copia para no modificar original
        df_procesado = df.copy()
        
        # Si no se especifican columnas, usar todas las numéricas
        if columnas_features is None:
            columnas_features = df_procesado.select_dtypes(include=[np.number]).columns.tolist()
        
        # Excluir columnas de ID si existen
        excluir = ['PedidoID', 'ProductoID', 'LineaPedidoID', 'index']
        columnas_features = [col for col in columnas_features if col not in excluir]
        
        # Verificar que tenemos columnas
        if not columnas_features:
            print("⚠️  No hay columnas numéricas para K-NN")
            return None, None, None
        
        # Seleccionar solo las columnas que existen
        columnas_existentes = [col for col in columnas_features if col in df_procesado.columns]
        
        if not columnas_existentes:
            print(f"⚠️  Ninguna de las columnas {columnas_features} existe en el DataFrame")
            return None, None, None
        
        print(f"  Usando columnas: {columnas_existentes}")
        
        # Extraer features
        X = df_procesado[columnas_existentes].copy()
        
        # Manejar NaN: reemplazar con media o eliminar
        if X.isnull().sum().sum() > 0:
            print(f"  ⚠️  {X.isnull().sum().sum()} valores NaN encontrados")
            # Opción 1: Eliminar filas con NaN
            X = X.dropna()
            # Opción 2: Rellenar con media (comentada)
            # X = X.fillna(X.mean())
        
        if len(X) == 0:
            print("❌ No hay datos válidos después de limpiar NaN")
            return None, None, None
        
        # Normalizar datos
        scaler = StandardScaler()
        X_normalized = scaler.fit_transform(X)
        
        return X_normalized, X, columnas_existentes
    
    def aplicar_knn_clustering(self, dataset_nombre, n_vecinos=5, algoritmo='kmeans', n_clusters=5):
        """
        Aplica K-NN y clustering a un dataset
        """
        print(f"\n🔧 Aplicando K-NN a: {dataset_nombre}")
        
        if dataset_nombre not in self.datasets:
            print(f"❌ Dataset {dataset_nombre} no encontrado")
            return None
        
        df = self.datasets[dataset_nombre]
        
        # Preparar datos
        X_normalized, X_original, columnas_used = self.preparar_datos_knn(df)
        
        if X_normalized is None:
            return None
        
        resultados = {
            'dataset': dataset_nombre,
            'n_muestras': len(X_normalized),
            'n_features': X_normalized.shape[1],
            'columnas_used': columnas_used
        }
        
        # ============================================
        # 1. K-NN: Encontrar vecinos más cercanos
        # ============================================
        print(f"  📐 K-NN con {n_vecinos} vecinos...")
        knn = NearestNeighbors(n_neighbors=min(n_vecinos, len(X_normalized)-1))
        knn.fit(X_normalized)
        
        # Calcular distancias a vecinos
        distances, indices = knn.kneighbors(X_normalized)
        
        # Métrica: distancia promedio a vecinos
        avg_distances = distances.mean(axis=1)
        resultados['knn_avg_distance'] = avg_distances.mean()
        resultados['knn_max_distance'] = avg_distances.max()
        
        # ============================================
        # 2. CLUSTERING basado en K-NN
        # ============================================
        if algoritmo == 'kmeans':
            print(f"  🎯 K-Means con {n_clusters} clusters...")
            clustering = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
            clusters = clustering.fit_predict(X_normalized)
            
            resultados['algoritmo'] = 'kmeans'
            resultados['n_clusters'] = n_clusters
            resultados['inertia'] = clustering.inertia_
            
        elif algoritmo == 'dbscan':
            print("  🎯 DBSCAN clustering...")
            # Calcular epsilon automáticamente a partir de distancias K-NN
            epsilon = np.percentile(distances[:, 1:].flatten(), 50)  # Percentil 50 de distancias
            clustering = DBSCAN(eps=epsilon, min_samples=5)
            clusters = clustering.fit_predict(X_normalized)
            
            n_clusters_real = len(set(clusters)) - (1 if -1 in clusters else 0)
            resultados['algoritmo'] = 'dbscan'
            resultados['n_clusters'] = n_clusters_real
            resultados['epsilon'] = epsilon
        
        # ============================================
        # 3. EVALUAR calidad de clusters
        # ============================================
        if len(set(clusters)) > 1:  # Solo si hay más de 1 cluster
            try:
                silhouette = silhouette_score(X_normalized, clusters)
                calinski = calinski_harabasz_score(X_normalized, clusters)
                
                resultados['silhouette_score'] = silhouette
                resultados['calinski_score'] = calinski
                
                print(f"  📊 Silhouette Score: {silhouette:.3f}")
                print(f"  📊 Calinski-Harabasz Score: {calinski:.1f}")
            except:
                print("  ⚠️  No se pudo calcular métricas de clustering")
        
        # ============================================
        # 4. ANALIZAR clusters
        # ============================================
        df_resultado = X_original.copy()
        df_resultado['cluster'] = clusters
        
        # Estadísticas por cluster
        stats_by_cluster = []
        for cluster_id in sorted(df_resultado['cluster'].unique()):
            cluster_data = df_resultado[df_resultado['cluster'] == cluster_id]
            
            if cluster_id == -1:  # Ruido en DBSCAN
                stats = {
                    'cluster': 'ruido',
                    'tamaño': len(cluster_data),
                    'porcentaje': len(cluster_data) / len(df_resultado) * 100
                }
            else:
                stats = {
                    'cluster': cluster_id,
                    'tamaño': len(cluster_data),
                    'porcentaje': len(cluster_data) / len(df_resultado) * 100
                }
            
            # Estadísticas por columna (solo numéricas)
            for col in X_original.columns:
                if pd.api.types.is_numeric_dtype(cluster_data[col]):
                    stats[f'{col}_mean'] = cluster_data[col].mean()
                    stats[f'{col}_std'] = cluster_data[col].std()
            
            stats_by_cluster.append(stats)
        
        resultados['stats_clusters'] = pd.DataFrame(stats_by_cluster)
        resultados['df_con_clusters'] = df_resultado
        
        # Añadir información del dataset original (IDs)
        if 'PedidoID' in df.columns:
            df_resultado['PedidoID'] = df.iloc[df_resultado.index]['PedidoID'].values
        
        print(f"  ✅ Clusters creados: {len(set(clusters))}")
        print(f"  📈 Distribución: {df_resultado['cluster'].value_counts().to_dict()}")
        
        self.resultados[dataset_nombre] = resultados
        return resultados
    
    def comparar_datasets(self, n_clusters=5):
        """
        Compara el rendimiento de K-NN en diferentes datasets
        """
        print("\n" + "=" * 70)
        print("📊 COMPARANDO DATASETS PARA K-NN")
        print("=" * 70)
        
        comparacion = []
        
        for dataset_nombre in self.datasets.keys():
            print(f"\n🔍 Analizando: {dataset_nombre}")
            
            # Probar con K-Means
            resultado = self.aplicar_knn_clustering(
                dataset_nombre=dataset_nombre,
                n_clusters=n_clusters,
                algoritmo='kmeans'
            )
            
            if resultado:
                comparacion.append({
                    'dataset': dataset_nombre,
                    'n_muestras': resultado['n_muestras'],
                    'n_features': resultado['n_features'],
                    'silhouette': resultado.get('silhouette_score', np.nan),
                    'calinski': resultado.get('calinski_score', np.nan),
                    'inertia': resultado.get('inertia', np.nan),
                    'n_clusters': resultado.get('n_clusters', np.nan)
                })
        
        if comparacion:
            df_comparacion = pd.DataFrame(comparacion)
            print("\n" + "=" * 70)
            print("🏆 RESULTADOS DE COMPARACIÓN")
            print("=" * 70)
            print(df_comparacion.to_string())
            
            # Guardar comparación
            df_comparacion.to_csv("app/data/comparacion_knn_datasets.csv", index=False)
            
            # Recomendar mejor dataset
            if 'silhouette' in df_comparacion.columns:
                mejor_idx = df_comparacion['silhouette'].idxmax()
                mejor_dataset = df_comparacion.loc[mejor_idx, 'dataset']
                print(f"\n🎯 MEJOR DATASET: {mejor_dataset}")
                print(f"   Silhouette Score: {df_comparacion.loc[mejor_idx, 'silhouette']:.3f}")
            
            return df_comparacion
        
        return None
    
    def visualizar_clusters(self, dataset_nombre, save_plots=True):
        """
        Visualiza los clusters resultantes
        """
        if dataset_nombre not in self.resultados:
            print(f"❌ No hay resultados para {dataset_nombre}")
            return
        
        resultado = self.resultados[dataset_nombre]
        df_con_clusters = resultado['df_con_clusters']
        
        print(f"\n🎨 Visualizando clusters para: {dataset_nombre}")
        
        # Configurar estilo
        plt.style.use('seaborn-v0_8-darkgrid')
        fig = plt.figure(figsize=(15, 10))
        
        # 1. Distribución de clusters
        ax1 = plt.subplot(2, 3, 1)
        cluster_counts = df_con_clusters['cluster'].value_counts().sort_index()
        colors = plt.cm.tab20(np.arange(len(cluster_counts)))
        
        bars = ax1.bar(range(len(cluster_counts)), cluster_counts.values, color=colors)
        ax1.set_title(f'Distribución de Clusters\n({dataset_nombre})')
        ax1.set_xlabel('Cluster')
        ax1.set_ylabel('Número de Pedidos')
        
        # Etiquetas en barras
        for bar, count in zip(bars, cluster_counts.values):
            height = bar.get_height()
            ax1.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                    f'{count}', ha='center', va='bottom')
        
        # 2. Scatter plot de las 2 primeras componentes (si hay suficientes features)
        if resultado['n_features'] >= 2:
            ax2 = plt.subplot(2, 3, 2)
            
            # Usar las dos primeras columnas o PCA si hay más de 2 features
            if resultado['n_features'] == 2:
                x_col = resultado['columnas_used'][0]
                y_col = resultado['columnas_used'][1]
                x = df_con_clusters[x_col]
                y = df_con_clusters[y_col]
            else:
                # PCA para reducción dimensional
                from sklearn.decomposition import PCA
                pca = PCA(n_components=2)
                coords = pca.fit_transform(df_con_clusters[resultado['columnas_used']])
                x = coords[:, 0]
                y = coords[:, 1]
                x_col = 'PCA1'
                y_col = 'PCA2'
            
            scatter = ax2.scatter(x, y, c=df_con_clusters['cluster'], cmap='tab20', alpha=0.6)
            ax2.set_title(f'Visualización 2D de Clusters')
            ax2.set_xlabel(x_col)
            ax2.set_ylabel(y_col)
            plt.colorbar(scatter, ax=ax2, label='Cluster')
        
        # 3. Boxplots por cluster para cada variable importante
        variables_importantes = resultado['columnas_used'][:3]  # Primeras 3 variables
        
        for i, var in enumerate(variables_importantes[:3]):  # Máximo 3 variables
            if var in df_con_clusters.columns:
                ax = plt.subplot(2, 3, 4 + i)
                
                # Crear lista de datos por cluster
                data_by_cluster = []
                cluster_labels = []
                
                for cluster_id in sorted(df_con_clusters['cluster'].unique()):
                    if cluster_id == -1:
                        label = 'Ruido'
                    else:
                        label = f'C{cluster_id}'
                    
                    cluster_data = df_con_clusters[df_con_clusters['cluster'] == cluster_id][var]
                    if len(cluster_data) > 0:
                        data_by_cluster.append(cluster_data)
                        cluster_labels.append(label)
                
                if data_by_cluster:
                    box = ax.boxplot(data_by_cluster, labels=cluster_labels, patch_artist=True)
                    
                    # Colores para las cajas
                    colors = plt.cm.tab20(np.arange(len(data_by_cluster)))
                    for patch, color in zip(box['boxes'], colors):
                        patch.set_facecolor(color)
                    
                    ax.set_title(f'Distribución de {var}')
                    ax.set_ylabel(var)
                    ax.tick_params(axis='x', rotation=45)
        
        plt.suptitle(f'Análisis de Clusters - {dataset_nombre}', fontsize=16, y=1.02)
        plt.tight_layout()
        
        if save_plots:
            plt.savefig(f'app/data/visualizacion_clusters_{dataset_nombre}.png', 
                       dpi=300, bbox_inches='tight')
            print(f"  💾 Gráfico guardado: app/data/visualizacion_clusters_{dataset_nombre}.png")
        
        plt.show()
    
    def generar_reporte_rutas(self, dataset_nombre):
        """
        Genera un reporte para el algoritmo genético de rutas
        """
        if dataset_nombre not in self.resultados:
            print(f"❌ No hay resultados para {dataset_nombre}")
            return
        
        resultado = self.resultados[dataset_nombre]
        df_con_clusters = resultado['df_con_clusters']
        
        print("\n" + "=" * 70)
        print("🚚 REPORTE PARA ALGORITMO GENÉTICO DE RUTAS")
        print("=" * 70)
        
        # Asegurar que tenemos PedidoID
        if 'PedidoID' not in df_con_clusters.columns:
            print("⚠️  No hay PedidoID en los datos clusterizados")
            return
        
        # Agrupar pedidos por cluster
        pedidos_por_cluster = df_con_clusters.groupby('cluster')['PedidoID'].apply(list).to_dict()
        
        # Crear archivo para el algoritmo genético
        datos_rutas = []
        
        for cluster_id, pedidos in pedidos_por_cluster.items():
            if cluster_id == -1:
                cluster_nombre = "Ruido"
            else:
                cluster_nombre = f"Cluster_{cluster_id}"
            
            # Obtener datos de estos pedidos
            pedidos_df = df_con_clusters[df_con_clusters['PedidoID'].isin(pedidos)]
            
            # Estadísticas del cluster
            stats = {
                'cluster_id': cluster_id,
                'cluster_nombre': cluster_nombre,
                'n_pedidos': len(pedidos),
                'pedidos': pedidos
            }
            
            # Añadir estadísticas por variable
            for col in ['distancia_km', 'Caducidad', 'TiempoFabricacionMedio']:
                if col in pedidos_df.columns:
                    stats[f'{col}_avg'] = pedidos_df[col].mean()
                    stats[f'{col}_std'] = pedidos_df[col].std()
                    stats[f'{col}_min'] = pedidos_df[col].min()
                    stats[f'{col}_max'] = pedidos_df[col].max()
            
            datos_rutas.append(stats)
        
        # Crear DataFrame
        df_rutas = pd.DataFrame(datos_rutas)
        
        # Guardar reporte
        df_rutas.to_csv("app/data/reporte_rutas_por_cluster.csv", index=False)
        
        # Guardar asignación pedido-cluster
        df_asignacion = df_con_clusters[['PedidoID', 'cluster']].copy()
        df_asignacion.to_csv("app/data/asignacion_pedidos_clusters.csv", index=False)
        
        print(f"\n📋 Reporte generado para {len(datos_rutas)} clusters")
        print(f"📁 Archivos creados:")
        print(f"   • reporte_rutas_por_cluster.csv")
        print(f"   • asignacion_pedidos_clusters.csv")
        
        # Mostrar resumen
        print("\n📊 RESUMEN DE CLUSTERS PARA RUTAS:")
        for _, row in df_rutas.iterrows():
            print(f"\n   {row['cluster_nombre']}:")
            print(f"     • Pedidos: {row['n_pedidos']}")
            if 'distancia_km_avg' in row:
                print(f"     • Distancia promedio: {row['distancia_km_avg']:.1f} km")
            if 'Caducidad_avg' in row:
                print(f"     • Caducidad promedio: {row['Caducidad_avg']:.1f} días")
        
        return df_rutas, df_asignacion

def main():
    """
    Función principal para ejecutar el sistema K-NN completo
    """
    print("\n" + "=" * 70)
    print("🧠 SISTEMA K-NN PARA OPTIMIZACIÓN DE RUTAS")
    print("=" * 70)
    
    # Crear instancia del sistema
    sistema = SistemaKNNRutas()
    
    # 1. Cargar datasets
    if not sistema.cargar_datasets():
        return
    
    # 2. Comparar todos los datasets
    print("\n" + "=" * 70)
    print("🔬 COMPARACIÓN INICIAL DE DATASETS")
    print("=" * 70)
    
    comparacion = sistema.comparar_datasets(n_clusters=5)
    
    if comparacion is None:
        print("❌ No se pudo comparar datasets")
        return
    
    # 3. Preguntar al usuario qué dataset usar
    print("\n" + "=" * 70)
    print("🤔 SELECCIÓN DE DATASET PARA ANÁLISIS DETALLADO")
    print("=" * 70)
    
    print("\n📁 Datasets disponibles:")
    for i, dataset in enumerate(sistema.datasets.keys(), 1):
        print(f"  {i}. {dataset}")
    
    try:
        seleccion = int(input("\nSelecciona el número del dataset a analizar: ")) - 1
        datasets_list = list(sistema.datasets.keys())
        
        if 0 <= seleccion < len(datasets_list):
            dataset_seleccionado = datasets_list[seleccion]
        else:
            print("⚠️  Selección inválida, usando el primero")
            dataset_seleccionado = datasets_list[0]
    except:
        print("⚠️  Entrada inválida, usando el primero")
        dataset_seleccionado = list(sistema.datasets.keys())[0]
    
    # 4. Análisis detallado del dataset seleccionado
    print(f"\n🎯 Analizando dataset: {dataset_seleccionado}")
    
    # Probar diferentes números de clusters
    for n_clusters in [3, 5, 7]:
        print(f"\n🔍 Probando con {n_clusters} clusters...")
        resultado = sistema.aplicar_knn_clustering(
            dataset_nombre=dataset_seleccionado,
            n_clusters=n_clusters,
            algoritmo='kmeans'
        )
        
        if resultado:
            print(f"   Silhouette Score: {resultado.get('silhouette_score', 'N/A')}")
    
    # 5. Visualizar clusters (usando el mejor n_clusters)
    sistema.visualizar_clusters(dataset_seleccionado, save_plots=True)
    
    # 6. Generar reporte para algoritmo genético
    sistema.generar_reporte_rutas(dataset_seleccionado)
    
    print("\n" + "=" * 70)
    print("✅ PROCESO K-NN COMPLETADO")
    print("=" * 70)
    print("\n🎯 Ahora puedes usar los archivos generados para:")
    print("   1. 'asignacion_pedidos_clusters.csv' → Entrada para algoritmo genético")
    print("   2. 'reporte_rutas_por_cluster.csv' → Información de cada cluster")
    print("\n💡 Los pedidos en el mismo cluster deberían asignarse a las mismas rutas")

if __name__ == "__main__":
    # Instalar dependencias si no las tienes:
    # pip install scikit-learn matplotlib seaborn pandas numpy
    
    main()