import pandas as pd
import os
import glob
from datetime import datetime
from sklearn.preprocessing import StandardScaler
import numpy as np

def encontrar_archivos():
    """Encuentra todos los archivos CSV necesarios"""
    archivos = {}
    
    archivos_necesarios = [
        "LineasPedidos.csv",
        "Pedidos.csv", 
        "Productos.csv",
        "Destinos.csv",
        "pedidos_con_destinos.csv"
    ]
    
    print("📂 Buscando archivos...")
    
    for archivo in archivos_necesarios:
        # Buscar en diferentes rutas
        rutas_posibles = [
            f"app/data/{archivo}",
            archivo,
            f"*{archivo}*",
            f"*{archivo.lower()}*",
            f"*{archivo.split('.')[0]}*.csv"
        ]
        
        encontrado = False
        for ruta in rutas_posibles:
            resultados = glob.glob(ruta)
            if resultados:
                nombre_clave = archivo.replace('.csv', '')
                archivos[nombre_clave] = resultados[0]
                print(f"✓ {nombre_clave}: {resultados[0]}")
                encontrado = True
                break
        
        if not encontrado:
            print(f"✗ No encontrado: {archivo}")
    
    return archivos

def cargar_y_unificar_datos(archivos):
    """Carga y unifica los datos básicos"""
    print("\n📥 Cargando y unificando datos...")
    
    # Cargar archivos base
    lineas = pd.read_csv(archivos["LineasPedidos"])
    pedidos = pd.read_csv(archivos["Pedidos"])
    productos = pd.read_csv(archivos["Productos"])
    
    # Convertir PrecioVenta a numérico
    if 'PrecioVenta' in productos.columns:
        productos['PrecioVenta'] = pd.to_numeric(
            productos['PrecioVenta'].astype(str).str.replace(',', '.'),
            errors='coerce'
        )
    
    # Cargar destinos (con o sin coordenadas)
    if "pedidos_con_destinos" in archivos:
        destinos = pd.read_csv(archivos["pedidos_con_destinos"])
        print("✓ Usando destinos con coordenadas")
    elif "Destinos" in archivos:
        destinos = pd.read_csv(archivos["Destinos"])
        print("✓ Usando destinos sin coordenadas")
    else:
        raise ValueError("No se encontró archivo de destinos")
    
    # Convertir distancia_km a numérico si existe
    if 'distancia_km' in destinos.columns:
        destinos['distancia_km'] = pd.to_numeric(
            destinos['distancia_km'].astype(str).str.replace(',', '.'),
            errors='coerce'
        )
    
    # ============================================
    # UNIFICACIÓN DE DATOS
    # ============================================
    
    # 1. LineasPedidos + Productos
    df_temp = pd.merge(
        lineas,
        productos,
        left_on="ProductoID",
        right_on="ProductoID",
        how="left",
        suffixes=('', '_producto')
    )
    
    # 2. + Pedidos
    df_temp = pd.merge(
        df_temp,
        pedidos,
        on="PedidoID",
        how="left",
        suffixes=('', '_pedido')
    )
    
    # 3. + Destinos
    # Determinar columna de join para destinos
    if 'DestinoID' in destinos.columns:
        columna_destino = 'DestinoID'
    elif 'DestinoEntregaID' in destinos.columns:
        columna_destino = 'DestinoEntregaID'
    else:
        # Si no hay columna obvia, usar la primera columna numérica
        columna_destino = destinos.columns[0]
    
    # Convertir a string para el join
    df_temp['DestinoEntregaID'] = df_temp['DestinoEntregaID'].astype(str)
    destinos[columna_destino] = destinos[columna_destino].astype(str)
    
    df_unificado = pd.merge(
        df_temp,
        destinos,
        left_on="DestinoEntregaID",
        right_on=columna_destino,
        how="left",
        suffixes=('', '_destino')
    )
    
    print(f"✓ Dataset unificado: {len(df_unificado)} filas, {len(df_unificado.columns)} columnas")
    
    return df_unificado

