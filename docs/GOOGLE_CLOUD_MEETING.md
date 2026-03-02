# Meeting Agenda: Google Cloud Free Trial ($300 Credits)

**Date:** _____________
**Attendees:** Section Managers
**Prepared by:** Project Aegis Team
**Duration:** 30 minutes

---

## 1. Overview (5 min)

Google Cloud offers **$300 in free credits** for new accounts, valid for **90 days**.
No credit card charge until credits run out AND you manually upgrade.

**Goal:** Use these credits to test cloud deployment, real-time data pipelines, and AI features for Project Aegis before committing to paid infrastructure.

---

## 2. Proposed Use Cases & Estimated Costs

### Priority A: Core Infrastructure (Est. $40-60/month)

| Service | Use Case | Est. Monthly Cost |
|---------|----------|-------------------|
| **Compute Engine (e2-small)** | Host Streamlit dashboard 24/7 | $15-20 |
| **Cloud Scheduler + Cloud Functions** | Run `aegis_brain.py` every 30 min (autonomous scan loop) | $2-5 |
| **Cloud Storage (5 GB)** | News cache, chart exports, reports | $0.50 |
| **Cloud SQL (db-f1-micro) or Firestore** | Replace JSON files with real database | $10-15 |
| **Artifact Registry** | Store Docker image for deployment | $1-2 |

**Subtotal: ~$30-45/month = ~$90-135 for 90 days**

### Priority B: Intelligence & AI (Est. $20-40/month)

| Service | Use Case | Est. Monthly Cost |
|---------|----------|-------------------|
| **Vertex AI / Gemini API** | LLM-powered causal analysis, natural language trade commands, auto-research | $15-30 |
| **BigQuery** | Historical analytics at scale (predictions, trades, lessons) | $5-10 |
| **Pub/Sub** | Real-time alert pipeline (instant Telegram/Discord notifications) | $2-5 |

**Subtotal: ~$20-40/month = ~$60-120 for 90 days**

### Priority C: Scale Testing (Est. $10-20 one-time)

| Service | Use Case | Est. Cost |
|---------|----------|-----------|
| **Load Testing (multiple instances)** | Simulate multi-user access before launch | $10-15 |
| **Cloud Monitoring + Logging** | Track uptime, errors, performance metrics | Free tier |
| **Cloud CDN** | Test landing page delivery speed globally | $5 |

**Subtotal: ~$15-20 one-time**

---

## 3. Total Estimated Spend

| Scenario | 90-Day Cost | Remaining Credits |
|----------|-------------|-------------------|
| **Conservative** (Priority A only) | ~$100 | ~$200 left |
| **Moderate** (A + B) | ~$200 | ~$100 left |
| **Full Test** (A + B + C) | ~$250 | ~$50 left |

**Recommendation:** Start with **Moderate** plan. We get full cloud deployment + AI testing and still have $100 buffer.

---

## 4. What We Learn From This Test

1. **Deployment readiness** — Can we reliably run Aegis 24/7 in the cloud?
2. **Database migration** — Is it worth moving from JSON to Cloud SQL/Firestore?
3. **AI value** — Does Gemini/Vertex add enough value vs. our rules-based engine?
4. **Real-time feasibility** — Can Pub/Sub + Cloud Functions deliver sub-minute alerts?
5. **Cost baseline** — What will production actually cost per month?
6. **Multi-user performance** — How does the dashboard handle 10+ concurrent users?

---

## 5. Action Items

| # | Action | Owner | Deadline |
|---|--------|-------|----------|
| 1 | Create Google Cloud account with free trial | __________ | __________ |
| 2 | Dockerize Aegis (Dockerfile already exists) | Dev Team | __________ |
| 3 | Deploy Streamlit to Compute Engine | Dev Team | __________ |
| 4 | Set up Cloud Scheduler for brain loop | Dev Team | __________ |
| 5 | Test Vertex AI / Gemini for causal analysis | AI Team | __________ |
| 6 | Set up monitoring & cost alerts ($50, $100, $200) | __________ | __________ |
| 7 | Report results after 30 days | All | __________ |

---

## 6. Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Credits expire before testing complete | Set up in Week 1, run tests immediately |
| Accidental overcharge | Set billing alerts at $50/$100/$200, disable auto-upgrade |
| Vendor lock-in | Use Docker + standard APIs, keep local JSON as fallback |
| Data security | No real money involved (paper trading only), use IAM best practices |

---

## 7. Decision Needed

- [ ] **Approve** Google Cloud free trial activation
- [ ] **Assign** account owner / billing admin
- [ ] **Select** scenario: Conservative / Moderate / Full Test
- [ ] **Set** start date and 30-day review checkpoint

---

*Project Aegis — Autonomous Trading Intelligence Platform*
*$0 risk, $300 in free cloud compute to validate our architecture.*
