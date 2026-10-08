# ENTREGABLE 2: Software Requirements Specification (SRS) & Architecture Blueprint

**Machine-to-Machine Document — Designed for Antigravity IDE Code Generation**

> [!IMPORTANT]
> Este documento es la Especificación de Requerimientos de Software (SRS) y Blueprint Arquitectónico para el Middleware de Integración `profit2k12-odoo-middleware`. Es un documento **Machine-to-Machine** diseñado para que un agente IA (Antigravity IDE) genere el código base completo. Cada sección contiene especificaciones ejecutables: DDL, interfaces Python, payloads JSON, contratos WCF y configuraciones de infraestructura.

---

## 1. Metadata del Proyecto

| Campo | Valor |
|-------|-------|
| **Nombre** | `profit2k12-odoo-middleware` |
| **Versión** | 1.0.0 |
| **Lenguaje Principal** | Python 3.11+ |
| **Framework API** | FastAPI 0.104+ |
| **ORM** | SQLAlchemy 2.0 (async) |
| **Task Queue** | Celery 5.3+ |
| **Message Broker** | RabbitMQ 3.12+ |
| **Cache** | Redis 7+ |
| **BD Intermedia** | PostgreSQL 15+ |
| **BD Odoo** | PostgreSQL 15+ (separada, por tenant) |
| **BD Profit** | Microsoft SQL Server 2016+ (separada, por tenant) |
| **SOAP Client** | zeep 4.2+ |
| **Arquitectura** | Hexagonal (Ports & Adapters) |
| **Patrón de Comunicación** | Event-Driven + Request-Response híbrido |
| **Dominio** | Retail multi-tenant venezolano (Farmacia, Restaurante, extensible) |
| **Timezone** | UTC internamente, `America/Caracas` (UTC-4) para presentación |
| **Precisión Monetaria** | `NUMERIC(20,8)` en tránsito, `NUMERIC(18,2)` en destino |

```mermaid
flowchart TD
    subgraph POS["Puntos de Venta (Odoo)"]
        ODOO_POS["Odoo POS<br/><i>JSON-RPC / XML-RPC</i>"]
        ODOO_DB[("PostgreSQL<br/><i>Odoo DB (por tenant)</i>")]
        ODOO_POS --> ODOO_DB
    end

    subgraph MW["profit2k12-odoo-middleware"]
        API["FastAPI REST API<br/><i>Puerto 8000</i>"]
        WORKERS["Celery Workers<br/><i>transaction, ftp, stock,<br/>rate, reconciliation</i>"]
        BEAT["Celery Beat<br/><i>Scheduler</i>"]
        BROKER[("RabbitMQ<br/><i>4 Exchanges, 15+ Queues</i>")]
        CACHE[("Redis 7<br/><i>Stock, Rates, Sessions,<br/>Idempotency, Locks</i>")]
        MW_DB[("PostgreSQL 15<br/><i>Middleware DB<br/>(tenants, transactions,<br/>mappings, audit)</i>")]

        API --> BROKER
        API --> CACHE
        API --> MW_DB
        BROKER --> WORKERS
        BEAT --> BROKER
        WORKERS --> CACHE
        WORKERS --> MW_DB
    end

    subgraph ERP["Backend ERP (Profit Plus 2k12)"]
        WCF["Servicios WCF<br/><i>IIS / .NET 4.8<br/>SOAP 1.2</i>"]
        PROFIT_DB[("SQL Server<br/><i>Profit DB (por tenant)</i>")]
        WCF --> PROFIT_DB
    end

    subgraph EXT["Sistemas Externos"]
        FTP[("FTP Droguerías<br/><i>COBECA, DIFACO, NENA</i>")]
        BCV["API BCV<br/><i>Tasa de cambio</i>"]
        CASHEA["API Cashea<br/><i>BNPL</i>"]
        FISCAL["Impresora Fiscal<br/><i>The Factory / Bixolon</i>"]
    end

    ODOO_POS <-->|"REST/JSON"| API
    WORKERS <-->|"SOAP/XML<br/>zeep"| WCF
    WORKERS <-->|"XML-RPC"| ODOO_POS
    WORKERS -->|"SFTP/FTPS"| FTP
    WORKERS -->|"HTTPS"| BCV
    API <-->|"Webhooks"| CASHEA
    ODOO_POS --> FISCAL
```

---

## 2. Estructura de Directorios

```text
profit2k12-odoo-middleware/
├── src/
│   ├── __init__.py
│   ├── main.py                          # FastAPI app factory
│   ├── core/                            # === DOMAIN LAYER ===
│   │   ├── __init__.py
│   │   ├── entities/                    # Rich domain entities
│   │   │   ├── __init__.py
│   │   │   ├── tenant.py                # Tenant entity
│   │   │   ├── transaction.py           # Transaction entity + state machine
│   │   │   ├── product.py               # Product entity with UoM
│   │   │   ├── payment.py               # Payment entity (multi-currency)
│   │   │   ├── lot.py                   # Lot tracking entity (pharmacy)
│   │   │   ├── recipe_capture.py        # Medical recipe capture entity
│   │   │   ├── exchange_rate.py         # Exchange rate entity
│   │   │   └── fiscal_document.py       # Fiscal control number entity
│   │   ├── value_objects/               # Immutable value objects
│   │   │   ├── __init__.py
│   │   │   ├── money.py                 # Money(amount, currency, precision)
│   │   │   ├── uom_conversion.py        # UoM conversion factor
│   │   │   ├── idempotency_key.py       # Validated idempotency key
│   │   │   ├── tax_breakdown.py         # Tax calculation (IVA, IGTF)
│   │   │   ├── bank_reference.py        # Bank reference with validation
│   │   │   └── fiscal_number.py         # Fiscal control number format
│   │   ├── ports/                       # Abstract interfaces (ABC)
│   │   │   ├── __init__.py
│   │   │   ├── product_catalog_port.py
│   │   │   ├── inventory_port.py
│   │   │   ├── transaction_port.py
│   │   │   ├── payment_gateway_port.py
│   │   │   ├── exchange_rate_port.py
│   │   │   ├── ftp_sync_port.py
│   │   │   ├── erp_connector_port.py
│   │   │   ├── pos_connector_port.py
│   │   │   ├── notification_port.py
│   │   │   ├── audit_port.py
│   │   │   ├── cache_port.py
│   │   │   └── fiscal_port.py
│   │   ├── services/                    # Domain services (orchestration)
│   │   │   ├── __init__.py
│   │   │   ├── transaction_service.py   # Transaction lifecycle management
│   │   │   ├── payment_service.py       # Multi-currency payment processing
│   │   │   ├── catalog_sync_service.py  # Catalog sync orchestration
│   │   │   ├── stock_service.py         # Stock queries with cache
│   │   │   ├── recipe_service.py        # Medical recipe validation (pharmacy)
│   │   │   ├── exchange_rate_service.py # Rate management + per-document rate
│   │   │   ├── uom_service.py          # UoM conversion (Caja→Blister→Unit)
│   │   │   ├── fiscal_service.py       # Fiscal control number management
│   │   │   └── change_service.py       # Mobile payment change calculation
│   │   └── events/                      # Domain event definitions
│   │       ├── __init__.py
│   │       ├── order_events.py          # OrderCreated, OrderClosed, OrderCancelled
│   │       ├── payment_events.py        # PaymentProcessed, PaymentRefunded
│   │       ├── product_events.py        # ProductSynced, PriceUpdated
│   │       ├── stock_events.py          # StockUpdated, StockLowAlert
│   │       ├── ftp_events.py            # FTPSyncCompleted, FTPSyncFailed
│   │       ├── recipe_events.py         # RecipeCaptured
│   │       ├── rate_events.py           # ExchangeRateUpdated
│   │       └── fiscal_events.py         # ControlNumberReserved
│   ├── adapters/                        # === INFRASTRUCTURE LAYER ===
│   │   ├── __init__.py
│   │   ├── inbound/                     # Driving adapters (HTTP, Webhooks)
│   │   │   ├── __init__.py
│   │   │   ├── rest/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── tenant_router.py
│   │   │   │   ├── product_router.py
│   │   │   │   ├── transaction_router.py
│   │   │   │   ├── payment_router.py
│   │   │   │   ├── exchange_rate_router.py
│   │   │   │   ├── ftp_sync_router.py
│   │   │   │   ├── pharmacy_router.py
│   │   │   │   ├── restaurant_router.py
│   │   │   │   ├── health_router.py
│   │   │   │   └── admin_router.py
│   │   │   ├── webhooks/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── odoo_webhook.py      # Odoo order notifications
│   │   │   │   ├── cashea_webhook.py    # Cashea payment confirmation
│   │   │   │   └── bank_webhook.py      # Bank payment notifications
│   │   │   └── middleware/
│   │   │       ├── __init__.py
│   │   │       ├── auth_middleware.py   # JWT validation
│   │   │       ├── tenant_middleware.py  # Tenant context injection
│   │   │       ├── rate_limit_middleware.py
│   │   │       └── request_id_middleware.py
│   │   ├── outbound/                    # Driven adapters
│   │   │   ├── __init__.py
│   │   │   ├── profit_wcf_adapter.py    # WCF/SOAP client (zeep)
│   │   │   ├── odoo_rpc_adapter.py      # Odoo XML-RPC/JSON-RPC client
│   │   │   ├── ftp_adapter.py           # FTP/SFTP client per provider
│   │   │   ├── redis_cache_adapter.py   # Redis cache implementation
│   │   │   ├── bcv_rate_adapter.py      # BCV exchange rate scraper
│   │   │   ├── cashea_adapter.py        # Cashea API client
│   │   │   └── repositories/
│   │   │       ├── __init__.py
│   │   │       ├── tenant_repository.py
│   │   │       ├── transaction_repository.py
│   │   │       ├── entity_mapping_repository.py
│   │   │       ├── exchange_rate_repository.py
│   │   │       ├── payment_reference_repository.py
│   │   │       ├── ftp_sync_repository.py
│   │   │       ├── lot_tracking_repository.py
│   │   │       ├── recipe_capture_repository.py
│   │   │       └── audit_repository.py
│   │   └── messaging/                   # RabbitMQ producers/consumers
│   │       ├── __init__.py
│   │       ├── event_publisher.py       # Publish events to exchanges
│   │       ├── event_consumer.py        # Consume events from queues
│   │       └── dead_letter_handler.py   # DLQ processing
│   ├── modules/                         # === BUSINESS VERTICAL MODULES ===
│   │   ├── __init__.py
│   │   ├── pharmacy/
│   │   │   ├── __init__.py
│   │   │   ├── pharmacy_service.py      # Recipe validation, lot FEFO, UoM
│   │   │   ├── ftp_parsers/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── base_parser.py       # Abstract parser
│   │   │   │   ├── cobeca_parser.py     # COBECA specific format
│   │   │   │   ├── difaco_parser.py     # DIFACO specific format
│   │   │   │   ├── nena_parser.py       # Droguería NENA format
│   │   │   │   └── drocerca_parser.py   # DROCERCA format
│   │   │   └── validators/
│   │   │       ├── __init__.py
│   │   │       ├── recipe_validator.py  # Medical recipe fields validation
│   │   │       └── lot_validator.py     # Expiry date, stock validation
│   │   ├── restaurant/
│   │   │   ├── __init__.py
│   │   │   ├── restaurant_service.py    # BOM explosion, tips, courtesy
│   │   │   ├── bom_handler.py           # Bill of Materials processing
│   │   │   └── tip_calculator.py        # Service charge + voluntary tip
│   │   └── core_router/
│   │       ├── __init__.py
│   │       ├── tenant_router_service.py # Route transactions by business type
│   │       ├── payment_router.py        # Route payments to correct handler
│   │       └── sync_router.py           # Route sync operations
│   ├── workers/                         # === CELERY TASKS ===
│   │   ├── __init__.py
│   │   ├── celery_app.py               # Celery application factory
│   │   ├── ftp_sync_worker.py          # FTP download + parse + update
│   │   ├── transaction_retry_worker.py # Retry failed transactions
│   │   ├── stock_sync_worker.py        # Periodic stock sync Profit→Redis
│   │   ├── reconciliation_worker.py    # Payment reconciliation
│   │   ├── rate_update_worker.py       # BCV rate fetch + distribute
│   │   ├── lot_expiry_worker.py        # Expiry alerts
│   │   ├── catalog_sync_worker.py      # Full catalog sync Profit→Odoo
│   │   └── dead_letter_worker.py       # Process DLQ messages
│   └── config/
│       ├── __init__.py
│       ├── settings.py                  # Pydantic BaseSettings
│       ├── database.py                  # SQLAlchemy async engine + session
│       ├── redis.py                     # Redis connection pool
│       ├── rabbitmq.py                  # RabbitMQ connection
│       └── logging.py                   # Structured JSON logging config
├── tests/
│   ├── __init__.py
│   ├── conftest.py                      # Shared fixtures
│   ├── factories/                       # factory_boy factories
│   │   ├── __init__.py
│   │   ├── tenant_factory.py
│   │   ├── transaction_factory.py
│   │   └── product_factory.py
│   ├── unit/
│   │   ├── __init__.py
│   │   ├── test_transaction_service.py
│   │   ├── test_payment_service.py
│   │   ├── test_uom_service.py
│   │   ├── test_exchange_rate_service.py
│   │   ├── test_recipe_validator.py
│   │   └── test_change_service.py
│   ├── integration/
│   │   ├── __init__.py
│   │   ├── test_profit_wcf_adapter.py
│   │   ├── test_odoo_rpc_adapter.py
│   │   ├── test_transaction_repository.py
│   │   └── test_redis_cache.py
│   ├── e2e/
│   │   ├── __init__.py
│   │   ├── test_restaurant_flow.py
│   │   └── test_pharmacy_flow.py
│   └── fixtures/
│       ├── wcf_responses/               # Captured SOAP XML responses
│       ├── ftp_samples/                 # Sample FTP files per provider
│       └── odoo_payloads/               # Sample Odoo order JSONs
├── migrations/
│   ├── alembic.ini
│   ├── env.py
│   └── versions/
│       └── 001_initial_schema.py
├── docker/
│   ├── Dockerfile.api
│   ├── Dockerfile.worker
│   ├── nginx.conf
│   └── entrypoint.sh
├── docker-compose.yml
├── docker-compose.dev.yml
├── pyproject.toml
├── requirements.txt
├── requirements-dev.txt
├── .env.example
├── Makefile
└── README.md
```