def calcular_variables_urgencia(df):
    """
    Calcula DIFERENTES versiones de urgencia para comparar
    """
    print("\n🧮 Calculando diferentes medidas de urgencia...")
    
    # Asegurar que tenemos las columnas necesarias
    columnas_necesarias = ['distancia_km', 'Caducidad', 'TiempoFabricacionMedio']
    for col in columnas_necesarias:
        if col not in df.columns:
            print(f"⚠️  Advertencia: Columna '{col}' no encontrada")
    
    # Crear copia para no modificar el original
    df_urgencias = df.copy()
    
    # ============================================
    # VERSIÓN 1: Urgencia solo por caducidad
    # ============================================
    if 'Caducidad' in df_urgencias.columns:
        df_urgencias['Urgencia_1_Caducidad'] = 1 / df_urgencias['Caducidad']
        print("✓ V1: Urgencia basada solo en caducidad (inversa)")
    
    # ============================================
    # VERSIÓN 2: Urgencia solo por distancia
    # ============================================
    if 'distancia_km' in df_urgencias.columns:
        # Normalizar distancia entre 0 y 1
        max_dist = df_urgencias['distancia_km'].max()
        if max_dist > 0:
            df_urgencias['Urgencia_2_Distancia'] = df_urgencias['distancia_km'] / max_dist
            print("✓ V2: Urgencia basada solo en distancia (normalizada)")
    
    # ============================================
    # VERSIÓN 3: Combinación 60% caducidad + 40% distancia
    # ============================================
    if 'Caducidad' in df_urgencias.columns and 'distancia_km' in df_urgencias.columns:
        max_dist = df_urgencias['distancia_km'].max()
        if max_dist > 0:
            df_urgencias['Urgencia_3_Combinada_60_40'] = (
                (1 / df_urgencias['Caducidad']) * 0.6 +
                (df_urgencias['distancia_km'] / max_dist) * 0.4
            )
            print("✓ V3: Combinación 60% caducidad + 40% distancia")
    
    # ============================================
    # VERSIÓN 4: Combinación 40% caducidad + 60% distancia
    # ============================================
    if 'Caducidad' in df_urgencias.columns and 'distancia_km' in df_urgencias.columns:
        max_dist = df_urgencias['distancia_km'].max()
        if max_dist > 0:
            df_urgencias['Urgencia_4_Combinada_40_60'] = (
                (1 / df_urgencias['Caducidad']) * 0.4 +
                (df_urgencias['distancia_km'] / max_dist) * 0.6
            )
            print("✓ V4: Combinación 40% caducidad + 60% distancia")
    
    # ============================================
    # VERSIÓN 5: Urgencia con tiempo de producción
    # ============================================
    if all(col in df_urgencias.columns for col in ['Caducidad', 'distancia_km', 'TiempoFabricacionMedio']):
        max_dist = df_urgencias['distancia_km'].max()
        max_tiempo = df_urgencias['TiempoFabricacionMedio'].max()
        
        if max_dist > 0 and max_tiempo > 0:
            df_urgencias['Urgencia_5_Tres_Factores'] = (
                (1 / df_urgencias['Caducidad']) * 0.5 +
                (df_urgencias['distancia_km'] / max_dist) * 0.3 +
                (df_urgencias['TiempoFabricacionMedio'] / max_tiempo) * 0.2
            )
            print("✓ V5: 50% caducidad + 30% distancia + 20% tiempo producción")
    
    # ============================================
    # VERSIÓN 6: Score logarítmico (penaliza extremos)
    # ============================================
    if 'Caducidad' in df_urgencias.columns and 'distancia_km' in df_urgencias.columns:
        max_dist = df_urgencias['distancia_km'].max()
        if max_dist > 0:
            # Usar logaritmo para suavizar diferencias extremas
            df_urgencias['Urgencia_6_Logaritmica'] = (
                np.log(1 / df_urgencias['Caducidad'] + 1) * 0.7 +
                np.log(df_urgencias['distancia_km'] / max_dist + 1) * 0.3
            )
            print("✓ V6: Score logarítmico (suavizado)")
    df_urgencias.to_csv("test")
    
    return df_urgencias

