"""draft_proposal — section-by-section generation (plan section 4.3).

Not one monolithic call: each section is drafted separately from the grant's
required format + the NGO profile + RAG context pulled from the NGO's own
documents. Smaller units are individually checkable, which is what makes the
verification stage meaningful.

On a revision pass, only the sections named in state["sections_to_revise"] are
regenerated — the rest are carried through untouched.
"""

from __future__ import annotations

import logging
from typing import Any

from app.db import pool
from app.graph.state import GrantSetuState
from app.services.embeddings import embed_query
from app.services.llm import get_llm, parse_json_response

logger = logging.getLogger(__name__)

# Default proposal skeleton; a grant with its own required format could
# override this later (e.g. from grant.eligibility_json or a template field).
DEFAULT_SECTIONS: list[str] = [
    "executive_summary",
    "organisation_background",
    "problem_statement",
    "goals_and_objectives",
    "proposed_intervention",
    "implementation_plan",
    "monitoring_and_evaluation",
    "budget",
    "sustainability",
]

# Human-readable heading for each section, used by the PDF export step
# (app/services/export.py) — kept here since it's the single source of
# truth for what each section key means.
SECTION_TITLES: dict[str, str] = {
    "executive_summary": "Executive Summary",
    "organisation_background": "Organisational Background",
    "problem_statement": "Statement of Need",
    "goals_and_objectives": "Goals and Objectives",
    "proposed_intervention": "Proposed Intervention",
    "implementation_plan": "Implementation Plan",
    "monitoring_and_evaluation": "Monitoring and Evaluation Plan",
    "budget": "Budget",
    "sustainability": "Sustainability Plan",
}

# A short retrieval query per section, so we pull chunks from the NGO's own
# documents that are actually relevant to *that* section, not just generically
# relevant to the NGO overall.
_SECTION_RETRIEVAL_QUERY: dict[str, str] = {
    "executive_summary": "organisation mission overview summary",
    "organisation_background": "organisation history establishment legal registration governance",
    "problem_statement": "community problem need beneficiaries challenges faced",
    "goals_and_objectives": "project goals objectives targets outcomes",
    "proposed_intervention": "program activities intervention approach methodology",
    "implementation_plan": "implementation timeline plan milestones schedule",
    "monitoring_and_evaluation": "monitoring evaluation indicators outcomes impact metrics results",
    "budget": "budget expenses financial statements funding utilization annual accounts",
    "sustainability": "sustainability long term plan future funding continuity",
}

# What each section must specifically be about — included directly in the
# prompt so a weaker/lite model has an explicit brief per key, not just a
# generic evidence block. Without this, a lite-tier model given several
# section keys at once can collapse them all into one repeated paragraph
# (observed: gemini-3.5-flash-lite returned identical text for 5 keys when
# only given a section label + evidence, no topical brief).
_SECTION_CONTENT_BRIEF: dict[str, str] = {
    "executive_summary": "A brief 3-5 sentence overview of who the NGO is and what THIS proposal aims to achieve.",
    "organisation_background": "The NGO's registration, history, and governance credentials only.",
    "problem_statement": "The specific community problem/need this grant addresses, with evidence of scale — not goals or solutions.",
    "goals_and_objectives": "The specific, measurable goals and objectives this project aims to achieve — not the problem, not the method.",
    "proposed_intervention": "The concrete activities and approach the NGO will carry out under this grant.",
    "implementation_plan": "A phased timeline for carrying out the proposed intervention.",
    "monitoring_and_evaluation": "How progress and impact will be tracked and measured.",
    "budget": "Financial figures and how grant funds will be utilised.",
    "sustainability": "How the initiative continues after this grant's funding ends.",
}

# Factual/numeric sections get a low temperature; narrative sections get more
# room (plan section 4.3: "temperature low for factual sections ... higher for
# narrative sections").
_LOW_TEMP_SECTIONS = {"organisation_background", "budget", "monitoring_and_evaluation"}
_LOW_TEMP = 0.2
_HIGH_TEMP = 0.6

_CONTEXT_CHUNKS_PER_SECTION = 5

