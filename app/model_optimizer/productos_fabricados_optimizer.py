import pandas as pd
import sys
import os
from datetime import datetime, timedelta
import math
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from app.camiones.Camiones import Camion

df_matriz = pd.read_csv('matriz_tiempos_destinos.csv', index_col=0)
Peso_maximo = 1800

# ========== VARIABLES GLOBALES PERSISTENTES ==========
camiones_creados = []      # TODOS los camiones (persistentes)
camiones_normales = []     # Camiones normales (persistentes)
camiones_especiales = []   # Camiones especiales (persistentes)
Id_camiones = 0           # Contador global de IDs
pedidos_pendientes = []   # Pedidos pospuestos (tiempo > 9h o de camiones eliminados)
expediciones_activas = [] 

# ========== FUNCIONES PARA RUTAS PRE-CALCULADAS ==========
def registrar_expedicion_salida(camion, fecha_salida):
    """Registra cuando un camión sale en ruta y guarda en CSV."""
    # Calcular tiempo de ruta
    tiempo_ruta = 0
    if hasattr(camion, 'tiempo_final') and camion.tiempo_final:
        tiempo_ruta = camion.tiempo_final
    elif camion.destinos and len(camion.destinos) > 0:
        tiempo_ruta = estimar_tiempo_ruta(camion.destinos)
    else:
        tiempo_ruta = 0
    
    # Calcular fecha de retorno
    dias_retorno = calcular_dias_para_retorno(tiempo_ruta)
    fecha_retorno = (datetime.strptime(fecha_salida, '%Y-%m-%d') + 
                     timedelta(days=dias_retorno)).strftime('%Y-%m-%d')
    
    # Extraer información detallada de productos
    productos_info = extraer_info_productos_detallada(camion, fecha_salida)
    
    # Calcular caducidad más próxima
    fecha_caducidad_proxima, dias_caducidad_proxima = calcular_caducidad_mas_proxima(productos_info)
    
    # Obtener resumen de productos para CSV
    productos_str, total_productos, destinos_str = obtener_resumen_productos(productos_info)
    
    # Crear ruta como string
    ruta_str = ""
    if hasattr(camion, 'ruta_final') and camion.ruta_final:
        ruta_str = "|".join(map(str, camion.ruta_final))
    elif camion.destinos:
        # Si no hay ruta optimizada, crear una simple
        ruta_simple = [0] + list(camion.destinos) + [0]
        ruta_str = "|".join(map(str, ruta_simple))
    
    expedicion = {
        'id_camion': camion.id_camion,
        'tipo': 'especial' if camion.es_especial else 'normal',
        'fecha_salida': fecha_salida,
        'fecha_retorno_estimada': fecha_retorno,
        'tiempo_ruta_horas': tiempo_ruta,
        'dias_retorno': dias_retorno,
        'destinos': camion.destinos.copy() if camion.destinos else [],
        'ruta_optima': camion.ruta_final.copy() if hasattr(camion, 'ruta_final') and camion.ruta_final else [],
        'peso_kg': camion.peso_actual,
        'peso_maximo_kg': camion.peso_maximo,
        'porcentaje_ocupacion': (camion.peso_actual / camion.peso_maximo * 100) if camion.peso_maximo > 0 else 0,
        'productos_info': productos_info,
        'productos_resumen': productos_str,
        'total_productos': total_productos,
        'destinos_productos': destinos_str,
        'fecha_caducidad_proxima': fecha_caducidad_proxima,
        'dias_caducidad_proxima': dias_caducidad_proxima,
        'estado': 'en_viaje',
        'fecha_real_retorno': None,
        'ruta_str': ruta_str
    }
    
    expediciones_activas.append(expedicion)
    
    # Guardar en CSV inmediatamente
    guardar_expedicion_csv(expedicion)
    
    if camion.destinos and len(camion.destinos) > 0:
        print(f"    📝 Expedición registrada: Retorna el {fecha_retorno} ({dias_retorno} días)")
        print(f"      📊 Guardado en CSV: Camión {camion.id_camion}, {total_productos} productos")
        if fecha_caducidad_proxima:
            print(f"      ⏰ Caducidad más próxima: {fecha_caducidad_proxima} ({dias_caducidad_proxima} días)")
    else:
        print("    ⚠️ Expedición registrada sin destinos")
    
    return expedicion

def cargar_rutas_precalculadas(archivo="rutas_completas.csv"):
    """Carga y procesa las rutas óptimas pre-calculadas."""
    try:
        df_rutas = pd.read_csv(archivo)
        
        rutas = []
        for _, row in df_rutas.iterrows():
            # Convertir string "8|25|12|5" a lista [8, 25, 12, 5]
            destinos = list(map(int, row['destinos'].split('|')))
            
            # Convertir string "0|5|8|12|25|0" a lista [0, 5, 8, 12, 25, 0]
            ruta_completa = list(map(int, row['ruta_completa'].split('|')))
            
            rutas.append({
                'id': row['cluster_id'],
                'destinos': destinos,
                'ruta_completa': ruta_completa,
                'num_destinos': row['num_destinos'],
                'tiempo_estimado': row['tiempo_horas'],
                'viable': row['viable'] == 'SI',
                'eficiencia': row['eficiencia']
            })
        
        # Ordenar por eficiencia (mejores rutas primero)
        rutas.sort(key=lambda x: x['eficiencia'], reverse=True)
        print(f"  ✓ Rutas pre-calculadas cargadas: {len(rutas)}")
        return rutas
        
    except FileNotFoundError:
        print(f"  ⚠️ Archivo {archivo} no encontrado. Continuando sin rutas pre-calculadas.")
        return []
    except Exception as e:
        print(f"  ⚠️ Error cargando rutas pre-calculadas: {e}")
        return []

def buscar_rutas_para_destino(destino_id, rutas_precalculadas):
    """Busca rutas pre-calculadas que incluyan un destino específico."""
    rutas_compatibles = []
    for ruta in rutas_precalculadas:
        if ruta['viable'] and destino_id in ruta['destinos']:
            rutas_compatibles.append(ruta)
    return rutas_compatibles

def asignar_pedido_a_ruta_precalculada(pedido, rutas_precalculadas, camiones_existentes):
    """
    Intenta asignar un pedido a una ruta pre-calculada existente.
    Devuelve el camión asignado o None si no se pudo.
    """
    destino_id = pedido['DestinoEntregaID']
    cantidad = pedido['Cantidad']
    
    # Buscar rutas que incluyan este destino
    rutas_compatibles = buscar_rutas_para_destino(destino_id, rutas_precalculadas)
    
    if not rutas_compatibles:
        return None
    
    # Primero: buscar camiones existentes que ya usen estas rutas
    for camion in camiones_existentes:
        if (camion.estado != "en_ruta" and 
            destino_id in camion.destinos and
            camion.capacidad_disponible() >= cantidad):
            
            # Verificar si este camión sigue una ruta pre-calculada
            for ruta in rutas_compatibles:
                # Verificar si los destinos del camión están en la ruta pre-calculada
                if set(camion.destinos).issubset(set(ruta['destinos'])):
                    return camion
    
    # Segundo: buscar cualquier camión con espacio que vaya a destinos de rutas compatibles
    for camion in camiones_existentes:
        if (camion.estado != "en_ruta" and
            camion.capacidad_disponible() >= cantidad):
            
            # Verificar si los destinos del camión están en alguna ruta compatible
            for ruta in rutas_compatibles:
                destinos_comunes = set(camion.destinos) & set(ruta['destinos'])
                if destinos_comunes:  # Si hay al menos un destino común
                    return camion
    
    return None

# ========== FUNCIONES DE CONSOLIDACIÓN Y DIVISIÓN INTELIGENTE ==========

def consolidar_destinos_duplicados(camiones_normales, df_matriz):
    """
    Combina camiones que tienen los mismos destinos.
    """
    print("\n🔄 CONSOLIDANDO DESTINOS DUPLICADOS")
    
    # Agrupar camiones por destino
    grupos = {}
    for camion in camiones_normales[:]:
        if camion.estado == "en_ruta" or not camion.destinos:
            continue
            
        # Ordenar destinos para comparación
        destinos_key = tuple(sorted(camion.destinos))
        
        if destinos_key not in grupos:
            grupos[destinos_key] = []
        grupos[destinos_key].append(camion)
    
    # Consolidar grupos con más de 1 camión
    consolidaciones = 0
    camiones_a_eliminar = []
    
    for destinos_key, camiones_grupo in grupos.items():
        if len(camiones_grupo) > 1:
            print(f"  Destinos {destinos_key}: {len(camiones_grupo)} camiones")
            
            # Ordenar por fecha de creación (más antiguo primero)
            camiones_grupo.sort(key=lambda x: x.id_camion)
            
            # Tomar el primer camión como base
            camion_base = camiones_grupo[0]
            
            # Combinar pedidos de los otros camiones
            for otro_camion in camiones_grupo[1:]:
                if camion_base == otro_camion:
                    continue
                
                # Verificar si cabe todo
                peso_total = camion_base.peso_actual + otro_camion.peso_actual
                if peso_total <= camion_base.peso_maximo:
                    print(f"    ✓ Consolidando camión {otro_camion.id_camion} en {camion_base.id_camion}")
                    
                    # Mover pedidos
                    pedidos_a_mover = otro_camion.productos_asignados.copy()
                    for pedido in pedidos_a_mover:
                        # Extraer información del pedido
                        destino_id = None
                        cantidad = 0
                        
                        if isinstance(pedido, dict):
                            destino_id = pedido.get('DestinoEntregaID')
                            cantidad = pedido.get('Cantidad', 0)
                        elif hasattr(pedido, 'DestinoEntregaID'):
                            destino_id = pedido.DestinoEntregaID
                            cantidad = getattr(pedido, 'Cantidad', 0)
                        
                        # Agregar al camión base
                        if destino_id and cantidad > 0:
                            if camion_base.agregar_producto(pedido, cantidad, destino_id):
                                # Remover del camión original
                                otro_camion.quitar_producto(pedido, cantidad)
                    
                    # Marcar camión para eliminar
                    camiones_a_eliminar.append(otro_camion)
                    consolidaciones += 1
    
    # Eliminar camiones consolidados
    for camion in camiones_a_eliminar:
        if camion in camiones_normales:
            camiones_normales.remove(camion)
        if camion in camiones_creados:
            camiones_creados.remove(camion)
    
    if consolidaciones > 0:
        print(f"  ✅ Total consolidaciones: {consolidaciones}")
    else:
        print("  ℹ️ No se encontraron consolidaciones necesarias")
    
    return consolidaciones

