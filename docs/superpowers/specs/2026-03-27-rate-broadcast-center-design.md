# Rate Broadcast Center — Design Spec

**Date:** 2026-03-27
**Author:** Claude + Rahul
**Status:** Approved
**Scope:** Daily personalized rate broadcasting via WhatsApp + Email with auto-triggers

---

## Goal

Build a Rate Broadcast Center that sends personalized bitumen rates to customers daily (9 AM auto), on IOCL/HPCL price revisions (instant), and on manual trigger — via WhatsApp + Email simultaneously. Each customer receives their city-specific landed cost for their preferred grade, prioritized by VIP tier.

---

## New Files

| File | Purpose | Est. Lines |
|------|---------|-----------|
| `rate_broadcast_engine.py` | Segmentation, personalization, send logic, auto-trigger, scheduling | ~350 |
| `command_intel/rate_broadcast_dashboard.py` | Streamlit UI — preview, send, schedule, history | ~400 |

## Modified Files

| File | Change |
|------|--------|
| `nav_config.py` | Add "Rate Broadcast" to Sales & CRM module |
| `dashboard.py` | Add PAGE_DISPATCH entry |
| `competitor_intelligence.py` | Hook `on_price_revision()` callback after `record_revision()` |

---

## Segmentation Logic

Contacts are filtered and prioritized:

1. **VIP Tier** — Platinum first (immediate), Gold (1 min delay), Silver (2 min), Standard (3 min)
2. **City** — Calculate landed cost per customer's city using `calculation_engine`
3. **Grade** — Send rates for customer's preferred grade (VG30/VG10/VG40/CRMB/PMB), default VG30
4. **Channel** — WhatsApp if opted-in + has phone, Email if has email, both if both available
5. **Opt-out** — Skip contacts who opted out of broadcasts

Contact data sourced from:
- `tbl_contacts.json` (66 records currently)
- SQLite `customers` table (via `database.py`)
- SQLite `contacts` table (via CRM engine)

---

## Three Trigger Modes

| Mode | Trigger | Behavior |
|------|---------|----------|
| **Auto Morning** | Background scheduler at 9:00 AM IST | Sends to ALL eligible contacts with today's rates |
| **Price Revision** | `competitor_intelligence.record_revision()` called | Sends ONLY to contacts in affected region with old vs new price comparison |
| **Manual** | User clicks "Broadcast Now" in dashboard | Sends to selected segment with current rates |

---

## Message Formats

### WhatsApp Message (per customer)

```
🔵 PPS Anantams — Rate Update
━━━━━━━━━━━━━━━━━━━
📅 {date}

Dear {customer_name},

Your rates for {city}:
{grade} Bulk: ₹{bulk_landed_cost}/MT
{grade} Drum: ₹{drum_landed_cost}/MT

Savings vs market: ₹{saving}/MT
━━━━━━━━━━━━━━━━━━━
100% Advance | 24hr Validity
Ex-Terminal | GST 18% Extra

📞 +91 7795242424
PPS Anantams Corporation Pvt Ltd
```

### Email (per customer)

HTML formatted email with:
- Company header with logo reference
- Rate table (grade, bulk price, drum price, landed cost)
- City-specific details
- "Request Quote" CTA button (wa.me link)
- Footer with GST, terms, contact

### Price Revision Alert (special format)

```
⚡ PRICE REVISION ALERT
━━━━━━━━━━━━━━━━━━━
{competitor} has revised {grade} prices!

Old: ₹{old_price}/MT
New: ₹{new_price}/MT
Change: {direction} ₹{change}/MT

Our rate for {city}: ₹{our_price}/MT
Your saving: ₹{saving}/MT vs {competitor}
━━━━━━━━━━━━━━━━━━━
Act now — 24hr validity
📞 +91 7795242424
```

---

## rate_broadcast_engine.py — Functions

