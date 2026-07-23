# CQRP Getting Started

## Local setup

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python -m unittest discover -s tests -p "test_*.py" -v
streamlit run dashboard/app.py
```

Open `http://localhost:8501`. Empty dashboard states are expected until data providers and research records are configured.

## Safe use

- Start in `DISABLED` or `PAPER`; do not enable live order placement during initial validation.
- Never enter credentials in source code, GitHub, SQLite, screenshots, or notebook outputs.
- Use the Configuration page for safe local configuration and masked status checks.
- Read [dashboard local setup](../dashboard/local-setup.md) and [dashboard troubleshooting](../dashboard/troubleshooting.md) for details.
