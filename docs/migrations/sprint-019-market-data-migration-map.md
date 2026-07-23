# Sprint-019 Market Data Migration Map

| Legacy boundary | Sprint-019 authoritative boundary | Status |
| --- | --- | --- |
| `engine/fyers_feed.py` raw Fyers response/parser | `market_data.providers.FyersProvider` + `market_data.mappers.fyers_mapper` | Legacy compatibility retained; new code uses platform |
| `engine/data_feed.py` raw Dhan response/parser | `market_data.providers.DhanProvider` + `market_data.mappers.dhan_mapper` | Legacy compatibility retained; new code uses platform |
| `src/market/snapshot.py` payload contract | `market_data.models.OptionChainSnapshot` | Existing collector remains supported through explicit bridge |
| `src/research.collector.SnapshotCaptureService` | `market_data.snapshot_service.MarketDataSnapshotService` | Canonical snapshot writes first; collector is replay compatibility |
| `market_snapshots` | `market_snapshot` | Existing research snapshots preserved; normalized enterprise evidence is append-only |
| Root `app.py` live-feed code | Dashboard 2.0 / CQRP 3.0 read models | Root app is legacy only; no new integration work permitted |

The next migration increment can remove the legacy root application's direct provider calls only after CQRP 3.0's read API is hosted and the legacy UI has a supported replacement.
