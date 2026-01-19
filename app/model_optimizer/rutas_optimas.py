import pandas as pd
import numpy as np
from sklearn.cluster import KMeans
from itertools import permutations
import json
from datetime import datetime

# ========== ALGORITMOS TSP PARA CLUSTERS ==========

def tsp_fuerza_bruta_cluster(destinos, df_matriz):
    """TSP por fuerza bruta para clusters pequeños (≤8 destinos)."""
    if len(destinos) <= 1:
        if destinos:
            tiempo = df_matriz.loc[0, str(destinos[0])] * 2
            return [0, destinos[0], 0], tiempo
        return [0, 0], 0.0
    
    mejor_ruta = None
    menor_tiempo = float('inf')
    
    for perm in permutations(destinos):
        tiempo_total = df_matriz.loc[0, str(perm[0])]
        
        for i in range(len(perm) - 1):
            tiempo_total += df_matriz.loc[perm[i], str(perm[i + 1])]
        
        tiempo_total += df_matriz.loc[perm[-1], '0']
        
        if tiempo_total < menor_tiempo:
            menor_tiempo = tiempo_total
            mejor_ruta = perm
    
    return [0] + list(mejor_ruta) + [0], menor_tiempo

def tsp_vecino_cercano_cluster(destinos, df_matriz):
    """TSP por vecino más cercano para clusters grandes."""
    if not destinos:
        return [0, 0], 0.0
    
    no_visitados = destinos.copy()
    ruta = [0]
    tiempo_total = 0
    actual = 0
    
    while no_visitados:
        mas_cercano = None
        menor_distancia = float('inf')
        
        for destino in no_visitados:
            distancia = df_matriz.loc[actual, str(destino)]
            if distancia < menor_distancia:
                menor_distancia = distancia
                mas_cercano = destino
        
        tiempo_total += menor_distancia
        ruta.append(mas_cercano)
        no_visitados.remove(mas_cercano)
        actual = mas_cercano
    
    tiempo_total += df_matriz.loc[actual, '0']
    ruta.append(0)
    
    return ruta, tiempo_total

def resolver_tsp_cluster(destinos, df_matriz):
    """Resuelve TSP para un cluster, eligiendo algoritmo según tamaño."""
    if len(destinos) <= 8:
        return tsp_fuerza_bruta_cluster(destinos, df_matriz)
    else:
        return tsp_vecino_cercano_cluster(destinos, df_matriz)

# ========== ALGORITMO K-MEANS SIMPLIFICADO ==========

