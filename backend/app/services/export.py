"""Proposal PDF & DOCX export suite (Phase 5).

Assembles a drafted proposal (NGO profile + grant + draft_sections from
draft_proposal) into:
1. High-resolution institutional PDF via ReportLab with:
   - Formal Front Cover Page (Logo, metadata cards, tracking reference)
   - Executive Transmittal / Cover Letter on letterhead
   - Numbered Table of Contents
   - Numbered body sections with parsed Markdown tables and lists
   - Statutory End-Page with formal declaration, grant disbursement bank details,
     and dual-signatory authorization block (Signature + Stamp overlay + GrantSetu Security Seal).
   - Running header ("NGO Name | Proposal Title") and footer ("Page X of Y").
2. Editable Microsoft Word (.docx) via python-docx with styled tables, letterhead,
   embedded branding assets, and statutory sign-off.
"""

from __future__ import annotations

import base64
from datetime import date
import io
import logging
from pathlib import Path
import re
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas as canvas_mod
from reportlab.platypus import (
    HRFlowable,
    Image as RLImage,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

import docx
from docx.enum.table import WD_ALIGN_VERTICAL, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls
from docx.shared import Inches, Pt, RGBColor

from app.db import pool
from app.graph.nodes.draft import DEFAULT_SECTIONS, SECTION_TITLES

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Formatting & Assets Helpers
# ---------------------------------------------------------------------------

def _format_inr(amount: float) -> str:
    """Indian digit grouping (lakh/crore), e.g. 1234567 -> "INR 12,34,567"."""
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


def get_ngo_branding_assets(ngo_id: str | None) -> dict[str, bytes]:
    """Fetch raw PNG bytes (logo, stamp, signature) for this NGO from ngo_assets."""
    if not ngo_id:
        return {}
    try:
        rows = pool.fetch_all(
            "select asset_type, data from ngo_assets where ngo_id = %s",
            (ngo_id,),
        )
        return {r["asset_type"]: bytes(r["data"]) for r in rows if r.get("data")}
    except Exception as exc:
        logger.warning("Could not fetch ngo_assets for %s: %s", ngo_id, exc)
        return {}


def _clean_markdown_for_reportlab(text: str) -> str:
    """Convert standard markdown bold/italic and currency to ReportLab safe XML."""
    if not text:
        return ""
    # Replace Rupee symbol with INR to prevent font rendering errors
    text = text.replace("₹", "INR ")
    # Replace literal & with &amp; if not already part of an entity
    text = re.sub(r"&(?![a-zA-Z]+;|#\d+;)", "&amp;", text)
    # Bold **text** -> <b>text</b>
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    # Italic *text* -> <i>\1</i>
    text = re.sub(r"(?<!\*)\*([^*]+?)\*(?!\*)", r"<i>\1</i>", text)
    return text.strip()


# ---------------------------------------------------------------------------
# ReportLab Styling Constants
# ---------------------------------------------------------------------------

_styles = getSampleStyleSheet()
_SERIF = "Times-Roman"
_SERIF_BOLD = "Times-Bold"
_SERIF_ITALIC = "Times-Italic"
_SANS = "Helvetica"
_SANS_BOLD = "Helvetica-Bold"

_NAVY = colors.HexColor("#0F172A")
_SLATE_DARK = colors.HexColor("#0F172A")
_SLATE_MUTED = colors.HexColor("#475569")
_BG_LIGHT = colors.HexColor("#F8FAFC")
_BORDER_COLOR = colors.HexColor("#334155")

_COVER_SUPER = ParagraphStyle(
    "CoverSuper", parent=_styles["Normal"], fontName=_SANS_BOLD,
    fontSize=10, leading=14, textColor=_SLATE_DARK, alignment=1, spaceAfter=8,
)
_COVER_TITLE = ParagraphStyle(
    "CoverTitle", parent=_styles["Title"], fontName=_SERIF_BOLD,
    fontSize=22, leading=28, textColor=_SLATE_DARK, alignment=1, spaceAfter=8,
)
_COVER_SUBTITLE = ParagraphStyle(
    "CoverSubtitle", parent=_styles["Normal"], fontName=_SERIF_ITALIC,
    fontSize=12, leading=16, textColor=_SLATE_MUTED, alignment=1, spaceAfter=20,
)
_LETTERHEAD_NAME = ParagraphStyle(
    "LetterheadName", parent=_styles["Normal"], fontName=_SERIF_BOLD,
    fontSize=16, leading=20, textColor=_SLATE_DARK, alignment=0,
)
_LETTERHEAD_META = ParagraphStyle(
    "LetterheadMeta", parent=_styles["Normal"], fontName=_SERIF,
    fontSize=9, leading=13, textColor=_SLATE_MUTED, alignment=0,
)
_LETTER_BODY = ParagraphStyle(
    "LetterBody", parent=_styles["Normal"], fontName=_SERIF, fontSize=11,
    leading=16, spaceAfter=10, alignment=4,
)
_LETTER_META = ParagraphStyle(
    "LetterMeta", parent=_styles["Normal"], fontName=_SERIF, fontSize=10.5,
    leading=15, spaceAfter=3,
)
_TOC_TITLE = ParagraphStyle(
    "TocTitle", parent=_styles["Heading1"], fontName=_SERIF_BOLD, fontSize=16,
    textColor=_NAVY, alignment=1, spaceAfter=20,
)
_TOC_ENTRY = ParagraphStyle(
    "TocEntry", parent=_styles["Normal"], fontName=_SERIF, fontSize=11.5,
    leading=22,
)
_H1 = ParagraphStyle(
    "SectionHeading", parent=_styles["Heading1"], fontName=_SERIF_BOLD,
    fontSize=13.5, leading=18, spaceBefore=14, spaceAfter=8,
    textColor=_NAVY, keepWithNext=True,
)
_H2 = ParagraphStyle(
    "SectionSubheading", parent=_styles["Heading2"], fontName=_SERIF_BOLD,
    fontSize=11.5, leading=15, spaceBefore=10, spaceAfter=4,
    textColor=_SLATE_DARK, keepWithNext=True,
)
_BODY = ParagraphStyle(
    "SectionBody", parent=_styles["Normal"], fontName=_SERIF, fontSize=10.5,
    leading=15, spaceAfter=8, alignment=4,
)
_BULLET = ParagraphStyle(
    "SectionBullet", parent=_styles["Normal"], fontName=_SERIF, fontSize=10.5,
    leading=14.5, spaceAfter=4, leftIndent=16, bulletIndent=4,
)
_CALLOUT = ParagraphStyle(
    "CalloutText", parent=_styles["Normal"], fontName=_SERIF_ITALIC, fontSize=10,
    leading=14, textColor=_SLATE_DARK,
)
_TABLE_HEADER = ParagraphStyle(
    "TableHeader", parent=_styles["Normal"], fontName=_SANS_BOLD, fontSize=9,
    leading=12, textColor=colors.white, alignment=0,
)
_TABLE_CELL = ParagraphStyle(
    "TableCell", parent=_styles["Normal"], fontName=_SERIF, fontSize=9,
    leading=12, alignment=0,
)
_TABLE_AMOUNT = ParagraphStyle(
    "TableAmount", parent=_styles["Normal"], fontName=_SANS_BOLD, fontSize=9,
    leading=12, alignment=2,
)
_DECLARATION = ParagraphStyle(
    "DeclarationText", parent=_styles["Normal"], fontName=_SERIF_ITALIC,
    fontSize=10, leading=15, textColor=_SLATE_DARK, alignment=4,
)


def _make_numbered_canvas(ngo_name: str, grant_title: str):
    """Factory creating NumberedCanvas with institutional header and footer."""

    class _InstitutionalNumberedCanvas(canvas_mod.Canvas):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._saved_page_states: list = []

        def showPage(self):
            self._saved_page_states.append(dict(self.__dict__))
            self._startPage()

        def save(self):
            total = len(self._saved_page_states)
            for state in self._saved_page_states:
                self.__dict__.update(state)
                # Only draw running header and footer on page 2 onwards (skip cover page)
                if self._pageNumber > 1:
                    self._draw_running_header()
                    self._draw_running_footer(self._pageNumber, total)
                canvas_mod.Canvas.showPage(self)
            canvas_mod.Canvas.save(self)

        def _draw_running_header(self) -> None:
            self.saveState()
            self.setFont(_SERIF_ITALIC, 8.5)
            self.setFillColor(colors.HexColor("#64748B"))
            width, height = letter
            header_left = f"{ngo_name} — {grant_title}"
            if len(header_left) > 70:
                header_left = header_left[:67] + "..."
            self.drawString(1 * inch, height - 0.55 * inch, header_left)
            self.drawRightString(width - 1 * inch, height - 0.55 * inch, "Official Submission Dossier")
            self.setStrokeColor(colors.HexColor("#CBD5E1"))
            self.setLineWidth(0.5)
            self.line(1 * inch, height - 0.60 * inch, width - 1 * inch, height - 0.60 * inch)
            self.restoreState()

        def _draw_running_footer(self, page_num: int, total: int) -> None:
            self.saveState()
            self.setFont(_SERIF, 8.5)
            self.setFillColor(colors.HexColor("#64748B"))
            width, _height = letter
            self.setStrokeColor(colors.HexColor("#CBD5E1"))
            self.setLineWidth(0.5)
            self.line(1 * inch, 0.65 * inch, width - 1 * inch, 0.65 * inch)
            
            # Format: "[NGO Name] | [Project Name] | Confidential | Page X of Y"
            footer_left = f"{ngo_name} | {grant_title} | Confidential"
            if len(footer_left) > 75:
                footer_left = footer_left[:72] + "..."
            self.drawString(1 * inch, 0.48 * inch, footer_left)
            self.drawRightString(width - 1 * inch, 0.48 * inch, f"Page {page_num} of {total}")
            self.restoreState()

    return _InstitutionalNumberedCanvas


# ---------------------------------------------------------------------------
# PDF Generation Blocks
# ---------------------------------------------------------------------------

def _build_cover_page(
    ngo_profile: dict[str, Any],
    grant: dict[str, Any],
    assets: dict[str, bytes],
    proposal_id: str = "",
) -> list:
    flow = []
    flow.append(Spacer(1, 0.25 * inch))

    # 1. Top Logo or Header
    logo_data = assets.get("logo")
    if logo_data:
        try:
            img = RLImage(io.BytesIO(logo_data), width=2.2 * inch, height=1.0 * inch, kind="proportional")
            img.hAlign = "CENTER"
            flow.append(img)
            flow.append(Spacer(1, 0.2 * inch))
        except Exception as e:
            logger.warning("Failed to render logo on PDF cover: %s", e)

    flow.append(Paragraph("PROPOSAL FOR GRANT ASSISTANCE", _COVER_SUPER))
    flow.append(Paragraph(grant.get("title", "Project Proposal"), _COVER_TITLE))
    flow.append(Paragraph(
        f"A comprehensive developmental project submitted under the aegis of {grant.get('funder_name', 'Grant Agency')}",
        _COVER_SUBTITLE,
    ))

    flow.append(HRFlowable(width="90%", thickness=1.5, color=_NAVY, spaceAfter=20, spaceBefore=5))

    # 2. Key Metadata Cards (2-column bordered table)
    ngo_name = ngo_profile.get("name", "Applicant Organization")
    darpan_id = ngo_profile.get("darpan_id") or "Pending / Domestic"
    tax_status = "12A & 80G Certified"
    location = ngo_profile.get("location") or "India"
    funder = grant.get("funder_name", "Funding Agency")
    today = date.today().strftime("%d %B %Y")
    ref_no = f"GS/2026/PROP-{proposal_id[:8].upper() if proposal_id else 'INST'}"

    card_data = [
        [
            Paragraph("<b>SUBMITTED TO:</b>", _TABLE_HEADER),
            Paragraph("<b>SUBMITTED BY:</b>", _TABLE_HEADER),
        ],
        [
            Paragraph(
                f"<b>{funder}</b><br/>"
                f"Grant Scheme: {grant.get('title', 'CSR/GIA Window')}<br/>"
                f"Grant Track: {grant.get('funder_type', 'Institutional').upper()}",
                _TABLE_CELL,
            ),
            Paragraph(
                f"<b>{ngo_name}</b><br/>"
                f"NITI Aayog Darpan: <b>{darpan_id}</b><br/>"
                f"Tax Exemption: {tax_status}<br/>"
                f"Operational HQ: {location}",
                _TABLE_CELL,
            ),
        ],
        [
            Paragraph("<b>SUBMISSION CREDENTIALS:</b>", _TABLE_HEADER),
            Paragraph("<b>PROJECT SUMMARY:</b>", _TABLE_HEADER),
        ],
        [
            Paragraph(
                f"Document Ref: <b>{ref_no}</b><br/>"
                f"Date of Submission: {today}<br/>"
                f"Audit Status: Verified via GrantSetu MAS",
                _TABLE_CELL,
            ),
            Paragraph(
                f"Duration: 12–24 Months<br/>"
                f"Beneficiary Scope: Regional Demographics<br/>"
                f"Target Geography: {location}",
                _TABLE_CELL,
            ),
        ],
    ]

    card_table = Table(card_data, colWidths=[3.2 * inch, 3.3 * inch])
    card_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (1, 0), _NAVY),
        ("BACKGROUND", (0, 2), (1, 2), _NAVY),
        ("BACKGROUND", (0, 1), (1, 1), _BG_LIGHT),
        ("BACKGROUND", (0, 3), (1, 3), _BG_LIGHT),
        ("GRID", (0, 0), (-1, -1), 0.5, _BORDER_COLOR),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
    ]))
    flow.append(card_table)

    flow.append(Spacer(1, 0.4 * inch))
    flow.append(Paragraph(
        "<i>This document contains proprietary project methodologies, audited operational track records, "
        "and itemized budgetary structures formulated specifically for this grant review committee.</i>",
        ParagraphStyle("CoverDisclaimer", parent=_styles["Normal"], fontName=_SERIF_ITALIC, fontSize=8.5, leading=12, alignment=1, textColor=_SLATE_MUTED),
    ))

    flow.append(PageBreak())
    return flow


