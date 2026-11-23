# Dietética Natural — Sistema de Control de Inventario y Predicción de Demanda

**Materia:** Análisis y Metodología de Sistemas (S0D41)  
**Institución:** Escuela Da Vinci — Carrera de Analista de Sistemas  
**Docente:** Lic. Diego Simonelli  
**Entrega:** Segundo Parcial — MVP Funcional  
**Alumnos:** Ricardo Gabriel Díaz (Legajo 29135452) y Benítez  
**Aplicación en Producción (Render):** [https://dietetica-natural-mvp.onrender.com](https://dietetica-natural-mvp.onrender.com)  
**Repositorio Oficial:** [https://github.com/rgabrieldiaz/dietetica-natural](https://github.com/rgabrieldiaz/dietetica-natural)  

---

## 1. Descripción del Proyecto

Este proyecto constituye el MVP (Producto Mínimo Viable) desarrollado a partir de la Especificación de Requerimientos de Software (SRS) presentada y aprobada en el Primer Parcial para la **"Gestión de Inventario para Dietética de Barrio"**.

El sistema resuelve la gestión integral de stock para una dietética, permitiendo controlar existencias físicas por peso/unidad, emitir alertas tempranas de reposición y calcular mediante un **modelo de Machine Learning (Regresión Lineal)** la cantidad de días de autonomía restantes para cada producto en función de su rotación de ventas.

### Cumplimiento de Reglas de Negocio del SRS:
- **RN-01 (Unicidad de Nombre):** No se permite registrar dos productos con el mismo nombre dentro de la misma categoría.
- **RN-02 (Stock Físico no Negativo):** El stock disponible no puede ser inferior a 0.
- **RN-03 (Precio Unitario Positivo):** El precio de venta debe ser estrictamente mayor a 0.
- **RN-04 (Integridad Referencial con Proveedores):** No se permite eliminar físicamente un proveedor si tiene productos asociados en el inventario.
- **RN-05 (Opcionalidad de Asociación):** Un producto puede darse de alta sin proveedor asignado inicialmente.
- **RN-06 (Semáforo de Alertas de Stock):**
  - `AGOTADO` (Badge rojo): Stock actual $\le 0.0$.
  - `STOCK_BAJO` (Badge amarillo): $0.0 <$ Stock actual $\le 5.0$.
  - `NORMAL` (Badge verde): Stock actual $> 5.0$.

---

## 2. Arquitectura de Software

El sistema sigue el patrón **Application Factory** y arquitectura modular con **Blueprints** en Flask, estructurado de forma limpia y desacoplada para facilitar su mantenimiento y despliegue en la nube (Render / Gunicorn):

```text
dietetica-natural/
├── .env.example              # Plantilla de variables de entorno (SECRET_KEY, DATABASE_URL)
├── .gitignore                # Exclusiones de Git (entornos, logs, sqlite local)
├── render.yaml               # Infraestructura como Código (Blueprint de Render)
├── requirements.txt          # Dependencias exactas para reproducir el entorno
├── run.py                    # Punto de entrada para ejecución local y producción
├── train_model.py            # Script de entrenamiento y serialización Scikit-Learn
├── test_mvp.py               # Suite de 12 pruebas unitarias automatizadas (unittest)
├── README.md                 # Documentación técnica de entrega
└── src/
    ├── app.py                # Application Factory (create_app), extensiones, errores 404/500 y seed
    ├── models.py             # Modelos SQLAlchemy (Usuario, Proveedor, Producto) y reglas RN
    ├── auth/                 # Módulo de Autenticación (Flask-Login + Bcrypt)
    │   └── routes.py
    ├── inventario/           # Módulo CRUD de Productos y Proveedores (Web + API REST)
    │   └── routes.py
    ├── ia/                   # Módulo Predictivo (Joblib + Scikit-Learn)
    │   ├── modelo_dietetica.joblib
    │   └── routes.py
    ├── static/
    │   └── plots/            # Gráfico de recta de regresión generado con Matplotlib
    │       └── regresion_autonomia.png
    └── templates/            # Vistas Jinja2 estilizadas con Tailwind CSS
        ├── base.html
        ├── login.html
        ├── register.html
        ├── inventario.html
        ├── producto_form.html
        ├── proveedores.html
        ├── proveedor_form.html
        ├── prediccion.html
        └── 404.html          # Manejo de error de recurso no encontrado amigable
```

---

## 3. Modelo Predictivo de Inteligencia Artificial (Scikit-Learn + Joblib)

Siguiendo la consigna de cátedra (Punto 3) y lo desarrollado en las clases 20, 21 y 28:
- **Objetivo:** Calcular la estimación de días de autonomía que le quedan a un producto a granel antes de agotar existencias, cruzando el stock físico actual y la rotación semanal promedio de ventas.
- **Algoritmo utilizado:** `LinearRegression` de la librería `scikit-learn` (regresión lineal para predecir un valor numérico continuo).
- **Script de Entrenamiento (`train_model.py`):**
  - Genera y normaliza un conjunto de datos histórico de ventas y consumos semanales.
  - Ajusta el modelo de regresión lineal relacionando existencias vs. demanda.
  - Evalúa el ajuste del modelo ($R^2 \approx 0.82$, indicando un buen ajuste entre stock y rotación).
  - Genera un gráfico ilustrativo en `src/static/plots/regresion_autonomia.png` con `matplotlib` (`matplotlib.use("Agg")`).
  - Guarda el modelo entrenado mediante `joblib.dump()` en el archivo `src/ia/modelo_dietetica.joblib`.
- **Integración en la aplicación Flask:**
  - Al iniciar el servidor, Flask carga el modelo binario con `joblib.load()`.
  - Expone la ruta web `/ia/prediccion` (interfaz visual) y el endpoint API REST `/ia/api/predecir` (JSON) para obtener la predicción en tiempo real.
  - Si los días de autonomía calculados son menores a 7 días, el sistema clasifica la situación como alerta crítica de reposición y vincula directamente los datos de contacto del proveedor asignado para agilizar el pedido.

---

## 4. Instalación y Ejecución Local

### Paso 1: Clonar el repositorio
```bash
git clone https://github.com/rgabrieldiaz/dietetica-natural.git
cd dietetica-natural
```

### Paso 2: Crear y activar entorno virtual
```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# Linux / macOS
python3 -m venv .venv
source .venv/bin/activate
```

### Paso 3: Instalar dependencias
```bash
pip install -r requirements.txt
```

### Paso 4: Configurar variables de entorno
Copiar el archivo de ejemplo `.env.example` a `.env`:
```bash
# Windows PowerShell
Copy-Item .env.example .env

# Linux / macOS
cp .env.example .env
```
*(Si no se define `DATABASE_URL`, el sistema utilizará automáticamente SQLite local en `dietetica.db`)*.

### Paso 5: Entrenar el modelo (opcional, ya viene pre-entrenado)
```bash
python train_model.py
```

### Paso 6: Iniciar el servidor
```bash
python run.py
```
Abrir en el navegador: [http://localhost:5000](http://localhost:5000).

---

## 5. Credenciales de Acceso para Evaluación

Al iniciar la aplicación por primera vez, el sistema precarga automáticamente datos semilla (8 productos categorizados y 3 proveedores) junto a un usuario operador para facilitar la corrección inmediata:

- **Usuario:** `admin` (o `admin@dietetica.com`)
- **Contraseña:** `dietetica2026`

*(También es posible registrar nuevos operadores desde la pantalla de Registro)*.

---

## 6. Pruebas Automatizadas

El proyecto incluye una suite de 12 pruebas unitarias automatizadas con `unittest` que cubren desde el ciclo de autenticación hasta las reglas de negocio del SRS y los endpoints REST:

```bash
python test_mvp.py
```

### Detalle de Casos de Prueba Verificados:
1. `test_01_login_view`: Renderizado correcto de la pantalla de login (HTTP 200).
2. `test_02_login_valido`: Inicio de sesión exitoso con credenciales válidas del operador.
3. `test_03_login_invalido`: Rechazo de credenciales erróneas con mensaje de advertencia.
4. `test_04_acceso_protegido_sin_auth`: Redirección automática al login ante accesos no autenticados.
5. `test_05_crear_producto_y_reglas_de_negocio`: Cumplimiento estricto de RN-01 (unicidad), RN-02 (stock no negativo) y RN-03 (precio positivo).
6. `test_06_alerta_stock_rn06`: Clasificación precisa del semáforo de existencias (Normal, Stock Bajo, Agotado).
7. `test_07_inferencia_ia_web`: Inferencia del modelo y renderizado del diagnóstico en Jinja2.
8. `test_08_inferencia_ia_api_rest`: Endpoint JSON `/ia/api/predecir` con cálculo de autonomía y sugerencia de compra.
9. `test_09_integridad_proveedor_rn04`: RN-04 (bloqueo de eliminación de proveedores con mercadería asociada).
10. `test_10_opcionalidad_asociacion_rn05`: RN-05 (alta exitosa de producto sin proveedor vinculado).
11. `test_11_api_rest_crud_completo`: Operaciones CRUD completas vía REST JSON (`POST`, `GET`, `PUT`, `DELETE`).
12. `test_12_manejo_errores_404`: Respuestas amigables ante recursos inexistentes (HTML 404 en web, JSON 404 en API) y rechazo 401 en endpoints privados.

Resultado de la ejecución:
```text
Ran 12 tests in 1.71s
OK
```

---

## 7. Despliegue en Producción (Render)

La aplicación incluye el archivo `render.yaml` (Blueprint) y se encuentra desplegada y operativa en **Render**:

* **Web Service:** `dietetica-natural-mvp` (Python 3, Gunicorn)
* **Base de Datos:** `dietetica-postgres-db` (PostgreSQL 18 administrada)
* **Start Command:** `gunicorn run:app`
* **Manejo de Base de Datos:** El sistema detecta automáticamente la variable de entorno `DATABASE_URL` y resuelve la compatibilidad con el dialecto moderno de SQLAlchemy (`postgresql://`).

---

## 8. Endpoints API REST

Además de la interfaz web en Jinja2, se exponen endpoints JSON para evaluación de servicios:

| Método | Endpoint | Descripción | Autenticación |
|---|---|---|---|
| `POST` | `/auth/api/login` | Login y obtención de datos del usuario | No |
| `GET` | `/api/productos` | Listado completo de productos en JSON | Requerida |
| `GET` | `/api/productos/<id>` | Detalle de un producto específico | Requerida |
| `POST` | `/api/productos` | Alta de nuevo producto (valida RN-01, RN-02, RN-03, RN-05) | Requerida |
| `PUT` | `/api/productos/<id>` | Modificación de un producto existente | Requerida |
| `DELETE` | `/api/productos/<id>` | Eliminación de un producto por ID | Requerida |
| `GET` | `/api/proveedores` | Listado de proveedores registrados | Requerida |
| `POST` | `/api/proveedores` | Alta de nuevo proveedor | Requerida |
| `DELETE` | `/api/proveedores/<id>` | Eliminación de proveedor (protegido por RN-04) | Requerida |
| `POST` | `/ia/api/predecir` | Inferencia de días de autonomía y sugerencia de compra | Requerida |

### Ejemplo de Payload para `/ia/api/predecir`:
```json
{
  "stock_actual": 12.5,
  "rotacion_semanal": 3.0
}
```
### Respuesta:
```json
{
  "stock_actual": 12.5,
  "rotacion_semanal": 3.0,
  "dias_autonomia_predichos": 28.5,
  "urgencia": "ÓPTIMA",
  "mensaje": "Estado saludable: El stock actual cubre holgadamente la demanda proyectada.",
  "sugerencia_compra": 0.36
}
```
