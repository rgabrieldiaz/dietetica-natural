"""
Suite de Pruebas Automatizadas para el MVP del Parcial 2
Verifica la funcionalidad completa: Auth, Inventario, Reglas de Negocio (RN-01 a RN-06) e Inferencia IA.
"""

import unittest
from run import app
from src.models import bd, Usuario, Producto, Proveedor

class DieteticaMVPTestCase(unittest.TestCase):

    def setUp(self):
        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False
        self.client = app.test_client()

    def test_01_login_view(self):
        """Verifica que la pantalla de login responda correctamente (HTTP 200)"""
        response = self.client.get("/auth/login")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Acceso al Sistema", response.data)

    def test_02_login_valido(self):
        """Verifica login con credenciales válidas del usuario admin"""
        response = self.client.post("/auth/login", data={
            "username_or_email": "admin",
            "password": "dietetica2026"
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Control de Stock e Inventario", response.data)

    def test_03_login_invalido(self):
        """Verifica rechazo de credenciales incorrectas"""
        response = self.client.post("/auth/login", data={
            "username_or_email": "admin",
            "password": "clave_incorrecta"
        }, follow_redirects=True)
        self.assertIn(b"Credenciales incorrectas", response.data)

    def test_04_acceso_protegido_sin_auth(self):
        """Verifica que rutas protegidas redirijan al login si no hay sesión activa"""
        response = self.client.get("/inventario", follow_redirects=False)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/auth/login", response.location)

    def test_05_crear_producto_y_reglas_de_negocio(self):
        """Verifica el alta de productos y la aplicación de RN-01, RN-02 y RN-03"""
        # Iniciar sesión primero
        self.client.post("/auth/login", data={"username_or_email": "admin", "password": "dietetica2026"})

        # 1. Alta válida
        resp_alta = self.client.post("/inventario/nuevo", data={
            "nombre": "Quinoa Real Roja",
            "categoria": "Semillas",
            "stock_actual": "15.0",
            "unidad_medida": "kg",
            "precio_unitario": "5200.0",
            "rotacion_semanal_estimada": "3.0"
        }, follow_redirects=True)
        self.assertEqual(resp_alta.status_code, 200)
        self.assertIn(b"Quinoa Real Roja", resp_alta.data)

        # 2. RN-01: Nombre duplicado en la misma categoría
        resp_dup = self.client.post("/inventario/nuevo", data={
            "nombre": "Quinoa Real Roja",
            "categoria": "Semillas",
            "stock_actual": "10.0",
            "unidad_medida": "kg",
            "precio_unitario": "5200.0",
            "rotacion_semanal_estimada": "3.0"
        }, follow_redirects=True)
        self.assertIn(b"RN-01", resp_dup.data)

        # 3. RN-02: Stock negativo
        resp_neg = self.client.post("/inventario/nuevo", data={
            "nombre": "Producto Invalido Negativo",
            "categoria": "Cereales",
            "stock_actual": "-5.0",
            "unidad_medida": "kg",
            "precio_unitario": "1000.0",
            "rotacion_semanal_estimada": "2.0"
        }, follow_redirects=True)
        self.assertIn(b"RN-02", resp_neg.data)

        # 4. RN-03: Precio unitario <= 0
        resp_precio = self.client.post("/inventario/nuevo", data={
            "nombre": "Producto Invalido Precio",
            "categoria": "Cereales",
            "stock_actual": "10.0",
            "unidad_medida": "kg",
            "precio_unitario": "0",
            "rotacion_semanal_estimada": "2.0"
        }, follow_redirects=True)
        self.assertIn(b"RN-03", resp_precio.data)

    def test_06_alerta_stock_rn06(self):
        """Verifica la lógica de alerta según RN-06 (NORMAL, STOCK_BAJO, AGOTADO)"""
        with app.app_context():
            p_normal = Producto.query.filter_by(nombre="Avena Arrollada Gruesa").first()
            p_bajo = Producto.query.filter_by(nombre="Semillas de Chía Agroecológicas").first()
            p_agotado = Producto.query.filter_by(nombre="Nuez Mariposa Extra Blanca").first()

            self.assertEqual(p_normal.estado_stock, "NORMAL")
            self.assertEqual(p_bajo.estado_stock, "STOCK_BAJO")
            self.assertEqual(p_agotado.estado_stock, "AGOTADO")

    def test_07_inferencia_ia_web(self):
        """Verifica la predicción de días de autonomía en la vista web de IA"""
        self.client.post("/auth/login", data={"username_or_email": "admin", "password": "dietetica2026"})
        response = self.client.post("/ia/prediccion", data={
            "stock_actual": "10.0",
            "rotacion_semanal": "2.5"
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Resultado de Predicci", response.data)
        self.assertIn(b"Autonom", response.data)

    def test_08_inferencia_ia_api_rest(self):
        """Verifica el endpoint JSON /ia/api/predecir"""
        self.client.post("/auth/login", data={"username_or_email": "admin", "password": "dietetica2026"})
        response = self.client.post("/ia/api/predecir", json={
            "stock_actual": 20.0,
            "rotacion_semanal": 4.0
        })
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn("dias_autonomia_predichos", data)
        self.assertIn("urgencia", data)
        self.assertGreater(data["dias_autonomia_predichos"], 0)


if __name__ == "__main__":
    unittest.main()
