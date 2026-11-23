from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

bd = SQLAlchemy()

# Categorías oficiales definidas en el SRS de la Dietética (Parcial 1)
CATEGORIAS_VALIDAS = [
    "Cereales",
    "Legumbres",
    "Semillas",
    "Aceites",
    "Infusiones",
    "Frutos Secos"
]

UNIDADES_VALIDAS = ["kg", "g", "l", "u"]

class Usuario(bd.Model, UserMixin):
    __tablename__ = "usuarios"

    id = bd.Column(bd.Integer, primary_key=True)
    username = bd.Column(bd.String(80), unique=True, nullable=False)
    email = bd.Column(bd.String(120), unique=True, nullable=False)
    password_hash = bd.Column(bd.String(255), nullable=False)

    def __init__(self, username, email, password_hash):
        self.username = username
        self.email = email
        self.password_hash = password_hash

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email
        }


class Proveedor(bd.Model):
    __tablename__ = "proveedores"

    id_proveedor = bd.Column(bd.Integer, primary_key=True)
    nombre = bd.Column(bd.String(120), nullable=False)
    contacto = bd.Column(bd.String(100), nullable=True)
    telefono = bd.Column(bd.String(50), nullable=True)
    email = bd.Column(bd.String(120), nullable=True)
    direccion = bd.Column(bd.String(200), nullable=True)

    # Relación uno-a-muchos con Producto
    productos = bd.relationship("Producto", backref="proveedor", lazy=True)

    def __init__(self, nombre, contacto=None, telefono=None, email=None, direccion=None):
        self.nombre = nombre
        self.contacto = contacto
        self.telefono = telefono
        self.email = email
        self.direccion = direccion

    def to_dict(self):
        return {
            "id_proveedor": self.id_proveedor,
            "nombre": self.nombre,
            "contacto": self.contacto,
            "telefono": self.telefono,
            "email": self.email,
            "direccion": self.direccion,
            "cantidad_productos": len(self.productos) if self.productos else 0
        }


class Producto(bd.Model):
    __tablename__ = "productos"

    id_producto = bd.Column(bd.Integer, primary_key=True)
    nombre = bd.Column(bd.String(120), nullable=False)
    categoria = bd.Column(bd.String(50), nullable=False)
    stock_actual = bd.Column(bd.Float, nullable=False, default=0.0)
    unidad_medida = bd.Column(bd.String(20), nullable=False, default="kg")
    precio_unitario = bd.Column(bd.Float, nullable=False, default=0.0)
    rotacion_semanal_estimada = bd.Column(bd.Float, nullable=False, default=2.5)
    id_proveedor = bd.Column(bd.Integer, bd.ForeignKey("proveedores.id_proveedor"), nullable=True)

    def __init__(self, nombre, categoria, stock_actual, unidad_medida, precio_unitario,
                 rotacion_semanal_estimada=2.5, id_proveedor=None):
        self.nombre = nombre
        self.categoria = categoria
        self.stock_actual = max(0.0, float(stock_actual))
        self.unidad_medida = unidad_medida
        self.precio_unitario = max(0.01, float(precio_unitario))
        self.rotacion_semanal_estimada = max(0.1, float(rotacion_semanal_estimada))
        self.id_proveedor = id_proveedor

    @property
    def estado_stock(self):
        """
        Regla de Negocio RN-06 (SRS Parcial 1):
        - Stock <= 0.0 -> AGOTADO
        - 0.0 < Stock <= 5.0 -> STOCK_BAJO
        - Stock > 5.0 -> NORMAL
        """
        if self.stock_actual <= 0.0:
            return "AGOTADO"
        elif self.stock_actual <= 5.0:
            return "STOCK_BAJO"
        return "NORMAL"

    @property
    def badge_color(self):
        estado = self.estado_stock
        if estado == "AGOTADO":
            return "bg-red-100 text-red-800 border-red-300"
        elif estado == "STOCK_BAJO":
            return "bg-amber-100 text-amber-800 border-amber-300"
        return "bg-emerald-100 text-emerald-800 border-emerald-300"

    def to_dict(self):
        return {
            "id_producto": self.id_producto,
            "nombre": self.nombre,
            "categoria": self.categoria,
            "stock_actual": self.stock_actual,
            "unidad_medida": self.unidad_medida,
            "precio_unitario": self.precio_unitario,
            "rotacion_semanal_estimada": self.rotacion_semanal_estimada,
            "estado_stock": self.estado_stock,
            "id_proveedor": self.id_proveedor,
            "proveedor_nombre": self.proveedor.nombre if self.proveedor else None
        }
