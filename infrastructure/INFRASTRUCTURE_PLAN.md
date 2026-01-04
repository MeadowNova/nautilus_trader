# Production Infrastructure Plan - Nautilus Trader

**Created:** January 2025  
**Purpose:** PostgreSQL, Redis, Monitoring stack for production trading system  
**Status:** Planning → Implementation

---

## Overview

This document outlines the complete production infrastructure for the Nautilus Trader system, including:
1. **PostgreSQL** - Data persistence (historical data, backtest results, trades)
2. **Redis** - Caching layer (real-time data, strategy state, rate limiting)
3. **Prometheus + Grafana** - Monitoring and visualization
4. **Docker Compose** - Orchestration for all services

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                     Nautilus Trader                         │
│                   (Python Application)                       │
└───────┬─────────────────┬─────────────────┬────────────────┘
        │                 │                 │
        ▼                 ▼                 ▼
  ┌──────────┐     ┌──────────┐     ┌──────────────┐
  │PostgreSQL│     │  Redis   │     │  Prometheus  │
  │(Storage) │     │ (Cache)  │     │  (Metrics)   │
  └──────────┘     └──────────┘     └───────┬──────┘
                                            │
                                            ▼
                                    ┌──────────────┐
                                    │   Grafana    │
                                    │(Dashboards)  │
                                    └──────────────┘
```

---

## 1. PostgreSQL Setup

### Purpose
- Store historical OHLCV market data
- Archive backtest results and performance metrics
- Maintain trade history and execution logs
- Track strategy parameter versions

### Schema Design

```sql
-- ============================================
-- MARKET DATA STORAGE
-- ============================================
CREATE TABLE market_data (
    id BIGSERIAL PRIMARY KEY,
    exchange VARCHAR(50) NOT NULL,
    symbol VARCHAR(50) NOT NULL,
    timeframe VARCHAR(10) NOT NULL,
    timestamp BIGINT NOT NULL,  -- Unix timestamp in nanoseconds
    open DECIMAL(20,8) NOT NULL,
    high DECIMAL(20,8) NOT NULL,
    low DECIMAL(20,8) NOT NULL,
    close DECIMAL(20,8) NOT NULL,
    volume DECIMAL(20,8) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(exchange, symbol, timeframe, timestamp)
);

CREATE INDEX idx_market_data_lookup 
ON market_data(exchange, symbol, timeframe, timestamp);

CREATE INDEX idx_market_data_timestamp 
ON market_data(timestamp DESC);

-- Partition by month for performance
CREATE TABLE market_data_2024_01 PARTITION OF market_data
FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');
-- (Create partitions for each month)

-- ============================================
-- BACKTEST RESULTS
-- ============================================
CREATE TABLE backtests (
    id SERIAL PRIMARY KEY,
    run_id VARCHAR(100) UNIQUE NOT NULL,  -- UUID for this backtest run
    strategy_name VARCHAR(100) NOT NULL,
    strategy_version VARCHAR(20),
    instrument VARCHAR(50) NOT NULL,
    start_date TIMESTAMP NOT NULL,
    end_date TIMESTAMP NOT NULL,
    
    -- Capital metrics
    initial_capital DECIMAL(20,2) NOT NULL,
    final_capital DECIMAL(20,2) NOT NULL,
    total_pnl DECIMAL(20,2) NOT NULL,
    total_pnl_pct DECIMAL(10,4),
    
    -- Trading metrics
    total_trades INTEGER DEFAULT 0,
    winning_trades INTEGER DEFAULT 0,
    losing_trades INTEGER DEFAULT 0,
    win_rate DECIMAL(5,2),
    
    -- Risk metrics
    sharpe_ratio DECIMAL(10,4),
    sortino_ratio DECIMAL(10,4),
    max_drawdown DECIMAL(10,4),
    max_drawdown_pct DECIMAL(10,4),
    calmar_ratio DECIMAL(10,4),
    
    -- Other metrics
    profit_factor DECIMAL(10,4),
    avg_win DECIMAL(20,2),
    avg_loss DECIMAL(20,2),
    largest_win DECIMAL(20,2),
    largest_loss DECIMAL(20,2),
    
    -- Strategy configuration
    parameters JSONB,  -- Store strategy parameters
    
    -- Metadata
    created_at TIMESTAMP DEFAULT NOW(),
    duration_seconds INTEGER,
    data_bars_processed BIGINT,
    notes TEXT
);

