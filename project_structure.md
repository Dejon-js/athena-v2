# Project ATHENA v2.2 - Directory Structure

```
athena-v2/
├── backend/
│   ├── modules/
│   │   ├── m1_data_core/
│   │   │   ├── __init__.py
│   │   │   ├── data_ingestion.py
│   │   │   ├── data_validation.py
│   │   │   └── schedulers.py
│   │   ├── m2_simulation/
│   │   │   ├── __init__.py
│   │   │   ├── player_projections.py
│   │   │   ├── monte_carlo.py
│   │   │   └── distributions.py
│   │   ├── m3_game_theory/
│   │   │   ├── __init__.py
│   │   │   ├── ownership_prediction.py
│   │   │   └── sentiment_analysis.py
│   │   ├── m4_optimizer/
│   │   │   ├── __init__.py
│   │   │   ├── linear_programming.py
│   │   │   ├── constraints.py
│   │   │   └── objective_function.py
│   │   ├── m5_live_ops/
│   │   │   ├── __init__.py
│   │   │   ├── live_data.py
│   │   │   └── suggestions.py
│   │   ├── m6_learning/
│   │   │   ├── __init__.py
│   │   │   ├── feedback_loop.py
│   │   │   └── model_retraining.py
│   │   └── m7_adaptive/
│   │       ├── __init__.py
│   │       └── early_season.py
│   ├── shared/
│   │   ├── __init__.py
│   │   ├── database.py
│   │   ├── config.py
│   │   └── utils.py
│   ├── api/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── routes/
│   │   └── websockets.py
│   ├── requirements.txt
│   └── docker-compose.yml
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── services/
│   │   └── utils/
│   ├── public/
│   ├── package.json
│   └── README.md
├── data/
│   ├── raw/
│   ├── processed/
│   └── models/
├── scripts/
│   ├── setup.py
│   └── deploy.py
├── tests/
│   ├── backend/
│   └── frontend/
├── docs/
│   ├── api.md
│   └── deployment.md
├── .env.example
├── .gitignore
├── docker-compose.yml
└── README.md
```
