# Project ATHENA v2.2 - NFL DFS Optimizer

## Overview
ATHENA is an autonomous agent for winning large-field NFL Daily Fantasy Sports (DFS) GPP tournaments. The system treats lineup construction as a constrained optimization problem, focusing on maximizing leveraged ceiling potential.

## Architecture
- **Backend**: 7 modules operating in sequential workflow
- **Frontend**: React-based dashboard with conversational AI interface
- **Database**: PostgreSQL for persistent storage, Neo4j for GraphRAG
- **Orchestration**: Apache Airflow for data pipelines

## Modules
1. **Data Core (M1)**: Aggregates all raw data sources
2. **Simulation & Projection Engine (M2)**: Player-level Monte Carlo simulations
3. **Game Theory & Ownership Engine (M3)**: Predicts opponent decisions
4. **The Optimizer Engine (M4)**: Core optimization using linear programming
5. **Live Operations & Suggestion Engine (M5)**: Real-time adjustments
6. **Learning & Feedback Loop (M6)**: Continuous improvement
7. **Early-Season Adaptive Logic (M7)**: Low-data mode for weeks 1-3

## Goals
- Achieve top 0.5% finish in 100k+ entry NFL GPP
- Maintain positive ROI across 18-week season
- >95% success rate for user strategy queries

## Development Timeline
- **Phase 1**: Backend MVP (Now - Sep 12, 2025)
- **Phase 2**: Frontend & Integration (Now - Sep 26, 2025)
- **Phase 3**: Advanced Features (Oct 2025)
- **Phase 4**: Operation & Maintenance (Nov 2025 - Feb 2026)