def dividir_ruta_inteligente(camion, df_matriz, tiempo_max=18.0):
    """
    Divide rutas inteligentemente, evitando destinos individuales cuando sea posible.
    """
    if not hasattr(camion, 'tiempo_final') or not camion.tiempo_final:
        camion.optimizar_rutas(df_matriz)
        seleccionar_mejor_ruta_automatico(camion)
    
    if camion.tiempo_final <= tiempo_max:
        return [camion]
    
    print(f"\n🔍 DIVIDIENDO INTELIGENTEMENTE CAMIÓN {camion.id_camion}")
    print(f"  Tiempo: {camion.tiempo_final:.2f}h > {tiempo_max}h")
    print(f"  Destinos: {camion.destinos} ({len(camion.destinos)} destinos)")
    print(f"  Carga: {camion.peso_actual}/{camion.peso_maximo}kg")
    
    # Ordenar destinos por tiempo desde Mataró (más cercanos primero)
    destinos_ordenados = sorted(camion.destinos, 
                               key=lambda x: df_matriz.loc[0, str(x)])
    
    # Crear grupos inteligentes
    rutas_propuestas = []
    i = 0
    
    while i < len(destinos_ordenados):
        # Intentar tomar 2-4 destinos juntos
        mejor_grupo = []
        mejor_tiempo = 0
        
        # Probar diferentes tamaños de grupo
        for tamano_grupo in range(4, 1, -1):  # 4, 3, 2
            if i + tamano_grupo <= len(destinos_ordenados):
                grupo_prueba = destinos_ordenados[i:i + tamano_grupo]
                tiempo_prueba = estimar_tiempo_ruta(grupo_prueba)
                
                # Verificar si el grupo es viable
                if tiempo_prueba <= tiempo_max:
                    mejor_grupo = grupo_prueba
                    mejor_tiempo = tiempo_prueba
                    break
        
        if mejor_grupo:
            rutas_propuestas.append(mejor_grupo)
            i += len(mejor_grupo)
            print(f"    Grupo {mejor_grupo}: {mejor_tiempo:.2f}h")
        else:
            # Si ningún grupo cabe, tomar destino individual
            rutas_propuestas.append([destinos_ordenados[i]])
            tiempo_individual = df_matriz.loc[0, str(destinos_ordenados[i])] * 2
            print(f"    Destino individual {destinos_ordenados[i]}: {tiempo_individual:.2f}h")
            i += 1
    
    print(f"  ✓ Propuesta de división en {len(rutas_propuestas)} rutas")
    
    # Crear camiones para cada ruta propuesta
    nuevos_camiones = []
    for ruta_destinos in rutas_propuestas:
        nuevo_camion = crear_camion_desde_destinos(ruta_destinos, camion, df_matriz)
        if nuevo_camion:
            nuevos_camiones.append(nuevo_camion)
    
    return nuevos_camiones

def crear_camion_desde_destinos(destinos, camion_original, df_matriz):
    """Crea un nuevo camión con un subconjunto de destinos."""
    global Id_camiones
    
    Id_camiones += 1
    nuevo_camion = Camion(
        id_camion=Id_camiones,
        peso_maximo=camion_original.peso_maximo,
        fecha_salida=camion_original.fecha_salida,
        es_especial=camion_original.es_especial
    )
    
    # Agregar solo los pedidos de estos destinos
    pedidos_procesados = 0
    for pedido in camion_original.productos_asignados:
        destino_id = None
        cantidad = 0
        
        if isinstance(pedido, dict):
            destino_id = pedido.get('DestinoEntregaID')
            cantidad = pedido.get('Cantidad', 0)
        elif hasattr(pedido, 'DestinoEntregaID'):
            destino_id = pedido.DestinoEntregaID
            cantidad = getattr(pedido, 'Cantidad', 0)
        
        if destino_id in destinos and cantidad > 0:
            if nuevo_camion.agregar_producto(pedido, cantidad, destino_id):
                pedidos_procesados += 1
    
    if pedidos_procesados > 0:
        # Optimizar ruta del nuevo camión
        nuevo_camion.optimizar_rutas(df_matriz)
        seleccionar_mejor_ruta_automatico(nuevo_camion)
        return nuevo_camion
    
    return None

# ========== FUNCIONES PRINCIPALES ==========

def comprobar_pedidos_fecha_produccion():
    df = pd.read_csv("productos_fabricados.csv")
    fechas_unicas = df['FechaFinFabricacion'].unique()
    
    global Id_camiones
    cont = 0
    for fecha in fechas_unicas:
        cont += 1
        pedidos_entrega = df.loc[df['FechaFinFabricacion'] == fecha].copy()
        print(f"\n{'='*80}")
        print(f"📅 FECHA: {fecha} - DÍA {cont}")
        print(f"{'='*80}")
        
        
        # Reparar expediciones si es necesario
        if expediciones_activas:
            reparar_expediciones_existentes()
        
        # Actualizar disponibilidad
        print("\n🔄 ACTUALIZANDO DISPONIBILIDAD")
        actualizar_disponibilidad_camiones(fecha)
        
        # Mostrar estado
        mostrar_estado_camiones_actual(fecha)
        
        # Procesar pendientes
        if pedidos_pendientes:
            procesar_pedidos_pendientes(fecha, pedidos_pendientes)
            pedidos_pendientes.clear()
        
        # Procesar nuevos
        procesar_pedidos_nuevos(pedidos_entrega, fecha)
        
        # Optimizar
        optimizar_camiones_con_rutas_precalculadas(fecha)
        
        # Consolidar
        consolidar_destinos_duplicados(camiones_normales, df_matriz)
        
        # Verificar y dividir
        verificar_y_dividir_camiones(fecha)
        
        # Resumen
        mostrar_resumen_fecha(fecha)
    
    # Exportar final sin ruido
    try:
        exportar_resumen_final_expediciones()
    except:
        pass  # Silenciar cualquier error de exportación
    
    mostrar_camiones_en_ruta()

def reparar_expediciones_existentes():
    """Repara expediciones que puedan tener campos faltantes."""
    if not expediciones_activas:
        return 0
    
    for exp in expediciones_activas:
        if 'estado' not in exp:
            exp['estado'] = 'en_viaje'
    
    return len(expediciones_activas)

def procesar_pedidos_pendientes(fecha, pedidos_pendientes_lista):
    """Procesa pedidos pendientes manteniendo caducidad."""
    for i, pedido in enumerate(pedidos_pendientes_lista):
        destino_id = pedido['DestinoEntregaID']
        cantidad = pedido['Cantidad']
        tiempo = df_matriz.loc[0, str(destino_id)]
        
        print(f"  {i+1}. Pedido pendiente - Destino {destino_id}, Cantidad {cantidad}")
        
        # Mostrar caducidad si está disponible
        if 'FechaCaducidad' in pedido:
            dias_restantes = (datetime.strptime(pedido['FechaCaducidad'], '%Y-%m-%d') - 
                            datetime.strptime(fecha, '%Y-%m-%d')).days
            print(f"     Caduca: {pedido['FechaCaducidad']} ({dias_restantes} días)")
        
        if tiempo >= 8.5:
            print("    → Buscando camión especial...")
            camion_especial = buscar_camion_especial_destino(destino_id)
            
            if camion_especial and camion_especial.agregar_producto(pedido, cantidad, destino_id):
                print(f"      ✓ Agregado a camión especial existente {camion_especial.id_camion}")
            else:
                nuevo_camion = crear_camion_ruta_especial(destino_id, fecha)
                if nuevo_camion.agregar_producto(pedido, cantidad, destino_id):
                    camiones_especiales.append(nuevo_camion)
                    camiones_creados.append(nuevo_camion)
                    print(f"      ✓ Nuevo camión especial {nuevo_camion.id_camion} creado")
        else:
            print("    → Buscando camión normal...")
            camion_normal = agregar_pedido_normal_a_camion(pedido, fecha, destino_id, cantidad)
            if not camion_normal:
                camion_normal = crear_nuevo_camion_normal(fecha, destino_id)
                camion_normal.agregar_producto(pedido, cantidad, destino_id)

