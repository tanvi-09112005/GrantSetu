"""Proposal PDF export (plan section: PDF/DOCX export, Phase 5).

Assembles a drafted proposal (NGO profile + grant + draft_sections from
draft_proposal) into a formatted PDF matching standard grant-proposal
convention: cover letter -> table of contents -> numbered sections ->
conclusion, styled like a formal institutional document (serif type,
1-inch margins, "Page X of Y").

The cover letter, table of contents, and conclusion are all
template-generated (not LLM calls) -- they're boilerplate built from fields
we already have, so there's no reason to spend Gemini quota on them.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas as canvas_mod
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.graph.nodes.draft import DEFAULT_SECTIONS, SECTION_TITLES


def _format_inr(amount: float) -> str:
    """Indian digit grouping (lakh/crore), e.g. 1234567 -> "INR 12,34,567".

    Uses "INR " text rather than the ₹ symbol: ReportLab's base-14 fonts
    (Times-Roman etc.) don't include the ₹ glyph, so it silently falls back
    to garbage ("n" or similar) instead of raising an error.
    """
    amount = int(round(amount))
    sign = "-" if amount < 0 else ""
    s = str(abs(amount))
    if len(s) <= 3:
        return f"{sign}INR {s}"
    last3, rest = s[-3:], s[:-3]
    parts = []
    while len(rest) > 2:
        parts.insert(0, rest[-2:])
        rest = rest[:-2]
    if rest:
        parts.insert(0, rest)
    return f"{sign}INR {','.join(parts)},{last3}"

_styles = getSampleStyleSheet()
_SERIF = "Times-Roman"
_SERIF_BOLD = "Times-Bold"
_SERIF_ITALIC = "Times-Italic"

_TITLE = ParagraphStyle(
    "ProposalTitle", parent=_styles["Title"], fontName=_SERIF_BOLD,
    fontSize=18, spaceAfter=4, alignment=1,
)
_SUBTITLE = ParagraphStyle(
    "ProposalSubtitle", parent=_styles["Normal"], fontName=_SERIF_ITALIC,
    fontSize=12, alignment=1, textColor=colors.HexColor("#333333"), spaceAfter=18,
)
_LETTER_BODY = ParagraphStyle(
    "LetterBody", parent=_styles["Normal"], fontName=_SERIF, fontSize=11.5,
    leading=17, spaceAfter=12, alignment=4,
)
_LETTER_META = ParagraphStyle(
    "LetterMeta", parent=_styles["Normal"], fontName=_SERIF, fontSize=11,
    leading=15, spaceAfter=2,
)
_TOC_TITLE = ParagraphStyle(
    "TocTitle", parent=_styles["Heading1"], fontName=_SERIF_BOLD, fontSize=16,
    alignment=1, spaceAfter=20,
)
_TOC_ENTRY = ParagraphStyle(
    "TocEntry", parent=_styles["Normal"], fontName=_SERIF, fontSize=12.5,
    leading=24,
)
_H1 = ParagraphStyle(
    "SectionHeading", parent=_styles["Heading1"], fontName=_SERIF_BOLD,
    fontSize=14, spaceBefore=16, spaceAfter=10,
    textColor=colors.HexColor("#000000"),
)
_BODY = ParagraphStyle(
    "SectionBody", parent=_styles["Normal"], fontName=_SERIF, fontSize=11,
    leading=16, spaceAfter=10, alignment=4,  # justified
)
_REG_LINE = ParagraphStyle(
    "RegLine", parent=_styles["Normal"], fontName=_SERIF_ITALIC, fontSize=9.5,
    leading=13, textColor=colors.HexColor("#444444"), alignment=1,
)
_TABLE_HEADER = ParagraphStyle(
    "TableHeader", parent=_styles["Normal"], fontName=_SERIF_BOLD, fontSize=10,
    textColor=colors.white,
)
_TABLE_CELL = ParagraphStyle(
    "TableCell", parent=_styles["Normal"], fontName=_SERIF, fontSize=9.5, leading=13,
)
_TABLE_AMOUNT = ParagraphStyle(
    "TableAmount", parent=_styles["Normal"], fontName=_SERIF, fontSize=9.5,
    leading=13, alignment=2,  # right-aligned
)
_TABLE_TOTAL = ParagraphStyle(
    "TableTotal", parent=_styles["Normal"], fontName=_SERIF_BOLD, fontSize=10,
    leading=13, alignment=2,
)

# (key, numbered title) — order here is the order printed and the TOC order.
# Conclusion is appended separately at the end (it's not in draft_sections).
_SECTION_NUMBERING: list[tuple[str, str]] = [
    (key, SECTION_TITLES.get(key, key.replace("_", " ").title()))
    for key in DEFAULT_SECTIONS
]


def _registration_line(ngo_profile: dict[str, Any]) -> str:
    parts = []
    for label, key in (
        ("12A", "reg_12a"), ("80G", "reg_80g"),
        ("FCRA", "reg_fcra"), ("NGO Darpan ID", "darpan_id"),
    ):
        value = ngo_profile.get(key)
        if value:
            parts.append(f"{label}: {value}")
    return " &nbsp;|&nbsp; ".join(parts)


def _cover_letter_flowables(ngo_profile: dict[str, Any], grant: dict[str, Any]) -> list:
    """A real business-letter cover page: sender block, date, recipient
    block, salutation, body, closing and signature — not just a title page."""
    ngo_name = ngo_profile.get("name", "the organisation")
    mission = ngo_profile.get("mission", "")
    today = date.today().strftime("%B %d, %Y")
    grant_title = grant.get("title", "")
    funder = grant.get("funder_name", "")

    flow: list = []
    flow.append(Paragraph(ngo_name, _TITLE))
    reg_line = _registration_line(ngo_profile)
    if reg_line:
        flow.append(Paragraph(reg_line, _REG_LINE))
    flow.append(Spacer(1, 0.5 * inch))

    flow.append(Paragraph(today, _LETTER_META))
    flow.append(Spacer(1, 0.25 * inch))
    flow.append(Paragraph("To,", _LETTER_META))
    flow.append(Paragraph(f"<b>{funder}</b>", _LETTER_META))
    flow.append(Paragraph(f"Subject: Grant Proposal for {grant_title}", _LETTER_META))
    flow.append(Spacer(1, 0.3 * inch))

    flow.append(Paragraph("Dear Sir/Madam,", _LETTER_BODY))
    flow.append(Paragraph(
        f"On behalf of <b>{ngo_name}</b>, we are pleased to submit the enclosed proposal "
        f"for your consideration under <b>{grant_title}</b>. {mission}",
        _LETTER_BODY,
    ))
    flow.append(Paragraph(
        "We believe this project aligns closely with the objectives of this grant "
        "programme and welcome the opportunity to discuss any aspect of this proposal "
        "further. Thank you for your time and consideration.",
        _LETTER_BODY,
    ))
    flow.append(Spacer(1, 0.4 * inch))
    flow.append(Paragraph("Yours sincerely,", _LETTER_BODY))
    flow.append(Spacer(1, 0.5 * inch))
    flow.append(Paragraph(f"<b>{ngo_name}</b>", _LETTER_META))

    flow.append(PageBreak())
    return flow


def _table_of_contents_flowables() -> list:
    flow: list = [Paragraph("Table of Contents", _TOC_TITLE)]
    for i, (_key, title) in enumerate(_SECTION_NUMBERING, start=1):
        flow.append(Paragraph(f"{i}.&nbsp;&nbsp;&nbsp;{title}", _TOC_ENTRY))
    flow.append(Paragraph(
        f"{len(_SECTION_NUMBERING) + 1}.&nbsp;&nbsp;&nbsp;Conclusion", _TOC_ENTRY
    ))
    flow.append(PageBreak())
    return flow


def _conclusion_flowable(ngo_profile: dict[str, Any], grant: dict[str, Any]) -> list:
    """Templated closing section — not an LLM call."""
    ngo_name = ngo_profile.get("name", "the organisation")
    grant_title = grant.get("title", "")
    n = len(_SECTION_NUMBERING) + 1
    flow: list = [Paragraph(f"{n}. Conclusion", _H1)]
    flow.append(Paragraph(
        f"{ngo_name} respectfully requests your favourable consideration of this "
        f"proposal for <b>{grant_title}</b>. We are committed to transparent and "
        f"accountable use of any funds granted, and remain available to provide any "
        f"further documentation or clarification the reviewing committee may require. "
        f"We thank you for the opportunity to be considered.",
        _BODY,
    ))
    return flow


class _NumberedCanvas(canvas_mod.Canvas):
    """Adds 'Page X of Y' footers — needs a two-pass build to know the total.

    showPage() must NOT finalize the page (that would write it to the PDF
    immediately); it only snapshots state and resets for the next page.
    Finalizing happens once per page, inside save().
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states: list = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()  # reset for the next page WITHOUT writing this one

    def save(self):
        total = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self._draw_footer(self._pageNumber, total)
            canvas_mod.Canvas.showPage(self)  # finalize exactly once per page
        canvas_mod.Canvas.save(self)

    def _draw_footer(self, page_num: int, total: int) -> None:
        self.saveState()
        self.setFont(_SERIF, 9)
        self.setFillColor(colors.HexColor("#666666"))
        width, _height = letter
        self.drawCentredString(width / 2, 0.6 * inch, f"Page {page_num} of {total}")
        self.restoreState()


