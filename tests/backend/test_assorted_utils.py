import pytest
from backend.utilities.assorted_utils import (
    what_wear,
    seconds_to_time,
    price_conversion
)

@pytest.mark.parametrize("float_val, expected_result", [
    (0.001, 0),
    (0.069999, 0),
    (0.07, 1),
    (0.15, 2),
    (0.38, 3),
    (0.45, 4),
    (0.69, 4)
])
def test_what_wear(float_val: float, expected_result: int):
    assert what_wear(float_val) == expected_result