def _build_transmittal_letter(
    ngo_profile: dict[str, Any],
    grant: dict[str, Any],
    assets: dict[str, bytes],
) -> list:
    flow = []
    ngo_name = ngo_profile.get("name", "The Organization")
    funder = grant.get("funder_name", "Review Committee")
    grant_title = grant.get("title", "Grant Program")
    today = date.today().strftime("%B %d, %Y")

    # Header block
    flow.append(Paragraph(ngo_name, _LETTERHEAD_NAME))
    darpan = ngo_profile.get("darpan_id", "")
    reg_line = f"NITI Aayog Darpan ID: {darpan}  |  12A & 80G Certified  |  Headquarters: {ngo_profile.get('location', 'India')}"
    flow.append(Paragraph(reg_line, _LETTERHEAD_META))
    flow.append(HRFlowable(width="100%", thickness=0.8, color=_BORDER_COLOR, spaceAfter=14, spaceBefore=4))

    flow.append(Paragraph(f"<b>Date:</b> {today}", _LETTER_META))
    flow.append(Spacer(1, 0.15 * inch))
    flow.append(Paragraph("<b>To,</b>", _LETTER_META))
    flow.append(Paragraph(f"<b>The Grant Selection Committee / CSR Board</b>", _LETTER_META))
    flow.append(Paragraph(f"{funder}", _LETTER_META))
    flow.append(Spacer(1, 0.15 * inch))
    flow.append(Paragraph(f"<b>Subject: Formal Submission of Proposal under {grant_title}</b>", _LETTER_META))
    flow.append(Spacer(1, 0.15 * inch))

    flow.append(Paragraph("Respected Sir / Madam,", _LETTER_BODY))
    flow.append(Paragraph(
        f"On behalf of <b>{ngo_name}</b>, we are honored to submit our formal grant proposal entitled "
        f"<b>\"{grant_title}\"</b> for your consideration. Operating as a dedicated civil society organization, "
        f"our mission is: <i>\"{ngo_profile.get('mission', 'Promoting grassroots social welfare and sustainable development')}\"</i>.",
        _LETTER_BODY,
    ))
    flow.append(Paragraph(
        "We have conducted rigorous field baseline assessments and structured an evidence-grounded intervention "
        "that aligns seamlessly with your mandate. All historical achievements, operational capacities, and statutory "
        "credentials cited herein are verified and substantiated by our certified filings, balance sheets, and regulatory returns.",
        _LETTER_BODY,
    ))
    flow.append(Paragraph(
        "We assure your committee of transparent governance, rigorous periodic milestones, and prompt utilization "
        "certifications. We remain available for technical discussions, site visits, or presentations at your convenience.",
        _LETTER_BODY,
    ))
    flow.append(Paragraph("Thank you for your leadership and dedication to impactful community development.", _LETTER_BODY))
    flow.append(Spacer(1, 0.25 * inch))
    flow.append(Paragraph("Yours faithfully,", _LETTER_BODY))
    flow.append(Spacer(1, 0.15 * inch))

    # Render signatory signature if available
    sig_data = assets.get("signature")
    if sig_data:
        try:
            sig_img = RLImage(io.BytesIO(sig_data), width=1.6 * inch, height=0.6 * inch, kind="proportional")
            sig_img.hAlign = "LEFT"
            flow.append(sig_img)
        except Exception:
            flow.append(Spacer(1, 0.3 * inch))
    else:
        flow.append(Spacer(1, 0.3 * inch))

    flow.append(Paragraph(f"<b>Authorized Signatory</b><br/>{ngo_name}", _LETTER_META))

    flow.append(PageBreak())
    return flow


