import pandas as pd
import random 
from deap import base, creator, tools, algorithms
import numpy as np
import streamlit as st

MAX_TIEMPO_RUTA = 8.0           # Restricción de 8 horas

PENALIZACION_GRANDE = 1000.0    # Factor para castigar rutas no factibles
TAMANO_POBLACION = 300          # Número de rutas por generación
NUM_GENERACIONES = 1000         # Número de iteraciones
PROB_CRUCE = 0.8                # Probabilidad de que ocurra un cruce
PROB_MUTACION = 0.1             # Probabilidad de mutación
TOUR_SIZE = 3                   # Tamaño del torneo para selección

ORIGEN = 0


def ejecutar_ag_sin_vuelta(ruta_temp, df_matriz_tiempos):
    ciudades = ruta_temp
    tiempos = df_matriz_tiempos.values.tolist()

    def calcular_fitness(cromosoma):
        rutas = []
        ruta_actual = []
        tiempo_total = 0
        tiempo_actual = 0
        punto_anterior = ORIGEN
        
        for destino in cromosoma:
            tiempo_viaje = tiempos[punto_anterior][destino]
            
            # Verificamos solo la ida al destino
            if tiempo_actual + tiempo_viaje <= MAX_TIEMPO_RUTA:
                ruta_actual.append(ciudades[destino])
                tiempo_actual += tiempo_viaje
                punto_anterior = destino
            else:
                # Se cierra ruta y el siguiente camión sale de Mataró
                rutas.append((ruta_actual, tiempo_actual))
                tiempo_total += tiempo_actual
                
                ruta_actual = [ciudades[destino]]
                tiempo_actual = tiempos[ORIGEN][destino]
                punto_anterior = destino
                
        rutas.append((ruta_actual, tiempo_actual))
        tiempo_total += tiempo_actual
        return tiempo_total, rutas

    # --- Algoritmo Genético ---
    poblacion_size = 100
    generaciones = 200
    indices_destinos = list(range(1, len(ciudades)))

    poblacion = [random.sample(indices_destinos, len(indices_destinos)) for _ in range(poblacion_size)]

    for gen in range(generaciones):
        poblacion = sorted(poblacion, key=lambda c: calcular_fitness(c)[0])
        nueva_gen = poblacion[:20] # Elitismo
        
        while len(nueva_gen) < poblacion_size:
            padre = random.choice(poblacion[:40])
            # Mutación por intercambio simple
            hijo = padre[:]
            idx1, idx2 = random.sample(range(len(hijo)), 2)
            hijo[idx1], hijo[idx2] = hijo[idx2], hijo[idx1]
            nueva_gen.append(hijo)
        poblacion = nueva_gen

    # Resultado
    mejor = poblacion[0]
    t_total, rutas_finales = calcular_fitness(mejor)

    st.title(f"Resultados de Optimización (Máx 8h por tramo):")
    st.write("-" * 50)
    for i, (r, t) in enumerate(rutas_finales):
        st.write(f"Camión {i+1}: Mataró -> {' -> '.join(r)} | Tiempo: {t:.2f}h")
    st.write("-" * 50)
    st.write(f"Tiempo total de conducción: {t_total:.2f}h")


