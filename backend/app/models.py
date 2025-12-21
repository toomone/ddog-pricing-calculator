from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class PricingItem(BaseModel):
    id: Optional[str] = None
    region: str
    product: str
    plan: str = "All"  # 'Pro', 'Enterprise', or 'All' (available to all plans)
    billing_unit: str
    billed_annually: Optional[str] = None
    billed_month_to_month: Optional[str] = None
    on_demand: Optional[str] = None


class AllotmentInfo(BaseModel):
    id: Optional[str] = None
    allotted_product: str
    quantity_included: int
    allotted_unit: str


class QuoteLineItem(BaseModel):
    id: Optional[str] = None
    product: str
    billing_unit: str
    quantity: int
    unit_price: float  # Price for selected billing type
    total_price: float  # Total for selected billing type
    # Prices for all billing types
    unit_price_annually: Optional[float] = None
    unit_price_monthly: Optional[float] = None
    unit_price_on_demand: Optional[float] = None
    total_price_annually: Optional[float] = None
    total_price_monthly: Optional[float] = None
    total_price_on_demand: Optional[float] = None
    is_allotment: bool = False
    allotments: list[AllotmentInfo] = []


class Quote(BaseModel):
    id: str
    name: Optional[str] = None
    region: str = "us"  # Datadog region
    billing_type: str  # 'annually', 'monthly', 'on_demand'
    items: list[QuoteLineItem]
    total: float
    total_annually: Optional[float] = None  # For savings comparison
    total_monthly: Optional[float] = None
    total_on_demand: Optional[float] = None
    created_at: str
    updated_at: str
    # Password protection for editing
    edit_password_hash: Optional[str] = None  # bcrypt hash, None means no protection
    is_protected: bool = False  # Convenience flag for frontend


class QuoteCreate(BaseModel):
    name: Optional[str] = None
    region: str = "us"
    billing_type: str
    items: list[dict]
    edit_password: Optional[str] = None  # Plain text password, will be hashed


class QuoteUpdate(BaseModel):
    name: Optional[str] = None
    region: str = "us"
    billing_type: str
    items: list[dict]
    edit_password: Optional[str] = None  # Required if quote is protected


class VerifyPasswordRequest(BaseModel):
    password: str


class VerifyPasswordResponse(BaseModel):
    valid: bool
    message: str


class SyncResponse(BaseModel):
    success: bool
    message: str
    products_count: int

