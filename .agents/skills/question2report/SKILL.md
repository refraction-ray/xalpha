---
name: question2report
description: >
  Turn a natural-language financial question into a polished, self-contained HTML report.
  Covers the full pipeline: requirement analysis → scope negotiation → data fetching →
  data cleaning → quantitative analysis → visualization → beautiful HTML output.
  Use when the user asks for any financial data comparison, fund screening, index analysis,
  or strategy back-test that should end with a deliverable report.
argument-hint: <question about financial data or analysis>
---

# Question → Report Skill

Transform a user's free-form financial question into a production-quality, self-contained
HTML report with embedded charts and tables.

## Pipeline

```
User Question
     │
     ▼
┌──────────────────┐
│ 1. ANALYZE       │  Parse intent, identify assets, metrics, time range
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ 2. CONFIRM       │  Present analysis plan to user; agree on scope
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ 3. DISCOVER API  │  Explore the xalpha codebase to find suitable APIs
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ 4. FETCH & CLEAN │  Write & run a Python script; handle errors & NaN
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ 5. ANALYZE DATA  │  Compute metrics appropriate to the question
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ 6. GENERATE HTML │  Build a beautiful, self-contained HTML report
└──────────────────┘
```

---

## Step 1 — Analyze the Question

Parse the user's natural-language question and extract:

- **Subject**: What assets, funds, indices, or strategies are being discussed?
- **Comparison / benchmark**: Is there a reference to compare against?
- **Time range**: Explicit dates, or implied ("last 3 years", "since inception").
  Default to the **most recent 3 full calendar years** if unspecified.
- **Desired output**: What kind of insights does the user want? (rankings, trend
  comparison, risk analysis, prediction accuracy, etc.)

If fund codes or asset identifiers are not given, **research them** via web search
or by exploring the xalpha codebase for relevant list/search APIs.

## Step 2 — Confirm Scope

Before any data work, present a concise plan to the user:

```
📋 Analysis Plan
─────────────────────────────────
Subject   : <what is being analyzed>
Assets    : <list of codes / tickers>
Period    : <start> → <end>
Analysis  : <what metrics / comparisons will be computed>
Charts    : <what visualizations will be included>
─────────────────────────────────
Shall I proceed, or would you like to adjust?
```

**Wait for user confirmation** before proceeding. Adjust scope if requested.

## Step 3 — Discover Suitable APIs

**Do NOT assume which xalpha APIs to use.** Instead:

1. Explore the codebase — read `xalpha/__init__.py`, outlines of key modules like
   `universal.py`, `info.py`, `toolbox.py`, `evaluate.py`, `indicator.py`, etc.
2. Identify the right functions for the user's question. The xalpha library is rich:
   it supports funds, indices, stocks, bonds, QDII, commodities, forex, PE/PB
   valuation, portfolio back-testing, holdings analysis, and more.