CREATE INDEX idx_backtests_strategy 
ON backtests(strategy_name, created_at DESC);

CREATE INDEX idx_backtests_performance 
ON backtests(sharpe_ratio DESC, total_pnl DESC);

-- ============================================
-- INDIVIDUAL TRADES
-- ============================================
CREATE TABLE trades (
    id BIGSERIAL PRIMARY KEY,
    backtest_id INTEGER REFERENCES backtests(id) ON DELETE CASCADE,
    trade_id VARCHAR(100) NOT NULL,
    
    -- Trade details
    instrument VARCHAR(50) NOT NULL,
    side VARCHAR(10) NOT NULL,  -- BUY or SELL
    quantity DECIMAL(20,8) NOT NULL,
    
    -- Entry
    entry_price DECIMAL(20,8) NOT NULL,
    entry_time BIGINT NOT NULL,
    entry_order_id VARCHAR(100),
    
    -- Exit
    exit_price DECIMAL(20,8),
    exit_time BIGINT,
    exit_order_id VARCHAR(100),
    exit_reason VARCHAR(50),  -- STOP_LOSS, TAKE_PROFIT, SIGNAL, etc.
    
    -- P&L
    pnl DECIMAL(20,2),
    pnl_pct DECIMAL(10,4),
    commission DECIMAL(20,2) DEFAULT 0,
    
    -- Duration
    duration_seconds INTEGER,
    
    -- Metadata
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_trades_backtest 
ON trades(backtest_id, entry_time);

CREATE INDEX idx_trades_performance 
ON trades(pnl DESC);

-- ============================================
-- PERFORMANCE METRICS (TIME SERIES)
-- ============================================
CREATE TABLE performance_metrics (
    id SERIAL PRIMARY KEY,
    backtest_id INTEGER REFERENCES backtests(id) ON DELETE CASCADE,
    timestamp BIGINT NOT NULL,
    
    -- Equity curve
    equity DECIMAL(20,2) NOT NULL,
    cash_balance DECIMAL(20,2),
    unrealized_pnl DECIMAL(20,2) DEFAULT 0,
    
    -- Rolling metrics
    rolling_sharpe DECIMAL(10,4),
    rolling_drawdown DECIMAL(10,4),
    
    -- Position data
    open_positions INTEGER DEFAULT 0,
    position_value DECIMAL(20,2) DEFAULT 0,
    
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_performance_backtest_ts 
ON performance_metrics(backtest_id, timestamp);

-- ============================================
-- STRATEGY VERSIONS
-- ============================================
CREATE TABLE strategy_versions (
    id SERIAL PRIMARY KEY,
    strategy_name VARCHAR(100) NOT NULL,
    version VARCHAR(20) NOT NULL,
    parameters JSONB NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(strategy_name, version)
);

-- ============================================
-- EXCHANGE API LOGS (for live trading)
-- ============================================
CREATE TABLE api_logs (
    id BIGSERIAL PRIMARY KEY,
    exchange VARCHAR(50) NOT NULL,
    endpoint VARCHAR(200) NOT NULL,
    method VARCHAR(10) NOT NULL,  -- GET, POST, etc.
    status_code INTEGER,
    latency_ms INTEGER,
    request_payload JSONB,
    response_payload JSONB,
    error_message TEXT,
    timestamp BIGINT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_api_logs_exchange_time 
ON api_logs(exchange, timestamp DESC);

-- ============================================
-- HELPER VIEWS
-- ============================================

-- View: Best performing strategies
CREATE VIEW v_top_strategies AS
SELECT 
    strategy_name,
    COUNT(*) as total_runs,
    AVG(total_pnl) as avg_pnl,
    AVG(win_rate) as avg_win_rate,
    AVG(sharpe_ratio) as avg_sharpe,
    MAX(total_pnl) as best_pnl,
    MIN(max_drawdown) as best_drawdown
FROM backtests
GROUP BY strategy_name
ORDER BY avg_sharpe DESC;

-- View: Recent backtest summary
CREATE VIEW v_recent_backtests AS
SELECT 
    b.id,
    b.run_id,
    b.strategy_name,
    b.instrument,
    b.total_pnl,
    b.win_rate,
    b.sharpe_ratio,
    b.max_drawdown,
    COUNT(t.id) as num_trades,
    b.created_at
FROM backtests b
LEFT JOIN trades t ON t.backtest_id = b.id
GROUP BY b.id
ORDER BY b.created_at DESC
LIMIT 50;
```

### Docker Configuration

**File:** `infrastructure/docker/docker-compose.yml`

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:16-alpine
    container_name: nautilus_postgres
    environment:
      POSTGRES_DB: nautilus_trader
      POSTGRES_USER: nautilus
      POSTGRES_PASSWORD: ${DB_PASSWORD:-changeme}
      PGDATA: /var/lib/postgresql/data/pgdata
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./postgres/schema.sql:/docker-entrypoint-initdb.d/01-schema.sql
      - ./postgres/init.sql:/docker-entrypoint-initdb.d/02-init.sql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U nautilus -d nautilus_trader"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped

volumes:
  postgres_data:
    driver: local
```

### Connection Configuration

**Python Example:**
```python
import psycopg2
from psycopg2.extras import RealDictCursor
import os

def get_db_connection():
    """Create PostgreSQL connection."""
    return psycopg2.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        port=os.getenv('DB_PORT', 5432),
        database=os.getenv('DB_NAME', 'nautilus_trader'),
        user=os.getenv('DB_USER', 'nautilus'),
        password=os.getenv('DB_PASSWORD', 'changeme'),
        cursor_factory=RealDictCursor
    )

def save_backtest_result(result_data):
    """Save backtest result to database."""
    conn = get_db_connection()
    cur = conn.cursor()
    
    query = """
        INSERT INTO backtests (
            run_id, strategy_name, instrument, start_date, end_date,
            initial_capital, final_capital, total_pnl, total_trades,
            win_rate, sharpe_ratio, max_drawdown, parameters
        ) VALUES (
            %(run_id)s, %(strategy_name)s, %(instrument)s, %(start_date)s, %(end_date)s,
            %(initial_capital)s, %(final_capital)s, %(total_pnl)s, %(total_trades)s,
            %(win_rate)s, %(sharpe_ratio)s, %(max_drawdown)s, %(parameters)s
        ) RETURNING id;
    """
    
    cur.execute(query, result_data)
    backtest_id = cur.fetchone()['id']
    
    conn.commit()
    cur.close()
    conn.close()
    
    return backtest_id
```

---

## 2. Redis Setup

### Purpose
- Cache real-time market data (tickers, order books)
- Store strategy state and session data
- Implement rate limiting for exchange API calls
- Pub/sub for real-time updates

### Cache Key Design

```python
# Market data keys (TTL: 5 seconds)
f"market:{exchange}:{symbol}:ticker"
f"market:{exchange}:{symbol}:orderbook"
f"market:{exchange}:{symbol}:trades"

# Strategy state keys (TTL: 60 seconds)
f"strategy:{strategy_name}:state"
f"strategy:{strategy_name}:positions"
f"strategy:{strategy_name}:orders"

# Rate limiting keys (TTL: 60 seconds)
f"ratelimit:{exchange}:{endpoint}:count"
f"ratelimit:{exchange}:global:requests"

# Session management (TTL: 1 hour)
f"session:{session_id}:data"
f"session:{session_id}:last_activity"

# Price alerts (no TTL)
f"alert:{symbol}:price_above:{price}"
f"alert:{symbol}:price_below:{price}"
```

### Redis Configuration

**File:** `infrastructure/redis/redis.conf`

```conf
# Network
bind 0.0.0.0
port 6379
protected-mode yes
requirepass ${REDIS_PASSWORD}

# Memory management
maxmemory 256mb
maxmemory-policy allkeys-lru  # Evict least recently used keys

# Persistence (for important data)
save 900 1        # Save if 1 key changed in 15 minutes
save 300 10       # Save if 10 keys changed in 5 minutes
save 60 10000     # Save if 10000 keys changed in 1 minute

appendonly yes
appendfilename "appendonly.aof"
appendfsync everysec

# Performance
tcp-backlog 511
timeout 300
tcp-keepalive 60

# Logging
loglevel notice
logfile /var/log/redis/redis.log

# Limits
maxclients 10000
```

### Docker Configuration

```yaml
  redis:
    image: redis:7-alpine
    container_name: nautilus_redis
    command: redis-server /usr/local/etc/redis/redis.conf --requirepass ${REDIS_PASSWORD:-changeme}
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
      - ./redis/redis.conf:/usr/local/etc/redis/redis.conf
    healthcheck:
      test: ["CMD", "redis-cli", "--raw", "incr", "ping"]
      interval: 10s
      timeout: 3s
      retries: 5
    restart: unless-stopped

volumes:
  redis_data:
    driver: local
```

### Python Integration

```python
import redis
import json
from typing import Optional
import os

class RedisCache:
    """Redis cache manager for Nautilus Trader."""
    
    def __init__(self):
        self.client = redis.Redis(
            host=os.getenv('REDIS_HOST', 'localhost'),
            port=int(os.getenv('REDIS_PORT', 6379)),
            password=os.getenv('REDIS_PASSWORD', 'changeme'),
            db=0,
            decode_responses=True
        )
    
    def cache_ticker(self, exchange: str, symbol: str, data: dict, ttl: int = 5):
        """Cache ticker data."""
        key = f"market:{exchange}:{symbol}:ticker"
        self.client.setex(key, ttl, json.dumps(data))
    
    def get_ticker(self, exchange: str, symbol: str) -> Optional[dict]:
        """Get cached ticker data."""
        key = f"market:{exchange}:{symbol}:ticker"
        data = self.client.get(key)
        return json.loads(data) if data else None
    
    def check_rate_limit(self, exchange: str, endpoint: str, limit: int, window: int = 60) -> bool:
        """Check if rate limit is exceeded."""
        key = f"ratelimit:{exchange}:{endpoint}:count"
        current = self.client.get(key)
        
        if current is None:
            self.client.setex(key, window, 1)
            return True
        
        if int(current) >= limit:
            return False
        
        self.client.incr(key)
        return True
```

---

## 3. Monitoring Stack (Prometheus + Grafana)

### Purpose
- Collect system and application metrics
- Visualize performance in real-time
- Alert on critical conditions
- Track historical performance

### Prometheus Configuration

**File:** `infrastructure/monitoring/prometheus.yml`

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s
  external_labels:
    cluster: 'nautilus_trader'
    environment: 'production'

# Alerting configuration
alerting:
  alertmanagers:
    - static_configs:
        - targets:
            - alertmanager:9093

# Scrape configurations
scrape_configs:
  # Nautilus Trader application metrics
  - job_name: 'nautilus_trader'
    static_configs:
      - targets: ['host.docker.internal:8000']
    metrics_path: '/metrics'
    scrape_interval: 10s
  
  # PostgreSQL metrics
  - job_name: 'postgres'
    static_configs:
      - targets: ['postgres_exporter:9187']
  
  # Redis metrics
  - job_name: 'redis'
    static_configs:
      - targets: ['redis_exporter:9121']
  
  # Node (system) metrics
  - job_name: 'node'
    static_configs:
      - targets: ['node_exporter:9100']
```

### Docker Configuration

```yaml
  prometheus:
    image: prom/prometheus:latest
    container_name: nautilus_prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
      - ./monitoring/alerts.yml:/etc/prometheus/alerts.yml
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.console.libraries=/etc/prometheus/console_libraries'
      - '--web.console.templates=/etc/prometheus/consoles'
      - '--storage.tsdb.retention.time=30d'
      - '--web.enable-lifecycle'
    restart: unless-stopped

  grafana:
    image: grafana/grafana:latest
    container_name: nautilus_grafana
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_USER=${GRAFANA_USER:-admin}
      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_PASSWORD:-admin}
      - GF_INSTALL_PLUGINS=redis-datasource,postgres-datasource
    volumes:
      - grafana_data:/var/lib/grafana
      - ./monitoring/grafana/dashboards:/etc/grafana/provisioning/dashboards
      - ./monitoring/grafana/datasources:/etc/grafana/provisioning/datasources
    depends_on:
      - prometheus
    restart: unless-stopped

  # Exporters for additional metrics
  postgres_exporter:
    image: prometheuscommunity/postgres-exporter
    container_name: nautilus_postgres_exporter
    environment:
      DATA_SOURCE_NAME: "postgresql://nautilus:${DB_PASSWORD:-changeme}@postgres:5432/nautilus_trader?sslmode=disable"
    ports:
      - "9187:9187"
    depends_on:
      - postgres
    restart: unless-stopped

  redis_exporter:
    image: oliver006/redis_exporter
    container_name: nautilus_redis_exporter
    environment:
      REDIS_ADDR: "redis:6379"
      REDIS_PASSWORD: "${REDIS_PASSWORD:-changeme}"
    ports:
      - "9121:9121"
    depends_on:
      - redis
    restart: unless-stopped

volumes:
  prometheus_data:
  grafana_data:
```

### Key Metrics to Track

```python
from prometheus_client import Counter, Gauge, Histogram, Summary

# Trading metrics
trades_total = Counter('nautilus_trades_total', 'Total trades executed', ['strategy', 'instrument', 'side'])
pnl_total = Gauge('nautilus_pnl_total', 'Total P&L', ['strategy'])
open_positions = Gauge('nautilus_open_positions', 'Number of open positions', ['strategy'])
win_rate = Gauge('nautilus_win_rate', 'Strategy win rate', ['strategy'])

# Performance metrics
sharpe_ratio = Gauge('nautilus_sharpe_ratio', 'Sharpe ratio', ['strategy'])
drawdown = Gauge('nautilus_drawdown', 'Current drawdown', ['strategy'])
equity = Gauge('nautilus_equity', 'Current equity', ['strategy'])

# System metrics
order_latency = Histogram('nautilus_order_latency_seconds', 'Order submission latency')
api_errors = Counter('nautilus_api_errors_total', 'API errors', ['exchange', 'error_type'])

# Exchange metrics
exchange_uptime = Gauge('nautilus_exchange_uptime', 'Exchange uptime', ['exchange'])
api_rate_limit_remaining = Gauge('nautilus_api_rate_limit', 'API rate limit remaining', ['exchange'])
```

### Grafana Dashboards

**Dashboard 1: Trading Overview**
- Real-time P&L chart
- Open positions count
- Trade distribution (wins/losses)
- Equity curve
- Win rate gauge

**Dashboard 2: Strategy Performance**
- Sharpe ratio trends
- Drawdown analysis
- Trade frequency
- Average trade duration
- Profit factor

**Dashboard 3: System Health**
- CPU usage
- Memory usage
- Disk I/O
- Network latency
- Error rates

**Dashboard 4: Exchange Monitoring**
- API call rates
- API latencies
- Error rates by exchange
- Rate limit status
- Connection status

---

## 4. Complete Docker Compose

**File:** `infrastructure/docker/docker-compose.yml`

```yaml
version: '3.8'

services:
  # ============================================
  # DATABASE
  # ============================================
  postgres:
    image: postgres:16-alpine
    container_name: nautilus_postgres
    environment:
      POSTGRES_DB: nautilus_trader
      POSTGRES_USER: nautilus
      POSTGRES_PASSWORD: ${DB_PASSWORD:-changeme}
      PGDATA: /var/lib/postgresql/data/pgdata
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./postgres/schema.sql:/docker-entrypoint-initdb.d/01-schema.sql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U nautilus -d nautilus_trader"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped
    networks:
      - nautilus_network

  # ============================================
  # CACHE
  # ============================================
  redis:
    image: redis:7-alpine
    container_name: nautilus_redis
    command: redis-server /usr/local/etc/redis/redis.conf --requirepass ${REDIS_PASSWORD:-changeme}
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
      - ./redis/redis.conf:/usr/local/etc/redis/redis.conf
    healthcheck:
      test: ["CMD", "redis-cli", "--raw", "incr", "ping"]
      interval: 10s
      timeout: 3s
      retries: 5
    restart: unless-stopped
    networks:
      - nautilus_network

  # ============================================
  # MONITORING
  # ============================================
  prometheus:
    image: prom/prometheus:latest
    container_name: nautilus_prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
      - ./monitoring/alerts.yml:/etc/prometheus/alerts.yml
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--storage.tsdb.retention.time=30d'
      - '--web.enable-lifecycle'
    restart: unless-stopped
    networks:
      - nautilus_network

  grafana:
    image: grafana/grafana:latest
    container_name: nautilus_grafana
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_USER=${GRAFANA_USER:-admin}
      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_PASSWORD:-admin}
      - GF_INSTALL_PLUGINS=redis-datasource,postgres-datasource
    volumes:
      - grafana_data:/var/lib/grafana
      - ./monitoring/grafana/dashboards:/etc/grafana/provisioning/dashboards
      - ./monitoring/grafana/datasources:/etc/grafana/provisioning/datasources
    depends_on:
      - prometheus
    restart: unless-stopped
    networks:
      - nautilus_network

  # ============================================
  # EXPORTERS
  # ============================================
  postgres_exporter:
    image: prometheuscommunity/postgres-exporter
    container_name: nautilus_postgres_exporter
    environment:
      DATA_SOURCE_NAME: "postgresql://nautilus:${DB_PASSWORD:-changeme}@postgres:5432/nautilus_trader?sslmode=disable"
    ports:
      - "9187:9187"
    depends_on:
      - postgres
    restart: unless-stopped
    networks:
      - nautilus_network

  redis_exporter:
    image: oliver006/redis_exporter
    container_name: nautilus_redis_exporter
    environment:
      REDIS_ADDR: "redis:6379"
      REDIS_PASSWORD: "${REDIS_PASSWORD:-changeme}"
    ports:
      - "9121:9121"
    depends_on:
      - redis
    restart: unless-stopped
    networks:
      - nautilus_network

networks:
  nautilus_network:
    driver: bridge

volumes:
  postgres_data:
  redis_data:
  prometheus_data:
  grafana_data:
```

---

## 5. Environment Configuration

**File:** `infrastructure/.env.example`

```bash
# PostgreSQL
DB_HOST=localhost
DB_PORT=5432
DB_NAME=nautilus_trader
DB_USER=nautilus
DB_PASSWORD=changeme_secure_password

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=changeme_secure_password

# Grafana
GRAFANA_USER=admin
GRAFANA_PASSWORD=changeme_secure_password

# Exchange API Keys (for live trading)
KRAKEN_API_KEY=your_api_key
KRAKEN_API_SECRET=your_api_secret

# Application
LOG_LEVEL=INFO
ENVIRONMENT=development
```

**File:** `.env.local` (gitignored)
```bash
# Copy .env.example and fill with real credentials
# NEVER commit this file to git
```

---

## 6. Deployment Instructions

### Initial Setup

```bash
# 1. Create infrastructure directory
cd /home/ajk/Nautilus/nautilus_trader
mkdir -p infrastructure/{docker,postgres,redis,monitoring/grafana/{dashboards,datasources}}

# 2. Copy configuration files
# (Copy docker-compose.yml, schema.sql, redis.conf, prometheus.yml)

# 3. Create environment file
cp infrastructure/.env.example infrastructure/.env.local
# Edit .env.local with secure passwords

# 4. Start services
cd infrastructure/docker
docker-compose up -d

# 5. Verify services
docker-compose ps
docker-compose logs -f
```

### Health Checks

```bash
# PostgreSQL
docker exec nautilus_postgres pg_isready -U nautilus

# Redis
docker exec nautilus_redis redis-cli ping

# Check all services
docker-compose ps
```

### Accessing Services

```bash
# Grafana: http://localhost:3000
# Username: admin (or from .env.local)
# Password: (from .env.local)

# Prometheus: http://localhost:9090

# PostgreSQL: localhost:5432
psql -h localhost -U nautilus -d nautilus_trader

# Redis: localhost:6379
redis-cli -h localhost -p 6379 -a your_password
```

---

## 7. Maintenance

### Backup

```bash
# PostgreSQL backup
docker exec nautilus_postgres pg_dump -U nautilus nautilus_trader > backup_$(date +%Y%m%d).sql

# Redis backup
docker exec nautilus_redis redis-cli --rdb /data/dump.rdb SAVE
docker cp nautilus_redis:/data/dump.rdb backup_redis_$(date +%Y%m%d).rdb
```

### Monitoring

```bash
# View logs
docker-compose logs -f [service_name]

# Resource usage
docker stats

# Disk usage
docker system df
```

### Updates

```bash
# Pull latest images
docker-compose pull

# Restart services
docker-compose down
docker-compose up -d
```

---

## 8. Security Checklist

- [ ] Change all default passwords
- [ ] Use strong passwords (20+ characters)
- [ ] Never commit `.env.local` to git
- [ ] Enable PostgreSQL SSL in production
- [ ] Use Redis password authentication
- [ ] Restrict network access (firewall rules)
- [ ] Regular backups (automated)
- [ ] Monitor for suspicious activity
- [ ] Keep Docker images updated
- [ ] Use secrets manager (Vault) for production

---

## 9. Performance Tuning

### PostgreSQL
```sql
-- Connection pooling
shared_buffers = 256MB
effective_cache_size = 1GB
maintenance_work_mem = 64MB
```

### Redis
```conf
# Increase max clients if needed
maxclients 10000

# Adjust memory based on usage
maxmemory 512mb
```

### Docker
```yaml
# Resource limits
services:
  postgres:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
```

---

## 10. Next Steps

**Week 1:**
- [ ] Create all infrastructure files
- [ ] Test local deployment
- [ ] Verify database schema
- [ ] Test Redis caching
- [ ] Set up basic Grafana dashboards

**Week 2:**
- [ ] Integrate with Nautilus Trader
- [ ] Store backtest results in PostgreSQL
- [ ] Implement Redis caching in strategies
- [ ] Create comprehensive dashboards
- [ ] Set up alerting rules

**Week 3:**
- [ ] Performance testing
- [ ] Security hardening
- [ ] Backup automation
- [ ] Documentation completion

---

**Last Updated:** January 2025  
**Status:** Planning Complete → Ready for Implementation  
**Estimated Setup Time:** 6-8 hours