VELOCIDAD_MEDIA = 75 # km/h
MAX_HORAS_CONDUCCION = 8
CAPACIDAD_MAX = 500
def fitness_logistica(cromosoma, df_sobrantes, matriz_km):
    total_camiones = 0
    total_distancia = 0
    n = len(cromosoma)
    
    i = 0
    while i < n:
        total_camiones += 1
        carga_actual = 0
        tiempo_conduccion_actual = 0
        ubicacion_actual = 0
        
        # Fecha salida inicial (YA DEBEN SER DATETIME EN EL DF)
        fecha_salida_camion = df_sobrantes.iloc[cromosoma[i]]['FechaFinFabricacion']
        
        inicio_camion_i = i # Para detectar si un pedido no cabe ni solo

        while i < n:
            idx_pedido = cromosoma[i]
            pedido = df_sobrantes.iloc[idx_pedido]
            destino_id = int(pedido['DestinoEntregaID'])
            
            # 1. Validar Capacidad
            if carga_actual + pedido['Cantidad'] > CAPACIDAD_MAX:
                break 
            
            distancia_tramo = matriz_km[ubicacion_actual][destino_id]
            tiempo_tramo = distancia_tramo / VELOCIDAD_MEDIA
            
            # 3. Validar Fecha Salida y Caducidad
            nueva_fecha_salida = max(fecha_salida_camion, pedido['FechaFinFabricacion'])
            posible_tiempo_total = tiempo_conduccion_actual + tiempo_tramo
            llegada_este_pedido = nueva_fecha_salida + pd.to_timedelta(posible_tiempo_total, unit='h')
            
            if llegada_este_pedido > pedido['FechaCaducidad']:
                # Si el pedido no cabe ni siquiera siendo el primero del camión, 
                # hay que saltarlo para evitar bucle infinito
                if carga_actual == 0: 
                    i += 1 
                break 
                
            # 4. Validar Horas de Conducción (incluyendo vuelta)
            idx_mataro = 0
            distancia_vuelta = matriz_km[destino_id][idx_mataro]
            tiempo_vuelta = distancia_vuelta / VELOCIDAD_MEDIA
            
            if (posible_tiempo_total + tiempo_vuelta) > MAX_HORAS_CONDUCCION:
                if carga_actual == 0: # Caso extremo: destino inalcanzable en 8h
                    i += 1
                break 

            # TODO OK: Añadimos pedido
            carga_actual += pedido['Cantidad']
            tiempo_conduccion_actual += tiempo_tramo
            total_distancia += distancia_tramo
            fecha_salida_camion = nueva_fecha_salida
            ubicacion_actual = destino_id
            i += 1
        
        # Vuelta a Mataró al cerrar camión
        total_distancia += matriz_km[ubicacion_actual][0]
        
    return total_camiones + (total_distancia / 10000)

def generar_individuo(n):
    # Crea una lista de índices aleatorios sin repetir
    individuo = list(range(n))
    random.shuffle(individuo)
    return individuo

def crossover_ox(padre1, padre2):
    # Ordered Crossover para evitar duplicados en la ruta
    size = len(padre1)
    a, b = sorted(random.sample(range(size), 2))
    
    hijo = [-1] * size
    hijo[a:b] = padre1[a:b]
    
    pos = b
    for item in padre2:
        if item not in hijo:
            if pos >= size:
                pos = 0
            hijo[pos] = item
            pos += 1
    return hijo

def mutacion_swap(individuo):
    # Intercambia dos posiciones al azar
    idx1, idx2 = random.sample(range(len(individuo)), 2)
    individuo[idx1], individuo[idx2] = individuo[idx2], individuo[idx1]
    return individuo

def algoritmo_genetico(df_sobrantes, matriz_km, matriz_tiempo, 
                       n_poblacion=20, n_generaciones=100, p_mutacion=0.1):
    
    n_pedidos = len(df_sobrantes)
    # 1. Población inicial
    poblacion = [generar_individuo(n_pedidos) for _ in range(n_poblacion)]
    
    mejor_individuo = None
    mejor_fitness = float('inf')

    for gen in range(n_generaciones):
        # 2. Evaluación con la función de fitness que refinamos antes

        print(f"🧬 Procesando generación {gen} de {n_generaciones}...")
        scores = []
        for ind in poblacion:
            f = fitness_logistica(ind, df_sobrantes, matriz_km)
            scores.append((f, ind))
            
            if f < mejor_fitness:
                mejor_fitness = f
                mejor_individuo = ind[:]
        
        # Ordenar por mejor fitness (menor es mejor)
        scores.sort(key=lambda x: x[0])
        
        # 3. Selección (Torneo o Elitismo)
        nueva_poblacion = [scores[i][1] for i in range(10)] # Elitismo: pasan los 10 mejores
        
        # 4. Reproducción
        while len(nueva_poblacion) < n_poblacion:
            p1, p2 = random.sample(scores[:20], 2) # Padres de entre los mejores
            hijo = crossover_ox(p1[1], p2[1])
            
            if random.random() < p_mutacion:
                hijo = mutacion_swap(hijo)
            
            nueva_poblacion.append(hijo)
            
        poblacion = nueva_poblacion
        if gen % 10 == 0:
            print(f"Generación {gen}: Mejor fitness = {mejor_fitness}")

    return mejor_individuo, mejor_fitness


