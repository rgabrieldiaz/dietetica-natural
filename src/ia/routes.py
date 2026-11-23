from pathlib import Path
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import current_user
from joblib import load
from src.models import Producto

ia_bp = Blueprint("ia", __name__, url_prefix="/ia")

# Carga segura del modelo entrenado
modelo_path = Path(__file__).resolve().parent / "modelo_dietetica.joblib"
modelo_data = None
modelo = None

if modelo_path.exists():
    try:
        modelo_data = load(modelo_path)
        modelo = modelo_data["modelo"]
    except Exception as e:
        print(f"[ADVERTENCIA IA] Error al cargar el modelo joblib: {e}")


@ia_bp.before_request
def verificar_autenticacion():
    if not current_user.is_authenticated:
        if request.path.startswith("/ia/api/") or request.is_json or request.headers.get("Accept") == "application/json":
            return jsonify({"error": "No autorizado", "message": "Se requiere autenticación para operar con la API de IA"}), 401
        return redirect(url_for("auth.login", next=request.url))


def _calcular_recomendacion(dias, rotacion, stock):
    """
    Genera el diagnóstico operativo de reposición sugerido por el modelo.
    """
    consumo_diario = rotacion / 7.0 if rotacion > 0 else 0.5
    stock_objetivo_30_dias = consumo_diario * 30.0
    sugerencia_compra = max(0.0, stock_objetivo_30_dias - stock)

    if dias <= 7.0:
        urgencia = "CRÍTICA"
        badge_urgencia = "bg-red-100 text-red-800 border-red-300"
        mensaje = "Alerta: El producto corre riesgo inminente de quiebre de stock en menos de una semana. Reordenar con proveedor urgente."
    elif dias <= 15.0:
        urgencia = "MODERADA"
        badge_urgencia = "bg-amber-100 text-amber-800 border-amber-300"
        mensaje = "Atención: La autonomía es inferior a 15 días. Conviene emitir orden de reposición esta semana."
    else:
        urgencia = "ÓPTIMA"
        badge_urgencia = "bg-emerald-100 text-emerald-800 border-emerald-300"
        mensaje = "Estado saludable: El stock actual cubre holgadamente la demanda proyectada."

    return {
        "urgencia": urgencia,
        "badge_urgencia": badge_urgencia,
        "mensaje": mensaje,
        "sugerencia_compra": round(sugerencia_compra, 2)
    }


@ia_bp.route("/prediccion", methods=["GET", "POST"])
def prediccion():
    productos = Producto.query.order_by(Producto.nombre.asc()).all()
    resultado = None
    producto_seleccionado_id = request.args.get("producto_id", type=int)

    # Valores por defecto para el formulario
    stock_val = 5.0
    rotacion_val = 2.0
    nombre_prod = "Cálculo Personalizado"

    proveedor_obj = None
    if producto_seleccionado_id:
        prod = Producto.query.get(producto_seleccionado_id)
        if prod:
            stock_val = prod.stock_actual
            rotacion_val = prod.rotacion_semanal_estimada
            nombre_prod = f"{prod.nombre} ({prod.categoria})"
            proveedor_obj = prod.proveedor

    if request.method == "POST":
        try:
            prod_id_form = request.form.get("producto_id")
            stock_val = float(request.form.get("stock_actual", 0.0))
            rotacion_val = float(request.form.get("rotacion_semanal", 1.0))

            if prod_id_form and prod_id_form.isdigit():
                prod_obj = Producto.query.get(int(prod_id_form))
                if prod_obj:
                    nombre_prod = f"{prod_obj.nombre} ({prod_obj.categoria})"
                    proveedor_obj = prod_obj.proveedor

            if rotacion_val <= 0:
                flash("La rotación semanal estimada debe ser mayor a 0.", "warning")
            elif modelo is None:
                flash("El modelo predictivo no está cargado. Ejecutá 'python train_model.py'.", "danger")
            else:
                # Inferencia con Scikit-Learn
                pred_dias = float(modelo.predict([[stock_val, rotacion_val]])[0])
                pred_dias = max(0.0, round(pred_dias, 1))

                recomendacion = _calcular_recomendacion(pred_dias, rotacion_val, stock_val)

                resultado = {
                    "nombre_producto": nombre_prod,
                    "stock_actual": stock_val,
                    "rotacion_semanal": rotacion_val,
                    "dias_autonomia": pred_dias,
                    "proveedor_nombre": proveedor_obj.nombre if proveedor_obj else None,
                    "proveedor_telefono": proveedor_obj.telefono if proveedor_obj else None,
                    **recomendacion
                }
        except ValueError:
            flash("Ingresá valores numéricos válidos para el cálculo.", "danger")

    metricas = modelo_data.get("metricas", {}) if modelo_data else {}

    return render_template(
        "prediccion.html",
        productos=productos,
        resultado=resultado,
        producto_seleccionado_id=producto_seleccionado_id,
        stock_val=stock_val,
        rotacion_val=rotacion_val,
        metricas=metricas
    )


@ia_bp.route("/api/predecir", methods=["POST"])
def api_predecir():
    if modelo is None:
        return jsonify({"error": "Modelo no cargado"}), 500

    data = request.get_json() or {}
    try:
        stock = float(data.get("stock_actual", 0.0))
        rotacion = float(data.get("rotacion_semanal", 1.0))
    except (ValueError, TypeError):
        return jsonify({"error": "Parámetros numéricos inválidos"}), 400

    pred_dias = float(modelo.predict([[stock, rotacion]])[0])
    pred_dias = max(0.0, round(pred_dias, 1))
    rec = _calcular_recomendacion(pred_dias, rotacion, stock)

    return jsonify({
        "stock_actual": stock,
        "rotacion_semanal": rotacion,
        "dias_autonomia_predichos": pred_dias,
        **rec
    }), 200
