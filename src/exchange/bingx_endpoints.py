# ruff: noqa
# mypy: ignore-errors
"""
BingX API Endpoints for Auto-Trading
=====================================

Based on BingX API Documentation (swap/v2):
- /openApi/swap/v2/user/account - Get account info
- /openApi/swap/v2/trade/marginType - Set margin type (CROSS/ISOLATED)
- /openApi/swap/v2/trade/positionSide - Set position mode (HEDGE/ONE_WAY)
- /openApi/swap/v2/trade/leverage - Set leverage
- /openApi/swap/v2/quote/contracts - Get contract info (symbol specs)
- /openApi/swap/v2/trade/order - Place order (market with TP)
- /openApi/swap/v2/user/positions - Get positions
- /openApi/swap/v2/trade/openOrders - Get open orders
- /openApi/swap/v2/trade/order - Place/cancel TP order

Key parameters for order placement (BingX swap/v2/trade/order):
- symbol: trading pair (e.g., BTC-USDT)
- side: BUY or SELL
- positionSide: LONG or SHORT (required for Hedge Mode)
- type: MARKET, LIMIT, STOP_MARKET, TAKE_PROFIT_MARKET
- quantity: order quantity
- price: price for limit orders
- tpPrice: take profit price (for market/limit orders with TP)
- slPrice: stop loss price (NOT USED in our strategy)
- reduceOnly: true/false (for closing positions)
- workingType: MARK_PRICE or CONTRACT_PRICE
"""

# BingX API endpoint constants
BINGX_ENDPOINTS = {
    # Account
    "GET_ACCOUNT": "/openApi/swap/v2/user/account",
    "GET_BALANCE": "/openApi/swap/v2/user/balance",
    "GET_POSITIONS": "/openApi/swap/v2/user/positions",
    "GET_OPEN_ORDERS": "/openApi/swap/v2/trade/openOrders",

    # Trading
    "PLACE_ORDER": "/openApi/swap/v2/trade/order",
    "CANCEL_ORDER": "/openApi/swap/v2/trade/cancelOrder",
    "CANCEL_ALL_ORDERS": "/openApi/swap/v2/trade/cancelAllOrders",

    # Account settings
    "SET_LEVERAGE": "/openApi/swap/v2/trade/leverage",
    "SET_MARGIN_TYPE": "/openApi/swap/v2/trade/marginType",
    "SET_POSITION_MODE": "/openApi/swap/v2/trade/positionSide",

    # Market data
    "GET_CONTRACTS": "/openApi/swap/v2/quote/contracts",
    "GET_KLINES": "/openApi/swap/v3/quote/klines",
}

# Order types
ORDER_TYPES = {
    "MARKET": "MARKET",
    "LIMIT": "LIMIT",
    "STOP_MARKET": "STOP_MARKET",
    "TAKE_PROFIT_MARKET": "TAKE_PROFIT_MARKET",
}

# Position sides (Hedge Mode)
POSITION_SIDES = {
    "LONG": "LONG",
    "SHORT": "SHORT",
}

# Order sides
ORDER_SIDES = {
    "BUY": "BUY",
    "SELL": "SELL",
}

# Margin types
MARGIN_TYPES = {
    "CROSS": "CROSS",
    "ISOLATED": "ISOLATED",
}

# Position modes
POSITION_MODES = {
    "HEDGE": "HEDGE",
    "ONE_WAY": "ONE_WAY",
}