######################################################################################



def calcular_fitness_tiempos(ruta, matriz_tiempos):#, df_pedidos):
    """
    ruta: lista de IDs de destino, ej. [0, 5, 12, 8, 0] (siempre empieza y termina en 0)
    matriz_tiempos: matriz donde matriz[i][j] es el tiempo en horas entre i y j
    """
    tiempo_total = 0
    penalizacion = 0
    limite_jornada = 9.0
    
    for i in range(len(ruta) - 1):
        actual = ruta[i]
        siguiente = ruta[i+1]
        
        tiempo_tramo = matriz_tiempos[actual][siguiente]
        tiempo_total += tiempo_tramo
        
        
    return tiempo_total 

def cruce_ox(padre1, padre2):
    size = len(padre1)
    hijo = [None] * size
    
    # 1. Elegir dos puntos de corte
    a, b = sorted(random.sample(range(size), 2))
    
    # 2. Copiar segmento del Padre 1
    hijo[a:b] = padre1[a:b]
    
    # 3. Rellenar con elementos del Padre 2 que no estén en el hijo
    pos_actual = b
    for item in (padre2[b:] + padre2[:b]):
        if item not in hijo:
            if pos_actual >= size:
                pos_actual = 0
            hijo[pos_actual] = item
            pos_actual += 1
    return hijo

def mutar_swap(ruta, probabilidad=0.05):
    if random.random() < probabilidad:
        # Elegir dos índices al azar e intercambiarlos
        idx1, idx2 = random.sample(range(len(ruta)), 2)
        ruta[idx1], ruta[idx2] = ruta[idx2], ruta[idx1]
    return ruta

def algoritmo_genetico_por_camion(destinos_cluster, matriz_tiempos, generaciones=200):
    # 'destinos_cluster' son los IDs de los pedidos asignados a este camión
    poblacion = [random.sample(destinos_cluster, len(destinos_cluster)) for _ in range(100)]
    
    for gen in range(generaciones):
        # 1. Calcular fitness de todos
        scores = []
        for ind in poblacion:
            # Añadimos el origen (0) al inicio y al final
            ruta_completa = [0] + ind + [0]
            scores.append((calcular_fitness_tiempos(ruta_completa, matriz_tiempos), ind))
        
        # 2. Ordenar por mejor fitness (menor es mejor)
        scores.sort(key=lambda x: x[0])
        mejor_ruta = scores[0]
        
        # 3. Crear nueva generación (Selección + Cruce + Mutación)
        nueva_poblacion = [scores[i][1] for i in range(10)] # Elitismo: pasan los 10 mejores
        
        while len(nueva_poblacion) < 100:
            # Aquí iría la lógica de Cruce OX y Mutación Swap
            padre1 = random.choice(nueva_poblacion[:20])
            padre2 = random.choice(nueva_poblacion[:20])
            hijo = cruce_ox(padre1, padre2)
            if random.random() < 0.1: hijo = mutar_swap(hijo)
            nueva_poblacion.append(hijo)
            
        poblacion = nueva_poblacion
        
    return mejor_ruta