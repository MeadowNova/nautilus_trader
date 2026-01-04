# Implementation Guide: Model Training — Nautilus Trader

## Overview
- **Last Updated:** 2025-10-07
- **Current Phase:** Phase 2 — Production Artefact Generation
- **Objective:** Produce refreshed HMM, LSTM, and XGBoost models from the full historical parquet dataset; capture metrics and persist artefacts for strategy integration.

---

## Session Notes (2025-10-07)

### Data & Environment
- Activated venv via `source activate_env.sh` (Python 3.13, TensorFlow CPU build).
- Input data: `data/nautilus/BTC-USDT-1-MINUTE.parquet`, `ETH-USDT-1-MINUTE.parquet` (~160 MB combined, ~2.26 M rows).
- Output directory: `ajk_strategies/models/` (created automatically during runs).

### Training Commands & Results
1. **Market Regime HMM**  
   ```bash
   python ajk_strategies/training/train_regime_hmm.py \
     --input-path data/nautilus \
     --output-path ajk_strategies/models/market_regime_hmm.pkl
   ```
   - Duration: ~1.5 minutes.  
   - Rows consumed: 2,262,971.  
   - State counts: `[57,896, 1,011,601, 1, 1,193,472, 1]`.  
   - Artefact bundles `(model, scaler, summary)` via joblib.

2. **Price Forecast LSTM**  
   ```bash
   python ajk_strategies/training/train_forecast_lstm.py \
     --input-path data/nautilus
   ```
   - Duration: ~19 minutes (CPU).  
   - Early stop at epoch 5 (best val_loss ≈ 0.83754).  
   - Artefacts: `price_forecast_lstm.h5`, `price_forecast_lstm_meta.pkl` (input scaler, target scaler, sequence length).

3. **Signal Aggregator XGBoost**  
   ```bash
   python ajk_strategies/training/train_signal_xgb.py \
     --input-path data/nautilus
   ```
   - Duration: ~2 minutes after vectorized LSTM forecasts.  
   - Class distribution: `[629,103 (hold), 819,741 (long), 814,091 (short)]`.  
   - Artefact: `signal_aggregator_xgb.pkl` with model, scaler, config metadata.

### Strategy Integration
- Updated `AIAdaptiveStrategyConfig` to expose model paths/thresholds so the live strategy can load refreshed artefacts.
- `AIAdaptiveStrategy` now loads HMM/LSTM/XGB on `on_start`, maintains streaming features (DSP trend, rolling volatility, scaled returns), and uses HMM regimes + XGB probabilities for entry decisions (logistic regression kept as fallback).
- Sanity backtest (`python ajk_strategies/run_backtest_with_real_data.py --max-bars 5000`) confirms runtime logs from HMM regime updates and Model-driven entries; run completed within ~10 minutes on CPU (initial attempt hit timeout but continued successfully on second run).

### Code Improvements
- `features.load_price_frame`: detects `ts_event`/`time` columns and renames to `timestamp` before processing.
- `train_signal_xgb.compute_lstm_forecasts`: switched to `numpy.sliding_window_view` + batched predictions (`batch_size=2048`), drastically reducing runtime.
- `ai_adaptive_strategy_main.AIAdaptiveStrategy`: HMM regime inference, LSTM forecasts, and XGB probability gating integrated with existing risk/sentiment pipeline.

### Verification
- `python -m compileall ajk_strategies/training/features.py ajk_strategies/training/train_signal_xgb.py ajk_strategies/ai_adaptive_strategy_main.py` (syntax/bytecode check).  
- Manual inspection of `ajk_strategies/models/` confirms artefacts present; backtest smoke test exercises full pipeline.

---

## Artefact Inventory
| File | Purpose | Notes |
|------|---------|-------|
| `market_regime_hmm.pkl` | GaussianHMM + StandardScaler + summary dict | State mapping persisted | 
| `price_forecast_lstm.h5` | Keras Sequential model | Validation MSE 0.83754 | 
| `price_forecast_lstm_meta.pkl` | Input/target scalers, sequence length, train split | Required for inference pipeline |
| `signal_aggregator_xgb.pkl` | XGBClassifier, StandardScaler, config | Depends on HMM + LSTM outputs |

---

## Outstanding Follow-ups
- Wire artefacts into `ai_adaptive_strategy_main.py` and verify inference path.  
- Record artefact hashes and training metrics in `INFRASTRUCTURE_STATUS.md`.  
- Execute verification backtests (BTC/ETH) using refreshed models.  
- Plan automated retraining schedule + retention policy.

---

## Next Actions
1. Update strategy configuration to load new models + scalers.  
2. Run end-to-end backtest to validate signal quality post-refresh.  
3. Document results + metrics in the new dashboard enhancement folder.  
4. Decide on cadence (monthly) and create scripts for scheduled retraining.
