                     key=lambda x: x[1], reverse=True)
```

---

## Optimization Algorithms

### 1. Portfolio Optimization

```python
import cvxpy as cp
from scipy.optimize import differential_evolution

class PortfolioOptimizer:
    """
    Advanced portfolio optimization techniques for crypto portfolios.
    Handles non-normal returns, tail risk, and dynamic rebalancing.
    """
    
    def __init__(self, returns_df):
        self.returns = returns_df
        self.mean_returns = returns_df.mean()
        self.cov_matrix = returns_df.cov()
        self.n_assets = len(returns_df.columns)
    
    def markowitz_optimization(self, target_return=None, risk_free_rate=0.0):
        """
        Classic mean-variance optimization.
        Minimize: w^T Σ w (portfolio variance)
        Subject to: w^T μ >= target_return, Σw = 1, w >= 0
        """
        w = cp.Variable(self.n_assets)
        
        # Objective: minimize portfolio variance
        portfolio_variance = cp.quad_form(w, self.cov_matrix.values)
        objective = cp.Minimize(portfolio_variance)
        
        # Constraints
        constraints = [
            cp.sum(w) == 1,  # Fully invested
            w >= 0  # No short selling
        ]
        
        if target_return is not None:
            expected_return = self.mean_returns.values @ w
            constraints.append(expected_return >= target_return)
        
        # Solve
        problem = cp.Problem(objective, constraints)
        problem.solve()
        
        if w.value is None:
            return None
        
        weights = pd.Series(w.value, index=self.returns.columns)
        
        return {
            'weights': weights,
            'expected_return': float(self.mean_returns @ weights),
            'volatility': float(np.sqrt(weights @ self.cov_matrix @ weights)),
            'sharpe_ratio': float((self.mean_returns @ weights - risk_free_rate) / 
                                 np.sqrt(weights @ self.cov_matrix @ weights))
        }
    
    def risk_parity_optimization(self):
        """
        Risk parity: allocate capital so each asset contributes equally to risk.
        More robust than mean-variance in crypto (non-normal returns).
        """
        def risk_contribution(weights):
            """Calculate risk contribution of each asset."""
            portfolio_vol = np.sqrt(weights @ self.cov_matrix @ weights)
            marginal_contrib = self.cov_matrix @ weights
            risk_contrib = weights * marginal_contrib / portfolio_vol
            return risk_contrib
        
        def objective(weights):
            """Minimize variance of risk contributions."""
            rc = risk_contribution(weights)
            target_rc = np.ones(self.n_assets) / self.n_assets
            return np.sum((rc - target_rc) ** 2)
        
        # Constraints
        constraints = [
            {'type': 'eq', 'fun': lambda w: np.sum(w) - 1}
        ]
        bounds = [(0, 1) for _ in range(self.n_assets)]
        
        # Initial guess: equal weights
        initial_weights = np.ones(self.n_assets) / self.n_assets
        
        # Optimize
        from scipy.optimize import minimize
        result = minimize(
            objective,
            initial_weights,
            method='SLSQP',
            bounds=bounds,
            constraints=constraints
        )
        
        weights = pd.Series(result.x, index=self.returns.columns)
        
        return {
            'weights': weights,
            'risk_contributions': risk_contribution(result.x)
        }
    
    def cvar_optimization(self, alpha=0.05, target_return=None):
        """
        Conditional Value at Risk (CVaR) optimization.
        Minimize tail risk instead of variance.
        Better for crypto (fat tails, extreme events).
        """
        w = cp.Variable(self.n_assets)
        
        # CVaR variables
        n_scenarios = len(self.returns)
        losses = -self.returns.values @ w  # Negative returns = losses
        
        # CVaR formulation
        var = cp.Variable()  # Value at Risk
        z = cp.Variable(n_scenarios)  # Auxiliary variables
        
        # CVaR = VaR + (1/α) * E[max(loss - VaR, 0)]
        cvar = var + (1 / (alpha * n_scenarios)) * cp.sum(z)
        
        objective = cp.Minimize(cvar)
        
        # Constraints
        constraints = [
            cp.sum(w) == 1,
            w >= 0,
            z >= 0,
            z >= losses - var
        ]
        
        if target_return is not None:
            expected_return = self.mean_returns.values @ w
            constraints.append(expected_return >= target_return)
        
        # Solve
        problem = cp.Problem(objective, constraints)
        problem.solve()
        
        weights = pd.Series(w.value, index=self.returns.columns)
        
        return {
            'weights': weights,
            'cvar': cvar.value,
            'var': var.value
        }
    
    def black_litterman_optimization(self, views, view_confidences):
        """
        Black-Litterman: combine market equilibrium with investor views.
        Useful when you have strong convictions about certain assets.
        
        Args:
            views: dict {asset: expected_return}
            view_confidences: dict {asset: confidence_level}
        """
        # Market equilibrium returns (reverse optimization)
        market_weights = np.ones(self.n_assets) / self.n_assets
        risk_aversion = 2.5
        pi = risk_aversion * self.cov_matrix @ market_weights
        
        # Build view matrix
        P = np.zeros((len(views), self.n_assets))
        Q = np.zeros(len(views))
        
        for i, (asset, expected_return) in enumerate(views.items()):
            asset_idx = self.returns.columns.get_loc(asset)
            P[i, asset_idx] = 1
            Q[i] = expected_return
        
        # View uncertainty (Omega matrix)
        tau = 0.025  # Scaling factor for uncertainty
        Omega = np.diag([1 / view_confidences[asset] for asset in views.keys()])
        
        # Black-Litterman formula
        Sigma = self.cov_matrix.values
        M_inverse = np.linalg.inv(tau * Sigma)
        Omega_inverse = np.linalg.inv(Omega)
        
        posterior_mean = np.linalg.inv(M_inverse + P.T @ Omega_inverse @ P) @ \
                        (M_inverse @ pi + P.T @ Omega_inverse @ Q)
        
        posterior_cov = np.linalg.inv(M_inverse + P.T @ Omega_inverse @ P)
        
        # Optimize with posterior distribution
        w = cp.Variable(self.n_assets)
        objective = cp.Minimize(cp.quad_form(w, posterior_cov))
        
        constraints = [
            cp.sum(w) == 1,
            w >= 0,
            posterior_mean @ w >= self.mean_returns.mean()
        ]
        
        problem = cp.Problem(objective, constraints)
        problem.solve()
        
        weights = pd.Series(w.value, index=self.returns.columns)
        
        return {
            'weights': weights,
            'posterior_returns': posterior_mean,
            'posterior_cov': posterior_cov
        }
    
    def genetic_algorithm_optimization(self, fitness_function, generations=100):
        """
        Genetic algorithm for portfolio optimization.
        Can handle complex, non-convex objective functions.
        """
        def fitness_wrapper(weights):
            """Wrapper to ensure constraints and calculate fitness."""
            # Normalize weights
            weights = weights / np.sum(weights)
            
            # Calculate metrics
            portfolio_return = self.mean_returns @ weights
            portfolio_vol = np.sqrt(weights @ self.cov_matrix @ weights)
            sharpe = portfolio_return / portfolio_vol if portfolio_vol > 0 else 0
            
            # Custom fitness (can incorporate multiple objectives)
            return -fitness_function(weights, portfolio_return, portfolio_vol, sharpe)
        
        # Bounds for each asset weight
        bounds = [(0, 1) for _ in range(self.n_assets)]
        
        # Run differential evolution
        result = differential_evolution(
            fitness_wrapper,
            bounds,
            strategy='best1bin',
            maxiter=generations,
            popsize=50,
            mutation=(0.5, 1.5),
            recombination=0.7
        )
        
        # Normalize final weights
        optimal_weights = result.x / np.sum(result.x)
        weights = pd.Series(optimal_weights, index=self.returns.columns)
        
        return {
            'weights': weights,
            'fitness_score': -result.fun
        }
    
    def hierarchical_risk_parity(self):
        """
        Hierarchical Risk Parity (HRP) by Marcos Lopez de Prado.
        Uses machine learning clustering for robust allocation.
        """
        from scipy.cluster.hierarchy import linkage, dendrogram
        from scipy.spatial.distance import squareform
        
        # Step 1: Tree clustering based on correlation
        corr_matrix = self.returns.corr()
        distances = np.sqrt((1 - corr_matrix) / 2)  # Distance metric
        
        # Hierarchical clustering
        linkage_matrix = linkage(squareform(distances.values), method='single')
        
        # Step 2: Quasi-diagonalization
        def get_quasi_diag(link):
            """Sort assets by hierarchical tree structure."""
            link = link.astype(int)
            sort_ix = pd.Series([link[-1, 0], link[-1, 1]])
            num_items = link[-1, 3]
            
            while sort_ix.max() >= num_items:
                sort_ix.index = range(0, sort_ix.shape[0] * 2, 2)
                df0 = sort_ix[sort_ix >= num_items]
                i = df0.index
                j = df0.values - num_items
                sort_ix[i] = link[j, 0]
                df0 = pd.Series(link[j, 1], index=i + 1)
                sort_ix = sort_ix.append(df0)
                sort_ix = sort_ix.sort_index()
                sort_ix.index = range(sort_ix.shape[0])
            
            return sort_ix.tolist()
        
        sorted_ix = get_quasi_diag(linkage_matrix)
        sorted_assets = self.returns.columns[sorted_ix]
        
        # Step 3: Recursive bisection for weight allocation
        def get_cluster_var(cov, cluster_items):
            """Calculate cluster variance."""
            cov_slice = cov.loc[cluster_items, cluster_items]
            w = self.get_ivp(cov_slice)
            cluster_var = np.dot(np.dot(w, cov_slice), w)
            return cluster_var
        
        def get_recursive_bisection(cov, sorted_items):
            """Recursive bisection to allocate weights."""
            weights = pd.Series(1, index=sorted_items)
            cluster_items = [sorted_items]
            
            while len(cluster_items) > 0:
                cluster_items = [
                    i[j:k] for i in cluster_items
                    for j, k in ((0, len(i) // 2), (len(i) // 2, len(i)))
                    if len(i) > 1
                ]
                
                for i in range(0, len(cluster_items), 2):
                    cluster0 = cluster_items[i]
                    cluster1 = cluster_items[i + 1]
                    
                    var0 = get_cluster_var(cov, cluster0)
                    var1 = get_cluster_var(cov, cluster1)
                    
                    alpha = 1 - var0 / (var0 + var1)
                    
                    weights[cluster0] *= alpha
                    weights[cluster1] *= 1 - alpha
            
            return weights
        
        # Get inverse variance portfolio weights
        weights = get_recursive_bisection(self.cov_matrix, sorted_assets.tolist())
        
        return {
            'weights': weights,
            'sorted_assets': sorted_assets
        }
    
    def get_ivp(self, cov):
        """Inverse variance portfolio weights."""
        ivp = 1 / np.diag(cov)
        ivp /= ivp.sum()
        return ivp
```

### 2. Execution Optimization

```python
class ExecutionOptimizer:
    """
    Optimal trade execution to minimize market impact and slippage.
    Implements TWAP, VWAP, and adaptive algorithms.
    """
    
    def __init__(self, orderbook_data, historical_volume):
        self.orderbook = orderbook_data
        self.historical_volume = historical_volume
    
    def twap_schedule(self, total_quantity, duration_minutes, num_slices):
        """
        Time-Weighted Average Price (TWAP).
        Split order equally over time.
        
        Best for: Non-urgent orders, minimizing timing risk.
        """
        slice_size = total_quantity / num_slices
        time_interval = duration_minutes / num_slices
        
        schedule = []
        for i in range(num_slices):
            schedule.append({
                'time': i * time_interval,
                'quantity': slice_size,
                'percentage': 100 / num_slices
            })
        
        return schedule
    
    def vwap_schedule(self, total_quantity, duration_minutes, 
                     volume_profile, num_slices):
        """
        Volume-Weighted Average Price (VWAP).
        Match execution to historical volume patterns.
        
        Best for: Large orders, following market rhythm.
        """
        # Estimate volume for each time slice based on historical pattern
        slice_duration = duration_minutes / num_slices
        
        expected_volumes = []
        total_expected_volume = 0
        
        for i in range(num_slices):
            # Get historical volume for this time window
            time_of_day = (i * slice_duration) % (24 * 60)  # Minutes since midnight
            volume = self.estimate_volume_for_time(time_of_day, volume_profile)
            expected_volumes.append(volume)
            total_expected_volume += volume
        
        # Allocate quantity proportional to expected volume
        schedule = []
        for i, volume in enumerate(expected_volumes):
            slice_quantity = total_quantity * (volume / total_expected_volume)
            schedule.append({
                'time': i * slice_duration,
                'quantity': slice_quantity,
                'percentage': (volume / total_expected_volume) * 100
            })
        
        return schedule
    
    def estimate_volume_for_time(self, time_minutes, volume_profile):
        """
        Estimate expected volume based on time of day.
        Crypto has distinct intraday patterns.
        """
        # Convert to hour
        hour = int(time_minutes / 60)
        
        # Typical crypto volume profile (peaks at market open/close times)
        if hour in [0, 1, 8, 9, 16, 17]:  # High activity hours (UTC)
            return volume_profile['high']
        elif hour in [2, 3, 4, 5, 6]:  # Low activity hours
            return volume_profile['low']
        else:
            return volume_profile['medium']
    
    def almgren_chriss_schedule(self, total_quantity, duration_minutes,
                                volatility, risk_aversion=1e-6):
        """
        Almgren-Chriss optimal execution.
        Balances market impact vs price risk.
        
        Minimize: Market Impact Cost + Risk Aversion × Price Risk
        """
        # Parameters
        T = duration_minutes / (60 * 24)  # Convert to days
        sigma = volatility  # Daily volatility
        
        # Temporary impact (immediate)
        epsilon = 0.1  # Price impact coefficient
        
        # Permanent impact (lasting)
        eta = 0.01  # Permanent impact coefficient
        
        # Calculate optimal trajectory
        lambda_param = risk_aversion * sigma ** 2
        
        # Trading rate parameter
        kappa = np.sqrt(lambda_param / (epsilon * T))
        
        # Optimal trajectory: exponential decay
        num_steps = int(duration_minutes)
        t_points = np.linspace(0, T, num_steps)
        
        # Almgren-Chriss formula
        tau = T - t_points
        holdings = total_quantity * np.sinh(kappa * tau) / np.sinh(kappa * T)
        
        # Convert holdings to trade schedule
        schedule = []
        for i in range(len(holdings) - 1):
            trade_quantity = holdings[i] - holdings[i + 1]
            schedule.append({
                'time': i,
                'quantity': trade_quantity,
                'remaining': holdings[i + 1]
            })
        
        return schedule
    
    def adaptive_schedule(self, total_quantity, duration_minutes,
                         real_time_data_feed):
        """
        Adaptive execution: adjust in real-time based on market conditions.
        
        Factors:
        - Order book depth
        - Recent volatility
        - Momentum
        - Other large orders detected
        """
        executed = 0
        remaining = total_quantity
        current_time = 0
        schedule = []
        
        while remaining > 0 and current_time < duration_minutes:
            # Get current market state
            market_state = real_time_data_feed.get_current_state()
            
            # Calculate urgency score (0-1)
            urgency = self.calculate_urgency(
                market_state,
                remaining,
                duration_minutes - current_time
            )
            
            # Calculate optimal slice size
            slice_size = self.calculate_adaptive_slice(
                remaining,
                urgency,
                market_state['orderbook_depth'],
                market_state['volatility']
            )
            
            # Clip to orderbook depth (avoid excessive impact)
            max_safe_size = market_state['orderbook_depth'] * 0.1
            slice_size = min(slice_size, max_safe_size)
            
            schedule.append({
                'time': current_time,
                'quantity': slice_size,
                'urgency': urgency,
                'market_conditions': market_state
            })
            
            executed += slice_size
            remaining -= slice_size
            current_time += 1  # Advance 1 minute
        
        return schedule
    
    def calculate_urgency(self, market_state, remaining_qty, 
                         remaining_time):
        """
        Calculate how urgently we need to execute.
        
        Higher urgency when:
        - Strong momentum against us
        - High volatility
        - Running out of time
        - Large orders detected
        """
        # Time pressure
        time_pressure = 1 - (remaining_time / self.initial_duration)
        
        # Momentum pressure
        momentum = market_state.get('momentum', 0)
        momentum_pressure = max(0, momentum) if self.side == 'buy' else max(0, -momentum)
        
        # Volatility pressure
        vol_pressure = min(1, market_state['volatility'] / market_state['avg_volatility'])
        
        # Combine factors
        urgency = 0.4 * time_pressure + 0.3 * momentum_pressure + 0.3 * vol_pressure
        
        return np.clip(urgency, 0, 1)
    
    def calculate_adaptive_slice(self, remaining, urgency, 
                                 depth, volatility):
        """
        Calculate optimal slice size based on urgency and market depth.
        """
        # Base slice: divide remaining equally over time
        base_slice = remaining * 0.05  # 5% per slice
        
        # Adjust for urgency
        urgency_multiplier = 1 + urgency
        
        # Adjust for depth (trade more when deep orderbook)
        depth_multiplier = np.log1p(depth / remaining)
        
        # Adjust for volatility (trade faster in low vol, slower in high vol)
        vol_multiplier = 1 / (1 + volatility)
        
        optimal_slice = base_slice * urgency_multiplier * depth_multiplier * vol_multiplier
        
        return optimal_slice
    
    def minimize_slippage(self, target_quantity, max_slippage_bps=10):
        """
        Execute order while keeping slippage below threshold.
        Uses orderbook analysis.
        """
        executed = 0
        trades = []
        
        # Walk through orderbook levels
        for level in self.orderbook['asks']:  # Assuming buy order
            price = level['price']
            size = level['size']
            
            # Calculate slippage for this level
            mid_price = self.get_mid_price()
            slippage_bps = (price - mid_price) / mid_price * 10000
            
            if slippage_bps > max_slippage_bps:
                break  # Stop if slippage exceeds threshold
            
            # Execute at this level
            trade_size = min(size, target_quantity - executed)
            
            trades.append({
                'price': price,
                'quantity': trade_size,
                'slippage_bps': slippage_bps
            })
            
            executed += trade_size
            
            if executed >= target_quantity:
                break
        
        return trades, executed
    
    def get_mid_price(self):
        """Calculate current mid price from orderbook."""
        best_bid = self.orderbook['bids'][0]['price']
        best_ask = self.orderbook['asks'][0]['price']
        return (best_bid + best_ask) / 2
```

---

## Strategy Implementation

### 1. High-Frequency Trading Strategy

```python
class HighFrequencyStrategy:
    """
    Microsecond-level trading using signal processing and ML.
    Exploits short-term market microstructure inefficiencies.
    """
    
    def __init__(self, symbol, exchange_api):
        self.symbol = symbol
        self.exchange = exchange_api
        
        # Signal processors
        self.butterworth = SignalProcessor(cutoff_freq=0.2, order=4)
        self.fourier = FourierAnalyzer(window_size=256)
        self.kalman = AdaptiveKalmanFilter()
        
        # ML model for tick prediction
        self.tick_predictor = self.build_tick_predictor()
        
        # State tracking
        self.orderbook_history = []
        self.trade_history = []
    
    def build_tick_predictor(self):
        """
        Neural network for predicting next tick movement.
        """
        import torch.nn as nn
        
        class TickPredictor(nn.Module):
            def __init__(self, input_dim=50):
                super(TickPredictor, self).__init__()
                
                self.layers = nn.Sequential(
                    nn.Linear(input_dim, 128),
                    nn.ReLU(),
                    nn.BatchNorm1d(128),
                    nn.Dropout(0.2),
                    
                    nn.Linear(128, 64),
                    nn.ReLU(),
                    nn.BatchNorm1d(64),
                    nn.Dropout(0.2),
                    
                    nn.Linear(64, 32),
                    nn.ReLU(),
                    
                    nn.Linear(32, 3)  # [down, neutral, up]
                )
            
            def forward(self, x):
                return self.layers(x)
        
        return TickPredictor()
    
    def process_tick(self, tick_data):
        """
        Process incoming tick and make trading decision.
        Sub-millisecond latency critical.
        """
        # Extract features
        features = self.extract_hft_features(tick_data)
        
        # Predict next movement
        prediction = self.tick_predictor(torch.tensor(features).float())
        probabilities = torch.softmax(prediction, dim=0).detach().numpy()
        
        # Generate signal
        if probabilities[2] > 0.6:  # High confidence up
            signal = 'BUY'
            confidence = probabilities[2]
        elif probabilities[0] > 0.6:  # High confidence down
            signal = 'SELL'
            confidence = probabilities[0]
        else:
            signal = 'HOLD'
            confidence = probabilities[1]
        
        return signal, confidence
    
    def extract_hft_features(self, tick_data):
        """
        Extract features from tick data for HFT model.
        """
        features = []
        
        # Price features
        features.append(tick_data['price'])
        features.append(tick_data['price_change'])
        features.append(tick_data['price_acceleration'])
        
        # Orderbook imbalance
        bid_depth = sum([l['size'] for l in tick_data['orderbook']['bids'][:5]])
        ask_depth = sum([l['size'] for l in tick_data['orderbook']['asks'][:5]])
        imbalance = (bid_depth - ask_depth) / (bid_depth + ask_depth)
        features.append(imbalance)
        
        # Spread
        spread = tick_data['orderbook']['asks'][0]['price'] - \
                tick_data['orderbook']['bids'][0]['price']
        features.append(spread)
        
        # Volume intensity
        features.append(tick_data['volume'])
        features.append(tick_data['volume_ma_ratio'])
        
        # Trade flow toxicity
        features.append(tick_data['buy_volume'] - tick_data['sell_volume'])
        
        # Microstructure features
        features.extend(self.calculate_microstructure_features(tick_data))
        
        return np.array(features)
    
    def calculate_microstructure_features(self, tick_data):
        """
        Advanced microstructure features.
        """
        # Effective spread
        mid_price = (tick_data['orderbook']['bids'][0]['price'] + 
                    tick_data['orderbook']['asks'][0]['price']) / 2
        
        effective_spread = 2 * abs(tick_data['price'] - mid_price)
        
        # Roll measure (spread estimator from trades)
        if len(self.trade_history) >= 2:
            price_changes = np.diff([t['price'] for t in self.trade_history[-10:]])
            roll_measure = 2 * np.sqrt(-np.cov(price_changes[:-1], price_changes[1:])[0,1])
        else:
            roll_measure = 0
        
        # Kyle's lambda (price impact)
        if tick_data['volume'] > 0:
            kyle_lambda = abs(tick_data['price_change']) / tick_data['volume']
        else:
            kyle_lambda = 0
        
        return [effective_spread, roll_measure, kyle_lambda]
    
    def execute_hft_trade(self, signal, confidence):
        """
        Execute trade with minimal latency.
        """
        if confidence < 0.7:
            return  # Skip low-confidence signals
        
        # Determine position size based on confidence
        base_size = 100  # Base position size
        position_size = base_size * confidence
        
        # Place limit order at best price
        if signal == 'BUY':
            price = self.exchange.get_best_bid() + 0.01  # Slightly aggressive
            order = self.exchange.place_limit_order(
                symbol=self.symbol,
                side='buy',
                price=price,
                quantity=position_size
            )
        elif signal == 'SELL':
            price = self.exchange.get_best_ask() - 0.01
            order = self.exchange.place_limit_order(
                symbol=self.symbol,
                side='sell',
                price=price,
                quantity=position_size
            )
        
        # Set aggressive timeout (cancel if not filled in 100ms)
        self.set_order_timeout(order['id'], timeout_ms=100)


### 2. Statistical Arbitrage Strategy

```python
class StatisticalArbitrageStrategy:
    """
    Pairs trading and statistical arbitrage across crypto assets.
    Exploits mean-reversion in cointegrated pairs.
    """
    
    def __init__(self, universe):
        self.universe = universe
        self.pairs = []
        self.positions = {}
    
    def find_cointegrated_pairs(self, price_data, significance=0.05):
        """
        Test all pairs for cointegration using Engle-Granger test.
        """
        from statsmodels.tsa.stattools import coint
        
        assets = price_data.columns
        cointegrated_pairs = []
        
        for i in range(len(assets)):
            for j in range(i + 1, len(assets)):
                asset1, asset2 = assets[i], assets[j]
                
                # Test cointegration
                score, pvalue, _ = coint(
                    price_data[asset1],
                    price_data[asset2]
                )
                
                if pvalue < significance:
                    # Found cointegrated pair
                    spread = self.calculate_spread(
                        price_data[asset1],
                        price_data[asset2]
                    )
                    
                    cointegrated_pairs.append({
                        'asset1': asset1,
                        'asset2': asset2,
                        'pvalue': pvalue,
                        'spread_mean': spread.mean(),
                        'spread_std': spread.std(),
                        'half_life': self.calculate_half_life(spread)
                    })
        
        self.pairs = cointegrated_pairs
        return cointegrated_pairs
    
    def calculate_spread(self, series1, series2):
        """
        Calculate cointegrated spread using hedge ratio.
        """
        # Linear regression to find hedge ratio
        from sklearn.linear_model import LinearRegression
        
        X = series1.values.reshape(-1, 1)
        y = series2.values
        
        model = LinearRegression()
        model.fit(X, y)
        
        hedge_ratio = model.coef_[0]
        
        # Spread = series2 - hedge_ratio * series1
        spread = series2 - hedge_ratio * series1
        
        return spread
    
    def calculate_half_life(self, spread):
        """
        Calculate mean-reversion half-life using Ornstein-Uhlenbeck process.
        Shorter half-life = faster mean reversion = better for trading.
        """
        spread_lag = spread.shift(1).dropna()
        spread_diff = spread.diff().dropna()
        
        # Align indices
        spread_lag = spread_lag[spread_diff.index]
        
        # Regression: Δspread = λ(μ - spread_lag) + ε
        # Rearrange: Δspread = α + β*spread_lag + ε
        X = spread_lag.values.reshape(-1, 1)
        y = spread_diff.values
        
        from sklearn.linear_model import LinearRegression
        model = LinearRegression()
        model.fit(X, y)
        
        lambda_param = -model.coef_[0]
        
        # Half-life = ln(2) / λ
        half_life = np.log(2) / lambda_param if lambda_param > 0 else np.inf
        
        return half_life
    
    def generate_signals(self, current_prices):
        """
        Generate trading signals based on spread deviations.
        """
        signals = []
        
        for pair in self.pairs:
            # Calculate current spread
            current_spread = current_prices[pair['asset2']] - \
                           pair['hedge_ratio'] * current_prices[pair['asset1']]
            
            # Z-score
            z_score = (current_spread - pair['spread_mean']) / pair['spread_std']
            
            # Entry thresholds
            if z_score > 2.0:
                # Spread too high: sell asset2, buy asset1
                signals.append({
                    'pair': (pair['asset1'], pair['asset2']),
                    'action': 'SHORT_SPREAD',
                    'z_score': z_score,
                    'expected_profit': abs(z_score) * pair['spread_std']
                })
            
            elif z_score < -2.0:
                # Spread too low: buy asset2, sell asset1
                signals.append({
                    'pair': (pair['asset1'], pair['asset2']),
                    'action': 'LONG_SPREAD',
                    'z_score': z_score,
                    'expected_profit': abs(z_score) * pair['spread_std']
                })
            
            # Exit thresholds
            elif -0.5 < z_score < 0.5:
                # Spread normalized: close position
                if (pair['asset1'], pair['asset2']) in self.positions:
                    signals.append({
                        'pair': (pair['asset1'], pair['asset2']),
                        'action': 'CLOSE',
                        'z_score': z_score
                    })
        
        return signals


### 3. Market Making Strategy

```python
class MarketMakingStrategy:
    """
    Provide liquidity and capture bid-ask spread.
    Uses inventory management and adverse selection protection.
    """
    
    def __init__(self, symbol, target_spread_bps=10):
        self.symbol = symbol
        self.target_spread_bps = target_spread_bps
        self.inventory = 0
        self.target_inventory = 0
    
    def calculate_quotes(self, mid_price, volatility, inventory_skew=True):
        """
        Calculate optimal bid/ask quotes.
        """
        # Base spread from target
        base_spread = mid_price * (self.target_spread_bps / 10000)
        
        # Adjust for volatility (wider in high vol)
        vol_adjustment = 1 + volatility / 0.02  # Normalize by 2% vol
        adjusted_spread = base_spread * vol_adjustment
        
        # Symmetric quotes
        bid_price = mid_price - adjusted_spread / 2
        ask_price = mid_price + adjusted_spread / 2
        
        # Inventory skew: adjust prices to reduce inventory risk
        if inventory_skew and self.inventory != self.target_inventory:
            inventory_delta = self.inventory - self.target_inventory
            skew_adjustment = 0.0001 * inventory_delta  # 1bps per unit
            
            bid_price -= skew_adjustment
            ask_price -= skew_adjustment
        
        return {
            'bid_price': bid_price,
            'ask_price': ask_price,
            'spread_bps': (ask_price - bid_price) / mid_price * 10000
        }
    
    def calculate_quote_sizes(self, orderbook_depth, max_inventory=1000):
        """
        Determine optimal quote sizes based on market depth.
        """
        # Match market depth (but not too large)
        bid_depth = sum([l['size'] for l in orderbook_depth['bids'][:3]])
        ask_depth = sum([l['size'] for l in orderbook_depth['asks'][:3]])
        
        avg_depth = (bid_depth + ask_depth) / 2
        
        # Quote 5-10% of market depth
        base_size = avg_depth * 0.075
        
        # Adjust for inventory constraints
        inventory_room = max_inventory - abs(self.inventory)
        max_size = min(base_size, inventory_room / 2)
        
        # Asymmetric sizes based on inventory
        if self.inventory > self.target_inventory:
            # Long inventory: larger ask, smaller bid
            bid_size = max_size * 0.5
            ask_size = max_size * 1.5
        elif self.inventory < self.target_inventory:
            # Short inventory: larger bid, smaller ask
            bid_size = max_size * 1.5
            ask_size = max_size * 0.5
        else:
            bid_size = ask_size = max_size
        
        return {'bid_size': bid_size, 'ask_size': ask_size}
    
    def adverse_selection_filter(self, recent_trades, threshold=0.7):
        """
        Detect informed trading (adverse selection) and widen spreads.
        """
        if len(recent_trades) < 10:
            return 1.0  # No adjustment
        
        # Calculate trade flow imbalance
        buy_volume = sum([t['size'] for t in recent_trades if t['side'] == 'buy'])
        sell_volume = sum([t['size'] for t in recent_trades if t['side'] == 'sell'])
        total_volume = buy_volume + sell_volume
        
        imbalance = abs(buy_volume - sell_volume) / total_volume
        
        # If strong imbalance, likely informed trading
        if imbalance > threshold:
            # Widen spread to protect against adverse selection
            adjustment = 1 + imbalance
            return adjustment
        
        return 1.0
```

---

## Risk Management System

```python
class RiskManager:
    """
    Comprehensive risk management for crypto trading.
    Monitors position risk, portfolio risk, and systemic risk.
    """
    
    def __init__(self, initial_capital, max_drawdown=0.20):
        self.capital = initial_capital
        self.peak_capital = initial_capital
        self.max_drawdown = max_drawdown
        
        self.positions = {}
        self.risk_limits = self.set_risk_limits()
    
    def set_risk_limits(self):
        """
        Define risk limits across multiple dimensions.
        """
        return {
            'max_position_size': 0.10,  # 10% of capital per position
            'max_sector_exposure': 0.30,  # 30% in any sector
            'max_leverage': 3.0,
            'max_correlation': 0.7,  # Max correlation between positions
            'var_limit': 0.05,  # 5% daily VaR
            'max_concentration': 0.25  # Top position max 25%
        }
    
    def calculate_position_size(self, signal_confidence, volatility, 
                               kelly_fraction=0.25):
        """
        Kelly Criterion for optimal position sizing.
        Accounts for win probability and risk/reward.
        """
        # Estimate win probability from signal confidence
        win_prob = 0.5 + (signal_confidence - 0.5) * 0.8
        
        # Estimate avg win/loss ratio (conservative: 1.5)
        win_loss_ratio = 1.5
        
        # Kelly formula: f* = (p*b - q) / b
        # where p = win_prob, q = 1-p, b = win/loss ratio
        kelly_fraction_full = (win_prob * win_loss_ratio - (1 - win_prob)) / win_loss_ratio
        
        # Use fractional Kelly (more conservative)
        kelly_position = kelly_fraction_full * kelly_fraction
        
        # Adjust for volatility (reduce size in high vol)
        vol_adjustment = 0.02 / volatility  # Normalize by 2% daily vol
        
        # Final position size
        position_size = self.capital * kelly_position * vol_adjustment
        
        # Apply position limits
        max_position = self.capital * self.risk_limits['max_position_size']
        position_size = min(position_size, max_position)
        
        return position_size
    
    def calculate_var(self, positions, confidence=0.95):
        """
        Calculate Portfolio Value at Risk using historical simulation.
        """
        # Get returns for all positions
        position_returns = []
        
        for symbol, position in positions.items():
            returns = position['historical_returns']
            weight = position['value'] / self.capital
            weighted_returns = returns * weight
            position_returns.append(weighted_returns)
        
        # Portfolio returns
        portfolio_returns = sum(position_returns)
        
        # Historical VaR
        var_percentile = (1 - confidence) * 100
        var = np.percentile(portfolio_returns, var_percentile)
        
        return abs(var)
    
    def calculate_cvar(self, positions, confidence=0.95):
        """
        Conditional Value at Risk (Expected Shortfall).
        Average loss in worst (1-confidence)% of cases.
        """
        portfolio_returns = self.get_portfolio_returns(positions)
        
        var_percentile = (1 - confidence) * 100
        var_threshold = np.percentile(portfolio_returns, var_percentile)
        
        # CVaR: average of returns below VaR
        tail_returns = portfolio_returns[portfolio_returns <= var_threshold]
        cvar = abs(tail_returns.mean())
        
        return cvar
    
    def check_correlation_risk(self, new_position, existing_positions):
        """
        Ensure new position doesn't create excessive correlation.
        """
        for symbol, position in existing_positions.items():
            correlation = self.calculate_correlation(
                new_position['returns'],
                position['returns']
            )
            
            if abs(correlation) > self.risk_limits['max_correlation']:
                return False, f"High correlation ({correlation:.2f}) with {symbol}"
        
        return True, "Correlation check passed"
    
    def monitor_drawdown(self, current_capital):
        """
        Monitor drawdown and trigger risk reduction if necessary.
        """
        # Update peak
        if current_capital > self.peak_capital:
            self.peak_capital = current_capital
        
        # Calculate drawdown
        drawdown = (self.peak_capital - current_capital) / self.peak_capital
        
        if drawdown > self.max_drawdown:
            # Trigger emergency risk reduction
            return {
                'action': 'REDUCE_RISK',
                'severity': 'HIGH',
                'drawdown': drawdown,
                'message': f'Drawdown {drawdown:.1%} exceeds limit {self.max_drawdown:.1%}'
            }
        
        elif drawdown > self.max_drawdown * 0.75:
            # Warning level
            return {
                'action': 'WARNING',
                'severity': 'MEDIUM',
                'drawdown': drawdown,
                'message': f'Approaching drawdown limit'
            }
        
        return {
            'action': 'OK',
            'drawdown': drawdown
        }
    
    def calculate_stress_scenarios(self, positions):
        """
        Stress test portfolio under extreme scenarios.
        """
        scenarios = {
            'flash_crash': -0.30,  # 30% drop
            'black_swan': -0.50,  # 50% drop
            'correlation_breakdown': 1.0,  # All correlations → 1
            'liquidity_crisis': 0.5  # 50% wider spreads
        }
        
        results = {}
        
        for scenario_name, impact in scenarios.items():
            if scenario_name == 'correlation_breakdown':
                # Simulate all assets moving together
                portfolio_value = sum([p['value'] for p in positions.values()])
                scenario_loss = portfolio_value * -0.20  # Assume 20% loss
            
            else:
                # Simulate scenario impact
                scenario_loss = sum([
                    position['value'] * impact 
                    for position in positions.values()
                ])
            
            results[scenario_name] = {
                'loss': scenario_loss,
                'loss_pct': scenario_loss / self.capital * 100,
                'surviving_capital': self.capital + scenario_loss
            }
        
        return results
```

---

## Integration Architecture

### System Integration Flow

```python
class TradingSystem:
    """
    Main trading system integrating all components.
    Orchestrates data flow, signal generation, and execution.
    """
    
    def __init__(self, config):
        self.config = config
        
        # Initialize components
        self.data_pipeline = DataPipeline(config['exchanges'])
        self.signal_processor = SignalProcessor()
        self.feature_engine = CryptoFeatureEngine()
        self.ml_ensemble = MultiModelEnsemble()
        self.regime_detector = MarketRegimeDetector()
        self.anomaly_detector = AnomalyDetector()
        self.portfolio_optimizer = PortfolioOptimizer(None)
        self.execution_optimizer = ExecutionOptimizer(None, None)
        self.risk_manager = RiskManager(config['initial_capital'])
        self.arbitrage_engine = ArbitrageEngine(config['exchanges'])
        
        # Strategy instances
        self.strategies = {
            'hft': HighFrequencyStrategy(config['symbols'][0], None),
            'stat_arb': StatisticalArbitrageStrategy(config['universe']),
            'market_making': MarketMakingStrategy(config['symbols'][0])
        }
        
        # State tracking
        self.current_positions = {}
        self.order_history = []
        self.performance_metrics = {}
    
    def run_trading_loop(self):
        """
        Main trading loop - orchestrates entire system.
        """
        while True:
            try:
                # 1. DATA INGESTION
                market_data = self.data_pipeline.fetch_latest_data()
                
                # 2. SIGNAL PROCESSING
                processed_signals = self.process_market_signals(market_data)
                
                # 3. FEATURE ENGINEERING
                features = self.generate_features(market_data, processed_signals)
                
                # 4. REGIME DETECTION
                current_regime = self.regime_detector.predict_regime(
                    features[-100:]  # Last 100 bars
                )
                
                # 5. ANOMALY DETECTION
                anomaly_check = self.anomaly_detector.detect_anomalies(
                    features[-1:]
                )
                
                # 6. STRATEGY SIGNAL GENERATION
                signals = self.generate_strategy_signals(
                    features, 
                    current_regime,
                    anomaly_check
                )
                
                # 7. PORTFOLIO OPTIMIZATION
                optimal_positions = self.optimize_portfolio(signals)
                
                # 8. RISK MANAGEMENT
                risk_adjusted_positions = self.apply_risk_controls(
                    optimal_positions
                )
                
                # 9. EXECUTION
                self.execute_trades(risk_adjusted_positions)
                
                # 10. MONITORING & LOGGING
                self.update_metrics()
                self.log_system_state()
                
                # Sleep until next iteration
                time.sleep(self.config['loop_interval'])
                
            except Exception as e:
                self.handle_error(e)
    
    def process_market_signals(self, market_data):
        """
        Apply signal processing techniques to clean data.
        """
        processed = {}
        
        for symbol, data in market_data.items():
            # Apply Butterworth filter
            filtered_prices = self.signal_processor.apply_filter(
                data['close'].values
            )
            
            # Fourier analysis for cycles
            dominant_cycles = self.signal_processor.fourier.find_dominant_cycles(
                filtered_prices
            )
            
            # Kalman filter for true price estimation
            kalman_prices = self.signal_processor.kalman.filter_prices(
                data['close'].values
            )
            
            processed[symbol] = {
                'filtered_prices': filtered_prices,
                'dominant_cycles': dominant_cycles,
                'kalman_prices': kalman_prices,
                'raw_data': data
            }
        
        return processed
    
    def generate_features(self, market_data, processed_signals):
        """
        Generate comprehensive feature set.
        """
        features = pd.DataFrame()
        
        for symbol in market_data.keys():
            # Technical features
            tech_features = self.feature_engine.generate_technical_features(
                market_data[symbol]
            )
            
            # Volume profile features
            volume_features = self.feature_engine.generate_volume_profile_features(
                market_data[symbol]
            )
            
            # Combine
            symbol_features = pd.concat([tech_features, volume_features], axis=1)
            symbol_features.columns = [f"{symbol}_{col}" for col in symbol_features.columns]
            
            features = pd.concat([features, symbol_features], axis=1)
        
        return features
    
    def generate_strategy_signals(self, features, regime, anomaly_check):
        """
        Generate signals from all active strategies.
        """
        all_signals = []
        
        # Skip trading during anomalies
        if anomaly_check['is_anomaly'].any():
            return []
        
        # Adapt strategy selection based on regime
        active_strategies = self.select_strategies_for_regime(regime)
        
        for strategy_name in active_strategies:
            strategy = self.strategies[strategy_name]
            
            if strategy_name == 'hft':
                # HFT strategy needs tick data
                signals = strategy.generate_signals(features)
            
            elif strategy_name == 'stat_arb':
                # Statistical arbitrage
                signals = strategy.generate_signals(features)
            
            elif strategy_name == 'market_making':
                # Market making
                signals = strategy.calculate_quotes(features)
            
            all_signals.extend(signals)
        
        return all_signals
    
    def select_strategies_for_regime(self, regime):
        """
        Select optimal strategies based on market regime.
        """
        regime_strategy_map = {
            0: ['stat_arb', 'market_making'],  # Low vol regime
            1: ['hft', 'market_making'],       # Trending regime
            2: ['stat_arb'],                   # Mean reverting regime
            3: []                               # High vol - reduce activity
        }
        
        return regime_strategy_map.get(regime, ['market_making'])
    
    def optimize_portfolio(self, signals):
        """
        Optimize portfolio allocation across signals.
        """
        if not signals:
            return self.current_positions
        
        # Convert signals to expected returns
        expected_returns = self.signals_to_returns(signals)
        
        # Get historical returns for covariance
        historical_returns = self.get_historical_returns()
        
        # Update portfolio optimizer
        self.portfolio_optimizer.returns = historical_returns
        self.portfolio_optimizer.mean_returns = expected_returns
        self.portfolio_optimizer.cov_matrix = historical_returns.cov()
        
        # Optimize based on current regime
        optimal_weights = self.portfolio_optimizer.risk_parity_optimization()
        
        return optimal_weights
    
    def apply_risk_controls(self, proposed_positions):
        """
        Apply risk management rules before execution.
        """
        # Check position size limits
        for symbol, weight in proposed_positions['weights'].items():
            position_value = weight * self.risk_manager.capital
            max_position = self.risk_manager.capital * \
                          self.risk_manager.risk_limits['max_position_size']
            
            if position_value > max_position:
                # Scale down to limit
                proposed_positions['weights'][symbol] = \
                    max_position / self.risk_manager.capital
        
        # Check VaR limit
        var = self.risk_manager.calculate_var(self.current_positions)
        if var > self.risk_manager.risk_limits['var_limit']:
            # Scale down all positions
            scale_factor = self.risk_manager.risk_limits['var_limit'] / var
            proposed_positions['weights'] *= scale_factor
        
        # Check drawdown
        current_capital = self.calculate_current_capital()
        drawdown_status = self.risk_manager.monitor_drawdown(current_capital)
        
        if drawdown_status['action'] == 'REDUCE_RISK':
            # Emergency risk reduction: cut positions by 50%
            proposed_positions['weights'] *= 0.5
        
        return proposed_positions
    
    def execute_trades(self, target_positions):
        """
        Execute trades to reach target positions.
        """
        for symbol, target_weight in target_positions['weights'].items():
            current_weight = self.current_positions.get(symbol, {}).get('weight', 0)
            
            # Calculate required trade
            weight_delta = target_weight - current_weight
            
            if abs(weight_delta) > 0.01:  # 1% threshold
                trade_size = weight_delta * self.risk_manager.capital
                
                # Optimize execution
                if abs(trade_size) > 10000:  # Large order
                    # Use TWAP/VWAP
                    schedule = self.execution_optimizer.vwap_schedule(
                        total_quantity=trade_size,
                        duration_minutes=30,
                        volume_profile=self.get_volume_profile(symbol),
                        num_slices=10
                    )
                    
                    # Execute scheduled trades
                    self.execute_scheduled_trades(symbol, schedule)
                
                else:
                    # Simple market order
                    self.place_market_order(symbol, trade_size)
    
    def update_metrics(self):
        """
        Calculate and update performance metrics.
        """
        # Calculate returns
        current_value = self.calculate_current_capital()
        returns = (current_value - self.risk_manager.capital) / \
                  self.risk_manager.capital
        
        # Sharpe ratio
        if len(self.order_history) > 30:
            daily_returns = self.calculate_daily_returns()
            sharpe = np.mean(daily_returns) / np.std(daily_returns) * np.sqrt(365)
        else:
            sharpe = 0
        
        # Max drawdown
        peak = self.risk_manager.peak_capital
        drawdown = (peak - current_value) / peak
        
        self.performance_metrics = {
            'total_return': returns,
            'sharpe_ratio': sharpe,
            'max_drawdown': drawdown,
            'num_trades': len(self.order_history),
            'win_rate': self.calculate_win_rate()
        }
    
    def calculate_current_capital(self):
        """Calculate current portfolio value."""
        position_value = sum([p['value'] for p in self.current_positions.values()])
        cash = self.risk_manager.capital - position_value
        return cash + position_value


class DataPipeline:
    """
    Unified data ingestion pipeline for multiple sources.
    """
    
    def __init__(self, exchanges):
        self.exchanges = exchanges
        self.cache = {}
        self.websockets = {}
    
    def initialize_feeds(self):
        """
        Initialize real-time data feeds.
        """
        for exchange in self.exchanges:
            # Initialize WebSocket connections
            ws = self.connect_websocket(exchange)
            self.websockets[exchange] = ws
    
    def fetch_latest_data(self):
        """
        Fetch latest market data from all sources.
        """
        data = {}
        
        # Exchange data
        for exchange in self.exchanges:
            exchange_data = self.fetch_exchange_data(exchange)
            data[exchange] = exchange_data
        
        # On-chain data
        onchain_data = self.fetch_onchain_data()
        data['onchain'] = onchain_data
        
        # Sentiment data
        sentiment_data = self.fetch_sentiment_data()
        data['sentiment'] = sentiment_data
        
        return data
    
    def fetch_exchange_data(self, exchange):
        """
        Fetch OHLCV, orderbook, and trades from exchange.
        """
        # Implementation depends on exchange API
        pass
    
    def fetch_onchain_data(self):
        """
        Fetch blockchain metrics.
        """
        # Use APIs like Glassnode, IntoTheBlock, etc.
        pass
    
    def fetch_sentiment_data(self):
        """
        Fetch social sentiment indicators.
        """
        # Use Twitter API, Reddit API, LunarCrush, etc.
        pass
```

---

## Performance Metrics

### Comprehensive Performance Analysis

```python
class PerformanceAnalyzer:
    """
    Calculate comprehensive performance metrics for trading strategies.
    """
    
    def __init__(self, returns, trades, risk_free_rate=0.02):
        self.returns = returns
        self.trades = trades
        self.rf = risk_free_rate / 252  # Daily risk-free rate
    
    def calculate_all_metrics(self):
        """
        Calculate complete set of performance metrics.
        """
        return {
            'return_metrics': self.calculate_return_metrics(),
            'risk_metrics': self.calculate_risk_metrics(),
            'risk_adjusted_metrics': self.calculate_risk_adjusted_metrics(),
            'trade_metrics': self.calculate_trade_metrics(),
            'drawdown_metrics': self.calculate_drawdown_metrics(),
            'distribution_metrics': self.calculate_distribution_metrics()
        }
    
    def calculate_return_metrics(self):
        """
        Return-based performance metrics.
        """
        total_return = (1 + self.returns).prod() - 1
        annualized_return = (1 + total_return) ** (252 / len(self.returns)) - 1
        
        # Compound Annual Growth Rate (CAGR)
        years = len(self.returns) / 252
        cagr = (1 + total_return) ** (1 / years) - 1
        
        return {
            'total_return': total_return,
            'annualized_return': annualized_return,
            'cagr': cagr,
            'daily_avg_return': self.returns.mean(),
            'monthly_avg_return': self.returns.mean() * 21,
            'best_day': self.returns.max(),
            'worst_day': self.returns.min()
        }
    
    def calculate_risk_metrics(self):
        """
        Volatility and risk metrics.
        """
        daily_vol = self.returns.std()
        annual_vol = daily_vol * np.sqrt(252)
        
        # Downside deviation (only negative returns)
        downside_returns = self.returns[self.returns < 0]
        downside_deviation = downside_returns.std() * np.sqrt(252)
        
        # Value at Risk (95% confidence)
        var_95 = np.percentile(self.returns, 5)
        var_99 = np.percentile(self.returns, 1)
        
        # Conditional VaR (Expected Shortfall)
        cvar_95 = self.returns[self.returns <= var_95].mean()
        cvar_99 = self.returns[self.returns <= var_99].mean()
        
        return {
            'daily_volatility': daily_vol,
            'annual_volatility': annual_vol,
            'downside_deviation': downside_deviation,
            'var_95': var_95,
            'var_99': var_99,
            'cvar_95': cvar_95,
            'cvar_99': cvar_99
        }
    
    def calculate_risk_adjusted_metrics(self):
        """
        Risk-adjusted performance ratios.
        """
        # Sharpe Ratio
        excess_returns = self.returns - self.rf
        sharpe = excess_returns.mean() / self.returns.std() * np.sqrt(252)
        
        # Sortino Ratio (uses downside deviation)
        downside_returns = self.returns[self.returns < self.rf]
        downside_std = downside_returns.std()
        sortino = excess_returns.mean() / downside_std * np.sqrt(252) if downside_std > 0 else 0
        
        # Calmar Ratio (return / max drawdown)
        max_dd = self.calculate_max_drawdown()
        annual_return = self.returns.mean() * 252
        calmar = annual_return / abs(max_dd) if max_dd != 0 else 0
        
        # Information Ratio (vs benchmark)
        # Assuming benchmark return = risk-free rate
        tracking_error = excess_returns.std() * np.sqrt(252)
        information_ratio = (annual_return - self.rf * 252) / tracking_error if tracking_error > 0 else 0
        
        # Omega Ratio (gains vs losses)
        threshold = 0
        gains = self.returns[self.returns > threshold].sum()
        losses = abs(self.returns[self.returns < threshold].sum())
        omega = gains / losses if losses > 0 else float('inf')
        
        return {
            'sharpe_ratio': sharpe,
            'sortino_ratio': sortino,
            'calmar_ratio': calmar,
            'information_ratio': information_ratio,
            'omega_ratio': omega
        }
    
    def calculate_trade_metrics(self):
        """
        Trade-level statistics.
        """
        winning_trades = [t for t in self.trades if t['pnl'] > 0]
        losing_trades = [t for t in self.trades if t['pnl'] < 0]
        
        win_rate = len(winning_trades) / len(self.trades) if self.trades else 0
        
        avg_win = np.mean([t['pnl'] for t in winning_trades]) if winning_trades else 0
        avg_loss = np.mean([t['pnl'] for t in losing_trades]) if losing_trades else 0
        
        # Profit factor (gross profit / gross loss)
        gross_profit = sum([t['pnl'] for t in winning_trades])
        gross_loss = abs(sum([t['pnl'] for t in losing_trades]))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        
        # Average holding period
        holding_periods = [t['exit_time'] - t['entry_time'] for t in self.trades]
        avg_holding = np.mean(holding_periods) if holding_periods else 0
        
        return {
            'total_trades': len(self.trades),
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': win_rate,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'avg_win_loss_ratio': avg_win / abs(avg_loss) if avg_loss != 0 else 0,
            'profit_factor': profit_factor,
            'avg_holding_period': avg_holding
        }
    
    def calculate_max_drawdown(self):
        """
        Calculate maximum drawdown.
        """
        cumulative_returns = (1 + self.returns).cumprod()
        running_max = cumulative_returns.expanding().max()
        drawdown = (cumulative_returns - running_max) / running_max
        max_drawdown = drawdown.min()
        
        return max_drawdown
    
    def calculate_drawdown_metrics(self):
        """
        Detailed drawdown analysis.
        """
        cumulative_returns = (1 + self.returns).cumprod()
        running_max = cumulative_returns.expanding().max()
        drawdown = (cumulative_returns - running_max) / running_max
        
        max_dd = drawdown.min()
        
        # Find longest drawdown period
        in_drawdown = drawdown < 0
        drawdown_periods = []
        start = None
        
        for i, is_dd in enumerate(in_drawdown):
            if is_dd and start is None:
                start = i
            elif not is_dd and start is not None:
                drawdown_periods.append(i - start)
                start = None
        
        longest_dd = max(drawdown_periods) if drawdown_periods else 0
        avg_dd_duration = np.mean(drawdown_periods) if drawdown_periods else 0
        
        return {
            'max_drawdown': max_dd,
            'longest_drawdown_days': longest_dd,
            'avg_drawdown_duration': avg_dd_duration,
            'num_drawdown_periods': len(drawdown_periods)
        }
    
    def calculate_distribution_metrics(self):
        """
        Return distribution characteristics.
        """
        from scipy.stats import skew, kurtosis
        
        return_skew = skew(self.returns)
        return_kurtosis = kurtosis(self.returns)
        
        # Positive skew is good (more extreme positive returns)
        # High kurtosis means fat tails (more extreme events)
        
        return {
            'skewness': return_skew,
            'kurtosis': return_kurtosis,
            'is_normal': abs(return_skew) < 0.5 and abs(return_kurtosis) < 3
        }
```

---

## Configuration & Deployment

### System Configuration

```yaml
# config.yaml

system:
  initial_capital: 1000000
  max_drawdown: 0.20
  loop_interval: 1  # seconds
  
exchanges:
  - binance
  - coinbase
  - kraken
  - ftx

symbols:
  - BTC/USDT
  - ETH/USDT
  - SOL/USDT
  - AVAX/USDT

universe:
  - BTC
  - ETH
  - SOL
  - AVAX
  - MATIC
  - LINK
  - UNI
  - AAVE

strategies:
  hft:
    enabled: true
    max_position_size: 0.05
    confidence_threshold: 0.7
    
  stat_arb:
    enabled: true
    cointegration_significance: 0.05
    entry_threshold: 2.0
    exit_threshold: 0.5
    
  market_making:
    enabled: true
    target_spread_bps: 10
    max_inventory: 1000
    inventory_skew: true

risk_management:
  max_position_size: 0.10
  max_sector_exposure: 0.30
  max_leverage: 3.0
  var_limit: 0.05
  
ml_models:
  lstm:
    hidden_dim: 128
    num_layers: 2
    dropout: 0.2
    
  transformer:
    d_model: 128
    nhead: 8
    num_layers: 4
    
  ensemble:
    models:
      - xgboost
      - lightgbm
      - random_forest
    optimization_method: validation_mse

signal_processing:
  butterworth:
    cutoff_freq: 0.1
    order: 4
    
  fourier:
    window_size: 256
    
  kalman:
    transition_covariance: auto
    observation_covariance: auto
```

### Deployment Script

```python
# deploy.py

import yaml
import logging
from trading_system import TradingSystem

def setup_logging():
    """Configure logging for production."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('trading_system.log'),
            logging.StreamHandler()
        ]
    )

def load_config(config_path='config.yaml'):
    """Load system configuration."""
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    return config

def main():
    # Setup
    setup_logging()
    logger = logging.getLogger(__name__)
    
    # Load configuration
    config = load_config()
    logger.info("Configuration loaded successfully")
    
    # Initialize trading system
    trading_system = TradingSystem(config)
    logger.info("Trading system initialized")
    
    # Start trading
    logger.info("Starting trading loop...")
    trading_system.run_trading_loop()

if __name__ == "__main__":
    main()
```

---

## Conclusion

This comprehensive system integrates:

1. **Signal Processing** - Butterworth filters, Fourier analysis, Kalman filters for noise reduction
2. **Machine Learning** - LSTM, Transformers, ensemble methods for prediction
3. **Graph Theory** - Arbitrage detection, correlation networks for multi-exchange optimization
4. **Optimization** - Portfolio optimization, execution algorithms, risk management
5. **Trading Strategies** - HFT, statistical arbitrage, market making
6. **Risk Management** - VaR, CVaR, drawdown monitoring, position sizing

### Key Advantages for Crypto:

- **24/7 Operation** - Continuous algorithm deployment
- **High Volatility** - More opportunities for profit
- **Multiple Venues** - Cross-exchange arbitrage
- **Digital Infrastructure** - Perfect for algorithmic execution
- **Market Inefficiencies** - Alpha generation opportunities

### Next Steps:

1. Backtest strategies on historical data
2. Paper trade to validate system
3. Start with small capital in production
4. Monitor and iterate based on performance
5. Scale up as confidence grows

**Remember**: Crypto markets are highly volatile. Always test thoroughly, start small, and never risk more than you can afford to lose.# Algorithmic Crypto Trading Systems: Technical Implementation Guide

## Table of Contents
1. [System Architecture Overview](#system-architecture-overview)
2. [Core Mathematical Foundations](#core-mathematical-foundations)
3. [Machine Learning Pipeline](#machine-learning-pipeline)
4. [Signal Processing Framework](#signal-processing-framework)
5. [Graph Theory Applications](#graph-theory-applications)
6. [Optimization Algorithms](#optimization-algorithms)
7. [Strategy Implementation](#strategy-implementation)
8. [Risk Management System](#risk-management-system)
9. [Integration Architecture](#integration-architecture)
10. [Performance Metrics](#performance-metrics)

---

## System Architecture Overview

### High-Level Component Design

```
┌─────────────────────────────────────────────────────────────┐
│                     Data Ingestion Layer                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │ Exchange │  │On-Chain  │  │ Social   │  │Derivative│   │
│  │   APIs   │  │  Data    │  │Sentiment │  │  Data    │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                   Signal Processing Layer                    │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │ Filters  │  │  Fourier │  │ Wavelets │  │  Kalman  │   │
│  │Butterworth│  │Transform │  │          │  │  Filter  │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                   Feature Engineering Layer                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │Technical │  │  Volume  │  │  Market  │  │On-Chain  │   │
│  │Indicators│  │ Profile  │  │Sentiment │  │ Metrics  │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    ML/AI Decision Layer                      │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │  Neural  │  │Ensemble  │  │ Regime   │  │ Anomaly  │   │
│  │ Networks │  │  Models  │  │Detection │  │Detection │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                  Portfolio Optimization Layer                │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │  Convex  │  │ Genetic  │  │  Monte   │  │   Risk   │   │
│  │Optimization│ │Algorithm │  │  Carlo   │  │  Parity  │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    Execution & Routing Layer                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │ Smart    │  │Arbitrage │  │  TWAP/   │  │Slippage  │   │
│  │ Routing  │  │  Engine  │  │   VWAP   │  │Minimizer │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    Risk Management Layer                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │   VaR    │  │Position  │  │Correlation│ │ Circuit  │   │
│  │  Model   │  │  Sizing  │  │ Monitor  │  │ Breakers │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## Core Mathematical Foundations

### 1. Signal Processing Theory

#### Butterworth Filter Implementation
```python
from scipy.signal import butter, filtfilt
import numpy as np

class SignalProcessor:
    """
    Low-pass Butterworth filter for noise reduction in price signals.
    Transfer function: H(s) = 1 / (1 + (s/ωc)^(2n))
    """
    def __init__(self, cutoff_freq=0.1, order=4, sampling_rate=1.0):
        self.cutoff = cutoff_freq
        self.order = order
        self.fs = sampling_rate
        self.nyquist = 0.5 * sampling_rate
        self.normal_cutoff = cutoff_freq / self.nyquist
        
    def apply_filter(self, data):
        """
        Apply zero-phase digital filtering to prevent phase distortion.
        Uses forward-backward filtering (filtfilt) for zero phase lag.
        """
        b, a = butter(self.order, self.normal_cutoff, btype='low', analog=False)
        filtered_data = filtfilt(b, a, data)
        return filtered_data
    
    def adaptive_cutoff(self, volatility):
        """
        Dynamically adjust cutoff frequency based on market volatility.
        Higher volatility → Higher cutoff → More smoothing
        """
        base_cutoff = self.cutoff
        adaptive_cutoff = base_cutoff * (1 + np.log1p(volatility))
        return min(adaptive_cutoff, self.nyquist * 0.9)
```

#### Fourier Analysis for Cyclical Patterns
```python
from scipy.fft import fft, fftfreq

class FourierAnalyzer:
    """
    Frequency domain analysis for identifying market cycles.
    Decomposes price series into constituent frequencies.
    """
    def __init__(self, window_size=512):
        self.window_size = window_size
        
    def find_dominant_cycles(self, price_series):
        """
        Extract dominant frequency components using FFT.
        Returns periods of significant market cycles.
        """
        # Apply Hanning window to reduce spectral leakage
        windowed = price_series * np.hanning(len(price_series))
        
        # Compute FFT
        fft_values = fft(windowed)
        frequencies = fftfreq(len(price_series))
        
        # Get power spectral density
        psd = np.abs(fft_values) ** 2
        
        # Find peaks in frequency domain
        from scipy.signal import find_peaks
        peaks, properties = find_peaks(psd[:len(psd)//2], 
                                       prominence=np.max(psd)*0.1)
        
        # Convert frequencies to periods (in bars/candles)
        dominant_periods = 1 / frequencies[peaks]
        return dominant_periods[dominant_periods > 0]
    
    def reconstruct_signal(self, price_series, keep_frequencies=10):
        """
        Reconstruct signal using only dominant frequencies.
        Effective noise reduction technique.
        """
        fft_values = fft(price_series)
        # Zero out all but the largest frequency components
        threshold = np.sort(np.abs(fft_values))[-keep_frequencies]
        fft_values[np.abs(fft_values) < threshold] = 0
        
        reconstructed = np.real(np.fft.ifft(fft_values))
        return reconstructed
```

#### Wavelet Transform for Multi-Resolution Analysis
```python
import pywt

class WaveletAnalyzer:
    """
    Wavelet decomposition for multi-timeframe analysis.
    Better than Fourier for non-stationary signals (crypto prices).
    """
    def __init__(self, wavelet='db4', levels=5):
        self.wavelet = wavelet
        self.levels = levels
    
    def decompose(self, price_series):
        """
        Decompose into approximation (trend) and details (noise/volatility).
        Each level represents a different time scale.
        """
        coeffs = pywt.wavedec(price_series, self.wavelet, level=self.levels)
        return coeffs
    
    def denoise(self, price_series, threshold_method='soft'):
        """
        Remove noise while preserving important features.
        Threshold small wavelet coefficients (likely noise).
        """
        coeffs = self.decompose(price_series)
        
        # Calculate threshold using universal threshold
        sigma = np.median(np.abs(coeffs[-1])) / 0.6745
        threshold = sigma * np.sqrt(2 * np.log(len(price_series)))
        
        # Apply thresholding to detail coefficients
        denoised_coeffs = [coeffs[0]]  # Keep approximation
        for detail in coeffs[1:]:
            if threshold_method == 'soft':
                denoised = pywt.threshold(detail, threshold, mode='soft')
            else:
                denoised = pywt.threshold(detail, threshold, mode='hard')
            denoised_coeffs.append(denoised)
        
        # Reconstruct signal
        denoised_signal = pywt.waverec(denoised_coeffs, self.wavelet)
        return denoised_signal[:len(price_series)]
```

#### Kalman Filter for State Estimation
```python
from pykalman import KalmanFilter

class AdaptiveKalmanFilter:
    """
    Optimal state estimation for tracking true price in noisy market.
    Adapts to changing market dynamics (volatility, trends).
    """
    def __init__(self):
        self.kf = None
        
    def initialize(self, initial_price):
        """
        Set up Kalman filter with state transition and observation models.
        State: [price, velocity, acceleration]
        """
        # State transition matrix (assumes constant acceleration model)
        transition_matrix = np.array([
            [1, 1, 0.5],  # price_new = price + velocity + 0.5*acceleration
            [0, 1, 1],    # velocity_new = velocity + acceleration
            [0, 0, 1]     # acceleration_new = acceleration
        ])
        
        # Observation matrix (we only observe price)
        observation_matrix = np.array([[1, 0, 0]])
        
        self.kf = KalmanFilter(
            transition_matrices=transition_matrix,
            observation_matrices=observation_matrix,
            initial_state_mean=[initial_price, 0, 0],
            em_vars=['transition_covariance', 'observation_covariance']
        )
    
    def filter_prices(self, price_series):
        """
        Apply Kalman filtering to estimate true underlying price.
        """
        if self.kf is None:
            self.initialize(price_series[0])
        
        # Learn optimal parameters from data
        self.kf = self.kf.em(price_series.reshape(-1, 1), n_iter=10)
        
        # Filter the price series
        state_means, state_covariances = self.kf.filter(
            price_series.reshape(-1, 1)
        )
        
        return state_means[:, 0]  # Return filtered price
    
    def predict_next(self, current_state, n_steps=1):
        """
        Predict future prices based on current state.
        """
        predictions = []
        state = current_state
        
        for _ in range(n_steps):
            state = self.kf.transition_matrices @ state
            predictions.append(state[0])
        
        return np.array(predictions)
```

### 2. Statistical Foundations

#### Stationarity Testing and Transformation
```python
from statsmodels.tsa.stattools import adfuller, kpss

class StationarityHandler:
    """
    Ensure time series stationarity for reliable statistical modeling.
    Most ML algorithms assume stationarity.
    """
    def test_stationarity(self, series):
        """
        Use Augmented Dickey-Fuller and KPSS tests.
        ADF: H0 = non-stationary (reject → stationary)
        KPSS: H0 = stationary (reject → non-stationary)
        """
        adf_result = adfuller(series, autolag='AIC')
        kpss_result = kpss(series, regression='ct', nlags='auto')
        
        is_stationary = (adf_result[1] < 0.05) and (kpss_result[1] > 0.05)
        
        return {
            'is_stationary': is_stationary,
            'adf_pvalue': adf_result[1],
            'kpss_pvalue': kpss_result[1],
            'adf_statistic': adf_result[0],
            'kpss_statistic': kpss_result[0]
        }
    
    def make_stationary(self, series, method='returns'):
        """
        Transform non-stationary series to stationary.
        """
        if method == 'returns':
            # Log returns: most common for financial data
            return np.log(series / series.shift(1)).dropna()
        
        elif method == 'diff':
            # First difference
            return series.diff().dropna()
        
        elif method == 'detrend':
            # Remove linear trend
            from scipy.signal import detrend
            return detrend(series)
        
        elif method == 'fractional':
            # Fractional differencing (preserves memory)
            return self.fractional_diff(series, d=0.5)
    
    def fractional_diff(self, series, d=0.5, threshold=1e-3):
        """
        Fractional differencing to achieve stationarity while preserving memory.
        More sophisticated than simple differencing.
        """
        from scipy.special import gamma
        
        # Calculate weights
        weights = [1.0]
        k = 1
        while abs(weights[-1]) > threshold:
            weight = -weights[-1] * (d - k + 1) / k
            weights.append(weight)
            k += 1
        
        weights = np.array(weights[::-1])
        
        # Apply fractional differencing
        diff_series = np.zeros(len(series) - len(weights) + 1)
        for i in range(len(diff_series)):
            diff_series[i] = np.dot(weights, series[i:i+len(weights)])
        
        return diff_series
```

---

## Machine Learning Pipeline

### 1. Feature Engineering

```python
import pandas as pd
import talib

class CryptoFeatureEngine:
    """
    Comprehensive feature engineering for crypto markets.
    Combines technical, fundamental, and sentiment indicators.
    """
    
    def __init__(self):
        self.features = {}
    
    def generate_technical_features(self, df):
        """
        Technical indicators from price/volume data.
        """
        features = pd.DataFrame(index=df.index)
        
        # Price-based features
        features['returns'] = df['close'].pct_change()
        features['log_returns'] = np.log(df['close'] / df['close'].shift(1))
        
        # Momentum indicators
        features['rsi'] = talib.RSI(df['close'], timeperiod=14)
        features['macd'], features['macd_signal'], features['macd_hist'] = \
            talib.MACD(df['close'], fastperiod=12, slowperiod=26, signalperiod=9)
        features['stoch_k'], features['stoch_d'] = talib.STOCH(
            df['high'], df['low'], df['close'],
            fastk_period=14, slowk_period=3, slowd_period=3
        )
        
        # Trend indicators
        features['sma_20'] = talib.SMA(df['close'], timeperiod=20)
        features['sma_50'] = talib.SMA(df['close'], timeperiod=50)
        features['ema_12'] = talib.EMA(df['close'], timeperiod=12)
        features['adx'] = talib.ADX(df['high'], df['low'], df['close'], timeperiod=14)
        
        # Volatility indicators
        features['bbands_upper'], features['bbands_middle'], features['bbands_lower'] = \
            talib.BBANDS(df['close'], timeperiod=20, nbdevup=2, nbdevdn=2)
        features['atr'] = talib.ATR(df['high'], df['low'], df['close'], timeperiod=14)
        
        # Volume indicators
        features['obv'] = talib.OBV(df['close'], df['volume'])
        features['ad'] = talib.AD(df['high'], df['low'], df['close'], df['volume'])
        features['mfi'] = talib.MFI(df['high'], df['low'], df['close'], 
                                     df['volume'], timeperiod=14)
        
        # Price patterns
        features['cdl_doji'] = talib.CDLDOJI(df['open'], df['high'], 
                                               df['low'], df['close'])
        features['cdl_hammer'] = talib.CDLHAMMER(df['open'], df['high'], 
                                                   df['low'], df['close'])
        
        return features
    
    def generate_volume_profile_features(self, df, num_bins=20):
        """
        Volume profile analysis - where volume occurred at each price level.
        """
        features = pd.DataFrame(index=df.index)
        
        for i in range(len(df)):
            if i < 20:  # Need minimum history
                continue
            
            window = df.iloc[i-20:i]
            price_range = window['high'].max() - window['low'].min()
            bin_size = price_range / num_bins
            
            # Create price bins
            bins = np.arange(window['low'].min(), 
                           window['high'].max() + bin_size, 
                           bin_size)
            
            # Aggregate volume at each price level
            volume_profile = np.zeros(len(bins)-1)
            for j, row in window.iterrows():
                price_bin = int((row['close'] - bins[0]) / bin_size)
                if 0 <= price_bin < len(volume_profile):
                    volume_profile[price_bin] += row['volume']
            
            # Extract features from volume profile
            poc_idx = np.argmax(volume_profile)  # Point of Control
            features.loc[df.index[i], 'poc_price'] = bins[poc_idx]
            features.loc[df.index[i], 'poc_volume'] = volume_profile[poc_idx]
            features.loc[df.index[i], 'value_area_high'] = bins[poc_idx + 2] if poc_idx + 2 < len(bins) else bins[-1]
            features.loc[df.index[i], 'value_area_low'] = bins[poc_idx - 2] if poc_idx >= 2 else bins[0]
        
        return features
    
    def generate_market_microstructure_features(self, orderbook_snapshots):
        """
        Order book imbalance and market impact features.
        """
        features = pd.DataFrame()
        
        for snapshot in orderbook_snapshots:
            # Order book imbalance
            bid_volume = sum([level['size'] for level in snapshot['bids'][:10]])
            ask_volume = sum([level['size'] for level in snapshot['asks'][:10]])
            imbalance = (bid_volume - ask_volume) / (bid_volume + ask_volume)
            
            # Spread metrics
            best_bid = snapshot['bids'][0]['price']
            best_ask = snapshot['asks'][0]['price']
            mid_price = (best_bid + best_ask) / 2
            spread_bps = (best_ask - best_bid) / mid_price * 10000
            
            # Market depth
            depth_5_levels = sum([level['size'] for level in snapshot['bids'][:5]]) + \
                           sum([level['size'] for level in snapshot['asks'][:5]])
            
            features = features.append({
                'ob_imbalance': imbalance,
                'spread_bps': spread_bps,
                'market_depth': depth_5_levels,
                'mid_price': mid_price
            }, ignore_index=True)
        
        return features
    
    def generate_onchain_features(self, onchain_data):
        """
        On-chain metrics for blockchain-native alpha.
        """
        features = pd.DataFrame()
        
        # Network activity
        features['active_addresses'] = onchain_data['active_addresses']
        features['transaction_count'] = onchain_data['transaction_count']
        features['nvt_ratio'] = onchain_data['network_value'] / \
                                onchain_data['transaction_volume']
        
        # Holder behavior
        features['exchange_inflow'] = onchain_data['exchange_inflows']
        features['exchange_outflow'] = onchain_data['exchange_outflows']
        features['net_exchange_flow'] = features['exchange_inflow'] - \
                                        features['exchange_outflow']
        
        # Miner metrics
        features['miner_revenue'] = onchain_data['miner_revenue']
        features['hash_rate'] = onchain_data['hash_rate']
        features['difficulty'] = onchain_data['difficulty']
        
        # Market value metrics
        features['mvrv_ratio'] = onchain_data['market_cap'] / \
                                 onchain_data['realized_cap']
        features['sopr'] = onchain_data['spent_output_profit_ratio']
        
        return features
    
    def generate_sentiment_features(self, social_data):
        """
        Sentiment analysis from social media and news.
        """
        from transformers import pipeline
        
        sentiment_analyzer = pipeline("sentiment-analysis")
        
        features = pd.DataFrame()
        
        for data_point in social_data:
            # Analyze sentiment
            sentiment_result = sentiment_analyzer(data_point['text'])[0]
            
            # Social metrics
            engagement = data_point.get('likes', 0) + \
                        data_point.get('retweets', 0) + \
                        data_point.get('comments', 0)
            
            features = features.append({
                'sentiment_score': sentiment_result['score'] if sentiment_result['label'] == 'POSITIVE' else -sentiment_result['score'],
                'social_volume': data_point.get('mention_count', 0),
                'engagement_rate': engagement,
                'fear_greed_index': data_point.get('fear_greed', 50)
            }, ignore_index=True)
        
        return features
```

### 2. Model Architecture

```python
import torch
import torch.nn as nn
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from xgboost import XGBRegressor
import lightgbm as lgb

class MultiModelEnsemble:
    """
    Ensemble of diverse models for robust predictions.
    Combines deep learning with traditional ML.
    """
    
    def __init__(self):
        self.models = {}
        self.weights = {}
        
    def build_lstm_model(self, input_dim, hidden_dim=128, num_layers=2):
        """
        LSTM for capturing temporal dependencies in price sequences.
        """
        class LSTMPredictor(nn.Module):
            def __init__(self, input_dim, hidden_dim, num_layers):
                super(LSTMPredictor, self).__init__()
                
                self.lstm = nn.LSTM(
                    input_dim, 
                    hidden_dim, 
                    num_layers,
                    batch_first=True,
                    dropout=0.2
                )
                
                self.attention = nn.MultiheadAttention(hidden_dim, num_heads=8)
                
                self.fc_layers = nn.Sequential(
                    nn.Linear(hidden_dim, 64),
                    nn.ReLU(),
                    nn.Dropout(0.3),
                    nn.Linear(64, 32),
                    nn.ReLU(),
                    nn.Linear(32, 1)
                )
            
            def forward(self, x):
                # LSTM layers
                lstm_out, (hidden, cell) = self.lstm(x)
                
                # Self-attention
                attn_out, _ = self.attention(lstm_out, lstm_out, lstm_out)
                
                # Use last timestep
                final_hidden = attn_out[:, -1, :]
                
                # Fully connected layers
                output = self.fc_layers(final_hidden)
                
                return output
        
        return LSTMPredictor(input_dim, hidden_dim, num_layers)
    
    def build_transformer_model(self, input_dim, d_model=128, nhead=8, num_layers=4):
        """
        Transformer architecture for handling long-range dependencies.
        Better than LSTM for capturing complex patterns.
        """
        class TransformerPredictor(nn.Module):
            def __init__(self, input_dim, d_model, nhead, num_layers):
                super(TransformerPredictor, self).__init__()
                
                self.input_projection = nn.Linear(input_dim, d_model)
                
                encoder_layer = nn.TransformerEncoderLayer(
                    d_model=d_model,
                    nhead=nhead,
                    dim_feedforward=d_model * 4,
                    dropout=0.1,
                    batch_first=True
                )
                
                self.transformer = nn.TransformerEncoder(
                    encoder_layer,
                    num_layers=num_layers
                )
                
                self.output_layer = nn.Sequential(
                    nn.Linear(d_model, 64),
                    nn.ReLU(),
                    nn.Dropout(0.2),
                    nn.Linear(64, 1)
                )
            
            def forward(self, x):
                # Project input to model dimension
                x = self.input_projection(x)
                
                # Transformer encoding
                encoded = self.transformer(x)
                
                # Use mean pooling across time dimension
                pooled = encoded.mean(dim=1)
                
                # Output prediction
                output = self.output_layer(pooled)
                
                return output
        
        return TransformerPredictor(input_dim, d_model, nhead, num_layers)
    
    def build_gradient_boosting_models(self):
        """
        Gradient boosting models for tabular feature learning.
        Often outperform neural networks on structured data.
        """
        self.models['xgboost'] = XGBRegressor(
            n_estimators=1000,
            learning_rate=0.01,
            max_depth=7,
            subsample=0.8,
            colsample_bytree=0.8,
            objective='reg:squarederror',
            tree_method='hist',
            enable_categorical=True
        )
        
        self.models['lightgbm'] = lgb.LGBMRegressor(
            n_estimators=1000,
            learning_rate=0.01,
            max_depth=7,
            num_leaves=31,
            subsample=0.8,
            colsample_bytree=0.8,
            objective='regression'
        )
        
        self.models['catboost'] = RandomForestRegressor(
            n_estimators=500,
            max_depth=15,
            min_samples_split=10,
            min_samples_leaf=5,
            n_jobs=-1
        )
    
    def train_ensemble(self, X_train, y_train, X_val, y_val):
        """
        Train all models and compute optimal ensemble weights.
        """
        predictions = {}
        
        # Train each model
        for name, model in self.models.items():
            print(f"Training {name}...")
            model.fit(X_train, y_train)
            
            # Validate
            val_pred = model.predict(X_val)
            predictions[name] = val_pred
            
            # Calculate validation error
            mse = np.mean((val_pred - y_val) ** 2)
            print(f"{name} validation MSE: {mse:.6f}")
        
        # Optimize ensemble weights using validation performance
        self.weights = self.optimize_ensemble_weights(predictions, y_val)
    
    def optimize_ensemble_weights(self, predictions, y_true):
        """
        Find optimal linear combination of model predictions.
        Uses constrained optimization (weights sum to 1).
        """
        from scipy.optimize import minimize
        
        pred_matrix = np.column_stack([predictions[name] for name in predictions])
        
        def objective(weights):
            ensemble_pred = pred_matrix @ weights
            return np.mean((ensemble_pred - y_true) ** 2)
        
        # Constraints: weights sum to 1, all non-negative
        constraints = {'type': 'eq', 'fun': lambda w: np.sum(w) - 1}
        bounds = [(0, 1) for _ in range(len(predictions))]
        
        # Initial guess: equal weights
        initial_weights = np.ones(len(predictions)) / len(predictions)
        
        result = minimize(
            objective,
            initial_weights,
            method='SLSQP',
            bounds=bounds,
            constraints=constraints
        )
        
        weights_dict = {name: weight for name, weight in 
                       zip(predictions.keys(), result.x)}
        
        return weights_dict
    
    def predict(self, X):
        """
        Generate ensemble prediction using optimal weights.
        """
        predictions = {}
        
        for name, model in self.models.items():
            predictions[name] = model.predict(X)
        
        # Weighted average of predictions
        ensemble_pred = sum(predictions[name] * self.weights[name] 
                          for name in predictions)
        
        return ensemble_pred, predictions  # Return individual predictions too


class MarketRegimeDetector:
    """
    Identify current market regime (bull, bear, sideways, high/low volatility).
    Critical for adaptive strategy selection.
    """
    
    def __init__(self, n_regimes=4):
        from hmmlearn import hmm
        self.n_regimes = n_regimes
        self.model = hmm.GaussianHMM(n_components=n_regimes, 
                                      covariance_type="full",
                                      n_iter=1000)
    
    def fit_regimes(self, returns, volumes):
        """
        Use Hidden Markov Model to identify latent market states.
        Features: returns, volatility, volume
        """
        # Prepare features
        volatility = returns.rolling(20).std()
        volume_ratio = volumes / volumes.rolling(20).mean()
        
        X = np.column_stack([
            returns,
            volatility,
            volume_ratio
        ])
        
        # Remove NaN rows
        X = X[~np.isnan(X).any(axis=1)]
        
        # Fit HMM
        self.model.fit(X)
        
        # Predict regimes
        regimes = self.model.predict(X)
        
        # Characterize each regime
        regime_characteristics = {}
        for regime in range(self.n_regimes):
            regime_mask = regimes == regime
            regime_characteristics[regime] = {
                'mean_return': returns[regime_mask].mean(),
                'volatility': returns[regime_mask].std(),
                'avg_volume': volumes[regime_mask].mean(),
                'frequency': regime_mask.sum() / len(regimes)
            }
        
        return regimes, regime_characteristics
    
    def predict_regime(self, recent_data):
        """
        Predict current market regime based on recent data.
        """
        return self.model.predict(recent_data)[-1]


class AnomalyDetector:
    """
    Detect unusual market events (flash crashes, pump & dumps, manipulation).
    Uses multiple anomaly detection techniques.
    """
    
    def __init__(self):
        from sklearn.ensemble import IsolationForest
        from sklearn.svm import OneClassSVM
        
        self.isolation_forest = IsolationForest(
            contamination=0.01,
            random_state=42
        )
        
        self.one_class_svm = OneClassSVM(
            nu=0.01,
            kernel='rbf',
            gamma='auto'
        )
    
    def fit(self, normal_market_data):
        """
        Learn what "normal" market behavior looks like.
        """
        self.isolation_forest.fit(normal_market_data)
        self.one_class_svm.fit(normal_market_data)
    
    def detect_anomalies(self, current_data):
        """
        Detect if current market behavior is anomalous.
        Returns anomaly score and flags.
        """
        # Isolation Forest score
        if_score = self.isolation_forest.score_samples(current_data)
        if_anomaly = self.isolation_forest.predict(current_data) == -1
        
        # One-Class SVM score
        svm_score = self.one_class_svm.score_samples(current_data)
        svm_anomaly = self.one_class_svm.predict(current_data) == -1
        
        # Combine both methods
        combined_anomaly = if_anomaly | svm_anomaly
        combined_score = (if_score + svm_score) / 2
        
        return {
            'is_anomaly': combined_anomaly,
            'anomaly_score': combined_score,
            'confidence': np.abs(combined_score)
        }
    
    def detect_flash_crash(self, prices, threshold_std=5):
        """
        Specific detector for flash crash events.
        """
        returns = np.diff(prices) / prices[:-1]
        mean_return = np.mean(returns)
        std_return = np.std(returns)
        
        # Check if latest return is extreme
        latest_return = returns[-1]
        z_score = (latest_return - mean_return) / std_return
        
        is_flash_crash = z_score < -threshold_std
        
        return is_flash_crash, z_score
```

---

## Graph Theory Applications

### 1. Multi-Exchange Arbitrage

```python
import networkx as nx
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import bellman_ford, dijkstra

class ArbitrageEngine:
    """
    Graph-based arbitrage detection and execution across multiple exchanges.
    Each exchange is a node, each trading pair is an edge.
    """
    
    def __init__(self, exchanges):
        self.exchanges = exchanges
        self.graph = nx.DiGraph()
        self.arbitrage_opportunities = []
    
    def build_exchange_graph(self, prices_dict):
        """
        Build weighted directed graph where:
        - Nodes: (Exchange, Currency) pairs
        - Edges: Trading pairs with exchange rates as weights
        - Weight: -log(exchange_rate) for Bellman-Ford negative cycle detection
        """
        self.graph.clear()
        
        for exchange in self.exchanges:
            for pair, price_data in prices_dict[exchange].items():
                base, quote = pair.split('/')
                
                # Add nodes
                self.graph.add_node(f"{exchange}_{base}")
                self.graph.add_node(f"{exchange}_{quote}")
                
                # Add edge with log-transformed weight
                # Negative log because we want to maximize returns
                ask_price = price_data['ask']
                bid_price = price_data['bid']
                
                # Forward edge (buy)
                self.graph.add_edge(
                    f"{exchange}_{quote}",
                    f"{exchange}_{base}",
                    weight=-np.log(1 / ask_price),
                    price=ask_price,
                    type='buy',
                    pair=pair,
                    exchange=exchange
                )
                
                # Reverse edge (sell)
                self.graph.add_edge(
                    f"{exchange}_{base}",
                    f"{exchange}_{quote}",
                    weight=-np.log(bid_price),
                    price=bid_price,
                    type='sell',
                    pair=pair,
                    exchange=exchange
                )
        
        # Add inter-exchange transfer edges (withdrawal/deposit)
        self.add_transfer_edges()
    
    def add_transfer_edges(self, transfer_fee=0.001):
        """
        Add edges representing transfers between exchanges.
        Account for withdrawal fees and time delays.
        """
        currencies = set()
        for node in self.graph.nodes():
            exchange, currency = node.split('_')
            currencies.add(currency)
        
        for currency in currencies:
            exchange_nodes = [n for n in self.graph.nodes() if n.endswith(f'_{currency}')]
            
            # Add transfer edges between all exchange pairs
            for i, node1 in enumerate(exchange_nodes):
                for node2 in exchange_nodes[i+1:]:
                    # Bidirectional transfer with fee
                    self.graph.add_edge(
                        node1, node2,
                        weight=-np.log(1 - transfer_fee),
                        type='transfer',
                        fee=transfer_fee
                    )
                    self.graph.add_edge(
                        node2, node1,
                        weight=-np.log(1 - transfer_fee),
                        type='transfer',
                        fee=transfer_fee
                    )
    
    def detect_arbitrage_bellman_ford(self):
        """
        Use Bellman-Ford algorithm to detect negative cycles.
        Negative cycle = arbitrage opportunity.
        """
        # Convert to adjacency matrix for scipy
        nodes = list(self.graph.nodes())
        node_to_idx = {node: idx for idx, node in enumerate(nodes)}
        
        n = len(nodes)
        adjacency_matrix = np.full((n, n), np.inf)
        
        for u, v, data in self.graph.edges(data=True):
            i, j = node_to_idx[u], node_to_idx[v]
            adjacency_matrix[i, j] = data['weight']
        
        # Run Bellman-Ford from each node
        arbitrage_cycles = []
        
        for start_node in range(n):
            dist, predecessors = bellman_ford(
                csr_matrix(adjacency_matrix),
                indices=start_node,
                return_predecessors=True
            )
            
            # Check for negative cycles
            for i in range(n):
                for j in range(n):
                    if adjacency_matrix[i, j] != np.inf:
                        if dist[i] + adjacency_matrix[i, j] < dist[j]:
                            # Found negative cycle
                            cycle = self.reconstruct_cycle(i, j, predecessors, nodes)
                            profit = self.calculate_cycle_profit(cycle)
                            
                            if profit > 1.001:  # >0.1% profit after fees
                                arbitrage_cycles.append({
                                    'cycle': cycle,
                                    'profit_ratio': profit,
                                    'profit_pct': (profit - 1) * 100
                                })
        
        self.arbitrage_opportunities = arbitrage_cycles
        return arbitrage_cycles
    
    def reconstruct_cycle(self, start, end, predecessors, nodes):
        """
        Reconstruct arbitrage cycle from predecessor array.
        """
        cycle = [nodes[end]]
        current = end
        
        while predecessors[current] != start and predecessors[current] != -9999:
            current = predecessors[current]
            cycle.append(nodes[current])
        
        cycle.append(nodes[start])
        return cycle[::-1]
    
    def calculate_cycle_profit(self, cycle):
        """
        Calculate expected profit from executing arbitrage cycle.
        """
        profit = 1.0
        
        for i in range(len(cycle) - 1):
            edge_data = self.graph.get_edge_data(cycle[i], cycle[i+1])
            
            if edge_data['type'] in ['buy', 'sell']:
                profit *= edge_data['price']
            elif edge_data['type'] == 'transfer':
                profit *= (1 - edge_data['fee'])
        
        return profit
    
    def find_optimal_execution_path(self, start_currency, end_currency, 
                                   start_exchange, amount):
        """
        Find cheapest path to convert currency accounting for:
        - Price impact
        - Trading fees
        - Slippage
        """
        start_node = f"{start_exchange}_{start_currency}"
        
        # Find all possible end nodes (any exchange with end_currency)
        end_nodes = [n for n in self.graph.nodes() 
                    if n.endswith(f'_{end_currency}')]
        
        best_path = None
        best_final_amount = 0
        
        for end_node in end_nodes:
            try:
                # Use Dijkstra for shortest path
                path = nx.shortest_path(
                    self.graph, 
                    start_node, 
                    end_node,
                    weight='weight'
                )
                
                # Simulate execution
                final_amount = self.simulate_execution(path, amount)
                
                if final_amount > best_final_amount:
                    best_final_amount = final_amount
                    best_path = path
            
            except nx.NetworkXNoPath:
                continue
        
        return best_path, best_final_amount
    
    def simulate_execution(self, path, initial_amount):
        """
        Simulate execution along path accounting for market impact.
        """
        amount = initial_amount
        
        for i in range(len(path) - 1):
            edge_data = self.graph.get_edge_data(path[i], path[i+1])
            
            if edge_data['type'] == 'buy':
                # Account for slippage (price impact)
                slippage = self.calculate_slippage(amount, edge_data)
                effective_price = edge_data['price'] * (1 + slippage)
                amount = amount / effective_price
                amount *= 0.999  # Trading fee
            
            elif edge_data['type'] == 'sell':
                slippage = self.calculate_slippage(amount, edge_data)
                effective_price = edge_data['price'] * (1 - slippage)
                amount = amount * effective_price
                amount *= 0.999  # Trading fee
            
            elif edge_data['type'] == 'transfer':
                amount *= (1 - edge_data['fee'])
        
        return amount
    
    def calculate_slippage(self, amount, edge_data, liquidity=1000000):
        """
        Estimate slippage based on order size and market liquidity.
        Uses square root market impact model.
        """
        # Simplified market impact: slippage ∝ sqrt(order_size / liquidity)
        impact_coef = 0.1  # Calibrated parameter
        slippage = impact_coef * np.sqrt(amount / liquidity)
        return slippage


class CorrelationNetwork:
    """
    Analyze correlation structure of crypto assets using network analysis.
    Identify diversification opportunities and systemic risks.
    """
    
    def __init__(self):
        self.correlation_matrix = None
        self.network = None
    
    def build_correlation_network(self, returns_df, threshold=0.5):
        """
        Build network where:
        - Nodes: crypto assets
        - Edges: significant correlations above threshold
        - Edge weights: correlation strength
        """
        # Calculate correlation matrix
        self.correlation_matrix = returns_df.corr()
        
        # Build network
        self.network = nx.Graph()
        
        assets = returns_df.columns
        for asset in assets:
            self.network.add_node(asset)
        
        # Add edges for significant correlations
        for i, asset1 in enumerate(assets):
            for j, asset2 in enumerate(assets):
                if i < j:  # Avoid duplicates
                    corr = self.correlation_matrix.loc[asset1, asset2]
                    
                    if abs(corr) > threshold:
                        self.network.add_edge(
                            asset1, asset2,
                            weight=abs(corr),
                            correlation=corr
                        )
    
    def detect_communities(self):
        """
        Identify asset clusters (e.g., DeFi tokens, Layer-1s, memecoins).
        Use Louvain community detection.
        """
        from community import community_louvain
        
        communities = community_louvain.best_partition(
            self.network,
            weight='weight'
        )
        
        # Group assets by community
        community_groups = {}
        for asset, community_id in communities.items():
            if community_id not in community_groups:
                community_groups[community_id] = []
            community_groups[community_id].append(asset)
        
        return community_groups
    
    def find_diversification_opportunities(self):
        """
        Find assets with low correlation to maximize diversification.
        """
        # Calculate average correlation for each asset
        avg_correlations = self.correlation_matrix.abs().mean(axis=1)
        
        # Assets with lowest average correlation are best diversifiers
        diversifiers = avg_correlations.sort_values().head(10)
        
        return diversifiers
    
    def calculate_systemic_risk(self):
        """
        Identify systemically important assets using centrality measures.
        """
        # Degree centrality: how many assets is it correlated with
        degree_centrality = nx.degree_centrality(self.network)
        
        # Betweenness centrality: bridge between communities
        betweenness = nx.betweenness_centrality(self.network, weight='weight')
        
        # Eigenvector centrality: connected to other important assets
        eigenvector = nx.eigenvector_centrality(self.network, weight='weight')
        
        # Combine metrics
        systemic_risk_scores = {}
        for asset in self.network.nodes():
            risk_score = (
                0.3 * degree_centrality.get(asset, 0) +
                0.3 * betweenness.get(asset, 0) +
                0.4 * eigenvector.get(asset, 0)
            )
            systemic_risk_scores[asset] = risk_score
        
        return sorted(systemic_risk_scores.items(), 
                     key=lambda x: x[1], reverse=True)

