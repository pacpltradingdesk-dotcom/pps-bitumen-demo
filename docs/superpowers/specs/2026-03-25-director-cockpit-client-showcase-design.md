# Director Cockpit + Client Showcase — Design Spec

**Date**: 2026-03-25
**Author**: Claude + Rahul
**Status**: Approved

## Problem

65 pages mein confusion — kaunsa feature kidhar hai, kya kholna hai. Director (Prince Shah) ko subah ek guided flow chahiye jo market se lekar quote send tak le jaaye. Clients ko ek clean showcase chahiye.

## Solution: Two New Pages

### Page 1: Director Cockpit (4-Step Wizard)

**File**: `pages/home/director_cockpit.py`
**Nav**: Home module, first item, starred
**User**: Prince Shah (owner/director)

#### Step 1 — Market Snapshot
- Brent, WTI, USD/INR, VG30 live prices (hub_cache.json + live_prices.json)
- AI Signal badge (BUY/SELL/HOLD + score from market_intelligence_engine)
- Top 3 alerts (from alert engine)
- [Next →] button

#### Step 2 — Today's Targets
- Hot leads from crm_engine (overdue + due today)
- Each lead card: Name, City, Days since contact, Opportunity type
- Action buttons: [Call Script] [WhatsApp] [Skip]
- Click lead → auto-fills Step 3 customer
- [← Back] [Next →]

#### Step 3 — Instant Price Calculator
- Customer dropdown (pre-filled from Step 2 if applicable)
- City (auto-detect), Grade (VG30/VG10), Quantity (MT)
- [Calculate] → Top 3 sources ranked by landed cost
- 3-tier offer display: Aggressive / Balanced / Premium
- Select tier → [Next →]

#### Step 4 — Send Quote
- Summary card: Customer, City, Grade, Qty, Price/MT, Source
- Send buttons: [📱 WhatsApp] [📧 Email] [📄 PDF]
- On send: auto-log CRM activity, create Day-3 follow-up task
- Success message
- [🔄 New Quote] to restart

#### Data Sources (no new engines)
- hub_cache.json, live_prices.json (market data)
- market_intelligence_engine.MarketIntelligenceEngine (AI signal)
- crm_engine.get_tasks() (leads)
- calculation_engine.get_engine() (pricing)
- communication_engine.CommunicationHub (message templates)
- database.log_communication() (CRM logging)

### Page 2: Client Showcase (Digital Visiting Card)

**File**: `pages/home/client_showcase.py`
**Nav**: Home module, after Director Cockpit
**User**: External clients/customers

#### Sections (single scroll, no sidebar needed)
1. **Hero**: Logo, "PPS Anantams Corporation Pvt Ltd", "24 Years in Bitumen Trading", Vadodara
2. **Products**: VG30, VG10, VG40, CRMB-55, CRMB-60, PMB — card grid with descriptions
3. **Today's Rates**: Indicative price table from live_prices.json (Grade, Bulk Rate, Drum Rate)
4. **Why PPS**: 24 years, 24,000+ contacts, Pan-India, 8 import terminals, PSU + Import sources
5. **Contact**: Click-to-call, WhatsApp (wa.me link), Email (mailto), Full address
6. **Footer**: GST, PAN, CIN, Bank details, Terms

#### Data Sources
- company_config.COMPANY_PROFILE (company details)
- live_prices.json (current rates)
- business_context.PRODUCTS (product catalog)

## What Doesn't Change
- Existing 65 pages untouched
- No engine modifications
- Nav structure stays — just 2 new entries in MODULE_NAV Home section