def crear_datasets_knn(df_urgencias):
    """
    Crea diferentes datasets para probar con K-NN
    """
    print("\n📊 Creando diferentes datasets para K-NN...")
    
    # Columnas base que siempre incluimos
    columnas_base = ['PedidoID', 'ProductoID', 'Cantidad', 'ProvinciaID']
    
    # Añadir columnas disponibles
    columnas_disponibles = []
    for col in ['distancia_km', 'Caducidad', 'TiempoFabricacionMedio', 'latitud', 'longitud']:
        if col in df_urgencias.columns:
            columnas_disponibles.append(col)
    
    # ============================================
    # DATASET 1: Solo variables originales
    # ============================================
    columnas_dataset1 = columnas_base + columnas_disponibles
    df_knn1 = df_urgencias[columnas_dataset1].drop_duplicates().copy()
    df_knn1.to_csv("app/data/knn_dataset1_variables_originales.csv", index=False)
    print("✓ Dataset 1: Variables originales (sin urgencia calculada)")
    
    # ============================================
    # DATASET 2: Con urgencia combinada (60-40)
    # ============================================
    if 'Urgencia_3_Combinada_60_40' in df_urgencias.columns:
        columnas_dataset2 = columnas_base + ['distancia_km', 'Caducidad', 'Urgencia_3_Combinada_60_40']
        df_knn2 = df_urgencias[columnas_dataset2].drop_duplicates().copy()
        df_knn2.to_csv("app/data/knn_dataset2_urgencia_60_40.csv", index=False)
        print("✓ Dataset 2: Con urgencia 60% caducidad + 40% distancia")
    
    # ============================================
    # DATASET 3: Con urgencia combinada (40-60)
    # ============================================
    if 'Urgencia_4_Combinada_40_60' in df_urgencias.columns:
        columnas_dataset3 = columnas_base + ['distancia_km', 'Caducidad', 'Urgencia_4_Combinada_40_60']
        df_knn3 = df_urgencias[columnas_dataset3].drop_duplicates().copy()
        df_knn3.to_csv("app/data/knn_dataset3_urgencia_40_60.csv", index=False)
        print("✓ Dataset 3: Con urgencia 40% caducidad + 60% distancia")
    
    # ============================================
    # DATASET 4: Con todas las urgencias
    # ============================================
    # Buscar todas las columnas de urgencia
    columnas_urgencia = [col for col in df_urgencias.columns if col.startswith('Urgencia_')]
    if columnas_urgencia:
        columnas_dataset4 = columnas_base + columnas_disponibles + columnas_urgencia
        df_knn4 = df_urgencias[columnas_dataset4].drop_duplicates().copy()
        df_knn4.to_csv("app/data/knn_dataset4_todas_urgencias.csv", index=False)
        print(f"✓ Dataset 4: Con todas las urgencias ({len(columnas_urgencia)} versiones)")
    
    # ============================================
    # DATASET 5: Normalizado para K-NN
    # ============================================
    if 'distancia_km' in df_urgencias.columns and 'Caducidad' in df_urgencias.columns:
        columnas_para_normalizar = ['distancia_km', 'Caducidad']
        if 'TiempoFabricacionMedio' in df_urgencias.columns:
            columnas_para_normalizar.append('TiempoFabricacionMedio')
        
        df_knn5 = df_urgencias[columnas_base + columnas_para_normalizar].drop_duplicates().copy()
        
        # Normalizar
        scaler = StandardScaler()
        df_knn5_normalizado = df_knn5.copy()
        df_knn5_normalizado[columnas_para_normalizar] = scaler.fit_transform(df_knn5[columnas_para_normalizar])
        
        df_knn5.to_csv("app/data/knn_dataset5_sin_normalizar.csv", index=False)
        df_knn5_normalizado.to_csv("app/data/knn_dataset5_normalizado.csv", index=False)
        print("✓ Dataset 5: Normalizado y sin normalizar")
    
    # ============================================
    # DATASET 6: Solo para análisis (compacto)
    # ============================================
    columnas_analisis = ['PedidoID', 'distancia_km', 'Caducidad']
    if 'TiempoFabricacionMedio' in df_urgencias.columns:
        columnas_analisis.append('TiempoFabricacionMedio')
    
    # Añadir todas las urgencias calculadas
    columnas_urgencia = [col for col in df_urgencias.columns if col.startswith('Urgencia_')]
    columnas_analisis.extend(columnas_urgencia)
    
    df_analisis = df_urgencias[columnas_analisis].drop_duplicates().copy()
    df_analisis.to_csv("app/data/analisis_comparativo_urgencias.csv", index=False)
    print("✓ Dataset análisis: Tabla comparativa de todas las urgencias")

