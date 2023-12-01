import base64
import hmac
import datetime
import urllib.parse
from typing import Optional, Dict, Any, List

from requests import Request, Session, Response
import os
import sys
import logging
import json
import traceback

class FormatterJSON(logging.Formatter):
    def format(self, record):
        json_msg = {'message': record.msg}

        # Practically, we should add timestamp. However, cloud functions will add their own timestamp so it's commented out
        # record.asctime = self.formatTime(record, self.datefmt)
        # json_msg['time'] = record.asctime

        json_msg['level'] = record.levelname
        json_msg['severity'] = record.levelname
        return json.dumps(json_msg, ensure_ascii=False)

#
# Caution: This will overwrite record itself so if you are using multiple logger, they will be also affected.
#
RESET_SEQ = "\x1b[0m"
class FormatterColor(logging.Formatter):
    def color(self, level):
        match level:
            case 'WARNING':
                return "\x1b[1;43m" + level + RESET_SEQ
            case 'INFO':
                return "\x1b[1;42m" + level + RESET_SEQ
            case 'DEBUG':
                return "\x1b[1;47m" + level + RESET_SEQ
            case 'CRITICAL':
                return "\x1b[1;41m" + level + RESET_SEQ
            case 'ERROR':
                return "\x1b[1;41m" + level + RESET_SEQ
            case _:
                # If it's already colored. Do nothing.
                return level

    def format(self, record):
        record.levelname = self.color(record.levelname)
        return super().format(record)

logger = logging.getLogger('console')
if os.environ.get("PROD"):
    h = logging.StreamHandler()
    fmt = FormatterJSON()
    h.setFormatter(fmt)
    logger.addHandler(h)
else:
    h = logging.StreamHandler()
    fmt = FormatterColor('[%(asctime)s] [%(levelname)s] %(message)s')
    h.setFormatter(fmt)
    logger.addHandler(h)
logger.setLevel(logging.DEBUG)

class OkxClient:
    _ENDPOINT = 'https://www.okx.com/api/v5/' # Don't forget last '/'

    def __init__(self, api_key=None, api_secret=None, api_pass=None) -> None:
        self._session = Session()
        self._api_key = api_key
        self._api_secret = api_secret
        self._api_pass = api_pass

    def _get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Any:
        return self._request('GET', path, params=params)

    def _post(self, path: str, params: Optional[Dict[str, Any]] = None) -> Any:
        return self._request('POST', path, json=params)

    def _delete(self, path: str, params: Optional[Dict[str, Any]] = None) -> Any:
        return self._request('DELETE', path, json=params)

    def _request(self, method: str, path: str, **kwargs) -> Any:
        request = Request(method, self._ENDPOINT + path, **kwargs)
        self._sign_request(request)
        response = self._session.send(request.prepare())
        return self._process_response(response)

    def _sign_request(self, request: Request) -> None:
        ts = datetime.datetime.utcnow().isoformat(timespec='milliseconds') + 'Z'
        prepared = request.prepare()
        signature_payload = f'{ts}{prepared.method}{prepared.path_url}'.encode()
        if prepared.body:
            signature_payload += prepared.body
        signature = hmac.new(self._api_secret.encode(), signature_payload, 'sha256').digest()
        signature = base64.b64encode(signature)
        request.headers['OK-ACCESS-KEY'] = self._api_key
        request.headers['OK-ACCESS-SIGN'] = signature
        request.headers['OK-ACCESS-TIMESTAMP'] = str(ts)
        request.headers['OK-ACCESS-PASSPHRASE'] = self._api_pass

    def _process_response(self, response: Response) -> Any:
        try:
            data = response.json()
        except ValueError:
            response.raise_for_status()
            raise
        else:
            return data['data']

    def get_balance(self, coin: str) -> dict:
        return self._get(f'account/balance', {'ccy':coin})

    def place_limit_order(self, market: str, side: str, size: str, mode: str, price: str, post_only:bool) -> dict:
        return self._post('trade/order', {
                                     'instId': market,
                                     'tdMode': mode,
                                     'side': side,
                                     'sz': size,
                                     'px': price,
                                     'ordType': 'post_only',
                                     })

    def place_market_order(self, market: str, side: str, size: str, mode: str) -> dict:
        return self._post('trade/order', {
                                     'instId': market,
                                     'tdMode': mode,
                                     'side': side,
                                     'sz': size,
                                     'ordType': 'market'
                                     })

    def get_balances(self) -> List[dict]:
        return self._get('account/balance')[0]

    def get_positions(self, show_avg_price: bool = False) -> List[dict]:
        position_list = self._get('account/positions')
        return {position['instId']:position for position in position_list}

    def get_account_position_risk(self, type) -> List[dict]:
        return self._get('account/account-position-risk', {'instType': type})

    def get_order_book(self, market:str) -> dict:
        return self._get('market/books', {'instId': market, 'sz':'100'})[0]

# Note:
# In this case, we don't need to take care of performance but if is the best practice to use global variable
# for reusable objects like client object so that functions can cache it for next call.
key = os.environ.get("API_KEY")
if not key:
    raise Exception("API key is not provided")
secret = os.environ.get("API_SECRET")
if not secret:
    raise Exception("API secret is not provided")
passphrase = os.environ.get("API_PASS")
if not passphrase:
    raise Exception("API passphrase is not provided")
leverage_init = float(os.environ.get("LEVERAGE_INIT"))
if not leverage_init:
    raise Exception("Leverage init value is not provided.")
leverage_ref_price = float(os.environ.get("LEVERAGE_REF_PRICE"))
if not leverage_ref_price:
    raise Exception("Leverage reference price is not provided.")