---

## 3. Esquema de Base de Datos Intermedia (PostgreSQL)

> [!WARNING]
> Esta base de datos actúa como almacén de estados, mapeo de identidades y sistema de tolerancia a fallos. **No sustituye** la persistencia de Odoo ni de Profit. Funciona como capa de transición, auditoría y eventual consistencia.

### 3.1 DDL Completo — Ejecutable en PostgreSQL 15+

```sql
-- ============================================================
-- profit2k12-odoo-middleware :: Esquema de Base de Datos
-- Versión: 1.0.0
-- Compatibilidad: PostgreSQL 15+
-- ============================================================

-- Extensiones requeridas
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============================================================
-- ENUMS
-- ============================================================
CREATE TYPE business_type_enum AS ENUM (
    'pharmacy', 'restaurant', 'hardware_store', 'generic'
);

CREATE TYPE transaction_status_enum AS ENUM (
    'pending', 'queued', 'processing', 'completed', 'failed',
    'retrying', 'dead_letter', 'cancelled'
);

CREATE TYPE sync_status_enum AS ENUM (
    'running', 'completed', 'completed_with_errors', 'failed'
);

CREATE TYPE payment_direction_enum AS ENUM (
    'inbound',   -- cobro normal
    'outbound'   -- egreso (vuelto por PM)
);

CREATE TYPE product_classification_enum AS ENUM (
    'otc', 'ethical', 'antibiotic', 'psychotropic',
    'narcotic', 'general', 'food', 'liquor'
);

CREATE TYPE currency_era_enum AS ENUM (
    'VEB',  -- Pre-2008 (Bolívar)
    'VEF',  -- 2008-2018 (Bolívar Fuerte)
    'VES',  -- 2018-2021 (Bolívar Soberano, pre-reconversión)
    'VED'   -- 2021+ (Bolívar Digital)
);

-- ============================================================
-- 3.1 TENANTS
-- ============================================================
CREATE TABLE tenants (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    code            VARCHAR(50) UNIQUE NOT NULL,
    name            VARCHAR(200) NOT NULL,
    business_type   business_type_enum NOT NULL,
    odoo_url        VARCHAR(500) NOT NULL,
    odoo_db         VARCHAR(100) NOT NULL,
    odoo_user       VARCHAR(100) NOT NULL,
    odoo_api_key    TEXT NOT NULL,  -- encrypted at rest
    profit_wcf_url  VARCHAR(500) NOT NULL,
    profit_db       VARCHAR(100) NOT NULL,
    profit_user     VARCHAR(100),
    profit_api_key  TEXT,           -- encrypted at rest
    timezone        VARCHAR(50) NOT NULL DEFAULT 'America/Caracas',
    default_warehouse VARCHAR(50) NOT NULL DEFAULT '01',
    config          JSONB NOT NULL DEFAULT '{
        "allow_negative_stock": false,
        "require_lot_tracking": false,
        "require_recipe_capture": false,
        "igtf_enabled": true,
        "igtf_rate": 3.0,
        "iva_rate": 16.0,
        "service_charge_rate": 10.0,
        "offline_tolerance_hours": 24,
        "max_retry_count": 5,
        "retry_backoff_base": 60,
        "currency_precision": 2,
        "exchange_rate_precision": 8,
        "ftp_providers": [],
        "payment_method_mappings": {}
    }'::jsonb,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_tenants_code ON tenants(code);
CREATE INDEX idx_tenants_business_type ON tenants(business_type);
CREATE INDEX idx_tenants_active ON tenants(is_active) WHERE is_active = TRUE;

-- ============================================================
-- 3.2 ENTITY MAPPINGS (Bidirectional Odoo ↔ Profit)
-- ============================================================
CREATE TABLE entity_mappings (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    entity_type     VARCHAR(50) NOT NULL,
        -- 'product', 'customer', 'warehouse', 'payment_method',
        -- 'tax_code', 'uom', 'account', 'vendor'
    odoo_id         VARCHAR(100) NOT NULL,
    odoo_model      VARCHAR(100),  -- e.g., 'product.template', 'res.partner'
    profit_code     VARCHAR(100) NOT NULL,
    profit_table    VARCHAR(100),  -- e.g., 'art', 'clientes', 'alma'
    sync_direction  VARCHAR(20) NOT NULL DEFAULT 'profit_to_odoo',
        -- 'profit_to_odoo', 'odoo_to_profit', 'bidirectional'
    last_synced_at  TIMESTAMPTZ,
    metadata        JSONB NOT NULL DEFAULT '{}'::jsonb,
        -- Ejemplo para product: { "barcode": "7501234567890", "active_ingredient": "losartan", "classification": "ethical", "uom_factor": 10.0 }
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT uq_entity_mapping_odoo UNIQUE (tenant_id, entity_type, odoo_id),
    CONSTRAINT uq_entity_mapping_profit UNIQUE (tenant_id, entity_type, profit_code)
);

CREATE INDEX idx_entity_mappings_lookup ON entity_mappings(tenant_id, entity_type, odoo_id);
CREATE INDEX idx_entity_mappings_profit ON entity_mappings(tenant_id, entity_type, profit_code);
CREATE INDEX idx_entity_mappings_barcode ON entity_mappings USING GIN ((metadata->'barcode'));
CREATE INDEX idx_entity_mappings_ingredient ON entity_mappings USING GIN ((metadata->'active_ingredient'));

-- ============================================================
-- 3.3 TRANSACTIONS (Cola de transacciones con máquina de estados)
-- ============================================================
CREATE TABLE transactions (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id),
    source_system   VARCHAR(20) NOT NULL CHECK (source_system IN ('odoo', 'profit', 'ftp', 'middleware')),
    transaction_type VARCHAR(50) NOT NULL,
        -- 'pos_invoice', 'credit_note', 'stock_sync', 'catalog_sync',
        -- 'payment_registration', 'ftp_catalog_update', 'rate_update',
        -- 'fiscal_registration', 'bom_explosion'
    payload         JSONB NOT NULL,
    result          JSONB,  -- response from target system
    status          transaction_status_enum NOT NULL DEFAULT 'pending',
    retry_count     INTEGER NOT NULL DEFAULT 0,
    max_retries     INTEGER NOT NULL DEFAULT 5,
    next_retry_at   TIMESTAMPTZ,
    correlation_id  UUID NOT NULL DEFAULT uuid_generate_v4(),
    idempotency_key VARCHAR(255) UNIQUE NOT NULL,
    priority        INTEGER NOT NULL DEFAULT 5,  -- 1=highest, 10=lowest
    business_type   business_type_enum,
    fiscal_control_number VARCHAR(50),
    profit_doc_number VARCHAR(50),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    queued_at       TIMESTAMPTZ,
    processing_at   TIMESTAMPTZ,
    processed_at    TIMESTAMPTZ,
    error_log       JSONB NOT NULL DEFAULT '[]'::jsonb
        -- Array of { "timestamp": "...", "error_code": "...", "message": "...", "stack_trace": "..." }
);

CREATE INDEX idx_transactions_status ON transactions(tenant_id, status);
CREATE INDEX idx_transactions_retry ON transactions(status, next_retry_at)
    WHERE status IN ('failed', 'retrying');
CREATE INDEX idx_transactions_correlation ON transactions(correlation_id);
CREATE INDEX idx_transactions_fiscal ON transactions(fiscal_control_number)
    WHERE fiscal_control_number IS NOT NULL;
CREATE INDEX idx_transactions_created ON transactions(tenant_id, created_at DESC);
CREATE INDEX idx_transactions_type ON transactions(tenant_id, transaction_type);

-- ============================================================
-- 3.4 EXCHANGE RATES (Tasa de cambio por documento)
-- ============================================================
CREATE TABLE exchange_rates (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id),
    document_ref    VARCHAR(100),    -- reference to pos.order or transaction
    rate_type       VARCHAR(30) NOT NULL CHECK (rate_type IN ('bcv', 'parallel', 'internal', 'manual')),
    rate            NUMERIC(20,8) NOT NULL CHECK (rate > 0),
    source_currency VARCHAR(3) NOT NULL DEFAULT 'USD',
    target_currency VARCHAR(3) NOT NULL DEFAULT 'VES',
    currency_era    currency_era_enum NOT NULL DEFAULT 'VED',
    captured_at     TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    captured_by     VARCHAR(100),   -- 'system:bcv_worker', 'user:cajero01'
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    metadata        JSONB NOT NULL DEFAULT '{}'::jsonb
        -- { "bcv_bulletin": "2026-10-08", "previous_rate": 35.50 }
);

CREATE INDEX idx_exchange_rates_current ON exchange_rates(tenant_id, source_currency, target_currency, captured_at DESC);
CREATE INDEX idx_exchange_rates_document ON exchange_rates(tenant_id, document_ref)
    WHERE document_ref IS NOT NULL;

-- ============================================================
-- 3.5 PAYMENT REFERENCES (Conciliación bancaria)
-- ============================================================
CREATE TABLE payment_references (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id),
    transaction_id  UUID NOT NULL REFERENCES transactions(id) ON DELETE CASCADE,
    line_number     INTEGER NOT NULL DEFAULT 1,
    direction       payment_direction_enum NOT NULL DEFAULT 'inbound',
    payment_method  VARCHAR(50) NOT NULL,   -- 'EFE-USD', 'TDD-BAN', 'PM-VES', etc.
    reference_number VARCHAR(100),           -- bank ref, confirmation #
    bank_code       VARCHAR(10),             -- '0102', '0134', etc.
    terminal_id     VARCHAR(50),             -- POS terminal serial
    batch_number    VARCHAR(20),             -- POS batch/lot number
    last_four_digits VARCHAR(4),             -- last 4 of card
    amount          NUMERIC(18,4) NOT NULL,  -- can be negative for change (vuelto)
    currency        VARCHAR(3) NOT NULL,     -- 'VES', 'USD', 'EUR'
    exchange_rate   NUMERIC(20,8),           -- rate used for this specific payment
    amount_ves      NUMERIC(18,4),           -- calculated VES equivalent
    profit_cobro_code VARCHAR(50),           -- mapped Profit payment code
    igtf_amount     NUMERIC(18,4) DEFAULT 0, -- IGTF tax if applies
    reconciled      BOOLEAN NOT NULL DEFAULT FALSE,
    reconciled_at   TIMESTAMPTZ,
    reconciled_by   VARCHAR(100),
    metadata        JSONB NOT NULL DEFAULT '{}'::jsonb,
        -- { "phone": "04141234567", "cashea_order_id": "CSH-001", "zelle_confirmation": "ZEL-999" }
    created_at      TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT uq_payment_ref UNIQUE (tenant_id, payment_method, reference_number)
);

CREATE INDEX idx_payment_refs_transaction ON payment_references(transaction_id);
CREATE INDEX idx_payment_refs_reconcile ON payment_references(tenant_id, reconciled)
    WHERE reconciled = FALSE;
CREATE INDEX idx_payment_refs_bank ON payment_references(tenant_id, bank_code, reference_number);

-- ============================================================
-- 3.6 FTP SYNC LOG
-- ============================================================
CREATE TABLE ftp_sync_log (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id),
    provider_code   VARCHAR(50) NOT NULL,   -- 'COBECA', 'DIFACO', 'NENA'
    file_name       VARCHAR(500) NOT NULL,
    file_hash       VARCHAR(128) NOT NULL,  -- SHA-256 of file content
    file_size_bytes BIGINT,
    original_encoding VARCHAR(20),           -- 'cp1252', 'latin-1', 'utf-8'
    records_total   INTEGER NOT NULL DEFAULT 0,
    records_new     INTEGER NOT NULL DEFAULT 0,
    records_updated INTEGER NOT NULL DEFAULT 0,
    records_skipped INTEGER NOT NULL DEFAULT 0,
    records_failed  INTEGER NOT NULL DEFAULT 0,
    price_changes   INTEGER NOT NULL DEFAULT 0,
    status          sync_status_enum NOT NULL DEFAULT 'running',
    started_at      TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at    TIMESTAMPTZ,
    error_details   JSONB NOT NULL DEFAULT '[]'::jsonb,
        -- Array of { "line": 45, "raw_data": "...", "error": "invalid EAN" }
    metadata        JSONB NOT NULL DEFAULT '{}'::jsonb
        -- { "price_increase_avg_pct": 3.5, "new_products_codes": ["EAN1", "EAN2"] }
);

CREATE INDEX idx_ftp_sync_provider ON ftp_sync_log(tenant_id, provider_code, started_at DESC);
CREATE INDEX idx_ftp_sync_hash ON ftp_sync_log(tenant_id, provider_code, file_hash);

-- ============================================================
-- 3.7 LOT TRACKING (Farmacia)
-- ============================================================
CREATE TABLE lot_tracking (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id),
    product_mapping_id  UUID NOT NULL REFERENCES entity_mappings(id) ON DELETE CASCADE,
    lot_number          VARCHAR(100) NOT NULL,
    expiry_date         DATE NOT NULL,
    quantity_available  NUMERIC(18,4) NOT NULL DEFAULT 0 CHECK (quantity_available >= 0),
    quantity_reserved   NUMERIC(18,4) NOT NULL DEFAULT 0 CHECK (quantity_reserved >= 0),
    uom_code            VARCHAR(20) NOT NULL,   -- 'CAJA', 'BLISTER', 'UNIDAD'
    uom_factor          NUMERIC(18,8) NOT NULL DEFAULT 1.0,  -- factor to base UoM
    warehouse_code      VARCHAR(50) NOT NULL,
    is_expired          BOOLEAN GENERATED ALWAYS AS (expiry_date < CURRENT_DATE) STORED,
    last_synced_at      TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT uq_lot UNIQUE (tenant_id, product_mapping_id, lot_number, warehouse_code),
    CONSTRAINT chk_available_gte_reserved CHECK (quantity_available >= quantity_reserved)
);

CREATE INDEX idx_lot_tracking_expiry ON lot_tracking(tenant_id, expiry_date)
    WHERE quantity_available > 0;
CREATE INDEX idx_lot_tracking_product ON lot_tracking(product_mapping_id, warehouse_code);

-- ============================================================
-- 3.8 RECIPE CAPTURES (Farmacia — Psicotrópicos)
-- ============================================================
CREATE TABLE recipe_captures (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id),
    transaction_id      UUID NOT NULL REFERENCES transactions(id) ON DELETE CASCADE,
    recipe_number       VARCHAR(100) NOT NULL,
    recipe_type         VARCHAR(30) NOT NULL DEFAULT 'standard',
        -- 'standard', 'special_psychotropic', 'triplicate_narcotic'
    doctor_name         VARCHAR(200) NOT NULL,
    doctor_license      VARCHAR(100) NOT NULL,  -- MPPS number
    medical_college     VARCHAR(200),
    patient_name        VARCHAR(200) NOT NULL,
    patient_id_type     VARCHAR(5) NOT NULL DEFAULT 'V',  -- 'V', 'E', 'P', 'J'
    patient_id_number   VARCHAR(20) NOT NULL,
    product_codes       JSONB NOT NULL,  -- ["PSI-001", "PSI-002"]
    is_original_retained BOOLEAN NOT NULL DEFAULT FALSE,
    retention_location   VARCHAR(100),   -- where physical recipe is stored
    dispensing_pharmacist VARCHAR(200),
    captured_at         TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    synced_to_profit    BOOLEAN NOT NULL DEFAULT FALSE,
    synced_at           TIMESTAMPTZ,
    metadata            JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX idx_recipe_patient ON recipe_captures(tenant_id, patient_id_number);
CREATE INDEX idx_recipe_doctor ON recipe_captures(tenant_id, doctor_license);
CREATE INDEX idx_recipe_number ON recipe_captures(tenant_id, recipe_number);

-- ============================================================
-- 3.9 AUDIT LOG (Inmutable)
-- ============================================================
CREATE TABLE audit_log (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id   UUID NOT NULL REFERENCES tenants(id),
    actor       VARCHAR(200) NOT NULL,   -- 'system:ftp_worker', 'user:cajero01', 'api:odoo_webhook'
    action      VARCHAR(50) NOT NULL,    -- 'create', 'update', 'delete', 'sync', 'login', 'override'
    entity_type VARCHAR(50) NOT NULL,    -- 'transaction', 'product', 'exchange_rate', 'lot'
    entity_id   VARCHAR(100) NOT NULL,
    old_value   JSONB,
    new_value   JSONB,
    ip_address  INET,
    user_agent  VARCHAR(500),
    correlation_id UUID,
    timestamp   TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Partition by month for performance (audit tables grow fast)
-- In production, consider creating partitions via pg_partman
CREATE INDEX idx_audit_log_entity ON audit_log(tenant_id, entity_type, entity_id);
CREATE INDEX idx_audit_log_actor ON audit_log(tenant_id, actor, timestamp DESC);
CREATE INDEX idx_audit_log_timestamp ON audit_log(tenant_id, timestamp DESC);
CREATE INDEX idx_audit_log_correlation ON audit_log(correlation_id)
    WHERE correlation_id IS NOT NULL;

-- ============================================================
-- 3.10 PENDING PRODUCTS (Productos nuevos pendientes de revisión)
-- ============================================================
CREATE TABLE pending_products (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id),
    provider_code   VARCHAR(50) NOT NULL,
    ftp_sync_id     UUID REFERENCES ftp_sync_log(id),
    barcode         VARCHAR(50),
    provider_code_internal VARCHAR(100),
    name            VARCHAR(500) NOT NULL,
    manufacturer    VARCHAR(200),
    active_ingredient VARCHAR(500),
    suggested_price NUMERIC(18,4),
    suggested_cost  NUMERIC(18,4),
    raw_data        JSONB NOT NULL,    -- original parsed row
    status          VARCHAR(30) NOT NULL DEFAULT 'pending',
        -- 'pending', 'approved', 'rejected', 'duplicate'
    reviewed_by     VARCHAR(100),
    reviewed_at     TIMESTAMPTZ,
    classification  product_classification_enum,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_pending_products_status ON pending_products(tenant_id, status);
CREATE INDEX idx_pending_products_barcode ON pending_products(tenant_id, barcode);

-- ============================================================
-- 3.11 POS SESSION CLOSINGS (Cierres de turno / Cierre Z)
-- ============================================================
CREATE TABLE pos_session_closings (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id),
    odoo_session_id VARCHAR(100) NOT NULL,
    pos_config_name VARCHAR(100),
    cashier_name    VARCHAR(200),
    opened_at       TIMESTAMPTZ NOT NULL,
    closed_at       TIMESTAMPTZ NOT NULL,
    total_sales     NUMERIC(18,4) NOT NULL,
    total_refunds   NUMERIC(18,4) NOT NULL DEFAULT 0,
    payment_summary JSONB NOT NULL,
        -- { "EFE-VES": 5000, "EFE-USD": 200, "TDD-BAN": 3000, "PM-VES": -500 }
    declared_cash_ves NUMERIC(18,4),
    declared_cash_usd NUMERIC(18,4),
    difference_ves  NUMERIC(18,4),   -- positive=surplus, negative=shortage
    difference_usd  NUMERIC(18,4),
    z_report_number VARCHAR(50),
    fiscal_machine_serial VARCHAR(50),
    synced_to_profit BOOLEAN NOT NULL DEFAULT FALSE,
    profit_doc_ref  VARCHAR(50),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_session_closings_tenant ON pos_session_closings(tenant_id, closed_at DESC);

-- ============================================================
-- TRIGGERS
-- ============================================================

-- Auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION trigger_set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER set_updated_at_tenants
    BEFORE UPDATE ON tenants
    FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

CREATE TRIGGER set_updated_at_entity_mappings
    BEFORE UPDATE ON entity_mappings
    FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

CREATE TRIGGER set_updated_at_lot_tracking
    BEFORE UPDATE ON lot_tracking
    FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

-- Auto-audit on transaction status change
CREATE OR REPLACE FUNCTION trigger_audit_transaction_status()
RETURNS TRIGGER AS $$
BEGIN
    IF OLD.status IS DISTINCT FROM NEW.status THEN
        INSERT INTO audit_log (tenant_id, actor, action, entity_type, entity_id, old_value, new_value)
        VALUES (
            NEW.tenant_id,
            'system:state_machine',
            'status_change',
            'transaction',
            NEW.id::text,
            jsonb_build_object('status', OLD.status),
            jsonb_build_object('status', NEW.status, 'retry_count', NEW.retry_count)
        );
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER audit_transaction_status
    AFTER UPDATE ON transactions
    FOR EACH ROW EXECUTE FUNCTION trigger_audit_transaction_status();
```

