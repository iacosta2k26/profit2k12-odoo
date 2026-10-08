from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class Metadata(BaseModel):
    tenant_id: str
    correlation_id: str
    source: str
    timestamp: datetime

class SessionInfo(BaseModel):
    session_id: str
    cashier_id: str
    offline_mode_flag: bool

class Transaction(BaseModel):
    order_id: str
    odoo_pos_reference: str
    type: str
    refunded_order_id: Optional[str] = None
    refund_reason_code: Optional[str] = None
    fec_emis: datetime
    exchange_rate_applied: float

class OrderLine(BaseModel):
    line_id: str
    product_id: str
    qty: float
    uom_code: str
    unit_price_raw_ves: float
    is_tip: bool
    tax_ids: List[str]

class TaxesSummary(BaseModel):
    base_imponible_usd: float
    base_imponible_ves: float
    monto_iva_ves: float
    monto_igtf_ves: float

class Payment(BaseModel):
    payment_id: str
    method_id: str
    amount_raw_usd: float
    amount_raw_ves: float
    reference_code: str

class PosOrderPayload(BaseModel):
    metadata: Metadata
    session: SessionInfo
    transaction: Transaction
    lines: List[OrderLine]
    taxes_summary: TaxesSummary
    payments: List[Payment]
