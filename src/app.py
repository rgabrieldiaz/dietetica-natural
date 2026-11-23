import os
from pathlib import Path
from flask import Flask, redirect, url_for
from flask_login import LoginManager, current_user
from flask_bcrypt import Bcrypt
from dotenv import load_dotenv

# Cargar variables de entorno desde .env si existe
load_dotenv()

# Instancias globales de extensiones
login_manager = LoginManager()
bcrypt = Bcrypt()

login_manager.login_view = "auth.login"
login_manager.login_message = "Por favor iniciá sesión para acceder al sistema."
login_manager.login_message_category = "warning"

def create_app():
    # Rutas absolutas para templates y static dentro de src/
    base_dir = Path(__file__).resolve().parent
    template_dir = base_dir / "templates"
    static_dir = base_dir / "static"

    app = Flask(
        __name__,
        template_folder=str(template_dir),
        static_folder=str(static_dir)
    )

    # Configuración de seguridad
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dietetica_secreto_seguro_2026")

    # Configuración Dual de Base de Datos:
    # 1. Local: SQLite (dietetica.db)
    # 2. Producción (Render / Cloud): PostgreSQL desde DATABASE_URL
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        # Por defecto SQLite local en la raíz del proyecto
        instance_db = base_dir.parent / "dietetica.db"
        database_url = f"sqlite:///{instance_db}"
    elif database_url.startswith("postgres://"):
        # Fix compatibilidad SQLAlchemy 2.x para URLs de Render / Supabase
        database_url = database_url.replace("postgres://", "postgresql://", 1)

    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # Inicialización de extensiones
    from src.models import bd, Usuario, Proveedor, Producto
    bd.init_app(app)
    login_manager.init_app(app)
    bcrypt.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return bd.session.get(Usuario, int(user_id))

    # Registro de Blueprints
    from src.auth.routes import auth_bp
    from src.inventario.routes import inventario_bp
    from src.ia.routes import ia_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(inventario_bp)
    app.register_blueprint(ia_bp)

    @app.route("/")
    def index():
        if current_user.is_authenticated:
            return redirect(url_for("inventario.listar_inventario"))
        return redirect(url_for("auth.login"))

    # Creación automática de tablas y datos iniciales de prueba (Seed)
    with app.app_context():
        bd.create_all()
        _seed_datos_iniciales(bd, Usuario, Proveedor, Producto)

    return app


def _seed_datos_iniciales(bd, Usuario, Proveedor, Producto):
    """
    Carga datos semilla si la base de datos está vacía para que
    el docente y los evaluadores puedan probar la app de inmediato.
    """
    # 1. Usuario Administrador por defecto
    if not Usuario.query.first():
        pw_hash = bcrypt.generate_password_hash("dietetica2026").decode("utf-8")
        admin = Usuario(
            username="admin",
            email="admin@dietetica.com",
            password_hash=pw_hash
        )
        bd.session.add(admin)
        bd.session.commit()

    # 2. Proveedores iniciales
    if not Proveedor.query.first():
        p1 = Proveedor(
            nombre="Distribuidora Natural Sur",
            contacto="Mariana Gómez",
            telefono="11-4523-8899",
            email="ventas@naturalsur.com.ar",
            direccion="Av. Mitre 1420, Avellaneda"
        )
        p2 = Proveedor(
            nombre="Molinos del Valle",
            contacto="Carlos Pérez",
            telefono="11-6632-1144",
            email="pedidos@molinosdelvalle.com",
            direccion="Ruta 8 Km 54, Pilar"
        )
        p3 = Proveedor(
            nombre="Frutos del Bosque S.A.",
            contacto="Lucía Fernández",
            telefono="11-5522-3311",
            email="info@frutosdelbosque.com",
            direccion="Calle 12 N° 450, La Plata"
        )
        bd.session.add_all([p1, p2, p3])
        bd.session.commit()

    # 3. Productos representativos del SRS (cubriendo estados NORMAL, STOCK_BAJO y AGOTADO)
    if not Producto.query.first():
        p_sur = Proveedor.query.filter_by(nombre="Distribuidora Natural Sur").first()
        p_molino = Proveedor.query.filter_by(nombre="Molinos del Valle").first()
        p_frutos = Proveedor.query.filter_by(nombre="Frutos del Bosque S.A.").first()

        productos_semilla = [
            Producto("Avena Arrollada Gruesa", "Cereales", 35.0, "kg", 2200.0, 6.0, p_molino.id_proveedor if p_molino else None),
            Producto("Lentejas Pardinas Seleccionadas", "Legumbres", 18.0, "kg", 3100.0, 3.5, p_sur.id_proveedor if p_sur else None),
            Producto("Semillas de Chía Agroecológicas", "Semillas", 3.5, "kg", 4500.0, 2.0, p_sur.id_proveedor if p_sur else None), # STOCK_BAJO
            Producto("Nuez Mariposa Extra Blanca", "Frutos Secos", 0.0, "kg", 9800.0, 4.0, p_frutos.id_proveedor if p_frutos else None), # AGOTADO
            Producto("Almendras Non Pareil", "Frutos Secos", 12.0, "kg", 11200.0, 3.0, p_frutos.id_proveedor if p_frutos else None),
            Producto("Aceite de Coco Neutro Prensado en Frío", "Aceites", 14.0, "u", 6500.0, 2.0, p_sur.id_proveedor if p_sur else None),
            Producto("Té Verde en Hebras Sencha", "Infusiones", 2.0, "kg", 7800.0, 1.5, p_sur.id_proveedor if p_sur else None), # STOCK_BAJO
            Producto("Harina de Almendras Pura", "Cereales", 8.5, "kg", 8900.0, 2.5, p_frutos.id_proveedor if p_frutos else None)
        ]
        bd.session.add_all(productos_semilla)
        bd.session.commit()