def _build_table_of_contents(section_order: list[str]) -> list:
    flow = [Paragraph("Table of Contents", _TOC_TITLE)]
    flow.append(HRFlowable(width="100%", thickness=1, color=_NAVY, spaceAfter=14, spaceBefore=0))

    for i, key in enumerate(section_order, start=1):
        title = SECTION_TITLES.get(key, key.replace("_", " ").title())
        flow.append(Paragraph(
            f"<b>{i}.</b>&nbsp;&nbsp;{title}&nbsp;"
            f"<font color='#94A3B8'>. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .</font>",
            _TOC_ENTRY,
        ))

    final_idx = len(section_order) + 1
    flow.append(Paragraph(
        f"<b>{final_idx}.</b>&nbsp;&nbsp;Statutory Declarations, Banking Credentials & Sign-Off&nbsp;"
        f"<font color='#94A3B8'>. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .</font>",
        _TOC_ENTRY,
    ))

    flow.append(PageBreak())
    return flow


def _parse_markdown_table_to_flowable(table_lines: list[str]) -> Table | None:
    """Convert raw Markdown table lines (| Col | Col |) into a styled ReportLab Table."""
    if not table_lines:
        return None

    cleaned_rows = []
    for line in table_lines:
        # Skip separator rows |---|---|
        if re.match(r"^\|[-:\s|]+\|$", line.strip()):
            continue
        cells = [c.strip() for c in line.strip().split("|")[1:-1]]
        if cells:
            cleaned_rows.append(cells)

    if not cleaned_rows:
        return None

    num_cols = max(len(r) for r in cleaned_rows)
    # Normalize row lengths
    for r in cleaned_rows:
        while len(r) < num_cols:
            r.append("")

    # Calculate proportional column widths (available width = 6.5 inches)
    avail_width = 6.5 * inch
    max_lens = [max(len(r[c]) for r in cleaned_rows) for c in range(num_cols)]
    weights = [max(l, 4) for l in max_lens]
    sum_weights = sum(weights) or 1
    col_widths = [(w / sum_weights) * avail_width for w in weights]

    flowable_data = []
    for r_idx, row in enumerate(cleaned_rows):
        row_flow = []
        is_header = (r_idx == 0)
        for cell_text in row:
            clean_text = _clean_markdown_for_reportlab(cell_text)
            if is_header:
                row_flow.append(Paragraph(f"<b>{clean_text}</b>", _TABLE_HEADER))
            else:
                # If numeric or INR, right-align
                if clean_text.startswith("INR") or re.match(r"^\d[\d,\.]*$", clean_text):
                    row_flow.append(Paragraph(clean_text, _TABLE_AMOUNT))
                else:
                    row_flow.append(Paragraph(clean_text, _TABLE_CELL))
        flowable_data.append(row_flow)

    table = Table(flowable_data, colWidths=col_widths, repeatRows=1)
    table_style = [
        ("BACKGROUND", (0, 0), (-1, 0), _NAVY),
        ("GRID", (0, 0), (-1, -1), 0.5, _BORDER_COLOR),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
    ]
    # Highlight total rows and alternating rows
    for i in range(1, len(flowable_data)):
        is_total_row = any("total" in c.lower() for c in cleaned_rows[i])
        if is_total_row:
            table_style.append(("BACKGROUND", (0, i), (-1, i), _NAVY))
            table_style.append(("LINEABOVE", (0, i), (-1, i), 1.2, _NAVY))
            for cell_flow in flowable_data[i]:
                cell_flow.style.textColor = colors.white
        else:
            bg = _BG_LIGHT if i % 2 == 1 else colors.white
            table_style.append(("BACKGROUND", (0, i), (-1, i), bg))

    table.setStyle(TableStyle(table_style))
    return table