def mostrar_resumen(df_urgencias):
    """Muestra un resumen de las urgencias calculadas"""
    print("\n" + "=" * 70)
    print("📈 RESUMEN DE URGENCIAS CALCULADAS")
    print("=" * 70)
    
    # Columnas de urgencia
    columnas_urgencia = [col for col in df_urgencias.columns if col.startswith('Urgencia_')]
    
    if not columnas_urgencia:
        print("⚠️  No se calcularon urgencias")
        return
    
    print(f"\nSe calcularon {len(columnas_urgencia)} medidas de urgencia:")
    
    for urgencia_col in columnas_urgencia:
        datos = df_urgencias[urgencia_col].dropna()
        if len(datos) > 0:
            print(f"\n🔹 {urgencia_col}:")
            print(f"   • Mínimo: {datos.min():.4f}")
            print(f"   • Máximo: {datos.max():.4f}")
            print(f"   • Promedio: {datos.mean():.4f}")
            print(f"   • Pedidos calculados: {len(datos)}")
    
    # Mostrar correlación entre urgencias (si hay más de una)
    if len(columnas_urgencia) > 1:
        print("\n📊 Correlación entre medidas de urgencia:")
        correlaciones = df_urgencias[columnas_urgencia].corr()
        print(correlaciones.to_string())

def main():
    print("\n" + "=" * 70)
    print("🧪 GENERADOR DE MÚLTIPLES MEDIDAS DE URGENCIA PARA K-NN")
    print("=" * 70)
    
    # 1. Encontrar archivos
    archivos = encontrar_archivos()
    
    # Verificar archivos mínimos
    archivos_minimos = ["LineasPedidos", "Pedidos", "Productos"]
    faltantes = [archivo for archivo in archivos_minimos if archivo not in archivos]
    
    if faltantes:
        print(f"\n❌ Faltan archivos esenciales: {faltantes}")
        return
    
    # 2. Cargar y unificar datos
    try:
        df_unificado = cargar_y_unificar_datos(archivos)
    except Exception as e:
        print(f"\n❌ Error unificando datos: {e}")
        return
    
    # 3. Calcular diferentes medidas de urgencia
    df_con_urgencias = calcular_variables_urgencia(df_unificado)
    
    # 4. Crear diferentes datasets para K-NN
    crear_datasets_knn(df_con_urgencias)
    
    # 5. Mostrar resumen
    mostrar_resumen(df_con_urgencias)
    
    # 6. Guardar dataset completo
    df_con_urgencias.to_csv("app/data/datos_completos_con_urgencias.csv", index=False)
    
    print("\n" + "=" * 70)
    print("✅ ARCHIVOS CREADOS PARA COMPARACIÓN")
    print("=" * 70)
    print("""
📁 Datos completos:
   • datos_completos_con_urgencias.csv

📁 Para K-NN (diferentes versiones):
   • knn_dataset1_variables_originales.csv
   • knn_dataset2_urgencia_60_40.csv
   • knn_dataset3_urgencia_40_60.csv
   • knn_dataset4_todas_urgencias.csv
   • knn_dataset5_sin_normalizar.csv
   • knn_dataset5_normalizado.csv

📁 Para análisis:
   • analisis_comparativo_urgencias.csv
    """)
    
    print("\n💡 Puedes probar K-NN con cada dataset y comparar resultados.")
    print("   El archivo 'analisis_comparativo_urgencias.csv' te permite ver")
    print("   todas las urgencias calculadas para el mismo pedido.")

if __name__ == "__main__":
    main()