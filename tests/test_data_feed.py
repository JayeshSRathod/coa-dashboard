import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from engine.data_feed import parse_dhan_chain

# Taken directly from DhanHQ v2 docs (https://dhanhq.co/docs/v2/option-chain/)
# so this test fails loudly if the real response shape ever changes.
SAMPLE_DHAN_RESPONSE = {
    "last_price": 25642.8,
    "oc": {
        "25650.000000": {
            "ce": {
                "average_price": 146.99,
                "greeks": {"delta": 0.53871, "theta": -15.1539, "gamma": 0.00132, "vega": 12.18593},
                "implied_volatility": 9.789193798280868,
                "last_price": 134,
                "oi": 3786445,
                "previous_close_price": 244.85,
                "previous_oi": 402220,
                "previous_volume": 31931705,
                "security_id": 42528,
                "top_ask_price": 134,
                "top_ask_quantity": 1365,
                "top_bid_price": 133.55,
                "top_bid_quantity": 1625,
                "volume": 117567970,
            },
            "pe": {
                "average_price": 134.62,
                "greeks": {"delta": -0.46732, "theta": -10.61131, "gamma": 0.00109, "vega": 12.2025},
                "implied_volatility": 11.939337251984934,
                "last_price": 132.8,
                "oi": 3096145,
                "previous_close_price": 101.45,
                "previous_oi": 2327260,
                "previous_volume": 81224780,
                "security_id": 42529,
                "top_ask_price": 132.75,
                "top_ask_quantity": 390,
                "top_bid_price": 132.45,
                "top_bid_quantity": 65,
                "volume": 157009970,
            },
        }
    },
}


def test_parse_dhan_chain_extracts_spot():
    df, spot = parse_dhan_chain(SAMPLE_DHAN_RESPONSE)
    assert spot == 25642.8
    print("spot extraction OK:", spot)


def test_parse_dhan_chain_maps_columns_correctly():
    df, spot = parse_dhan_chain(SAMPLE_DHAN_RESPONSE)
    row = df.iloc[0]
    assert row["Strike"] == 25650.0
    assert row["Call_Vol"] == 117567970
    assert row["Call_OI"] == 3786445
    assert row["Call_LTP"] == 134
    assert row["Put_Vol"] == 157009970
    assert row["Put_OI"] == 3096145
    assert row["Put_LTP"] == 132.8
    print("column mapping OK")


def test_parse_dhan_chain_handles_missing_side():
    # Deep ITM/OTM strikes sometimes have no quotes on one side
    raw = {"last_price": 100.0, "oc": {"200.000000": {"ce": {}, "pe": {"volume": 500, "oi": 10}}}}
    df, spot = parse_dhan_chain(raw)
    assert df.iloc[0]["Call_Vol"] == 0
    assert df.iloc[0]["Put_Vol"] == 500
    print("missing-side handling OK")


if __name__ == "__main__":
    test_parse_dhan_chain_extracts_spot()
    test_parse_dhan_chain_maps_columns_correctly()
    test_parse_dhan_chain_handles_missing_side()
    print("All Dhan parsing tests passed.")
