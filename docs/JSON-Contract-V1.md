# Contrato JSON Universal (Odoo ↔ Middleware ↔ Profit Plus 2k12)

Este contrato ha sido diseñado tomando en cuenta los hallazgos de los 5 agentes especialistas durante el Gap Analysis, asegurando:
1. **Idempotencia y Trazabilidad:** Uso de `correlation_id` y `odoo_pos_reference`.
2. **Auditoría Estricta:** Inyección del `cashier_id` para mapeo con `co_us_in` en Profit.
3. **Mitigación de Coma Flotante:** Uso de montos crudos (raw) y estampa de `exchange_rate_applied`.
4. **Resiliencia Offline:** Estampa de la fecha de emisión original (`fec_emis`).
5. **Cero Texto Libre:** Justificaciones tabuladas y motivos estructurados.

## Payload de Venta / Devolución (POS Order)

```json
{
  "metadata": {
    "tenant_id": "tenant_001",
    "correlation_id": "550e8400-e29b-41d4-a716-446655440000",
    "source": "odoo_pos",
    "timestamp": "2026-10-08T03:45:00Z"
  },
  "session": {
    "session_id": "sess_09876",
    "cashier_id": "user_456",
    "offline_mode_flag": true
  },
  "transaction": {
    "order_id": "ord_10293",
    "odoo_pos_reference": "POS-001-00056",
    "type": "invoice", // "invoice" | "refund"
    "refunded_order_id": null, // Requerido si type == "refund"
    "refund_reason_code": null, // Sin texto libre, código tabulado
    "fec_emis": "2026-10-08T03:15:00Z", // Fecha original de la operación
    "exchange_rate_applied": 38.50
  },
  "lines": [
    {
      "line_id": "line_1",
      "product_id": "prod_789", // Se mapeará a co_art en Profit
      "qty": 2.000,
      "uom_code": "PZA",
      "unit_price_raw_ves": 150.00,
      "is_tip": false,
      "tax_ids": ["tax_iva_16"]
    },
    {
      "line_id": "line_2",
      "product_id": "TIP_ID",
      "qty": 1.000,
      "uom_code": "SRV",
      "unit_price_raw_ves": 15.00,
      "is_tip": true, // Dispara inserción a cuenta de Pasivo / Servicio Exento
      "tax_ids": ["tax_exempt"]
    }
  ],
  "taxes_summary": {
    "base_imponible_usd": 4.28,
    "base_imponible_ves": 165.00,
    "monto_iva_ves": 24.00,
    "monto_igtf_ves": 5.10
  },
  "payments": [
    {
      "payment_id": "pay_001",
      "method_id": "pm_usd_cash", // Dispara el cálculo del IGTF
      "amount_raw_usd": 4.28,
      "amount_raw_ves": 165.00,
      "reference_code": "CASH"
    },
    {
      "payment_id": "pay_002",
      "method_id": "pm_pago_movil",
      "amount_raw_usd": 0.00,
      "amount_raw_ves": 29.10,
      "reference_code": "0102-12345678" // Referencia bancaria obligatoria
    }
  ]
}
```

## Flujo de Procesamiento Esperado
1. **Odoo** encola este JSON en RabbitMQ al momento del pago (o en ráfaga si estaba Offline).
2. **Middleware Python** valida el esquema, convierte los IDs y delega a un *Worker*.
3. **Servicio WCF** recibe el JSON estructurado, valida correlativos, y asienta el registro en `factura`, `reng_fac`, `cobros` y `mov_caj` con `fec_emis` estricta y mapeando al usuario nativo de Profit.
