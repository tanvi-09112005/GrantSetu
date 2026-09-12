# GrantSetu — foreign funding & FCRA source inventory

**Reconnaissance date: 7 September 2026.** Companion to `docs/data-sources.md`
(domestic government + CSR). Same tiering rules. Everything below was checked
live unless explicitly marked as a lead.

---

## 0. Read this first: FCRA is a hard gate, not a filter

For domestic grants, eligibility is a ranking signal. For foreign contribution it
is **binary admission**: an Indian NGO without valid FCRA registration (or
scheme-specific prior permission) **cannot lawfully receive foreign money at
all.** Showing an NGO a foreign opportunity it cannot legally accept is worse
than showing it nothing.

Verified requirements:

| Requirement | Detail |
|---|---|
| Registration validity | **5 years** from date of grant |
| Renewal | **Form FC-3C**, filed **at least 6 months before** expiry |
| Bank account | An **"FCRA Account" at State Bank of India, Main Branch, New Delhi** — mandatory, named in the renewal application |
| Darpan ID | Required before renewal |
| Annual return | **Form FC-4**, due **31 December** (9 months after FY close). A **NIL return is mandatory** even with zero receipts |
| Prior returns | All previous ARs must be filed before renewal is granted |

Two properties that matter for the data model:

1. **FCRA status is time-bounded and revocable.** Registrations are cancelled in
   bulk — **5,789 entities** lost their licence in one round (including IIT
   Delhi, Jamia Millia Islamia and the Indian Medical Association); **1,827** were
   cancelled between 2018 and 2022.
2. **MHA repeatedly issues blanket validity extensions** by notification, so an
   expiry date printed on a certificate is not authoritative on its own.

### Schema consequence

`ngo_profiles.reg_fcra text` is **not sufficient**. A registration number alone
cannot answer "may this NGO accept foreign money today?". Migration `0003`
adds `fcra_valid_until`, `fcra_status` and `fcra_verified_on`. The eligibility
engine must treat foreign opportunities as:

```
eligible_for_foreign = reg_fcra is not null
                       and fcra_status = 'active'
                       and (fcra_valid_until is null or fcra_valid_until >= today)
```

...and must say *"your FCRA lapsed on <date>"* rather than silently dropping the
grant from the list.

---

## Tier 1 — verified working, keyless, build against these

### 1.1 grants.gov (US federal) — ★ tested live, works

**No API key. No authentication.** Confirmed by live call on 7 Sep 2026.

```
POST https://api.grants.gov/v1/api/search2
POST https://api.grants.gov/v1/api/fetchOpportunity
```

Live result for `{"keyword":"India","rows":3,"oppStatuses":"posted"}` — 6 open
opportunities, including:

- `CDC-RFA-JG-26-0051` — "Strengthening global health security in India to
  contain public health threats and accelerate outbreak response"
  (CDC-GHC, opens 03 Aug 2026, **closes 02 Oct 2026**)
- `CDC-RFA-JG-26-0142` — "Ending HIV and TB as public health threats through an
  accelerated and sustained comprehensive response in India"
  (CDC-GHC, opens 17 Aug 2026, **closes 16 Sep 2026**)

`fetchOpportunity` returns `opportunityTitle`, `agencyName`, `responseDate`,
`awardCeiling`, and a structured `applicantTypes` list which includes
*"Unrestricted (i.e., open to any type of entity above)"*.

**Caveat that must be enforced in code:** `applicantTypes` is US-centric (501(c)(3)
status, tribal governments, school districts). **Do not infer Indian NGO
eligibility from it.** Some CDC/NIH global-health calls are open to foreign
entities, some require a US prime with an Indian sub-recipient. Parse
`applicantEligibilityDesc` and surface it verbatim for human judgement — never
let the rules engine assert "you are eligible" for a US federal opportunity.

This is the single best foreign source: real deadlines, real award ceilings,
clean JSON, no key, no scraping.

### 1.2 d-portal.org — IATI open aid data — ★ tested live, works

**No API key.** Confirmed live.

```
GET https://d-portal.org/q.json?from=act&country_code=IN&limit=3
```

Returned real IATI activity identifiers for India (e.g. `US-GOV-1-D3B17F571B83`).
Covers every donor publishing to the International Aid Transparency Initiative —
bilateral donors, UN agencies, large foundations.

**Note:** my `select=` column list was partly ignored; the response came back
with only `aid` and `day_end`. The correct column names for
`title_narrative` / `reporting_org_narrative` / commitment values need to be
read off d-portal's `dquery` documentation before building. The endpoint itself
is confirmed working — only the field list is unresolved.

