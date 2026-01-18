import pandas as pd
import streamlit as st


import os
import sys

# Ruta ABSOLUTA a la raíz del proyecto (carpeta PROYECTO1-OPTIMIZACION-RUTAS)
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from app.database import database

hola = 