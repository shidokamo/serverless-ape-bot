# Ape Bot
# Parameter example
```
API_KEY = ************************************
API_SECRET = *********************************
API_PASS = ********************
LEVERAGE_INIT = 1.8
LEVERAGE_MIN = 1
LEVERAGE_DECAY = 0.3
LEVERAGE_REF_PRICE = 32000
MAX_INIT_PRICE = 42000
BASE = BTC
QUOTE = USDT
ORDER_SIZE = 10
NO_ORDER_LIMIT = 45000
TAKE_PROFIT_LIMIT_PRICE = 45800

NAME = ape-bot
REGION = ***********
SCHEDULER_SERVICE_ACCOUNT = ************e@*************.iam.gserviceaccount.com
URI = https://*************************.cloudfunctions.net/ape-bot
```


# Install
Python package installation is required.
If you are using `pipenv`, you can just run following command.

```
make install
```

# Testing bot
```
make run
```

# Deploy
```
make deploy
```

# Functions Log
```
make log
```