def procesar_pedidos_nuevos(pedidos_entrega, fecha):
    """Procesa pedidos nuevos del día actual manteniendo información de caducidad."""
    global pedidos_pendientes
    
    # Cargar rutas pre-calculadas
    rutas_precalculadas = cargar_rutas_precalculadas()
    
    for index, producto in pedidos_entrega.iterrows():
        destino_id = producto['DestinoEntregaID']
        cantidad = producto['Cantidad']
        tiempo = df_matriz.loc[0, str(destino_id)]
        fecha_caducidad = producto['FechaCaducidad']
        
        # Crear diccionario completo con toda la información
        pedido_dict = {
            'DestinoEntregaID': destino_id,
            'Cantidad': cantidad,
            'ProductoID': producto['ProductoID'],
            'FechaFinFabricacion': producto['FechaFinFabricacion'],
            'FechaCaducidad': fecha_caducidad,
            'es_pendiente': False
        }
        
        print(f"Destino {destino_id}: {tiempo}h → ", end="")
        
        if tiempo >= 8.5:
            print("Camión especial")
            camion_especial = buscar_camion_especial_destino(destino_id)
            
            if camion_especial and camion_especial.agregar_producto(pedido_dict, cantidad, destino_id):
                print(f"  ✓ Agregado a camión especial existente {camion_especial.id_camion}")
            else:
                nuevo_camion = crear_camion_ruta_especial(destino_id, fecha)
                if nuevo_camion.agregar_producto(pedido_dict, cantidad, destino_id):
                    camiones_especiales.append(nuevo_camion)
                    camiones_creados.append(nuevo_camion)
                    print(f"  ✓ Nuevo camión especial {nuevo_camion.id_camion} creado")
        else:
            print("Ruta normal")
            
            # INTENTAR USAR RUTA PRE-CALCULADA
            camion_asignado = None
            if rutas_precalculadas:
                camion_asignado = asignar_pedido_a_ruta_precalculada(
                    pedido_dict, rutas_precalculadas, camiones_normales
                )
            
            if camion_asignado:
                if camion_asignado.agregar_producto(pedido_dict, cantidad, destino_id):
                    print(f"  ✓ Agregado a camión {camion_asignado.id_camion} (ruta pre-calculada)")
                    continue
            
            # Si no encontró ruta pre-calculada, usar la lógica normal
            camion_normal = agregar_pedido_normal_a_camion(pedido_dict, fecha, destino_id, cantidad)
            if not camion_normal:
                camion_normal = crear_nuevo_camion_normal(fecha, destino_id)
                camion_normal.agregar_producto(pedido_dict, cantidad, destino_id)
# ========== FUNCIÓN MEJORADA DE AGREGAR PEDIDOS NORMALES ==========

def agregar_pedido_normal_a_camion(pedido, fecha, destino_id, cantidad):
    """Busca o crea camión normal manteniendo información de caducidad."""
    global Id_camiones, camiones_normales, camiones_creados
    
    producto_id = pedido['ProductoID'] if isinstance(pedido, dict) else pedido.ProductoID
    
    # PRIMERO: Buscar camión con MISMO DESTINO y MISMO PRODUCTO
    camion_preferido = None
    
    for c in camiones_normales:
        if (c.estado != "en_ruta" and 
            destino_id in c.destinos and 
            tiene_mismo_producto(c, producto_id) and
            c.capacidad_disponible() >= cantidad):
            camion_preferido = c
            break
    
    # SEGUNDO: Si no encuentra, buscar camión con MISMO DESTINO
    if not camion_preferido:
        for c in camiones_normales:
            if (c.estado != "en_ruta" and
                destino_id in c.destinos and
                c.capacidad_disponible() >= cantidad):
                camion_preferido = c
                break
    
    # TERCERO: Priorizar camiones con productos que caducan pronto
    if not camion_preferido:
        # Buscar camión con productos que caduquen en similar fecha
        fecha_pedido_caducidad = None
        if isinstance(pedido, dict) and 'FechaCaducidad' in pedido:
            fecha_pedido_caducidad = pedido['FechaCaducidad']
        
        if fecha_pedido_caducidad:
            for c in camiones_normales:
                if (c.estado != "en_ruta" and
                    c.capacidad_disponible() >= cantidad):
                    # Verificar si tiene productos con caducidad similar
                    for p in c.productos_asignados:
                        p_caducidad = None
                        if isinstance(p, dict) and 'FechaCaducidad' in p:
                            p_caducidad = p['FechaCaducidad']
                        
                        if p_caducidad and abs((datetime.strptime(p_caducidad, '%Y-%m-%d') - 
                                              datetime.strptime(fecha_pedido_caducidad, '%Y-%m-%d')).days) <= 3:
                            camion_preferido = c
                            break
                    if camion_preferido:
                        break
    
    # CUARTO: Si aún no encuentra, buscar cualquier camión con capacidad
    if not camion_preferido:
        for c in camiones_normales:
            if (c.estado != "en_ruta" and
                c.capacidad_disponible() >= cantidad):
                camion_preferido = c
                break
    
    # QUINTO: Si aún no encuentra, crear nuevo camión
    if not camion_preferido:
        Id_camiones += 1
        camion_preferido = Camion(
            id_camion=Id_camiones,
            peso_maximo=Peso_maximo,
            fecha_salida=fecha,
            es_especial=False
        )
        camiones_normales.append(camion_preferido)
        camiones_creados.append(camion_preferido)
        print(f"  🚚 Nuevo camión normal {Id_camiones}")
    
    # Agregar producto
    if camion_preferido.agregar_producto(pedido, cantidad, destino_id):
        print(f"  ✓ Agregado al camión {camion_preferido.id_camion}")
        print(f"    Destinos: {camion_preferido.destinos}")
        print(f"    Producto ID: {producto_id}")
        if isinstance(pedido, dict) and 'FechaCaducidad' in pedido:
            dias = (datetime.strptime(pedido['FechaCaducidad'], '%Y-%m-%d') - 
                   datetime.strptime(fecha, '%Y-%m-%d')).days
            print(f"    Caduca en: {dias} días")
        return camion_preferido
    
    print(f"  ✗ Error: Sin capacidad en camión {camion_preferido.id_camion}")
    return None

def tiene_mismo_producto(camion, producto_id):
    """Verifica si el camión ya lleva este producto."""
    for pedido in camion.productos_asignados:
        if isinstance(pedido, dict):
            if pedido.get('ProductoID') == producto_id:
                return True
        elif hasattr(pedido, 'ProductoID'):
            if pedido.ProductoID == producto_id:
                return True
    return False

# ========== OPTIMIZACIÓN CON RUTAS PRE-CALCULADAS ==========

def optimizar_camiones_con_rutas_precalculadas(fecha):
    """
    Optimiza los camiones normales usando rutas pre-calculadas como guía.
    """
    print(f"\n{'='*60}")
    print(f"OPTIMIZANDO CAMIONES CON RUTAS PRE-CALCULADAS - FECHA {fecha}")
    print(f"{'='*60}")
    
    if not camiones_normales:
        print("No hay camiones normales para optimizar.")
        return
    
    # Cargar rutas pre-calculadas
    rutas_precalculadas = cargar_rutas_precalculadas()
    
    if not rutas_precalculadas:
        print("No hay rutas pre-calculadas disponibles. Usando optimización normal.")
        optimizar_rutas_fecha_actual(fecha)
        return
    
    camiones_optimizados = 0
    camiones_con_ruta_optima = 0
    
    for camion in camiones_normales:
        if camion.estado == "en_ruta" or not camion.destinos:
            continue
        
        # Asegurar que tiene tiempos calculados
        if not hasattr(camion, 'tiempo_final') or not camion.tiempo_final:
            camion.optimizar_rutas(df_matriz)
            seleccionar_mejor_ruta_automatico(camion)
        
        print(f"\n{'─'*40}")
        print(f"Camion {camion.id_camion}:")
        print(f"  Destinos actuales: {camion.destinos}")
        print(f"  Carga: {camion.peso_actual}/{camion.peso_maximo}kg")
        print(f"  Tiempo actual: {camion.tiempo_final:.2f}h")
        
        # Buscar ruta pre-calculada que coincida con estos destinos
        mejor_ruta = None
        mejor_coincidencia = 0
        
        for ruta in rutas_precalculadas:
            if not ruta['viable']:
                continue
            
            # Calcular cuántos destinos coinciden
            destinos_comunes = set(camion.destinos) & set(ruta['destinos'])
            coincidencia = len(destinos_comunes)
            
            if coincidencia > mejor_coincidencia:
                mejor_coincidencia = coincidencia
                mejor_ruta = ruta
        
        if mejor_ruta and mejor_coincidencia >= 2:
            print(f"  ✓ Ruta pre-calculada encontrada: {mejor_ruta['id']}")
            print(f"    Destinos ruta: {mejor_ruta['destinos']}")
            print(f"    Coinciden {mejor_coincidencia} de {len(camion.destinos)} destinos")
            print(f"    Tiempo estimado ruta: {mejor_ruta['tiempo_estimado']}h")
            print(f"    Eficiencia: {mejor_ruta['eficiencia']:.3f}")
            
            # Sugerir agregar destinos faltantes de la ruta pre-calculada
            destinos_faltantes = set(mejor_ruta['destinos']) - set(camion.destinos)
            if destinos_faltantes:
                print(f"    Destinos sugeridos para agregar: {sorted(destinos_faltantes)}")
            
            camiones_con_ruta_optima += 1
        
        camiones_optimizados += 1
    
    print(f"\n{'='*60}")
    print("RESUMEN OPTIMIZACIÓN:")
    print(f"  Camiones normales: {len(camiones_normales)}")
    print(f"  Camiones optimizados: {camiones_optimizados}")
    print(f"  Camiones con ruta óptima pre-calculada: {camiones_con_ruta_optima}")
    print(f"{'='*60}")

