from .utilities import (
    INVENTORY_DB,
    create_inventory_skins_table_db,
    remove_inventory_skins_table_db,
    add_inventory_skins_table_db,
    load_all_inventory_skins_table_db,
    get_price_float_buckets_skin_data_db,
    SKIN_DATA_DB,
    InventoryItemOut,
    InventoryItemIn
)
from fastapi import FastAPI
from math import floor

app = FastAPI()

def compute_current_value(skin_name: str, float_val: float) -> float:
    """Reuses your existing float_prices baseline table."""
    buckets = get_price_float_buckets_skin_data_db(skin_name, SKIN_DATA_DB)
    bucket_index = int(floor(float_val * 100))
    return buckets.get(bucket_index, 0.0)

@app.get("/inventory", response_model=list[InventoryItemOut])
def get_inventory():
    skins = load_all_inventory_skins_table_db(INVENTORY_DB)
    result = []
    for item in skins:
        current_value = compute_current_value(item[1], item[2])
        profit = round(current_value - item[3], 2)
        result.append(InventoryItemOut(
            **item,
            expected_sale_price=current_value,
            profit=profit
        ))
    return result

@app.post("/inventory")
def add_inventory_item(item: InventoryItemIn):
    add_inventory_skins_table_db(item.skin_name, item.float_val, item.purchase_price, INVENTORY_DB)
    return {"status": "added"}

@app.delete("/inventory/{item_id}")
def delete_inventory_item(item_id: str):
    remove_inventory_skins_table_db(item_id, INVENTORY_DB)
    return {"status": "deleted"}

if __name__  == "__main__":
    create_inventory_skins_table_db(INVENTORY_DB)