def crear_rutas_kmeans_simple(df_matriz, tiempo_max=18.0):
    """
    Versión simplificada de K-Means que garantiza rutas viables.
    """
    print("\n🔄 EJECUTANDO K-MEANS SIMPLIFICADO")
    
    destinos = [int(col) for col in df_matriz.columns if col != '0' and col.isdigit()]
    
    if len(destinos) <= 4:
        # Si hay pocos destinos, resolver directamente
        ruta, tiempo = resolver_tsp_cluster(destinos, df_matriz)
        if tiempo <= tiempo_max:
            return [{
                'cluster_id': 'K001',
                'ruta': ruta,
                'destinos': destinos,
                'num_destinos': len(destinos),
                'tiempo_horas': round(tiempo, 2),
                'viable': True,
                'estado': '✅ VIABLE',
                'eficiencia': round(len(destinos) / tiempo, 3) if tiempo > 0 else 0,
                'tipo': 'kmeans'
            }]
        return []
    
    # Preparar características
    caracteristicas = []
    for destino in destinos:
        tiempo_mataro = df_matriz.loc[0, str(destino)]
        
        # Calcular promedio de 3 destinos más cercanos
        tiempos = []
        for otro in destinos:
            if otro != destino:
                tiempos.append(df_matriz.loc[destino, str(otro)])
        
        tiempos.sort()
        avg_cercanos = np.mean(tiempos[:3]) if len(tiempos) >= 3 else np.mean(tiempos)
        
        caracteristicas.append([tiempo_mataro, avg_cercanos])
    
    X = np.array(caracteristicas)
    
    # Normalizar
    from sklearn.preprocessing import StandardScaler
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    # K-Means con número fijo de clusters
    n_clusters = max(2, min(5, len(destinos) // 3))
    
    try:
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        labels = kmeans.fit_predict(X_scaled)
        
        rutas = []
        cluster_id = 0
        
        for i in range(n_clusters):
            destinos_cluster = [destinos[j] for j in range(len(destinos)) if labels[j] == i]
            
            if not destinos_cluster:
                continue
            
            # Si cluster tiene más de 4 destinos, dividirlo
            if len(destinos_cluster) > 4:
                # Dividir por tiempo desde Mataró
                destinos_cluster.sort(key=lambda x: df_matriz.loc[0, str(x)])
                mitad = len(destinos_cluster) // 2
                
                subgrupo1 = destinos_cluster[:mitad]
                subgrupo2 = destinos_cluster[mitad:]
                
                for subgrupo in [subgrupo1, subgrupo2]:
                    if subgrupo:
                        ruta, tiempo = resolver_tsp_cluster(subgrupo, df_matriz)
                        if tiempo <= tiempo_max:
                            rutas.append({
                                'cluster_id': f'K{cluster_id:03d}',
                                'ruta': ruta,
                                'destinos': subgrupo,
                                'num_destinos': len(subgrupo),
                                'tiempo_horas': round(tiempo, 2),
                                'viable': True,
                                'estado': '✅ VIABLE',
                                'eficiencia': round(len(subgrupo) / tiempo, 3) if tiempo > 0 else 0,
                                'tipo': 'kmeans'
                            })
                            cluster_id += 1
            else:
                ruta, tiempo = resolver_tsp_cluster(destinos_cluster, df_matriz)
                if tiempo <= tiempo_max:
                    rutas.append({
                        'cluster_id': f'K{cluster_id:03d}',
                        'ruta': ruta,
                        'destinos': destinos_cluster,
                        'num_destinos': len(destinos_cluster),
                        'tiempo_horas': round(tiempo, 2),
                        'viable': True,
                        'estado': '✅ VIABLE',
                        'eficiencia': round(len(destinos_cluster) / tiempo, 3) if tiempo > 0 else 0,
                        'tipo': 'kmeans'
                    })
                    cluster_id += 1
        
        print(f"  Rutas K-Means generadas: {len(rutas)}")
        return rutas
        
    except Exception as e:
        print(f"  ⚠️ Error en K-Means: {e}")
        return []

# ========== ALGORITMO DE BARRIDO ==========

def crear_rutas_barrido(df_matriz, tiempo_max=18.0):
    """
    Algoritmo de barrido simple y efectivo.
    """
    print("\n🔄 EJECUTANDO ALGORITMO DE BARRIDO")
    
    destinos = [int(col) for col in df_matriz.columns if col != '0' and col.isdigit()]
    destinos_ordenados = sorted(destinos, key=lambda x: df_matriz.loc[0, str(x)])
    
    rutas = []
    ruta_actual = []
    ruta_id = 0
    
    for destino in destinos_ordenados:
        # Probar agregar destino
        ruta_prueba = ruta_actual + [destino]
        
        # Estimación rápida de tiempo
        if len(ruta_prueba) == 1:
            tiempo_estimado = df_matriz.loc[0, str(destino)] * 2
        else:
            suma_distancias = sum(df_matriz.loc[0, str(d)] for d in ruta_prueba)
            tiempo_estimado = suma_distancias * 0.7
        
        # Verificar restricciones
        if len(ruta_prueba) <= 4 and tiempo_estimado <= tiempo_max * 0.9:
            ruta_actual.append(destino)
        else:
            # Finalizar ruta actual
            if ruta_actual:
                ruta_optima, tiempo_real = resolver_tsp_cluster(ruta_actual, df_matriz)
                if tiempo_real <= tiempo_max:
                    rutas.append({
                        'cluster_id': f'B{ruta_id:03d}',
                        'ruta': ruta_optima,
                        'destinos': ruta_actual.copy(),
                        'num_destinos': len(ruta_actual),
                        'tiempo_horas': round(tiempo_real, 2),
                        'viable': True,
                        'estado': '✅ VIABLE',
                        'eficiencia': round(len(ruta_actual) / tiempo_real, 3) if tiempo_real > 0 else 0,
                        'tipo': 'barrido'
                    })
                    ruta_id += 1
            
            ruta_actual = [destino]
    
    # Última ruta
    if ruta_actual:
        ruta_optima, tiempo_real = resolver_tsp_cluster(ruta_actual, df_matriz)
        if tiempo_real <= tiempo_max:
            rutas.append({
                'cluster_id': f'B{ruta_id:03d}',
                'ruta': ruta_optima,
                'destinos': ruta_actual.copy(),
                'num_destinos': len(ruta_actual),
                'tiempo_horas': round(tiempo_real, 2),
                'viable': True,
                'estado': '✅ VIABLE',
                'eficiencia': round(len(ruta_actual) / tiempo_real, 3) if tiempo_real > 0 else 0,
                'tipo': 'barrido'
            })
    
    print(f"  Rutas barrido generadas: {len(rutas)}")
    return rutas

# ========== FUNCIONES AUXILIARES ==========

def combinar_destinos_pequenos(destinos, df_matriz, tiempo_max):
    """Combina destinos pequeños en rutas viables."""
    rutas = []
    
    destinos_ordenados = sorted(destinos, key=lambda x: df_matriz.loc[0, str(x)])
    i = 0
    
    while i < len(destinos_ordenados):
        # Intentar grupos de 2
        if i + 1 < len(destinos_ordenados):
            grupo = destinos_ordenados[i:i+2]
            ruta, tiempo = resolver_tsp_cluster(grupo, df_matriz)
            
            if tiempo <= tiempo_max:
                rutas.append({
                    'cluster_id': f'C{len(rutas):03d}',
                    'ruta': ruta,
                    'destinos': grupo,
                    'num_destinos': len(grupo),
                    'tiempo_horas': round(tiempo, 2),
                    'viable': True,
                    'estado': '✅ VIABLE',
                    'eficiencia': round(len(grupo) / tiempo, 3),
                    'tipo': 'combinada'
                })
                i += 2
                continue
        
        # Ruta individual
        destino = destinos_ordenados[i]
        tiempo = df_matriz.loc[0, str(destino)] * 2
        
        if tiempo <= tiempo_max:
            rutas.append({
                'cluster_id': f'I{len(rutas):03d}',
                'ruta': [0, destino, 0],
                'destinos': [destino],
                'num_destinos': 1,
                'tiempo_horas': round(tiempo, 2),
                'viable': True,
                'estado': '✅ VIABLE',
                'eficiencia': round(1 / tiempo, 3),
                'tipo': 'individual'
            })
        
        i += 1
    
    return rutas

def encontrar_ruta_para_agregar(destino, rutas_existentes, df_matriz, tiempo_max):
    """Encuentra una ruta existente donde agregar un destino."""
    for ruta in rutas_existentes:
        if not ruta['viable'] or destino in ruta['destinos']:
            continue
        
        nuevos_destinos = ruta['destinos'] + [destino]
        nueva_ruta, nuevo_tiempo = resolver_tsp_cluster(nuevos_destinos, df_matriz)
        
        if nuevo_tiempo <= tiempo_max:
            # Actualizar ruta
            ruta['destinos'] = nuevos_destinos
            ruta['ruta'] = nueva_ruta
            ruta['num_destinos'] = len(nuevos_destinos)
            ruta['tiempo_horas'] = round(nuevo_tiempo, 2)
            ruta['eficiencia'] = round(len(nuevos_destinos) / nuevo_tiempo, 3)
            ruta['tipo'] = ruta.get('tipo', 'base') + '_ampliada'
            return ruta
    
    return None

# ========== FUNCIÓN PRINCIPAL DE GENERACIÓN ==========

def generar_rutas_completas(df_matriz, tiempo_max=18.0):
    """
    Genera rutas que cubran TODOS los destinos.
    """
    print(f"\n🎯 GENERANDO RUTAS COMPLETAS (COBERTURA TOTAL)")
    print("="*60)
    
    destinos = [int(col) for col in df_matriz.columns if col != '0' and col.isdigit()]
    print(f"Destinos totales: {len(destinos)}")
    print(f"Destinos: {sorted(destinos)}")
    
    todas_rutas = []
    destinos_cubiertos = set()
    
    # ESTRATEGIA 1: K-Means
    print(f"\n1️⃣ RUTAS K-MEANS OPTIMIZADAS:")
    rutas_kmeans = crear_rutas_kmeans_simple(df_matriz, tiempo_max)
    
    for ruta in rutas_kmeans:
        if ruta['viable']:
            todas_rutas.append(ruta)
            destinos_cubiertos.update(ruta['destinos'])
    
    print(f"   Destinos cubiertos: {len(destinos_cubiertos)}/{len(destinos)}")
    
    # ESTRATEGIA 2: Barrido para destinos faltantes
    destinos_faltantes = [d for d in destinos if d not in destinos_cubiertos]
    
    if destinos_faltantes:
        print(f"\n2️⃣ RUTAS DE BARRIDO PARA DESTINOS FALTANTES:")
        print(f"   Destinos sin cubrir: {len(destinos_faltantes)}")
        
        # Filtrar matriz solo para destinos faltantes
        columnas_faltantes = ['0'] + [str(d) for d in destinos_faltantes]
        filas_faltantes = [0] + destinos_faltantes
        df_filtrado = df_matriz.loc[filas_faltantes, columnas_faltantes]
        
        rutas_barrido = crear_rutas_barrido(df_filtrado, tiempo_max)
        
        for ruta in rutas_barrido:
            todas_rutas.append(ruta)
            destinos_cubiertos.update(ruta['destinos'])
    
    # ESTRATEGIA 3: Combinar destinos muy pequeños
    destinos_faltantes = [d for d in destinos if d not in destinos_cubiertos]
    
    if destinos_faltantes:
        print(f"\n3️⃣ COMBINANDO DESTINOS MUY PEQUEÑOS:")
        print(f"   Destinos pendientes: {len(destinos_faltantes)}")
        
        rutas_combinadas = combinar_destinos_pequenos(destinos_faltantes, df_matriz, tiempo_max)
        
        for ruta in rutas_combinadas:
            todas_rutas.append(ruta)
            destinos_cubiertos.update(ruta['destinos'])
    
    # ESTRATEGIA 4: Agregar a rutas existentes
    destinos_faltantes = [d for d in destinos if d not in destinos_cubiertos]
    
    if destinos_faltantes:
        print(f"\n4️⃣ AGREGANDO A RUTAS EXISTENTES:")
        
        for destino in destinos_faltantes:
            ruta_encontrada = encontrar_ruta_para_agregar(destino, todas_rutas, df_matriz, tiempo_max)
            
            if ruta_encontrada:
                destinos_cubiertos.add(destino)
            else:
                # Ruta individual forzada
                tiempo = df_matriz.loc[0, str(destino)] * 2
                ruta_individual = {
                    'cluster_id': f'F{destino:03d}',
                    'ruta': [0, destino, 0],
                    'destinos': [destino],
                    'num_destinos': 1,
                    'tiempo_horas': round(tiempo, 2),
                    'viable': tiempo <= tiempo_max,
                    'estado': '⚠️ FORZADA' if tiempo > tiempo_max else '✅ VIABLE',
                    'eficiencia': round(1 / tiempo, 3) if tiempo > 0 else 0,
                    'tipo': 'forzada'
                }
                todas_rutas.append(ruta_individual)
                destinos_cubiertos.add(destino)
    
    # RESULTADO FINAL
    print(f"\n{'='*60}")
    print("📊 COBERTURA FINAL")
    print(f"{'='*60}")
    
    cobertura = len(destinos_cubiertos) / len(destinos) * 100
    
    print(f"Destinos totales: {len(destinos)}")
    print(f"Destinos cubiertos: {len(destinos_cubiertos)} ({cobertura:.1f}%)")
    print(f"Cobertura: {'✅ COMPLETA' if cobertura == 100 else '⚠️ INCOMPLETA'}")
    
    # Ordenar por eficiencia
    todas_rutas.sort(key=lambda x: x['eficiencia'], reverse=True)
    
    # Renumerar
    for i, ruta in enumerate(todas_rutas):
        ruta['cluster_id'] = f"R{i+1:03d}"
    
    print(f"\nTotal rutas generadas: {len(todas_rutas)}")
    
    return todas_rutas

# ========== FUNCIONES DE GUARDADO ==========

def guardar_rutas_csv(rutas, nombre_archivo="rutas_completas.csv"):
    """Guarda las rutas optimizadas en CSV."""
    if not rutas:
        print("⚠️ No hay rutas para guardar")
        return None
    
    datos = []
    for ruta in rutas:
        datos.append({
            'cluster_id': ruta['cluster_id'],
            'destinos': '|'.join(map(str, ruta['destinos'])),
            'ruta_completa': '|'.join(map(str, ruta['ruta'])),
            'num_destinos': ruta['num_destinos'],
            'tiempo_horas': ruta['tiempo_horas'],
            'viable': 'SI' if ruta['viable'] else 'NO',
            'estado': ruta['estado'],
            'eficiencia': round(ruta['eficiencia'], 3),
            'fecha_generacion': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })
    
    df_rutas = pd.DataFrame(datos)
    df_rutas.to_csv(nombre_archivo, index=False, encoding='utf-8')
    
    rutas_viables = [r for r in rutas if r['viable']]
    
    print(f"\n💾 RESULTADOS GUARDADOS:")
    print(f"  Archivo: {nombre_archivo}")
    print(f"  Total rutas: {len(rutas)}")
    print(f"  Rutas viables: {len(rutas_viables)}")
    
    if rutas_viables:
        print(f"  Destinos cubiertos: {sum([r['num_destinos'] for r in rutas_viables])}")
        print(f"  Tiempo total: {sum([r['tiempo_horas'] for r in rutas_viables]):.2f}h")
    
    return nombre_archivo

def mostrar_rutas_detalladas(rutas, df_matriz):
    """Muestra las rutas de forma detallada."""
    print(f"\n{'='*80}")
    print("DETALLE DE RUTAS GENERADAS")
    print(f"{'='*80}")
    
    rutas_viables = [r for r in rutas if r['viable']]
    
    if rutas_viables:
        print(f"\n✅ RUTAS VIABLES ({len(rutas_viables)}):")
        for i, ruta in enumerate(rutas_viables[:10]):  # Mostrar solo 10
            print(f"\n  {ruta['cluster_id']} ({ruta.get('tipo', 'N/A')}):")
            print(f"    Destinos: {ruta['destinos']}")
            print(f"    Ruta: {ruta['ruta']}")
            print(f"    Tiempo: {ruta['tiempo_horas']}h")
            print(f"    Eficiencia: {ruta['eficiencia']:.3f} destinos/hora")

# ========== MAIN ==========

def main():
    """
    Función principal.
    """
    print("\n" + "="*80)
    print("GENERADOR DE RUTAS OPTIMIZADAS - COBERTURA 100%")
    print("="*80)
    
    try:
        # Cargar matriz
        df_matriz = pd.read_csv('matriz_tiempos_destinos.csv', index_col=0)
        destinos_total = len([col for col in df_matriz.columns if col != '0' and col.isdigit()])
        print(f"✅ Matriz cargada: {destinos_total} destinos")
        
        # Generar rutas
        rutas = generar_rutas_completas(df_matriz, tiempo_max=18.0)
        
        # Mostrar resumen
        rutas_viables = [r for r in rutas if r['viable']]
        
        print(f"\n{'='*80}")
        print("RESUMEN EJECUTIVO")
        print(f"{'='*80}")
        
        print(f"📊 ESTADÍSTICAS:")
        print(f"  Total rutas: {len(rutas)}")
        print(f"  Rutas viables: {len(rutas_viables)}")
        
        if rutas_viables:
            destinos_cubiertos = set()
            for ruta in rutas_viables:
                destinos_cubiertos.update(ruta['destinos'])
            
            print(f"  Destinos cubiertos: {len(destinos_cubiertos)}/{destinos_total}")
            print(f"  Cobertura: {len(destinos_cubiertos)/destinos_total*100:.1f}%")
            
            # Calcular métricas
            tiempo_total = sum([r['tiempo_horas'] for r in rutas_viables])
            eficiencias = [r['eficiencia'] for r in rutas_viables if r['tiempo_horas'] > 0]
            
            if eficiencias:
                print(f"  Tiempo total: {tiempo_total:.2f}h")
                print(f"  Eficiencia promedio: {np.mean(eficiencias):.3f}")
                print(f"  Mejor eficiencia: {max(eficiencias):.3f}")
        
        # Mostrar detalle
        mostrar_rutas_detalladas(rutas, df_matriz)
        
        # Guardar
        archivo = guardar_rutas_csv(rutas)
        
        # Guardar JSON
        if rutas:
            with open('rutas_detalladas.json', 'w', encoding='utf-8') as f:
                json.dump(rutas, f, indent=2, default=str, ensure_ascii=False)
            print(f"\n💾 JSON guardado: rutas_detalladas.json")
        
        return rutas, archivo
        
    except FileNotFoundError:
        print("❌ Archivo 'matriz_tiempos_destinos.csv' no encontrado")
        return [], None
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return [], None

# ========== EJECUCIÓN ==========

if __name__ == "__main__":
    rutas, archivo = main()
    
    if archivo:
        print(f"\n🎯 Proceso completado.")
        print(f"   Archivo CSV: {archivo}")
        print(f"   Para usar: pd.read_csv('{archivo}')")