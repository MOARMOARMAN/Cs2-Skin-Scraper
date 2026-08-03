import pytest
from backend.utilities.assorted_utils import (
    what_wear,
    seconds_to_time,
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

@pytest.mark.parametrize("seconds, expected_result", [
    (60, "1 minute(s)"),
    (61, "1 minute(s) 1 second(s)"),
    (59, "59 second(s)"),
    (3601, "1 hour(s) 1 second(s)"),
    (3600, "1 hour(s)"),
    (3662, "1 hour(s) 1 minute(s) 2 second(s)")
])
def test_seconds_to_time(seconds: float, expected_result: str):
    assert seconds_to_time(seconds) == expected_result

    