---

## 4. Definición de Ports (Interfaces Python)

> [!TIP]
> Estas interfaces definen los contratos que la capa de infraestructura debe implementar. El Domain Core SOLO conoce estas interfaces. **Nunca** importa `zeep`, `xmlrpc`, `redis`, `sqlalchemy` u otra librería de infraestructura.

```python
"""
src/core/ports/__init__.py
All port interfaces for the Hexagonal Architecture.
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Any, Sequence
from uuid import UUID
from datetime import datetime, date
from decimal import Decimal
from dataclasses import dataclass
from enum import Enum


# ============================================================
# Data Transfer Objects for Ports
# ============================================================

@dataclass(frozen=True)
class ProductDTO:
    code: str
    name: str
    barcode: Optional[str]
    active_ingredient: Optional[str]
    classification: str  # 'otc', 'ethical', 'psychotropic', etc.
    price: Decimal
    cost: Decimal
    tax_code: str
    uom_base: str
    uom_conversions: List[Dict[str, Any]]  # [{"uom": "BLISTER", "factor": 10}]
    metadata: Dict[str, Any]


@dataclass(frozen=True)
class StockDTO:
    product_code: str
    warehouse_code: str
    quantity_available: Decimal
    quantity_reserved: Decimal
    uom: str


@dataclass(frozen=True)
class LotDTO:
    lot_number: str
    expiry_date: date
    quantity_available: Decimal
    quantity_reserved: Decimal
    uom: str
    warehouse_code: str


@dataclass(frozen=True)
class TransactionResultDTO:
    success: bool
    profit_doc_number: Optional[str]
    error_code: Optional[str]
    error_message: Optional[str]
    metadata: Dict[str, Any]


@dataclass(frozen=True)
class ExchangeRateDTO:
    rate: Decimal
    source_currency: str
    target_currency: str
    rate_type: str
    captured_at: datetime
    source: str


@dataclass(frozen=True)
class PaymentResultDTO:
    success: bool
    reference: Optional[str]
    authorization_code: Optional[str]
    error_message: Optional[str]


@dataclass(frozen=True)
class FiscalDocumentDTO:
    control_number: str
    z_report_number: Optional[str]
    machine_serial: str
    document_type: str
    total_amount: Decimal
    tax_amount: Decimal
    fiscal_date: date


# ============================================================
# PORT INTERFACES
# ============================================================

class ProductCatalogPort(ABC):
    """Interface for product catalog operations."""

    @abstractmethod
    async def get_product(self, tenant_id: UUID, product_code: str) -> Optional[ProductDTO]:
        """Get a single product by its code."""
        ...

    @abstractmethod
    async def search_by_active_ingredient(
        self, tenant_id: UUID, ingredient: str, limit: int = 20
    ) -> List[ProductDTO]:
        """Search products by active ingredient (pharmacy)."""
        ...

    @abstractmethod
    async def get_products_modified_since(
        self, tenant_id: UUID, since: datetime
    ) -> List[ProductDTO]:
        """Get products modified since a given date for delta sync."""
        ...

    @abstractmethod
    async def update_prices(
        self, tenant_id: UUID, price_updates: List[Dict[str, Any]]
    ) -> int:
        """Bulk update product prices. Returns count of updated products."""
        ...

    @abstractmethod
    async def sync_product_to_pos(
        self, tenant_id: UUID, product: ProductDTO
    ) -> bool:
        """Create or update a product in the POS system (Odoo)."""
        ...


class InventoryPort(ABC):
    """Interface for inventory/stock operations."""

    @abstractmethod
    async def get_stock(
        self, tenant_id: UUID, product_code: str, warehouse_code: str
    ) -> StockDTO:
        """Get current stock for a product in a warehouse."""
        ...

    @abstractmethod
    async def get_lots(
        self, tenant_id: UUID, product_code: str, warehouse_code: Optional[str] = None
    ) -> List[LotDTO]:
        """Get lot details for a product (pharmacy). Ordered by expiry (FEFO)."""
        ...

    @abstractmethod
    async def reserve_stock(
        self, tenant_id: UUID, product_code: str, lot_number: str,
        quantity: Decimal, warehouse_code: str
    ) -> bool:
        """Reserve stock for a pending sale. Returns True if reservation succeeded."""
        ...

    @abstractmethod
    async def release_reservation(
        self, tenant_id: UUID, product_code: str, lot_number: str,
        quantity: Decimal, warehouse_code: str
    ) -> bool:
        """Release a stock reservation (e.g., cancelled sale)."""
        ...

    @abstractmethod
    async def get_expiring_lots(
        self, tenant_id: UUID, days_ahead: int = 30
    ) -> List[LotDTO]:
        """Get lots expiring within N days for alerting."""
        ...

    @abstractmethod
    async def explode_bom(
        self, tenant_id: UUID, bom_code: str, quantity: Decimal
    ) -> List[Dict[str, Any]]:
        """Explode a Bill of Materials and return components. (Restaurant)"""
        ...


class TransactionPort(ABC):
    """Interface for transaction lifecycle management."""

    @abstractmethod
    async def send_invoice(
        self, tenant_id: UUID, invoice_data: Dict[str, Any]
    ) -> TransactionResultDTO:
        """Send an invoice to the ERP backend."""
        ...

    @abstractmethod
    async def send_credit_note(
        self, tenant_id: UUID, credit_note_data: Dict[str, Any]
    ) -> TransactionResultDTO:
        """Send a credit note (return/refund) to the ERP backend."""
        ...

    @abstractmethod
    async def register_fiscal_document(
        self, tenant_id: UUID, fiscal_data: FiscalDocumentDTO
    ) -> TransactionResultDTO:
        """Register a fiscal document (control number) in the ERP."""
        ...

    @abstractmethod
    async def get_next_control_number(
        self, tenant_id: UUID, document_type: str
    ) -> str:
        """Get the next available fiscal control number from the ERP."""
        ...


class PaymentGatewayPort(ABC):
    """Interface for payment processing and reconciliation."""

    @abstractmethod
    async def process_payment(
        self, tenant_id: UUID, payment_data: Dict[str, Any]
    ) -> PaymentResultDTO:
        """Process a payment through the ERP."""
        ...

    @abstractmethod
    async def register_refund(
        self, tenant_id: UUID, refund_data: Dict[str, Any]
    ) -> PaymentResultDTO:
        """Register a refund/change (vuelto PM) in the ERP."""
        ...

    @abstractmethod
    async def get_reconciliation_status(
        self, tenant_id: UUID, payment_id: UUID
    ) -> Dict[str, Any]:
        """Check reconciliation status of a payment."""
        ...


class ExchangeRatePort(ABC):
    """Interface for exchange rate management."""

    @abstractmethod
    async def fetch_current_rate(
        self, source_currency: str = "USD", target_currency: str = "VES"
    ) -> ExchangeRateDTO:
        """Fetch the current exchange rate from external source (BCV)."""
        ...

    @abstractmethod
    async def get_cached_rate(
        self, tenant_id: UUID, source_currency: str = "USD"
    ) -> Optional[ExchangeRateDTO]:
        """Get the cached exchange rate."""
        ...

    @abstractmethod
    async def store_document_rate(
        self, tenant_id: UUID, document_ref: str, rate: ExchangeRateDTO
    ) -> None:
        """Store the exchange rate associated with a specific document."""
        ...


class FTPSyncPort(ABC):
    """Interface for FTP catalog synchronization (drugstore providers)."""

    @abstractmethod
    async def connect(self, provider_code: str) -> bool:
        """Connect to a provider's FTP server."""
        ...

    @abstractmethod
    async def list_files(self, provider_code: str, path: str = "/") -> List[str]:
        """List available files on FTP."""
        ...

    @abstractmethod
    async def download_file(
        self, provider_code: str, remote_path: str, local_path: str
    ) -> str:
        """Download a file. Returns the local file path."""
        ...

    @abstractmethod
    async def parse_catalog(
        self, provider_code: str, file_path: str
    ) -> List[Dict[str, Any]]:
        """Parse a downloaded catalog file into normalized product records."""
        ...


class ERPConnectorPort(ABC):
    """Generic interface for ERP backend communication (Profit WCF)."""

    @abstractmethod
    async def call_service(
        self, tenant_id: UUID, service_name: str, method_name: str,
        payload: Dict[str, Any], timeout: int = 30
    ) -> Dict[str, Any]:
        """Call a WCF service method. Returns the response as a dict."""
        ...

    @abstractmethod
    async def health_check(self, tenant_id: UUID) -> bool:
        """Check if the ERP backend is reachable."""
        ...


class POSConnectorPort(ABC):
    """Generic interface for POS frontend communication (Odoo RPC)."""

    @abstractmethod
    async def search_read(
        self, tenant_id: UUID, model: str, domain: List,
        fields: List[str], limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Execute search_read on Odoo model."""
        ...

    @abstractmethod
    async def create(
        self, tenant_id: UUID, model: str, values: Dict[str, Any]
    ) -> int:
        """Create a record in Odoo. Returns the new record ID."""
        ...

    @abstractmethod
    async def write(
        self, tenant_id: UUID, model: str, record_id: int,
        values: Dict[str, Any]
    ) -> bool:
        """Update a record in Odoo."""
        ...

    @abstractmethod
    async def execute_kw(
        self, tenant_id: UUID, model: str, method: str,
        args: List[Any], kwargs: Optional[Dict[str, Any]] = None
    ) -> Any:
        """Execute any Odoo RPC method."""
        ...


class CachePort(ABC):
    """Interface for cache operations."""

    @abstractmethod
    async def get(self, key: str) -> Optional[str]:
        ...

    @abstractmethod
    async def set(self, key: str, value: str, ttl_seconds: int = 300) -> None:
        ...

    @abstractmethod
    async def hget(self, key: str, field: str) -> Optional[str]:
        ...

    @abstractmethod
    async def hset(self, key: str, mapping: Dict[str, str]) -> None:
        ...

    @abstractmethod
    async def delete(self, key: str) -> None:
        ...

    @abstractmethod
    async def acquire_lock(
        self, key: str, timeout: int = 10, blocking: bool = True
    ) -> bool:
        """Acquire a distributed lock. Used for fiscal correlatives."""
        ...

    @abstractmethod
    async def release_lock(self, key: str) -> None:
        ...


class NotificationPort(ABC):
    """Interface for sending alerts and notifications."""

    @abstractmethod
    async def send_alert(
        self, tenant_id: UUID, level: str, title: str,
        message: str, channel: str = "email"
    ) -> None:
        """Send an alert. Channels: 'email', 'telegram', 'webhook'."""
        ...


class AuditPort(ABC):
    """Interface for immutable audit logging."""

    @abstractmethod
    async def log(
        self, tenant_id: UUID, actor: str, action: str,
        entity_type: str, entity_id: str,
        old_value: Optional[Dict] = None,
        new_value: Optional[Dict] = None,
        ip_address: Optional[str] = None,
        correlation_id: Optional[UUID] = None
    ) -> None:
        ...


class FiscalPort(ABC):
    """Interface for fiscal operations (SENIAT compliance)."""

    @abstractmethod
    async def reserve_control_number(
        self, tenant_id: UUID, document_type: str, pos_id: str
    ) -> str:
        """Reserve the next fiscal control number with distributed locking."""
        ...

    @abstractmethod
    async def register_z_report(
        self, tenant_id: UUID, z_report_data: Dict[str, Any]
    ) -> bool:
        """Register a Z-Report closing in the ERP."""
        ...
```

