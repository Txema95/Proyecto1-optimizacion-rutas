import pandas as pd
# En productos_fabricados_optimizer.py
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from app.camiones.Camiones import Camion

df_matriz = pd.read_csv('matriz_tiempos_destinos.csv', index_col=0)
Peso_maximo = 1800
camiones_normales = []
camion_normal_actual = None

def comprobar_pedidos_fecha_produccion():
    df = pd.read_csv("productos_fabricados.csv")
    fechas_unicas = df['FechaFinFabricacion'].unique()
    global camiones_creados, Id_camiones
    camiones_creados = []
    Id_camiones = 0
    for fecha in fechas_unicas:
        pedidos_entrega = df.loc[df['FechaFinFabricacion'] == fecha].copy()
        print(f"Procesando fecha: {fecha}")
        # Procesar cada pedido de esta fecha
        for index, producto in pedidos_entrega.iterrows():
            destino_id = producto['DestinoEntregaID']
            cantidad = producto['Cantidad']
            
            # Comprobar si es destino largo (≥ 8.5h)
            if df_matriz.loc[0, str(destino_id)] >= 8.5:
                print(f"Destino {destino_id}: {df_matriz.loc[0, str(destino_id)]}h → Camión especial")
                
                # Buscar camión con misma ruta
                camion_existente = buscar_camion_misma_ruta(destino_id)
                
                if camion_existente and camion_existente.agregar_producto(producto, cantidad, destino_id):
                    print(f"  ✓ Agregado a camión existente {camion_existente.id_camion}")
                else:
                    # Crear nuevo camión
                    nuevo_camion = crear_camion_ruta_especial(destino_id, fecha)
                    if nuevo_camion.agregar_producto(producto, cantidad,destino_id):
                        camiones_creados.append(nuevo_camion)
                        Id_camiones += 1
                        print(f"  ✓ Nuevo camión {nuevo_camion.id_camion} creado")
            else:
                print(f"Destino {destino_id}: {df_matriz.loc[0, str(destino_id)]}h → Ruta normal")
                agregar_pedido_normal_a_camion(producto, fecha, destino_id, cantidad)
        
        optimizar_rutas_fecha_actual(fecha)
        
        # MOSTRAR RESUMEN
        mostrar_resumen_fecha(fecha)
        break
        
def buscar_camion_misma_ruta(destino_id):
    """Busca un camión existente con la misma ruta y capacidad disponible."""
    for camion in camiones_creados:
        if (camion.ruta == destino_id and 
            camion.estado == "disponible" and
            camion.capacidad_disponible() > 0):
            return camion
    return None

def crear_camion_ruta_especial(destino_id, fecha_salida):
    """Crea un nuevo camión para rutas especiales."""
    nuevo_id = Id_camiones + 1
    return Camion(
        id_camion=nuevo_id,
        peso_maximo=Peso_maximo,
        fecha_salida=fecha_salida,
        ruta=destino_id,  # Usamos el destino como ruta
        es_especial=True
    )
    
def agregar_pedido_normal_a_camion(producto,fecha, destino_id,cantidad=int):
    global Id_camiones
    
    # Buscar camión normal con capacidad
    camion = None
    for c in camiones_normales:
        if c.capacidad_disponible() >= cantidad:
            camion = c
            break
    
    # Si no hay camión con capacidad, crear uno nuevo
    if not camion:
        Id_camiones += 1
        camion = Camion(
            id_camion=Id_camiones,
            peso_maximo=Peso_maximo,
            ruta=destino_id,
            fecha_salida=fecha,
            es_especial=False
        )
        camiones_normales.append(camion)
        camiones_creados.append(camion)
        print(f"  🚚 Nuevo camión normal {Id_camiones}")
    # Agregar el producto
    if camion.agregar_producto(producto, cantidad, destino_id):
        print(f"  ✓ Agregado al camión {camion.id_camion} (Destinos: {camion.destinos})")
    else:
        print(f"  ✗ Error: Sin capacidad en camión {camion.id_camion}")
    
    return camion
        
        
        
        
