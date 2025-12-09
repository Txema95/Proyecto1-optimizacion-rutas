from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv
import urllib
import pandas as pd
load_dotenv()



class database:
    def __init__(self):
        self.__server = os.environ.get("SERVER")
        self.__database = os.environ.get("DATABASE")
        self.__username = os.environ.get("USER")
        self.__password = os.environ.get("PASSWORD")
        self.__engine = None
        self.connect()
    def get_server(self):
        return self.__server
    
    def get_username(self):
        return self.__username
    
    def get_password(self):
        return self.__password
    
    def get_database(self):
        return self.__database
    
    def get_engine(self):
        """Retorna el motor de conexión almacenado."""
        return self.__engine
    
    def connect(self):
        """
        Crea el motor de conexión (engine) y lo guarda en self.__engine.
        Retorna el motor de conexión.
        """
        if self.__engine is not None:
            print("Engine ya existe. Retornando el existente.")
            return self.__engine
            
        try:
            # 1. Lógica para construir la URL (usando los getters)
            SERVER_URL = self.get_server() # Asegúrate de que esto incluye IP,PUERTO si es necesario
            DRIVER = 'SQL Server' # Ajusta si usas {SQL Server}
            quoted_driver = urllib.parse.quote_plus(DRIVER)
            
            # Opciones MARS para evitar el error HY010
            CONNECTION_OPTIONS = "MARS_Connection=yes;MultipleActiveResultSets=True"
            quoted_connection_options = urllib.parse.quote_plus(CONNECTION_OPTIONS)
            
            SQLALCHEMY_DATABASE_URL = (
                f"mssql+pyodbc://{self.get_username()}:{self.get_password()}@{SERVER_URL}/{self.get_database()}?"
                f"driver={quoted_driver}&{quoted_connection_options}"
            )

            # 2. Crear y guardar el motor
            engine = create_engine(SQLALCHEMY_DATABASE_URL)
            self.__engine = engine # ⬅️ Aquí se guarda el motor

            # Prueba de conexión
            with engine.connect():
                print("🎉 Motor de conexión creado exitosamente y guardado en la instancia.")
                
            return self.__engine
            
        except Exception as e:
            print(f"❌ Error al crear el motor de conexión: {e}")
            self.__engine = None
            return None
        
    def select_all(self,table):
        query = f"Select * from {table}"
        return pd.read_sql(query,self.get_engine())

