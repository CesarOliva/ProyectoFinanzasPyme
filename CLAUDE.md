# CLAUDE.md — Plataforma de inteligencia financiera para tiendas pequeñas (México)

> Archivo de contexto para asistentes de IA (Claude Code, Cursor, etc.). Léelo completo antes de escribir código. Si algo aquí contradice una petición puntual, avisa antes de hacer el cambio.

## 1. Qué es este proyecto

Plataforma web que ayuda a **microempresas mexicanas que venden productos al consumidor final (B2C)** a entender su situación financiera sin ser contadores. El dueño sube sus Excel/CSV, el sistema los convierte a una base de datos SQL y le muestra un panel claro con estados financieros, gráficas, alertas y consejos generados con IA.

- **Contexto:** proyecto de curso (Full Stack con integración de IA). No es un prototipo desechable: debe estar bien estructurado, probado y presentable.
- **Inspiración de UX:** el panel de la central de vendedores de Mercado Libre: un panel unificado, con resumen arriba, menú lateral por módulos y avisos accionables ("tienes 3 productos con poco stock").
- **Usuario objetivo:** dueño de abarrotes, miscelánea, papelería, tienda de ropa local, frutería o farmacia independiente. Comercio al por menor (~45% de las microempresas en México, según INEGI). Solo negocios que **venden productos** (no servicios), porque su modelo de datos (ventas, costo, inventario) es el que soportamos.
- **Problema:** estos negocios no están bien administrados financieramente. No saben si ganan, en qué gastan ni cuánto comprar.

### Frase guía
> "¿Estoy ganando? ¿Qué producto me deja más? ¿Dónde gasto demasiado? ¿Me va a alcanzar el efectivo?"

Toda funcionalidad debe ayudar a responder una de estas preguntas en menos de 30 segundos.

## 2. Principios de diseño (no negociables)

1. **Lenguaje sencillo.** Nada de jerga contable en la interfaz. Di "Lo que ganaste" en vez de "Utilidad operativa" (puedes mostrar el término técnico en un tooltip).
2. **El código calcula, el LLM explica.** Todas las cifras (márgenes, proyecciones, punto de equilibrio) se calculan con código determinista (SQL/Python). El LLM solo recibe métricas ya calculadas y las redacta como alertas o consejos. **Nunca** dejes que el LLM haga aritmética ni invente cifras.
3. **Forecasting estadístico, no con LLM.** Las proyecciones usan modelos de series de tiempo (Prophet, ARIMA o Holt-Winters), no un prompt.
4. **Aislamiento por empresa.** Toda tabla de negocio lleva `id_empresa` y toda consulta filtra por él (ver §8).
5. **Los datos de entrada son sucios.** Los Excel de tienditas no tienen formato estándar. El pipeline de ingesta debe validar, avisar y permitir corregir; nunca fallar en silencio.
6. **Honestidad financiera.** Los consejos de la IA son orientativos, no asesoría financiera, contable ni fiscal. Incluir aviso visible. Lenguaje cuidadoso en temas de préstamos (ver §7).

## 3. Alcance por fases

### Fase 1 — MVP (lo que se construye ahora)

| Módulo | Contenido |
|---|---|
| Ingesta | Subir Excel/CSV, mapeo de columnas asistido por IA, validación, carga a SQL, historial de importaciones |
| Resumen | Tarjetas KPI: ventas, costo de ventas, utilidad bruta, gastos, utilidad, margen. Filtro por mes/trimestre/año |
| Finanzas | Estado de resultados simplificado, ingresos vs gastos por mes, utilidad mensual, distribución de gastos (dona), punto de equilibrio |
| Productos | Ventas, costo, utilidad y margen por producto; top 5 por utilidad; inventario con semáforo (🟢🟡🔴) |
| Flujo de efectivo | Entradas vs salidas, efectivo final y **proyección simple a 30 días** (línea base con promedio móvil; ver nota de fase 2) |
| Alertas | Reglas deterministas + texto redactado por LLM (ver §7) |

### Fase 2 — Se diseña para ella desde ahora, pero no se implementa completa