# ========== VERIFICACIÓN Y DIVISIÓN MEJORADA ==========

def verificar_y_dividir_camiones(fecha):
    """Verifica condiciones y DIVIDE camiones que no cumplen (con caducidad)."""
    global camiones_normales, camiones_creados, pedidos_pendientes
    
    print(f"\n{'='*60}")
    print(f"VERIFICANDO Y DIVIDIENDO CAMIONES - FECHA {fecha}")
    print(f"{'='*60}")
    
    camiones_a_dividir = []
    camiones_que_salen = []
    camiones_con_baja_ocupacion = []
    camiones_vacios = []
    
    for camion in camiones_normales[:]:
        # Saltar camiones que ya están en ruta
        if camion.estado == "en_ruta":
            continue
        
        # CASO 1: CAMIÓN VACÍO (sin destinos ni carga)
        if (not camion.destinos or len(camion.destinos) == 0) and camion.peso_actual == 0:
            # Asegurar que el tiempo es 0
            if hasattr(camion, 'tiempo_final'):
                camion.tiempo_final = 0
            if hasattr(camion, 'ruta_final'):
                camion.ruta_final = None
            
            print(f"\nCamión normal {camion.id_camion}:")
            print("  ⚪ VACÍO - Sin destinos ni carga")
            print("  ⏳ VACÍO: Espera mañana (sin costo de tiempo)")
            camiones_vacios.append(camion)
            continue
        
        # CASO 2: CAMIÓN CON DESTINOS O CARGA
        # Asegurar que tiene tiempo_final calculado (solo si tiene destinos)
        if camion.destinos and len(camion.destinos) > 0:
            if not hasattr(camion, 'tiempo_final') or camion.tiempo_final is None:
                camion.optimizar_rutas(df_matriz)
                seleccionar_mejor_ruta_automatico(camion)
        else:
            # Si no tiene destinos pero tiene carga (caso raro), tiempo = 0
            if hasattr(camion, 'tiempo_final'):
                camion.tiempo_final = 0
        
        # Obtener tiempo total
        if camion.destinos and len(camion.destinos) > 0:
            tiempo_total = camion.tiempo_final if hasattr(camion, 'tiempo_final') else estimar_tiempo_ruta(camion.destinos)
        else:
            tiempo_total = 0
        
        porcentaje_ocupacion = (camion.peso_actual / camion.peso_maximo) * 100 if camion.peso_maximo > 0 else 0
        
        # Verificar caducidad (solo si hay productos)
        if camion.productos_asignados and len(camion.productos_asignados) > 0:
            es_urgente = tiene_caducidad_urgente(camion, fecha)
            dias_caducidad = obtener_dias_hasta_caducidad_mas_cercana(camion, fecha)
        else:
            es_urgente = False
            dias_caducidad = float('inf')
        
        print(f"\nCamión normal {camion.id_camion}:")
        print(f"  Destinos: {camion.destinos}")
        print(f"  Carga: {camion.peso_actual}/{camion.peso_maximo}kg ({porcentaje_ocupacion:.1f}%)")
        
        # Mostrar tiempo solo si hay destinos
        if camion.destinos and len(camion.destinos) > 0:
            print(f"  Tiempo estimado: {tiempo_total:.2f}h")
        else:
            print("  Tiempo estimado: 0.00h (sin destinos)")
        
        if dias_caducidad is not None and dias_caducidad != float('inf'):
            print(f"  Caducidad más cercana: {dias_caducidad} días")
        
        # REGLAS CON CADUCIDAD:
        
        # 1. Si tiempo > 18h y tiene destinos → Se divide
        if tiempo_total > 18.0 and camion.destinos and len(camion.destinos) > 0:
            print(f"  ⚠️ TIEMPO EXCEDIDO ({tiempo_total:.2f}h > 18h): Se divide")
            camiones_a_dividir.append(camion)
        
        # 2. Si tiempo <= 18h y ocupación >= 75% → Sale hoy
        elif tiempo_total <= 18.0 and porcentaje_ocupacion >= 75.0:
            print("  ✅ CUMPLE: Sale hoy (ocupación ≥75%)")
            camion.estado = "en_ruta"
            camiones_que_salen.append(camion)
            # Registrar la expedición cuando el camión sale
            if camion.destinos and len(camion.destinos) > 0:
                registrar_expedicion_salida(camion, fecha)
            else:
                print(f"  ⚠️ ADVERTENCIA: Camión {camion.id_camion} sale sin destinos")
        
        # 3. Si tiempo <= 18h y ocupación entre 50-75% → Zona de decisión
        elif tiempo_total <= 18.0 and porcentaje_ocupacion >= 50.0:
            # Zona de decisión (50-75%)
            if es_urgente:
                print(f"  ⚡ CON CADUCIDAD URGENTE: Sale hoy ({porcentaje_ocupacion:.1f}% ocupación)")
                print("     (Productos caducan en ≤2 días)")
                camion.estado = "en_ruta"
                camiones_que_salen.append(camion)
                # Registrar la expedición cuando el camión sale
                if camion.destinos and len(camion.destinos) > 0:
                    registrar_expedicion_salida(camion, fecha)
                else:
                    print(f"  ⚠️ ADVERTENCIA: Camión {camion.id_camion} sale sin destinos")
            else:
                print("  ⏳ OCUPACIÓN MEDIA (50-75%): Espera mañana")
                print("     (Sin urgencia de caducidad)")
                camiones_con_baja_ocupacion.append(camion)
        
        # 4. Si ocupación < 50% → Espera mañana
        elif porcentaje_ocupacion < 50.0:
            print("  ⏳ BAJA OCUPACIÓN (<50%): Espera mañana")
            camiones_con_baja_ocupacion.append(camion)
        
        # 5. Caso especial: Sin destinos pero con carga (no debería pasar)
        elif not camion.destinos or len(camion.destinos) == 0:
            print("  ⚠️ SIN DESTINOS: Espera asignación de destinos")
            camiones_con_baja_ocupacion.append(camion)
    
    # Dividir camiones grandes (mantener misma lógica)
    camiones_divididos_totales = 0
    for camion in camiones_a_dividir:
        if camion in camiones_normales:
            camiones_normales.remove(camion)
        
        # Solo dividir si tiene destinos
        if camion.destinos and len(camion.destinos) > 0:
            camiones_divididos = dividir_ruta_inteligente(camion, df_matriz)
            camiones_divididos_totales += len(camiones_divididos)
            
            for nuevo_camion in camiones_divididos:
                nuevo_camion.optimizar_rutas(df_matriz)
                seleccionar_mejor_ruta_automatico(nuevo_camion)
                
                nuevo_ocupacion = (nuevo_camion.peso_actual / nuevo_camion.peso_maximo) * 100
                nuevo_urgente = tiene_caducidad_urgente(nuevo_camion, fecha) if nuevo_camion.productos_asignados else False
                
                # Aplicar mismas reglas a camiones divididos
                if (nuevo_camion.tiempo_final <= 18.0 and 
                    (nuevo_ocupacion >= 75.0 or (nuevo_ocupacion >= 50.0 and nuevo_urgente))):
                    nuevo_camion.estado = "en_ruta"
                    camiones_que_salen.append(nuevo_camion)
                    camiones_creados.append(nuevo_camion)
                    print(f"  ✅ Camión {nuevo_camion.id_camion} creado y sale hoy")
                    # Registrar expedición para camiones divididos que salen
                    if nuevo_camion.destinos and len(nuevo_camion.destinos) > 0:
                        registrar_expedicion_salida(nuevo_camion, fecha)
                else:
                    camiones_normales.append(nuevo_camion)
                    camiones_creados.append(nuevo_camion)
                    print(f"  ⏳ Camión {nuevo_camion.id_camion} creado, espera para mañana")
        else:
            print(f"  ⚠️ No se puede dividir camión {camion.id_camion}: no tiene destinos")
    
    print(f"\n{'='*60}")
    print("RESUMEN CON CADUCIDAD:")
    print(f"  Camiones que SALEN hoy: {len(camiones_que_salen)}")
    print(f"  Camiones DIVIDIDOS: {len(camiones_a_dividir)} → {camiones_divididos_totales} nuevos camiones")
    print(f"  Camiones con BAJA OCUPACIÓN (<50%): {len(camiones_con_baja_ocupacion)}")
    print(f"  Camiones VACÍOS (sin carga ni destinos): {len(camiones_vacios)}")
    print(f"  Camiones con OCUPACIÓN MEDIA (50-75% sin urgencia): {len([c for c in camiones_con_baja_ocupacion if (c.peso_actual/c.peso_maximo*100) >= 50])}")
    print(f"  Camiones normales ACTIVOS para mañana: {len(camiones_normales)}")
    
    # Mostrar expediciones registradas hoy
    if camiones_que_salen:
        print(f"\n📋 EXPEDICIONES REGISTRADAS HOY ({fecha}):")
        for camion in camiones_que_salen:
            # Buscar la expedición recién registrada
            expedicion_encontrada = False
            for expedicion in expediciones_activas:
                if expedicion['id_camion'] == camion.id_camion and expedicion['fecha_salida'] == fecha:
                    print(f"  • Camión {camion.id_camion}: Retorna el {expedicion['fecha_retorno_estimada']}")
                    expedicion_encontrada = True
                    break
            
            if not expedicion_encontrada and camion.destinos and len(camion.destinos) > 0:
                print(f"  ⚠️ Camión {camion.id_camion}: Expedición no registrada (error)")
    
    # Advertencia si hay muchos camiones vacíos
    if len(camiones_vacios) > 5:
        print(f"\n⚠️  ADVERTENCIA: Hay {len(camiones_vacios)} camiones vacíos")
        print("   Considera limpiar camiones vacíos persistentes")
    
    print(f"{'='*60}")

