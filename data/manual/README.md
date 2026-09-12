# Manually downloaded sources

Everything here was fetched by a human because it cannot lawfully or technically
be scraped — see `docs/data-sources.md` for why, per source.

## Rules

One directory per source. Every directory MUST contain a `SOURCE.md` with:

```markdown
- Source name:
- URL downloaded from:
- Downloaded by:
- Downloaded on:            # absolute date, not "last week"
- Access method:            # e.g. "manual, CAPTCHA-gated"
- Stated terms on the page: # quote them
- Coverage:                 # e.g. "FY 2024-25, all states"
- Known limitations:        # e.g. "aggregate only; no per-project rows"
```

A file without a `SOURCE.md` does not get loaded into the database. This project
argues that generated text must be traceable to evidence; the evidence itself
has to be traceable too.

## Expected layout

```
data/manual/
  csr_gov_in/          # CAPTCHA-gated MIS + company-wise reports, per FY
  data_gov_in/         # robots.txt disallows crawling; portal CSV exports
  scheme_guidelines/   # scheme guideline + timeline PDFs
```
