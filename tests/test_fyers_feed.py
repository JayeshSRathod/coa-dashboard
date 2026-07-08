import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from engine.fyers_feed import parse_fyers_chain

# Mock payload shaped like Fyers' actual optionchain response, based on the
# field names confirmed via a community-maintained typed Go client
# (github.com/sainipankaj15/All-In-One-Broker/Fyers) that mirrors the same
# JSON keys. The first entry (no option_type/strike_price) represents the
# underlying's own row — this is the assumption flagged for live verification.
MOCK_FYERS_DATA = {
    "callOi": 1234567,
    "putOi": 2345678,
    "optionsChain": [
        {"ltp": 24440.85, "symbol": "NSE:NIFTY50-INDEX"},  # underlying row
        {
            "ask": 135.5, "bid": 134.0, "fyToken": "abc1",
            "ltp": 134.0, "oi": 3786445, "option_type": "CE",
            "prev_oi": 402220, "strike_price": 24450.0,
            "symbol": "NSE:NIFTY2571724450CE", "volume": 117567970,
        },
        {
            "ask": 133.0, "bid": 132.45, "fyToken": "abc2",
            "ltp": 132.8, "oi": 3096145, "option_type": "PE",
            "prev_oi": 2327260, "strike_price": 24450.0,
            "symbol": "NSE:NIFTY2571724450PE", "volume": 157009970,
        },
        {
            "ask": 90.0, "bid": 89.5, "fyToken": "abc3",
            "ltp": 90.0, "oi": 1000000, "option_type": "CE",
            "prev_oi": 900000, "strike_price": 24500.0,
            "symbol": "NSE:NIFTY2571724500CE", "volume": 50000000,
        },
    ],
}


def test_parse_extracts_spot_from_underlying_row():
    df, spot = parse_fyers_chain(MOCK_FYERS_DATA)
    assert spot == 24440.85
    print("spot extraction OK:", spot)


def test_parse_groups_ce_pe_by_strike():
    df, spot = parse_fyers_chain(MOCK_FYERS_DATA)
    row_24450 = df[df["Strike"] == 24450.0].iloc[0]
    assert row_24450["Call_LTP"] == 134.0
    assert row_24450["Call_Vol"] == 117567970
    assert row_24450["Put_LTP"] == 132.8
    assert row_24450["Put_Vol"] == 157009970
    print("CE/PE grouping OK")


def test_parse_handles_missing_side():
    # Strike 24500 only has a CE entry in the mock — Put side should default to 0
    df, spot = parse_fyers_chain(MOCK_FYERS_DATA)
    row_24500 = df[df["Strike"] == 24500.0].iloc[0]
    assert row_24500["Call_Vol"] == 50000000
    assert row_24500["Put_Vol"] == 0.0
    print("missing-side handling OK")


def test_parse_raises_if_no_underlying_row_found():
    bad_data = {"optionsChain": [
        {"ask": 1, "option_type": "CE", "strike_price": 100, "ltp": 5, "oi": 1, "volume": 1}
    ]}
    try:
        parse_fyers_chain(bad_data)
        raise AssertionError("Expected RuntimeError when no underlying row is present")
    except RuntimeError:
        print("missing-underlying-row raises clearly OK")


if __name__ == "__main__":
    test_parse_extracts_spot_from_underlying_row()
    test_parse_groups_ce_pe_by_strike()
    test_parse_handles_missing_side()
    test_parse_raises_if_no_underlying_row_found()
    print("All Fyers parsing tests passed.")
