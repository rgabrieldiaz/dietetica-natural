from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required
from src.models import (
    Producto, Proveedor, bd,
    CATEGORIAS_VALIDAS, UNIDADES_VALIDAS
)

inventario_bp = Blueprint("inventario", __name__)

# Middleware de seguridad: toda la sección de inventario requiere autenticación activa
@inventario_bp.before_request
@login_required
def verificar_autenticacion():
    pass


# ==============================================================================
# Vistas Web de Productos (Jinja2)
# ==============================================================================

@inventario_bp.route("/inventario")
def listar_inventario():
    # Parámetros de filtrado
    categoria_filtro = request.args.get("categoria", "").strip()
    estado_filtro = request.args.get("estado", "").strip()
    busqueda = request.args.get("buscar", "").strip()

    query = Producto.query

    if categoria_filtro and categoria_filtro in CATEGORIAS_VALIDAS:
        query = query.filter_by(categoria=categoria_filtro)

    if busqueda:
        query = query.filter(Producto.nombre.ilike(f"%{busqueda}%"))

    productos = query.order_by(Producto.nombre.asc()).all()

    # Filtrado posterior por estado de alerta (RN-06)
    if estado_filtro and estado_filtro in ["NORMAL", "STOCK_BAJO", "AGOTADO"]:
        productos = [p for p in productos if p.estado_stock == estado_filtro]

    # Estadísticas para el resumen del dashboard
    todos_los_productos = Producto.query.all()
    total_productos = len(todos_los_productos)
    agotados_count = sum(1 for p in todos_los_productos if p.estado_stock == "AGOTADO")
    bajos_count = sum(1 for p in todos_los_productos if p.estado_stock == "STOCK_BAJO")
    valor_inventario = sum(p.stock_actual * p.precio_unitario for p in todos_los_productos)

    return render_template(
        "inventario.html",
        productos=productos,
        categorias=CATEGORIAS_VALIDAS,
        categoria_filtro=categoria_filtro,
        estado_filtro=estado_filtro,
        busqueda=busqueda,
        total_productos=total_productos,
        agotados_count=agotados_count,
        bajos_count=bajos_count,
        valor_inventario=valor_inventario
    )


@inventario_bp.route("/inventario/nuevo", methods=["GET", "POST"])
def nuevo_producto():
    proveedores = Proveedor.query.order_by(Proveedor.nombre.asc()).all()

    if request.method == "POST":
        nombre = request.form.get("nombre", "").strip()
        categoria = request.form.get("categoria", "").strip()
        stock_str = request.form.get("stock_actual", "0").strip()
        unidad = request.form.get("unidad_medida", "kg").strip()
        precio_str = request.form.get("precio_unitario", "0").strip()
        rotacion_str = request.form.get("rotacion_semanal_estimada", "2.0").strip()
        id_proveedor = request.form.get("id_proveedor")

        # Validaciones de Reglas de Negocio
        if not nombre or not categoria:
            flash("El nombre y la categoría son obligatorios.", "danger")
            return render_template("producto_form.html", categorias=CATEGORIAS_VALIDAS, unidades=UNIDADES_VALIDAS, proveedores=proveedores, producto=None)

        if categoria not in CATEGORIAS_VALIDAS:
            flash(f"Categoría inválida. Debe ser una de: {', '.join(CATEGORIAS_VALIDAS)}", "danger")
            return render_template("producto_form.html", categorias=CATEGORIAS_VALIDAS, unidades=UNIDADES_VALIDAS, proveedores=proveedores, producto=None)

        # RN-01: Nombre único por categoría
        existente = Producto.query.filter_by(nombre=nombre, categoria=categoria).first()
        if existente:
            flash(f"Ya existe un producto con el nombre '{nombre}' en la categoría '{categoria}' (RN-01).", "danger")
            return render_template("producto_form.html", categorias=CATEGORIAS_VALIDAS, unidades=UNIDADES_VALIDAS, proveedores=proveedores, producto=None)

        try:
            stock = float(stock_str)
            precio = float(precio_str)
            rotacion = float(rotacion_str)
        except ValueError:
            flash("Los valores numéricos de stock, precio y rotación no son válidos.", "danger")
            return render_template("producto_form.html", categorias=CATEGORIAS_VALIDAS, unidades=UNIDADES_VALIDAS, proveedores=proveedores, producto=None)

        # RN-02 y RN-03
        if stock < 0:
            flash("El stock actual no puede ser un valor negativo (RN-02).", "danger")
            return render_template("producto_form.html", categorias=CATEGORIAS_VALIDAS, unidades=UNIDADES_VALIDAS, proveedores=proveedores, producto=None)

        if precio <= 0:
            flash("El precio unitario debe ser mayor a 0 (RN-03).", "danger")
            return render_template("producto_form.html", categorias=CATEGORIAS_VALIDAS, unidades=UNIDADES_VALIDAS, proveedores=proveedores, producto=None)

        id_prov = int(id_proveedor) if (id_proveedor and id_proveedor.isdigit()) else None

        nuevo = Producto(
            nombre=nombre,
            categoria=categoria,
            stock_actual=stock,
            unidad_medida=unidad,
            precio_unitario=precio,
            rotacion_semanal_estimada=rotacion,
            id_proveedor=id_prov
        )
        bd.session.add(nuevo)
        bd.session.commit()

        flash(f"Producto '{nombre}' agregado exitosamente al inventario.", "success")
        return redirect(url_for("inventario.listar_inventario"))

    return render_template(
        "producto_form.html",
        categorias=CATEGORIAS_VALIDAS,
        unidades=UNIDADES_VALIDAS,
        proveedores=proveedores,
        producto=None
    )


