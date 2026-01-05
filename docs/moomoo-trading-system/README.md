# Nautilus Trader Production Infrastructure

**Complete Docker-based infrastructure for algorithmic trading**

---

## 🎯 Quick Start (5 Minutes)

```bash
# 1. Navigate to infrastructure
cd /home/ajk/Nautilus/nautilus_trader/infrastructure

# 2. Run automated setup
./setup.sh

# 3. Access Grafana
open http://localhost:3000

# ✅ Done! Your trading infrastructure is running.
```

---

## 📚 Documentation

| Document | Purpose | When to Read |
|----------|---------|--------------|
| **[OPERATIONS_GUIDE.md](OPERATIONS_GUIDE.md)** | Complete guide from setup to live trading | **Start here** |
| **[plan.md](../ai-working/database_Infra layer/plan.md)** | Detailed implementation plan | For developers |
| **[docker-compose.yml](docker/docker-compose.yml)** | Service orchestration | For configuration |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Docker Infrastructure                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐           │
│  │ PostgreSQL  │  │   Redis     │  │ Prometheus  │           │
│  │  (Data)     │  │  (Cache)    │  │  (Metrics)  │           │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘           │
│         │                │                │                    │
│         └────────────────┴────────────────┘                    │
│                          │                                     │
│                  ┌───────▼────────┐                            │
│                  │    Grafana     │                            │
│                  │  (Dashboards)  │                            │
│                  └────────────────┘                            │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                          ▲
                          │
                ┌─────────┴──────────┐
                │  Nautilus Trader   │
                │  (Your Strategies) │
                └────────────────────┘
```

---

## 📦 What's Included

### Services

| Service | Port | Purpose |
|---------|------|---------|
| **PostgreSQL 16** | 5432 | Persistent data storage (backtests, trades) |
| **Redis 7** | 6379 | High-speed caching (strategy state, ML models) |
| **Prometheus** | 9090 | Metrics collection |
| **Grafana** | 3000 | Visualization dashboards |
| **Postgres Exporter** | 9187 | PostgreSQL metrics |
| **Redis Exporter** | 9121 | Redis metrics |

### Database Schema

**Core Tables:**
- `backtests` - Backtest results with full metrics
- `trades` - Individual trade records
- `ml_optimization_log` - ML parameter adjustments
- `regime_detection_log` - Market regime changes
- `pattern_detection_log` - Chart patterns detected
- `risk_events` - Risk management events
- `sentiment_log` - Social sentiment data
- `performance_metrics` - Time-series equity curve

**Helper Views:**
- `v_strategy_health` - Strategy health dashboard
- `v_top_strategies` - Best performing configurations
- `v_recent_backtests` - Recent backtest summary

### Configuration Files

```
infrastructure/
├── .env.template           # Environment variables template
├── .env.local              # Your secrets (gitignored)
├── setup.sh                # Automated setup script
├── OPERATIONS_GUIDE.md     # Complete operations manual
├── README.md               # This file
│
├── docker/
│   └── docker-compose.yml  # Service orchestration
│
├── postgres/
│   ├── postgresql.conf     # PostgreSQL tuning
│   ├── 01-base-schema.sql  # Base Nautilus schema
│   ├── 02-ai-extensions.sql # AI-specific tables
│   └── 03-indexes.sql      # Performance indexes
│
└── monitoring/
    ├── prometheus/
    │   ├── prometheus.yml  # Metrics collection config
    │   └── alerts.yml      # Alert rules
    │
    └── grafana/
        ├── provisioning/   # Auto-configuration
        └── dashboards/     # Pre-built dashboards
```

---

## 🚀 Usage

### Start Everything
```bash
cd infrastructure/docker
docker-compose up -d
```

### Check Status
```bash
docker-compose ps
```

Expected output:
```
NAME                       STATUS
nautilus_postgres          Up (healthy)
nautilus_redis             Up (healthy)
nautilus_prometheus        Up (healthy)
nautilus_grafana           Up (healthy)
nautilus_postgres_exporter Up
nautilus_redis_exporter    Up
```

### View Logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f postgres
docker-compose logs -f redis
docker-compose logs -f grafana
```

### Stop Everything
```bash
docker-compose down
```

### Restart a Service
```bash
docker-compose restart postgres
```

### Complete Reset (⚠️ DELETES ALL DATA)
```bash
docker-compose down -v
docker-compose up -d
```

---

## 🔐 Security

### Initial Setup
1. **Copy template:** `cp .env.template .env.local`
2. **Generate passwords:** Use `openssl rand -base64 24` for each
3. **Secure file:** `chmod 600 .env.local`
4. **Verify gitignore:** `.env.local` should be listed

### Required Changes in .env.local
```bash
DB_PASSWORD=<generate_strong_password>
REDIS_PASSWORD=<generate_strong_password>
GRAFANA_PASSWORD=<generate_strong_password>
```

