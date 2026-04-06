from dataclasses import dataclass
from typing import List, Optional
from order_book import OrderBook, Trade, Order, Side, OrderType

@dataclass
class MMState:
    timestamp: float
    inventory: float
    cash: float
    mid_price: float
    bid_quote: Optional[float]
    ask_quote: Optional[float]
    mark_to_market_pnl: float
    

class MarketMaker:
    def __init__(self, trader_id, half_spread, inventory_skew, max_position, order_size):
        self.trader_id = trader_id
        self.half_spread = half_spread
        self.inventory_skew = inventory_skew
        self.max_position = max_position
        self.order_size = order_size
        
        # State variables
        self.inventory = 0.0
        self.cash = 0.0
        self.state_history: List[MMState] = []
        self._next_order_id = 0
        self._last_trade_idx = 0

    def update(self, book: OrderBook, timestamp: float):
        """Orchestrates: process fills, cancel, compute, place, record."""
        self._process_fills(book)
        book.cancel_trader_orders(self.trader_id)
        mid = book.midprice()
        if mid is None:
            mid = self.state_history[-1].mid_price if self.state_history else 100.0 # default mid price if no history
            
        bid, ask = self._compute_quotes(mid)

        if bid is not None:
            order = Order(
                order_id=self._next_order_id,
                side=Side.BUY,
                price=bid,
                size=self.order_size,
                timestamp=timestamp,
                order_type=OrderType.LIMIT,
                trader_id=self.trader_id,
            )
            book.add_limit_order(order)
            self._next_order_id += 1

        if ask is not None:
            order = Order(
                order_id=self._next_order_id,
                side=Side.SELL,
                price=ask,
                size=self.order_size,
                timestamp=timestamp,
                order_type=OrderType.LIMIT,
                trader_id=self.trader_id,
            )
            book.add_limit_order(order)
            self._next_order_id += 1

        mtm = self.cash + self.inventory * mid
        self.state_history.append(MMState(
            timestamp=timestamp,
            inventory=self.inventory,
            cash=self.cash,
            mid_price=mid,
            bid_quote=bid,
            ask_quote=ask,
            mark_to_market_pnl=mtm,
        ))
        

    def _process_fills(self, book: OrderBook):
        """Update inventory and cash from new trades."""
        new_trades = book._trade_log[self._last_trade_idx:]
        self._last_trade_idx = len(book._trade_log)

        for trade in new_trades:
            if trade.buyer_id == self.trader_id:
                self.inventory += trade.size
                self.cash -= trade.price * trade.size
            elif trade.seller_id == self.trader_id:
                self.inventory -= trade.size
                self.cash += trade.price * trade.size
        

    def _compute_quotes(self, mid: float) -> tuple[Optional[float], Optional[float]]:
        """Return (bid, ask) quotes based on observed midprice and inventory."""
        skew = self.inventory_skew * self.inventory

        bid: Optional[float] = mid - self.half_spread - skew
        ask: Optional[float] = mid + self.half_spread - skew

        if self.inventory >= self.max_position:
            bid = None
        if self.inventory <= -self.max_position:
            ask = None

        if bid is not None and bid <= 0:
            bid = None
        if ask is not None and ask <= 0:
            ask = None

        if bid is not None and ask is not None and bid >= ask:
            center = (bid + ask) / 2.0
            bid = center - 1e-6
            ask = center + 1e-6

        return bid, ask

    def get_total_pnl(self, true_price: float) -> float:
        return self.cash + self.inventory * true_price