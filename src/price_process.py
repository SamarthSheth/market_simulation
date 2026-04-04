

from typing import List

import numpy as np
from order_book import OrderBook, Trade


class PriceProcess:
    def __init__(self, curr_price : float, curr_time : float, mu : float, sigma : float, rng : np.random.Generator) -> None:
        self.curr_price = curr_price #i might replace this with max(0.001, curr_price) to prevent negative prices
        self.curr_time = curr_time
        #self.config = config
        self.mu = mu
        self.sigma = sigma
        self.rng = rng
        self.history: List[tuple[float, float]] = [(curr_time, curr_price)]
        
    def step(self, dt: float) -> float:
        """Advance the true price by one time step. Returns new price."""
        # For simplicity, we model the price as am arithmetic Brownian motion with drift
        dW = self.rng.normal(0, np.sqrt(dt))
        dS = self.mu * dt + self.sigma * dW
        self.curr_price += dS
        self.curr_time += dt
        self.history.append((self.curr_time, self.curr_price))
        return self.curr_price
    
    def get_current_price(self) -> float:
        return self.curr_price
        
        