- **Forecasting estadístico** de ventas por producto/categoría y de compras, con puntos de reorden de inventario (Prophet / ARIMA / Holt-Winters).
- **Impuestos** (importante, pero fuera del MVP): cálculo de ISR/IVA según régimen (RESICO, Persona Física con Actividad Empresarial), utilidad neta después de impuestos.
- Consejos de IA más avanzados (precios, compras, financiamiento).
- Comparación de periodos, estacionalidad.

**Cómo dejar la puerta abierta en la fase 1 (obligatorio):**
- Vista SQL `v_ventas_diarias` (empresa, producto, fecha, unidades, ingreso, costo) lista para alimentar un modelo de series de tiempo.
- Interfaz `ForecastService` en el backend con una implementación base (promedio móvil) y la firma pensada para reemplazarla por Prophet/ARIMA sin tocar los endpoints.
- Endpoint `GET /empresas/{id}/forecast` ya definido y documentado, aunque devuelva la línea base.
- Campo `regimen_fiscal` en `empresas` (nullable) y columna/espacio para impuestos en el estado de resultados (valor 0 / "no calculado" en fase 1).

## 4. Stack

| Capa | Tecnología |
|---|---|
| Frontend | Next.js (React) + TypeScript, gráficas con Recharts |
| Backend | Python + FastAPI |
| Base de datos | PostgreSQL |
| Ingesta / ETL | pandas + openpyxl; LLM para mapear columnas |
| Forecasting | statsmodels / Prophet (fase 2); promedio móvil en fase 1 |
| IA | API de Claude para el parser de columnas y la redacción de alertas/consejos |
| Pruebas | pytest (backend), Vitest/Testing Library (frontend) |

Si necesitas agregar una dependencia relevante, justifícalo en una línea.

## 5. Modelo de datos (mínimo)

Todas las tablas de negocio incluyen `id_empresa` (FK a `empresas`). Montos en `NUMERIC(12,2)`, moneda MXN. Fechas en UTC o `DATE` según corresponda.

```
empresas ──┬── gastos_fijos
           ├── gastos_variables
           ├── productos_cat ──┐
           ├── historial_ventas ┘ (FK a productos_cat)
           └── importaciones
```

- **empresas:** `id_empresa` (PK), `nombre_negocio`, `giro`, `regimen_fiscal` (nullable, fase 2), `fecha_registro`.
- **gastos_fijos:** `id_gasto_fijo` (PK), `id_empresa`, `concepto`, `monto_mensual`, `dia_pago`. Renta, nómina base, servicios fijos, licencias.
- **gastos_variables:** `id_gasto_var` (PK), `id_empresa`, `fecha`, `concepto`, `monto`, `categoria`. Insumos, mantenimiento, fletes, comisiones.
- **productos_cat:** `id_producto` (PK), `id_empresa`, `sku_o_nombre`, `categoria`, `stock_actual`, `costo_promedio`, `precio_venta`.
- **historial_ventas:** `id_venta` (PK), `id_empresa`, `id_producto` (FK), `fecha_hora`, `cantidad_vendida`, `precio_unitario`, `costo_unitario`.
- **importaciones:** `id_importacion` (PK), `id_empresa`, `nombre_archivo`, `fecha`, `estado`, `filas_ok`, `filas_con_error`, `detalle_errores` (JSON). Sirve para trazabilidad y para deshacer cargas.

Índices mínimos: `(id_empresa, fecha_hora)` en ventas, `(id_empresa, fecha)` en gastos variables, `(id_empresa, id_producto)` en productos.

## 6. Pipeline de ingesta (Excel → SQL)

1. **Subida:** el usuario carga `.xlsx` / `.csv`.
2. **Profiling:** pandas lee el archivo y detecta columnas, tipos, filas vacías, formatos de fecha, texto en columnas numéricas.
3. **Mapeo asistido por IA:** el LLM propone a qué campo canónico corresponde cada columna (p. ej. "P. Unitario", "Precio", "Venta" → `precio_unitario`). Recibe **solo encabezados y una muestra pequeña de filas**, nunca el archivo completo. Devuelve JSON estricto.
4. **Confirmación del usuario:** se muestra el mapeo propuesto y el usuario lo acepta o corrige. No cargar nada sin confirmar.
5. **Limpieza y staging:** normalización de fechas, montos, duplicados; tabla de staging.
6. **Carga masiva** a las tablas finales dentro de una transacción. Si falla, rollback.
7. **Reporte:** filas cargadas, filas rechazadas y el porqué, registrado en `importaciones`.

