# Guía del proyecto Cuentas Claras

Esta guía sirve para ejecutar el proyecto y ubicar rápidamente el código. El repositorio está dentro de `ProyectoFinanzasPyme/`.

## Qué hace

Aplicación web para consultar las finanzas de pequeños negocios. El frontend muestra resúmenes, finanzas, productos, flujo de efectivo, alertas, importación de Excel/CSV y un asistente. El backend calcula las cifras y las expone mediante una API. Ollama es opcional y se usa para redactar explicaciones; la aplicación puede funcionar con textos de plantilla.

## Requisitos

- Python 3.12 o superior.
- Node.js 20 o superior y npm.
- MySQL 8 ejecutándose localmente.
- Ollama y `llama3.2:3b` (opcionales).

## Cómo ejecutarlo en Windows / PowerShell

Abre dos terminales en la carpeta `ProyectoFinanzasPyme`. La primera ejecuta el backend y la segunda el frontend.

### 1. Preparar la base de datos

Importa `database/cuentas_claras.sql` desde MySQL Workbench (`File > Open SQL Script`, luego ejecutar). Este archivo crea la base y carga datos de demostración. Para arrancar sin datos, usa `database/schema.sql`.

### 2. Preparar y arrancar el backend

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Edita `backend/.env`: configura `DATABASE_URL` con el usuario, contraseña y base MySQL, y cambia `JWT_SECRET` por un valor aleatorio. Después, desde `backend/`:

```powershell
uvicorn app.main:app --reload --port 8000
```

La API queda en `http://localhost:8000`; su documentación interactiva está en `http://localhost:8000/docs` y el chequeo de salud en `http://localhost:8000/api/salud`.

Si cargaste `cuentas_claras.sql`, las tablas ya existen. Si creaste una base vacía compatible con las migraciones, usa `alembic upgrade head` desde `backend/`.

### 3. Preparar y arrancar el frontend

En la segunda terminal, desde `ProyectoFinanzasPyme/`:

```powershell
cd frontend
npm install
npm run dev
```

Abre `http://localhost:5173`. Vite reenvía las peticiones `/api` al backend en el puerto 8000 (`frontend/vite.config.ts`), por lo que ambos procesos deben estar activos.

### Ollama (opcional)

Instala e inicia Ollama y descarga el modelo con `ollama pull llama3.2:3b`. La URL, modelo y tiempo de espera se configuran en `backend/.env`. Si Ollama no está disponible, se usan respuestas de plantilla.

### Accesos de demostración

La contraseña compartida es `Demo2026!`. Cuentas: `ana.ruiz@example.com`, `lupita.martinez@example.com`, `sofia.herrera@example.com` y `carlos.mendez@example.com`. La pantalla de acceso también ofrece botones rápidos. Consulta el README para el negocio que corresponde a cada cuenta.

## Mapa de carpetas

