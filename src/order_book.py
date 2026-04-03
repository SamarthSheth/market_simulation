from dataclasses import dataclass, field
from enum import Enum
import re
from typing import List
from collections import deque
from sortedcontainers import SortedDict

class Side(Enum):
    BUY = "buy"
    SELL = "sell"

class OrderType(Enum):
    LIMIT = "limit"
    MARKET = "market"

@dataclass
class Order:
    order_id: int
    side: Side
    price: float | None
    size: float
    timestamp: float
    order_type: OrderType
    trader_id: str
    
    def __post_init__(self):
        if not isinstance(self.side, Side):
            raise TypeError("side must be a Side enum")

        if not isinstance(self.order_type, OrderType):
            raise TypeError("order_type must be an OrderType enum")

        if self.size <= 0:
            raise ValueError("size must be positive")

        if self.order_type == OrderType.LIMIT:
            if self.price is None or self.price <= 0:
                raise ValueError("limit orders must have a positive price")

        if self.order_type == OrderType.MARKET:
            if self.price is not None:
                raise ValueError("market orders should not have a price")
        
@dataclass
class Trade:
    trade_id: int
    price: float
    size: float
    timestamp: float
    buyer_id: str
    seller_id: str
    incoming_order_id: int
    resting_order_id: int
        
class OrderBook:
    '''Price-time priority limit order book
    Bids: highest price willing to buy for are sorted descending by price, ascending by time
    Asks: lowest price willing to sell for are sorted ascending by price, ascending by time

    '''
    def __init__(self) -> None:
        self._bids: SortedDict[float, deque] = SortedDict() #like Map(price, deque(Orders)) will store 100, 99.5 like [-100, -99.5] so we can peekitem(0) to get the best bid
        self._asks: SortedDict[float, deque] = SortedDict()
        self._trade_log: List[Trade] = []
        self._next_trade_id: int = 0
        
    @property #so usage is book.best_bid
    def best_bid(self) -> float | None:
        if not self._bids:
            return None
        return -self._bids.peekitem(0)[0] #equiv to -self._bids.keys()[0]
    
    @property
    def best_ask(self) -> float | None:
        if not self._asks:
            return None
        return self._asks.peekitem(0)[0]
        
    def add_limit_order(self, order: Order):
        if order.order_type != OrderType.LIMIT:
            raise ValueError("Only limit orders can be added to the order book")
        
        book = self._asks if order.side == Side.BUY else self._bids
        trades = self._match(order, book, price_limit=order.price)
        if order.size > 0:
            rest_book = self._bids if order.side == Side.BUY else self._asks
            key = -order.price if order.side == Side.BUY else order.price # type: ignore
            if key not in rest_book:
                rest_book[key] = deque()
            rest_book[key].append(order)
        return trades
        
    def _match(self, order: Order, book: SortedDict, price_limit: float | None) -> List[Trade]:
        """Match an incoming order against resting orders.
        price_limit: None for market orders (match any price),
        order.price for limit orders (stop if resting price is worse)
        """
        # your existing while loop, but add a check:
        # if price_limit is set, break when resting price is worse
        trades : List[Trade] = []
        resting_side = Side.BUY if order.side == Side.SELL else Side.SELL
        while order.size > 0 and book:
            price_key, orders = book.peekitem(0) #best price level
            resting_price = -price_key if resting_side == Side.BUY else price_key
            if price_limit is not None:
                if (resting_side == Side.BUY and resting_price < price_limit) or (resting_side == Side.SELL and resting_price > price_limit):
                    break # stop matching if best resting price is worse than limit
            
            resting_order = orders[0]
            trade_size = min(order.size, resting_order.size)
            trade_price = resting_order.price
            
            # Log the trade
            trade = Trade(
                trade_id=self._next_trade_id,
                price=trade_price,
                size=trade_size,
                timestamp=order.timestamp,
                buyer_id=order.trader_id if order.side == Side.BUY else resting_order.trader_id,
                seller_id=order.trader_id if order.side == Side.SELL else resting_order.trader_id,
                incoming_order_id=order.order_id,
                resting_order_id=resting_order.order_id,
            )
            self._next_trade_id += 1
            self._trade_log.append(trade)
            trades.append(trade)
            
            # Execute the trade
            order.size -= trade_size
            resting_order.size -= trade_size
            
            # If the resting order is fully filled, remove it from the book
            if resting_order.size <= 0:
                orders.popleft()
                if not orders:
                    del book[price_key]
        return trades
    
    def best_price(self, side: Side) -> float | None:
        if side == Side.BUY:
            return self.best_bid
        else:
            return self.best_ask
    
    def orders_at_price(self, side: Side, price: float) -> List[Order]:
        book = self._bids if side == Side.BUY else self._asks
        price_key = -price if side == Side.BUY else price
        return list(book.get(price_key, []))
        
    
    
    def submit_market_order(self, order: Order) -> List[Trade]:
        if order.order_type != OrderType.MARKET:
            raise ValueError("Only market orders can be submitted")
        # Market orders are executed immediately against the best available price
        side = order.side
        book = self._asks if side == Side.BUY else self._bids #book has to be dual to order
        return self._match(order, book, price_limit=None) 

    def midprice(self):
        best_bid = self.best_bid
        best_ask = self.best_ask
        if best_bid is None or best_ask is None:
            return None
        return (best_bid + best_ask) / 2

    def spread(self):
        best_bid = self.best_bid
        best_ask = self.best_ask
        if best_bid is None or best_ask is None:
            return None
        return best_ask - best_bid

        