---

## 5. API REST Endpoints (FastAPI)

### Arquitectura de Rutas

```mermaid
flowchart LR
    subgraph "API Gateway (FastAPI)"
        AUTH["Auth Middleware<br/><i>JWT Validation</i>"]
        TENANT["Tenant Middleware<br/><i>Context Injection</i>"]
        RATE["Rate Limiter<br/><i>Per Tenant</i>"]
        REQ_ID["Request ID<br/><i>Correlation</i>"]
    end

    subgraph "Routers"
        R1["tenant_router<br/>/api/v1/tenants"]
        R2["product_router<br/>/api/v1/{t}/products"]
        R3["transaction_router<br/>/api/v1/{t}/transactions"]
        R4["payment_router<br/>/api/v1/{t}/payments"]
        R5["rate_router<br/>/api/v1/{t}/exchange-rates"]
        R6["ftp_router<br/>/api/v1/{t}/ftp"]
        R7["pharmacy_router<br/>/api/v1/{t}/pharmacy"]
        R8["restaurant_router<br/>/api/v1/{t}/restaurant"]
        R9["health_router<br/>/health, /metrics"]
        R10["admin_router<br/>/api/v1/admin"]
    end

    AUTH --> TENANT --> RATE --> REQ_ID
    REQ_ID --> R1 & R2 & R3 & R4 & R5 & R6 & R7 & R8 & R9 & R10
```

### 5.1 Tenant Management

#### `POST /api/v1/tenants`
**Auth:** SuperAdmin  
**Request:**
```json
{
  "code": "FARM_CENTRAL_01",
  "name": "Farmacia Central Sede Principal",
  "business_type": "pharmacy",
  "odoo_url": "https://odoo.farmcentral.com",
  "odoo_db": "farmcentral_prod",
  "odoo_user": "integration@farmcentral.com",
  "odoo_api_key": "enc:AES256:...",
  "profit_wcf_url": "http://192.168.1.100:8080/ProfitWCF/Services",
  "profit_db": "PROFIT_FARMCENTRAL",
  "default_warehouse": "01",
  "config": {
    "allow_negative_stock": false,
    "require_lot_tracking": true,
    "require_recipe_capture": true,
    "igtf_enabled": true,
    "ftp_providers": [
      {
        "code": "COBECA",
        "host": "ftp.cobeca.com.ve",
        "port": 21,
        "user": "farmcentral",
        "path": "/catalogos/",
        "encoding": "cp1252",
        "format": "fixed_width"
      }
    ],
    "payment_method_mappings": {
      "cash_ves": "EFE-VES",
      "cash_usd": "EFE-USD",
      "tdd_mercantil": "TDD-MER",
      "tdd_banesco": "TDD-BAN",
      "pago_movil": "PM-VES",
      "zelle": "DIV-ZEL",
      "cashea": "CRD-CSH"
    }
  }
}
```
**Response `201 Created`:**
```json
{
  "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "code": "FARM_CENTRAL_01",
  "name": "Farmacia Central Sede Principal",
  "business_type": "pharmacy",
  "is_active": true,
  "created_at": "2026-10-08T14:30:00Z"
}
```

#### `GET /api/v1/tenants/{tenant_id}`
**Auth:** SuperAdmin, TenantAdmin  
**Response `200 OK`:**
```json
{
  "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "code": "FARM_CENTRAL_01",
  "name": "Farmacia Central Sede Principal",
  "business_type": "pharmacy",
  "odoo_db": "farmcentral_prod",
  "profit_db": "PROFIT_FARMCENTRAL",
  "default_warehouse": "01",
  "is_active": true,
  "config": { "...": "..." },
  "created_at": "2026-10-08T14:30:00Z",
  "updated_at": "2026-10-08T14:30:00Z"
}
```

#### `PATCH /api/v1/tenants/{tenant_id}`
**Auth:** SuperAdmin  
**Request:** (partial update)
```json
{
  "config": {
    "igtf_rate": 3.5,
    "iva_rate": 16.0
  }
}
```
**Response `200 OK`:** Updated tenant object.

---

### 5.2 Product Sync

#### `POST /api/v1/{tenant_id}/products/sync`
**Auth:** TenantAdmin  
**Description:** Triggers a delta sync of products from Profit → Odoo.
```json
// REQUEST
{
  "last_sync_date": "2026-10-07T00:00:00Z",
  "include_inactive": false,
  "categories": ["FARMACIA", "OTC"]
}
```
```json
// RESPONSE 202 Accepted
{
  "job_id": "job-cat-sync-20261008-001",
  "status": "queued",
  "estimated_products": 1250,
  "message": "Sincronización de catálogo iniciada"
}
```

#### `POST /api/v1/{tenant_id}/products/search`
**Auth:** POSClient, TenantAdmin  
**Description:** Search products by active ingredient (pharmacy).
```json
// REQUEST
{
  "query": "losartan",
  "search_fields": ["active_ingredient", "name", "barcode"],
  "limit": 20,
  "include_stock": true
}
```
```json
// RESPONSE 200 OK
{
  "results": [
    {
      "product_code": "MED-LOSA-50",
      "name": "Losartán 50mg Tab x30",
      "barcode": "7501234567890",
      "active_ingredient": "Losartán Potásico",
      "manufacturer": "Calox Internacional",
      "classification": "ethical",
      "price_ves": 15.00,
      "price_usd": 0.41,
      "tax_code": "IVA-EX",
      "stock": {
        "total": 45.0,
        "uom": "CAJA",
        "by_lot": [
          {"lot": "L2026A", "expiry": "2027-03-15", "qty": 30.0},
          {"lot": "L2026B", "expiry": "2027-06-20", "qty": 15.0}
        ]
      }
    },
    {
      "product_code": "MED-COZA-50",
      "name": "Cozaar® 50mg Tab x30 (Merck)",
      "barcode": "7509876543210",
      "active_ingredient": "Losartán Potásico",
      "manufacturer": "Merck Sharp & Dohme",
      "classification": "ethical",
      "price_ves": 85.00,
      "price_usd": 2.35,
      "tax_code": "IVA-EX",
      "stock": {
        "total": 8.0,
        "uom": "CAJA",
        "by_lot": [
          {"lot": "MK-2026-XR", "expiry": "2028-01-31", "qty": 8.0}
        ]
      }
    }
  ],
  "total_results": 2
}
```

#### `GET /api/v1/{tenant_id}/products/{product_code}/stock`
**Auth:** POSClient  
```json
// RESPONSE 200 OK
{
  "product_code": "MED-LOSA-50",
  "product_name": "Losartán 50mg Tab x30",
  "total_stock": 45.0,
  "base_uom": "CAJA",
  "warehouses": [
    {"code": "01", "name": "Almacén Principal", "stock": 40.0},
    {"code": "02", "name": "Mostrador", "stock": 5.0}
  ],
  "last_synced_at": "2026-10-08T14:25:00Z",
  "cache_source": "redis",
  "cache_ttl_remaining_seconds": 180
}
```

#### `GET /api/v1/{tenant_id}/products/{product_code}/lots`
**Auth:** POSClient  
```json
// RESPONSE 200 OK
{
  "product_code": "MED-LOSA-50",
  "lots": [
    {
      "lot_number": "L2025-Z99",
      "expiry_date": "2026-12-01",
      "quantity_available": 5.0,
      "quantity_reserved": 0.0,
      "uom": "CAJA",
      "warehouse": "01",
      "is_expired": false,
      "days_to_expiry": 54,
      "status": "warning_near_expiry"
    },
    {
      "lot_number": "L2026A",
      "expiry_date": "2027-03-15",
      "quantity_available": 30.0,
      "quantity_reserved": 2.0,
      "uom": "CAJA",
      "warehouse": "01",
      "is_expired": false,
      "days_to_expiry": 158,
      "status": "ok"
    }
  ],
  "fefo_recommendation": "L2025-Z99"
}
```

---

### 5.3 Transactions

#### `POST /api/v1/{tenant_id}/transactions`
**Auth:** POSClient  
**Description:** Submit a new POS transaction (sale) for processing.
```json
// REQUEST — Full Restaurant Example
{
  "source_system": "odoo",
  "transaction_type": "pos_invoice",
  "idempotency_key": "POS-2026-10-08-CAJA01-00045",
  "business_type": "restaurant",
  "fiscal_control_number": "00-00012345",
  "exchange_rate": {
    "rate": 36.28500000,
    "source_currency": "USD",
    "target_currency": "VES",
    "captured_at": "2026-10-08T14:30:00-04:00"
  },
  "customer": {
    "id_type": "V",
    "id_number": "12345678",
    "name": "Juan Pérez",
    "is_tax_withholding_agent": false
  },
  "lines": [
    {
      "product_code": "HAMB-PREM-01",
      "product_name": "Hamburguesa Premium",
      "quantity": 2.0,
      "unit_price_usd": 12.50,
      "unit_price_ves": 453.56,
      "discount_percent": 0.0,
      "tax_code": "IVA-16",
      "tax_amount_usd": 4.00,
      "tax_amount_ves": 145.14,
      "line_total_usd": 29.00,
      "line_total_ves": 1052.27
    },
    {
      "product_code": "MOJ-CLAS-01",
      "product_name": "Mojito Clásico",
      "quantity": 2.0,
      "unit_price_usd": 8.00,
      "unit_price_ves": 290.28,
      "discount_percent": 0.0,
      "tax_code": "IVA-16-LIC",
      "tax_amount_usd": 2.56,
      "tax_amount_ves": 92.89,
      "line_total_usd": 18.56,
      "line_total_ves": 673.17
    },
    {
      "product_code": "SVC-10PCT",
      "product_name": "Servicio 10%",
      "quantity": 1.0,
      "unit_price_usd": 4.10,
      "unit_price_ves": 148.77,
      "discount_percent": 0.0,
      "tax_code": "EXENTO",
      "tax_amount_usd": 0.0,
      "tax_amount_ves": 0.0,
      "line_total_usd": 4.10,
      "line_total_ves": 148.77
    }
  ],
  "payments": [
    {
      "method": "EFE-USD",
      "amount": 50.00,
      "currency": "USD",
      "reference": null,
      "igtf_applicable": true,
      "igtf_amount_usd": 1.55
    },
    {
      "method": "PM-VES",
      "amount": -258.82,
      "currency": "VES",
      "direction": "outbound",
      "reference": "20261008143500",
      "bank_code": "0102",
      "metadata": {
        "customer_phone": "04141234567",
        "reason": "change_mobile_payment"
      }
    }
  ],
  "totals": {
    "subtotal_usd": 41.00,
    "subtotal_ves": 1487.69,
    "tax_usd": 6.56,
    "tax_ves": 238.03,
    "service_charge_usd": 4.10,
    "service_charge_ves": 148.77,
    "igtf_usd": 1.55,
    "igtf_ves": 56.24,
    "total_usd": 53.21,
    "total_ves": 1930.73
  },
  "metadata": {
    "pos_session": "POS/2026/10/08/001",
    "cashier": "cajero03",
    "table": "Mesa 5",
    "waiter": "Carlos Rodríguez",
    "guests": 2,
    "order_opened_at": "2026-10-08T13:15:00-04:00",
    "order_closed_at": "2026-10-08T14:30:00-04:00"
  }
}
```
```json
// RESPONSE 202 Accepted
{
  "transaction_id": "550e8400-e29b-41d4-a716-446655440000",
  "correlation_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "status": "queued",
  "idempotency_key": "POS-2026-10-08-CAJA01-00045",
  "message": "Transacción encolada para procesamiento"
}
```

