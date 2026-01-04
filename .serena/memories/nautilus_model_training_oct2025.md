## 2025-10-07 Model Training Refresh
- Re-trained all production models on `data/nautilus` parquet set (~2.26M minute bars).
- Artefacts saved in `ajk_strategies/models/`: `market_regime_hmm.pkl`, `price_forecast_lstm.h5`, `price_forecast_lstm_meta.pkl`, `signal_aggregator_xgb.pkl`.
- HMM: state counts `[57896, 1011601, 1, 1193472, 1]` with scaler + mapping stored.
- LSTM: early stop at epoch 5; validation MSE ≈ 0.83754.
- XGBoost: class distribution (hold/long/short) `[629103, 819741, 814091]`; LSTM forecast generation vectorized for speed.