# ========== FUNCIONES AUXILIARES ==========

def buscar_camion_especial_destino(destino_id):
    """Busca camión especial existente para un destino específico."""
    for camion in camiones_especiales:
        if (camion.es_especial and 
            camion.destinos and 
            destino_id in camion.destinos and
            camion.capacidad_disponible() > 0 and
            camion.estado != "en_ruta"):
            return camion
    return None

def crear_nuevo_camion_normal(fecha, destino_id):
    """Crea un nuevo camión normal (función de respaldo)."""
    global Id_camiones, camiones_normales, camiones_creados
    
    Id_camiones += 1
    nuevo_camion = Camion(
        id_camion=Id_camiones,
        peso_maximo=Peso_maximo,
        fecha_salida=fecha,
        es_especial=False
    )
    camiones_normales.append(nuevo_camion)
    camiones_creados.append(nuevo_camion)
    print(f"  🚚 Nuevo camión normal {Id_camiones} creado (respaldado)")
    return nuevo_camion

def crear_camion_ruta_especial(destino_id, fecha_salida):
    """Crea un nuevo camión para rutas especiales."""
    global Id_camiones
    Id_camiones += 1
    return Camion(
        id_camion=Id_camiones,
        peso_maximo=Peso_maximo,
        fecha_salida=fecha_salida,
        es_especial=True
    )

# ========== FUNCIONES RESTANTES (sin cambios significativos) ==========

def mostrar_estado_camiones_actual(fecha):
    print(f"\n📊 ESTADO AL INICIO DEL DÍA {fecha}:")
    print(f"Camiones especiales: {len(camiones_especiales)}")
    print(f"Camiones normales: {len(camiones_normales)}")
    print(f"Pedidos pendientes: {len(pedidos_pendientes)}")

def optimizar_rutas_fecha_actual(fecha):
    """Función original de optimización (mantenida para compatibilidad)."""
    print(f"\n{'='*60}")
    print(f"OPTIMIZANDO RUTAS - FECHA {fecha}")
    print(f"{'='*60}")
    
    if camiones_normales:
        print(f"\nCamiones normales a optimizar: {len(camiones_normales)}")
        
        for camion in camiones_normales:
            if len(camion.destinos) > 0 and camion.estado != "en_ruta":
                print(f"\n{'─'*40}")
                print(f"Camion {camion.id_camion}:")
                print(f"  Destinos: {camion.destinos}")
                print(f"  Carga: {camion.peso_actual}/{camion.peso_maximo}kg")
                
                if hasattr(camion, 'optimizar_rutas'):
                    camion.optimizar_rutas(df_matriz)
                    if hasattr(camion, 'mostrar_comparacion_rutas'):
                        camion.mostrar_comparacion_rutas()
                    seleccionar_mejor_ruta_automatico(camion)

def estimar_tiempo_ruta(destinos):
    """Estima tiempo de una ruta. Devuelve 0 si no hay destinos."""
    if not destinos or len(destinos) == 0:
        return 0.0
    
    tiempo_total = 0
    for destino in destinos:
        tiempo_total += df_matriz.loc[0, str(destino)]
    
    if destinos:
        tiempo_total += df_matriz.loc[destinos[-1], '0']
    
    return tiempo_total

def seleccionar_mejor_ruta_automatico(camion):
    """Selecciona la mejor ruta automáticamente. SOLO si hay destinos."""
    
    # Si no hay destinos, NO calcular tiempos
    if not camion.destinos or len(camion.destinos) == 0:
        if hasattr(camion, 'tiempo_final'):
            camion.tiempo_final = 0
        if hasattr(camion, 'ruta_final'):
            camion.ruta_final = None
        return  # ← SALIR TEMPRANO
    
    if hasattr(camion, 'seleccionar_mejor_ruta'):
        camion.seleccionar_mejor_ruta()
    else:
        tiempos = []
        
        if hasattr(camion, 'tiempo_fuerza_bruta') and camion.tiempo_fuerza_bruta:
            tiempos.append(('fuerza_bruta', camion.tiempo_fuerza_bruta))
        
        if hasattr(camion, 'tiempo_vecino_cercano'):
            tiempos.append(('vecino_cercano', camion.tiempo_vecino_cercano))
        
        if hasattr(camion, 'tiempo_insercion'):
            tiempos.append(('insercion', camion.tiempo_insercion))
        
        if tiempos:
            tiempos.sort(key=lambda x: x[1])
            mejor_algoritmo, mejor_tiempo = tiempos[0]
            
            print(f"  ✓ Seleccionado: {mejor_algoritmo.replace('_', ' ').title()}")
            print(f"    Tiempo: {mejor_tiempo:.2f}h")
            
            if mejor_algoritmo == 'fuerza_bruta':
                camion.ruta_final = camion.ruta_fuerza_bruta
            elif mejor_algoritmo == 'vecino_cercano':
                camion.ruta_final = camion.ruta_vecino_cercano
            elif mejor_algoritmo == 'insercion':
                camion.ruta_final = camion.ruta_insercion
            
            camion.tiempo_final = mejor_tiempo
        else:
            # Si no hay tiempos calculados, estimar
            if camion.destinos:
                camion.tiempo_final = estimar_tiempo_ruta(camion.destinos)

def mostrar_resumen_fecha(fecha):
    print(f"\n{'='*80}")
    print(f"RESUMEN FINAL - FECHA {fecha}")
    print(f"{'='*80}")
    
    camiones_en_ruta = [c for c in camiones_creados if c.estado == "en_ruta"]
    camiones_especiales_activos = [c for c in camiones_especiales if c.estado != "en_ruta"]
    camiones_normales_activos = [c for c in camiones_normales if c.estado != "en_ruta"]
    
    # FILTRAR: Solo camiones normales que tienen carga o destinos
    camiones_normales_con_carga = [c for c in camiones_normales_activos 
                                   if (c.peso_actual > 0 or 
                                       (hasattr(c, 'destinos') and c.destinos))]
    
    print("\n📊 ESTADO AL FINAL DEL DÍA:")
    print(f"Camiones especiales activos: {len(camiones_especiales_activos)}")
    print(f"Camiones normales con carga: {len(camiones_normales_con_carga)}")
    print(f"Camiones normales vacíos: {len(camiones_normales_activos) - len(camiones_normales_con_carga)}")
    print(f"Camiones en ruta: {len(camiones_en_ruta)}")
    print(f"Pedidos pendientes para mañana: {len(pedidos_pendientes)}")
    
    # Mostrar expediciones activas
    if expediciones_activas:
        print(f"\n🚛 EXPEDICIONES EN CURSO ({len(expediciones_activas)}):")
        for exp in expediciones_activas:
            if exp['estado'] == 'en_viaje':
                print(f"  • Camión {exp['id_camion']}: Salió {exp['fecha_salida']}, Retorna {exp['fecha_retorno_estimada']}")
                print(f"    Destinos: {exp['destinos']}")
    
    if camiones_especiales_activos:
        print("\n🔵 CAMIONES ESPECIALES (persistentes):")
        for camion in camiones_especiales_activos:
            if camion.peso_actual > 0:  # Solo mostrar si tienen carga
                print(f"  Camión {camion.id_camion}: Destino {camion.destinos}, " +
                      f"Carga: {camion.peso_actual}/{camion.peso_maximo}kg")
    
    if camiones_normales_con_carga:
        print("\n🟢 CAMIONES NORMALES CON CARGA:")
        for camion in camiones_normales_con_carga:
            tiempo = camion.tiempo_final if hasattr(camion, 'tiempo_final') else estimar_tiempo_ruta(camion.destinos)
            ocupacion = (camion.peso_actual / camion.peso_maximo) * 100
            print(f"  Camión {camion.id_camion}: Destinos {camion.destinos}, " +
                  f"Carga: {camion.peso_actual}/{camion.peso_maximo}kg ({ocupacion:.1f}%), " +
                  f"Tiempo: {tiempo:.2f}h")

