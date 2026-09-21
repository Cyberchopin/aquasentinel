# Backtest: illustrative mechanics, not environmental validation

Run `python scripts/backtest.py`; machine-readable results are in `backtest.json`.

Synthetic: 200 reproducible scenarios, seed 260921. A deliberately correlated
artificial rain generator and artificial runoff labels exercise the actual Watch
function. Thresholds 3, 5, 10, 15 mm are swept. Precision=TP/(TP+FP), recall=TP/(TP+FN),
false-alert rate=FP/(FP+TN). Positive artificial events peak 18 hours after the
evaluation time. These constructed lead times are NOT observed forecast skill.
No tuning result is promoted to a validated operational threshold.

Real: the eight USGS daily means identify local maxima on February 2 and February
5, 2024. This is explicitly a **PROXY for rain-driven runoff events**. Discharge
alone does not establish rainfall causality. It does not validate unusual citizen
reports, contamination, water quality or disease. The daily resolution does not
identify the sub-day peak time.

Open-Meteo archive/reanalysis is separately captured for context. It is **not
as-issued forecast skill** and is never fed into the forecast Watch path. Since
we have no contemporaneously captured forecasts from February 2024, real forecast
precision, recall and lead time are unreported (null), not manufactured. The
September capture cannot be backdated into February. A meaningful real prospective
evaluation requires more captured forecast vintages and independently specified
event windows; eight days and two local maxima are insufficient.
