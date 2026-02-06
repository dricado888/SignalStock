# SignalStock - Real-Time Stock Event Detection Platform

## Project Overview
MVP real-time stock market event detection system. Scrapes financial news, classifies events with AI, maps them to affected stocks, and sends email alerts.

## Architecture
- **5 microservices**: scraper, classifier, stock-mapper, alert-engine, api
- **Tech stack**: Python (FastAPI/Flask), React, PostgreSQL, Redis, Docker
- **AI**: Gemini 2.5 Flash-Lite for event classification
- **Deployment**: AWS ECS (future), local Docker for MVP

## Key Constraints
- Free-tier APIs only (MVP budget: $0)
- Gemini Flash-Lite: 1,000 requests/day limit
- Scraper runs every 5 minutes via cron
- Target: Handle 10-30 articles per scrape cycle

## News Sources
- finlight.me: 10K requests/month (primary financial news)
- NewsAPI: 100 requests/day (breaking news backup)

## Event Types Detected
- earnings_report
- merger_acquisition
- product_launch
- regulatory_action
- executive_change
- lawsuit
- partnership
- other

## Development Strategy
Multi-agent parallel build using git worktrees. Each service built independently by Claude Code subagents, then merged into main.

## Current Phase
Phase 0 complete. Ready for Phase 1: Database Schema.
EOF