Best use: **funder prospecting** ("who has funded health projects in Bihar, at
what scale, and are they still active"), not deadline discovery. IATI records
committed and disbursed activity, not open calls.

---

## Tier 2 — works, but needs a key or registration

| Source | Status | Notes |
|---|---|---|
| **IATI official datastore** — `api.iatistandard.org/datastore/activity/select` | **HTTP 401** | Live, requires a free `Ocp-Apim-Subscription-Key`. Richer and better documented than d-portal. Register and use this in preference once you have a key |
| **GlobalGiving API** — `globalgiving.org/api/` | Public API confirmed to exist | 30+ methods over projects, organisations, themes, countries. Key required; obtain via their Getting Started flow. **Read their Code of Conduct and Terms of Service before ingesting** |

---

## Tier 3 — endpoint alive, integration unresolved

### EU Funding & Tenders Portal (SEDIA search API)

```
POST https://api.tech.ec.europa.eu/search-api/prod/rest/search?apiKey=SEDIA
```

The endpoint is **live** — it returns structured JSON
(`{"apiVersion":"2.154","type":"throwable","message":"An internal error occurred"}`),
so it is responding, not down. Two attempts with different `query` shapes both
failed. **I did not get a working query and am not going to guess at one.** The
documented multipart request format needs to be read properly before this is
usable. Recorded as a real lead, not a working integration.

Relevance: Horizon Europe and Global Gateway calls are sometimes open to Indian
partners, usually as consortium members rather than lead applicants.

### FCRA portal — `fcraonline.nic.in` — RETEST FROM INDIA

`ECONNREFUSED` on `164.100.158.56:443` from our test network — the same NIC
IP-range pattern seen across the domestic inventory, so this is **probably egress
filtering of our network, not an outage.** The portal is MHA's live FCRA system
and is certainly operational in India.

Public pages identified (verify each locally):

- `https://fcraonline.nic.in/fc8_statewise.aspx` — **List of FCRA Registered Associations**, state-wise
- `https://fcraonline.nic.in/fc_public_login.aspx?Resp_Id=41` — public query interface
- Annual returns (FC-4) of each association are published on the portal

Scale reference: **16,383 FCRA-registered organisations** as of 10 March 2023, of
which 14,966 filed FY2021-22 returns.

**This is the highest-value FCRA source and the top priority for local testing.**
It answers both "is this NGO allowed to take foreign money" and "which foreign
donors have actually funded organisations like this one".

---

## Landscape change you cannot ignore: USAID is gone

In January 2025 all US foreign assistance was paused for review. By the end of
March 2025 **83% of USAID programmes were terminated**; surviving functions moved
to the Department of State, and everything else was discontinued. Food for Peace
and McGovern-Dole moved to USDA (**$1.44bn in 2026, $420m less than 2025**).
USAID had provided **$175m to India in 2023**.

**Any funder list that still shows USAID as a live donor is wrong.** This is also
a good example for the report of why a scheduled scraper with health checks beats
a hand-curated list: a static CSV written in 2024 would still be recommending a
dissolved agency.

---

## Tier X — commercial / licence-restricted

Do not ingest without checking terms. Listed because the team will find them and
should know the status.

| Source | Note |
|---|---|
| **dataful.in** | Has FCRA datasets (year/state-wise registered associations; district-wise associations receiving foreign contribution). Aggregator — **check licensing** |
| **Candid / Foundation Directory** | Subscription. Comprehensive US foundation grant data |
| **Devex** | Subscription. Funding opportunity intelligence |
| **fundsforNGOs** | Freemium, aggressively scraped-from; **terms prohibit redistribution** |
| **GuideStar India** | NGO credibility ratings, not a funder list |

---

## MANUAL DOWNLOAD CHECKLIST — foreign

Save under `data/manual/<source>/` with a `SOURCE.md` (see `data/manual/README.md`).

- [ ] **FCRA registered associations list** — `fcraonline.nic.in/fc8_statewise.aspx`, per state *(retest reachability from India first; may turn out to be scrapable, in which case move to Tier 1)*
- [ ] **FCRA annual returns (FC-4)** for a sample of comparable NGOs — these show *which foreign donors actually fund your sector*, which is the real prospecting signal
- [ ] **MHA FCRA cancellation / suspension notifications** — needed to keep `fcra_status` honest
- [ ] **MHA blanket validity-extension notifications** — these override printed expiry dates
- [ ] dataful.in FCRA datasets *(only if licensing permits)*

---

## Leads NOT verified

Nobody has checked these. Do not enter them into `grants` until someone confirms
them live. Recorded so the search is reproducible.

- UN Partner Portal (UNPP) — UN agency partnership calls
- UNDP / UNICEF / WHO India country office procurement and partnership notices
- The Global Fund (HIV/TB/malaria) — India is a major recipient country
- Gavi, the Vaccine Alliance
- Gates Foundation — grant opportunities page
- Wellcome Trust — schemes, some open to Indian institutions
- Ford Foundation India
- Rockefeller Foundation
- UK FCDO / DevTracker
- World Bank and ADB — civil-society grant windows (e.g. Japan Social Development Fund)
- Embassy small-grants schemes (Japan's GGP, Germany, Canada Fund) — small but genuinely open to Indian NGOs, and usually FCRA-prior-permission friendly

---

## Summary for the scraper design

1. **grants.gov first** — it is keyless, documented, live, and already returning
   India opportunities with real deadlines. Lowest effort, highest immediate value.
2. **FCRA portal is the strategic source** but is blocked from our network. Test
   it from an Indian connection before anything else; it may well be Tier 1.
3. **Never assert eligibility for a foreign opportunity.** Surface the
   eligibility text and the NGO's FCRA state, and let a human decide. This is the
   one place where a confident wrong answer has legal consequences for the user.
4. **IATI (d-portal now, official datastore once keyed) is for prospecting**, not
   deadlines — same role CSR data plays on the domestic side.
5. **Treat FCRA validity as a dated, refreshable fact**, not a string field.