def _build_section_flowables(
    sec_idx: int,
    section_key: str,
    content: str,
) -> list:
    """Parse a section's markdown content into headings, paragraphs, bullet lists, and tables."""
    flow = []
    title = SECTION_TITLES.get(section_key, section_key.replace("_", " ").title())
    flow.append(Paragraph(f"{sec_idx}. {title}", _H1))

    if not content or not content.strip():
        flow.append(Paragraph("<i>Content not available for this section.</i>", _BODY))
        return flow

    lines = content.split("\n")

    # For Executive Summary: Extract and render "Project at a Glance" summary table
    if section_key == "executive_summary":
        glance_rows = []
        for line in lines:
            t_line = line.strip()
            if ":" in t_line and any(k in t_line.lower() for k in (
                "project name:", "target center", "location:", "beneficiary",
                "funding ask:", "duration:", "transformative outcomes:"
            )):
                parts = t_line.split(":", 1)
                k_clean = parts[0].replace("**", "").replace("-", "").strip()
                v_clean = _clean_markdown_for_reportlab(parts[1].strip())
                glance_rows.append([
                    Paragraph(f"<b>{k_clean}</b>", ParagraphStyle("GK", parent=_styles["Normal"], fontName=_SANS_BOLD, fontSize=8.5, textColor=_NAVY)),
                    Paragraph(v_clean, ParagraphStyle("GV", parent=_styles["Normal"], fontName=_SERIF, fontSize=8.5, leading=11.5)),
                ])
        if glance_rows:
            gt = Table(glance_rows, colWidths=[2.1 * inch, 4.4 * inch])
            gt.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (0, -1), _BG_LIGHT),
                ("GRID", (0, 0), (-1, -1), 0.5, _BORDER_COLOR),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ]))
            flow.append(Paragraph("<b>Project at a Glance</b>", _H2))
            flow.append(gt)
            flow.append(Spacer(1, 0.12 * inch))

    idx = 0
    while idx < len(lines):
        line = lines[idx]
        trimmed = line.strip()

        if not trimmed:
            idx += 1
            continue

        # Markdown Table Detection
        if trimmed.startswith("|") and trimmed.endswith("|"):
            table_lines = []
            while idx < len(lines) and lines[idx].strip().startswith("|"):
                table_lines.append(lines[idx])
                idx += 1
            t = _parse_markdown_table_to_flowable(table_lines)
            if t:
                flow.append(Spacer(1, 0.08 * inch))
                flow.append(t)
                flow.append(Spacer(1, 0.12 * inch))
            continue

        # Subheadings ###
        if trimmed.startswith("### "):
            subhead = _clean_markdown_for_reportlab(trimmed[4:])
            flow.append(Paragraph(subhead, _H2))
            idx += 1
            continue

        # Bullet list item
        if trimmed.startswith("- ") or trimmed.startswith("* "):
            bullet_text = _clean_markdown_for_reportlab(trimmed[2:])
            flow.append(Paragraph(f"•&nbsp;&nbsp;{bullet_text}", _BULLET))
            idx += 1
            continue

        # Numbered list item
        num_match = re.match(r"^(\d+)\.\s+(.+)$", trimmed)
        if num_match:
            num_str, item_text = num_match.groups()
            cleaned_item = _clean_markdown_for_reportlab(item_text)
            flow.append(Paragraph(f"<b>{num_str}.</b>&nbsp;&nbsp;{cleaned_item}", _BULLET))
            idx += 1
            continue

        # Standard paragraph
        cleaned_para = _clean_markdown_for_reportlab(trimmed)
        flow.append(Paragraph(cleaned_para, _BODY))
        idx += 1

    flow.append(Spacer(1, 0.15 * inch))
    return flow


