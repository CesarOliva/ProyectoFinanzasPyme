-- =====================================================================
-- Cuentas Claras · Plataforma de inteligencia financiera para tiendas
-- Esquema (sin datos)
-- Generado por backend/scripts/generar_seed.py (no editar a mano).
-- MySQL 8.0+.  Uso:  mysql -u root -p < database/schema.sql
-- =====================================================================

CREATE DATABASE IF NOT EXISTS cuentas_claras CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE cuentas_claras;

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;
DROP VIEW IF EXISTS v_ventas_diarias;
DROP TABLE IF EXISTS historial_ventas;
DROP TABLE IF EXISTS compras_producto;
DROP TABLE IF EXISTS productos_cat;
DROP TABLE IF EXISTS gastos_operativos;
DROP TABLE IF EXISTS usuarios_empresas;
DROP TABLE IF EXISTS importaciones;
DROP TABLE IF EXISTS usuarios;
DROP TABLE IF EXISTS empresas;
SET FOREIGN_KEY_CHECKS = 1;

CREATE TABLE empresas (
	id_empresa INTEGER NOT NULL AUTO_INCREMENT, 
	nombre_negocio VARCHAR(150) NOT NULL, 
	giro VARCHAR(80) NOT NULL, 
	ciudad VARCHAR(80), 
	regimen_fiscal VARCHAR(60) COMMENT 'Fase 2: RESICO, PFAE, etc.', 
	saldo_inicial NUMERIC(12, 2) NOT NULL COMMENT 'Efectivo al iniciar el registro' DEFAULT '0', 
	fecha_saldo_inicial DATE, 
	umbrales_alerta JSON COMMENT 'Sobrescribe los umbrales por defecto', 
	fecha_registro DATETIME NOT NULL DEFAULT (now()), 
	PRIMARY KEY (id_empresa)
)COMMENT='Negocios (tiendas) registrados' ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


CREATE TABLE usuarios (
	id_usuario INTEGER NOT NULL AUTO_INCREMENT, 
	nombre VARCHAR(120) NOT NULL, 
	email VARCHAR(160) NOT NULL, 
	password_hash VARCHAR(255) NOT NULL, 
	fecha_registro DATETIME NOT NULL DEFAULT (now()), 
	PRIMARY KEY (id_usuario), 
	UNIQUE (email)
)COMMENT='Personas que inician sesión en la plataforma' ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


CREATE TABLE importaciones (
	id_importacion INTEGER NOT NULL AUTO_INCREMENT, 
	id_empresa INTEGER NOT NULL, 
	id_usuario INTEGER, 
	nombre_archivo VARCHAR(255) NOT NULL, 
	tipo_datos ENUM('ventas','productos','compras','gastos') NOT NULL, 
	fecha DATETIME NOT NULL DEFAULT (now()), 
	estado ENUM('completada','con_errores','deshecha') NOT NULL, 
	filas_ok INTEGER NOT NULL DEFAULT '0', 
	filas_con_error INTEGER NOT NULL DEFAULT '0', 
	detalle_errores JSON, 
	PRIMARY KEY (id_importacion), 
	FOREIGN KEY(id_empresa) REFERENCES empresas (id_empresa) ON DELETE CASCADE, 
	FOREIGN KEY(id_usuario) REFERENCES usuarios (id_usuario) ON DELETE SET NULL
)COMMENT='Historial de cargas de Excel/CSV (trazabilidad y deshacer)' ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX ix_importaciones_empresa_fecha ON importaciones (id_empresa, fecha);

CREATE TABLE usuarios_empresas (
	id_usuario INTEGER NOT NULL, 
	id_empresa INTEGER NOT NULL, 
	rol ENUM('dueno','consulta') NOT NULL DEFAULT 'dueno', 
	PRIMARY KEY (id_usuario, id_empresa), 
	FOREIGN KEY(id_usuario) REFERENCES usuarios (id_usuario) ON DELETE CASCADE, 
	FOREIGN KEY(id_empresa) REFERENCES empresas (id_empresa) ON DELETE CASCADE
)COMMENT='Qué usuario puede ver qué empresa' ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


