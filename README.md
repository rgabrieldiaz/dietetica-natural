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

Este proyecto constituye el MVP (Producto Mínimo Viable) desarrollado a partir de la Especificación de Requerimientos de Software (SRS) presentada y aprobada en el Primer Parcial.

El sistema resuelve la gestión integral de stock para una **Dietética de Barrio**, permitiendo controlar existencias físicas por peso/unidad, emitir alertas tempranas de reposición y calcular mediante un **modelo de Machine Learning (Regresión Lineal)** la cantidad de días de autonomía restantes para cada producto en función de su rotación de ventas.

### Cumplimiento de Reglas de Negocio del SRS:
- **RN-01 (Unicidad):** No se permite duplicar el nombre de un producto dentro de la misma categoría.
- **RN-02 (Stock Físico no Negativo):** El stock disponible no puede ser inferior a 0.
- **RN-03 (Precio Positivo):** El precio unitario debe ser estrictamente mayor a 0.
- **RN-06 (Semáforo de Alertas de Stock):**
  - `AGOTADO` (Badge rojo): Stock actual $\le 0.0$.
  - `STOCK_BAJO` (Badge amarillo): $0.0 <$ Stock actual $\le 5.0$.
  - `NORMAL` (Badge verde): Stock actual $> 5.0$.

---

## 2. Arquitectura de Software

El sistema sigue el patrón **Application Factory** y arquitectura modular con **Blueprints** en Flask, garantizando separación de responsabilidades y compatibilidad con entornos Cloud (Render / Gunicorn):

```text
parcial-2-mvp/
├── .env.example              # Plantilla de variables de entorno
├── .gitignore                # Exclusiones de Git (entornos, logs, db)
├── requirements.txt          # Dependencias exactas del proyecto
├── run.py                    # Entry point para ejecución local y producción
├── train_model.py            # Pipeline de entrenamiento y exportación Scikit-Learn
├── test_mvp.py               # Suite de 8 pruebas unitarias y de integración
├── README.md                 # Documentación completa de entrega
└── src/
    ├── app.py                # Application Factory (create_app), extensiones y seed inicial
    ├── models.py             # Modelos de base de datos SQLAlchemy y reglas de negocio
    ├── auth/                 # Módulo de Autenticación (Flask-Login + Bcrypt)
    │   └── routes.py
    ├── inventario/           # Módulo CRUD de Productos y Proveedores
    │   └── routes.py
    ├── ia/                   # Módulo Predictivo (Joblib + Scikit-Learn)
    │   ├── modelo_dietetica.joblib
    │   └── routes.py
    ├── static/
    │   └── plots/            # Gráficos analíticos generados por Matplotlib
    │       ├── regresion_autonomia.png
    │       └── residuos_modelo.png
    └── templates/            # Vistas Jinja2 estilizadas con Tailwind CSS
        ├── base.html
        ├── login.html
        ├── register.html
        ├── inventario.html
        ├── producto_form.html
        ├── proveedores.html
        ├── proveedor_form.html
        └── prediccion.html
```

---

## 3. Modelo de Machine Learning Incorporado

- **Objetivo de Negocio:** Predecir cuántos días de abastecimiento le quedan a la dietética antes de agotar un insumo a granel, considerando las ventas promedio semanales y el stock físico disponible.
- **Algoritmo:** `LinearRegression` (Scikit-Learn).
- **Entrenamiento:** Pipeline desarrollado en `train_model.py`.
- **Métricas de Evaluación:**
  - **$R^2$ Score:** `0.8201` (82% de varianza explicada).
  - **MAE (Error Absoluto Medio):** `8.59 días`.
  - **MSE (Error Cuadrático Medio):** `134.01`.
- **Serialización:** Exportado como binario portable en `src/ia/modelo_dietetica.joblib`.
- **Visualizaciones generadas:**
  - `regresion_autonomia.png`: Gráfico de dispersión comparando valores observados vs. recta de predicción ideal.
  - `residuos_modelo.png`: Histograma de distribución de residuos para verificación de normalidad del error.

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

Al iniciar la aplicación por primera vez, el sistema precarga automáticamente datos semilla y un usuario operador para facilitar la corrección:

- **Usuario:** `admin` (o `admin@dietetica.com`)
- **Contraseña:** `dietetica2026`

*(También es posible registrar nuevos operadores desde la pantalla de Registro)*.

---

## 6. Pruebas Automatizadas

El proyecto incluye una suite de pruebas automatizadas con `unittest` que verifica autenticación, validación de reglas de negocio RN-01 a RN-06 e inferencia del modelo predictivo:

```bash
python test_mvp.py
```
Resultado esperado:
```text
Ran 8 tests in 0.95s
OK
```

---

## 7. Despliegue en Producción (Render)

La aplicación incluye el archivo `render.yaml` (Infrastructure as Code) y está preparada para despliegue inmediato en **Render**:

### Opción A: Despliegue Automático con Blueprint (Recomendado)
1. En el Dashboard de [Render](https://dashboard.render.com), hacer clic en **New +** y seleccionar **Blueprint**.
2. Conectar el repositorio `https://github.com/rgabrieldiaz/dietetica-natural`.
3. Render detectará automáticamente `render.yaml` y creará la base de datos PostgreSQL (`dietetica-postgres-db`) y el Web Service (`dietetica-natural-mvp`) vinculados entre sí.

### Opción B: Despliegue Manual como Web Service
- **Build Command:** `pip install -r requirements.txt && python train_model.py`
- **Start Command:** `gunicorn run:app`
- **Variables de Entorno en Render:**
  - `SECRET_KEY`: Cadena aleatoria segura (ej. `dietetica_prod_secreto_2026`).
  - `DATABASE_URL`: Conexión a la base PostgreSQL interna o externa (el sistema convierte automáticamente `postgres://` a `postgresql://` para compatibilidad con SQLAlchemy 2.x). Si se omite, funcionará con SQLite local.

---

## 8. Endpoints API REST

Además de la interfaz web en Jinja2, se exponen endpoints JSON para evaluación de servicios:

| Método | Endpoint | Descripción | Autenticación |
|---|---|---|---|
| `POST` | `/auth/api/login` | Login y obtención de datos del usuario | No |
| `GET` | `/api/productos` | Listado completo de productos en formato JSON | Requerida |
| `GET` | `/api/productos/<id>` | Detalle de un producto por ID | Requerida |
| `GET` | `/api/proveedores` | Listado de proveedores registrados | Requerida |
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