@inventario_bp.route("/inventario/editar/<int:id_producto>", methods=["GET", "POST"])
def editar_producto(id_producto):
    producto = Producto.query.get_or_404(id_producto)
    proveedores = Proveedor.query.order_by(Proveedor.nombre.asc()).all()

    if request.method == "POST":
        nombre = request.form.get("nombre", "").strip()
        categoria = request.form.get("categoria", "").strip()
        stock_str = request.form.get("stock_actual", "0").strip()
        unidad = request.form.get("unidad_medida", "kg").strip()
        precio_str = request.form.get("precio_unitario", "0").strip()
        rotacion_str = request.form.get("rotacion_semanal_estimada", "2.0").strip()
        id_proveedor = request.form.get("id_proveedor")

        if not nombre or not categoria:
            flash("El nombre y la categoría son obligatorios.", "danger")
            return render_template("producto_form.html", categorias=CATEGORIAS_VALIDAS, unidades=UNIDADES_VALIDAS, proveedores=proveedores, producto=producto)

        # RN-01: Unicidad por categoría excluyendo el producto actual
        existente = Producto.query.filter(
            Producto.nombre == nombre,
            Producto.categoria == categoria,
            Producto.id_producto != id_producto
        ).first()
        if existente:
            flash(f"Ya existe otro producto con el nombre '{nombre}' en '{categoria}'.", "danger")
            return render_template("producto_form.html", categorias=CATEGORIAS_VALIDAS, unidades=UNIDADES_VALIDAS, proveedores=proveedores, producto=producto)

        try:
            stock = float(stock_str)
            precio = float(precio_str)
            rotacion = float(rotacion_str)
        except ValueError:
            flash("Valores numéricos inválidos.", "danger")
            return render_template("producto_form.html", categorias=CATEGORIAS_VALIDAS, unidades=UNIDADES_VALIDAS, proveedores=proveedores, producto=producto)

        if stock < 0:
            flash("El stock no puede ser negativo (RN-02).", "danger")
            return render_template("producto_form.html", categorias=CATEGORIAS_VALIDAS, unidades=UNIDADES_VALIDAS, proveedores=proveedores, producto=producto)

        if precio <= 0:
            flash("El precio debe ser mayor a 0 (RN-03).", "danger")
            return render_template("producto_form.html", categorias=CATEGORIAS_VALIDAS, unidades=UNIDADES_VALIDAS, proveedores=proveedores, producto=producto)

        producto.nombre = nombre
        producto.categoria = categoria
        producto.stock_actual = stock
        producto.unidad_medida = unidad
        producto.precio_unitario = precio
        producto.rotacion_semanal_estimada = rotacion
        producto.id_proveedor = int(id_proveedor) if (id_proveedor and id_proveedor.isdigit()) else None

        bd.session.commit()
        flash(f"Producto '{producto.nombre}' actualizado correctamente.", "success")
        return redirect(url_for("inventario.listar_inventario"))

    return render_template(
        "producto_form.html",
        categorias=CATEGORIAS_VALIDAS,
        unidades=UNIDADES_VALIDAS,
        proveedores=proveedores,
        producto=producto
    )


