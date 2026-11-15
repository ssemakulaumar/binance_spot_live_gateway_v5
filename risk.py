from decimal import Decimal, ROUND_DOWN
from config import RISK_FRACTION, MAX_ALLOCATION_FRACTION, FEE_BUFFER_FRACTION

def D(value): return Decimal(str(value))

def floor_step(value, step):
    value, step = D(value), D(step)
    if step <= 0: raise ValueError("Invalid quantity step")
    return (value / step).to_integral_value(rounding=ROUND_DOWN) * step

def calculate_quantity(equity, entry, stop, step_size):
    equity, entry, stop = map(D, (equity, entry, stop))
    if equity <= 0 or entry <= 0 or stop <= 0 or stop >= entry:
        raise ValueError("For a BUY, equity/entry/stop must be positive and stop below entry.")
    risk_qty = equity * RISK_FRACTION / (entry - stop)
    allocation_qty = equity * MAX_ALLOCATION_FRACTION / (entry * (1 + FEE_BUFFER_FRACTION))
    return floor_step(min(risk_qty, allocation_qty), step_size)

def validate_prices(entry, stop_trigger, stop_limit, take_profit, tick):
    entry, stop_trigger, stop_limit, take_profit, tick = map(D, (entry, stop_trigger, stop_limit, take_profit, tick))
    if tick <= 0: raise ValueError("Invalid price tick")
    for name, price in (("entry",entry),("stop trigger",stop_trigger),("stop limit",stop_limit),("take profit",take_profit)):
        if price <= 0 or price % tick != 0: raise ValueError(f"{name} must be positive and aligned to tick size {tick}")
    if not stop_limit <= stop_trigger < entry < take_profit:
        raise ValueError("Required BUY bracket: stop-limit <= stop-trigger < entry < take-profit.")
