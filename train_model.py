"""
Script de Entrenamiento del Modelo de Machine Learning
Materia: Análisis y Metodología de Sistemas (S0D41) - Escuela Da Vinci
Profesor: Lic. Diego Simonelli
Alumnos: Ricardo Gabriel Díaz (Legajo 29135452) y Benítez

Modelo: Regresión Lineal para Estimación de Días de Autonomía de Stock
Permite a la Dietética predecir cuántos días restan antes del desabastecimiento
en función del stock físico disponible y la tasa de rotación semanal estimada.
"""

import os
from pathlib import Path
from joblib import dump
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import r2_score, mean_absolute_error, mean_squared_error

def generar_datos_historicos():
    """
    Genera un conjunto de datos realista de consumo de una dietética de barrio.
    X: [stock_actual (kg/unidades), rotacion_semanal (kg/unidades)]
    y: dias_autonomia = (stock / rotacion) * 7 + variabilidad aleatoria
    """
    np.random.seed(42)
    n_samples = 150

    # Stock actual entre 0.5 kg y 60 kg
    stock_actual = np.random.uniform(1.0, 60.0, n_samples)
    
    # Rotación semanal entre 0.8 kg y 15 kg por semana
    rotacion_semanal = np.random.uniform(0.8, 15.0, n_samples)

    # Días de autonomía teóricos con ruido estocástico de consumo
    ruido = np.random.normal(0, 1.2, n_samples)
    dias_autonomia = (stock_actual / rotacion_semanal) * 7.0 + ruido
    
    # El stock nunca puede durar menos de 0 días
    dias_autonomia = np.clip(dias_autonomia, 0.5, 90.0)

    X = np.column_stack([stock_actual, rotacion_semanal])
    y = dias_autonomia
    return X, y

def main():
    print("=" * 60)
    print("Iniciando entrenamiento del Modelo Predictivo de Dietética")
    print("=" * 60)

    X, y = generar_datos_historicos()

    # Split train/test
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.25, random_state=42
    )

    # Modelo de Regresión
    modelo = LinearRegression()
    modelo.fit(X_train, y_train)

    # Evaluación
    y_pred = modelo.predict(X_test)
    r2 = r2_score(y_test, y_pred)
    mae = mean_absolute_error(y_test, y_pred)
    mse = mean_squared_error(y_test, y_pred)

    print(f"R² Score: {r2:.4f}")
    print(f"MAE (Error Absoluto Medio): {mae:.2f} días")
    print(f"MSE (Error Cuadrático Medio): {mse:.2f}")

    # Guardar modelo serializado con joblib en src/ia/
    base_dir = Path(__file__).resolve().parent
    ia_dir = base_dir / "src" / "ia"
    ia_dir.mkdir(parents=True, exist_ok=True)

    modelo_path = ia_dir / "modelo_dietetica.joblib"
    datos_modelo = {
        "modelo": modelo,
        "features": ["stock_actual", "rotacion_semanal"],
        "metricas": {
            "r2": float(r2),
            "mae": float(mae),
            "mse": float(mse)
        },
        "coeficientes": modelo.coef_.tolist(),
        "intercept": float(modelo.intercept_)
    }
    dump(datos_modelo, modelo_path)
    print(f"Modelo exportado exitosamente a: {modelo_path}")

    # Generar gráficos estáticos para la visualización en la app
    plots_dir = base_dir / "src" / "static" / "plots"
    plots_dir.mkdir(parents=True, exist_ok=True)

    # Gráfico 1: Real vs Predicho
    plt.figure(figsize=(7, 5))
    plt.scatter(y_test, y_pred, color="#10B981", alpha=0.75, edgecolors="k", label="Observaciones de Test")
    min_val = min(y_test.min(), y_pred.min())
    max_val = max(y_test.max(), y_pred.max())
    plt.plot([min_val, max_val], [min_val, max_val], color="#EF4444", linestyle="--", linewidth=2, label="Predicción Ideal")
    plt.xlabel("Días de Autonomía Reales")
    plt.ylabel("Días de Autonomía Predichos por el Modelo")
    plt.title(f"Ajuste del Modelo Predictivo (R² = {r2:.3f})")
    plt.grid(True, linestyle=":", alpha=0.6)
    plt.legend()
    plt.tight_layout()
    plt.savefig(plots_dir / "regresion_autonomia.png", dpi=150)
    plt.clf()

    # Gráfico 2: Distribución de Errores (Residuos)
    residuos = y_test - y_pred
    plt.figure(figsize=(7, 5))
    plt.hist(residuos, bins=15, color="#3B82F6", edgecolor="black", alpha=0.7)
    plt.axvline(0, color="#EF4444", linestyle="--", linewidth=2)
    plt.xlabel("Error de Predicción (Días Reales - Días Predichos)")
    plt.ylabel("Frecuencia")
    plt.title("Distribución de Residuos del Modelo")
    plt.grid(True, linestyle=":", alpha=0.6)
    plt.tight_layout()
    plt.savefig(plots_dir / "residuos_modelo.png", dpi=150)
    plt.close()

    print(f"Gráficos analíticos generados en: {plots_dir}")
    print("Entrenamiento finalizado con éxito.")

if __name__ == "__main__":
    main()
