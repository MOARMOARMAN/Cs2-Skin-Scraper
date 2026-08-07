from backend.batch import (
    calculate_overpay_percentages
)
from backend.utilities import (
    listingData
)
import pytest
from unittest.mock import patch

@patch("backend.batch.get_price_float_buckets_skin_data_db")
def test_calculate_overpay_percentages(mock_get_db):
    mock_get_db.return_value = {
        1:20.0,
        2:18.0,
    }

    skin_name = "AK-47 | Ice Coaled"
    skin_listings = {
        "1": listingData(float_val=0.012, price=25),
        "2": listingData(float_val=0.021, price=9)
    }

    result = calculate_overpay_percentages(skin_name, skin_listings)
    assert result["1"]["name"] == "AK-47 | Ice Coaled"
    assert result["1"]["price"] == 25 
    assert result["1"]["overpay_percentage"] == 25.0 
    assert result["1"]["float"] == 0.012 

    assert result["2"]["overpay_percentage"] == -50.0 

