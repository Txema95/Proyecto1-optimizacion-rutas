from datetime import datetime
from typing import List, Optional
from Camiones import camiones

class FlotaCamiones(camiones):
    def __init__(self):
        self.camiones: List[camiones] = []
        self.proximo_id = 1
    
    def agregar_camion(self, peso_maximo: int, fecha_salida: datetime, ruta: str = "", dias_viaje: int = 1) -> camiones:
        """
        Agrega un nuevo camión a la flota.
        """
        nuevo_camion = camiones(
            id_camion=self.proximo_id,
            peso_maximo=peso_maximo,
            fecha_salida=fecha_salida,
            ruta=ruta,
            dias_viaje=dias_viaje
        )
        self.camiones.append(nuevo_camion)
        self.proximo_id += 1
        return nuevo_camion
    
    def buscar_camion_por_id(self, id_camion: int) -> Optional[camiones]:
        """
        Busca un camión por su ID.
        """
        for camion in self.camiones:
            if camion.id_camion == id_camion:
                return camion
        return None
    
    def buscar_camiones_disponibles(self, fecha: datetime) -> List[camiones]:
        """
        Busca camiones disponibles para una fecha específica.
        """
        disponibles = []
        for camion in self.camiones:
            if (camion.estado == "disponible" and 
                camion.fecha_salida.date() == fecha.date()):
                disponibles.append(camion)
        return disponibles
    
    def camiones_en_ruta(self) -> List[camiones]:
        """
        Retorna todos los camiones que están en ruta.
        """
        return [camion for camion in self.camiones if camion.estado == "en_ruta"]
    
    def resumen_flota(self) -> None:
        """
        Muestra un resumen de toda la flota.
        """
        print(f"=== RESUMEN DE FLOTA ({len(self.camiones)} camiones) ===")
        for camion in self.camiones:
            print(camion.info_corta())
        print("=" * 50)