
from .utilities import (
    INVENTORY_DB,
    create_inventory_skins_table_db,
    create_transactions_table_db,
    remove_inventory_skins_table_db,
    add_inventory_skins_table_db,
    insert_transaction_transactions_table_db,
    load_all_inventory_skins_table_db,
    get_current_balance_transactions_table_db,
    get_price_float_buckets_skin_data_db,
    remove_transaction_transactions_table_db,
    SKIN_DATA_DB,
    InventoryItemOut,
    InventoryItemIn,
    TransactionEntry
)
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from math import floor

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

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
            id_=item[0],
            skin_name=item[1],
            float_val=item[2],
            purchase_price=item[3],
            recorded_at=item[4],
            expected_sale_price=current_value,
            profit=profit
        ))
    return result

@app.post("/inventory")
def add_inventory_item(item: InventoryItemIn):
    add_inventory_skins_table_db(item.skin_name, item.float_val, item.purchase_price, INVENTORY_DB)
    return {"status": "added"}

@app.delete("/inventory/{item_id}")
def delete_inventory_item(item_id: int):
    delete_state = remove_inventory_skins_table_db(item_id, INVENTORY_DB)
    if delete_state:
        return {"status": "deleted"}
    else:
        return {"status": "not deleted"}

@app.get("/transactions/balance")
def get_transaction_balance():
    transaction_balance = get_current_balance_transactions_table_db(INVENTORY_DB)
    return transaction_balance

@app.post("/transactions")
def add_transaction_entry(transaction: TransactionEntry):
    insert_transaction_transactions_table_db(transaction.transaction_type, transaction.transaction_value, transaction.transaction_details, INVENTORY_DB)
    return {"status": "added"}

@app.delete("/transactions/{transaction_id}")
def remove_transaction_entry(transaction_id: int):
    remove_state = remove_transaction_transactions_table_db(transaction_id, INVENTORY_DB)
    if remove_state:
        return {"status": "deleted"}
    else:
        return {"status": "not deleted"}

if __name__  == "__main__":
    print(get_inventory())