| Function | Purpose |
|----------|---------|
| `get_broadcast_contacts(filters)` | Load and filter contacts by city/grade/VIP/opt-in |
| `calculate_personalized_rate(customer)` | Get landed cost for customer's city + grade via calculation_engine |
| `generate_wa_message(customer, rates, trigger_type)` | Format WhatsApp message per customer |
| `generate_email_html(customer, rates, trigger_type)` | Format HTML email per customer |
| `generate_revision_alert(customer, revision_data)` | Special format for price revision alerts |
| `execute_broadcast(filters, trigger_type)` | Main send function — segment → personalize → queue WA + Email |
| `schedule_morning_broadcast()` | Background thread that fires at 9 AM IST daily |
| `on_price_revision(revision_data)` | Callback for competitor price changes |
| `get_broadcast_history(limit)` | Query broadcast_log table |
| `get_broadcast_stats(broadcast_id)` | Delivery stats for specific broadcast |
| `_stagger_by_vip(contacts)` | Sort by VIP tier with time gaps |
| `_queue_whatsapp(phone, message)` | Queue via whatsapp_engine |
| `_queue_email(email, subject, html)` | Queue via email_engine |
| `ensure_table()` | Create broadcast_log table |

---

## rate_broadcast_dashboard.py — UI

### Tab 1: 📡 Broadcast Now

- **Segment Filters**: City multiselect, Grade multiselect, VIP tier multiselect
- **Preview Count**: "245 customers will receive this broadcast"
- **Channel Preview**: "WhatsApp: 198, Email: 230, Both: 183"
- **Message Preview**: Show sample message for first customer
- **Send Button**: "Broadcast Now" (primary) with confirmation
- **Progress**: st.progress bar during send

### Tab 2: ⏰ Schedule

- **Auto Morning Toggle**: Enable/disable 9 AM daily broadcast
- **Time Picker**: Change broadcast time (default 9:00 AM)
- **Price Revision Toggle**: Enable/disable auto-broadcast on IOCL/HPCL revision
- **Segment for Auto**: Which segments get auto-broadcasts (default: all)
- **Status**: "Next broadcast: Tomorrow 9:00 AM | Last: Today 9:00 AM (sent 1,245)"

### Tab 3: 📊 History

- **Broadcast Log Table**: Date, trigger type, recipients, WA sent/delivered, Email sent/delivered, status
- **Filter**: By date range, trigger type
- **Click to expand**: See segment details, failed contacts

### Tab 4: ⚙️ Settings

- **Rate Limits**: WA per minute (default 20), Email per hour (default 50)
- **VIP Stagger**: Minutes between tiers (default 1/2/3)
- **Message Template Editor**: Edit WhatsApp and Email templates
- **Opt-out List**: View/manage opted-out contacts
- **Test Mode**: Send to self only (for testing)

---

## New DB Table

```sql
CREATE TABLE IF NOT EXISTS broadcast_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    broadcast_id TEXT UNIQUE,
    trigger_type TEXT,
    segment_filter TEXT,
    total_recipients INTEGER DEFAULT 0,
    wa_sent INTEGER DEFAULT 0,
    wa_delivered INTEGER DEFAULT 0,
    wa_failed INTEGER DEFAULT 0,
    email_sent INTEGER DEFAULT 0,
    email_delivered INTEGER DEFAULT 0,
    email_failed INTEGER DEFAULT 0,
    message_template TEXT,
    created_at TEXT,
    completed_at TEXT,
    status TEXT DEFAULT 'pending'
);
```

---

## Rate Limit Safety

- WhatsApp: 20/min, 1000/day (360dialog API limit)
- Email: 50/hr (SMTP limit)
- VIP stagger: Platinum → immediate, Gold → +1 min, Silver → +2 min, Standard → +3 min
- If daily limit reached, remaining queued for next day
- Failed messages retry up to 3 times with 15-min delay

---

## Integration Points

1. **calculation_engine.py** — `get_engine().find_best_sources(city, grade)` for landed cost
2. **whatsapp_engine.py** — `queue_message()` for WhatsApp sends
3. **email_engine.py** — `queue_email()` for Email sends
4. **competitor_intelligence.py** — `record_revision()` triggers `on_price_revision()`
5. **crm_engine.py** — VIP tier data for staggering
6. **live_prices.json** — Current market rates
7. **database.py** — Contact data, broadcast logging

---

## Dependencies

- No new Python packages needed
- Uses existing WhatsApp (360dialog) and Email (SMTP/SendGrid/Brevo) infrastructure
- Uses existing calculation_engine for city-wise pricing
- Uses existing VIP scoring from crm_engine
