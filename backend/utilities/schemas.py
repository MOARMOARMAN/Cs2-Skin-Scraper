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