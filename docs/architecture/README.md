# Architecture index

CQRP v2 evolves the existing application incrementally.

```
presentation (existing Streamlit app)
        ↓
application / trading / validation / research / analytics / execution
        ↓
infrastructure (configuration, logging)
        ↓
persistence (repositories and SQLite connection)
```

The v1 `engine/` and `db/` directories remain operational baselines until a later sprint deliberately migrates one responsibility at a time.