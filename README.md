# sigmaTrading
This repo is for generic option portfolio optimisation code. 
Essentially we take the market data snapshot for a given instrument's option chain and then run a MIP model to tune the greeks.
Following that we compose a basket order that performs the portfolio rebalance. 
Nothing too fancy.

Currently the code does not include optimisation formulation ready for production. 
For compatibility I am including a play example that may or may not make sense.
Naturally, don't even think about using any of that for real production and trading.
