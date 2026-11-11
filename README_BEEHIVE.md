# BeeHive Intelligence — demo-only research bot (experimental MVP)

Upgrade path for the original BeeHive Analysis / Streamlit project. The old \`app.py\` and
\`simplified_app.py\` remain intact. New code lives under \`beehive/\`.

**Scope:** EUR/USD, GBP/USD and XAU/USD on Exness **MT5 DEMO** accounts only.
M15 completed-candle breakout with H1 trend context; optional, experimental ML
direction estimates; scheduled market outlooks; Telegram signals and controlled
demo-only execution. Default maximum risk is 0.5% equity per trade and a 2% daily
equity drawdown gate. **These limits cannot guarantee a maximum realised loss.**
Gaps, slippage, disconnections and overlapping positions can cause greater losses.

## Current status / honest limitations

- This is a new implementation, not a backtested/profitable strategy.
- All accounts with MT5 \`trade_mode\` other than \`ACCOUNT_TRADE_MODE_DEMO\` are refused
  at connection **and** before order submission. No live-money integration.
- Execution is **off by default** and the persistent kill switch starts HALTED.
  Both opt-in \`DEMO_AUTO_EXECUTE=true\` and an explicit \`resume\` are needed.
- Positions and signals are stored in a SQLite journal; there is no broker P/L
  reconciliation, portfolio-level risk engine, or robust execution recovery yet.
  Never describe the journal as a realised profit report.
- The experimental ML direction probability is **uncalibrated**. Brier/accuracy
  metrics describe a holdout next-4-candle direction experiment, not tradable win rate.
- Three symbols are scanned, but data/instrument availability depends on the
  exact Exness demo server. Quote spread thresholds may filter many trades.
- A Windows machine or VPS with a running and logged-in MetaTrader 5 terminal
  is needed for the official Python MT5 adapter. A Mac can run tests and the
  dashboard but not this official terminal bridge natively.
- Continuous monitoring relies on the daemon process staying alive. Use Windows
  Task Scheduler or a supervised Windows service in a real deployment.

## Install / dry run

1. Clone this branch, create a Python 3.11+ environment and install
   \`pip install -r requirements-beehive.txt\`.
2. On the Windows MT5 host, additionally install
   \`pip install -r requirements-mt5-windows.txt\`.
3. Open MT5 and log in to an **Exness demo** account. Set environment variables
   based on \`.env.beehive.example\`. Use an account login/password/server in
   your secure local environment, never in Git, screenshots or Telegram.
4. Create a Telegram bot with BotFather. Configure \`TELEGRAM_BOT_TOKEN\`,
   a destination \`TELEGRAM_CHAT_ID\`, and your numeric \`TELEGRAM_ADMIN_ID\`.
   Admin commands from any other account are ignored.
5. First check the connection and all market symbols, **without submitting orders**:
   `python -m beehive.cli preflight`
   Confirm that it reports DEMO, the expected symbol names, and recent candles.
   Then run **read-only** analysis:
   \`python -m beehive.cli outlook\`
   \`python -m beehive.cli scan\`
   \`python -m beehive.cli status\`
6. Only after verifying your DEMO account and observing signals, consciously
   opt in: set \`DEMO_AUTO_EXECUTE=true\`, then run
   \`python -m beehive.cli resume\`.
7. Start \`python -m beehive.cli daemon\`. The daemon scans at approximately
   1 minute after each M15 boundary and sends reports at 07:00, 09:00,
   14:00 and 22:00 **Africa/Lagos**. These are planned schedule slots,
   not guarantees of delivery if the process or network is down.

Emergency stop: \`python -m beehive.cli stop\` or admin Telegram \`/stop\`.
Re-arm: local \`resume\` or admin \`/resume\`. \`/status\` is also available.
**Emergency stop prevents new orders; it does not liquidate existing positions.**
Use MT5 to close/review any open demo positions and retain broker SL/TP.

## Data and research notes

- The broker adapter requests only **completed** M15/H1 candles (position 1 onward).
- H1 EMA20 vs EMA50 sets a trend bias; completed M15 10-bar breakout with RSI
  and MACD filters can produce BUY/SELL or NO TRADE.
- Stop distance = 1.5 × M15 ATR, target = 2R. The final stop and target are
  computed from current MT5 bid/ask at risk-check time.
- Spread filter: 2.5 pips for EURUSD/GBPUSD, 0.70 quoted price units for
  XAUUSD. These are conservative experimental settings, not universal.
- Position size uses **MT5 order_calc_profit**, not guessed pip values. An
  unaffordable minimum lot yields NO ORDER.
- A SQLite journal records unique signals, action results and the first
  observed equity each UTC day. This is not yet a fully reconciled ledger.
- Historical time-series research uses chronological holdout with a purged
  forecast horizon. It does not establish profitability or eliminate overfitting.

## Tests

\`python -m unittest discover -s tests -p 'test_beehive*.py' -v\`

Tests use fakes; they do **not** send MT5 orders. On a Windows demo terminal,
run read-only smoke checks before enabling demo execution. The earlier
Streamlit dashboards are intentionally unchanged during this first increment.

## Development roadmap

1. **This increment:** MT5 connection, risk-gated signals, experimental ML,
   Telegram admin commands, scheduled outlooks, journal and unit tests.
2. **Next:** realistic cost-aware historical backtesting (bid/ask, execution,
   stop-first fills), stable trade reconciliation, per-position portfolio risk,
   simulation-only integration tests, and real Exness DEMO smoke tests.
3. **Later:** Laravel subscriber API, authenticated analytics, subscriptions,
   broker abstraction and commercial/regulatory review before any public paid
   signal product.

Do not sell or advertise these signals as guaranteed returns.

## Historical candle backtest (research only)

Run `python -m beehive.cli backtest` on an authenticated Windows MT5
**demo** terminal. Uses up to 2,000 M15 and 600 H1 broker candles per symbol.
The simulator uses the recorded MT5 spread, next-candle opening entry,
conservative stop-first intrabar tie-breaking, gap-through-stop treatment,
and a maximum 16-candle holding horizon. It intentionally **does not**
model commission, swaps, other slippage, partial fills or margin calls.
The reported return is a simplified research statistic, not a proven
or audited investment return. Never optimise directly on the reported
backtest and then describe it as out-of-sample performance.

## Operational safety update

- The system now refuses new entries if any pending order exists on the broker
  account. This is intentionally conservative for a shared demo account.
- The daily equity anchor uses the **Africa/Lagos calendar day**. This anchor
  is the first observed equity that day, not an MT5-confirmed midnight balance.
- Run `python -m beehive.cli preflight` before any demo execution to validate
  DEMO status, trade permissions, symbol names, spreads and candle freshness
  without sending a trade. On market closures, stale data is expected and is
  correctly reported as a failed market readiness check.


## Mac M1/M2 (optional experimental research path)

MetaQuotes' Mac installer runs MT5 using Wine; the official Python
MetaTrader5 module itself is Windows-only. BeeHive now auto-selects a
read-only macOS research adapter. The optional third-party mt5_mac v0.3.0
beta package is NOT official and bootstraps its own Wine Python process.
Review that software and its permissions before using it. Use DEMO only.

- Install MT5 for Mac from metatrader5.com and log in to Exness DEMO.
- Create a Python 3.11 environment and install requirements-beehive.txt.
- Optionally install mt5_mac==0.3.0 after reviewing the package.
- Run: python -m beehive.cli preflight
- Run: python -m beehive.cli outlook
- Run: python -m beehive.cli scan

Mac scanning/alerts work only while the terminal and Mac are awake and
connected. The Mac connector always blocks trade execution, even if
DEMO_AUTO_EXECUTE=true, because the published adapter lacks the broker risk
validation operations required by this implementation. The next integration
step is a first-party MQL5 Expert Advisor with demo-only order execution
and independently verified broker-side risk controls.
