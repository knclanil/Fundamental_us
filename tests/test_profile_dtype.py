"""v3.0.5 regression: null profile columns must accept text values."""
import pandas as pd

def test_profile_nullable_string_dtype():
    instruments = pd.DataFrame({"ticker": ["AAPL"], "sector": pd.Series([pd.NA], dtype="Int32"), "industry": pd.Series([pd.NA], dtype="Int32")})
    for column in ("sector", "industry"):
        instruments[column] = instruments[column].astype("string")
    instruments.loc[instruments.ticker == "AAPL", "sector"] = "Technology"
    instruments.loc[instruments.ticker == "AAPL", "industry"] = "Consumer Electronics"
    assert instruments.loc[0, "sector"] == "Technology"
    assert instruments.loc[0, "industry"] == "Consumer Electronics"