```text
ProyectoFinanzasPyme/
├── backend/                         # API y lógica de negocio Python
│   ├── app/
│   │   ├── main.py                  # Crea FastAPI, registra rutas y /api/salud
│   │   ├── config.py                # Variables de entorno y valores por defecto
│   │   ├── api/                     # Endpoints, dependencias y seguridad JWT
│   │   │   ├── rutas_auth.py        # Registro e inicio de sesión
│   │   │   ├── rutas_empresas.py    # Resumen, finanzas, productos, flujo y alertas
│   │   │   ├── rutas_chat.py        # Asistente y respuestas de chat
│   │   │   ├── rutas_ingesta.py     # Análisis, vista previa y confirmación de cargas
│   │   │   ├── deps.py              # Dependencias compartidas de las rutas
│   │   │   └── seguridad.py         # Validación de sesión y permisos
│   │   ├── db/                      # Tablas SQLAlchemy y conexión/transacciones
│   │   │   ├── models.py            # Fuente única del esquema de datos
│   │   │   └── session.py           # Motor y sesiones de base de datos
│   │   ├── finance/                 # Consultas, fórmulas, periodos y KPIs
│   │   ├── forecasting/             # Pronósticos financieros
│   │   ├── alerts/                  # Reglas de alertas y redacción
│   │   ├── chat/                    # Intenciones, hechos calculados y asistente
│   │   ├── ingestion/               # Lectura, limpieza, mapeo y carga Excel/CSV
│   │   └── llm/                     # Cliente Ollama y guardia de cifras
│   ├── alembic/                     # Configuración y versiones de migraciones
│   ├── scripts/generar_seed.py      # Genera SQL y datos demostrativos
│   ├── tests/                       # Pruebas del backend y archivos de ejemplo
│   ├── requirements.txt             # Dependencias Python
│   └── .env.example                 # Plantilla de configuración local
├── frontend/                        # Aplicación React + TypeScript + Vite
│   ├── src/
│   │   ├── main.tsx                 # Punto de entrada React
│   │   ├── App.tsx                  # Rutas y composición general
│   │   ├── pages/                   # Pantallas: Resumen, Finanzas, Flujo, etc.
│   │   ├── components/              # Elementos reutilizables, layout y gráficas
│   │   ├── context/                 # Estado compartido: sesión, periodo, chat
│   │   ├── hooks/                   # Hooks, incluido el acceso a la API
│   │   ├── lib/                     # Cliente API, tipos, formatos, periodos y voz
│   │   ├── styles/                  # Estilos globales, layout y pantallas
│   │   └── test/                    # Pruebas de frontend
│   ├── package.json                 # Comandos y dependencias npm
│   └── vite.config.ts               # Vite, proxy /api y configuración Vitest
├── database/
│   ├── schema.sql                   # SQL del esquema, sin datos demostrativos
│   └── cuentas_claras.sql           # Esquema más datos demostrativos
├── docs/
│   ├── decisiones.md                # Decisiones técnicas y sus motivos
│   └── esquema.md                   # Relaciones y descripción de tablas
├── README.md                        # Instrucciones originales y detalles funcionales
└── GUIA_PROYECTO.md                 # Esta guía
```

## Por dónde empezar a buscar

| Si quieres cambiar… | Empieza en… |
|---|---|
| Una pantalla | `frontend/src/pages/` |
| Navegación, sesión o diseño general | `frontend/src/App.tsx`, `frontend/src/context/` y `frontend/src/components/layout/` |
| Una gráfica o elemento reutilizable | `frontend/src/components/` |
| Llamadas del frontend al servidor | `frontend/src/lib/api.ts` y `frontend/src/hooks/useApi.ts` |
| Un endpoint o permisos | `backend/app/api/` |
| Una fórmula o KPI | `backend/app/finance/` |
| Reglas de alertas | `backend/app/alerts/` |
| El asistente | `backend/app/chat/`; para el modelo y filtrado numérico, `backend/app/llm/` |
| Importación Excel/CSV | `backend/app/ingestion/` y `backend/app/api/rutas_ingesta.py` |
| Tablas o conexión a BD | `backend/app/db/` |
| Datos de demostración | `backend/scripts/generar_seed.py` y `database/` |

## Ramas Git

Las referencias locales presentes en `.git/refs/heads/` son:

```text
main
└── feature/plataforma-mvp
```

El nombre `feature/plataforma-mvp` describe una rama de trabajo para la plataforma MVP; Git no guarda una explicación funcional de la rama. Para ver la rama activa y su estado, ejecuta `git status -sb` desde `ProyectoFinanzasPyme/`. Para listar ramas locales y remotas: `git branch -a`.

## Comandos útiles

```powershell
# Backend (desde backend/):
pytest

# Frontend (desde frontend/):
npm test
npm run build
```

Las pruebas del backend usan SQLite en memoria; no requieren MySQL ni Ollama. Para más detalle de endpoints, cuentas de demostración y formatos de importación, revisa `README.md`.
