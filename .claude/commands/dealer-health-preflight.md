# Dealer Health Dashboard — Pre-flight Check

Run a full dependency check for the Dealer Health Dashboard, then optionally inspect live worksheet names from admin.cars.com to resolve any layout-change warnings.

## Steps

1. Run the preflight script and report results:
```bash
python3 ~/Documents/scripts/preflight_dealer_health.py
```

2. If Chrome CDP is reachable, run a live worksheet discovery for demand_signals on a known dealer to find the current "Pricing Summary" replacement name. Use ACA (CCID 6051462) as the test dealer:
```python
import sys
sys.path.insert(0, '/Users/jcrawley/Documents/scripts')
import admin_cars, logging
logging.basicConfig(level=logging.WARNING)

# This will log the available worksheet names if Pricing Summary is missing
result = admin_cars.fetch_market_comparison('6051462')
print('market_comparison result:', result)
print('missing worksheets:', admin_cars.get_last_missing_worksheets())
```

3. Report:
   - Pass/fail for each dependency (Chrome, admin.cars.com, Claude CLI, Salesforce)
   - If market comparison failed: the available worksheet names from the diagnostic log
   - Next step: if a new worksheet name is found, update `REQUIRED_WORKSHEETS` and `_MC_JS` in `admin_cars.py:48` and `admin_cars.py:503`

## Quick launch (after all checks pass)
```bash
python3 -m streamlit run ~/Documents/scripts/dealer_health.py
```