def extraer_info_pedido(pedido):
    """Extrae información de un pedido en diferentes formatos."""
    info = {
        'DestinoEntregaID': None,
        'Cantidad': None,
        'ProductoID': 'desconocido',
        'es_pendiente': True
    }
    
    # Si es diccionario
    if isinstance(pedido, dict):
        info['DestinoEntregaID'] = pedido.get('DestinoEntregaID') or pedido.get('destino_id')
        info['Cantidad'] = pedido.get('Cantidad') or pedido.get('cantidad')
        info['ProductoID'] = pedido.get('ProductoID') or pedido.get('producto_id', 'desconocido')
    
    # Si es objeto con atributos
    elif hasattr(pedido, '__dict__'):
        info['DestinoEntregaID'] = getattr(pedido, 'DestinoEntregaID', None) or getattr(pedido, 'destino_id', None)
        info['Cantidad'] = getattr(pedido, 'Cantidad', None) or getattr(pedido, 'cantidad', None)
        info['ProductoID'] = getattr(pedido, 'ProductoID', None) or getattr(pedido, 'producto_id', 'desconocido')
    
    # Si es una tupla con estructura conocida (ej: (destino, cantidad, producto))
    elif isinstance(pedido, (tuple, list)) and len(pedido) >= 2:
        info['DestinoEntregaID'] = pedido[0] if len(pedido) > 0 else None
        info['Cantidad'] = pedido[1] if len(pedido) > 1 else None
        info['ProductoID'] = pedido[2] if len(pedido) > 2 else 'desconocido'
    
    # Verificar que tenemos información mínima
    if info['DestinoEntregaID'] is not None and info['Cantidad'] is not None:
        return info
    else:
        print(f"⚠️ No se pudo extraer información completa del pedido: {pedido}")
        return None
def mostrar_camiones_en_ruta():
    """Muestra todos los camiones que están actualmente en ruta."""
    
    print(f"\n{'='*80}")
    print("🚚 CAMIONES EN RUTA (ACTIVOS)")
    print(f"{'='*80}")
    print(f"Camiones en memoria actualmente: {len(camiones_creados)}")
    # Filtrar camiones en ruta
    camiones_en_ruta = [c for c in camiones_creados if c.estado == "en_ruta"]
    camiones_especiales_ruta = [c for c in camiones_especiales if c.estado == "en_ruta"]
    camiones_normales_ruta = [c for c in camiones_normales if c.estado == "en_ruta"]
    
    if not camiones_en_ruta:
        print("No hay camiones en ruta en este momento.")
        return
    
    print("\n📊 RESUMEN:")
    print(f"  Total camiones en ruta: {len(camiones_en_ruta)}")
    print(f"  Camiones especiales en ruta: {len(camiones_especiales_ruta)}")
    print(f"  Camiones normales en ruta: {len(camiones_normales_ruta)}")
    
    # Calcular estadísticas
    peso_total = sum(c.peso_actual for c in camiones_en_ruta)
    tiempo_total = sum(c.tiempo_final for c in camiones_en_ruta if hasattr(c, 'tiempo_final'))
    destinos_total = sum(len(c.destinos) for c in camiones_en_ruta)
    
    print("\n📈 ESTADÍSTICAS:")
    print(f"  Peso total transportado: {peso_total:,}kg")
    print(f"  Tiempo total de ruta: {tiempo_total:.2f}h")
    print(f"  Destinos totales cubiertos: {destinos_total}")
    print(f"  Eficiencia promedio: {destinos_total/tiempo_total:.3f} destinos/hora" if tiempo_total > 0 else "  Eficiencia promedio: N/A")
    
    # Mostrar camiones especiales en ruta
    if camiones_especiales_ruta:
        print("\n🔵 CAMIONES ESPECIALES EN RUTA:")
        for camion in camiones_especiales_ruta:
            tiempo = camion.tiempo_final if hasattr(camion, 'tiempo_final') else df_matriz.loc[0, str(camion.destinos[0])] * 2
            print(f"  • Camión {camion.id_camion}:")
            print(f"     Destinos: {camion.destinos}")
            print(f"     Peso: {camion.peso_actual}/{camion.peso_maximo}kg ({(camion.peso_actual/camion.peso_maximo*100):.1f}%)")
            print(f"     Tiempo estimado: {tiempo:.2f}h")
            if hasattr(camion, 'ruta_final') and camion.ruta_final:
                print(f"     Ruta: {camion.ruta_final}")
    
    # Mostrar camiones normales en ruta
    if camiones_normales_ruta:
        print("\n🟢 CAMIONES NORMALES EN RUTA:")
        for camion in camiones_normales_ruta:
            tiempo = camion.tiempo_final if hasattr(camion, 'tiempo_final') else estimar_tiempo_ruta(camion.destinos)
            print(f"  • Camión {camion.id_camion}:")
            print(f"     Destinos: {camion.destinos}")
            print(f"     Peso: {camion.peso_actual}/{camion.peso_maximo}kg ({(camion.peso_actual/camion.peso_maximo*100):.1f}%)")
            print(f"     Tiempo: {tiempo:.2f}h")
            if hasattr(camion, 'ruta_final') and camion.ruta_final:
                print(f"     Ruta óptima: {camion.ruta_final}")
            if hasattr(camion, 'eficiencia'):
                print(f"     Eficiencia: {camion.eficiencia:.3f} destinos/hora")
    
    # Mostrar por fecha de salida (si están agrupados)
    fechas_salida = {}
    for camion in camiones_en_ruta:
        fecha = camion.fecha_salida if hasattr(camion, 'fecha_salida') else 'Sin fecha'
        if fecha not in fechas_salida:
            fechas_salida[fecha] = []
        fechas_salida[fecha].append(camion)
    
    if len(fechas_salida) > 1:
        print("\n📅 DISTRIBUCIÓN POR FECHA DE SALIDA:")
        for fecha, camiones_fecha in sorted(fechas_salida.items()):
            print(f"  {fecha}: {len(camiones_fecha)} camiones")
    
    print(f"\n{'='*80}")
    
def tiene_caducidad_urgente(camion, fecha_actual):
    """
    Verifica si algún pedido del camión tiene caducidad urgente.
    Urgente = caduca en 2 días o menos.
    """
    if not camion.productos_asignados:
        return False
    
    fecha_actual_dt = datetime.strptime(fecha_actual, '%Y-%m-%d')
    
    for pedido in camion.productos_asignados:
        fecha_caducidad = None
        
        # Extraer fecha de caducidad según el formato
        if isinstance(pedido, dict):
            if 'FechaCaducidad' in pedido:
                fecha_caducidad = datetime.strptime(pedido['FechaCaducidad'], '%Y-%m-%d')
            elif 'fecha_caducidad' in pedido:
                fecha_caducidad = datetime.strptime(pedido['fecha_caducidad'], '%Y-%m-%d')
        elif hasattr(pedido, 'FechaCaducidad'):
            fecha_caducidad = datetime.strptime(pedido.FechaCaducidad, '%Y-%m-%d')
        elif hasattr(pedido, 'fecha_caducidad'):
            fecha_caducidad = datetime.strptime(pedido.fecha_caducidad, '%Y-%m-%d')
        
        if fecha_caducidad:
            dias_hasta_caducidad = (fecha_caducidad - fecha_actual_dt).days
            
            # Considerar urgente si caduca en 2 días o menos
            if dias_hasta_caducidad <= 2:
                return True
    
    return False

def obtener_dias_hasta_caducidad_mas_cercana(camion, fecha_actual):
    """Obtiene los días hasta la caducidad más cercana en el camión."""
    if not camion.productos_asignados:
        return float('inf')
    
    fecha_actual_dt = datetime.strptime(fecha_actual, '%Y-%m-%d')
    dias_minimos = float('inf')
    
    for pedido in camion.productos_asignados:
        fecha_caducidad = None
        
        if isinstance(pedido, dict):
            if 'FechaCaducidad' in pedido:
                fecha_caducidad = datetime.strptime(pedido['FechaCaducidad'], '%Y-%m-%d')
            elif 'fecha_caducidad' in pedido:
                fecha_caducidad = datetime.strptime(pedido['fecha_caducidad'], '%Y-%m-%d')
        elif hasattr(pedido, 'FechaCaducidad'):
            fecha_caducidad = datetime.strptime(pedido.FechaCaducidad, '%Y-%m-%d')
        elif hasattr(pedido, 'fecha_caducidad'):
            fecha_caducidad = datetime.strptime(pedido.fecha_caducidad, '%Y-%m-%d')
        
        if fecha_caducidad:
            dias = (fecha_caducidad - fecha_actual_dt).days
            dias_minimos = min(dias_minimos, dias)
    
    return dias_minimos if dias_minimos != float('inf') else None

