"""V5 Binance Spot gateway: paper, testnet, or explicitly enabled live mode."""
import argparse, uuid, json
from decimal import Decimal
from pathlib import Path
from config import MODE, QUOTE_ASSET, MAX_DAILY_LOSS_FRACTION, FEE_BUFFER_FRACTION, KILL_SWITCH_FILE
from risk import D, calculate_quantity, validate_prices
from state import killed, daily_guard
from binance_client import BinanceClient, BinanceAPIError

def balances(account):
    return {x["asset"]: D(x["free"]) + D(x["locked"]) for x in account.get("balances", [])}

def marked_equity(client, account):
    """Value every non-zero holding in quote asset; fail closed if an asset cannot be priced."""
    total = Decimal("0")
    for asset, amount in balances(account).items():
        if amount == 0: continue
        if asset == QUOTE_ASSET:
            total += amount
            continue
        pair = asset + QUOTE_ASSET
        try: total += amount * client.ticker_price(pair)
        except Exception as exc:
            raise ValueError(f"Cannot value held asset {asset} in {QUOTE_ASSET}; refusing live trade.") from exc
    return total

def symbol_filters(client, symbol):
    data = client.exchange_info(symbol).get("symbols", [])
    if len(data) != 1: raise ValueError("Symbol not found or ambiguous.")
    s = data[0]
    if s.get("status") != "TRADING" or not s.get("isSpotTradingAllowed", False):
        raise ValueError("Symbol is not enabled for Spot trading.")
    f = {x["filterType"]: x for x in s.get("filters", [])}
    for key in ("PRICE_FILTER", "LOT_SIZE"):
        if key not in f: raise ValueError(f"Missing {key}")
    return s, f

def validate_order(price, qty, filters):
    price, qty = D(price), D(qty)
    pf, lf = filters["PRICE_FILTER"], filters["LOT_SIZE"]
    tick, step = D(pf["tickSize"]), D(lf["stepSize"])
    if price < D(pf["minPrice"]) or price > D(pf["maxPrice"]) or price % tick:
        raise ValueError("Entry violates PRICE_FILTER.")
    if qty < D(lf["minQty"]) or qty > D(lf["maxQty"]) or qty % step:
        raise ValueError("Quantity violates LOT_SIZE.")
    notional = price * qty
    mn, nt = filters.get("MIN_NOTIONAL"), filters.get("NOTIONAL")
    if mn and notional < D(mn["minNotional"]): raise ValueError("Below MIN_NOTIONAL.")
    if nt and (notional < D(nt["minNotional"]) or notional > D(nt["maxNotional"])):
        raise ValueError("Violates NOTIONAL bounds.")
    return notional