#### `POST /api/v1/{tenant_id}/transactions` — Pharmacy Example
```json
// REQUEST — Pharmacy with Lot + Recipe
{
  "source_system": "odoo",
  "transaction_type": "pos_invoice",
  "idempotency_key": "POS-2026-10-08-FARM01-00112",
  "business_type": "pharmacy",
  "fiscal_control_number": "00-00056789",
  "exchange_rate": {
    "rate": 36.28500000,
    "source_currency": "USD",
    "target_currency": "VES",
    "captured_at": "2026-10-08T10:00:00-04:00"
  },
  "lines": [
    {
      "product_code": "MED-CLONAZ-2MG",
      "product_name": "Clonazepam 2mg Tab x30 (Psicotrópico)",
      "quantity": 1.0,
      "unit_price_ves": 25.00,
      "uom": "CAJA",
      "uom_factor": 1.0,
      "lot_number": "PSI-2026-A01",
      "lot_expiry": "2027-06-15",
      "tax_code": "IVA-EX",
      "classification": "psychotropic",
      "recipe_required": true
    },
    {
      "product_code": "MED-AMOX-500",
      "product_name": "Amoxicilina 500mg Caps x21",
      "quantity": 2.0,
      "unit_price_ves": 18.50,
      "uom": "BLISTER",
      "uom_factor": 0.1,
      "profit_uom_quantity": 0.2,
      "profit_uom": "CAJA",
      "lot_number": "L2026-B02",
      "lot_expiry": "2027-08-30",
      "tax_code": "IVA-EX",
      "classification": "antibiotic",
      "recipe_required": true
    }
  ],
  "recipe_capture": {
    "recipe_number": "REC-2026-004521",
    "recipe_type": "special_psychotropic",
    "doctor_name": "Dr. María Elena Gutiérrez",
    "doctor_license": "MPPS-54321",
    "medical_college": "Colegio de Médicos del Edo. Miranda",
    "patient_name": "Roberto Martínez",
    "patient_id_type": "V",
    "patient_id_number": "18765432",
    "is_original_retained": true,
    "dispensing_pharmacist": "Lcda. Ana Rodríguez"
  },
  "payments": [
    {
      "method": "TDD-BAN",
      "amount": 62.00,
      "currency": "VES",
      "reference": "0012",
      "bank_code": "0134",
      "terminal_id": "BAN-TERM-0045",
      "batch_number": "045"
    }
  ]
}
```

#### `GET /api/v1/{tenant_id}/transactions/{tx_id}`
**Auth:** POSClient, TenantAdmin  
```json
// RESPONSE 200 OK
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "tenant_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "completed",
  "transaction_type": "pos_invoice",
  "idempotency_key": "POS-2026-10-08-CAJA01-00045",
  "correlation_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "profit_doc_number": "FAC-0001234",
  "fiscal_control_number": "00-00012345",
  "retry_count": 0,
  "created_at": "2026-10-08T14:30:05Z",
  "queued_at": "2026-10-08T14:30:06Z",
  "processing_at": "2026-10-08T14:30:08Z",
  "processed_at": "2026-10-08T14:30:10Z",
  "error_log": []
}
```

#### `POST /api/v1/{tenant_id}/transactions/{tx_id}/retry`
**Auth:** TenantAdmin  
```json
// RESPONSE 200 OK
{
  "transaction_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "retrying",
  "retry_count": 3,
  "next_retry_at": "2026-10-08T14:35:00Z"
}
```

#### `GET /api/v1/{tenant_id}/transactions?status=failed&page=1&per_page=20`
**Auth:** TenantAdmin  
```json
// RESPONSE 200 OK
{
  "transactions": [
    {
      "id": "...",
      "idempotency_key": "...",
      "status": "failed",
      "retry_count": 5,
      "error_log": [
        {
          "timestamp": "2026-10-08T14:30:10Z",
          "error_code": "WCF_TIMEOUT",
          "message": "WCF service did not respond within 30000ms"
        }
      ],
      "created_at": "2026-10-08T14:30:05Z"
    }
  ],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total": 3,
    "total_pages": 1
  }
}
```

---

### 5.4 Payments

#### `POST /api/v1/{tenant_id}/payments/process`
```json
// REQUEST
{
  "transaction_id": "550e8400-e29b-41d4-a716-446655440000",
  "payments": [
    {
      "method": "EFE-USD",
      "amount": 50.00,
      "currency": "USD",
      "exchange_rate": 36.28500000,
      "igtf_applicable": true,
      "igtf_amount": 1.50
    },
    {
      "method": "PM-VES",
      "amount": 500.00,
      "currency": "VES",
      "reference": "20261008143500",
      "bank_code": "0102",
      "phone": "04141234567"
    }
  ]
}
```
```json
// RESPONSE 200 OK
{
  "status": "processed",
  "payment_refs": [
    {
      "id": "ref-uuid-1",
      "method": "EFE-USD",
      "profit_cobro_code": "EFE-USD",
      "amount": 50.00,
      "igtf": 1.50,
      "reconciled": false
    },
    {
      "id": "ref-uuid-2",
      "method": "PM-VES",
      "profit_cobro_code": "PM-VES",
      "amount": 500.00,
      "reference": "20261008143500",
      "reconciled": false
    }
  ]
}
```

#### `POST /api/v1/{tenant_id}/payments/refund`
**Description:** Register a change/refund via Pago Móvil (vuelto).
```json
// REQUEST
{
  "transaction_id": "550e8400-e29b-41d4-a716-446655440000",
  "refund_method": "PM-VES",
  "amount": -950.00,
  "currency": "VES",
  "reference": "20261008143505",
  "bank_code": "0102",
  "reason": "change_mobile_payment",
  "customer_phone": "04141234567",
  "customer_id": "V-12345678"
}
```
```json
// RESPONSE 200 OK
{
  "status": "processed",
  "refund_ref_id": "ref-uuid-3",
  "profit_cobro_code": "PM-VES",
  "direction": "outbound",
  "message": "Vuelto por Pago Móvil registrado exitosamente"
}
```

---

### 5.5 Exchange Rates

#### `POST /api/v1/{tenant_id}/exchange-rates`
**Auth:** TenantAdmin, System  
```json
// REQUEST
{
  "rate": 36.28500000,
  "source_currency": "USD",
  "target_currency": "VES",
  "rate_type": "bcv",
  "captured_by": "system:bcv_worker"
}
```
```json
// RESPONSE 201 Created
{
  "id": "rate-uuid-1",
  "rate": 36.28500000,
  "source_currency": "USD",
  "target_currency": "VES",
  "rate_type": "bcv",
  "captured_at": "2026-10-08T14:30:00Z",
  "distributed_to": ["profit", "odoo", "redis"]
}
```

#### `GET /api/v1/{tenant_id}/exchange-rates/current`
```json
// RESPONSE 200 OK
{
  "rates": [
    {
      "source_currency": "USD",
      "target_currency": "VES",
      "rate": 36.28500000,
      "rate_type": "bcv",
      "captured_at": "2026-10-08T13:15:00Z",
      "next_update_expected": "2026-10-09T13:00:00Z"
    },
    {
      "source_currency": "EUR",
      "target_currency": "VES",
      "rate": 39.45200000,
      "rate_type": "bcv",
      "captured_at": "2026-10-08T13:15:00Z"
    }
  ]
}
```

#### `GET /api/v1/{tenant_id}/exchange-rates/history?from=2026-10-01&to=2026-10-08`
```json
// RESPONSE 200 OK
{
  "rates": [
    {"date": "2026-10-01", "rate": 35.50000000},
    {"date": "2026-10-02", "rate": 35.75000000},
    {"date": "2026-10-08", "rate": 36.28500000}
  ],
  "period_change_pct": 2.21
}
```

---

### 5.6 FTP Sync

#### `POST /api/v1/{tenant_id}/ftp/sync/trigger`
**Auth:** TenantAdmin  
```json
// REQUEST
{
  "provider_code": "COBECA",
  "force_full_sync": false
}
```
```json
// RESPONSE 202 Accepted
{
  "job_id": "job-ftp-cobeca-20261008-001",
  "provider": "COBECA",
  "status": "queued",
  "message": "Sincronización FTP programada"
}
```

#### `GET /api/v1/{tenant_id}/ftp/sync/status?job_id=job-ftp-cobeca-20261008-001`
```json
// RESPONSE 200 OK
{
  "job_id": "job-ftp-cobeca-20261008-001",
  "provider": "COBECA",
  "status": "completed_with_errors",
  "file_name": "catalogo_20261008.txt",
  "file_hash": "sha256:abc123...",
  "original_encoding": "cp1252",
  "records_total": 12450,
  "records_new": 23,
  "records_updated": 11890,
  "records_skipped": 520,
  "records_failed": 17,
  "price_changes": 3450,
  "started_at": "2026-10-08T02:00:05Z",
  "completed_at": "2026-10-08T02:05:32Z",
  "duration_seconds": 327,
  "errors_sample": [
    {"line": 4521, "error": "Invalid EAN: '750ABC'", "raw": "750ABC|PRODUCTO X|10.50"}
  ]
}
```

---

### 5.7 Pharmacy Specific

#### `POST /api/v1/{tenant_id}/pharmacy/recipe`
```json
// REQUEST
{
  "transaction_id": "550e8400-e29b-41d4-a716-446655440000",
  "recipe_number": "REC-2026-004521",
  "recipe_type": "special_psychotropic",
  "doctor_name": "Dr. María Elena Gutiérrez",
  "doctor_license": "MPPS-54321",
  "medical_college": "Colegio de Médicos del Edo. Miranda",
  "patient_name": "Roberto Martínez",
  "patient_id_type": "V",
  "patient_id_number": "18765432",
  "product_codes": ["MED-CLONAZ-2MG"],
  "is_original_retained": true,
  "dispensing_pharmacist": "Lcda. Ana Rodríguez"
}
```
```json
// RESPONSE 201 Created
{
  "capture_id": "cap-uuid-001",
  "status": "captured",
  "synced_to_profit": false,
  "message": "Récipe capturado exitosamente"
}
```

#### `GET /api/v1/{tenant_id}/pharmacy/lots/expiring?days=30`
```json
// RESPONSE 200 OK
{
  "expiring_lots": [
    {
      "product_code": "MED-AMOX-500",
      "product_name": "Amoxicilina 500mg",
      "lot_number": "L2025-Z99",
      "expiry_date": "2026-12-01",
      "days_remaining": 54,
      "quantity_available": 5.0,
      "uom": "CAJA",
      "warehouse": "01",
      "value_at_cost": 92.50,
      "recommended_action": "discount_or_return"
    }
  ],
  "total_value_at_risk": 92.50
}
```

#### `POST /api/v1/{tenant_id}/pharmacy/uom/convert`
```json
// REQUEST
{
  "product_code": "MED-LOSA-50",
  "from_uom": "BLISTER",
  "to_uom": "CAJA",
  "quantity": 3.0
}
```
```json
// RESPONSE 200 OK
{
  "product_code": "MED-LOSA-50",
  "from_uom": "BLISTER",
  "from_quantity": 3.0,
  "to_uom": "CAJA",
  "to_quantity": 0.30000000,
  "conversion_factor": 0.10000000,
  "precision_note": "Calculation uses NUMERIC(20,8) precision"
}
```

---

### 5.8 Restaurant Specific

#### `POST /api/v1/{tenant_id}/restaurant/orders/close`
**Description:** Process a restaurant order closing with tip and BOM explosion.
```json
// REQUEST
{
  "odoo_order_id": "POS/2026/10/08/0045",
  "table": "Mesa 5",
  "waiter": "Carlos",
  "lines": [
    {"product_code": "HAMB-PREM-01", "qty": 2, "price": 12.50},
    {"product_code": "MOJ-CLAS-01", "qty": 2, "price": 8.00}
  ],
  "service_charge": {"rate": 10.0, "amount": 4.10},
  "voluntary_tip": 3.00,
  "payments": [
    {"method": "EFE-USD", "amount": 48.66, "igtf": 1.46}
  ]
}
```
```json
// RESPONSE 202 Accepted
{
  "transaction_id": "tx-uuid",
  "status": "queued",
  "bom_explosion_status": "pending"
}
```

#### `POST /api/v1/{tenant_id}/restaurant/bom/explode`
**Description:** Test endpoint to verify BOM explosion results.
```json
// REQUEST
{
  "bom_code": "HAMB-PREM-01",
  "quantity": 2.0
}
```
```json
// RESPONSE 200 OK
{
  "bom_code": "HAMB-PREM-01",
  "bom_name": "Hamburguesa Premium",
  "input_quantity": 2.0,
  "components": [
    {"code": "INS-PAN-BRIG", "name": "Pan Brioche", "qty": 2.0, "uom": "UNIDAD", "stock": 45},
    {"code": "INS-CARNE-200", "name": "Carne Res 200g", "qty": 2.0, "uom": "UNIDAD", "stock": 30},
    {"code": "INS-QUESO-CH", "name": "Queso Cheddar", "qty": 4.0, "uom": "LONCHA", "stock": 120},
    {"code": "INS-TOMATE", "name": "Tomate Rodaja", "qty": 4.0, "uom": "RODAJA", "stock": 80},
    {"code": "INS-LECHUGA", "name": "Lechuga", "qty": 2.0, "uom": "HOJA", "stock": 60},
    {"code": "INS-SALSA-ESP", "name": "Salsa Especial Casa", "qty": 0.06, "uom": "LITRO", "stock": 5.2}
  ],
  "all_components_available": true
}
```