def optimizar_rutas_fecha_actual(fecha):
    """Llama a los métodos de optimización de la clase Camion."""
    print(f"\n{'='*60}")
    print(f"OPTIMIZANDO RUTAS - FECHA {fecha}")
    print(f"{'='*60}")
    
    # Separar camiones
    camiones_especiales = [c for c in camiones_creados if c.es_especial]
    camiones_normales = [c for c in camiones_creados if not c.es_especial]
    
    # Camiones especiales (solo mostrar)
    if camiones_especiales:
        print(f"\nCamiones especiales ({len(camiones_especiales)}):")
        for camion in camiones_especiales:
            print(f"  Camión {camion.id_camion}: Destino único {camion.destinos[0]}")
            print(f"    Tiempo: {df_matriz.loc[0, str(camion.destinos[0])]*2:.2f}h (ida y vuelta)")
    
    # Camiones normales (optimizar)
    if camiones_normales:
        print(f"\nCamiones normales ({len(camiones_normales)}):")
        
        for camion in camiones_normales:
            if len(camion.destinos) > 0:
                print(f"\n{'─'*40}")
                print(f"Camion {camion.id_camion}:")
                print(f"  Destinos: {camion.destinos}")
                print(f"  Carga: {camion.peso_actual}/{camion.peso_maximo}kg")
                
                # LLAMADA A LA OPTIMIZACIÓN DENTRO DE LA CLASE CAMION
                # (Asumo que tu clase Camion tiene este método)
                camion.optimizar_rutas(df_matriz)
                
                # Mostrar resultados (asumo que tu clase tiene estos atributos)
                if hasattr(camion, 'mostrar_comparacion_rutas'):
                    camion.mostrar_comparacion_rutas()
                else:
                    # Versión simplificada si no tiene el método
                    mostrar_comparacion_simplificada(camion)
                
                # Seleccionar automáticamente la mejor ruta
                seleccionar_mejor_ruta_automatico(camion)

def mostrar_comparacion_simplificada(camion):
    """Muestra comparación si la clase Camion no tiene el método."""
    if hasattr(camion, 'tiempo_fuerza_bruta') and camion.tiempo_fuerza_bruta:
        print(f"  Fuerza Bruta: {camion.ruta_fuerza_bruta} - {camion.tiempo_fuerza_bruta:.2f}h")
    
    if hasattr(camion, 'tiempo_vecino_cercano'):
        print(f"  Vecino Cercano: {camion.ruta_vecino_cercano} - {camion.tiempo_vecino_cercano:.2f}h")
    
    if hasattr(camion, 'tiempo_insercion'):
        print(f"  Inserción: {camion.ruta_insercion} - {camion.tiempo_insercion:.2f}h")

def seleccionar_mejor_ruta_automatico(camion):
    """Selecciona automáticamente la mejor ruta para el camión."""
    # Si la clase ya tiene lógica de selección, usa esa
    if hasattr(camion, 'seleccionar_mejor_ruta'):
        camion.seleccionar_mejor_ruta()
    else:
        # Lógica simple de selección
        tiempos = []
        
        if hasattr(camion, 'tiempo_fuerza_bruta') and camion.tiempo_fuerza_bruta:
            tiempos.append(('fuerza_bruta', camion.tiempo_fuerza_bruta))
        
        if hasattr(camion, 'tiempo_vecino_cercano'):
            tiempos.append(('vecino_cercano', camion.tiempo_vecino_cercano))
        
        if hasattr(camion, 'tiempo_insercion'):
            tiempos.append(('insercion', camion.tiempo_insercion))
        
        if tiempos:
            # Ordenar por tiempo (menor primero)
            tiempos.sort(key=lambda x: x[1])
            mejor_algoritmo, mejor_tiempo = tiempos[0]
            
            print(f"  ✓ Seleccionado: {mejor_algoritmo.replace('_', ' ').title()}")
            print(f"    Tiempo: {mejor_tiempo:.2f}h")
            
            # Asignar la ruta seleccionada al camión
            if mejor_algoritmo == 'fuerza_bruta':
                camion.ruta_final = camion.ruta_fuerza_bruta
            elif mejor_algoritmo == 'vecino_cercano':
                camion.ruta_final = camion.ruta_vecino_cercano
            elif mejor_algoritmo == 'insercion':
                camion.ruta_final = camion.ruta_insercion
            
            camion.tiempo_final = mejor_tiempo

def mostrar_resumen_fecha(fecha):
    """Muestra resumen de camiones para una fecha."""
    camiones_fecha = [c for c in camiones_creados]
    
    print(f"\n{'='*60}")
    print(f"RESUMEN FECHA {fecha}")
    print(f"{'='*60}")
    
    total_camiones = len(camiones_fecha)
    total_especiales = len([c for c in camiones_fecha if c.es_especial])
    total_normales = total_camiones - total_especiales
    
    print(f"Total camiones: {total_camiones}")
    print(f"  - Especiales: {total_especiales}")
    print(f"  - Normales: {total_normales}")
    
    # Mostrar cada camión
    for camion in camiones_fecha:
        tipo = "Especial" if camion.es_especial else "Normal"
        destinos = camion.destinos if hasattr(camion, 'destinos') else []
        
        print(f"\nCamión {camion.id_camion} ({tipo}):")
        print(f"  Destinos: {destinos}")
        print(f"  Carga: {camion.peso_actual}/{camion.peso_maximo}kg")
        
        # Mostrar tiempo si está optimizado
        if hasattr(camion, 'tiempo_final') and camion.tiempo_final:
            print(f"  Tiempo estimado: {camion.tiempo_final:.2f}h")
            
            
comprobar_pedidos_fecha_produccion()
