# GrantSetu — data source inventory

**Reconnaissance date: 7 September 2026.** Every status below was checked live on
that date, not recalled. Where something is unverified it says so explicitly.

## How to read this

Sources are tiered by *whether we can legally and technically get the data*, not
by how useful the data is. A rich source behind a CAPTCHA is Tier X, not Tier 1.

| Tier | Meaning |
|---|---|
| **1** | Public, no login, no CAPTCHA, robots permits — build a scraper |
| **2** | Reachable but login-gated or thin — partial value, usually PDFs only |
| **3** | Unreachable **from our test network** — must be retested from an Indian IP before writing off |
| **4** | DNS does not resolve — confirmed dead |
| **X** | Reachable but **must not** be automated (CAPTCHA / robots disallow) — manual download only |

### An important caveat on Tier 3

Many `.gov.in` / `.nic.in` hosts returned `ECONNREFUSED` on port 443 from IPs in
the `164.100.x.x` range (NIC's own block). That is **not proof the site is down** —
it is equally consistent with geo- or egress-filtering of our test network. The
team is in Mumbai. **Retest every Tier 3 host from a local Indian connection
before concluding it is dead.** `ENOTFOUND` (Tier 4) is different: those domains
do not resolve in public DNS anywhere, which is strong evidence.

---

## Tier 1 — build scrapers for these

### 1.1 eAnudaan — `grants-msje.gov.in` ★ highest value

Serves **two** ministries: Social Justice & Empowerment, and Empowerment of
Persons with Disabilities (both NGO Darpan entries point here).

- No login wall, no CAPTCHA on public pages
- `/schemes` — the scheme catalogue. Currently four umbrella schemes:
  - **NAPDDR** — National Action Plan for Drug Demand Reduction
  - **AVYAY** — Atal Vayo Abhyuday Yojana
  - **SHRESHTA** — Residential Education for Students in High Schools in Targeted Areas (SC welfare)
  - **SMILE** — Support for Marginalised Individuals for Livelihood and Enterprise
- `/office-memorandums` — OMs and guidelines
- **Dated notices carrying real application windows**, e.g. "Notice inviting
  applications for Gap District", "Extension of last date for submission of
  proposals", "Opening of e-anudaan portal throughout the year", "Notice
  inviting application for Garima Greh", NAPDDR (DDAC) EoI + corrigendum
- Guidelines published in English and Hindi (relevant: BGE-M3 is multilingual —
  this is where that choice earns its keep)

**This is the single best source in the inventory.** Real institutional grants,
real 12A/80G/FCRA-style eligibility, real deadlines, publicly served.

### 1.2 NGO Grants Portal — `ngo.tribal.gov.in` ★

Ministry of Tribal Affairs. No login wall, no CAPTCHA on public pages.

- `/newGuidelines`, `/archivedGuidelines`, `/otherDocuments`, `/newsAndUpdates`, `/faq`
- `/priorityVillagesList` — targeting data
- **Dated PDFs with live windows** (all current as of the recon date):
  - `RevisedTimelines202627.pdf` — FY 2026-27 processing timelines
  - `extensionLetter07052026.pdf` — deadline extension, 7 May 2026
  - `ngoPortalOpen202627.pdf` — portal open for FY 2026-27 proposals
  - `TimelinesOngoing24252526NGO.pdf`
  - `scheduledAreaList10032026.pdf` — **List of Scheduled Areas → geography eligibility**
- Annual report format, inspection formats (education / health / livelihood)
- ST female literacy rate list by district

### 1.3 NGO Darpan — `ngodarpan.gov.in`

NITI Aayog's NPO registry. Public dashboard, no login for aggregates.

- **610,206 total Darpan IDs; 610,121 active; 85 blacklisted**
- Entity split: Trust 304,094 (49.84%), Society 250,300 (41.02%),
  Section 8 Company 55,727 (9.13%)
- Per-state filtering available
- **The canonical index of 25 ministry grant portals** — this is what seeded
  this inventory

Two uses: (a) the ministry portal index, (b) validating that a user's Darpan ID
is real. Note the site's own advisory prohibits use of the NITI Aayog name/logo
or National Emblem — **do not put those in GrantSetu's UI.**

No `robots.txt` is served (the path returns the SPA shell).

---

## Tier 2 — reachable, but gated or off-topic

| Host | Ministry | Finding |
|---|---|---|
| `npcbvi.mohfw.gov.in` | MoHFW (blindness/visual impairment) | Login-gated. Banner: "Portal is undergoing migration to better domains." Lists 2,203 registered NGOs; "Pattern of Assistance under NPCBVI" doc exists but details are behind login |
| `aimapp2.aim.gov.in` | NITI Aayog — Atal Innovation Mission | Login-gated. **Stale: "Deadline 31st March, 2019 is over now."** Targets schools (UDISE code), not NGOs |
| `new.broadcastseva.gov.in` | Information & Broadcasting | Login-gated. Broadcast licences (satellite TV, community radio, DTH, OTT) — **not NGO grants**. Community radio is the only plausibly relevant slice |
| `ncmei.gov.in` | Higher Education | Reachable, no login. But it is a **quasi-judicial body** issuing Minority Status Certificates — **no grants at all**. NGO Darpan's index is wrong to list it as a grant portal |
| `doj.gov.in/ngo` | Department of Justice | **HTTP 403** to our fetcher — likely UA-based bot blocking rather than policy. Retest in a real browser |

---

## Tier 3 — unreachable from our network (RETEST FROM INDIA)

Do not write these off until someone in Mumbai tries them.

| Host | Ministry / scheme | Error |
|---|---|---|
| `sfurti.msme.gov.in` | MSME — SFURTI | ECONNREFUSED :443 |
| `nlcpr.mdoner.gov.in/ngo/` | North Eastern Region | ECONNREFUSED :443 |
| `cpds.chemicals.gov.in` | Chemicals & Petrochemicals | ECONNREFUSED :443 |
| `handicrafts.gov.in` | Textiles — DC Handicrafts | ECONNREFUSED :443 |
| `tourismhsrtempanelment.nic.in` | Tourism — HSRT | ECONNREFUSED :443 |
| `ngodarpan.nacwc.gov.in` | Cabinet Secretariat — NACWC | ECONNREFUSED :443 |
| `jsactr.mowr.gov.in` | Jal Shakti — National Water Mission | ECONNREFUSED :443 |
| `research.mines.gov.in` | Mines | TLS: incomplete certificate chain |
| `dbtepromis.nic.in` | Biotechnology | TLS: cannot verify first certificate |
| `jss.gov.in` | Skill Development — Jan Shikshan Sansthan | TLS cert is for `skillindiadigital.gov.in` — **migrated**, follow it there |
| `ngogrant.mohua.gov.in` | Housing & Urban Affairs | Navigation refused in our browser; not conclusively tested |
| `mofapp.nic.in/deagrants` | Economic Affairs | **HTTP 404** — path is wrong or retired |

Not yet probed: `pmsuryaghar.gov.in` (M/o New & Renewable Energy),
`mplads.sbi` (MPLADS). Both are on the NGO Darpan list.

---

## Tier 4 — confirmed dead (DNS does not resolve)

These do not resolve in public DNS. NGO Darpan is still linking them.

| Host | Ministry |
|---|---|
| `ngogrant.pharmaceuticals.gov.in` | Department of Pharmaceuticals |
| `nairoshni.minorityaffairs.gov.in` | Minority Affairs — Nai Roshni |
| `ngo.ayush.gov.in` | AYUSH |

**Design consequence:** the authoritative government index of NGO grant portals
contains dead links. A scraper that assumes the index is live will silently lose
sources. Per-source health checks and staleness alerting are not optional here —
this is the concrete justification for the Addendum's "Antigravity owns scraper
maintenance" line.

---

## Tier X — do not automate

### csr.gov.in — National CSR Portal (MCA) — **CAPTCHA-gated**

Rich data: FY 2024-25 shows **29,546 companies, ₹40,794 Cr spent, 72,233 CSR
projects, 14 development sectors, 40 states/UTs**.

**Every data view is CAPTCHA-gated** — the company-wise search *and* the
aggregate MIS reports (State Wise, PSU/Non-PSU Wise, Development Sector Wise).
Each page renders "Captcha: Refresh Captcha / Enter the Value: / Submit /
Download Report". The site also loads `clientlibs-gcmencrypt.min.js` and
`clientlibs-encrptdecrypt.min.js` (client-side encrypted queries) and serves
`/bin/csr/generateCaptchaWithHMAC`.

**We will not bypass this.** It is an explicit anti-automation control.
→ **Manual download only.** See the checklist below.

Also note the provenance, from MCA's own disclaimer: the data comes from
*"disclosures made by companies in Segment III of e-form AOC-4 (XBRL and
Non-XBRL)"* — statutory filings made **after** money is spent, with MCA
explicitly disclaiming completeness and accuracy and stating the company's Board
Report takes precedence.

