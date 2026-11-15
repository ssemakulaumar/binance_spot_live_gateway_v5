"""Minimal standard-library Binance Spot REST client."""
import hashlib, hmac, json, time, urllib.parse, urllib.request
from decimal import Decimal
from config import BASE_URL, API_KEY, API_SECRET, RECV_WINDOW_MS, HTTP_TIMEOUT_SECONDS

class BinanceAPIError(RuntimeError):
    pass

class BinanceClient:
    def __init__(self):
        if not BASE_URL:
            raise BinanceAPIError("Paper mode has no exchange client.")
        if not API_KEY or not API_SECRET:
            env = "BINANCE_LIVE_API_KEY/SECRET" if BASE_URL == "https://api.binance.com" else "BINANCE_TESTNET_API_KEY/SECRET"
            raise BinanceAPIError(f"Missing {env}; never paste API keys into chat.")
        self.api_key, self.secret = API_KEY, API_SECRET.encode()

    def _request(self, method, path, params=None, signed=False):
        params = dict(params or {})
        headers = {"X-MBX-APIKEY": self.api_key}
        if signed:
            params["timestamp"] = int(time.time() * 1000)
            params["recvWindow"] = RECV_WINDOW_MS
            query = urllib.parse.urlencode(params)
            params["signature"] = hmac.new(self.secret, query.encode(), hashlib.sha256).hexdigest()
        query = urllib.parse.urlencode(params)
        url = BASE_URL + path + (("?" + query) if query and method == "GET" else "")
        data = query.encode() if query and method != "GET" else None
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT_SECONDS) as resp:
                return json.loads(resp.read().decode())
        except Exception as exc:
            body = ""
            if hasattr(exc, "read"):
                try: body = exc.read().decode(errors="replace")[:1000]
                except Exception: pass
            raise BinanceAPIError(f"Binance request failed: {exc}; {body}") from exc

    def account(self): return self._request("GET", "/api/v3/account", signed=True)
    def exchange_info(self, symbol=None):
        return self._request("GET", "/api/v3/exchangeInfo", {"symbol": symbol} if symbol else None)
    def ticker_price(self, symbol):
        return Decimal(self._request("GET", "/api/v3/ticker/price", {"symbol": symbol})["price"])
    def test_order(self, params): return self._request("POST", "/api/v3/order/test", params, signed=True)
    def place_otoco(self, params):
        # Atomic entry + contingent OCO exit list. Protective legs activate after working order fills.
        return self._request("POST", "/api/v3/orderList/otoco", params, signed=True)
    def query_order(self, symbol, client_order_id):
        return self._request("GET", "/api/v3/order", {"symbol": symbol, "origClientOrderId": client_order_id}, signed=True)