### API Keys (for paper/live trading)
Add exchange API keys to `.env.local` when ready for Phase 3+:
```bash
BINANCE_API_KEY=
BINANCE_API_SECRET=
BINANCE_TESTNET=true  # false for live
```

**⚠️ NEVER commit .env.local to git!**

---

## 📊 Monitoring

### Access Grafana
1. Open: http://localhost:3000
2. Login: `admin` / `<your GRAFANA_PASSWORD>`
3. Navigate to Dashboards

### Key Dashboards
- **Trading Overview** - Real-time P&L, positions, trades
- **Risk Metrics** - Drawdown, risk limits, circuit breakers
- **System Health** - Container status, resource usage
- **AI Strategy** - ML optimization, regime detection, patterns

### Query Database Directly
```bash
# Open PostgreSQL shell
docker exec -it nautilus_postgres psql -U nautilus -d nautilus_trader

# Example queries:
SELECT * FROM backtests ORDER BY created_at DESC LIMIT 10;
SELECT * FROM v_strategy_health;
SELECT * FROM v_top_strategies;
```

---

## 🔧 Maintenance

### Daily Backup
```bash
# Backup database
docker exec nautilus_postgres pg_dump -U nautilus nautilus_trader | gzip > \
    backups/nautilus_trader_$(date +%Y%m%d).sql.gz

# Restore from backup
gunzip < backups/nautilus_trader_20250115.sql.gz | \
    docker exec -i nautilus_postgres psql -U nautilus -d nautilus_trader
```

### Clean Up Docker Resources
```bash
# Remove unused images/volumes
docker system prune -f

# View disk usage
docker system df
```

### Update Services
```bash
cd infrastructure/docker

# Pull latest images
docker-compose pull

# Restart with new images
docker-compose down
docker-compose up -d
```

### Database Optimization
```bash
# Vacuum and analyze
docker exec -it nautilus_postgres psql -U nautilus -d nautilus_trader -c "
VACUUM ANALYZE;
REINDEX DATABASE nautilus_trader;
"
```

---

## 🐛 Troubleshooting

### Container Won't Start
```bash
# Check logs
docker-compose logs [service_name]

# Common fixes:
docker-compose down
docker-compose up -d
```

### Can't Connect to PostgreSQL
```bash
# Test connection
docker exec -it nautilus_postgres pg_isready -U nautilus

# Verify password
grep DB_PASSWORD .env.local

# Restart
docker-compose restart postgres
```

### High Memory Usage
```bash
# Check usage
docker stats

# Restart services
docker-compose restart

# Adjust limits in docker-compose.yml (deploy.resources section)
```

### Port Already in Use
```bash
# Find process using port
sudo lsof -i :5432

# Kill process or change port in docker-compose.yml
```

---

## 📈 Performance Tuning

### PostgreSQL
- **Small systems (< 4GB RAM):** `shared_buffers=512MB`
- **Medium systems (8GB RAM):** `shared_buffers=2GB` (current)
- **Large systems (16GB+ RAM):** `shared_buffers=4GB`

Edit: `postgres/postgresql.conf`

### Redis
- **Memory limit:** Currently 512MB
- **Eviction policy:** `allkeys-lru`
- **Persistence:** AOF + RDB enabled

Edit: `docker-compose.yml` (redis section)

### Resource Limits
Adjust in `docker-compose.yml`:
```yaml
deploy:
  resources:
    limits:
      cpus: '2.0'
      memory: 2G
```

---

## 📞 Support

### Documentation
- **Operations Guide:** [OPERATIONS_GUIDE.md](OPERATIONS_GUIDE.md)
- **Implementation Plan:** [plan.md](../ai-working/database_Infra layer/plan.md)
- **Nautilus Docs:** https://nautilustrader.io/docs/

### Community
- **Discord:** https://discord.gg/nautilustrader
- **GitHub Issues:** https://github.com/nautechsystems/nautilus_trader/issues

### Logs
- **Application:** `logs/` directory
- **Docker:** `docker-compose logs -f`
- **PostgreSQL:** Inside container at `/var/lib/postgresql/data/log/`

---

## 📝 Next Steps

1. ✅ **Setup complete?** → Read [OPERATIONS_GUIDE.md](OPERATIONS_GUIDE.md)
2. ✅ **Guide read?** → Run your first backtest
3. ✅ **Backtest successful?** → Start paper trading
4. ✅ **Paper trading stable?** → Consider live trading (with caution!)

---

## ⚠️ Important Notes

- **Never commit `.env.local`** to git (contains secrets)
- **Start small** when going live (test with minimum capital)
- **Use paper trading first** (minimum 2 weeks)
- **Keep backups** (daily database exports)
- **Monitor constantly** (especially first week of live trading)
- **Have a kill switch** (emergency stop procedure)

---

**Built with:** Docker, PostgreSQL, Redis, Prometheus, Grafana  
**Maintained by:** Nautilus Trader Contributors  
**License:** LGPL v3.0

**Last Updated:** January 2025  
**Version:** 1.0
