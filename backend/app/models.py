from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class PricingItem(BaseModel):
    region: str
    product: str
    billing_unit: str
    billed_annually: Optional[str] = None
    billed_month_to_month: Optional[str] = None
    on_demand: Optional[str] = None


class AllotmentInfo(BaseModel):
    allotted_product: str
    quantity_included: int
    allotted_unit: str


class QuoteLineItem(BaseModel):
    product: str
    billing_unit: str
    quantity: int
    unit_price: float
    total_price: float
    is_allotment: bool = False
    allotments: list[AllotmentInfo] = []


class Quote(BaseModel):
    id: str
    name: Optional[str] = None
    billing_type: str  # 'annually', 'monthly', 'on_demand'
    items: list[QuoteLineItem]
    total: float
    created_at: str
    updated_at: str


class QuoteCreate(BaseModel):
    name: Optional[str] = None
    billing_type: str
    items: list[dict]


class SyncResponse(BaseModel):
    success: bool
    message: str
    products_count: int

