from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import current_user
from src.models import (
    Producto, Proveedor, bd,
    CATEGORIAS_VALIDAS, UNIDADES_VALIDAS
)

inventario_bp = Blueprint("inventario", __name__)

# Middleware de seguridad: distingue entre peticiones Web (redirect) y peticiones API REST (401 JSON)
@inventario_bp.before_request
def verificar_autenticacion():
    if not current_user.is_authenticated:
        if request.path.startswith("/api/") or request.is_json:
            return jsonify({"error": "No autorizado", "message": "Se requiere autenticación para operar con la API"}), 401
        return redirect(url_for("auth.login", next=request.url))


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
# Endpoints API REST para Evaluación de Cátedra (Visto en Clases 17 y 18)
# ==============================================================================

@inventario_bp.route("/api/productos", methods=["GET"])
def api_listar_productos():
    productos = Producto.query.all()
    return jsonify([p.to_dict() for p in productos]), 200


@inventario_bp.route("/api/productos/<int:id>", methods=["GET"])
def api_detalle_producto(id):
    producto = bd.session.get(Producto, id)
    if not producto:
        return jsonify({"error": "Producto no encontrado"}), 404
    return jsonify(producto.to_dict()), 200


@inventario_bp.route("/api/productos", methods=["POST"])
def api_crear_producto():
    data = request.get_json() or {}
    nombre = data.get("nombre", "").strip()
    categoria = data.get("categoria", "").strip()
    stock = data.get("stock_actual", 0.0)
    unidad = data.get("unidad_medida", "kg").strip()
    precio = data.get("precio_unitario", 0.0)
    rotacion = data.get("rotacion_semanal_estimada", 2.0)
    id_proveedor = data.get("id_proveedor")

    if not nombre or not categoria:
        return jsonify({"error": "Nombre y categoría son obligatorios"}), 400

    if categoria not in CATEGORIAS_VALIDAS:
        return jsonify({"error": f"Categoría inválida. Debe ser una de: {', '.join(CATEGORIAS_VALIDAS)}"}), 400

    # RN-01: Unicidad de nombre en la misma categoría
    if Producto.query.filter_by(nombre=nombre, categoria=categoria).first():
        return jsonify({"error": f"Ya existe un producto con el nombre '{nombre}' en '{categoria}' (RN-01)"}), 409

    try:
        stock = float(stock)
        precio = float(precio)
        rotacion = float(rotacion)
    except (ValueError, TypeError):
        return jsonify({"error": "Valores numéricos de stock, precio o rotación inválidos"}), 400

    # RN-02: Stock no negativo
    if stock < 0:
        return jsonify({"error": "El stock no puede ser negativo (RN-02)"}), 400

    # RN-03: Precio positivo
    if precio <= 0:
        return jsonify({"error": "El precio debe ser mayor a 0 (RN-03)"}), 400

    # RN-05: Opcionalidad de asociación (id_proveedor puede ser None)
    if id_proveedor is not None:
        try:
            id_proveedor = int(id_proveedor)
            if not bd.session.get(Proveedor, id_proveedor):
                return jsonify({"error": "El proveedor indicado no existe"}), 404
        except (ValueError, TypeError):
            id_proveedor = None

    nuevo = Producto(
        nombre=nombre,
        categoria=categoria,
        stock_actual=stock,
        unidad_medida=unidad,
        precio_unitario=precio,
        rotacion_semanal_estimada=rotacion,
        id_proveedor=id_proveedor
    )
    bd.session.add(nuevo)
    bd.session.commit()
    return jsonify(nuevo.to_dict()), 201


@inventario_bp.route("/api/productos/<int:id>", methods=["PUT"])
def api_actualizar_producto(id):
    producto = bd.session.get(Producto, id)
    if not producto:
        return jsonify({"error": "Producto no encontrado"}), 404

    data = request.get_json() or {}
    nombre = data.get("nombre", producto.nombre).strip()
    categoria = data.get("categoria", producto.categoria).strip()

    if categoria not in CATEGORIAS_VALIDAS:
        return jsonify({"error": "Categoría inválida"}), 400

    # RN-01: Unicidad excluyendo el producto actual
    existente = Producto.query.filter(
        Producto.nombre == nombre,
        Producto.categoria == categoria,
        Producto.id_producto != id
    ).first()
    if existente:
        return jsonify({"error": f"Ya existe otro producto con el nombre '{nombre}' en '{categoria}' (RN-01)"}), 409

    if "stock_actual" in data:
        try:
            stock = float(data["stock_actual"])
            if stock < 0:
                return jsonify({"error": "El stock no puede ser negativo (RN-02)"}), 400
            producto.stock_actual = stock
        except (ValueError, TypeError):
            return jsonify({"error": "Stock inválido"}), 400

    if "precio_unitario" in data:
        try:
            precio = float(data["precio_unitario"])
            if precio <= 0:
                return jsonify({"error": "El precio debe ser mayor a 0 (RN-03)"}), 400
            producto.precio_unitario = precio
        except (ValueError, TypeError):
            return jsonify({"error": "Precio inválido"}), 400

    producto.nombre = nombre
    producto.categoria = categoria
    if "unidad_medida" in data:
        producto.unidad_medida = data["unidad_medida"]
    if "rotacion_semanal_estimada" in data:
        producto.rotacion_semanal_estimada = float(data["rotacion_semanal_estimada"])
    if "id_proveedor" in data:
        producto.id_proveedor = data["id_proveedor"]

    bd.session.commit()
    return jsonify(producto.to_dict()), 200


@inventario_bp.route("/api/productos/<int:id>", methods=["DELETE"])
def api_eliminar_producto(id):
    producto = bd.session.get(Producto, id)
    if not producto:
        return jsonify({"error": "Producto no encontrado"}), 404

    nombre = producto.nombre
    bd.session.delete(producto)
    bd.session.commit()
    return jsonify({"message": f"Producto '{nombre}' eliminado exitosamente"}), 200


@inventario_bp.route("/api/proveedores", methods=["GET"])
def api_listar_proveedores():
    proveedores = Proveedor.query.all()
    return jsonify([p.to_dict() for p in proveedores]), 200


@inventario_bp.route("/api/proveedores", methods=["POST"])
def api_crear_proveedor():
    data = request.get_json() or {}
    nombre = data.get("nombre", "").strip()
    if not nombre:
        return jsonify({"error": "El nombre del proveedor es obligatorio"}), 400

    nuevo = Proveedor(
        nombre=nombre,
        contacto=data.get("contacto"),
        telefono=data.get("telefono"),
        email=data.get("email"),
        direccion=data.get("direccion")
    )
    bd.session.add(nuevo)
    bd.session.commit()
    return jsonify(nuevo.to_dict()), 201


@inventario_bp.route("/api/proveedores/<int:id>", methods=["DELETE"])
def api_eliminar_proveedor(id):
    proveedor = bd.session.get(Proveedor, id)
    if not proveedor:
        return jsonify({"error": "Proveedor no encontrado"}), 404

    # RN-04: No se puede borrar físicamente un proveedor con productos asociados
    cant_productos = len(proveedor.productos)
    if cant_productos > 0:
        return jsonify({
            "error": f"No se puede eliminar el proveedor '{proveedor.nombre}' porque tiene {cant_productos} producto(s) vinculado(s) (Regla RN-04)"
        }), 409

    nombre = proveedor.nombre
    bd.session.delete(proveedor)
    bd.session.commit()
    return jsonify({"message": f"Proveedor '{nombre}' eliminado exitosamente"}), 200
