import pandas as pd
from datetime import datetime, timedelta
import glob

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

def calcular_disponibilidad_pedidos_caducidad_correcta(df_unificado, fecha_inicio=None):
    """
    Calcula disponibilidad con caducidad POST-producción
    
    CADUCIDAD CORRECTA: Días de vida DESPUÉS de terminada la producción
    """
    print("\n⚙️ CALCULANDO DISPONIBILIDAD CON CADUCIDAD CORRECTA")
    print("=" * 70)
    
    if fecha_inicio is None:
        fecha_inicio = datetime.now()
    
    print(f"Fecha inicio producción: {fecha_inicio.strftime('%Y-%m-%d')}")
    print("REGLA: Caducidad cuenta DESPUÉS de terminada la producción")
    
    # 1. Para cada pedido, encontrar el producto que más tarda
    print("\n1. Analizando tiempos de producción...")
    
    pedidos_info = df_unificado.groupby('PedidoID').agg({
        'ProductoID': lambda x: list(set(x)),
        'TiempoFabricacionMedio': lambda x: list(set(x)),
        'distancia_km': 'first',
        'Caducidad': 'first',  # Días de vida POST-producción
        'provinciaID': 'first'
    }).reset_index()
    
    # Tiempo del pedido = MAX(tiempo de sus productos)
    pedidos_info['TiempoProduccion'] = pedidos_info['TiempoFabricacionMedio'].apply(
        lambda x: max(x) if x else 0
    )
    
    # 2. Calcular fechas CORRECTAS
    print("2. Calculando fechas con caducidad POST-producción...")
    
    resultados = []
    for idx, pedido in pedidos_info.iterrows():
        pedido_id = pedido['PedidoID']
        tiempo_produccion = pedido['TiempoProduccion']
        caducidad_dias = pedido['Caducidad']  # Días de vida POST-producción
        
        # Fechas de producción (todos empiezan al mismo tiempo)
        fecha_inicio_produccion = fecha_inicio
        fecha_fin_produccion = fecha_inicio + timedelta(days=tiempo_produccion)
        
        # Fecha de entrega estimada (producción + logística)
        fecha_entrega_estimada = fecha_fin_produccion + timedelta(days=1)
        
        # ⭐⭐ CADUCIDAD CORRECTA: fecha_fin_producción + caducidad_dias ⭐⭐
        fecha_caducidad = fecha_fin_produccion + timedelta(days=caducidad_dias)
        
        # ¿Se puede entregar a tiempo? (entrega debe ser ANTES de caducar)
        entregable = fecha_entrega_estimada <= fecha_caducidad
        
        # Días restantes después de entrega (margen de seguridad)
        if entregable:
            dias_restantes = (fecha_caducidad - fecha_entrega_estimada).days
        else:
            dias_restantes = -1  # No se puede entregar a tiempo
        
        resultados.append({
            'PedidoID': pedido_id,
            'TiempoProduccion': tiempo_produccion,
            'Caducidad_dias': caducidad_dias,  # Vida útil post-producción
            'fecha_inicio_produccion': fecha_inicio_produccion,
            'fecha_fin_produccion': fecha_fin_produccion,
            'fecha_entrega_estimada': fecha_entrega_estimada,
            'fecha_caducidad': fecha_caducidad,
            'entregable': entregable,
            'dias_restantes_post_entrega': dias_restantes,
            'distancia_km': pedido['distancia_km'],
            'provinciaID': pedido['provinciaID']
        })
    
    # 3. DataFrame de resultados
    df_resultados = pd.DataFrame(resultados)
    
    # 4. Análisis
    print("\n3. ANÁLISIS DE CADUCIDAD CORRECTA:")
    
    # Pedidos entregables
    entregables = df_resultados[df_resultados['entregable'] == True]
    no_entregables = df_resultados[df_resultados['entregable'] == False]
    
    print(f"   • Total pedidos: {len(df_resultados)}")
    print(f"   • Pedidos ENTREGABLES: {len(entregables)} ({len(entregables)/len(df_resultados)*100:.1f}%)")
    print(f"   • Pedidos NO entregables: {len(no_entregables)}")
    
    if len(entregables) > 0:
        print(f"   • Días restantes promedio post-entrega: {entregables['dias_restantes_post_entrega'].mean():.1f} días")
        print(f"   • Pedidos con margen < 2 días: {len(entregables[entregables['dias_restantes_post_entrega'] < 2])} (urgentes)")
    
    if len(no_entregables) > 0:
        print("   • Razón no entregables: caducan antes de poder entregarse")
    
    return df_resultados

