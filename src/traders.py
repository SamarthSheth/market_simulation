'''Here I will implement the traders:

1. NoiseTrader: Submits market orders with random size and direction at random intervals.
2. InformedTrader: Trades with market orders too, but have knowledge of what the 'true' price should be

In the future I could try make them use limit orders but for experimental simplicity, 
they will only use market orders. 

'''
import numpy as np
from order_book import Order, OrderBook, Side, OrderType

class NoiseTrader:
    def __init__(self, trader_id: str, rng: np.random.Generator, order_rate: float):
        self.trader_id = trader_id
        self.rng = rng
        self.order_rate = order_rate
        self._next_order_id = 0
        
    def generate_market_order(self, book:OrderBook, timestamp: float, dt: float):
        '''using a poisson process to submit market orders'''
        lam = self.order_rate * dt
        num_orders = self.rng.poisson(lam=lam)
        for _ in range(num_orders):
            side = Side.BUY if self.rng.random() < 0.5 else Side.SELL #randomly choose buy or sell
            size = 1.0 #might change later to random size between 1 and 10
            order = Order(
                order_id=self._next_order_id,
                side=side,
                price=None, 
                size=size,
                timestamp=timestamp,
                order_type=OrderType.MARKET,
                trader_id=self.trader_id
            )
            book.submit_market_order(order)
            self._next_order_id += 1
        
    
class InformedTrader:
    def __init__(self, trader_id: str, rng: np.random.Generator, order_rate: float):
        self.trader_id = trader_id
        self.rng = rng
        self.order_rate = order_rate
        self._next_order_id = 0
        
    def generate_market_order(self, book:OrderBook, timestamp: float, dt: float, true_price: float):
        lam = self.order_rate * dt
        num_orders = self.rng.poisson(lam=lam)
        for _ in range(num_orders):
            if book.best_ask is not None and true_price > book.best_ask:
                side = Side.BUY
            elif book.best_bid is not None and true_price < book.best_bid:
                side = Side.SELL
            else:
                continue
            
            order = Order(
                order_id=self._next_order_id,
                side=side,
                price=None,
                size=1.0,
                timestamp=timestamp,
                order_type=OrderType.MARKET,
                trader_id=self.trader_id
            )
            book.submit_market_order(order)
            self._next_order_id += 1
    