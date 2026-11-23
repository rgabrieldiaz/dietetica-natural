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

    def test_09_integridad_proveedor_rn04(self):
        """Verifica que RN-04 impida eliminar un proveedor con productos vinculados"""
        self.client.post("/auth/login", data={"username_or_email": "admin", "password": "dietetica2026"})
        with app.app_context():
            prov = Proveedor.query.filter(Proveedor.productos.any()).first()
            self.assertIsNotNone(prov, "Debe existir al menos un proveedor con productos")
            prov_id = prov.id_proveedor

        response = self.client.post(f"/proveedores/eliminar/{prov_id}", follow_redirects=True)
        self.assertIn(b"RN-04", response.data)

        # Comprobar que no se haya borrado de la base de datos
        with app.app_context():
            prov_check = bd.session.get(Proveedor, prov_id)
            self.assertIsNotNone(prov_check)

    def test_10_opcionalidad_asociacion_rn05(self):
        """Verifica que RN-05 permita dar de alta un producto sin proveedor asignado"""
        self.client.post("/auth/login", data={"username_or_email": "admin", "password": "dietetica2026"})
        resp = self.client.post("/inventario/nuevo", data={
            "nombre": "Mijo Pelado Nacional",
            "categoria": "Cereales",
            "stock_actual": "12.0",
            "unidad_medida": "kg",
            "precio_unitario": "1800.0",
            "rotacion_semanal_estimada": "2.0",
            "id_proveedor": ""
        }, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        with app.app_context():
            p = Producto.query.filter_by(nombre="Mijo Pelado Nacional").first()
            self.assertIsNotNone(p)
            self.assertIsNone(p.id_proveedor, "El producto debe persistirse con id_proveedor = None según RN-05")

    def test_11_api_rest_crud_completo(self):
        """Verifica el CRUD completo vía REST JSON (Clase 17: GET, POST, PUT, DELETE)"""
        self.client.post("/auth/login", data={"username_or_email": "admin", "password": "dietetica2026"})
        
        # 1. POST /api/productos (crear)
        resp_post = self.client.post("/api/productos", json={
            "nombre": "Sésamo Negro Integral",
            "categoria": "Semillas",
            "stock_actual": 8.0,
            "unidad_medida": "kg",
            "precio_unitario": 3900.0,
            "rotacion_semanal_estimada": 1.5
        })
        self.assertEqual(resp_post.status_code, 201)
        prod_data = resp_post.get_json()
        nuevo_id = prod_data["id_producto"]

        # 2. GET /api/productos/<id> (detalle)
        resp_get = self.client.get(f"/api/productos/{nuevo_id}")
        self.assertEqual(resp_get.status_code, 200)
        self.assertEqual(resp_get.get_json()["nombre"], "Sésamo Negro Integral")

        # 3. PUT /api/productos/<id> (actualizar)
        resp_put = self.client.put(f"/api/productos/{nuevo_id}", json={
            "nombre": "Sésamo Negro Tostado",
            "precio_unitario": 4100.0
        })
        self.assertEqual(resp_put.status_code, 200)
        self.assertEqual(resp_put.get_json()["nombre"], "Sésamo Negro Tostado")

        # 4. DELETE /api/productos/<id> (eliminar)
        resp_del = self.client.delete(f"/api/productos/{nuevo_id}")
        self.assertEqual(resp_del.status_code, 200)
        with app.app_context():
            self.assertIsNone(bd.session.get(Producto, nuevo_id))

    def test_12_manejo_errores_404(self):
        """Verifica que rutas o recursos inexistentes devuelvan 404 limpio en HTML y JSON, y 401 sin sesión"""
        # 1. HTML 404 para ruta web inexistente
        resp_web = self.client.get("/ruta-que-no-existe-en-la-app")
        self.assertEqual(resp_web.status_code, 404)
        self.assertIn(b"Recurso No Encontrado", resp_web.data)

        # 2. JSON 404 para ruta de API no registrada en el servidor
        resp_api_inexistente = self.client.get("/api/ruta_que_no_existe_en_ningun_lado")
        self.assertEqual(resp_api_inexistente.status_code, 404)
        self.assertIn("error", resp_api_inexistente.get_json())

        # 3. API 401 si no hay sesión iniciada al acceder a un endpoint protegido
        resp_unauth = self.client.get("/api/productos/99999")
        self.assertEqual(resp_unauth.status_code, 401)
        self.assertIn("error", resp_unauth.get_json())

        # 4. JSON 404 autenticado para recurso con ID inexistente en la BD
        self.client.post("/auth/login", data={"username_or_email": "admin", "password": "dietetica2026"})
        resp_api = self.client.get("/api/productos/99999")
        self.assertEqual(resp_api.status_code, 404)
        self.assertIn("error", resp_api.get_json())


if __name__ == "__main__":
    unittest.main()