def calcular_dias_para_retorno(tiempo_ruta_horas):
    """
    Calcula días necesarios para que un camión retorne.
    Basado en tiempo máximo de conducción por día (9h).
    """
    if tiempo_ruta_horas <= 9.0:
        return 1  # Vuelve al día siguiente
    elif tiempo_ruta_horas <= 18.0:
        return 2  # Vuelve en 2 días
    else:
        # Para rutas > 18h (deberían estar divididas)
        return math.ceil(tiempo_ruta_horas / 9.0)

def calcular_fecha_retorno(fecha_salida_str, tiempo_ruta_horas):
    """
    Calcula la fecha en que el camión estará disponible nuevamente.
    """
    if not fecha_salida_str:
        return None
    
    dias_retorno = calcular_dias_para_retorno(tiempo_ruta_horas)
    fecha_salida = datetime.strptime(fecha_salida_str, '%Y-%m-%d')
    fecha_retorno = fecha_salida + timedelta(days=dias_retorno)
    return fecha_retorno.strftime('%Y-%m-%d')

def actualizar_disponibilidad_camiones(fecha_actual_str):
    """
    Actualiza camiones que han completado sus rutas y están disponibles.
    """
    camiones_que_retornan = []
    expediciones_completadas_hoy = []
    
    # Verificar expediciones activas
    for expedicion in expediciones_activas[:]:
        if expedicion.get('estado') == 'en_viaje' and expedicion.get('fecha_retorno_estimada'):
            if fecha_actual_str >= expedicion['fecha_retorno_estimada']:
                # Buscar el camión correspondiente
                for camion in camiones_creados:
                    if camion.id_camion == expedicion['id_camion'] and camion.estado == "en_ruta":
                        print(f"  ✅ Camión {camion.id_camion} ha retornado (salió {expedicion['fecha_salida']})")
                        
                        # Actualizar expedición
                        expedicion['estado'] = 'completado'
                        expedicion['fecha_real_retorno'] = fecha_actual_str
                        expediciones_completadas_hoy.append(expedicion.copy())
                        
                        # NUEVO: Actualizar en CSV
                        actualizar_retorno_expedicion_csv(camion.id_camion, fecha_actual_str)
                        
                        camiones_que_retornan.append(camion)
                        break
    
    # Reiniciar camiones que han retornado
    for camion in camiones_que_retornan:
        reiniciar_camion_disponible(camion)
    
    # Quitar expediciones completadas de la lista activa
    expediciones_activas[:] = [e for e in expediciones_activas if e.get('estado') == 'en_viaje']
    
    if expediciones_completadas_hoy:
        print(f"  📊 {len(expediciones_completadas_hoy)} expediciones completadas hoy")
    
    return len(camiones_que_retornan)

