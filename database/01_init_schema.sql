-- Estructura Base Multitenant (PostgreSQL)

CREATE SCHEMA IF NOT EXISTS public;

-- Tabla central de Tenants
CREATE TABLE public.tenants (
    id SERIAL PRIMARY KEY,
    tenant_id VARCHAR(50) UNIQUE NOT NULL,
    company_name VARCHAR(100),
    profit_db_connection VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Esquema de ejemplo para el Tenant 001
CREATE SCHEMA IF NOT EXISTS tenant_001;

-- Tabla de mapeo polimórfico
CREATE TABLE tenant_001.sync_mappings (
    id SERIAL PRIMARY KEY,
    entity_type VARCHAR(50) NOT NULL, -- 'product', 'tax', 'user', 'payment_method'
    odoo_id VARCHAR(100) NOT NULL,
    profit_code VARCHAR(50) NOT NULL,
    UNIQUE (entity_type, odoo_id)
);

-- Tabla de órdenes POS (Idempotencia y Trazabilidad)
CREATE TABLE tenant_001.pos_orders (
    id SERIAL PRIMARY KEY,
    correlation_id UUID UNIQUE NOT NULL,
    odoo_pos_reference VARCHAR(100) UNIQUE NOT NULL,
    order_type VARCHAR(20) NOT NULL, -- 'invoice', 'refund'
    refunded_order_id VARCHAR(100),
    fec_emis TIMESTAMP NOT NULL,
    raw_payload JSONB NOT NULL,
    sync_status VARCHAR(20) DEFAULT 'pending', -- 'pending', 'processing', 'synced', 'failed'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabla de Sesiones (Z Reports)
CREATE TABLE tenant_001.pos_sessions (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(100) UNIQUE NOT NULL,
    cashier_id VARCHAR(50),
    z_report_summary JSONB,
    status VARCHAR(20) DEFAULT 'opened'
);
