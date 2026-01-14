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