leverage_decay = float(os.environ.get("LEVERAGE_DECAY"))
if not leverage_decay:
    raise Exception("Leverage decay parameter not provided.")
leverage_min = float(os.environ.get("LEVERAGE_MIN"))
if not leverage_min:
    raise Exception("Minimum leverage is not provided.")
max_init_price = os.environ.get("MAX_INIT_PRICE")
if not max_init_price:
    raise Exception("Max init price is not provided.")
quote = os.environ.get("QUOTE")
if not quote:
    raise Exception("Quote coin name is not provided")
if not quote in ['USDT']:
    raise Exception("Quote coin %s is not supported" % quote)
base = os.environ.get("BASE")
if not base:
    raise Exception("Base coin name is not provided")
if not base in ['BTC', 'ETH']:
    raise Exception("Base coin  %s is not supported" % base)
order_size = os.environ.get("ORDER_SIZE")
if not order_size:
    raise Exception("Order size is not provided.")
no_order_limit = float(os.environ.get("NO_ORDER_LIMIT"))
if not no_order_limit:
    raise Exception("No order limit is not specified.")
take_profit_limit = os.environ.get("TAKE_PROFIT_LIMIT_PRICE")
if not take_profit_limit:
    raise Exception("take profit limit is not specified.")

client = OkxClient(key, secret, passphrase)

def run(requests=None) -> None:
    global client
    global key
    global secret
    global passphrase
    global leverage_init
    global leverage_ref_price
    global leverage_decay
    global leverage_min
    global quote
    global base
    global order_size
    global no_orderr_limit
    global take_profit_limit
    try:
        spot_market =  base + '-' + quote
        logger.info("Spot market: %s" % spot_market)

        balances = client.get_balances()
        positions = client.get_positions()
        risks = client.get_account_position_risk('MARGIN')

        def get_coin_balance(balances) -> List[dict]:
            return {coin['ccy']:coin for coin in balances['details']}
        coins = get_coin_balance(balances)
        logger.debug(balances)
        logger.debug(coins)
        logger.debug(positions)
        logger.debug(risks)

        def get_leverage(balances) -> float:
            return float(balances['notionalUsd']) / float(balances['totalEq'])
        leverage_est = get_leverage(balances)

        def get_liq_price(balances, risks, coins) -> float:
            # Use cashBal for caluculation. Otherwise, it becomes huge.
            return (float(balances['mmr']) - float([x for x in risks[0]['balData'] if x['ccy'] == quote][0]['eq'])) / float(coins[base]['cashBal'])

        market = "%s-%s"%(base,quote)

        b = client.get_order_book(market)
        ask_best = b['asks'][0][0]
        bid_best = b['bids'][0][0]

        def get_desired_leverage():
            return max(leverage_init * ((leverage_ref_price / float(ask_best)) ** leverage_decay), leverage_min)
        leverage = get_desired_leverage()

        # Account is flesh or very few coin is remaining
        if (not base in coins or float(coins[base]['eqUsd']) < 1) and float(bid_best) > float(max_init_price):
            logger.warning("Init order can't be placed. Best bid > MAX_INIT_PRICE:%s" % max_init_price)
        # No order threshold
        elif float(bid_best) > no_order_limit:
            logger.warning("Best bid is greater than no order limit price. No buying order is made.")
        elif leverage_est / leverage < 0.99:
            logger.warning("There is buying power available. Put order")
            r = client.place_market_order(market=market, side="buy", size=order_size, mode='cross')
            logger.debug(r)

        # Sell orders
        if base in coins:
            if float(coins[base]['availBal'])*float(bid_best) < 1:
                logger.warning("There is no coins available for sell. Maybe we already placed limit order for all coins.")
            else:
                r = client.place_limit_order(market=market, side="sell", price=take_profit_limit, size=coins[base]['availBal'], post_only=False, mode='cross')
                logger.debug(r)

        def show_info() -> None:
            # Important information last
            logger.info("Initial Margin USD             : %s" % balances['imr'])
            logger.info("Maintenance Margin USD         : %s" % balances['mmr'])
            if balances['mgnRatio']:
                logger.info("Margin Ratio %%                 : %f" % (float(balances['mgnRatio']) * 100))
            if base in coins:
                logger.info("%-10s balance free        : %s" % (base, coins[base]['availBal']))
                logger.info("%-10s balance total       : %s" % (base, coins[base]['cashBal']))
                logger.info("%-10s balance USD         : %s" % (base, coins[base]['eqUsd']))
            if quote in coins:
                logger.info("%-10s balance free        : %s" % (quote, coins[quote]['availBal']))
                logger.info("%-10s balance total       : %s" % (quote, coins[quote]['cashBal']))
                logger.info("%-10s balance USD         : %s" % (quote, coins[quote]['eqUsd']))
            logger.info("Total notional value USD       : %s" % balances['notionalUsd'])
            logger.info("Total net USD                  : %s" % balances['adjEq'])
            logger.info("Best ask                       : %s" % ask_best)
            logger.info("Best bid                       : %s" % bid_best)
            logger.info("Sell order price               : %s" % take_profit_limit)
            if base in coins and quote in coins:
                liq_price_est = get_liq_price(balances, risks, coins)
                logger.info("Estimated Liq Price            : %f" % liq_price_est)
            logger.info("Current target leverage        : %s" % leverage)
            logger.info("Leverage                       : %f" % leverage_est)
            logger.info("Total equity USD               : %s" % balances['totalEq'])
        show_info()


        return 'OK' # HTTP request return value should be specifi
    except Exception as e:
        logger.exception("Exception in run command.")
        exc_info = sys.exc_info()
        logger.exception(traceback.format_exception(*exc_info))
        return 'ERROR' # HTTP request return value should be specifi

if __name__ == "__main__":
    run()