def crear_datasets_optimizados(df_unificado, df_disponibilidad):
    """
    Crea datasets para K-NN optimizados para rutas
    """
    print("\n📦 CREANDO DATASETS OPTIMIZADOS PARA RUTAS")
    print("=" * 70)
    
    # 1. Solo pedidos entregables
    df_entregables = df_disponibilidad[df_disponibilidad['entregable'] == True].copy()
    
    if len(df_entregables) == 0:
        print("❌ ERROR: No hay pedidos entregables")
        return
    
    print(f"Pedidos entregables: {len(df_entregables)}")
    
    # 2. Agrupar por FECHA DE ENTREGA ESTIMADA
    df_entregables['fecha_entrega_estimada'] = pd.to_datetime(df_entregables['fecha_entrega_estimada'])
    
    # Agrupar por DÍA de entrega (más granular que por semana)
    df_entregables['dia_entrega'] = df_entregables['fecha_entrega_estimada'].dt.date
    
    # 3. Para cada día de entrega, crear dataset K-NN
    print("\nCreando datasets por día de entrega...")
    
    dias_entrega = sorted(df_entregables['dia_entrega'].unique())
    
    for dia in dias_entrega:
        # Pedidos que se entregan este día
        pedidos_dia = df_entregables[df_entregables['dia_entrega'] == dia]['PedidoID'].tolist()
        
        if len(pedidos_dia) == 0:
            continue
        
        # Obtener datos originales de estos pedidos
        df_dia = df_unificado[df_unificado['PedidoID'].isin(pedidos_dia)].copy()
        
        # Agrupar por pedido (un registro por pedido)
        df_dia_agrupado = df_dia.groupby('PedidoID').agg({
            'distancia_km': 'first',
            'provinciaID': 'first',
            'Caducidad': 'first'  # Días de vida post-producción
        }).reset_index()
        
        # Añadir información de disponibilidad
        info_dia = df_entregables[df_entregables['dia_entrega'] == dia][
            ['PedidoID', 'dias_restantes_post_entrega', 'fecha_entrega_estimada']
        ]
        df_dia_agrupado = pd.merge(df_dia_agrupado, info_dia, on='PedidoID')
        
        # Calcular URGENCIA REAL para K-NN
        # Basada en días restantes post-entrega (menos días = más urgente)
        df_dia_agrupado['Urgencia_Real'] = 1 / (df_dia_agrupado['dias_restantes_post_entrega'] + 1)
        
        # Normalizar distancia
        max_dist = df_dia_agrupado['distancia_km'].max()
        if max_dist > 0:
            df_dia_agrupado['Distancia_Normalizada'] = df_dia_agrupado['distancia_km'] / max_dist
        
        # Score combinado para K-NN (prioridad de ruta)
        if 'Distancia_Normalizada' in df_dia_agrupado.columns:
            df_dia_agrupado['Score_Ruta'] = (
                df_dia_agrupado['Urgencia_Real'] * 0.6 +  # 60% urgencia (caducidad)
                df_dia_agrupado['Distancia_Normalizada'] * 0.4  # 40% distancia
            )
        
        # Formatear nombre de archivo
        dia_str = dia.strftime('%Y-%m-%d')
        nombre_archivo = f"app/data/knn_dia_{dia_str}.csv"
        
        # Columnas para K-NN
        columnas_knn = [
            'PedidoID', 'distancia_km', 'provinciaID', 
            'dias_restantes_post_entrega', 'Urgencia_Real', 'Score_Ruta'
        ]
        columnas_existentes = [c for c in columnas_knn if c in df_dia_agrupado.columns]
        
        df_dia_agrupado[columnas_existentes].to_csv(nombre_archivo, index=False)
    
    print(f"✓ Datasets creados: {len(dias_entrega)} días diferentes de entrega")
    
    # 4. Dataset para pedidos URGENTES (margen < 3 días)
    print("\nCreando dataset para pedidos URGENTES...")
    
    urgentes = df_entregables[df_entregables['dias_restantes_post_entrega'] < 3].copy()
    
    if len(urgentes) > 0:
        pedidos_urgentes = urgentes['PedidoID'].tolist()
        df_urg = df_unificado[df_unificado['PedidoID'].isin(pedidos_urgentes)].copy()
        
        df_urg_agrupado = df_urg.groupby('PedidoID').agg({
            'distancia_km': 'first',
            'provinciaID': 'first'
        }).reset_index()
        
        # Añadir urgencia
        info_urg = urgentes[['PedidoID', 'dias_restantes_post_entrega']]
        df_urg_agrupado = pd.merge(df_urg_agrupado, info_urg, on='PedidoID')
        
        # Score de prioridad (más urgente = mayor score)
        df_urg_agrupado['Prioridad_Urgente'] = 1 / (df_urg_agrupado['dias_restantes_post_entrega'] + 0.5)
        
        df_urg_agrupado.to_csv("app/data/knn_urgentes.csv", index=False)
        print(f"✓ Dataset urgentes: {len(urgentes)} pedidos con margen < 3 días")
    
    # 5. Dataset general (todos los entregables)
    print("\nCreando dataset general...")
    
    todos_pedidos = df_entregables['PedidoID'].tolist()
    df_todos = df_unificado[df_unificado['PedidoID'].isin(todos_pedidos)].copy()
    
    df_todos_agrupado = df_todos.groupby('PedidoID').agg({
        'distancia_km': 'first',
        'provinciaID': 'first',
        'Caducidad': 'first'
    }).reset_index()
    
    # Añadir toda la información
    df_todos_agrupado = pd.merge(
        df_todos_agrupado,
        df_entregables[['PedidoID', 'dias_restantes_post_entrega', 'fecha_entrega_estimada']],
        on='PedidoID'
    )
    
    # Calcular scores
    df_todos_agrupado['Urgencia'] = 1 / (df_todos_agrupado['dias_restantes_post_entrega'] + 1)
    max_dist = df_todos_agrupado['distancia_km'].max()
    if max_dist > 0:
        df_todos_agrupado['Distancia_Norm'] = df_todos_agrupado['distancia_km'] / max_dist
        df_todos_agrupado['Score_General'] = (
            df_todos_agrupado['Urgencia'] * 0.6 + 
            df_todos_agrupado['Distancia_Norm'] * 0.4
        )
    
    df_todos_agrupado.to_csv("app/data/knn_todos_entregables.csv", index=False)
    print("✓ Dataset general creado")
    
    # 6. Guardar reporte
    df_disponibilidad.to_csv("app/data/reporte_disponibilidad_correcta.csv", index=False)
    print("✓ Reporte de disponibilidad guardado")
    
    return df_entregables