---

### 5.9 Health & Admin

#### `GET /health`
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "uptime_seconds": 86400,
  "dependencies": {
    "postgres": {"status": "ok", "latency_ms": 2},
    "redis": {"status": "ok", "latency_ms": 1},
    "rabbitmq": {"status": "ok", "latency_ms": 3, "queued_messages": 12}
  }
}
```

#### `GET /metrics`
**Format:** Prometheus exposition format.

#### `GET /api/v1/admin/queues/status`
**Auth:** SuperAdmin  
```json
{
  "exchanges": [
    {"name": "pos.events", "type": "topic", "messages_published_today": 1250}
  ],
  "queues": [
    {"name": "restaurant.orders", "messages_ready": 3, "messages_unacked": 1, "consumers": 2},
    {"name": "pharmacy.orders", "messages_ready": 0, "messages_unacked": 0, "consumers": 2},
    {"name": "ftp.sync", "messages_ready": 0, "messages_unacked": 0, "consumers": 1},
    {"name": "dead_letter", "messages_ready": 2, "messages_unacked": 0, "consumers": 1}
  ]
}
```

---

## 6. WCF Contract Specifications (Profit Plus)

> [!IMPORTANT]
> Estos son los contratos WCF de Profit Plus con los que el Middleware interactúa. El Middleware usa `zeep` (Python SOAP client) para generar los DTOs XML automáticamente a partir de estos JSON equivalentes. **Nunca se escribe T-SQL directo contra la BD de Profit.**

### `IProfitSalesService.CreateInvoice(InvoiceDTO)`
```json
{
  "InvoiceCode": "",
  "DocumentType": "FACT",
  "IssueDate": "2026-10-08T00:00:00",
  "DueDate": "2026-10-08T00:00:00",
  "CustomerCode": "CLI-00001",
  "CustomerRIF": "V-12345678-0",
  "SalesPersonCode": "VEN-001",
  "WarehouseCode": "01",
  "CurrencyCode": "US$",
  "ExchangeRate": 36.28500000,
  "FiscalControlNumber": "00-00012345",
  "FiscalMachineSerial": "PNY-1234567",
  "ZReportNumber": "",
  "Notes": "Venta POS - Mesa 5",
  "Lines": [
    {
      "LineNumber": 1,
      "ArticleCode": "HAMB-PREM-01",
      "Description": "Hamburguesa Premium",
      "Quantity": 2.0,
      "UnitOfMeasure": "UND",
      "UnitPrice": 12.50,
      "DiscountPercent": 0.0,
      "TaxCode": "IVA16",
      "TaxPercent": 16.0,
      "TaxAmount": 4.00,
      "LineTotal": 29.00,
      "WarehouseCode": "01",
      "IsComposite": true,
      "ExplodeBOM": true
    }
  ],
  "Payments": [
    {
      "PaymentCode": "EFE-USD",
      "Amount": 50.00,
      "Currency": "US$",
      "Reference": "",
      "BankCode": "",
      "IGTFAmount": 1.50,
      "IGTFPercent": 3.0
    },
    {
      "PaymentCode": "PM-VES",
      "Amount": -258.82,
      "Currency": "Bs",
      "Reference": "20261008143500",
      "BankCode": "0102",
      "IGTFAmount": 0,
      "IGTFPercent": 0,
      "IsRefund": true,
      "RefundReason": "VUELTO_PM"
    }
  ],
  "Taxes": [
    {
      "TaxCode": "IVA16",
      "TaxBase": 41.00,
      "TaxAmount": 6.56,
      "TaxPercent": 16.0
    },
    {
      "TaxCode": "IGTF",
      "TaxBase": 50.00,
      "TaxAmount": 1.50,
      "TaxPercent": 3.0
    }
  ]
}
```

### `IProfitSalesService.CreateCreditNote(CreditNoteDTO)`
```json
{
  "CreditNoteCode": "",
  "DocumentType": "N/CR",
  "IssueDate": "2026-10-08T00:00:00",
  "OriginalInvoiceCode": "FAC-0001234",
  "OriginalControlNumber": "00-00012345",
  "CustomerCode": "CLI-00001",
  "Reason": "DEVOLUCION_PRODUCTO",
  "WarehouseCode": "01",
  "CurrencyCode": "US$",
  "ExchangeRate": 36.28500000,
  "Lines": [
    {
      "ArticleCode": "HAMB-PREM-01",
      "Quantity": 1.0,
      "UnitPrice": 12.50,
      "TaxCode": "IVA16",
      "ReturnToStock": false
    }
  ]
}
```

### `IProfitInventoryService.GetStock(productCode, warehouseCode)`
```json
// Request
{ "ArticleCode": "MED-LOSA-50", "WarehouseCode": "01" }
// Response
{
  "ArticleCode": "MED-LOSA-50",
  "WarehouseCode": "01",
  "StockAvailable": 45.0000,
  "StockReserved": 2.0000,
  "StockInTransit": 0.0000,
  "UnitOfMeasure": "CAJA",
  "LastUpdated": "2026-10-08T14:00:00"
}
```

### `IProfitInventoryService.GetLots(productCode)`
```json
// Response
{
  "ArticleCode": "MED-LOSA-50",
  "Lots": [
    {
      "LotNumber": "L2025-Z99",
      "ExpiryDate": "2026-12-01",
      "QuantityAvailable": 5.0000,
      "WarehouseCode": "01"
    },
    {
      "LotNumber": "L2026A",
      "ExpiryDate": "2027-03-15",
      "QuantityAvailable": 30.0000,
      "WarehouseCode": "01"
    }
  ]
}
```

### `IProfitInventoryService.ExplodeBOM(bomCode, quantity)`
```json
// Request
{ "ArticleCode": "HAMB-PREM-01", "Quantity": 2.0 }
// Response
{
  "ArticleCode": "HAMB-PREM-01",
  "Components": [
    { "Code": "INS-PAN-BRIG", "Quantity": 2.0, "UOM": "UND", "Cost": 0.50 },
    { "Code": "INS-CARNE-200", "Quantity": 2.0, "UOM": "UND", "Cost": 3.20 },
    { "Code": "INS-QUESO-CH", "Quantity": 4.0, "UOM": "UND", "Cost": 0.30 }
  ],
  "TotalCost": 8.00
}
```

### `IProfitCatalogService.GetProducts(lastSyncDate)`
```json
// Request
{ "LastSyncDate": "2026-10-07T00:00:00", "IncludeInactive": false }
// Response
{
  "Products": [
    {
      "Code": "MED-LOSA-50",
      "Description": "Losartán 50mg Tab x30",
      "Barcode": "7501234567890",
      "Category": "FARMACIA",
      "SubCategory": "CARDIOVASCULAR",
      "Brand": "Calox",
      "ActiveIngredient": "Losartán Potásico",
      "Classification": "ethical",
      "PriceList1": 15.00,
      "PriceList2": 12.00,
      "Cost": 10.50,
      "TaxCode": "IVA-EX",
      "BaseUOM": "CAJA",
      "AlternateUOMs": [
        { "UOM": "BLISTER", "Factor": 10.0 },
        { "UOM": "TABLETA", "Factor": 100.0 }
      ],
      "IsActive": true,
      "LastModified": "2026-10-08T10:30:00"
    }
  ],
  "TotalRecords": 1,
  "HasMore": false
}
```

### `IProfitCatalogService.UpdatePrices(PriceUpdateDTO[])`
```json
// Request
{
  "Updates": [
    {
      "ArticleCode": "MED-LOSA-50",
      "PriceList1": 16.00,
      "Cost": 11.20,
      "EffectiveDate": "2026-10-08"
    }
  ]
}
// Response
{ "Updated": 1, "Failed": 0, "Errors": [] }
```

### `IProfitPaymentService.RegisterPayment(PaymentDTO)`
```json
{
  "InvoiceCode": "FAC-0001234",
  "PaymentDate": "2026-10-08T00:00:00",
  "Payments": [
    {
      "PaymentCode": "EFE-USD",
      "Amount": 50.00,
      "Currency": "US$",
      "ExchangeRate": 36.28500000,
      "Reference": "",
      "BankAccount": ""
    }
  ]
}
```

### `IProfitFiscalService.GetNextControlNumber(documentType)`
```json
// Request
{ "DocumentType": "FACT", "POSId": "CAJA01" }
// Response
{ "ControlNumber": "00-00012346", "Sequence": 12346 }
```

### `IProfitFiscalService.RegisterFiscalDocument(FiscalDocumentDTO)`
```json
{
  "DocumentType": "FACT",
  "InvoiceCode": "FAC-0001234",
  "ControlNumber": "00-00012345",
  "ZReportNumber": "Z-0456",
  "MachineSerial": "PNY-1234567",
  "FiscalDate": "2026-10-08",
  "TotalAmount": 53.21,
  "TaxableBase": 41.00,
  "TaxAmount": 6.56,
  "ExemptAmount": 4.10,
  "IGTFAmount": 1.55
}
```

---

## 7. Event Schemas (RabbitMQ)

### Topología del Broker

```mermaid
flowchart TD
    subgraph "Exchanges"
        EX1["pos.events<br/><i>type: topic</i>"]
        EX2["erp.events<br/><i>type: topic</i>"]
        EX3["sync.events<br/><i>type: topic</i>"]
        EX4["system.events<br/><i>type: fanout</i>"]
        DLX["dead.letter.exchange<br/><i>type: direct</i>"]
    end

    subgraph "Queues"
        Q1["restaurant.orders"]
        Q2["pharmacy.orders"]
        Q3["payment.processing"]
        Q4["product.sync"]
        Q5["stock.updates"]
        Q6["ftp.sync.tasks"]
        Q7["rate.updates"]
        Q8["fiscal.registration"]
        Q9["recipe.captures"]
        Q10["session.closings"]
        Q11["notifications"]
        Q12["audit.log"]
        Q13["dead.letter.queue"]
    end

    EX1 -->|"order.closed.restaurant"| Q1
    EX1 -->|"order.closed.pharmacy"| Q2
    EX1 -->|"payment.processed.*"| Q3
    EX1 -->|"order.cancelled.*"| Q1
    EX1 -->|"order.cancelled.*"| Q2

    EX2 -->|"product.updated"| Q4
    EX2 -->|"stock.changed.*"| Q5
    EX2 -->|"price.updated.*"| Q4

    EX3 -->|"ftp.sync.*"| Q6
    EX3 -->|"rate.update.*"| Q7
    EX3 -->|"fiscal.*"| Q8
    EX3 -->|"recipe.*"| Q9
    EX3 -->|"session.*"| Q10

    EX4 --> Q11
    EX4 --> Q12

    DLX -->|"dlq"| Q13

    Q1 -.->|"on failure after max retries"| DLX
    Q2 -.->|"on failure after max retries"| DLX
    Q3 -.->|"on failure after max retries"| DLX
```

### Event: `order.closed`
```json
{
  "event_id": "evt-7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "event_type": "order.closed",
  "timestamp": "2026-10-08T18:30:00.123Z",
  "tenant_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "correlation_id": "corr-uuid",
  "idempotency_key": "POS-2026-10-08-CAJA01-00045",
  "routing_key": "order.closed.restaurant",
  "payload": {
    "order_id": "POS/2026/10/08/0045",
    "business_type": "restaurant",
    "fiscal_control_number": "00-00012345",
    "exchange_rate": 36.28500000,
    "lines": ["..."],
    "payments": ["..."],
    "totals": {"...": "..."}
  }
}
```

### Event: `payment.processed`
```json
{
  "event_id": "evt-uuid",
  "event_type": "payment.processed",
  "timestamp": "2026-10-08T18:30:01Z",
  "tenant_id": "tenant-uuid",
  "routing_key": "payment.processed.pos",
  "payload": {
    "transaction_id": "tx-uuid",
    "payment_method": "TDD-BAN",
    "amount": 62.00,
    "currency": "VES",
    "reference": "0012",
    "profit_cobro_code": "TDD-BAN",
    "reconciled": false
  }
}
```

### Event: `product.price_updated`
```json
{
  "event_id": "evt-uuid",
  "event_type": "product.price_updated",
  "timestamp": "2026-10-08T03:00:00Z",
  "tenant_id": "tenant-uuid",
  "routing_key": "price.updated.ftp",
  "payload": {
    "source": "ftp_sync",
    "provider": "COBECA",
    "products_updated": 3450,
    "sample_changes": [
      {
        "product_code": "MED-LOSA-50",
        "old_price": 15.00,
        "new_price": 16.00,
        "change_pct": 6.67
      }
    ]
  }
}
```

### Event: `stock.low_alert`
```json
{
  "event_id": "evt-uuid",
  "event_type": "stock.low_alert",
  "timestamp": "2026-10-08T14:30:00Z",
  "tenant_id": "tenant-uuid",
  "routing_key": "stock.changed.low",
  "payload": {
    "product_code": "MED-AMOX-500",
    "product_name": "Amoxicilina 500mg",
    "warehouse": "01",
    "current_stock": 3.0,
    "minimum_stock": 10.0,
    "reorder_point": 20.0,
    "uom": "CAJA"
  }
}
```

### Event: `exchange_rate.updated`
```json
{
  "event_id": "evt-uuid",
  "event_type": "exchange_rate.updated",
  "timestamp": "2026-10-08T13:15:00Z",
  "tenant_id": "ALL",
  "routing_key": "rate.update.bcv",
  "payload": {
    "source": "bcv",
    "rates": [
      {"from": "USD", "to": "VES", "rate": 36.28500000},
      {"from": "EUR", "to": "VES", "rate": 39.45200000}
    ],
    "effective_date": "2026-10-08",
    "previous_rates": [
      {"from": "USD", "to": "VES", "rate": 36.10000000}
    ]
  }
}
```

### Event: `fiscal.control_number.reserved`
```json
{
  "event_id": "evt-uuid",
  "event_type": "fiscal.control_number.reserved",
  "timestamp": "2026-10-08T14:29:59Z",
  "tenant_id": "tenant-uuid",
  "routing_key": "fiscal.control_reserved",
  "payload": {
    "control_number": "00-00012345",
    "document_type": "FACT",
    "pos_id": "CAJA01",
    "reserved_by": "cajero03",
    "lock_key": "fiscal:tenant-uuid:CAJA01"
  }
}
```

---

## 8. Redis Cache Schemas

| Key Pattern | Type | TTL | Description |
|------------|------|-----|-------------|
| `{tenant}:stock:{product_code}` | Hash | 300s (5 min) | Stock by warehouse |
| `{tenant}:lots:{product_code}` | Sorted Set | 1800s (30 min) | Lots sorted by expiry timestamp |
| `{tenant}:rate:current:{currency}` | String (JSON) | 43200s (12 hrs) | Current exchange rate |
| `{tenant}:rate:history` | List | 604800s (7 days) | Rate history (last 7 days) |
| `{tenant}:session:{pos_id}` | Hash | 86400s (24 hrs) | Active POS session info |
| `{tenant}:product:{product_code}` | Hash | 3600s (1 hr) | Product details cache |
| `idemp:{tenant}:{idempotency_key}` | String | 86400s (24 hrs) | Idempotency guard |
| `lock:fiscal:{tenant}:{pos_id}` | String (NX) | 10s | Distributed lock for fiscal correlatives |
| `lock:stock:{tenant}:{product}:{lot}` | String (NX) | 5s | Optimistic lock for stock reservation |
| `{tenant}:payment_methods` | Hash | 86400s (24 hrs) | Payment method → Profit code mapping |

**Example Stock Cache:**
```
KEY: FARM_CENTRAL_01:stock:MED-LOSA-50
TYPE: Hash
FIELDS:
  warehouse_01: "45.0000"
  warehouse_02: "5.0000"
  total: "50.0000"
  uom: "CAJA"
  last_synced: "2026-10-08T14:25:00Z"
