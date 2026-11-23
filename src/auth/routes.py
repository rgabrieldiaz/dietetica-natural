from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from src.models import Usuario, bd
from src.app import bcrypt

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("inventario.listar_inventario"))

    if request.method == "POST":
        identificador = request.form.get("username_or_email", "").strip()
        password = request.form.get("password", "").strip()

        if not identificador or not password:
            flash("Por favor completá todos los campos requeridos.", "danger")
            return render_template("login.html")

        # Permite iniciar sesión tanto con email como con nombre de usuario
        usuario = Usuario.query.filter(
            (Usuario.email == identificador) | (Usuario.username == identificador)
        ).first()

        if usuario and bcrypt.check_password_hash(usuario.password_hash, password):
            login_user(usuario)
            flash(f"¡Bienvenido de nuevo, {usuario.username}!", "success")
            next_page = request.args.get("next")
            return redirect(next_page or url_for("inventario.listar_inventario"))
        else:
            flash("Credenciales incorrectas. Verificá tu usuario y contraseña.", "danger")

    return render_template("login.html")


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("inventario.listar_inventario"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "").strip()
        confirm_password = request.form.get("confirm_password", "").strip()

        if not username or not email or not password:
            flash("Todos los campos son obligatorios.", "danger")
            return render_template("register.html")

        if password != confirm_password:
            flash("Las contraseñas ingresadas no coinciden.", "danger")
            return render_template("register.html")

        if len(password) < 6:
            flash("La contraseña debe contener al menos 6 caracteres.", "warning")
            return render_template("register.html")

        # Verificar unicidad
        if Usuario.query.filter_by(username=username).first():
            flash("El nombre de usuario ya está registrado por otro operador.", "danger")
            return render_template("register.html")

        if Usuario.query.filter_by(email=email).first():
            flash("El correo electrónico ya se encuentra registrado.", "danger")
            return render_template("register.html")

        # Hasheo seguro con Bcrypt (visto en Clase 17)
        hashed_pw = bcrypt.generate_password_hash(password).decode("utf-8")
        nuevo_usuario = Usuario(username=username, email=email, password_hash=hashed_pw)
        bd.session.add(nuevo_usuario)
        bd.session.commit()

        flash("Registro exitoso. Ahora podés iniciar sesión con tus credenciales.", "success")
        return redirect(url_for("auth.login"))

    return render_template("register.html")


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Sesión cerrada correctamente.", "info")
    return redirect(url_for("auth.login"))


# Endpoints API REST para integración y evaluación
@auth_bp.route("/api/login", methods=["POST"])
def api_login():
    data = request.get_json() or request.form
    identificador = data.get("username_or_email", "").strip()
    password = data.get("password", "").strip()

    usuario = Usuario.query.filter(
        (Usuario.email == identificador) | (Usuario.username == identificador)
    ).first()

    if usuario and bcrypt.check_password_hash(usuario.password_hash, password):
        login_user(usuario)
        return jsonify({"success": True, "message": "Login exitoso", "user": usuario.to_dict()}), 200

    return jsonify({"success": False, "message": "Credenciales inválidas"}), 401