def main_final():
    """
    Versión FINAL con todas las correcciones
    """
    print("\n" + "=" * 70)
    print("🎯 SISTEMA FINAL: DISPONIBILIDAD Y CADUCIDAD CORRECTA")
    print("=" * 70)
    
    print("\n📋 REGLAS DEL SISTEMA:")
    print("   1. Todos los pedidos empiezan producción SIMULTÁNEAMENTE")
    print("   2. Tiempo del pedido = MAX(tiempo de sus productos)")
    print("   3. Caducidad cuenta DESPUÉS de terminada la producción")
    print("   4. Entrega = Fin producción + 1 día logística")
    
    # 1. Cargar datos
    archivos = encontrar_archivos()
    
    archivos_minimos = ["LineasPedidos", "Pedidos", "Productos"]
    faltantes = [archivo for archivo in archivos_minimos if archivo not in archivos]
    
    if faltantes:
        print(f"\n❌ Faltan archivos: {faltantes}")
        return
    
    # 2. Unificar
    try:
        df_unificado = cargar_y_unificar_datos(archivos)
        print(f"\n✓ Datos unificados: {len(df_unificado)} filas")
    except Exception as e:
        print(f"❌ Error: {e}")
        return
    
    # 3. Calcular disponibilidad CORRECTA
    print("\n" + "-" * 70)
    print("CALCULANDO DISPONIBILIDAD...")
    print("-" * 70)
    
    df_disponibilidad = calcular_disponibilidad_pedidos_caducidad_correcta(df_unificado)
    
    # 4. Crear datasets optimizados
    print("\n" + "-" * 70)
    print("CREANDO DATASETS PARA K-NN...")
    print("-" * 70)
    
    df_entregables = crear_datasets_optimizados(df_unificado, df_disponibilidad)
    
    # 5. Resumen final
    print("\n" + "=" * 70)
    print("✅ PROCESO COMPLETADO - RESUMEN FINAL")
    print("=" * 70)
    
    if df_entregables is not None and len(df_entregables) > 0:
        # Estadísticas
        dias_entrega = df_entregables['dia_entrega'].nunique()
        max_entregas_dia = df_entregables['dia_entrega'].value_counts().max()
        
        print("\n📊 ESTADÍSTICAS:")
        print(f"   • Pedidos entregables: {len(df_entregables)}")
        print(f"   • Días diferentes de entrega: {dias_entrega}")
        print(f"   • Máximo entregas en un día: {max_entregas_dia}")
        print(f"   • Urgencia promedio: {df_entregables['dias_restantes_post_entrega'].mean():.1f} días restantes")
        
        # Mostrar primeros días de entrega
        print("\n📅 PRÓXIMAS ENTREGAS:")
        primeros_dias = sorted(df_entregables['dia_entrega'].unique())[:5]
        
        for dia in primeros_dias:
            pedidos_dia = df_entregables[df_entregables['dia_entrega'] == dia]
            dia_str = dia.strftime('%d/%m/%Y')
            
            print(f"\n   {dia_str}:")
            print(f"   • Pedidos: {len(pedidos_dia)}")
            print(f"   • Días restantes promedio: {pedidos_dia['dias_restantes_post_entrega'].mean():.1f}")
            
            # Destinos principales
            if 'provinciaID' in pedidos_dia.columns:
                provincias = pedidos_dia['provinciaID'].unique()
                print(f"   • Provincias: {len(provincias)}")
        
        print("\n📁 ARCHIVOS CREADOS:")
        print("   1. knn_dia_AAAA-MM-DD.csv - Para cada día de entrega")
        print("   2. knn_urgentes.csv - Pedidos con margen < 3 días")
        print("   3. knn_todos_entregables.csv - Vista general")
        print("   4. reporte_disponibilidad_correcta.csv - Timeline completo")
        
        print("\n🎯 RECOMENDACIÓN PARA ALGORITMO GENÉTICO:")
        print("   Usa 'knn_dia_AAAA-MM-DD.csv' para optimizar rutas POR DÍA")
        print("   Los pedidos en el mismo archivo se entregarán el MISMO DÍA")
        print("   El AG puede asignarlos a los mismos camiones/rutas")
    else:
        print("❌ No hay pedidos entregables para planificar")

# EJECUTAR
if __name__ == "__main__":
    main_final()