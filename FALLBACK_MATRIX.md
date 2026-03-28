# PPS Anantam — Fallback Matrix

## 7 Data Categories — Primary / Secondary / Tertiary / Emergency

All sources are **FREE**. No paid services required for 24/7 operation.

---

### 1. Foreign Exchange Rates

| Level | Source | Auth | TTL | Confidence |
|-------|--------|------|-----|------------|
| **Primary** | fawazahmed0 CDN | None (free) | 1 hour | 95% |
| **Secondary** | Frankfurter ECB Proxy | None (free) | 2 hours | 85% |
| **Tertiary** | Last-Known-Good Cache | Local | 24 hours | 60% |
| **Emergency** | Static Q1 2026 (86.80 INR/USD) | Local | Infinite | 30% |

### 2. Crude Oil Prices

| Level | Source | Auth | TTL | Confidence |
|-------|--------|------|-----|------------|
| **Primary** | Yahoo Finance (BZ=F, CL=F) | None (free) | 15 min | 95% |
| **Secondary** | EIA API | API Key (free) | 1 hour | 90% |
| **Tertiary** | Last-Known-Good Cache | Local | 24 hours | 55% |
| **Emergency** | Static Q1 2026 (Brent $75.50) | Local | Infinite | 25% |

### 3. Weather Data

| Level | Source | Auth | TTL | Confidence |
|-------|--------|------|-----|------------|
| **Primary** | Open-Meteo (5 port cities) | None (free) | 1 hour | 90% |
| **Secondary** | OpenWeather | API Key (free) | 1 hour | 88% |
| **Tertiary** | Last-Known-Good Cache | Local | 12 hours | 50% |
| **Emergency** | Seasonal Average (Mar: 28-38C) | Local | Infinite | 25% |

### 4. News & Events

| Level | Source | Auth | TTL | Confidence |
|-------|--------|------|-----|------------|
| **Primary** | 12-Source RSS Aggregator | None (free) | 10 min | 85% |
| **Secondary** | Google News RSS | None (free) | 30 min | 75% |
| **Tertiary** | Last-Known-Good Cache | Local | 24 hours | 45% |
| **Emergency** | Last 24h Cached Articles | Local | 24 hours | 30% |

### 5. Government & Infrastructure Data

| Level | Source | Auth | TTL | Confidence |
|-------|--------|------|-----|------------|
| **Primary** | data.gov.in NHAI API | API Key (free) | 24 hours | 90% |
| **Secondary** | PIB Infrastructure RSS | None (free) | 24 hours | 70% |
| **Tertiary** | Static FY24 NHAI Reference | Local | Infinite | 45% |
| **Emergency** | Manual Override (Settings) | Local | Infinite | 20% |

### 6. Trade & Import Data

| Level | Source | Auth | TTL | Confidence |
|-------|--------|------|-----|------------|
| **Primary** | UN Comtrade HS 271320 | None (free) | 24 hours | 90% |
| **Secondary** | World Bank India API | None (free) | 24 hours | 70% |
| **Tertiary** | Static Trade Data (2023) | Local | Infinite | 40% |
| **Emergency** | Manual Override (Settings) | Local | Infinite | 20% |

### 7. System Clock

| Level | Source | Auth | TTL | Confidence |
|-------|--------|------|-----|------------|
| **Primary** | TimeAPI.io | None (free) | 1 min | 99% |
| **Secondary** | WorldTimeAPI | None (free) | 1 min | 95% |
| **Tertiary** | Python datetime (IST) | Local | Real-time | 90% |
| **Emergency** | OS System Clock | Local | Real-time | 85% |

---

## Self-Healing Rules

| Rule | Threshold | Action |
|------|-----------|--------|
| API Retry | 3 attempts | Backoff: [2s, 8s, 20s] |
| Circuit Breaker Open | 3-5 consecutive failures | Block calls, recover after 30-120s |
| Stale Data Warning | > 2 hours | Yellow traffic light |
| Stale Data Critical | > 6 hours | Red traffic light, switch to LKG |
| Dead Thread | No heartbeat for interval x 2.5 | Auto-restart (max 3/hr) |
| DLQ Retry | Failed job | Retry at 5m, 30m, 2h |
| P1 Escalation | Open > 24 hours | Auto-escalate to P0 |

## Confidence Badge System

| Badge | Range | Meaning |
|-------|-------|---------|
| 🟢 Green | >= 80% | Verified — fresh primary data |
| 🟡 Yellow | 60-79% | Estimated — secondary/cached data |
| 🔴 Red | 40-59% | Stale — tertiary/degraded data |
| 🔵 Blue | < 40% | Unavailable — emergency/offline |