3. Check function signatures and docstrings to understand parameters, return types,
   and any known quirks (e.g. some classes don't accept `start` in `__init__`).
4. If you encounter an API error at runtime, read the traceback, explore the source
   for alternatives, and fix the script. Be resilient.

## Step 3.1 — Common xalpha APIs & Interfaces

To accelerate discovery, prioritize these common interfaces in the `xalpha` package:

### Data Fetching (`xalpha.universal`)
- `xa.get_daily(code, start=None, end=None)`: The "universal" historical data fetcher.
  - **A-Share**: `SH600000` (prefix SH/SZ + 6-digit code).
  - **HK-Share**: `HK00700`.
  - **US-Share**: `AAPL`, `MSFT`.
  - **Funds**: `F000001` (unit net value), `T000001` (accumulated net value).
  - **Valuation**: `peb-SH000300` (Index PE/PB, **requires JQData**), `peb-600000` (Stock PE/PB, handles 6-digit codes automatically, no JQ required).


- `xa.get_rt(code)`: Fetches real-time price and basic metadata (name, market, etc.).

### Fund Analysis (`xalpha.info`)
- `xa.fundinfo(code, path=None, priceonly=True)`: Core class for fund data.
  - `.price`: DataFrame with `date` and `netvalue`.
  - `.get_holdings(year, season)`: Quarterly holdings data.

### Backtesting & Portfolios (`xalpha.trade`, `xa.multiple`)
- `xa.trade(fund_obj, status_df)`: Backtests a single fund/asset based on a transaction table (`status_df`).
- `xa.itrade(fund_obj, status_df)`: For exchange-traded assets (stocks/ETFs).
- `xa.multiple(trade_list)`: Aggregates multiple `trade`/`itrade` objects into a portfolio.
  - `.v_totvalue()`: Visualizes the portfolio total value curve.
  - `.combsummary()`: Generates a summary table of the portfolio performance.

### Evaluation & Comparison (`xalpha.evaluate`, `xa.toolbox`)
- `xa.evaluate(asset_obj)`: Provides comprehensive performance metrics (Sharpe, Max Drawdown).
- `xa.compare(list_of_objs, start=None)`: Compares multiple assets/strategies on a normalized (1.0) scale.

### Technical Indicators (`xalpha.indicator`)
- `xa.indicator(daily_df)`: Wraps a daily price DataFrame to compute indicators like MA, RSI, MACD.



## Step 4 — Fetch & Clean Data

Write a **single self-contained Python script** that:


1. Imports `xalpha` and any needed stdlib/pandas/numpy modules.
2. Fetches all required data using the APIs discovered in Step 3.
3. **Workspace Organization**: If you create scratch scripts (e.g., `test_api.py`, `diag.py`) or temporary files to debug, create them directly in the target report folder or move them there immediately.
4. Handles errors gracefully — if one data source fails, try fallbacks; if one asset in a list fails, skip it and warn rather than crash.
5. Cleans the data:
   - Ensure dates are `datetime64`.
   - Handle NaN: forward-fill small gaps (≤3 days); drop assets with >30% missing.
   - Align data on common trading dates when comparing multiple series.
6. Saves intermediate results to a temporary workspace CSV (or keeps in memory if the script does everything in one pass).

Run the script using the user's specified Python/conda environment. If not
specified, use the system default.

## Step 5 — Quantitative Analysis

Compute metrics **appropriate to the user's question**. Do not blindly apply a fixed
set of metrics. Choose what makes sense:

- For return comparison: total return, annualized return, excess return / alpha.
- For risk analysis: max drawdown, annualized volatility, Sharpe ratio.
- For tracking analysis: tracking error, information ratio, correlation.
- For valuation: PE/PB percentiles, dividend yield.
- For prediction accuracy: predicted vs actual, RMSE, hit rate.
- For portfolio analysis: asset allocation, sector exposure, concentration.

The agent should determine which metrics are relevant based on the question context.

## Step 5.1 — Pro-Tips for Reliable Analysis

Apply these principles to avoid common pitfalls in quantitative reporting:

- **Unit Consistency**: Verify if your backtesting engine treats trade inputs as **shares** or **cash value**. Inconsistent handling (e.g., selling "100 shares" but interpreting it as "100 dollars") is a frequent cause of hidden performance erosion.
- **Cross-Verification**: Don't trust high-level CAGR/NAV metrics blindly. Periodically reconcile the final liquidity by summing raw cash flows from underlying trade logs.
- **Contextual Visuals**: Use timeline mapping (Gantt-style) to show when a strategy was "Active" vs. "Hedged/In Cash". This explains *why* a performance gap occurred, providing more insight than a simple NAV curve.
- **Document Framework Patches**: If you apply a library-specific fix (e.g., a monkey-patch or a non-standard initialization) to bypass a known bug, document it clearly in the methodology notes.

## Step 6 — Generate the HTML Report

This is the most important step for user experience. The report must be:

### Interactive & Self-Contained
- **All CSS, JS logic, and raw data are embedded.** The HTML file must render perfectly when opened directly in any browser.
- **Interactive Charts**: Load high-quality interactive charting libraries (specifically Apache ECharts, or alternatively Chart.js) from highly reliable public CDNs (e.g., `cdn.jsdelivr.net` or `cdnjs.cloudflare.com`). ECharts is strongly recommended for financial data because of its native support for data zoom sliders, interactive legends, crosshairs, CJK tooltips, and high-quality styling.
- **Data Serialization**: In the python script, serialize raw timeseries data (dates, returns, alpha curves, drawdowns) as a JSON object, and inject it inside the HTML in a `<script>` block. This allows the browser to perform calculations (such as dynamic start/end date selection and real-time return metrics calculation).
- Do NOT use static Matplotlib PNG images unless interactive libraries are absolutely unavailable.

### Visually Polished & Responsive
Follow the design system in [templates/report_style.css](templates/report_style.css):

- **Color palette**: Professional dark/light-themed design using CSS variables. Primary dark blue/teal, warm accent colors. Positive values in green (`#27ae60`), negative in red (`#e74c3c`).
- **Layout**: Card-based responsive grids with subtle transitions and interactive tabs to switch between tables or groups.
- **Typography**: System font stack with CJK support.
- **Tables**: Zebra-striped rows, interactive hover highlights, conditional coloring for performance metrics.
- **Dynamic Charts**: Consistent CJK label support, gridlines, responsive sizing, and interactive legend toggles.
- **Controls**: Add clean UI selectors (tabs, buttons, sliders) to allow the user to toggle between different metrics or filter the display dynamically.

### Structured Sections
Every report should include (adapt as needed):

1. **Header** — Report title, date range, generation timestamp.
2. **Executive Summary** — 3–5 bullet points with key takeaways. This is what a
   busy reader should see first.
3. **Data & Charts** — The main analytical content: comparison charts, distribution
   plots, time series, etc. One card per logical section.
4. **Metrics Tables** — Summary tables with computed statistics. Use conditional
   formatting (green/red) for values where direction matters.
5. **Methodology Note** — Brief paragraph on data source and any caveats.
6. **Footer** — "Generated by xalpha · question2report skill · {date}".

### Output Location & Organization

All generated artifacts—including the fetching/analysis Python scripts, intermediate data files (JSON/CSV), and the final HTML report—must be organized into a dedicated folder.

- **Default Location**: `<project_root>/doc/samples/reports/<descriptive_name>_<YYYYMMDD>/`
- **Custom Location**: If the user specifies a directory, use that.

The folder structure should look like this:
```
<report_folder>/
├── <fetch_and_analyze_script>.py
├── <generate_report_script>.py
├── <data_results>.json
└── <final_report>.html
```

## Cleanup

After the report is generated successfully:
- **Move all related scripts, debug/test files, and intermediate data files** into the designated output folder. DO NOT leave any temporary files (e.g., `test_fetch.py`, `diag.py`, `data.csv`) in the project root.
- **Perform a final cleanup**: Delete any transient test scripts or log files that are not part of the final reproducible analysis (unless they are valuable for documenting the process). Ensure the project environment is as clean as it was before the task started.
- Verify the HTML report correctly is 100% self-contained for the best portability.

## Error Handling Philosophy

- **Fail gracefully**: if one asset out of many fails, skip it and note the skip in
  the report, rather than aborting the whole pipeline.
- **Informative errors**: when a script fails, read the traceback, understand the
  root cause, fix the script, and re-run. Don't just report the error to the user
  without attempting a fix.
- **Interactive fallbacks**: If CDN scripts fail to load, ensure the page falls back to simple table views or provides a clear error notification rather than crashing. Ensure local JSON data is still fully accessible.
- **Framework Patching**: If you encounter a bug in a 3rd-party library (like the `TypeError` in `xalpha.multiple` or `ZeroDivisionError` in `combsummary`), document the patch you applied in the **Methodology Note** of the report.

## Additional Resources

- For the CSS design system, see [templates/report_style.css](templates/report_style.css)
- For an example report structure, see [examples/sample_report_structure.md](examples/sample_report_structure.md)
