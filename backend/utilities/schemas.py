from pydantic import BaseModel

class InventoryItemIn(BaseModel):
    skin_name: str
    float_val: float
    purchase_price: float

class InventoryItemOut(BaseModel):
    id_: int
    skin_name: str
    float_val: float
    purchase_price: float
    recorded_at: str
    expected_sale_price: float
    profit: float

class TransactionEntry(BaseModel):
    transaction_type: str
    transaction_value: float
    transaction_details: str