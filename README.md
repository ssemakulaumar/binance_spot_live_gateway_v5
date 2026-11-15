# Binance Spot Gateway V5

V5 adds explicitly separated PAPER, TESTNET, and LIVE modes, per-trade typed approval,
an exchange-side OTOCO entry/exit order list, balance and portfolio valuation checks,
a persistent UTC-day drawdown baseline, and a file-based entry kill switch.

## Important safety limits

- Default mode is `paper`. Paper mode only validates and displays proposals; it does
  not yet simulate fills or maintain a paper portfolio.
- `testnet` uses `testnet.binance.vision` and Testnet credentials.
- `live` uses `api.binance.com` and a completely separate LIVE key pair. Live mode is
  deliberately explicit; never test with funds you cannot afford to lose.
- Every order list requires a unique typed approval phrase. The program rechecks the
  kill switch, account valuation, daily loss and quote balance immediately before
  submission.
- The entry is a BUY LIMIT and the contingent exits are an OTOCO SELL stop-loss-limit
  and take-profit-limit. Binance activates the pending exits after the working entry
  is filled. This avoids leaving a naked filled position during normal OTOCO handling.
- Stop-limit orders are not guaranteed to execute in a gap, fast market, outage,
  or illiquid market. Monitor the exchange order list and position.
- Daily drawdown is based on marked account equity in the configured quote asset,
  valued using direct `ASSETUSDT` ticker pairs. If any non-zero holding cannot be
  priced, the bot fails closed. The baseline is initialized on the first run of each
  UTC day. Keep the SQLite state file persistent; deleting it resets the baseline.
- The kill switch blocks new entries only. It does NOT cancel exchange orders or
  liquidate holdings. Protective exits should generally remain active; manage/cancel
  open orders manually in Binance after reviewing exposure.
- This single-process CLI is not a 24/7 supervisor. A crash, network outage, exchange
  rejection, or unfilled stop-limit can leave risk. Reconcile orders and balances in
  Binance after uncertain API responses. Do not run multiple copies concurrently.
- OTOCO order-list parameters can be subject to Binance API changes, account
  permissions, symbol filters and exchange eligibility. This client does not claim
  a successful order until Binance returns a response.

## Install in Termux

```bash
pkg update && pkg upgrade -y
pkg install python unzip -y
unzip binance_spot_live_gateway_v5.zip
cd binance_spot_live_gateway_v5
python -m unittest -v
```

## Paper proposal

```bash
export BINANCE_MODE=paper
python gateway.py --symbol BTCUSDT --entry 60000 --stop 59400 --stop-limit 59300 --take-profit 61200
```

## Testnet

```bash
export BINANCE_MODE=testnet
export BINANCE_TESTNET_API_KEY='YOUR_TESTNET_KEY'
export BINANCE_TESTNET_API_SECRET='YOUR_TESTNET_SECRET'
python gateway.py --symbol BTCUSDT --entry 60000 --stop 59400 --stop-limit 59300 --take-profit 61200
```

## Live mode — use only after Testnet validation

```bash
export BINANCE_MODE=live
export BINANCE_LIVE_API_KEY='YOUR_RESTRICTED_LIVE_KEY'
export BINANCE_LIVE_API_SECRET='YOUR_LIVE_SECRET'
python gateway.py --symbol BTCUSDT --entry 60000 --stop 59400 --stop-limit 59300 --take-profit 61200
```

Never paste keys into ChatGPT, source files, screenshots, or shared logs. Use a
dedicated Binance API key with Spot trading permission only, withdrawals disabled,
and IP restrictions enabled where possible.

## Kill switch

```bash
python kill_switch.py on
python kill_switch.py off
```

`on` blocks new proposals/submissions. `off` only re-enables new entries; it does not
change existing orders. The switch is a local file, so it only works while this
program is running on the same device and directory/state path.

## Configuration

Risk defaults: 0.5% of marked equity risk budget, 10% max allocation, 2% daily
drawdown limit. These are conservative code defaults, not a guarantee of safety.
The daily baseline is UTC-day and stored in `v5_state.sqlite3`.

## What still requires operational validation

Before using real funds, validate OTOCO behavior on Binance Spot Testnet and verify
the returned order list includes both exit legs. Test partial fills, rejected lists,
network timeouts, app termination, day rollover, unsupported assets, and kill-switch
behavior. The CLI does not run a background position monitor, cannot guarantee a
stop fill, and does not automatically flatten positions if protective orders fail.
