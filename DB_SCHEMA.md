# DB_SCHEMA.md — InverTec

Modelo relacional en MySQL. Coincide con el diagrama entidad-relación de la documentación (Avance de reto, sección 2.7).

## Entidades

### Usuario
| Campo | Tipo | Notas |
|---|---|---|
| id | INT, PK, AUTO_INCREMENT | |
| nombre | VARCHAR(120) | |
| correo | VARCHAR(150), UNIQUE | |
| password_hash | VARCHAR(255) | nunca guardar la contraseña en texto plano |
| rol | ENUM('inversionista','administrador') | default 'inversionista' |
| fecha_registro | DATETIME | default CURRENT_TIMESTAMP |

### Portafolio
| Campo | Tipo | Notas |
|---|---|---|
| id | INT, PK, AUTO_INCREMENT | |
| usuario_id | INT, FK → Usuario.id | relación 1:1 con Usuario |
| saldo_virtual | DECIMAL(12,2) | saldo simulado disponible |
| fecha_creacion | DATETIME | default CURRENT_TIMESTAMP |

### Accion
| Campo | Tipo | Notas |
|---|---|---|
| id | INT, PK, AUTO_INCREMENT | |
| ticker | VARCHAR(10), UNIQUE | ej. GOOGL, NVDA |
| nombre_empresa | VARCHAR(150) | |

### Movimiento
| Campo | Tipo | Notas |
|---|---|---|
| id | INT, PK, AUTO_INCREMENT | |
| portafolio_id | INT, FK → Portafolio.id | |
| accion_id | INT, FK → Accion.id | |
| tipo | ENUM('compra','venta') | |
| cantidad | DECIMAL(12,4) | |
| precio_unitario | DECIMAL(12,2) | precio de mercado al momento del movimiento |
| riesgo_calculado | DECIMAL(5,2) | nivel de riesgo mostrado antes de confirmar |
| fecha | DATETIME | default CURRENT_TIMESTAMP |

## Relaciones

- Usuario **1 : 1** Portafolio
- Portafolio **1 : N** Movimiento
- Accion **1 : N** Movimiento

## DDL de referencia (MySQL)

```sql
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
```