Testing: probar con 3–5 formatos reales (o realistas) de tienditas/papelerías. Mantener esos archivos como fixtures en `tests/fixtures/`.

## 7. KPIs, reglas de alertas y consejos de IA

### Fórmulas (viven en código, con pruebas unitarias)
- Utilidad bruta = ventas − costo de ventas
- Utilidad = utilidad bruta − gastos de operación (fase 2: − impuestos)
- Margen = utilidad / ventas
- Margen por producto = (precio − costo) / precio
- Punto de equilibrio (en ventas) = gastos fijos / margen de contribución %, con margen de contribución % = (ventas − costos variables) / ventas
- Margen de seguridad = ventas actuales − punto de equilibrio
- Días de inventario = stock actual / ventas diarias promedio

### Alertas deterministas (umbrales configurables, no hardcodeados)
- 🔴 Margen neto bajo (p. ej. < 20%)
- 🔴 Producto con margen muy bajo (p. ej. < 10%)
- 🔴 Inventario bajo / producto por agotarse
- 🟡 Gastos crecen más rápido que las ventas
- 🟡 Costo de mercancía subió y el precio de venta no
- 🟡 Caída de ventas frente al mes anterior
- 🔴 Flujo de efectivo proyectado negativo en 30 días
- 🟢 Buena rentabilidad / ventas creciendo (refuerzo positivo)

### Cómo participa el LLM
1. El código detecta la alerta y calcula las cifras.
2. El LLM recibe un JSON con las métricas ya calculadas y redacta un aviso breve, claro y accionable en español de México.
3. Debe usar **solo** las cifras del JSON. Si falta un dato, no lo inventa.

Ejemplos de tono:
- *Warning:* "Tu costo de mercancía subió 12% este mes pero tus precios siguen igual. Tu margen bajó a 18%."
- *Consejo:* "Eres rentable, pero tus compras te dejaron con poco efectivo. Puedes explorar un financiamiento de corto plazo para capital de trabajo; compara costos y plazos antes de decidir."

### Reglas para consejos sobre préstamos/financiamiento
- Presentar como **opción a evaluar**, nunca como instrucción ("consigue un préstamo").
- Basarse en datos reales: rentabilidad + flujo proyectado.
- No recomendar productos financieros ni instituciones concretas.
- Aviso visible: "Orientación general, no constituye asesoría financiera."

## 8. Seguridad y multi-empresa

- Autenticación de usuarios; cada usuario pertenece a una o más empresas.
- **Todas** las consultas filtran por `id_empresa` del usuario autenticado, resuelto en el backend (nunca confiar en un `id_empresa` enviado por el cliente sin verificar permiso).
- Valida tipo y tamaño de archivos subidos; no ejecutar contenido de las celdas (cuidado con fórmulas/inyección en CSV).
- Secretos (API keys, DB) en variables de entorno; nada en el repo.
- Al enviar datos al LLM, mandar el mínimo necesario (encabezados, muestras, métricas agregadas); no enviar datos personales innecesarios.
- Los datos financieros son sensibles: logs sin montos ni nombres de clientes.

## 9. Arquitectura y estructura sugerida

```
[ Next.js / React ]  ⇄ HTTPS ⇄  [ FastAPI ]
                                   ├─ ingestion/   (profiling, mapeo IA, limpieza, carga)
                                   ├─ finance/     (KPIs, estado de resultados, punto de equilibrio)
                                   ├─ forecasting/ (ForecastService: baseline → Prophet/ARIMA)
                                   ├─ alerts/      (reglas deterministas + redacción con LLM)
                                   └─ db/          (modelos, migraciones, vistas)
                                        └─ PostgreSQL
```

```
/frontend   app/ (rutas por módulo), components/, lib/api.ts
/backend    app/{ingestion,finance,forecasting,alerts,db,api}, tests/
/docs       decisiones.md, esquema.md
```

## 10. Convenciones de código

- Código y nombres de tablas/columnas en **español** para el dominio (como en §5); términos técnicos estándar en inglés.
- Tipado estricto (TypeScript, type hints en Python, Pydantic para validar entradas/salidas).
- Lógica financiera en funciones puras y testeables, separadas de los endpoints.
- Migraciones versionadas (Alembic) para cualquier cambio de esquema.
- Mensajes de error pensados para el usuario final, en lenguaje simple.
- Commits pequeños y descriptivos.

