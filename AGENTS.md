# XAlpha Agent Platform Guidelines

Welcome to `xalpha`. This document defines the operational rules for AI agents and contributors. 

**Core Identity:** `xalpha` is not just a quantitative finance Python library—it is an **AI Agent Platform**. Agents are expected to use natural language instructions to automatically write `xalpha` code, perform financial data mining, backtest strategies, and generate analytical reports.

## 1. The Agentic Workflow
When a user asks for financial analysis or data mining via natural language:
- **Understand the Domain:** Use `xalpha.universal`, `xalpha.fundinfo`, and `xalpha.policy` as your primary tools.
- **Write Scripts:** Do not just explain how to do it; write and execute Python scripts utilizing `xalpha` to fetch real data, compute metrics (e.g., XIRR, volatility, correlation), and save results.
- **Be Proactive:** If a data source (like Investing.com or Xueqiu) throws an error or requires an ID mapping, autonomously debug and ask the user for the fix plan.
- **Synthesize:** Present the final financial analysis clearly to the user, backed by the data you mined.

## 2. Core Compatibility Contracts
Code written or modified by agents MUST be broadly compatible across the scientific Python ecosystem:
- **Pandas 1.x up to 3.x:** Handle frequency format changes (`"M"` vs `"ME"`). Always wrap HTML strings in `io.StringIO()` before `pd.read_html()`. Use explicitly strict type casting (`.astype(float)`) to avoid `LossySetitemError`.
- **Numpy 1.x through 2.x:** Avoid deprecated aliases like `np.float`. Use `float` or `np.float64`.

## 3. Data Scraping & API Resilience
`xalpha` heavily relies on web scraping (`beautifulsoup4`) and API endpoints. 
- **Robust Parsing:** Upstream HTML changes frequently. Avoid fragile exact string matches `soup.find(string="text")`. Use iterative tag searching and `get_text(strip=True)`.
- **Graceful Fallbacks:** If an endpoint fails (e.g., anti-scraping on Investing.com), agents should implement or utilize fallback logic (e.g., JSON APIs vs HTML parsing) and use the `rget` decorator for network resilience.
- **Never Break the DataFrame:** Ensure that any updated scraping logic exactly restores the original DataFrame schema expected by `xalpha`.

## 4. Local Caching
`xalpha` uses local caching (CSV/SQL) for performance.
- When expanding data classes (e.g., adding a new attribute to `fundinfo`), agents MUST update both `_save_csv/_sql` and `_fetch_csv/_sql`.
- Handle legacy caches defensively using `.get("new_key", "default")`.

## 5. Dashboards & Visualization
When generating HTML reports or dashboards (e.g., QDII prediction pages):
- **Rich Aesthetics:** Use modern, light-themed layouts, DataTables, and CSS variables. Keep Python focused on data; offload rendering logic to JS/CSS.

## 6. Code Quality & CI/CD
- **Testing:** Ensure tests pass using `pytest`. Use `pytest.importorskip` for optional dependencies.
- **Testing Efficiency:** Running the entire/global test suite is very heavy. Minimize running global tests, and prefer running targeted tests (e.g. `pytest tests/test_file.py::test_func`) to verify changes.
- **Linting:** Enforce `black` formatting and strict adherence to a **10.00/10** Pylint score for the `xalpha/` directory.

## 7. Development Mindset
1. **Atomic & Precise Changes:** When fixing bugs in the library itself, make the smallest possible change. Avoid unnecessary refactoring of legacy code.
2. **Data-Driven:** When asked to analyze, write the code, run it, and let the data speak. 
3. **Self-Healing & Fail-Fast:** If you encounter a `KeyError` or `NoneType` during data fetching, investigate the upstream response and patch the parsers or input normalizers autonomously. **Avoid over-protective code** (e.g., blanket try-except or returning empty DataFrames) that swallows original errors. Let it fail naturally so the root cause is visible, then fix it at the source.
