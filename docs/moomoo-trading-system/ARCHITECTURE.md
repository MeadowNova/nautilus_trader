# System Architecture

Deep-dive into the Moomoo RL Paper Trading System architecture, components, and design decisions.

## Table of Contents

1. [High-Level Architecture](#high-level-architecture)
2. [Component Details](#component-details)
3. [Data Flow](#data-flow)
4. [Event-Driven Architecture](#event-driven-architecture)
5. [RL Integration](#rl-integration)
6. [Risk Management](#risk-management)
7. [Performance Characteristics](#performance-characteristics)
8. [Design Decisions](#design-decisions)

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                   MOOMOO RL TRADING SYSTEM                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌───────────┐     ┌──────────────┐     ┌────────────────────┐     │
│  │   Moomoo  │     │ NautilusTrader│    │   RL Framework     │     │
│  │   OpenD   │◄───►│    Engine     │◄──►│   (PyTorch)        │     │
│  │  Gateway  │     │  (Rust Core)  │    │                    │     │
│  └───────────┘     └──────────────┘     └────────────────────┘     │
│       │                   │                       │                 │
│       │ Market Data       │ Events/               │ State/          │
│       │ Execution         │ Orders                │ Action/         │
│       ▼                   ▼                       ▼ Reward          │
│  ┌───────────┐     ┌──────────────┐     ┌────────────────────┐     │
│  │ Data      │     │  Strategies  │     │  Experience        │     │
│  │ Adapter   │     │  - Pairs     │     │  Replay Buffer     │     │
│  │ Execution │     │  - Momentum  │     │  (PostgreSQL)      │     │
│  │ Adapter   │     └──────────────┘     └────────────────────┘     │
│  └───────────┘           │                       │                 │
│                          ▼                       ▼                  │
│                   ┌──────────────┐     ┌────────────────────┐      │
│                   │     Risk     │     │    Training        │      │
│                   │  Management  │     │    Orchestrator    │      │
│                   └──────────────┘     └────────────────────┘      │
│                          │                       │                 │
│                          ▼                       ▼                  │
│                   ┌──────────────────────────────────────┐         │
│                   │    Infrastructure Services           │         │
│                   │  - PostgreSQL (persistence)          │         │
│                   │  - Redis (cache)                     │         │
│                   │  - Prometheus (metrics)              │         │
│                   │  - Grafana (dashboards)              │         │
│                   └──────────────────────────────────────┘         │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Component Details

### 1. Moomoo OpenD Gateway

**Purpose:** Bridge between trading system and Moomoo's servers.

**Technology:** C++ application with TCP/TLS protocol.

**Responsibilities:**
- Market data streaming (quotes, tickers, trades)
- Order submission and management
- Account and position queries
- Session management and authentication

**API Interface:**
```python
# Quote Context (market data)
OpenQuoteContext(host="127.0.0.1", port=11111)

# Trade Context (execution)
OpenSecTradeContext(host="127.0.0.1", port=11111, trd_env=TrdEnv.SIMULATE)
```

**Rate Limits:**
- 15 orders per 30 seconds
- 1000 quote subscriptions (plan-dependent)
- 5 requests/second for account queries

**Failure Modes:**
- Session timeout (24 hours)
- Network disconnection
- Market data permission errors
- Order rejection

---

### 2. Nautilus Trader Engine

**Purpose:** High-performance event-driven trading engine.

**Technology:** Rust core with Python bindings (Cython, PyO3).

**Architecture Layers:**

```
┌─────────────────────────────────────┐
│      Python Strategy Layer           │  ← User strategies
├─────────────────────────────────────┤
│      Python API (Cython)             │  ← Bindings
├─────────────────────────────────────┤
│      Rust Core                       │
│  - Event loop (tokio async)          │
│  - Message bus                       │
│  - Cache (in-memory)                 │
│  - Clock (nanosecond precision)      │
├─────────────────────────────────────┤
│      Adapters (Rust/Python)          │
│  - MoomooDataClient                  │
│  - MoomooExecClient                  │
└─────────────────────────────────────┘
```

**Key Components:**

**Message Bus:**
- Pub/sub architecture
- Nanosecond-precision timestamps
- Type-safe message passing
- Event replay capability

**Cache:**
- In-memory storage
- O(1) instrument/order/position lookups
- Automatic invalidation
- Thread-safe (Rust mutex)

**Clock:**
- System time or simulated time
- Nanosecond resolution
- Monotonic (no time travel)
- Timer registration

**Execution Engine:**
- Order lifecycle management
- Position tracking
- P&L calculation
- Risk checks (pre-trade, post-trade)

---

### 3. Moomoo Adapter

**Purpose:** Connect NautilusTrader to Moomoo OpenD API.

**Location:** `/nautilus_trader/adapters/moomoo/`

**Files:**

```
moomoo/
├── __init__.py          # Venue constant
├── config.py            # Configuration dataclasses
├── common.py            # Shared utilities
├── providers.py         # Instrument provider
├── data.py              # Market data client
├── execution.py         # Order execution client
└── factories.py         # Client factories
```

**Data Client (`data.py`):**

```python
class MoomooDataClient(LiveDataClient):
    """Streams market data from Moomoo."""

    async def _connect(self):
        # Connect to OpenD quote context
        self._quote_ctx = OpenQuoteContext(...)

        # Subscribe to quote updates
        self._quote_ctx.set_handler(QuoteHandlerBase())

        # Subscribe to instruments
        for instrument_id in self._instruments:
            self._subscribe_quotes(instrument_id)

    async def _subscribe_quotes(self, command):
        # Extract instrument
        instrument_id = command.instrument_id
        moomoo_code = self._get_moomoo_code(instrument_id)

        # Subscribe via OpenD
        ret = self._quote_ctx.subscribe([moomoo_code], ['QUOTE'])

        # Handle callbacks
        def on_quote(quote):
            # Convert to NautilusTrader QuoteTick
            tick = self._parse_quote(quote)
            self._handle_data(tick)
```

**Execution Client (`execution.py`):**

```python
class MoomooExecClient(LiveExecutionClient):
    """Executes orders via Moomoo."""

    async def _submit_order(self, command):
        # Extract order details
        order = command.order

        # Convert to Moomoo format
        moomoo_order = self._create_moomoo_order(order)

        # Submit via OpenD
        ret, data = self._trd_ctx.place_order(
            price=moomoo_order.price,
            qty=moomoo_order.qty,
            code=moomoo_order.code,
            trd_side=moomoo_order.side,
            order_type=moomoo_order.type,
            trd_env=TrdEnv.SIMULATE,
        )

        # Handle response
        if ret == RET_OK:
            self._handle_order_accepted(order, data)
        else:
            self._handle_order_rejected(order, data)

    async def generate_order_status_reports(self, command):
        """Reconciliation: Query open orders from Moomoo."""
        ret, orders_df = self._trd_ctx.order_list_query()

        reports = []
        for _, row in orders_df.iterrows():
            report = self._create_order_status_report(row)
            reports.append(report)

        return reports
```

**Key Features:**

1. **Reconciliation:** On startup, queries Moomoo for open orders/positions
2. **Error Handling:** Maps Moomoo errors to NautilusTrader events
3. **Rate Limiting:** Enforces 15 orders/30s limit
4. **Data Transformation:** Converts between Moomoo and Nautilus types

---

### 4. RL Framework

**Purpose:** Learn optimal trading decisions through reinforcement learning.

**Location:** `/ajk_strategies/rl_framework/`

**Structure:**

```
rl_framework/
├── agents/
│   ├── base_agent.py        # RLAgent abstract + SimpleRuleAgent
│   └── __init__.py
├── state/
│   ├── state_builder.py     # Build state vectors from market data
│   └── __init__.py
├── reward/
│   ├── reward_calculator.py  # Calculate rewards from trades
│   ├── credit_assignment.py # N-step TD, "seeing out" bonus
│   └── __init__.py
└── training/
    ├── trainer.py            # RLTrainer class
    ├── experience_buffer.py  # Prioritized replay buffer
    └── __init__.py
```

**State Builder:**

```python
class StateBuilder:
    """Constructs state vectors for RL agent."""

    def build_state(self, bar: Bar, position, indicators) -> np.ndarray:
        state = []

        # Price features (10)
        state.extend(self._price_features(bar))

        # Technical indicators (10)
        state.extend(self._indicator_features(indicators))

        # Volume features (5)
        state.extend(self._volume_features(bar))

        # Strategy-specific (15)
        state.extend(self._strategy_features(...))

        # Position info (10)
        state.extend(self._position_features(position))

        # Market regime (10)
        state.extend(self._regime_features(...))

        # Recent performance (15)
        state.extend(self._performance_features(...))

        return np.array(state, dtype=np.float32)  # 75-dim
```

**Reward Calculator:**

```python
class RewardCalculator:
    """Calculates rewards for RL training."""

    def calculate_reward(self, trade: Trade) -> float:
        # Base reward from P&L
        base = trade.pnl / self.account_balance

        # "Seeing out" bonus
        if trade.pnl > 0:
            capture_ratio = trade.pnl / trade.max_favorable_excursion
            if capture_ratio >= 0.8:
                seeing_out_bonus = 1.0
            elif capture_ratio >= 0.5:
                seeing_out_bonus = 0.5
            else:
                seeing_out_bonus = 0.0
        else:
            seeing_out_bonus = 0.0

        # Holding penalty (for losers)
        if trade.pnl < 0:
            hold_penalty = -0.1 * (trade.bars_held / self.max_hold)
        else:
            hold_penalty = 0.0

        return base + seeing_out_bonus + hold_penalty
```

**Experience Replay Buffer:**

```python
class PrioritizedReplayBuffer:
    """Stores experiences with priority sampling."""

    def __init__(self, capacity=100000, alpha=0.6, beta=0.4):
        self.capacity = capacity
        self.alpha = alpha  # Priority exponent
        self.beta = beta    # Importance sampling
        self.buffer = []
        self.priorities = []

    def add(self, experience: Experience):
        # Add with max priority (initially)
        max_priority = max(self.priorities) if self.priorities else 1.0

        if len(self.buffer) < self.capacity:
            self.buffer.append(experience)
            self.priorities.append(max_priority)
        else:
            # Replace oldest
            idx = len(self.buffer) % self.capacity
            self.buffer[idx] = experience
            self.priorities[idx] = max_priority

    def sample(self, batch_size=64):
        # Sample based on priorities
        priorities = np.array(self.priorities)
        probs = priorities ** self.alpha
        probs /= probs.sum()

        indices = np.random.choice(len(self.buffer), batch_size, p=probs)
        samples = [self.buffer[i] for i in indices]

        # Importance sampling weights
        weights = (len(self.buffer) * probs[indices]) ** (-self.beta)
        weights /= weights.max()

        return samples, weights, indices

    def update_priorities(self, indices, td_errors):
        # Update priorities based on TD error
        for idx, error in zip(indices, td_errors):
            self.priorities[idx] = abs(error) + 1e-6
```

**Training Orchestrator:**

```python
class TradingOrchestrator:
    """Manages paper trading + RL training."""

    def __init__(self, node, rl_agent, experience_buffer):
        self.node = node
        self.rl_agent = rl_agent
        self.experience_buffer = experience_buffer
        self.trainer = RLTrainer(agent, buffer, config)

    async def training_loop(self):
        """Background training loop."""
        while self._running:
            # Train if enough experiences
            if self.trainer.should_train():
                metrics = await self.trainer.train_step()
                self.log_metrics(metrics)

            await asyncio.sleep(60)  # Check every minute

    def stop(self):
        """Graceful shutdown."""
        self._running = False

        # Save checkpoint
        checkpoint_path = f"models/moomoo_rl_agent_{timestamp}.pt"
        self.trainer.save_checkpoint(checkpoint_path)
```

---

## Data Flow

### Market Data Flow

```
Moomoo Servers
      │
      ▼
  OpenD Gateway (localhost:11111)
      │
      ▼
  MoomooDataClient._quote_handler()
      │
      ▼
  Parse to QuoteTick/TradeTick
      │
      ▼
  NautilusTrader Message Bus
      │
      ├──► Cache (store)
      │
      └──► Strategy.on_quote_tick()
               │
               ▼
          Bar Aggregator (if subscribed to bars)
               │
               ▼
          Strategy.on_bar()
               │
               ▼
          Decision Logic (+ RL Agent)
               │
               ▼
          Order Generation
```

### Order Execution Flow

```
Strategy.submit_order(order)
      │
      ▼
  Order Factory (create Order object)
      │
      ▼
  Risk Engine (pre-trade checks)
      │
      ├──► PASS → Continue
      │
      └──► FAIL → OrderRejected event
      │
      ▼
  Execution Engine (route to venue)
      │
      ▼
  MoomooExecClient.submit_order()
      │
      ▼
  OpenD Gateway.place_order()
      │
      ▼
  Moomoo Servers (order matching)
      │
      ├──► OrderAccepted event
      │
      └──► OrderFilled event
               │
               ▼
          Position Updated
               │
               ▼
          Strategy.on_order_filled()
               │
               ▼
          Experience Stored (for RL)
```

### RL Training Flow

```
Trade Completed
      │
      ▼
  RewardCalculator.calculate_reward()
      │
      ▼
  CreditAssignment (N-step TD)
      │
      ▼
  Experience(state, action, reward, next_state)
      │
      ▼
  PrioritizedReplayBuffer.add(experience)
      │
      ▼
  [Buffer accumulates 100+ experiences]
      │
      ▼
  RLTrainer.should_train() → True
      │
      ▼
  RLTrainer.train_step()
      │
      ├──► Sample batch (64 experiences)
      │
      ├──► Compute TD error
      │
      ├──► Update policy (gradient descent)
      │
      ├──► Update priorities
      │
      └──► Log metrics (Prometheus)
```

---

## Event-Driven Architecture

NautilusTrader uses an event-driven architecture for all market data, orders, and system events.

### Event Types

| Event Type | Trigger | Handler |
|------------|---------|---------|
| `QuoteTick` | New bid/ask quote | `on_quote_tick()` |
| `TradeTick` | Trade execution (market) | `on_trade_tick()` |
| `Bar` | Time/volume bar complete | `on_bar()` |
| `OrderSubmitted` | Order sent to venue | `on_order_submitted()` |
| `OrderAccepted` | Venue confirms order | `on_order_accepted()` |
| `OrderFilled` | Order fully executed | `on_order_filled()` |
| `PositionOpened` | New position created | `on_position_opened()` |
| `PositionClosed` | Position exits | `on_position_closed()` |

### Event Flow Example

```python
# In Strategy class
def on_bar(self, bar: Bar):
    """Called when new 1-minute bar completes."""

    # Update indicators
    self.rsi.update(bar)
    self.atr.update(bar)

    # Build state for RL agent
    state = self.state_builder.build_state(bar, self.position, self.indicators)

    # Get RL action
    action = self.rl_agent.select_action(state)

    # Execute action
    if action == Action.BUY and self.position is None:
        self.enter_long(bar)

    elif action == Action.EXIT and self.position is not None:
        self.close_position(bar)

def enter_long(self, bar: Bar):
    """Enter long position."""
    order = self.order_factory.market(
        instrument_id=self.instrument,
        order_side=OrderSide.BUY,
        quantity=self.calculate_quantity(bar),
    )
    self.submit_order(order)  # Triggers OrderSubmitted event

def on_order_filled(self, event: OrderFilled):
    """Order filled by venue."""
    self._log.info(f"Order filled: {event}")

    # Position now open, save entry state for RL
    self.entry_state = self.last_state
    self.entry_time = event.ts_event

def on_position_closed(self, event: PositionClosed):
    """Position closed."""
    # Calculate reward
    trade = self.create_trade_summary(event.position)
    reward = self.reward_calculator.calculate_reward(trade)

    # Store experience
    experience = Experience(
        state=self.entry_state,
        action=self.entry_action,
        reward=reward,
        next_state=self.last_state,
    )
    self.experience_buffer.add(experience)
```

---

## Performance Characteristics

### Latency

| Operation | Typical Latency |
|-----------|-----------------|
| QuoteTick processing | < 1 ms |
| Bar aggregation | < 5 ms |
| Strategy on_bar() | 5-20 ms |
| RL inference (CPU) | 10-30 ms |
| Order submission | 10-50 ms |
| OpenD round-trip | 5-20 ms |
| End-to-end (quote → order) | 30-100 ms |

### Throughput

| Metric | Capacity |
|--------|----------|
| Quotes/second | 10,000+ |
| Bars/second | 1,000+ |
| Orders/minute | 15 (API limit) |
| Strategies (concurrent) | 10-20 |
| Instruments (concurrent) | 50-100 |

### Memory Usage

| Component | Memory |
|-----------|--------|
| NautilusTrader Engine | 100-200 MB |
| Moomoo Adapter | 50-100 MB |
| RL Framework | 100-300 MB |
| Experience Buffer (100K) | 500 MB - 1 GB |
| **Total** | **1-2 GB** |

### Storage

| Data | Size per Day |
|------|--------------|
| Logs | 10-50 MB |
| Trade records | 1-5 MB |
| Metrics (Prometheus) | 50-100 MB |
| Model checkpoints | 10-50 MB |
| **Total** | **70-200 MB** |

---

## Design Decisions

### Why NautilusTrader?

**Chosen for:**
- Rust core = nanosecond precision + safety
- Event-driven = natural for algo trading
- Adapter system = easy to add Moomoo
- Production-grade = used by prop shops

**Alternatives considered:**
- Backtrader (Python-only, slower)
- QuantConnect (cloud-based, less control)
- Custom system (too much reinvention)

### Why Reinforcement Learning?

**Problem:** Static rule-based strategies can't adapt:
- Market regimes change
- Optimal holding periods vary
- Entry/exit timing is nuanced

**RL Solution:**
- Learn from experience (trades)
- Adapt to changing conditions
- Optimize for long-term reward (not single trade)

**Key Innovation: "Seeing Out" Bonus**
- Encourages holding winners longer
- Penalizes holding losers
- Addresses #1 trader psychology issue

### Why Paper Trading First?

**Risk-free validation:**
- Test strategies with real market data
- Validate RL training works
- Identify bugs before risking capital

**Accelerated learning:**
- 30 days paper trading = validate approach
- Historical pre-training = 2+ years compressed to days
- Parallel instruments = faster experience collection

**Seamless transition:**
- Same code for paper and live
- Only config change: `trading_mode="LIVE"`

### Why Docker for Infrastructure?

**Portability:**
- Consistent environment (dev/prod)
- Easy deployment
- Version pinning

**Isolation:**
- Services don't conflict
- Easy to restart/upgrade
- Resource limits

**Monitoring:**
- Grafana/Prometheus = industry standard
- Pre-built dashboards
- Alert integration

---

**For API usage examples, see [API_REFERENCE.md](API_REFERENCE.md).**
