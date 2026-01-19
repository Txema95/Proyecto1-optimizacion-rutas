from datetime import datetime, timedelta
from typing import List, Optional
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from app.optimizacion_rutas import fuerza_bruta, vecino_cercano, insercion

class Camion:
    def __init__(self, 
                 id_camion: int,
                 peso_maximo: int,
                 fecha_salida: datetime = None,
                 ruta: str = "",
                 dias_viaje: int = 1,
                 es_especial: int = 0):
        """
        Inicializa un camión.
        
        Args:
            id_camion: Identificador único del camión
            peso_maximo: Peso máximo en kg que puede transportar
            fecha_salida: Fecha de salida del camión
            ruta: Ruta o destino del camión
            dias_viaje: Días que dura el viaje (ida y vuelta)
        """
        self.es_especial = es_especial
        self.id_camion = id_camion
        self.peso_maximo = peso_maximo
        self.peso_actual = 0
        self.productos_asignados: List[int] = []
        self.destinos = []
        self.fecha_salida = fecha_salida
        self.fecha_vuelta = None
        self.ruta = ruta
        self.estado = None  # None = disponible, "en_ruta" = en viaje
        
        # 
        self.ruta_fuerza_bruta = None
        self.ruta_vecino_cercano = None
        self.ruta_insercion = None
        self.tiempo_fuerza_bruta = 0
        self.tiempo_vecino_cercano = 0
        self.tiempo_insercion = 0
        
    def agregar_producto(self, producto_id: int, peso: int, destino_id) -> bool:
        """
        Agrega un producto al camión si hay capacidad disponible.
        
        Args:
            producto_id: ID del producto a agregar
            peso: Peso del producto en kg
            
        Returns:
            bool: True si se agregó exitosamente, False si no hay capacidad
        """
        if self.peso_actual + peso <= self.peso_maximo:
            self.productos_asignados.append(producto_id)
            self.peso_actual += peso
            if destino_id not in self.destinos:
                self.destinos.append(destino_id)
            return True
        else:
            print(f"Error: No hay capacidad suficiente. Peso actual: {self.peso_actual}/{self.peso_maximo}")
            return False
    
    def quitar_producto(self, producto_id: int, peso: int) -> bool:
        """
        Quita un producto del camión.
        
        Args:
            producto_id: ID del producto a quitar
            peso: Peso del producto en kg
            
        Returns:
            bool: True si se quitó exitosamente, False si el producto no existe
        """
        if producto_id in self.productos_asignados:
            self.productos_asignados.remove(producto_id)
            self.peso_actual -= peso
            return True
        return False
    
    def cambiar_ruta(self, nueva_ruta: str, dias_viaje: int) -> None:
        """
        Cambia la ruta y recalcula la fecha de vuelta.
        
        Args:
            nueva_ruta: Nueva ruta del camión
            dias_viaje: Nuevos días de viaje
        """
        self.ruta = nueva_ruta
        self.fecha_vuelta = self.fecha_salida + timedelta(days=dias_viaje)
    
    def cambiar_fecha_salida(self, nueva_fecha: datetime, dias_viaje: Optional[int] = None) -> None:
        """
        Cambia la fecha de salida y recalcula la fecha de vuelta.
        
        Args:
            nueva_fecha: Nueva fecha de salida
            dias_viaje: Si se proporciona, cambia también los días de viaje
        """
        self.fecha_salida = nueva_fecha
        if dias_viaje is not None:
            self.fecha_vuelta = nueva_fecha + timedelta(days=dias_viaje)
        else:
            # Mantener la misma duración de viaje
            duracion_actual = self.fecha_vuelta - self.fecha_salida
            self.fecha_vuelta = nueva_fecha + duracion_actual
    
    def capacidad_disponible(self) -> int:
        """
        Calcula la capacidad disponible en el camión.
        
        Returns:
            int: Peso disponible en kg
        """
        return self.peso_maximo - self.peso_actual
    
    def porcentaje_ocupacion(self) -> float:
        """
        Calcula el porcentaje de ocupación del camión.
        
        Returns:
            float: Porcentaje de ocupación (0-100)
        """
        return (self.peso_actual / self.peso_maximo) * 100
    
    def cambiar_estado(self, nuevo_estado: str) -> None:
        """
        Cambia el estado del camión.
        
        Args:
            nuevo_estado: Nuevo estado (disponible, en_ruta, en_mantenimiento)
        """
        estados_validos = ["disponible", "en_ruta", "en_mantenimiento"]
        if nuevo_estado in estados_validos:
            self.estado = nuevo_estado
        else:
            raise ValueError(f"Estado no válido. Estados permitidos: {estados_validos}")
    
    def reiniciar_carga(self) -> None:
        """
        Vacía completamente el camión.
        """
        self.productos_asignados = []
        self.peso_actual = 0
    
    def optimizar_rutas(self, df_matriz):
        """Calcula rutas optimizadas con los 3 algoritmos."""
        if not self.destinos:
            return
        
        # 1. Fuerza bruta (solo si ≤ 10 destinos para no saturar)
        if len(self.destinos) <= 10:
            self.ruta_fuerza_bruta, self.tiempo_fuerza_bruta = \
                fuerza_bruta.tsp_fuerza_bruta(self.destinos, df_matriz)
        
        # 2. Vecino más cercano
        self.ruta_vecino_cercano, self.tiempo_vecino_cercano = \
            vecino_cercano.tsp_vecino_mas_cercano_mejor_inicio(self.destinos, df_matriz)
        
        # 3. Inserción
        self.ruta_insercion, self.tiempo_insercion = \
            insercion.tsp_insercion_mejor_inicio(self.destinos, df_matriz)
    
    def mostrar_comparacion_rutas(self):
        """Muestra comparación de los 3 algoritmos."""
        print(f"\n{'='*60}")
        print(f"CAMIÓN {self.id_camion} - Destinos: {self.destinos}")
        print(f"{'='*60}")
        
        if len(self.destinos) <= 10 and self.ruta_fuerza_bruta:
            print("Fuerza Bruta (ÓPTIMO):")
            print(f"  Ruta: {self.ruta_fuerza_bruta}")
            print(f"  Tiempo: {self.tiempo_fuerza_bruta:.2f}h")
            print()
        
        print("Vecino Más Cercano:")
        print(f"  Ruta: {self.ruta_vecino_cercano}")
        print(f"  Tiempo: {self.tiempo_vecino_cercano:.2f}h")
        print(f"  Diferencia: +{self.tiempo_vecino_cercano - self.tiempo_fuerza_bruta:.2f}h" 
              if self.ruta_fuerza_bruta else "")
        print()
        
        print("Inserción:")
        print(f"  Ruta: {self.ruta_insercion}")
        print(f"  Tiempo: {self.tiempo_insercion:.2f}h")
        print(f"  Diferencia: +{self.tiempo_insercion - self.tiempo_fuerza_bruta:.2f}h" 
              if self.ruta_fuerza_bruta else "")
        
    def agregar_pedido_normal_a_camion(self,producto, fecha, destino_id, cantidad):
        global Id_camiones, camiones_normales, camiones_creados
        
        producto_id = producto['ProductoID']
        
        # PRIMERO: Buscar camión con MISMO DESTINO y MISMO PRODUCTO
        camion_preferido = None
        
        for c in camiones_normales:
            if (destino_id in c.destinos and 
                tiene_mismo_producto(c, producto_id) and
                c.capacidad_disponible() >= cantidad):
                camion_preferido = c
                break
        
        # SEGUNDO: Si no encuentra, buscar cualquier camión con capacidad
        if not camion_preferido:
            for c in camiones_normales:
                if c.capacidad_disponible() >= cantidad:
                    camion_preferido = c
                    break
        
        # TERCERO: Si aún no encuentra, crear nuevo camión
        if not camion_preferido:
            Id_camiones += 1
            camion_preferido = Camion(
                id_camion=Id_camiones,
                peso_maximo=self.Peso_maximo,
                fecha_salida=fecha,
                es_especial=False
            )
            camiones_normales.append(camion_preferido)
            camiones_creados.append(camion_preferido)
            print(f"  🚚 Nuevo camión normal {Id_camiones}")
        
        # Agregar producto
        if camion_preferido.agregar_producto(producto, cantidad, destino_id):
            print(f"  ✓ Agregado al camión {camion_preferido.id_camion}")
            print(f"    Destinos: {camion_preferido.destinos}")
            print(f"    Producto ID: {producto_id}")
            return camion_preferido
        
        return None

def tiene_mismo_producto(camion, producto_id):
    """Verifica si el camión ya lleva este producto."""
    for pedido in camion.productos_asignados:
        if isinstance(pedido, dict) and pedido.get('ProductoID') == producto_id:
            return True
        elif hasattr(pedido, 'ProductoID') and pedido.ProductoID == producto_id:
            return True
    return False
        
    def get_rutas(self):
        return self.ruta
    
    def __str__(self) -> str:
        """
        Representación en string del camión.
        """
        return (f"Camion ID: {self.id_camion}\n"
                f"Estado: {self.estado}\n"
                f"Peso: {self.peso_actual}/{self.peso_maximo} kg ({self.porcentaje_ocupacion():.1f}%)\n"
                f"Productos asignados: {len(self.productos_asignados)}\n"
                f"Ruta: {self.ruta}\n"
                f"Salida: {self.fecha_salida.strftime('%Y-%m-%d')}\n"
                f"Vuelta: {self.fecha_vuelta.strftime('%Y-%m-%d')}")