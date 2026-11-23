"""
Punto de Entrada Principal (Runner)
Dietética Natural — Gestión de Inventario y Predicción IA
Materia: Análisis y Metodología de Sistemas (S0D41)
"""

import os
from src.app import create_app

# Instancia de la aplicación Flask creada mediante Application Factory
app = create_app()

if __name__ == "__main__":
    # Render asigna dinámicamente un puerto a través de la variable PORT
    puerto = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=puerto, debug=True)