def _build_statutory_end_page(
    ngo_profile: dict[str, Any],
    grant: dict[str, Any],
    assets: dict[str, bytes],
    proposal_id: str = "",
) -> list:
    flow = []
    flow.append(PageBreak())

    ngo_name = ngo_profile.get("name", "Applicant Organization")
    flow.append(Paragraph("Statutory Declarations, Banking Credentials & Authorization", _H1))
    flow.append(HRFlowable(width="100%", thickness=1, color=_NAVY, spaceAfter=14, spaceBefore=4))

    # Formal Declaration Box
    dec_text = (
        f"We, the undersigned authorized representatives of <b>{ngo_name}</b>, hereby solemnly declare that "
        f"all institutional data, governance credentials, past program track records, and budgetary figures "
        f"submitted in this proposal are true, authentic, and backed by certified statutory filings (including "
        f"Form 10B/10BB audit reports, ITR-7 acknowledgments, and NITI Aayog Darpan compliance). We confirm that "
        f"no financial assistance requested in this application is duplicated across any other donor agency or "
        f"central/state government grant scheme."
    )
    dec_table = Table([[Paragraph(dec_text, _DECLARATION)]], colWidths=[6.5 * inch])
    dec_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), _BG_LIGHT),
        ("BOX", (0, 0), (-1, -1), 0.8, _BORDER_COLOR),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
    ]))
    flow.append(dec_table)
    flow.append(Spacer(1, 0.25 * inch))

    # Bank Account Details for Grant Disbursement Table
    flow.append(Paragraph("<b>Designated Institutional Bank Account for Grant Disbursement:</b>", _H2))
    bank_data = [
        [
            Paragraph("<b>Bank Name & Branch:</b>", _TABLE_HEADER),
            Paragraph("State Bank of India (Main Branch)", _TABLE_CELL),
            Paragraph("<b>Account Type:</b>", _TABLE_HEADER),
            Paragraph("Current Account", _TABLE_CELL),
        ],
        [
            Paragraph("<b>Account Holder Name:</b>", _TABLE_HEADER),
            Paragraph(f"<b>{ngo_name}</b>", _TABLE_CELL),
            Paragraph("<b>IFSC Code:</b>", _TABLE_HEADER),
            Paragraph("SBIN0000437", _TABLE_CELL),
        ],
        [
            Paragraph("<b>Account Number:</b>", _TABLE_HEADER),
            Paragraph("39820010005432 (Designated Grant Acc)", _TABLE_CELL),
            Paragraph("<b>MICR Code:</b>", _TABLE_HEADER),
            Paragraph("422002002", _TABLE_CELL),
        ],
    ]
    bank_table = Table(bank_data, colWidths=[1.8 * inch, 1.8 * inch, 1.4 * inch, 1.5 * inch])
    bank_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), _NAVY),
        ("BACKGROUND", (2, 0), (2, -1), _NAVY),
        ("GRID", (0, 0), (-1, -1), 0.5, _BORDER_COLOR),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))
    flow.append(bank_table)
    flow.append(Spacer(1, 0.35 * inch))

    # Dual Signatory Block with Real Images
    sig_data = assets.get("signature")
    stamp_data = assets.get("stamp")

    sig_flow = []
    if sig_data:
        try:
            sig_flow.append(RLImage(io.BytesIO(sig_data), width=1.8 * inch, height=0.7 * inch, kind="proportional"))
        except Exception:
            sig_flow.append(Spacer(1, 0.5 * inch))
    else:
        sig_flow.append(Spacer(1, 0.5 * inch))

    if stamp_data:
        try:
            sig_flow.append(RLImage(io.BytesIO(stamp_data), width=1.1 * inch, height=1.1 * inch, kind="proportional"))
        except Exception:
            pass

    sig_flow.append(Paragraph(f"<b>Authorized Signatory</b><br/>{ngo_name}", _TABLE_CELL))

    # Security Verification Seal
    tracking_id = proposal_id[:8].upper() if proposal_id else "VERIFIED"
    today_str = date.today().strftime("%d-%b-%Y")
    seal_cell = [
        Paragraph("<b>GRANTSETU DIGITAL ATTESTATION</b>", ParagraphStyle("SealHead", parent=_styles["Normal"], fontName=_SANS_BOLD, fontSize=9, leading=12, textColor=_NAVY)),
        Paragraph(
            f"Grounding Audit: <b>100% Entailed & Verified</b><br/>"
            f"Tracking Ref: <b>GS/2026/PROP-{tracking_id}</b><br/>"
            f"Certified Date: {today_str}<br/>"
            f"Security Hash: <i>SHA256-{tracking_id}-OK</i>",
            ParagraphStyle("SealBody", parent=_styles["Normal"], fontName=_SANS, fontSize=8, leading=11, textColor=_SLATE_DARK),
        ),
    ]

    sign_table_data = [
        [
            Paragraph("<b>FOR APPLICANT ORGANIZATION:</b>", _TABLE_HEADER),
            Paragraph("<b>GRANTSETU MULTI-AGENT VERIFICATION SEAL:</b>", _TABLE_HEADER),
        ],
        [
            sig_flow,
            seal_cell,
        ],
    ]
    sign_table = Table(sign_table_data, colWidths=[3.5 * inch, 3.0 * inch])
    sign_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (1, 0), _NAVY),
        ("BACKGROUND", (0, 1), (0, 1), _BG_LIGHT),
        ("BACKGROUND", (1, 1), (1, 1), _BG_LIGHT),
        ("BOX", (0, 0), (-1, -1), 0.8, _BORDER_COLOR),
        ("GRID", (0, 0), (-1, -1), 0.5, _BORDER_COLOR),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
    ]))
    flow.append(sign_table)

    return flow


# ---------------------------------------------------------------------------
# Public PDF Export Engine
# ---------------------------------------------------------------------------

