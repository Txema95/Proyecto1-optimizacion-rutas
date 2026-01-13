
def to_numeric(ruta_temp,origen_fijo , df_matriz_tiempos):
    """
    Convierte todos los valores del DataFrame a numéricos.
    """
    ruta_temp = [origen_fijo] + ruta_temp
    destinos_str = ruta_temp

    # Crear Mapeo
    id_to_nombre = {i: nombre for i, nombre in enumerate(destinos_str)}
    nombre_to_id = {nombre: i for i, nombre in enumerate(destinos_str)}

    nombres = df_matriz_tiempos.columns.tolist()
    ids = [nombre_to_id[n] for n in nombres]

    # Reindexar el DataFrame usando IDs numéricos
    df_tiempos_viaje_id = df_matriz_tiempos.copy()
    df_tiempos_viaje_id.columns = ids
    df_tiempos_viaje_id.index = ids

    return df_tiempos_viaje_id