CREATE TABLE gastos_operativos (
	id_gasto INTEGER NOT NULL AUTO_INCREMENT, 
	id_empresa INTEGER NOT NULL, 
	fecha DATE NOT NULL, 
	concepto VARCHAR(150) NOT NULL, 
	categoria VARCHAR(80) NOT NULL, 
	tipo ENUM('fijo','variable') NOT NULL COMMENT 'fijo = renta, nómina, servicios; variable = insumos, fletes, comisiones', 
	monto NUMERIC(12, 2) NOT NULL, 
	id_importacion INTEGER, 
	PRIMARY KEY (id_gasto), 
	FOREIGN KEY(id_empresa) REFERENCES empresas (id_empresa) ON DELETE CASCADE, 
	FOREIGN KEY(id_importacion) REFERENCES importaciones (id_importacion) ON DELETE SET NULL
)COMMENT='Registro de gastos operativos (fijos y variables)' ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX ix_gastos_empresa_fecha ON gastos_operativos (id_empresa, fecha);

CREATE TABLE productos_cat (
	id_producto INTEGER NOT NULL AUTO_INCREMENT, 
	id_empresa INTEGER NOT NULL, 
	sku_o_nombre VARCHAR(150) NOT NULL, 
	categoria VARCHAR(80) NOT NULL DEFAULT 'General', 
	unidad VARCHAR(20) NOT NULL DEFAULT 'pieza', 
	stock_actual NUMERIC(12, 2) NOT NULL DEFAULT '0', 
	stock_minimo NUMERIC(12, 2) NOT NULL DEFAULT '0', 
	costo_promedio NUMERIC(12, 2) NOT NULL DEFAULT '0', 
	precio_venta NUMERIC(12, 2) NOT NULL DEFAULT '0', 
	id_importacion INTEGER, 
	PRIMARY KEY (id_producto), 
	CONSTRAINT uq_producto_empresa_nombre UNIQUE (id_empresa, sku_o_nombre), 
	FOREIGN KEY(id_empresa) REFERENCES empresas (id_empresa) ON DELETE CASCADE, 
	FOREIGN KEY(id_importacion) REFERENCES importaciones (id_importacion) ON DELETE SET NULL
)COMMENT='Registro de productos' ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX ix_productos_empresa_producto ON productos_cat (id_empresa, id_producto);

CREATE TABLE compras_producto (
	id_compra INTEGER NOT NULL AUTO_INCREMENT, 
	id_empresa INTEGER NOT NULL, 
	id_producto INTEGER NOT NULL, 
	fecha DATE NOT NULL, 
	cantidad NUMERIC(12, 2) NOT NULL, 
	costo_unitario NUMERIC(12, 2) NOT NULL, 
	proveedor VARCHAR(120), 
	id_importacion INTEGER, 
	PRIMARY KEY (id_compra), 
	FOREIGN KEY(id_empresa) REFERENCES empresas (id_empresa) ON DELETE CASCADE, 
	FOREIGN KEY(id_producto) REFERENCES productos_cat (id_producto) ON DELETE CASCADE, 
	FOREIGN KEY(id_importacion) REFERENCES importaciones (id_importacion) ON DELETE SET NULL
)COMMENT='Registro de compras de producto (resurtido de inventario)' ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX ix_compras_empresa_fecha ON compras_producto (id_empresa, fecha);

CREATE TABLE historial_ventas (
	id_venta INTEGER NOT NULL AUTO_INCREMENT, 
	id_empresa INTEGER NOT NULL, 
	id_producto INTEGER NOT NULL, 
	fecha_hora DATETIME NOT NULL, 
	cantidad_vendida NUMERIC(12, 2) NOT NULL, 
	precio_unitario NUMERIC(12, 2) NOT NULL, 
	costo_unitario NUMERIC(12, 2) NOT NULL, 
	id_importacion INTEGER, 
	PRIMARY KEY (id_venta), 
	FOREIGN KEY(id_empresa) REFERENCES empresas (id_empresa) ON DELETE CASCADE, 
	FOREIGN KEY(id_producto) REFERENCES productos_cat (id_producto) ON DELETE CASCADE, 
	FOREIGN KEY(id_importacion) REFERENCES importaciones (id_importacion) ON DELETE SET NULL
)COMMENT='Registro de ventas' ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX ix_ventas_empresa_fecha ON historial_ventas (id_empresa, fecha_hora);

-- Vista para modelos de series de tiempo (fase 2)
CREATE VIEW v_ventas_diarias AS
SELECT
    id_empresa,
    id_producto,
    DATE(fecha_hora)                         AS fecha,
    SUM(cantidad_vendida)                    AS unidades,
    SUM(cantidad_vendida * precio_unitario)  AS ingreso,
    SUM(cantidad_vendida * costo_unitario)   AS costo
FROM historial_ventas
GROUP BY id_empresa, id_producto, DATE(fecha_hora);