# Cap how many sections go into one batched call. A larger batch saves more
# quota but raises the risk of a weaker model collapsing sections into
# repeated text (observed at 5-in-1-call with gemini-3.5-flash-lite; 3-in-1
# worked correctly). 3 is a compromise between quota savings and reliability.
_MAX_BATCH_SIZE = 3


def _chunked(items: list[str], size: int) -> list[list[str]]:
    return [items[i : i + size] for i in range(0, len(items), size)]


def _get_ngo_profile(state: GrantSetuState) -> dict[str, Any]:
    profile = state.get("ngo_profile") or {}
    if profile:
        return profile
    ngo_id = state.get("ngo_id")
    if not ngo_id:
        return {}
    return pool.fetch_one("select * from ngo_profiles where id = %s", (ngo_id,)) or {}


def _get_grant(grant_id: str) -> dict[str, Any]:
    row = pool.fetch_one(
        """
        select id, title, funder_name, funder_type, description,
               sectors, geography, deadline, eligibility_text, eligibility_json
        from grants
        where id = %s
        """,
        (grant_id,),
    )
    return dict(row) if row else {}


def _retrieve_context(ngo_id: str, section_key: str, k: int = _CONTEXT_CHUNKS_PER_SECTION) -> str:
    """Pull the k most relevant chunks from this NGO's own documents for a section.

    Falls back to an empty string (not an exception) if embedding or the query
    fails — a section can still draft without grounding, it'll just carry more
    fabrication risk, which is exactly what the verification stage downstream
    exists to catch.
    """
    query_text = _SECTION_RETRIEVAL_QUERY.get(section_key, section_key)
    try:
        vector = embed_query(query_text)
    except Exception as exc:
        logger.warning("embed_query failed for section=%s (%s); drafting without context", section_key, exc)
        return ""

    try:
        rows = pool.fetch_all(
            """
            select chunk_text
            from document_chunks
            where ngo_id = %s
            order by embedding <=> %s::vector
            limit %s
            """,
            (ngo_id, vector, k),
        )
    except Exception as exc:
        logger.warning("chunk retrieval failed for section=%s (%s); drafting without context", section_key, exc)
        return ""

    return "\n---\n".join(r["chunk_text"] for r in rows)


def _build_batch_prompt(
    section_keys: list[str],
    ngo_profile: dict[str, Any],
    grant: dict[str, Any],
    context_map: dict[str, str],
) -> str:
    ngo_name = ngo_profile.get("name", "the organisation")
    mission = ngo_profile.get("mission", "")
    sectors = ", ".join(ngo_profile.get("sectors") or [])

    grant_title = grant.get("title", "")
    funder = grant.get("funder_name", "")
    grant_desc = grant.get("description", "")

    sections_block = ""
    for key in section_keys:
        label = key.replace("_", " ")
        brief = _SECTION_CONTENT_BRIEF.get(key, label)
        ctx = context_map.get(key) or "[no supporting document context retrieved for this section]"
        sections_block += (
            f'\n### Section key: "{key}" ({label})\n'
            f"This section is ONLY about: {brief}\n"
            f"Evidence for THIS section only:\n{ctx}\n"
        )

    return f"""You are drafting multiple sections of a grant proposal for {ngo_name},
applying to "{grant_title}" ({funder}).

NGO mission: {mission}
NGO sectors: {sectors}
Grant description: {grant_desc}

For each section below, write its body text using ONLY that section's own evidence block and
its own topic brief. Do not invent numbers, dates or claims not present in that section's
evidence, and do not borrow evidence from one section into another. If a section's evidence
doesn't cover something, write generally rather than inventing specifics. No headings inside
the text.

CRITICAL: each section's text must be substantively different from every other section's —
different focus, different sentences. Do NOT write the same paragraph (or near-identical
wording) for more than one key. If two sections would otherwise say the same thing, narrow
each one to only what its topic brief asks for.
{sections_block}

Return ONLY a JSON object mapping each section key to its drafted body text, exactly these
keys: {section_keys}
Example shape: {{"{section_keys[0]}": "...", ...}}"""