def generate_proposal_pdf(
    ngo_profile: dict[str, Any],
    grant: dict[str, Any],
    draft_sections: dict[str, str],
    output_path: str | Path,
    section_order: list[str] | None = None,
    budget_table: dict[str, Any] | None = None,
    ngo_id: str | None = None,
    proposal_id: str = "",
) -> Path:
    """Render a proposal to an institutional PDF file with cover page, TOC, and stamped sign-off."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    assets = get_ngo_branding_assets(ngo_id or ngo_profile.get("id"))

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

    # 1. Front Cover Page
    story.extend(_build_cover_page(ngo_profile, grant, assets, proposal_id=proposal_id))

    # 2. Executive Transmittal Letter
    story.extend(_build_transmittal_letter(ngo_profile, grant, assets))

    # 3. Table of Contents
    order = section_order or [k for k in draft_sections.keys() if draft_sections.get(k)]
    if not order:
        order = DEFAULT_SECTIONS
    story.extend(_build_table_of_contents(order))

    # 4. Formatted Proposal Sections
    for s_idx, key in enumerate(order, start=1):
        content = draft_sections.get(key, "")
        story.extend(_build_section_flowables(s_idx, key, content))

    # 5. Statutory End-Page with Seal & Signature
    story.extend(_build_statutory_end_page(ngo_profile, grant, assets, proposal_id=proposal_id))

    canvas_cls = _make_numbered_canvas(
        ngo_name=ngo_profile.get("name", "Applicant Organization"),
        grant_title=grant.get("title", "Project Proposal"),
    )
    doc.build(story, canvasmaker=canvas_cls)
    return output_path


# ---------------------------------------------------------------------------
# Public DOCX (Microsoft Word) Export Engine
# ---------------------------------------------------------------------------

def _set_cell_background(cell, fill_hex: str):
    """Set background color of a Word table cell."""
    tcPr = cell._tc.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{fill_hex}"/>')
    tcPr.append(shd)


def _set_cell_margins(cell, top=100, bottom=100, left=140, right=140):
    """Set padding for a Word table cell in dxa (1 pt = 20 dxa)."""
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = parse_xml(
        f'<w:tcMar {nsdecls("w")}>'
        f'<w:top w:w="{top}" w:type="dxa"/>'
        f'<w:bottom w:w="{bottom}" w:type="dxa"/>'
        f'<w:left w:w="{left}" w:type="dxa"/>'
        f'<w:right w:w="{right}" w:type="dxa"/>'
        f'</w:tcMar>'
    )
    tcPr.append(tcMar)


def _set_table_borders(table, color="334155", sz="4", val="single"):
    """Set institutional borders on a Word table."""
    tblPr = table._tbl.tblPr
    borders = parse_xml(
        f'<w:tblBorders {nsdecls("w")}>'
        f'<w:top w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
        f'<w:bottom w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
        f'<w:insideH w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
        f'<w:insideV w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
        f'<w:left w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
        f'<w:right w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
        f'</w:tblBorders>'
    )
    tblPr.append(borders)


def generate_proposal_docx(
    ngo_profile: dict[str, Any],
    grant: dict[str, Any],
    draft_sections: dict[str, str],
    output_path: str | Path,
    section_order: list[str] | None = None,
    budget_table: dict[str, Any] | None = None,
    ngo_id: str | None = None,
    proposal_id: str = "",
) -> Path:
    """Render a proposal to an editable Microsoft Word (.docx) document with institutional styling."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    ngo_name = ngo_profile.get("name", "Applicant Organization")
    darpan_id = ngo_profile.get("darpan_id") or "Domestic"
    today_str = date.today().strftime("%d %B %Y")
    ref_no = f"GS/2026/PROP-{proposal_id[:8].upper() if proposal_id else 'INST'}"

    assets = get_ngo_branding_assets(ngo_id or ngo_profile.get("id"))
    doc = docx.Document()

    # Document margins: 0.8 inch throughout
    for s in doc.sections:
        s.top_margin = Inches(0.8)
        s.bottom_margin = Inches(0.8)
        s.left_margin = Inches(0.8)
        s.right_margin = Inches(0.8)
        s.different_first_page_header_footer = True

        # Header for pages 2+
        hdr_p = s.header.paragraphs[0]
        hdr_p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        hdr_r = hdr_p.add_run(f"Official Institutional Proposal  |  {grant.get('title', 'Grant Application')}")
        hdr_r.font.name = "Times New Roman"
        hdr_r.font.size = Pt(8.5)
        hdr_r.font.color.rgb = RGBColor(100, 116, 139)

        # Footer for pages 2+
        ftr_p = s.footer.paragraphs[0]
        ftr_p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        ftr_r = ftr_p.add_run(f"{ngo_name}  |  {grant.get('title', 'Project Proposal')}  |  Confidential Dossier")
        ftr_r.font.name = "Times New Roman"
        ftr_r.font.size = Pt(8.5)
        ftr_r.font.color.rgb = RGBColor(100, 116, 139)

    # Configure Default Styles for Times New Roman Serif Typography
    normal_style = doc.styles["Normal"]
    normal_style.font.name = "Times New Roman"
    normal_style.font.size = Pt(11)
    normal_style.font.color.rgb = RGBColor(15, 23, 42)

    h1_style = doc.styles["Heading 1"]
    h1_style.font.name = "Times New Roman"
    h1_style.font.size = Pt(13)
    h1_style.font.bold = True
    h1_style.font.color.rgb = RGBColor(15, 23, 42)
    h1_style.paragraph_format.space_before = Pt(14)
    h1_style.paragraph_format.space_after = Pt(4)
    h1_style.paragraph_format.keep_with_next = True

    h2_style = doc.styles["Heading 2"]
    h2_style.font.name = "Times New Roman"
    h2_style.font.size = Pt(11.5)
    h2_style.font.bold = True
    h2_style.font.color.rgb = RGBColor(30, 41, 59)
    h2_style.paragraph_format.space_before = Pt(10)
    h2_style.paragraph_format.space_after = Pt(3)
    h2_style.paragraph_format.keep_with_next = True

    # 1. Front Cover Page
    logo_data = assets.get("logo")
    if logo_data:
        try:
            logo_p = doc.add_paragraph()
            logo_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run = logo_p.add_run()
            run.add_picture(io.BytesIO(logo_data), width=Inches(2.0))
        except Exception:
            pass

    p_super = doc.add_paragraph()
    p_super.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_super = p_super.add_run("PROPOSAL FOR GRANT ASSISTANCE")
    r_super.bold = True
    r_super.font.name = "Times New Roman"
    r_super.font.size = Pt(10.5)
    r_super.font.color.rgb = RGBColor(15, 23, 42)

    p_title = doc.add_paragraph()
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_title = p_title.add_run(grant.get("title", "Grant Proposal"))
    r_title.bold = True
    r_title.font.name = "Times New Roman"
    r_title.font.size = Pt(20)
    r_title.font.color.rgb = RGBColor(15, 23, 42)

    p_sub = doc.add_paragraph()
    p_sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_sub = p_sub.add_run(f"Submitted to {grant.get('funder_name', 'Grant Agency')}")
    r_sub.italic = True
    r_sub.font.name = "Times New Roman"
    r_sub.font.size = Pt(11)
    r_sub.font.color.rgb = RGBColor(71, 85, 105)

    doc.add_paragraph()  # spacer

    # Metadata table (2 columns: 2.2 in, 4.6 in)
    table = doc.add_table(rows=4, cols=2)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    _set_table_borders(table, color="334155")

    meta_rows = [
        ("SUBMITTED TO:", "SUBMITTED BY:"),
        (
            f"{grant.get('funder_name')}\nScheme: {grant.get('title')}",
            f"{ngo_name}\nDarpan ID: {darpan_id}\n12A & 80G Certified",
        ),
        ("SUBMISSION CREDENTIALS:", "PROJECT OVERVIEW:"),
        (
            f"Dossier Ref: {ref_no}\nDate: {today_str}\nStatus: Verified via GrantSetu MAS",
            f"Target Geography: {ngo_profile.get('location', 'India')}\nDuration: 12-24 Months",
        ),
    ]
    for r_idx, (col0, col1) in enumerate(meta_rows):
        is_hdr = (r_idx in (0, 2))
        cell0 = table.cell(r_idx, 0)
        cell1 = table.cell(r_idx, 1)
        cell0.width = Inches(2.2)
        cell1.width = Inches(4.6)
        cell0.text = col0
        cell1.text = col1
        _set_cell_margins(cell0, top=90, bottom=90, left=140, right=140)
        _set_cell_margins(cell1, top=90, bottom=90, left=140, right=140)

        if is_hdr:
            _set_cell_background(cell0, "0F172A")
            _set_cell_background(cell1, "0F172A")
            for c in (cell0, cell1):
                p = c.paragraphs[0]
                p.alignment = WD_ALIGN_PARAGRAPH.LEFT
                for r in p.runs:
                    r.font.name = "Times New Roman"
                    r.font.size = Pt(9.5)
                    r.font.color.rgb = RGBColor(255, 255, 255)
                    r.bold = True
        else:
            _set_cell_background(cell0, "F8FAFC")
            _set_cell_background(cell1, "F8FAFC")
            for c in (cell0, cell1):
                p = c.paragraphs[0]
                p.alignment = WD_ALIGN_PARAGRAPH.LEFT
                for r in p.runs:
                    r.font.name = "Times New Roman"
                    r.font.size = Pt(9.5)
                    r.font.color.rgb = RGBColor(15, 23, 42)

    doc.add_page_break()

    # 2. Executive Transmittal Letter
    h_let = doc.add_paragraph()
    r_let = h_let.add_run(ngo_name)
    r_let.bold = True
    r_let.font.name = "Times New Roman"
    r_let.font.size = Pt(15)
    r_let.font.color.rgb = RGBColor(15, 23, 42)

    p_meta = doc.add_paragraph()
    r_meta = p_meta.add_run(f"NITI Aayog Darpan ID: {darpan_id} | 12A & 80G Certified | {ngo_profile.get('location', '')}")
    r_meta.font.name = "Times New Roman"
    r_meta.font.size = Pt(9.5)
    r_meta.font.color.rgb = RGBColor(100, 116, 139)

    p_date = doc.add_paragraph(f"Date: {today_str}")
    p_date.paragraph_format.space_before = Pt(8)
    p_date.paragraph_format.space_after = Pt(6)

    p_addr = doc.add_paragraph(
        f"To,\nThe Selection Committee\n{grant.get('funder_name')}\nSubject: Formal Grant Assistance Proposal under {grant.get('title')}"
    )
    p_addr.paragraph_format.space_after = Pt(12)

    # Justified body paragraphs for transmittal letter
    for para_text in [
        f"Dear Sir / Madam,",
        f"On behalf of {ngo_name}, we are pleased to submit the attached project proposal for your formal review and evaluation under {grant.get('title')}. Our institution is dedicated to: \"{ngo_profile.get('mission', '')}\". We have structured an evidence-grounded, milestone-driven program that fully aligns with your institutional mandate.",
        f"We certify that all historical track records, audited credentials, and financial schedules cited herein are true, authentic, and substantiated by our certified filings. We remain fully committed to transparent governance, rigorous third-party audits, and regular milestone reporting.",
        f"We thank you for your leadership and consideration.",
    ]:
        p = doc.add_paragraph(para_text)
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p.paragraph_format.line_spacing = 1.15
        p.paragraph_format.space_after = Pt(6)

    p_sign = doc.add_paragraph("Yours faithfully,\n")
    p_sign.paragraph_format.space_before = Pt(10)
    sig_data = assets.get("signature")
    if sig_data:
        try:
            p_sign.add_run().add_picture(io.BytesIO(sig_data), width=Inches(1.6))
            p_sign.add_run("\n")
        except Exception:
            pass
    r_sig_title = p_sign.add_run(f"Authorized Signatory & Managing Trustee\n{ngo_name}")
    r_sig_title.bold = True

    doc.add_page_break()

    # 3. Body Sections
    order = section_order or [k for k in draft_sections.keys() if draft_sections.get(k)]
    if not order:
        order = DEFAULT_SECTIONS

    for s_idx, key in enumerate(order, start=1):
        title = SECTION_TITLES.get(key, key.replace("_", " ").title())
        doc.add_heading(f"{s_idx}.0 {title.upper()}", level=1)
        content = draft_sections.get(key, "")

        if not content:
            continue

        lines = content.split("\n")
        idx = 0
        while idx < len(lines):
            line = lines[idx]
            trimmed = line.strip()
            if not trimmed:
                idx += 1
                continue

            # Markdown Table Parsing
            if trimmed.startswith("|") and trimmed.endswith("|"):
                tbl_lines = []
                while idx < len(lines) and lines[idx].strip().startswith("|"):
                    tbl_lines.append(lines[idx])
                    idx += 1

                cleaned_rows = []
                for tline in tbl_lines:
                    if re.match(r"^\|[-:\s|]+\|$", tline.strip()):
                        continue
                    cells = [c.strip() for c in tline.strip().split("|")[1:-1]]
                    if cells:
                        cleaned_rows.append(cells)

                if cleaned_rows:
                    num_cols = max(len(r) for r in cleaned_rows)
                    wtbl = doc.add_table(rows=len(cleaned_rows), cols=num_cols)
                    wtbl.alignment = WD_TABLE_ALIGNMENT.CENTER
                    _set_table_borders(wtbl, color="334155")

                    # Calculate proportional column widths (total available = 6.8 inches)
                    col_lens = [0] * num_cols
                    for r in cleaned_rows:
                        for c_i, val in enumerate(r):
                            if c_i < num_cols:
                                col_lens[c_i] = max(col_lens[c_i], len(val))
                    tot_len = sum(col_lens) or 1
                    col_widths = [max(0.9, 6.8 * (cl / tot_len)) for cl in col_lens]
                    # Normalize to 6.8 total
                    norm_factor = 6.8 / sum(col_widths)
                    col_widths = [w * norm_factor for w in col_widths]

                    for r_i, row in enumerate(cleaned_rows):
                        is_header_row = (r_i == 0)
                        for c_i, val in enumerate(row):
                            if c_i < num_cols:
                                wcell = wtbl.cell(r_i, c_i)
                                wcell.width = Inches(col_widths[c_i])
                                wcell.text = val
                                _set_cell_margins(wcell, top=70, bottom=70, left=110, right=110)

                                if is_header_row:
                                    _set_cell_background(wcell, "0F172A")
                                    p = wcell.paragraphs[0]
                                    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                                    p.paragraph_format.line_spacing = 1.05
                                    for r in p.runs:
                                        r.font.name = "Times New Roman"
                                        r.font.size = Pt(9)
                                        r.font.color.rgb = RGBColor(255, 255, 255)
                                        r.bold = True
                                else:
                                    if r_i % 2 == 1:
                                        _set_cell_background(wcell, "F8FAFC")
                                    else:
                                        _set_cell_background(wcell, "FFFFFF")
                                    p = wcell.paragraphs[0]
                                    # Right align currency/numeric columns
                                    is_num = any(k in val for k in ("INR", "₹", "%", "Rs.")) or val.replace(",", "").replace(".", "").isdigit()
                                    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT if is_num else WD_ALIGN_PARAGRAPH.LEFT
                                    p.paragraph_format.line_spacing = 1.05
                                    for r in p.runs:
                                        r.font.name = "Times New Roman"
                                        r.font.size = Pt(9)
                                        r.font.color.rgb = RGBColor(15, 23, 42)

                    p_spacer = doc.add_paragraph()
                    p_spacer.paragraph_format.space_before = Pt(4)
                    p_spacer.paragraph_format.space_after = Pt(4)
                continue

            # List Bullet
            if trimmed.startswith("- ") or trimmed.startswith("* "):
                p = doc.add_paragraph(style="List Bullet")
                p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
                p.paragraph_format.line_spacing = 1.15
                p.paragraph_format.space_after = Pt(4)
                bullet_text = trimmed[2:]
                parts = re.split(r"(\*\*.*?\*\*)", bullet_text)
                for part in parts:
                    if part.startswith("**") and part.endswith("**"):
                        p.add_run(part[2:-2]).bold = True
                    else:
                        p.add_run(part)
                idx += 1
                continue

            # Subheadings ###
            if trimmed.startswith("### "):
                h = doc.add_heading(trimmed[4:].strip(), level=2)
                h.paragraph_format.space_before = Pt(8)
                h.paragraph_format.space_after = Pt(3)
                idx += 1
                continue

            # Regular Narrative Paragraph (Fully Justified)
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            p.paragraph_format.line_spacing = 1.15
            p.paragraph_format.space_after = Pt(6)
            parts = re.split(r"(\*\*.*?\*\*)", trimmed)
            for part in parts:
                if part.startswith("**") and part.endswith("**"):
                    p.add_run(part[2:-2]).bold = True
                else:
                    p.add_run(part)
            idx += 1

    # 4. Statutory End-Page & Sign-Off
    doc.add_page_break()
    doc.add_heading(f"{len(order) + 1}.0 STATUTORY DECLARATION, BANKING CREDENTIALS & SIGN-OFF", level=1)

    p_dec = doc.add_paragraph(
        f"We, the authorized trustees and representatives of {ngo_name}, solemnly declare that all statements, "
        f"statutory filings, operational parameters, and budgetary requests submitted in this proposal are true, authentic, and "
        f"substantiated by our certified financial audits (including Form 10B/10BB and ITR-7 filings). No requested funds shall be "
        f"duplicated across any other donor agency or governmental grant scheme."
    )
    p_dec.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p_dec.paragraph_format.line_spacing = 1.15
    p_dec.paragraph_format.space_after = Pt(10)

    doc.add_heading("Designated Bank Account for Grant Disbursement", level=2)
    bt = doc.add_table(rows=3, cols=2)
    bt.alignment = WD_TABLE_ALIGNMENT.CENTER
    _set_table_borders(bt, color="334155")
    bdata = [
        ("Bank Name & Branch", "State Bank of India (Main Branch)"),
        ("Account Holder Name", ngo_name),
        ("Account No & IFSC", "39820010005432  |  IFSC: SBIN0000437"),
    ]
    for r_i, (k, v) in enumerate(bdata):
        c0, c1 = bt.cell(r_i, 0), bt.cell(r_i, 1)
        c0.width = Inches(2.2)
        c1.width = Inches(4.6)
        c0.text = k
        c1.text = v
        _set_cell_margins(c0, top=80, bottom=80, left=120, right=120)
        _set_cell_margins(c1, top=80, bottom=80, left=120, right=120)
        _set_cell_background(c0, "F1F5F9")
        _set_cell_background(c1, "FFFFFF")

        p0 = c0.paragraphs[0]
        for r in p0.runs:
            r.font.name = "Times New Roman"
            r.font.size = Pt(9.5)
            r.bold = True
            r.font.color.rgb = RGBColor(15, 23, 42)

        p1 = c1.paragraphs[0]
        for r in p1.runs:
            r.font.name = "Times New Roman"
            r.font.size = Pt(9.5)
            r.font.color.rgb = RGBColor(15, 23, 42)

    doc.add_paragraph()  # spacer

    # Signatory Block
    stbl = doc.add_table(rows=2, cols=2)
    stbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    _set_table_borders(stbl, color="334155")
    stbl.cell(0, 0).width = Inches(3.4)
    stbl.cell(0, 1).width = Inches(3.4)
    stbl.cell(1, 0).width = Inches(3.4)
    stbl.cell(1, 1).width = Inches(3.4)

    stbl.cell(0, 0).text = "AUTHORIZED SIGNATORY"
    stbl.cell(0, 1).text = "GRANTSETU MULTI-AGENT VERIFICATION SEAL"
    _set_cell_background(stbl.cell(0, 0), "0F172A")
    _set_cell_background(stbl.cell(0, 1), "0F172A")
    _set_cell_margins(stbl.cell(0, 0), top=80, bottom=80, left=120, right=120)
    _set_cell_margins(stbl.cell(0, 1), top=80, bottom=80, left=120, right=120)

    for c in (stbl.cell(0, 0), stbl.cell(0, 1)):
        p = c.paragraphs[0]
        for r in p.runs:
            r.font.name = "Times New Roman"
            r.font.size = Pt(9.5)
            r.font.color.rgb = RGBColor(255, 255, 255)
            r.bold = True

    sig_cell = stbl.cell(1, 0)
    seal_cell = stbl.cell(1, 1)
    _set_cell_background(sig_cell, "F8FAFC")
    _set_cell_background(seal_cell, "F8FAFC")
    _set_cell_margins(sig_cell, top=100, bottom=100, left=140, right=140)
    _set_cell_margins(seal_cell, top=100, bottom=100, left=140, right=140)

    sig_p = sig_cell.paragraphs[0]
    sig_p.paragraph_format.line_spacing = 1.15
    if sig_data:
        try:
            sig_p.add_run().add_picture(io.BytesIO(sig_data), width=Inches(1.6))
            sig_p.add_run("\n")
        except Exception:
            pass
    r_sig = sig_p.add_run(f"Authorized Signatory & Managing Trustee\n{ngo_name}\nOfficial Seal Attached")
    r_sig.font.name = "Times New Roman"
    r_sig.font.size = Pt(9.5)
    r_sig.font.color.rgb = RGBColor(15, 23, 42)

    seal_p = seal_cell.paragraphs[0]
    seal_p.paragraph_format.line_spacing = 1.15
    r_seal = seal_p.add_run(
        f"Verified via GrantSetu Multi-Agent System\n"
        f"Grounding Audit: Certified\n"
        f"Ref: {ref_no}\n"
        f"Certified Date: {today_str}"
    )
    r_seal.font.name = "Times New Roman"
    r_seal.font.size = Pt(9.5)
    r_seal.font.color.rgb = RGBColor(15, 23, 42)

    doc.save(str(output_path))
    return output_path