def main():
    p = argparse.ArgumentParser(description="Binance Spot V5 approval gateway")
    p.add_argument("--symbol", required=True)
    p.add_argument("--entry", required=True, help="BUY limit price")
    p.add_argument("--stop", required=True, help="STOP_LOSS_LIMIT trigger")
    p.add_argument("--stop-limit", required=True, help="STOP_LOSS_LIMIT execution price; <= --stop")
    p.add_argument("--take-profit", required=True, help="TAKE_PROFIT_LIMIT price")
    args = p.parse_args()
    symbol = args.symbol.upper()
    entry, stop, stop_limit, tp = map(D, (args.entry,args.stop,args.stop_limit,args.take_profit))

    if killed(): raise ValueError(f"Kill switch active ({KILL_SWITCH_FILE} exists). Remove it deliberately to re-enable entries.")
    if MODE == "paper":
        print("PAPER MODE: no exchange orders or real funds will be used.")
        print(f"Proposal only: BUY {symbol} @ {entry}; stop trigger {stop}, stop-limit {stop_limit}, take-profit {tp}.")
        print("Paper mode in this release validates the proposal; it does not simulate fills.")
        return

    client = BinanceClient()
    s, f = symbol_filters(client, symbol)
    validate_prices(entry, stop, stop_limit, tp, f["PRICE_FILTER"]["tickSize"])
    account = client.account()
    equity = marked_equity(client, account)
    allowed, loss, baseline = daily_guard(equity)
    if not allowed:
        raise ValueError(f"Daily loss guard active: drawdown {loss:.2%}, limit {MAX_DAILY_LOSS_FRACTION:.2%}.")
    quote_free = balances(account).get(QUOTE_ASSET, Decimal("0"))
    qty = calculate_quantity(equity, entry, stop, f["LOT_SIZE"]["stepSize"])
    notional = validate_order(entry, qty, f)
    if qty <= 0: raise ValueError("Calculated quantity is zero.")
    if notional * (1 + FEE_BUFFER_FRACTION) > quote_free:
        raise ValueError(f"Insufficient free {QUOTE_ASSET}; need approx {notional*(1+FEE_BUFFER_FRACTION)}, have {quote_free}.")
    if entry >= client.ticker_price(symbol):
        raise ValueError("Entry must be below current ticker reference for this BUY-limit workflow.")

    list_id = "v5" + uuid.uuid4().hex[:28]
    params = {
        "symbol": symbol,
        "workingType": "LIMIT", "workingSide": "BUY",
        "workingPrice": format(entry, "f"), "workingQuantity": format(qty, "f"),
        "workingTimeInForce": "GTC",
        "pendingSide": "SELL",
        "pendingBelowType": "STOP_LOSS_LIMIT",
        "pendingBelowStopPrice": format(stop, "f"),
        "pendingBelowPrice": format(stop_limit, "f"),
        "pendingBelowTimeInForce": "GTC",
        "pendingAboveType": "TAKE_PROFIT_LIMIT",
        "pendingAboveStopPrice": format(tp, "f"),
        "pendingAbovePrice": format(tp, "f"),
        "pendingAboveTimeInForce": "GTC",
        "listClientOrderId": list_id,
        "newOrderRespType": "RESULT",
    }
    # Test endpoint validates a regular order, but does not validate/execute an order list.
    # Do not claim OTOCO test validation. Show exact order-list payload for approval.
    print("\\n=== V5 ORDER PROPOSAL ===")
    print(f"Mode: {MODE.upper()} | Symbol: {symbol} | Quote: {QUOTE_ASSET}")
    print(f"BUY LIMIT: {entry} | Quantity: {qty} | Notional: {notional}")
    print(f"STOP trigger/limit: {stop}/{stop_limit} | TAKE PROFIT: {tp}")
    print(f"Marked account equity: {equity} | Daily baseline: {baseline} | Drawdown: {loss:.2%}")
    print("Protective exit orders are contingent and activate after the entry fills (OTOCO).")
    print("A stop-limit is not guaranteed to fill during a fast gap or illiquid market.")
    if MODE == "live":
        print("\\n*** REAL MONEY LIVE MODE ***")
        print("Verify API key is Spot-trading only, IP-restricted, and withdrawals disabled.")
    phrase = f"APPROVE {MODE.upper()} {list_id}"
    typed = input(f"\\nType exactly to submit this trade:\\n{phrase}\\n> ").strip()
    if typed != phrase:
        print("Rejected. No order submitted.")
        return
    # Re-check kill switch, balances, daily loss and price immediately before submission.
    if killed(): raise ValueError("Kill switch activated during approval; no order submitted.")
    fresh = client.account()
    fresh_equity = marked_equity(client, fresh)
    allowed, fresh_loss, _ = daily_guard(fresh_equity)
    if not allowed: raise ValueError("Daily loss limit reached during approval; no order submitted.")
    fresh_quote = balances(fresh).get(QUOTE_ASSET, Decimal("0"))
    if notional * (1 + FEE_BUFFER_FRACTION) > fresh_quote:
        raise ValueError("Quote balance changed; refusing submission.")
    if entry >= client.ticker_price(symbol): raise ValueError("Market moved; entry is no longer below ticker.")
    print("Submitting OTOCO order list...")
    try:
        result = client.place_otoco(params)
        print(json.dumps(result, indent=2))
        print("IMPORTANT: Confirm both contingent exit legs are present in Binance open order lists.")
    except BinanceAPIError:
        print("Submission outcome may be uncertain. Do not blindly retry; reconcile open order lists and order history on Binance.")
        raise

if __name__ == "__main__":
    try: main()
    except (ValueError, BinanceAPIError) as exc: raise SystemExit(f"SAFE STOP: {exc}")