def _build_budget_prompt(
    ngo_profile: dict[str, Any],
    grant: dict[str, Any],
    context: str,
) -> str:
    ngo_name = ngo_profile.get("name", "the organisation")
    grant_title = grant.get("title", "")

    return f"""You are drafting the BUDGET section of a grant proposal for {ngo_name},
applying to "{grant_title}".

The evidence below is likely the NGO's own PAST organisation-wide financial statement
(e.g. an annual report) — NOT a budget for this specific new project. Use it ONLY to judge
what scale of spending is realistic and credible for an organisation of this size. Do NOT
copy its categories or figures directly as line items, and do NOT take any single aggregate
figure from it and then also break that same figure into invented sub-items — that would
double-count the same money.

Evidence (organisational financial context only):
{context if context else "[no supporting document context retrieved]"}

Produce a NEW, project-specific budget for what THIS grant needs to fund — individual line
items appropriate to this type of project (e.g. staff salaries, programme materials,
monitoring & evaluation, administrative overheads). Each line item must be for genuinely
different spending — no item may be a subset, breakdown, or restatement of another item's
figure. The line items must be mutually exclusive: summing them should represent real total
new spend, not double-counted spend.

Return ONLY a JSON object of this exact shape (no extra keys, no markdown fences):
{{
  "narrative": "1-2 sentence summary of the overall budget approach",
  "line_items": [
    {{"item": "short line item name", "amount_inr": <number, no commas or currency symbols>, "justification": "one short sentence"}}
  ]
}}"""


def _detect_subset_sum_overlap(line_items: list[dict[str, Any]], tolerance: float = 0.01) -> list[str]:
    """Flag budget items where a group of smaller items sums to ~another
    item's value — the signature of an aggregate + its own breakdown being
    listed as separate line items (double-counted money).

    Bounded to combinations of size 2-4 for performance; budgets rarely have
    enough line items for this to matter, and this is a heuristic safeguard,
    not a proof — it flags for human review, it doesn't silently "fix" data.
    """
    import itertools

    warnings: list[str] = []
    amounts = [(item.get("item", ""), item.get("amount_inr", 0)) for item in line_items]
    n = len(amounts)
    if n < 3:
        return warnings

    for target_idx, (target_name, target_amount) in enumerate(amounts):
        if target_amount <= 0:
            continue
        others = [a for i, a in enumerate(amounts) if i != target_idx]
        for size in range(2, min(4, len(others)) + 1):
            for combo in itertools.combinations(others, size):
                combo_sum = sum(a for _, a in combo)
                if target_amount > 0 and abs(combo_sum - target_amount) / target_amount < tolerance:
                    combo_names = ", ".join(name for name, _ in combo)
                    warnings.append(
                        f"budget: '{target_name}' (INR {target_amount:,.0f}) appears to equal "
                        f"the sum of [{combo_names}] — possible double-counted aggregate + breakdown"
                    )
    return warnings


def _draft_budget(
    ngo_id: str,
    ngo_profile: dict[str, Any],
    grant: dict[str, Any],
) -> tuple[str, list[dict[str, Any]], list[str]]:
    """Draft the budget as structured line items, not prose.

    Returns (narrative_text, line_items, errors). The total is computed in
    code from line_items rather than trusted from the model — letting an LLM
    both generate figures and sum them risks an arithmetic fabrication on top
    of a content one.
    """
    context = _retrieve_context(ngo_id, "budget") if ngo_id else ""
    prompt = _build_budget_prompt(ngo_profile, grant, context)
    errors: list[str] = []

    try:
        llm = get_llm(tier="pro", temperature=_LOW_TEMP)
        resp = llm.invoke(prompt)
        text = resp.content
        if isinstance(text, list):
            text = " ".join(
                part.get("text", "") if isinstance(part, dict) else str(part)
                for part in text
            )
        parsed = parse_json_response(str(text))
        narrative = str(parsed.get("narrative", "")).strip() if isinstance(parsed, dict) else ""
        raw_items = parsed.get("line_items", []) if isinstance(parsed, dict) else []

        line_items = []
        for item in raw_items:
            if not isinstance(item, dict):
                continue
            try:
                amount = float(item.get("amount_inr", 0))
            except (TypeError, ValueError):
                amount = 0.0
            line_items.append({
                "item": str(item.get("item", "")).strip(),
                "amount_inr": amount,
                "justification": str(item.get("justification", "")).strip(),
            })

        if not line_items:
            errors.append("draft_proposal: budget returned no usable line items")
        else:
            errors.extend(_detect_subset_sum_overlap(line_items))

        return narrative, line_items, errors
    except Exception as exc:
        logger.exception("drafting failed for budget")
        errors.append(f"draft_proposal: budget failed ({exc})")
        return "", [], errors