def actualizar_retorno_expedicion_csv(id_camion, fecha_real_retorno, archivo="expediciones_camiones.csv"):
    """Actualiza el CSV cuando un camión retorna."""
    
    if not os.path.exists(archivo):
        print(f"⚠️ Archivo {archivo} no existe. No se puede actualizar retorno.")
        return False
    
    try:
        df = pd.read_csv(archivo)
        
        # Buscar la expedición más reciente de este camión que esté en_viaje
        mask = (df['id_camion'] == id_camion) & (df['estado'] == 'en_viaje')
        
        if mask.any():
            # Actualizar la última expedición en_viaje
            idx = df[mask].index[-1]
            df.at[idx, 'fecha_real_retorno'] = fecha_real_retorno
            df.at[idx, 'estado'] = 'completado'
            df.at[idx, 'timestamp_actualizacion'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # Guardar cambios
            df.to_csv(archivo, index=False, encoding='utf-8')
            
            print(f"    ✅ Actualizado CSV: Camión {id_camion} retornó el {fecha_real_retorno}")
            return True
        else:
            print(f"    ⚠️ No se encontró expedición en_viaje para camión {id_camion}")
            return False
            
    except Exception as e:
        print(f"⚠️ Error actualizando CSV: {e}")
        return False

def reiniciar_camion_disponible(camion):
    """
    Reinicia un camión para que esté disponible nuevamente.
    Asegura que quede completamente vacío.
    """
    print(f"  🔄 Reiniciando camión {camion.id_camion} para reutilización")
    
    # Guardar tipo original
    era_especial = camion.es_especial
    
    # Limpiar estado COMPLETAMENTE
    camion.estado = None  # No "en_ruta" = disponible
    camion.productos_asignados = []
    camion.peso_actual = 0
    camion.destinos = []  # ← Vaciar destinos
    
    # Asegurar que todos los tiempos se pongan a 0
    if hasattr(camion, 'ruta_final'):
        camion.ruta_final = None
    if hasattr(camion, 'tiempo_final'):
        camion.tiempo_final = 0
    if hasattr(camion, 'tiempo_fuerza_bruta'):
        camion.tiempo_fuerza_bruta = 0
    if hasattr(camion, 'tiempo_vecino_cercano'):
        camion.tiempo_vecino_cercano = 0
    if hasattr(camion, 'tiempo_insercion'):
        camion.tiempo_insercion = 0
    
    # Limpiar rutas calculadas
    if hasattr(camion, 'ruta_fuerza_bruta'):
        camion.ruta_fuerza_bruta = None
    if hasattr(camion, 'ruta_vecino_cercano'):
        camion.ruta_vecino_cercano = None
    if hasattr(camion, 'ruta_insercion'):
        camion.ruta_insercion = None
    
    # Si era especial, convertirlo a normal para reutilización
    if era_especial:
        camion.es_especial = False
        if camion in camiones_especiales:
            camiones_especiales.remove(camion)
        camiones_normales.append(camion)
        print("    → Convertido de especial a normal para reutilización")
    
    print(f"    ✅ Camión {camion.id_camion} completamente vacío y listo para reutilizar")
        
def verificar_reutilizacion_camiones():
    """Verifica si los camiones se están reutilizando."""
    print(f"\n{'='*60}")
    print("🔄 VERIFICACIÓN DE REUTILIZACIÓN DE CAMIONES")
    print(f"{'='*60}")
    
    # IDs de camiones que han estado en ruta
    ids_en_ruta = set()
    for camion in camiones_creados:
        if hasattr(camion, 'estado') and camion.estado == "en_ruta":
            ids_en_ruta.add(camion.id_camion)
    
    # Camiones disponibles
    disponibles = [c for c in camiones_creados if not hasattr(c, 'estado') or camion.estado != "en_ruta"]
    
    print(f"Total camiones creados: {Id_camiones}")
    print(f"Camiones en memoria: {len(camiones_creados)}")
    print(f"Camiones en ruta ahora: {len(ids_en_ruta)}")
    print(f"Camiones disponibles: {len(disponibles)}")
    
    if disponibles:
        print(f"IDs disponibles para reutilizar: {[c.id_camion for c in disponibles]}")
    
    # Verificar si hay IDs reutilizados
    if len(camiones_creados) < Id_camiones:
        print(f"♻️  POSIBLE REUTILIZACIÓN: {Id_camiones - len(camiones_creados)} camiones eliminados/consolidados")
    else:
        print("⚠️  SIN REUTILIZACIÓN: Todos los camiones creados siguen en memoria")
        
def mostrar_expediciones_activas():
    """Muestra las expediciones en curso."""
    if not expediciones_activas:
        print("  ℹ️ No hay expediciones activas")
        return
    
    print(f"\n🚛 EXPEDICIONES EN CURSO ({len(expediciones_activas)}):")
    for exp in expediciones_activas:
        print(f"  • Camión {exp['id_camion']}: Salió {exp['fecha_salida']}, Retorna {exp['fecha_retorno_estimada']}")
        print(f"    Destinos: {exp['destinos']}, Tiempo: {exp['tiempo_ruta']:.2f}h, Peso: {exp['peso']}kg")
        
def limpiar_camiones_vacios():
    """Elimina camiones que han estado vacíos por muchos días."""
    global camiones_normales, camiones_creados, camiones_especiales
    
    camiones_a_eliminar = []
    
    # Camiones normales vacíos por más de 3 días
    for camion in camiones_normales[:]:
        if (camion.estado != "en_ruta" and 
            camion.peso_actual == 0 and 
            (not camion.destinos or len(camion.destinos) == 0)):
            # Verificar si es un camión recién creado o muy antiguo
            # (esto es un ejemplo, ajusta según tu lógica)
            camiones_a_eliminar.append(camion)
    
    # Camiones especiales con muy poca carga
    for camion in camiones_especiales[:]:
        if (camion.estado != "en_ruta" and 
            camion.peso_actual < 500):  # Menos de 500kg
            # Considerar eliminar si hay muchos especiales
            if len(camiones_especiales) > 10:  # Si hay más de 10 especiales
                camiones_a_eliminar.append(camion)
    
    if camiones_a_eliminar:
        print(f"\n🧹 LIMPIANDO {len(camiones_a_eliminar)} CAMIONES VACÍOS/INEFICIENTES")
        for camion in camiones_a_eliminar:
            print(f"  • Eliminando camión {camion.id_camion} ({'especial' if camion.es_especial else 'normal'})")
            
            if camion in camiones_normales:
                camiones_normales.remove(camion)
            if camion in camiones_especiales:
                camiones_especiales.remove(camion)
            if camion in camiones_creados:
                camiones_creados.remove(camion)
        
        print("  ✅ Limpieza completada")
        print(f"     Camiones normales: {len(camiones_normales)}")
        print(f"     Camiones especiales: {len(camiones_especiales)}")
        print(f"     Total camiones: {len(camiones_creados)}")
    
    return len(camiones_a_eliminar)

def exportar_resumen_final_expediciones(archivo="resumen_expediciones.csv"):
    """Exporta un resumen final de todas las expediciones."""
    
    try:
        if os.path.exists("expediciones_camiones.csv"):
            df = pd.read_csv("expediciones_camiones.csv")
            
            # Crear resumen por día
            resumen_por_dia = df.groupby('fecha_salida').agg({
                'id_expedicion': 'count',
                'id_camion': lambda x: list(x),
                'total_productos': 'sum',
                'peso_carga_kg': 'sum',
                'num_destinos': 'sum'
            }).reset_index()
            
            resumen_por_dia.columns = ['fecha', 'num_expediciones', 'camiones', 'total_productos', 'peso_total_kg', 'total_destinos']
            
            # Calcular estadísticas
            resumen_por_dia['productos_por_expedicion'] = resumen_por_dia['total_productos'] / resumen_por_dia['num_expediciones']
            resumen_por_dia['peso_promedio_kg'] = resumen_por_dia['peso_total_kg'] / resumen_por_dia['num_expediciones']
            
            # Guardar resumen
            resumen_por_dia.to_csv(archivo, index=False, encoding='utf-8')
            
            print(f"\n📊 RESUMEN EXPORTADO a {archivo}")
            print(f"   Días procesados: {len(resumen_por_dia)}")
            print(f"   Total expediciones: {resumen_por_dia['num_expediciones'].sum()}")
            print(f"   Total productos enviados: {resumen_por_dia['total_productos'].sum()}")
            print(f"   Total peso transportado: {resumen_por_dia['peso_total_kg'].sum():,.0f}kg")
            
            return archivo
            
        else:
            print("⚠️ No hay datos de expediciones para exportar.")
            return None
            
    except Exception as e:
        print(f"⚠️ Error exportando resumen: {e}")
        return None

def guardar_expedicion_csv(expedicion, archivo="expediciones_camiones.csv"):
    """Guarda o actualiza una expedición en el archivo CSV."""
    
    # Preparar datos para la fila del CSV
    fila = {
        'id_expedicion': len(pd.read_csv(archivo).index) + 1 if os.path.exists(archivo) else 1,
        'id_camion': expedicion['id_camion'],
        'tipo_camion': expedicion['tipo'],
        'fecha_salida': expedicion['fecha_salida'],
        'fecha_retorno_estimada': expedicion['fecha_retorno_estimada'],
        'fecha_real_retorno': expedicion['fecha_real_retorno'] or '',
        'tiempo_ruta_horas': f"{expedicion['tiempo_ruta_horas']:.2f}",
        'dias_viaje': expedicion['dias_retorno'],
        'ruta_completa': expedicion['ruta_str'],
        'destinos': '|'.join(map(str, expedicion['destinos'])) if expedicion['destinos'] else '',
        'num_destinos': len(expedicion['destinos']),
        'peso_carga_kg': expedicion['peso_kg'],
        'peso_maximo_kg': expedicion['peso_maximo_kg'],
        'porcentaje_ocupacion': f"{expedicion['porcentaje_ocupacion']:.1f}",
        'productos_resumen': expedicion['productos_resumen'],
        'total_productos': expedicion['total_productos'],
        'destinos_productos': expedicion['destinos_productos'],
        'fecha_caducidad_proxima': expedicion['fecha_caducidad_proxima'] or '',
        'dias_caducidad_proxima': expedicion['dias_caducidad_proxima'] or '',
        'estado': expedicion['estado'],
        'timestamp_registro': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    # Crear DataFrame con la nueva fila
    nueva_fila_df = pd.DataFrame([fila])
    
    # Verificar si el archivo existe
    if os.path.exists(archivo):
        try:
            # Leer CSV existente
            df_existente = pd.read_csv(archivo)
            # Concatenar nueva fila
            df_completo = pd.concat([df_existente, nueva_fila_df], ignore_index=True)
        except Exception as e:
            print(f"⚠️ Error leyendo CSV existente: {e}. Creando nuevo archivo.")
            df_completo = nueva_fila_df
    else:
        df_completo = nueva_fila_df
    
    # Guardar en CSV
    df_completo.to_csv(archivo, index=False, encoding='utf-8')
    
    return fila['id_expedicion']
def extraer_info_productos_detallada(camion, fecha_actual):
    """Extrae información detallada de todos los productos de un camión."""
    productos_info = []
    
    for pedido in camion.productos_asignados:
        info = {
            'producto_id': 'desconocido',
            'cantidad': 0,
            'destino_id': None,
            'fecha_caducidad': None,
            'dias_hasta_caducidad': None,
            'fecha_fabricacion': None
        }
        
        # Extraer según formato del pedido
        if isinstance(pedido, dict):
            info['producto_id'] = pedido.get('ProductoID', pedido.get('producto_id', 'desconocido'))
            info['cantidad'] = pedido.get('Cantidad', pedido.get('cantidad', 0))
            info['destino_id'] = pedido.get('DestinoEntregaID', pedido.get('destino_id'))
            info['fecha_caducidad'] = pedido.get('FechaCaducidad', pedido.get('fecha_caducidad'))
            info['fecha_fabricacion'] = pedido.get('FechaFinFabricacion', pedido.get('fecha_fabricacion'))
        
        elif hasattr(pedido, '__dict__'):
            info['producto_id'] = getattr(pedido, 'ProductoID', getattr(pedido, 'producto_id', 'desconocido'))
            info['cantidad'] = getattr(pedido, 'Cantidad', getattr(pedido, 'cantidad', 0))
            info['destino_id'] = getattr(pedido, 'DestinoEntregaID', getattr(pedido, 'destino_id', None))
            info['fecha_caducidad'] = getattr(pedido, 'FechaCaducidad', getattr(pedido, 'fecha_caducidad', None))
            info['fecha_fabricacion'] = getattr(pedido, 'FechaFinFabricacion', getattr(pedido, 'fecha_fabricacion', None))
        
        # Calcular días hasta caducidad
        if info['fecha_caducidad'] and fecha_actual:
            try:
                fecha_cad_dt = datetime.strptime(info['fecha_caducidad'], '%Y-%m-%d')
                fecha_actual_dt = datetime.strptime(fecha_actual, '%Y-%m-%d')
                info['dias_hasta_caducidad'] = (fecha_cad_dt - fecha_actual_dt).days
            except:
                info['dias_hasta_caducidad'] = None
        
        if info['producto_id'] != 'desconocido' and info['cantidad'] > 0:
            productos_info.append(info)
    
    return productos_info

def calcular_caducidad_mas_proxima(productos_info):
    """Calcula la fecha de caducidad más próxima de una lista de productos."""
    if not productos_info:
        return None, None
    
    fecha_mas_proxima = None
    dias_minimos = float('inf')
    
    for producto in productos_info:
        if producto['dias_hasta_caducidad'] is not None:
            if producto['dias_hasta_caducidad'] < dias_minimos:
                dias_minimos = producto['dias_hasta_caducidad']
                fecha_mas_proxima = producto['fecha_caducidad']
    
    return fecha_mas_proxima, dias_minimos if dias_minimos != float('inf') else None

def obtener_resumen_productos(productos_info):
    """Crea un resumen de productos para el CSV."""
    if not productos_info:
        return "SIN_PRODUCTOS", 0, ""
    
    # Agrupar por producto_id
    productos_agrupados = {}
    for prod in productos_info:
        producto_id = str(prod['producto_id'])
        if producto_id not in productos_agrupados:
            productos_agrupados[producto_id] = {
                'cantidad_total': 0,
                'destinos': set(),
                'caducidad_minima': float('inf'),
                'fecha_caducidad_minima': None
            }
        
        productos_agrupados[producto_id]['cantidad_total'] += prod['cantidad']
        if prod['destino_id']:
            productos_agrupados[producto_id]['destinos'].add(str(prod['destino_id']))
        
        if prod['dias_hasta_caducidad'] is not None and prod['dias_hasta_caducidad'] < productos_agrupados[producto_id]['caducidad_minima']:
            productos_agrupados[producto_id]['caducidad_minima'] = prod['dias_hasta_caducidad']
            productos_agrupados[producto_id]['fecha_caducidad_minima'] = prod['fecha_caducidad']
    
    # Crear strings para CSV
    productos_str = "|".join([f"{pid}:{data['cantidad_total']}" for pid, data in productos_agrupados.items()])
    total_productos = sum(data['cantidad_total'] for data in productos_agrupados.values())
    destinos_str = "|".join(sorted(set().union(*[data['destinos'] for data in productos_agrupados.values()])))
    
    return productos_str, total_productos, destinos_str
# ========== EJECUCIÓN ==========
if __name__ == "__main__":
    comprobar_pedidos_fecha_produccion()
    verificar_reutilizacion_camiones()