def _budget_table_flowable(budget_table: dict[str, Any]) -> list:
    line_items = budget_table.get("line_items") or []
    if not line_items:
        return []

    header = [
        Paragraph("Budget Item", _TABLE_HEADER),
        Paragraph("Amount", _TABLE_HEADER),
        Paragraph("Justification", _TABLE_HEADER),
    ]
    rows = [header]
    for item in line_items:
        rows.append([
            Paragraph(str(item.get("item", "")), _TABLE_CELL),
            Paragraph(_format_inr(item.get("amount_inr", 0)), _TABLE_AMOUNT),
            Paragraph(str(item.get("justification", "")), _TABLE_CELL),
        ])

    total = budget_table.get("total_amount_inr")
    if total is None:
        total = sum(item.get("amount_inr", 0) for item in line_items)
    rows.append([
        Paragraph("Total", _TABLE_TOTAL),
        Paragraph(_format_inr(total), _TABLE_TOTAL),
        "",
    ])

    table = Table(rows, colWidths=[2.1 * inch, 1.1 * inch, 3.3 * inch], repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#333333")),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#eeeeee")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#999999")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("SPAN", (2, -1), (2, -1)),
    ]))
    return [Spacer(1, 0.1 * inch), table, Spacer(1, 0.15 * inch)]