@inventario_bp.route("/inventario/eliminar/<int:id_producto>", methods=["POST"])
def eliminar_producto(id_producto):
    producto = Producto.query.get_or_404(id_producto)
    nombre = producto.nombre
    bd.session.delete(producto)
    bd.session.commit()
    flash(f"Producto '{nombre}' eliminado del inventario.", "info")
    return redirect(url_for("inventario.listar_inventario"))


# ==============================================================================
# Vistas Web de Proveedores (Jinja2)
# ==============================================================================

@inventario_bp.route("/proveedores")
def listar_proveedores():
    proveedores = Proveedor.query.order_by(Proveedor.nombre.asc()).all()
    return render_template("proveedores.html", proveedores=proveedores)


@inventario_bp.route("/proveedores/nuevo", methods=["GET", "POST"])
def nuevo_proveedor():
    if request.method == "POST":
        nombre = request.form.get("nombre", "").strip()
        contacto = request.form.get("contacto", "").strip()
        telefono = request.form.get("telefono", "").strip()
        email = request.form.get("email", "").strip()
        direccion = request.form.get("direccion", "").strip()

        if not nombre:
            flash("El nombre de la empresa o proveedor es obligatorio.", "danger")
            return render_template("proveedor_form.html", proveedor=None)

        nuevo = Proveedor(
            nombre=nombre,
            contacto=contacto or None,
            telefono=telefono or None,
            email=email or None,
            direccion=direccion or None
        )
        bd.session.add(nuevo)
        bd.session.commit()

        flash(f"Proveedor '{nombre}' registrado exitosamente.", "success")
        return redirect(url_for("inventario.listar_proveedores"))

    return render_template("proveedor_form.html", proveedor=None)


@inventario_bp.route("/proveedores/editar/<int:id_proveedor>", methods=["GET", "POST"])
def editar_proveedor(id_proveedor):
    proveedor = Proveedor.query.get_or_404(id_proveedor)

    if request.method == "POST":
        nombre = request.form.get("nombre", "").strip()
        if not nombre:
            flash("El nombre del proveedor es obligatorio.", "danger")
            return render_template("proveedor_form.html", proveedor=proveedor)

        proveedor.nombre = nombre
        proveedor.contacto = request.form.get("contacto", "").strip() or None
        proveedor.telefono = request.form.get("telefono", "").strip() or None
        proveedor.email = request.form.get("email", "").strip() or None
        proveedor.direccion = request.form.get("direccion", "").strip() or None

        bd.session.commit()
        flash(f"Proveedor '{proveedor.nombre}' actualizado con éxito.", "success")
        return redirect(url_for("inventario.listar_proveedores"))

    return render_template("proveedor_form.html", proveedor=proveedor)


@inventario_bp.route("/proveedores/eliminar/<int:id_proveedor>", methods=["POST"])
def eliminar_proveedor(id_proveedor):
    proveedor = Proveedor.query.get_or_404(id_proveedor)
    
    # RN-04 (Protección de Integridad en Bajas):
    # No se puede borrar físicamente un proveedor si posee productos vinculados en el inventario.
    cant_productos = len(proveedor.productos)
    if cant_productos > 0:
        flash(
            f"No se puede eliminar al proveedor '{proveedor.nombre}' porque tiene {cant_productos} "
            f"producto(s) vinculado(s) en inventario (Regla RN-04). Reasigne o elimine los productos primero.",
            "danger"
        )
        return redirect(url_for("inventario.listar_proveedores"))

    nombre = proveedor.nombre
    bd.session.delete(proveedor)
    bd.session.commit()
    flash(f"Proveedor '{nombre}' eliminado correctamente.", "info")
    return redirect(url_for("inventario.listar_proveedores"))


# ==============================================================================
# Endpoints API REST para Evaluación de Cátedra
# ==============================================================================

@inventario_bp.route("/api/productos", methods=["GET"])
def api_listar_productos():
    productos = Producto.query.all()
    return jsonify([p.to_dict() for p in productos]), 200


@inventario_bp.route("/api/productos/<int:id>", methods=["GET"])
def api_detalle_producto(id):
    producto = Producto.query.get_or_404(id)
    return jsonify(producto.to_dict()), 200


@inventario_bp.route("/api/proveedores", methods=["GET"])
def api_listar_proveedores():
    proveedores = Proveedor.query.all()
    return jsonify([p.to_dict() for p in proveedores]), 200