## 11. UX y diseño

- Estilo de panel tipo central de vendedores: **menú lateral** con los módulos (Resumen, Finanzas, Productos, Análisis, Alertas), **tarjetas KPI arriba**, gráficas debajo, alertas visibles.
- Gráficas: línea para tendencias (ventas, utilidad), barras para ingresos vs gastos y top productos, dona solo para composiciones simples (distribución de gastos).
- Semáforo consistente: 🟢 bien, 🟡 atención, 🔴 acción.
- Responsive (el dueño de una tienda probablemente use el celular).
- Estados vacíos claros ("Sube tu primer Excel para empezar") y estados de carga/error.
- Accesibilidad básica: contraste, no depender solo del color, textos alternativos.

## 12. Datos de ejemplo para desarrollo y demo

Caso base (enero–septiembre 2026, MXN): ventas $170,000 · costo de ventas $75,000 · utilidad bruta $95,000 · gastos de operación $30,000 · utilidad antes de impuestos $65,000 · margen 38.2%. Sin otros ingresos/gastos.

Generar un dataset sintético coherente con estas cifras (productos, ventas diarias, gastos fijos/variables) para seeds, pruebas y demo. Incluir al menos un producto con margen bajo, uno con stock crítico y un mes con caída de ventas para que las alertas se puedan mostrar.

## 13. Criterios de calidad (proyecto de curso)

Se considera terminado cuando:
- [ ] Un usuario nuevo puede registrarse, subir un Excel de ejemplo, confirmar el mapeo y ver su dashboard.
- [ ] Las fórmulas de §7 tienen pruebas unitarias y los totales cuadran con el caso base de §12.
- [ ] Hay al menos 3 formatos de Excel distintos probados en el pipeline de ingesta.
- [ ] Las alertas se generan con cifras del código y el LLM nunca calcula.
- [ ] Un usuario no puede ver datos de otra empresa (prueba automatizada).
- [ ] README con instalación, variables de entorno y cómo correr seeds y pruebas.
- [ ] Demo estable con datos sintéticos.

## 14. Fuera de alcance (por ahora)

- Empresas de servicios y B2B (el modelo de datos asume productos con costo y stock).
- Facturación electrónica / integración con el SAT.
- Contabilidad formal (balance general, pólizas).
- Integraciones directas con punto de venta o marketplaces (posible idea futura).

## 15. Notas e ideas futuras

> Espacio vivo: agrega aquí ideas sin comprometerte a implementarlas.

- **Impuestos (prioridad alta en fase 2):** ISR e IVA por régimen, calendario de pagos, utilidad neta real, alerta de provisión de impuestos.
- **Forecasting:** demanda por producto/categoría, estacionalidad (Día de Muertos, regreso a clases, temporada navideña), puntos de reorden, sugerencia de cuánto comprar.
- **Liquidez a 30/60/90 días** con escenarios (optimista/base/pesimista) y colchón recomendado de capital de trabajo.
- **Consejos de precios:** detectar productos donde conviene subir el precio según margen y rotación.
- **Integración con Mercado Libre u otros marketplaces** para importar ventas automáticamente (la inspiración de UX podría volverse fuente de datos).
- **Importar desde fotos o PDF** de notas de venta/tickets (aprovechando la parte multimodal).
- **Asistente conversacional:** el dueño pregunta "¿cuánto gané en agosto?" y la IA responde con consultas SQL seguras.
- **Modelo de negocio:** freemium vs suscripción mensual; estimar costo de IA por usuario.
- **Notificaciones** por correo/WhatsApp con el resumen semanal.
- **Benchmarks** anónimos entre negocios del mismo giro.

## 16. Cómo trabajar conmigo (instrucciones para la IA)

- Antes de un cambio grande, resume el plan en pocas líneas y espera confirmación.
- Si una petición viola un principio de §2 (p. ej. dejar que el LLM calcule), señálalo y propón la alternativa.
- Prefiere soluciones simples que cumplan el MVP; deja ganchos para la fase 2, no la implementes sin pedirlo.
- Explica brevemente las decisiones técnicas importantes: es un proyecto de aprendizaje.
- Si falta información (un formato de Excel, un umbral, una decisión de producto), pregunta en vez de asumir.
