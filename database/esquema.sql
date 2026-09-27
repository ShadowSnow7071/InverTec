-- Esquema MySQL de referencia (mismo contenido que DB_SCHEMA.md).
-- En desarrollo se aplica con: flask db upgrade
-- No ejecutar a mano si ya usas migraciones Alembic.

CREATE TABLE usuario (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(120) NOT NULL,
    correo VARCHAR(150) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    rol ENUM('inversionista','administrador') NOT NULL DEFAULT 'inversionista',
    fecha_registro DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE portafolio (
    id INT AUTO_INCREMENT PRIMARY KEY,
    usuario_id INT NOT NULL UNIQUE,
    saldo_virtual DECIMAL(12,2) NOT NULL DEFAULT 10000.00,
    fecha_creacion DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (usuario_id) REFERENCES usuario(id)
);

CREATE TABLE accion (
    id INT AUTO_INCREMENT PRIMARY KEY,
    ticker VARCHAR(10) NOT NULL UNIQUE,
    nombre_empresa VARCHAR(150) NOT NULL
);

CREATE TABLE movimiento (
    id INT AUTO_INCREMENT PRIMARY KEY,
    portafolio_id INT NOT NULL,
    accion_id INT NOT NULL,
    tipo ENUM('compra','venta') NOT NULL,
    cantidad DECIMAL(12,4) NOT NULL,
    precio_unitario DECIMAL(12,2) NOT NULL,
    riesgo_calculado DECIMAL(5,2),
    fecha DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (portafolio_id) REFERENCES portafolio(id),
    FOREIGN KEY (accion_id) REFERENCES accion(id)
);