def draft_proposal(state: GrantSetuState) -> GrantSetuState:
    ngo_id = state.get("ngo_id", "")
    grant_id = state.get("selected_grant_id", "")
    targets = state.get("sections_to_revise") or DEFAULT_SECTIONS

    ngo_profile = _get_ngo_profile(state)
    grant = _get_grant(grant_id) if grant_id else {}

    sections = dict(state.get("draft_sections", {}))
    errors = list(state.get("errors", []))
    budget_table = dict(state.get("budget_table") or {})

    # Budget is handled separately as structured line items, not batched prose
    # — a PDF export needs a real table here, not a paragraph.
    if "budget" in targets:
        narrative, line_items, budget_errors = _draft_budget(ngo_id, ngo_profile, grant)
        errors.extend(budget_errors)
        if line_items or narrative:
            sections["budget"] = narrative
            total = sum(item["amount_inr"] for item in line_items)
            budget_table = {"line_items": line_items, "total_amount_inr": total}
        else:
            sections.setdefault("budget", "")

    # Batch everything else by temperature tier, capped at _MAX_BATCH_SIZE per
    # call. Retrieval (embed_query) stays per-section since it's a separate,
    # much higher-quota API than generateContent.
    remaining = [s for s in targets if s != "budget"]
    low_group = [s for s in remaining if s in _LOW_TEMP_SECTIONS]
    high_group = [s for s in remaining if s not in _LOW_TEMP_SECTIONS]

    batches = [
        (chunk, _LOW_TEMP)
        for chunk in _chunked(low_group, _MAX_BATCH_SIZE)
    ] + [
        (chunk, _HIGH_TEMP)
        for chunk in _chunked(high_group, _MAX_BATCH_SIZE)
    ]

    for group, temperature in batches:
        context_map = {s: (_retrieve_context(ngo_id, s) if ngo_id else "") for s in group}
        prompt = _build_batch_prompt(group, ngo_profile, grant, context_map)

        try:
            llm = get_llm(tier="pro", temperature=temperature)
            resp = llm.invoke(prompt)
            text = resp.content
            if isinstance(text, list):
                text = " ".join(
                    part.get("text", "") if isinstance(part, dict) else str(part)
                    for part in text
                )
            parsed = parse_json_response(str(text))

            # Safeguard: a weak/lite model can collapse multiple keys into
            # identical (or near-identical) text instead of writing distinct
            # sections. Detect exact duplicates within this batch and treat
            # every key after the first occurrence as failed, rather than
            # silently shipping wrong content into multiple sections.
            seen_texts: dict[str, str] = {}
            for key in group:
                value = parsed.get(key) if isinstance(parsed, dict) else None
                if not value:
                    errors.append(f"draft_proposal: {key} missing from batched response")
                    sections.setdefault(key, "")
                    continue

                normalized = str(value).strip().lower()
                if normalized in seen_texts:
                    logger.warning(
                        "draft_proposal: %s duplicated %s's output in the same batch — dropping",
                        key,
                        seen_texts[normalized],
                    )
                    errors.append(
                        f"draft_proposal: {key} returned duplicate content "
                        f"(same as {seen_texts[normalized]}); batch may need a smaller size "
                        "or a stronger model"
                    )
                    sections.setdefault(key, "")
                    continue

                seen_texts[normalized] = key
                sections[key] = str(value).strip()
        except Exception as exc:
            logger.exception("drafting failed for section group=%s", group)
            for key in group:
                errors.append(f"draft_proposal: {key} failed ({exc})")
                # Keep whatever was there before (e.g. a prior revision),
                # rather than wiping a working section on a transient failure.
                sections.setdefault(key, "")

    return {
        "draft_sections": sections,
        "budget_table": budget_table,
        "sections_to_revise": [],
        "status": "drafted",
        "errors": errors,
    }