**So csr.gov.in tells you what was already funded, not what is open to apply
for.** There is no official machine-readable database of open Indian CSR calls,
because Indian CSR largely does not run on public RFPs. Plan the CSR half of
GrantSetu as **funder prospecting** ("which companies funded my sector in my
district, at what scale"), not as deadline-driven grant discovery.

### data.gov.in — website disallowed, **official API allowed**

**Corrected 7 Sep 2026** — an earlier revision of this document said "manual
download only". That was too strict. Two different hosts, two different rules:

| Host | Rule |
|---|---|
| `www.data.gov.in` (the website) | `robots.txt` is `User-agent: * / Disallow: /` → **do not crawl** |
| `api.data.gov.in` (the OGD REST API) | **Sanctioned programmatic access.** No robots.txt (404). Requires a free registered API key |

Verified live: a request with no key returns `400`; with an invalid key it
returns `{"error": "Key not authorised"}`. So the API is real and key-gated.

```
GET https://api.data.gov.in/resource/{resource_id}?api-key={key}&format=json&offset=0&limit=100
```

Licence: **Government Open Data Licence – India (GODL)** — worldwide,
royalty-free, perpetual reuse **with attribution**. Attribution is a condition,
not a courtesy; carry the source name through to the UI.

**Per-dataset caveat:** not every dataset is API-enabled. Where a dataset page
shows a "Request API" button instead of a resource ID, that dataset has no API
and must still be downloaded by hand. The CSR datasets below appear to be in
that category — confirm per dataset before assuming.

Known CSR datasets (aggregates only, coverage ends 2021-22): sector-wise CSR
expenditure 2018-19→2020-21; year-wise CSR spend by MCA-registry companies
2018-19→2020-21; state/UT-wise CSR funds 2017-18→2021-22.

**Action:** register for an OGD API key, then search the catalogue for real
resource IDs — `backend/scrapers/data_gov_in.py` currently ships with an empty
`DEFAULT_RESOURCE_IDS` placeholder list.

---

## myScheme — `myscheme.gov.in` — crawlable, but mostly the wrong corpus

`robots.txt` is permissive:

```
User-agent: *
Allow: /
Disallow: /404
Sitemap: https://www.myscheme.gov.in/sitemap.xml
```

**4,772 schemes** live. Scheme detail pages at `/schemes/{slug}` with sections:
Details, Benefits, Eligibility, Application Process, Documents Required, FAQ.

Three things to know before building against it:

1. **Enumeration is not free.** The sitemap contains only ~40 static pages — no
   scheme URLs. You must paginate the search UI to discover slugs.
2. **No stable JSON API.** The internal `/_next/data/{buildId}/...` endpoint
   rotates its build ID on every deploy (we watched a request to it fall back to
   HTML mid-session). `api.myscheme.gov.in` exists but requires a key we do not
   legitimately have. **Plan on rendered-page extraction.**
3. **Most of it is citizen-facing, not NGO-facing.** Top results are Stand-Up
   India (loans to individual entrepreneurs), PM Suraksha Bima Yojana
   (individual insurance), pensions for veteran artists, marriage assistance for
   widows' daughters, UGC faculty research grants. The filter facets are Gender,
   Age, Caste, Marital Status, Disability Percentage, Employment Status, BPL,
   Student — **attributes of a person, not an organisation.**

Our `ngo_profiles` schema keys eligibility off 12A / 80G / FCRA / years
registered — attributes of an *organisation*. Those axes do not meet. Ingest a
**filtered subset** (the ministry grant-in-aid schemes) or a beneficiary-scheme
feature becomes a separate product with its own eligibility engine.

---

## MANUAL DOWNLOAD CHECKLIST

Everything below must be fetched by a human. Save under `data/manual/<source>/`
with a `SOURCE.md` recording **who downloaded it, when, from which URL, and the
page's stated terms**. Provenance matters — this project's whole thesis is about
grounding claims in verifiable sources.

### Must download — CSR (csr.gov.in, CAPTCHA-gated)

- [ ] **Development Sector Wise** MIS report — `ExploreCsrData/mis-reports/development-sector-wise.html` → "Download Report"
- [ ] **State Wise** MIS report — `ExploreCsrData/mis-reports/state-wise-report.html`
- [ ] **PSU / Non-PSU Wise** MIS report — `ExploreCsrData/mis-reports/psu-nonpsu-wise.html`
- [ ] **Company-wise** data — `ExploreCsrData/company-wise.html` (the funder-prospecting core)
- [ ] Repeat per financial year: FY 2024-25, 2023-24, 2022-23, 2021-22, 2020-21

### Must download — data.gov.in datasets with no API

*(Check each dataset for an API resource ID first — only hand-download the ones with no API.)*

- [ ] Sector-wise CSR expenditure, education/special education/vocational skill, 2018-19 → 2020-21
- [ ] Year-wise CSR spent by companies in the MCA-21 registry, 2018-19 → 2020-21
- [ ] Year-wise state/UT-wise CSR funds, 2017-18 → 2021-22

### Must download — scheme guideline PDFs (linked publicly; grab once, re-check per phase)

- [ ] eAnudaan: SMILE guidelines (EN + HI), NAPDDR/DDAC guidelines, AVYAY/IPOP guidelines, DDRS notices, Garima Greh EoI
- [ ] Tribal: `RevisedTimelines202627.pdf`, `ngoPortalOpen202627.pdf`, `scheduledAreaList10032026.pdf`, `DocumentFormatsforNGO06022023.pdf`

*(These are freely linked and could be fetched by the scraper; listing them here
so the corpus is reproducible even if a link rots.)*

---

## Leads NOT yet verified

Listed as **leads only** — nobody has checked these. Do not enter them into
`grants` until someone confirms them live. Recorded so the search is
reproducible, not as claims.

- NABARD (FPO/producer-organisation grant support)
- DST — SEED division (Science for Equity, Empowerment and Development)
- Ministry of Women & Child Development (Mission Shakti implementing partners)
- National Trust for Persons with Disabilities
- ICSSR (social science research grants)
- Ministry of Minority Affairs (beyond the dead Nai Roshni host)
- Individual corporate CSR / foundation pages — crawlable per funder, no central index
- State-level CSR and NGO portals
- Commercial aggregators (fundsforNGOs, GuideStar India, Devex) — **check licensing before touching**

---

## Summary for the scraper design

1. **Two Tier-1 scrapers first**: eAnudaan and Tribal NGO Grants. Between them
   they cover three ministries, carry real deadlines, and have no access
   controls. This is the corpus that makes discovery + eligibility meaningful.
2. **Health-check every source on every run.** The government index is already
   partly rotted; three portals are dead in DNS and one links a 2019 deadline.
   Alert on staleness rather than silently dropping a funder.
3. **Never live-fetch during a user request.** The app reads the DB; the scraper
   fills it. A portal outage must not take a demo down.
4. **Manual downloads are first-class citizens**, not a stopgap. CSR data can
   only ever enter the system this way, so build the loader and the provenance
   record for it properly.
5. **Do not automate csr.gov.in** (CAPTCHA) and **do not crawl the
   data.gov.in website** (robots disallow). The `api.data.gov.in` REST API
   with a registered key is fine and is the correct path — attribute under GODL.