def generate_proposal_pdf(
    ngo_profile: dict[str, Any],
    grant: dict[str, Any],
    draft_sections: dict[str, str],
    output_path: str | Path,
    section_order: list[str] | None = None,
    budget_table: dict[str, Any] | None = None,
) -> Path:
    """Render a proposal to a PDF file at output_path. Returns the path.

    budget_table, if provided (from draft_proposal's structured budget
    output — {"line_items": [...], "total_amount_inr": ...}), renders the
    budget section as an actual table instead of the plain narrative text.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=letter,
        leftMargin=1 * inch,
        rightMargin=1 * inch,
        topMargin=1 * inch,
        bottomMargin=1 * inch,
        title=f"{grant.get('title', 'Grant Proposal')} - {ngo_profile.get('name', '')}",
    )

    story: list = []
    story.extend(_cover_letter_flowables(ngo_profile, grant))
    story.extend(_table_of_contents_flowables())

    order = section_order or [k for k, _ in _SECTION_NUMBERING]
    numbering = {key: i + 1 for i, (key, _title) in enumerate(_SECTION_NUMBERING)}
    for key in order:
        text = draft_sections.get(key)
        if not text and not (key == "budget" and budget_table and budget_table.get("line_items")):
            continue
        title = SECTION_TITLES.get(key, key.replace("_", " ").title())
        num = numbering.get(key, "")
        story.append(Paragraph(f"{num}. {title}", _H1))
        if text:
            for para in text.split("\n\n"):
                para = para.strip()
                if para:
                    story.append(Paragraph(para, _BODY))
        if key == "budget" and budget_table:
            story.extend(_budget_table_flowable(budget_table))

    story.extend(_conclusion_flowable(ngo_profile, grant))

    doc.build(story, canvasmaker=_NumberedCanvas)
    return output_path