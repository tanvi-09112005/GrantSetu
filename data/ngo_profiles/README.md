# Test NGO profiles

Week-1 checklist item: **one realistic test NGO profile built from a real NGO's
public annual report**, in week 1 — not as a late scramble before a demo.

This is the fallback for having no live NGO partner, and it is also what the
verification stage is measured against: claims in a generated proposal are
checked against *these* documents, so the corpus has to be real prose with real
numbers in it.

## What to put here

```
data/ngo_profiles/<slug>/
  profile.json          # matches the ngo_profiles columns
  source.md             # where the documents came from, and the licence/terms
  docs/                 # the PDFs themselves (annual report, program reports)
```

`profile.json`:

```json
{
  "name": "...",
  "mission": "...",
  "sectors": ["education", "health"],
  "location": "Maharashtra",
  "reg_12a": "AAATx1234xE20214",
  "reg_80g": null,
  "reg_fcra": null,
  "registered_on": "2011-06-14"
}
```

Use registration numbers only if they are published in the organisation's own
public filings; otherwise leave the field `null` and note it in `source.md`.
A null reads as "does not hold this registration" to the eligibility engine,
so record in `source.md` which nulls mean *not held* and which mean *unknown*.

## Controlled test case

Phase 4 needs a proposal containing a claim **deliberately absent** from these
documents — otherwise a demo cannot show the verification step firing. Keep it
in `data/ngo_profiles/<slug>/controlled_case.md` alongside the expected verdict.