```

**Example Lots Cache:**
```
KEY: FARM_CENTRAL_01:lots:MED-LOSA-50
TYPE: Sorted Set
MEMBERS (score = expiry unix timestamp):
  Score: 1764547200  → Member: '{"lot":"L2025-Z99","qty":5.0,"wh":"01","exp":"2026-12-01"}'
  Score: 1773619200  → Member: '{"lot":"L2026A","qty":30.0,"wh":"01","exp":"2027-03-15"}'
  Score: 1782086400  → Member: '{"lot":"L2026B","qty":15.0,"wh":"01","exp":"2027-06-20"}'
```

---

## 9. Celery Workers & Tasks

| Worker | Task Name | Schedule | Concurrency | Queue | Description |
|--------|-----------|----------|-------------|-------|-------------|
| `ftp_sync_worker` | `tasks.ftp.sync_provider_catalog` | `0 2 * * *` (2:00 AM) | 1 (serial) | `ftp.sync.tasks` | Download + parse + update FTP catalogs per provider |
| `transaction_retry_worker` | `tasks.tx.retry_failed` | `*/5 * * * *` (every 5 min) | 2 | `restaurant.orders`, `pharmacy.orders` | Retry failed transactions with exponential backoff |
| `stock_sync_worker` | `tasks.stock.sync_active_products` | `*/5 * * * *` (every 5 min) | 3 | `stock.updates` | Sync stock from Profit → Redis for active products |
| `reconciliation_worker` | `tasks.payments.reconcile` | `0 22 * * *` (10:00 PM) | 1 | `payment.processing` | Cross-reference payment references with bank statements |
| `rate_update_worker` | `tasks.rates.fetch_bcv` | `0 8,13,16 * * *` (8AM, 1PM, 4PM) | 1 | `rate.updates` | Fetch BCV rate, update Redis + Profit + Odoo |
| `lot_expiry_worker` | `tasks.pharmacy.check_expiring_lots` | `0 6 * * 1` (Mon 6 AM) | 1 | `notifications` | Alert on lots expiring within 30/60/90 days |
| `catalog_sync_worker` | `tasks.catalog.full_sync` | `0 3 * * 0` (Sun 3 AM) | 1 | `product.sync` | Full catalog reconciliation Profit → Odoo |
| `dead_letter_worker` | `tasks.dlq.process` | `*/15 * * * *` (every 15 min) | 1 | `dead.letter.queue` | Process DLQ, alert admins, attempt recovery |
| `session_closing_worker` | `tasks.sessions.process_closing` | On-demand | 2 | `session.closings` | Process POS session closings → Profit |

**Retry Policy (Exponential Backoff):**
```python
RETRY_POLICY = {
    "max_retries": 5,
    "backoff_base_seconds": 60,
    "backoff_multiplier": 2,
    "backoff_max_seconds": 3600,
    # Retry 1: 60s, Retry 2: 120s, Retry 3: 240s, Retry 4: 480s, Retry 5: 960s
    # After retry 5: → Dead Letter Queue
}
```

---

## 10. Seguridad

### JWT Token Structure
```json
{
  "sub": "user-uuid-12345",
  "tenant_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "tenant_code": "FARM_CENTRAL_01",
  "roles": ["TenantAdmin", "POSClient"],
  "permissions": [
    "transactions:write",
    "products:read",
    "payments:write",
    "ftp:trigger",
    "reports:read"
  ],
  "pos_id": "CAJA01",
  "iat": 1696780200,
  "exp": 1696866600,
  "iss": "profit2k12-odoo-middleware",
  "aud": "pos-client"
}
```

### OAuth2 Scopes

| Scope | Description |
|-------|-------------|
| `tenants:manage` | Create, update, delete tenants |
| `transactions:read` | View transactions |
| `transactions:write` | Create transactions |
| `transactions:retry` | Retry failed transactions |
| `products:read` | View products and stock |
| `products:sync` | Trigger catalog sync |
| `payments:write` | Process payments |
| `payments:reconcile` | Reconcile payments |
| `ftp:trigger` | Trigger FTP sync |
| `ftp:read` | View FTP sync status |
| `rates:write` | Update exchange rates |
| `rates:read` | View exchange rates |
| `pharmacy:recipes` | Capture medical recipes |
| `pharmacy:lots` | View lot information |
| `admin:queues` | View queue status |
| `admin:audit` | View audit logs |

### RBAC Matrix

| Role | tenants | transactions | products | payments | ftp | rates | pharmacy | restaurant | admin |
|------|---------|-------------|----------|----------|-----|-------|----------|------------|-------|
| **SuperAdmin** | CRUD | RW + Retry | R + Sync | RW + Reconcile | RW | RW | All | All | All |
| **TenantAdmin** | R (own) | RW + Retry | R + Sync | RW + Reconcile | RW | R | All | All | R (queues) |
| **POSClient** | — | W | R | W | — | R | Recipes + Lots | Orders | — |
| **Viewer** | R (own) | R | R | R | R | R | R | R | — |
| **FTPWorker** (system) | — | — | Sync | — | RW | — | — | — | — |
| **RateWorker** (system) | — | — | — | — | — | RW | — | — | — |

### Rate Limiting (per tenant)

| Endpoint Group | Limit |
|---------------|-------|
| `/api/v1/{t}/transactions` (POST) | 100 req/min |
| `/api/v1/{t}/products/*` (GET) | 300 req/min |
| `/api/v1/{t}/payments/*` | 100 req/min |
| `/api/v1/{t}/ftp/sync/trigger` | 5 req/hour |
| `/api/v1/{t}/exchange-rates` (POST) | 10 req/hour |
| `/health`, `/metrics` | No limit |

---

## 11. Docker Compose

```yaml
version: '3.8'

services:
  # === API Gateway ===
  nginx:
    image: nginx:1.25-alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./docker/nginx.conf:/etc/nginx/conf.d/default.conf:ro
      - ./docker/ssl:/etc/nginx/ssl:ro
    depends_on:
      api:
        condition: service_healthy
    networks:
      - frontend
    restart: unless-stopped

  # === FastAPI Application ===
  api:
    build:
      context: .
      dockerfile: docker/Dockerfile.api
    environment:
      - APP_ENV=${APP_ENV:-production}
      - DATABASE_URL=postgresql+asyncpg://${DB_USER}:${DB_PASSWORD}@postgres:5432/${DB_NAME}
      - REDIS_URL=redis://redis:6379/0
      - CELERY_BROKER_URL=amqp://${MQ_USER}:${MQ_PASSWORD}@rabbitmq:5672//
      - JWT_SECRET_KEY=${JWT_SECRET_KEY}
      - JWT_ALGORITHM=HS256
      - LOG_LEVEL=${LOG_LEVEL:-INFO}
      - LOG_FORMAT=json
    ports:
      - "8000:8000"
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
      rabbitmq:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 15s
      timeout: 5s
      retries: 3
      start_period: 10s
    networks:
      - frontend
      - backend
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 512M

  # === Celery Workers ===
  worker-transactions:
    build:
      context: .
      dockerfile: docker/Dockerfile.worker
    command: celery -A src.workers.celery_app worker -Q restaurant.orders,pharmacy.orders,payment.processing,session.closings -c 4 --loglevel=info
    environment:
      - DATABASE_URL=postgresql+asyncpg://${DB_USER}:${DB_PASSWORD}@postgres:5432/${DB_NAME}
      - REDIS_URL=redis://redis:6379/0
      - CELERY_BROKER_URL=amqp://${MQ_USER}:${MQ_PASSWORD}@rabbitmq:5672//
      - PROFIT_WCF_BASE_URL=${PROFIT_WCF_BASE_URL}
      - PROFIT_WCF_TIMEOUT=${PROFIT_WCF_TIMEOUT:-30}
      - LOG_LEVEL=${LOG_LEVEL:-INFO}
      - LOG_FORMAT=json
    depends_on:
      - rabbitmq
      - redis
      - postgres
    networks:
      - backend
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 1G

  worker-sync:
    build:
      context: .
      dockerfile: docker/Dockerfile.worker
    command: celery -A src.workers.celery_app worker -Q ftp.sync.tasks,product.sync,stock.updates,rate.updates -c 2 --loglevel=info
    environment:
      - DATABASE_URL=postgresql+asyncpg://${DB_USER}:${DB_PASSWORD}@postgres:5432/${DB_NAME}
      - REDIS_URL=redis://redis:6379/0
      - CELERY_BROKER_URL=amqp://${MQ_USER}:${MQ_PASSWORD}@rabbitmq:5672//
      - LOG_LEVEL=${LOG_LEVEL:-INFO}
      - LOG_FORMAT=json
    depends_on:
      - rabbitmq
      - redis
      - postgres
    networks:
      - backend
    restart: unless-stopped

  worker-dlq:
    build:
      context: .
      dockerfile: docker/Dockerfile.worker
    command: celery -A src.workers.celery_app worker -Q dead.letter.queue,notifications,audit.log -c 1 --loglevel=info
    environment:
      - DATABASE_URL=postgresql+asyncpg://${DB_USER}:${DB_PASSWORD}@postgres:5432/${DB_NAME}
      - REDIS_URL=redis://redis:6379/0
      - CELERY_BROKER_URL=amqp://${MQ_USER}:${MQ_PASSWORD}@rabbitmq:5672//
      - LOG_LEVEL=${LOG_LEVEL:-INFO}
      - LOG_FORMAT=json
    depends_on:
      - rabbitmq
      - redis
      - postgres
    networks:
      - backend
    restart: unless-stopped

  # === Celery Beat (Scheduler) ===
  beat:
    build:
      context: .
      dockerfile: docker/Dockerfile.worker
    command: celery -A src.workers.celery_app beat --loglevel=info
    environment:
      - DATABASE_URL=postgresql+asyncpg://${DB_USER}:${DB_PASSWORD}@postgres:5432/${DB_NAME}
      - REDIS_URL=redis://redis:6379/0
      - CELERY_BROKER_URL=amqp://${MQ_USER}:${MQ_PASSWORD}@rabbitmq:5672//
    depends_on:
      - rabbitmq
    networks:
      - backend
    restart: unless-stopped

  # === PostgreSQL (Middleware DB) ===
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: ${DB_USER:-middleware}
      POSTGRES_PASSWORD: ${DB_PASSWORD:-middleware_secret}
      POSTGRES_DB: ${DB_NAME:-middleware_db}
    volumes:
      - pgdata:/var/lib/postgresql/data
      - ./migrations/init.sql:/docker-entrypoint-initdb.d/01-init.sql:ro
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DB_USER:-middleware} -d ${DB_NAME:-middleware_db}"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - backend
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 512M

  # === Redis ===
  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes --maxmemory 256mb --maxmemory-policy allkeys-lru
    volumes:
      - redisdata:/data
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - backend
    restart: unless-stopped

  # === RabbitMQ ===
  rabbitmq:
    image: rabbitmq:3.12-management-alpine
    environment:
      RABBITMQ_DEFAULT_USER: ${MQ_USER:-middleware}
      RABBITMQ_DEFAULT_PASS: ${MQ_PASSWORD:-middleware_secret}
      RABBITMQ_DEFAULT_VHOST: /
    ports:
      - "5672:5672"
      - "15672:15672"
    volumes:
      - mqdata:/var/lib/rabbitmq
      - ./docker/rabbitmq-definitions.json:/etc/rabbitmq/definitions.json:ro
    healthcheck:
      test: ["CMD", "rabbitmq-diagnostics", "check_port_connectivity"]
      interval: 15s
      timeout: 10s
      retries: 5
      start_period: 30s
    networks:
      - backend
    restart: unless-stopped

volumes:
  pgdata:
    driver: local
  redisdata:
    driver: local
  mqdata:
    driver: local

networks:
  frontend:
    driver: bridge
  backend:
    driver: bridge
```

---

## 12. Configuración de Entorno (`.env.example`)

```env
# ============================================================
# profit2k12-odoo-middleware — Environment Configuration
# ============================================================

# === APPLICATION ===
APP_ENV=development                    # development | staging | production
APP_DEBUG=true
API_HOST=0.0.0.0
API_PORT=8000
API_WORKERS=4                          # uvicorn workers (production: CPU cores × 2 + 1)
LOG_LEVEL=INFO                         # DEBUG | INFO | WARNING | ERROR
LOG_FORMAT=json                        # json | text

# === DATABASE (Middleware PostgreSQL) ===
DB_USER=middleware
DB_PASSWORD=CHANGE_ME_IN_PRODUCTION
DB_NAME=middleware_db
DB_HOST=postgres
DB_PORT=5432
DATABASE_URL=postgresql+asyncpg://${DB_USER}:${DB_PASSWORD}@${DB_HOST}:${DB_PORT}/${DB_NAME}
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=10

# === REDIS ===
REDIS_URL=redis://redis:6379/0
REDIS_MAX_CONNECTIONS=50

# === RABBITMQ ===
MQ_USER=middleware
MQ_PASSWORD=CHANGE_ME_IN_PRODUCTION
MQ_HOST=rabbitmq
MQ_PORT=5672
CELERY_BROKER_URL=amqp://${MQ_USER}:${MQ_PASSWORD}@${MQ_HOST}:${MQ_PORT}//
CELERY_RESULT_BACKEND=redis://redis:6379/1

# === SECURITY ===
JWT_SECRET_KEY=CHANGE_ME_TO_A_RANDOM_256BIT_KEY
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440       # 24 hours
CORS_ALLOWED_ORIGINS=https://odoo.example.com,https://admin.example.com

# === PROFIT PLUS WCF (defaults, overridden per tenant) ===
PROFIT_WCF_BASE_URL=http://192.168.1.100:8080/ProfitWCF/Services
PROFIT_WCF_TIMEOUT=30                  # seconds
PROFIT_WCF_MAX_RETRIES=3

# === ODOO (defaults, overridden per tenant) ===
ODOO_DEFAULT_URL=https://odoo.example.com
ODOO_DEFAULT_DB=odoo_prod

# === FTP (defaults) ===
FTP_DEFAULT_TIMEOUT=30
FTP_DEFAULT_PASSIVE_MODE=true
FTP_DOWNLOAD_DIR=/tmp/ftp_downloads

# === BCV EXCHANGE RATE ===
BCV_SCRAPER_URL=https://www.bcv.org.ve
BCV_FALLBACK_API=https://api.exchangerate.host/latest
BCV_FETCH_SCHEDULE=0 8,13,16 * * *    # 8AM, 1PM, 4PM

# === MONITORING ===
SENTRY_DSN=
PROMETHEUS_ENABLED=true
ELK_HOST=elasticsearch:9200

# === NOTIFICATIONS ===
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
SMTP_HOST=
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
ALERT_EMAIL=admin@example.com
```

---

## 13. Mitigación de Riesgos Técnicos (Unknown Unknowns)

> [!CAUTION]
> El entorno retail venezolano es volátil: infraestructura eléctrica y de internet inestable, regulaciones fiscales que cambian con poco aviso, y reconversiones monetarias impredecibles. Cada riesgo listado abajo tiene una probabilidad **real** de ocurrencia.

### 13.1 Latencia SOAP/WCF vs REST/JSON

**Riesgo:** Las llamadas WCF/SOAP son inherentemente más lentas que REST (serialización XML, handshake, headers SOAP). Un `CreateInvoice` puede tomar 500ms-2s en condiciones normales, y 5-10s bajo carga.

**Mitigación:**
- Todas las escrituras a Profit son **asíncronas** (via RabbitMQ). El POS nunca espera por Profit.
- Las lecturas de stock usan **Redis cache** (< 5ms).
- Pool de conexiones `zeep` con keep-alive para reusar sesiones HTTP subyacentes.
- Timeout estricto de 30s en WCF; si excede, va a retry queue.
- Circuit breaker pattern: si Profit falla 3 veces consecutivas, deja de intentar por 5 minutos y alerta.

### 13.2 Concurrencia en Correlativos Fiscales (Race Conditions)

**Riesgo:** Dos cajas solicitando el siguiente Nro. de Control simultáneamente pueden obtener el mismo número, creando un duplicado fiscal ilegal.

**Mitigación:**
- Distributed lock en Redis: `SET lock:fiscal:{tenant}:{pos_id} {uuid} NX EX 10`
- Solo un thread puede reservar un correlativo a la vez por POS.
- El correlativo se reserva **antes** de imprimir la factura fiscal.
- Si la impresión falla, el correlativo se marca como "void" (anulado) — los huecos en correlativos son legales, los duplicados no.

### 13.3 Timeout en WCF durante Explosión BOM Compleja

**Riesgo:** Una receta con 20+ ingredientes (ej. un buffet o menú ejecutivo con múltiples platos) puede causar timeout en el WCF de Profit al explotar todos los BOMs.

**Mitigación:**
- Pre-caché de recetas frecuentes en Redis.
- Si la explosión BOM toma > 10s, el Worker la divide en batches de 5 platos.
- Fallback: si WCF timeout, el Worker envía las líneas planas (sin explosión) y marca la transacción para `manual_bom_explosion` en Profit por el usuario.

### 13.4 Inconsistencia de Stock por Caché Stale

**Riesgo:** Redis muestra 5 unidades, pero Profit ya las vendió por otro canal (venta directa en Profit, otro POS). El cajero vende un producto inexistente.

**Mitigación:**
- TTL agresivo: 5 minutos para stock (no más).
- Al procesar la venta, el Worker **verifica stock en Profit** en tiempo real antes de confirmar.
- Si Profit rechaza por stock insuficiente, la transacción va a `failed` con error `STOCK_INSUFFICIENT` y se notifica al cajero.
- Write-through: cada venta exitosa descuenta del caché Redis inmediatamente.
- Reconciliación nocturna: cron que compara Redis vs. Profit y corrige.

### 13.5 Reconversión Monetaria Mid-Flight

**Riesgo:** El BCV anuncia una reconversión (ej. eliminar 6 ceros) con 2 semanas de aviso. Todas las transacciones en tránsito deben convertirse.

**Mitigación:**
- Cada transacción almacena `currency_era` (VEB, VEF, VES, VED).
- El Middleware tiene un `ReconversionService` con `conversion_factor` y `effective_date`.
- Las transacciones creadas antes de la reconversión se procesan con la era original.
- Las transacciones después se procesan con la nueva era.
- Feature flag `RECONVERSION_ACTIVE=true` + `RECONVERSION_FACTOR=1000000` + `RECONVERSION_DATE=2026-10-01`.

### 13.6 Pérdida de Conectividad FTP de Droguerías

**Riesgo:** El FTP de COBECA está caído el día de la sincronización. No se actualizan precios.

**Mitigación:**
- Reintentos: 3 intentos con 30 min entre cada uno.
- Si falla, alerta al administrador.
- La última sincronización exitosa sigue vigente (no se borran datos anteriores).
- Log detallado en `ftp_sync_log` con `file_hash` para detectar archivos truncados.

### 13.7 Incompatibilidad de Encodings (CP1252 vs UTF-8)

**Riesgo:** Los archivos FTP de droguerías venezolanas usan CP1252 (Windows). Si se leen como UTF-8, los caracteres `ñ`, `á`, `é`, `ó` se corrompen. Un producto llamado "Ibuprofeno 400mg Cápsulas" aparece como "Ibuprofeno 400mg C\xc3\xa1psulas".

**Mitigación:**
- Cada `ftp_parser` tiene `encoding` configurable por proveedor.
- Auto-detect con `chardet` como fallback.
- Validación post-parse: si el nombre contiene bytes inválidos para el encoding declarado, marca como error.
- Todos los datos se almacenan en UTF-8 en PostgreSQL.

### 13.8 Límites de Payload en WCF

**Riesgo:** Profit WCF tiene un límite default de payload (64KB en `maxReceivedMessageSize`). Una factura con 50+ líneas puede excederlo.

**Mitigación:**
- El adaptador WCF verifica el tamaño del payload antes de enviar.
- Si excede 50KB, divide en lotes (aunque esto es raro en retail).
- Recomendación: que el equipo de infraestructura aumente `maxReceivedMessageSize` a 1MB en `web.config` de Profit WCF.

### 13.9 Deadlocks en SQL Server de Profit

**Riesgo:** Dos Workers actualizando el mismo artículo simultáneamente (ej. dos cajas vendiendo el mismo producto) pueden causar deadlock en SQL Server.

**Mitigación:**
- Las colas de transacciones críticas (`restaurant.orders`, `pharmacy.orders`) usan `concurrency=1` por tenant (serialización).
- Para alto volumen, usar concurrencia pero con `SELECT ... WITH (UPDLOCK, ROWLOCK)` en los stored procedures de Profit.
- El Worker implementa retry automático en `deadlock_detected` (error 1205 de SQL Server), hasta 3 intentos.

### 13.10 Drift de Reloj entre Sistemas

**Riesgo:** Odoo dice 14:30:00, el Middleware dice 14:30:05, Profit dice 14:29:55. Diferencias de reloj causan problemas en auditoría y ordenamiento temporal.

**Mitigación:**
- Todos los servidores usan NTP sincronizado.
- El Middleware es la fuente de verdad temporal: `created_at` siempre se genera en el Middleware, no se confía en el timestamp de Odoo ni de Profit.
- Tolerancia de ±30 segundos para ordenamiento.
- Todos los timestamps internos son UTC; la conversión a `America/Caracas` solo se hace en la capa de presentación.

### 13.11 Saturación de RabbitMQ en Hora Pico

**Riesgo:** 10 cajas generando 500 transacciones en 2 horas pueden saturar las colas si los Workers están lentos.

**Mitigación:**
- Monitoreo: alerta si `messages_ready > 50` en cualquier cola.
- Auto-scaling: en Kubernetes, HPA escala Workers cuando la cola supera umbral.
- Backpressure: si la cola supera 200 mensajes, el API retorna `503 Service Unavailable` temporalmente en endpoints no críticos.
- Las colas tienen `x-max-length: 10000` con política `reject-publish` para evitar OOM.

### 13.12 Corrupción de Datos por Falta de Transacciones Atómicas

**Riesgo:** El Worker escribe en el Middleware DB, pero falla al enviar a Profit WCF. El estado queda inconsistente.

**Mitigación:**
- Patrón Outbox: la transacción se marca como `processing` en el Middleware DB dentro de una transacción atómica.
- Si el WCF falla, el estado se revierte a `failed` con el error.
- Si el Worker crashea, el mensaje permanece en RabbitMQ (no se hace ACK hasta confirmar éxito completo).
- Idempotencia: si el Worker se reinicia y reprocesa, la `idempotency_key` previene duplicados.

---

## 14. Testing Strategy

### Unit Tests (pytest + pytest-asyncio)
```python
# tests/unit/test_uom_service.py
import pytest
from decimal import Decimal
from src.core.services.uom_service import UoMService

class TestUoMConversion:
    def test_blister_to_caja(self):
        """1 BLISTER = 0.1 CAJA (factor = 10)"""
        service = UoMService()
        result = service.convert(
            quantity=Decimal("3.0"),
            from_uom="BLISTER",
            to_uom="CAJA",
            factor=Decimal("10.0")
        )
        assert result == Decimal("0.30000000")

    def test_tableta_to_caja_precision(self):
        """99 TABLETAS = 0.99 CAJA, not 0.989999..."""
        service = UoMService()
        result = service.convert(
            quantity=Decimal("99"),
            from_uom="TABLETA",
            to_uom="CAJA",
            factor=Decimal("100.0")
        )
        assert result == Decimal("0.99000000")

    def test_igtf_calculation(self):
        """IGTF 3% on USD payment"""
        service = UoMService()  # or PaymentService
        usd_amount = Decimal("50.00")
        igtf_rate = Decimal("3.0")
        igtf = (usd_amount * igtf_rate / Decimal("100")).quantize(Decimal("0.01"))
        assert igtf == Decimal("1.50")
```

### Integration Tests (testcontainers)
```python
# tests/integration/conftest.py
import pytest
from testcontainers.postgres import PostgresContainer
from testcontainers.redis import RedisContainer

@pytest.fixture(scope="session")
def postgres_container():
    with PostgresContainer("postgres:15-alpine") as pg:
        yield pg

@pytest.fixture(scope="session")
def redis_container():
    with RedisContainer("redis:7-alpine") as redis:
        yield redis
```

### Contract Tests for WCF
```python
# tests/integration/test_profit_wcf_adapter.py
class TestProfitWCFContract:
    """Validates that our SOAP serialization matches Profit's expected schema."""

    def test_create_invoice_xml_matches_xsd(self, wcf_adapter, sample_invoice):
        """Serialize an invoice and validate against Profit's XSD."""
        xml_output = wcf_adapter.serialize_invoice(sample_invoice)
        assert validate_xsd(xml_output, "fixtures/wcf_responses/invoice.xsd")

    def test_handle_wcf_fault(self, wcf_adapter):
        """Ensure WCF SOAP faults are properly parsed."""
        with open("tests/fixtures/wcf_responses/stock_insufficient_fault.xml") as f:
            fault_xml = f.read()
        result = wcf_adapter.parse_response(fault_xml)
        assert result.success is False
        assert result.error_code == "STOCK_INSUFFICIENT"
```

### Factories (factory_boy)
```python
# tests/factories/transaction_factory.py
import factory
from src.core.entities.transaction import Transaction

class TransactionFactory(factory.Factory):
    class Meta:
        model = Transaction

    tenant_id = factory.LazyFunction(uuid4)
    source_system = "odoo"
    transaction_type = "pos_invoice"
    idempotency_key = factory.Sequence(lambda n: f"POS-2026-10-08-CAJA01-{n:05d}")
    status = "pending"
    business_type = "pharmacy"
    payload = factory.LazyFunction(lambda: {
        "lines": [{"product_code": "MED-001", "quantity": 1.0, "price": 10.0}],
        "payments": [{"method": "EFE-VES", "amount": 11.60, "currency": "VES"}]
    })
```

---

*Fin del SRS & Architecture Blueprint — v1.0.0*  
*Diseñado para generación de código por Antigravity IDE*  
*Última actualización: Octubre 2026*
