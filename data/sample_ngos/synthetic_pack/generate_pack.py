"""Generate the synthetic NGO document pack.

    python generate_pack.py            # (re)creates the three NGO folders here

Needs: reportlab, pillow, numpy.  Output is deterministic (seeded), so re-running
gives identical files. EVERYTHING GENERATED IS FICTIONAL TEST DATA.
"""

from __future__ import annotations

import json
import math
import random
import zlib
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (KeepTogether, PageBreak, Paragraph, SimpleDocTemplate,
                                Spacer, Table, TableStyle)

from ngo_data import AY, FY, NEXT_FY, NGOS, PRIOR_FY

OUT = Path(__file__).resolve().parent
FOOTER = ("SYNTHETIC DOCUMENT - generated for GrantSetu testing. Fictional organisation; "
          "not a real statutory filing.")


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def inr(n: float) -> str:
    """Indian digit grouping: 12345678 -> 'Rs. 1,23,45,678'."""
    n = int(round(n))
    sign = "-" if n < 0 else ""
    s = str(abs(n))
    if len(s) > 3:
        head, tail = s[:-3], s[-3:]
        parts = []
        while len(head) > 2:
            parts.insert(0, head[-2:])
            head = head[:-2]
        if head:
            parts.insert(0, head)
        s = ",".join(parts) + "," + tail
    return f"{sign}Rs. {s}"


def num(n: float) -> str:
    return inr(n).replace("Rs. ", "")


def split_int(total: int, shares: list[float]) -> list[int]:
    """Split `total` by `shares`, fixing rounding so the parts sum exactly."""
    parts = [int(round(total * s)) for s in shares]
    parts[-1] += total - sum(parts)
    return parts


def round_k(n: float) -> int:
    return int(round(n / 1000.0) * 1000)


_ss = getSampleStyleSheet()
H1 = ParagraphStyle("H1", parent=_ss["Heading1"], fontSize=17, spaceAfter=4, leading=21)
H2 = ParagraphStyle("H2", parent=_ss["Heading2"], fontSize=12.5, spaceBefore=10, spaceAfter=4)
BODY = ParagraphStyle("B", parent=_ss["BodyText"], fontSize=9.6, leading=13.5)
SMALL = ParagraphStyle("S", parent=BODY, fontSize=8.2, leading=11, textColor=colors.HexColor("#555555"))
CENTER = ParagraphStyle("C", parent=BODY, alignment=1)
TITLE_C = ParagraphStyle("TC", parent=H1, alignment=1, fontSize=15)


def P(text, style=BODY):
    return Paragraph(text, style)


def table(rows, col_widths=None, header=True, bold_last=False, accent="#2b4a8b", align_right_from=1):
    t = Table(rows, colWidths=col_widths, repeatRows=1 if header else 0)
    style = [
        ("FONT", (0, 0), (-1, -1), "Helvetica", 8.8),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#b8b8b8")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3.2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3.2),
        ("ALIGN", (align_right_from, 0), (-1, -1), "RIGHT"),
    ]
    if header:
        style += [("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(accent)),
                  ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                  ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 8.8)]
    if bold_last:
        style += [("FONT", (0, -1), (-1, -1), "Helvetica-Bold", 8.8),
                  ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#eef1f7"))]
    t.setStyle(TableStyle(style))
    return t


def kv_table(rows, w=(55 * mm, 110 * mm)):
    t = Table(rows, colWidths=list(w))
    t.setStyle(TableStyle([
        ("FONT", (0, 0), (0, -1), "Helvetica-Bold", 9.4),
        ("FONT", (1, 0), (1, -1), "Helvetica", 9.4),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LINEBELOW", (0, 0), (-1, -1), 0.3, colors.HexColor("#d0d0d0")),
        ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return t


def build_pdf(path: Path, story: list, title: str, ngo: dict):
    path.parent.mkdir(parents=True, exist_ok=True)

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(colors.HexColor("#8a8a8a"))
        canvas.drawCentredString(A4[0] / 2, 10 * mm, FOOTER)
        canvas.drawRightString(A4[0] - 18 * mm, 15 * mm, f"{ngo['name']}  |  page {doc.page}")
        canvas.restoreState()

    doc = SimpleDocTemplate(str(path), pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm,
                            topMargin=16 * mm, bottomMargin=22 * mm, title=title,
                            author=ngo["name"])
    doc.build(story, onFirstPage=footer, onLaterPages=footer)


def letterhead(ngo, doc_title, subtitle=None):
    c = colors.Color(*[v / 255 for v in ngo["palette"][0]])
    head = Table([[P(f"<b>{ngo['name'].upper()}</b>", ParagraphStyle("lh", parent=CENTER, fontSize=14, textColor=c))],
                  [P(ngo["address"], ParagraphStyle("lh2", parent=CENTER, fontSize=8.5))]],
                 colWidths=[174 * mm])
    head.setStyle(TableStyle([("LINEBELOW", (0, -1), (-1, -1), 1.2, c), ("BOTTOMPADDING", (0, -1), (-1, -1), 6)]))
    out = [head, Spacer(1, 8), P(f"<b>{doc_title}</b>", TITLE_C)]
    if subtitle:
        out.append(P(subtitle, CENTER))
    out.append(Spacer(1, 8))
    return out


# ---------------------------------------------------------------------------
# finance model (single source of truth per NGO)
# ---------------------------------------------------------------------------
def finance(n: dict) -> dict:
    inc = dict(n["income"])
    income_total = sum(inc.values())
    prior_inc = {k: round_k(v / n["growth"]) for k, v in inc.items()}
    prior_income_total = sum(prior_inc.values())

    surplus = round_k(income_total * n["surplus_pct"])
    expenses = income_total - surplus
    fund_exp = round_k(expenses * n["fundraising_share"])
    admin_exp = round_k(expenses * n["admin_share"])
    prog_total = expenses - fund_exp - admin_exp

    def split_k(total, shares):
        parts = [round_k(total * sh) for sh in shares[:-1]]
        parts.append(total - sum(parts))
        return parts

    prog_parts = split_k(prog_total, [p["share"] for p in n["programmes"]])

    prior_surplus = round_k(prior_income_total * (n["surplus_pct"] - 0.005))
    prior_expenses = prior_income_total - prior_surplus
    prior_admin = round_k(admin_exp / n["growth"])
    prior_fund = round_k(fund_exp / n["growth"])
    prior_prog_total = prior_expenses - prior_admin - prior_fund
    prior_prog_parts = split_k(prior_prog_total, [p["share"] for p in n["programmes"]])

    b = n["bs"]
    general_fy25 = b["general_fy25"]
    general_fy26 = general_fy25 + surplus
    liab_total = b["corpus"] + general_fy26 + b["restricted"] + b["liab"]
    invest = liab_total - b["fixed"] - b["receivables"] - b["cash"]
    assert invest > 0, f"{n['slug']}: investments plug is negative"

    # prior-year balance sheet (a simple, balanced earlier snapshot)
    p_restricted = round_k(b["restricted"] * 0.9)
    p_liab = round_k(b["liab"] * 0.92)
    p_general = general_fy25
    p_total = b["corpus"] + p_general + p_restricted + p_liab
    p_fixed = round_k(b["fixed"] * 1.06)
    p_recv = round_k(b["receivables"] * 0.9)
    p_cash = round_k(b["cash"] * 0.85)
    p_invest = p_total - p_fixed - p_recv - p_cash
    assert p_invest > 0

    return dict(
        inc=inc, prior_inc=prior_inc, income_total=income_total, prior_income_total=prior_income_total,
        surplus=surplus, expenses=expenses, fund_exp=fund_exp, admin_exp=admin_exp,
        prog_total=prog_total, prog_parts=prog_parts,
        prior_surplus=prior_surplus, prior_expenses=prior_expenses, prior_prog_parts=prior_prog_parts,
        prior_admin=prior_admin, prior_fund=prior_fund,
        general_fy26=general_fy26, liab_total=liab_total, invest=invest,
        p=dict(restricted=p_restricted, liab=p_liab, general=p_general, total=p_total,
               fixed=p_fixed, recv=p_recv, cash=p_cash, invest=p_invest),
        prog_pct=round(100 * prog_total / expenses, 1),
    )


# ---------------------------------------------------------------------------
# 1. statutory documents
# ---------------------------------------------------------------------------
def doc_darpan(n, fin, path):
    s = letterhead(n, "NGO DARPAN - REGISTRATION CERTIFICATE", "NITI Aayog, Government of India (synthetic sample)")
    s.append(kv_table([
        ["Unique ID", f"<b>{n['darpan']}</b>"],
        ["Name of NGO", n["name"]],
        ["Registered under", n["reg_act"]],
        ["Registration number", n["reg_no"]],
        ["Date of registration", n["inc_date"]],
        ["PAN of organisation", n["pan"]],
        ["Registered address", n["address"]],
        ["State / District", f"{n['state']} / {n['district']}"],
        ["Key issues", ", ".join(n["sectors"])],
        ["Authorised signatory", f"{n['signatory'][0]}, {n['signatory'][1]}"],
        ["Certificate generated on", "05 January 2026"],
    ]))
    s += [Spacer(1, 10), P("This certificate confirms that the organisation named above is enrolled on the "
                           "NGO Darpan portal with the Unique ID shown. The Unique ID is required for applying to "
                           "grants-in-aid schemes of the Central Government.", BODY)]
    build_pdf(path, s, "Darpan Certificate", n)


def doc_12a(n, fin, path):
    no, dt, valid = n["reg12a"]
    s = letterhead(n, "REGISTRATION UNDER SECTION 12AB - ORDER", "Income Tax Department (synthetic sample)")
    s.append(kv_table([
        ["Provisional / final registration no.", f"<b>{no}</b>"],
        ["Name of trust / society", n["name"]],
        ["PAN", n["pan"]],
        ["Date of order", dt],
        ["Section", "12A read with 12AB of the Income-tax Act, 1961"],
        ["Period of validity", valid],
        ["Status", "Registered - charitable purpose"],
    ]))
    s += [Spacer(1, 10), P("The application for registration filed by the organisation has been examined. It is "
                           "satisfied that the objects are charitable and the activities are genuine. The "
                           "organisation is registered under section 12AB for the period stated above.", BODY)]
    build_pdf(path, s, "12A Certificate", n)


def doc_80g(n, fin, path):
    no, dt, valid = n["reg80g"]
    s = letterhead(n, "APPROVAL UNDER SECTION 80G(5) - ORDER", "Income Tax Department (synthetic sample)")
    s.append(kv_table([
        ["Approval number", f"<b>{no}</b>"],
        ["Name of trust / society", n["name"]],
        ["PAN", n["pan"]],
        ["Date of order", dt],
        ["Validity", valid],
        ["Donor deduction", "50% of the donation, subject to the qualifying limit under section 80G"],
    ]))
    s += [Spacer(1, 10), P("Donations made to the organisation during the period of validity qualify for deduction "
                           "in the hands of the donor as per section 80G, subject to the provisions of the Act.", BODY)]
    build_pdf(path, s, "80G Certificate", n)


def doc_fcra(n, fin, path):
    no, dt, valid_text, _ = n["fcra"]
    s = letterhead(n, "CERTIFICATE OF REGISTRATION - FCRA, 2010", "Ministry of Home Affairs, Government of India (synthetic sample)")
    s.append(kv_table([
        ["Registration number", f"<b>{no}</b>"],
        ["Name of association", n["name"]],
        ["Date of registration", dt],
        ["Valid up to", valid_text],
        ["Nature", "Registration to receive foreign contribution (social and medical purposes)"],
        ["Designated FCRA account", "State Bank of India, New Delhi Main Branch (FCRA account)"],
    ]))
    s += [Spacer(1, 10), P("The association is permitted to receive foreign contribution for the stated purposes "
                           "subject to the conditions of the Foreign Contribution (Regulation) Act, 2010 and Rules.", BODY)]
    build_pdf(path, s, "FCRA Certificate", n)


def doc_csr1(n, fin, path):
    no, dt = n["csr1"]
    s = letterhead(n, "FORM CSR-1 - REGISTRATION ACKNOWLEDGEMENT", "Ministry of Corporate Affairs (synthetic sample)")
    s.append(kv_table([
        ["CSR Registration Number", f"<b>{no}</b>"],
        ["Name of entity", n["name"]],
        ["PAN", n["pan"]],
        ["Date of registration", dt],
        ["Entity type", "Registered trust / society under section 8 of the Companies Act equivalence (12A and 80G holder)"],
        ["Areas of work", ", ".join(n["sectors"])],
        ["Authorised signatory (e-form)", f"{n['signatory'][0]}, {n['signatory'][1]}"],
    ]))
    s += [Spacer(1, 10), P("The entity has filed Form CSR-1 and is eligible to be considered by companies for "
                           "implementation of Corporate Social Responsibility projects.", BODY)]
    build_pdf(path, s, "CSR-1 Registration", n)


# ---------------------------------------------------------------------------
# 2. financial documents
# ---------------------------------------------------------------------------
def doc_balance_sheet(n, fin, path):
    b, p = n["bs"], fin["p"]
    cw = [96 * mm, 38 * mm, 38 * mm]
    s = letterhead(n, f"AUDITED FINANCIAL STATEMENTS - FY {FY}", f"Year ended 31 March 2026 (comparative: FY {PRIOR_FY})")
    s.append(P("<b>1. Balance Sheet as at 31 March 2026</b> (amounts in Rs.)", H2))
    liab_rows = [["FUNDS AND LIABILITIES", "31-Mar-2026", "31-Mar-2025"],
                 ["Corpus fund", num(b["corpus"]), num(b["corpus"])],
                 ["General fund (opening + surplus for the year)", num(fin["general_fy26"]), num(p["general"])],
                 ["Restricted / earmarked project funds", num(b["restricted"]), num(p["restricted"])],
                 ["Current liabilities and provisions", num(b["liab"]), num(p["liab"])],
                 ["TOTAL", num(fin["liab_total"]), num(p["total"])]]
    s.append(table(liab_rows, cw, bold_last=True))
    s.append(Spacer(1, 6))
    asset_rows = [["ASSETS", "31-Mar-2026", "31-Mar-2025"],
                  ["Fixed assets (net of depreciation)", num(b["fixed"]), num(p["fixed"])],
                  ["Investments (fixed deposits)", num(fin["invest"]), num(p["invest"])],
                  ["Receivables and advances", num(b["receivables"]), num(p["recv"])],
                  ["Cash and bank balances", num(b["cash"]), num(p["cash"])],
                  ["TOTAL", num(fin["liab_total"]), num(p["total"])]]
    s.append(table(asset_rows, cw, bold_last=True))

    s.append(P(f"<b>2. Income and Expenditure Account for FY {FY}</b> (amounts in Rs.)", H2))
    inc_rows = [["INCOME", f"FY {FY}", f"FY {PRIOR_FY}"]]
    for k, v in fin["inc"].items():
        inc_rows.append([k, num(v), num(fin["prior_inc"][k])])
    inc_rows.append(["TOTAL INCOME", num(fin["income_total"]), num(fin["prior_income_total"])])
    s.append(table(inc_rows, cw, bold_last=True))
    s.append(Spacer(1, 6))
    exp_rows = [["EXPENDITURE", f"FY {FY}", f"FY {PRIOR_FY}"]]
    for prog, cur, prv in zip(n["programmes"], fin["prog_parts"], fin["prior_prog_parts"]):
        exp_rows.append([f"Programme: {prog['name']}", num(cur), num(prv)])
    exp_rows += [["Administration and overheads", num(fin["admin_exp"]), num(fin["prior_admin"])],
                 ["Fundraising and communications", num(fin["fund_exp"]), num(fin["prior_fund"])],
                 ["TOTAL EXPENDITURE", num(fin["expenses"]), num(fin["prior_expenses"])],
                 ["SURPLUS TRANSFERRED TO GENERAL FUND", num(fin["surplus"]), num(fin["prior_surplus"])]]
    s.append(table(exp_rows, cw, bold_last=True))
    s.append(Spacer(1, 6))
    s.append(P(f"Programme expenditure was {fin['prog_pct']}% of total expenditure in FY {FY}.", SMALL))

    a = n["auditor"]
    aud = [P("<b>3. Independent Auditor's Report</b>", H2)]
    aud.append(P(f"We have audited the accompanying financial statements of <b>{n['name']}</b> (PAN {n['pan']}), which "
               "comprise the Balance Sheet as at 31 March 2026 and the Income and Expenditure Account for the year "
               "then ended. In our opinion, and to the best of our information and according to the explanations "
               "given to us, the financial statements give a true and fair view of the state of affairs of the "
               "organisation as at 31 March 2026 and of its surplus for the year then ended, in conformity with "
               "accounting principles generally accepted in India. Our opinion is <b>unqualified</b>.", BODY))
    aud.append(Spacer(1, 8))
    aud.append(P(f"For <b>{a[0]}</b>, {a[1]}<br/>Firm Registration No.: {a[2].replace('FRN ', '')}<br/>"
               f"{a[3]}, Partner ({a[4]})<br/>Place: {n['city']} &nbsp;&nbsp; Date: 28 August 2026", BODY))
    s.append(KeepTogether(aud))
    build_pdf(path, s, "Audited Financial Statements", n)


def doc_itr7(n, fin, path):
    rnd = random.Random(n["slug"])
    ack = "".join(str(rnd.randint(0, 9)) for _ in range(15))
    applied_pct = round(100 * fin["expenses"] / fin["income_total"], 1)
    s = letterhead(n, f"ITR-7 ACKNOWLEDGEMENT - ASSESSMENT YEAR {AY}", "Income Tax Department e-filing (synthetic sample)")
    s.append(kv_table([
        ["Acknowledgement number", f"<b>{ack}</b>"],
        ["Date of filing", "26 September 2026 (filed within the due date of 31 October 2026)"],
        ["Name", n["name"]],
        ["PAN", n["pan"]],
        ["Status", "Trust / Society claiming exemption under sections 11 and 12"],
        ["Return type", "Original, filed under section 139(4A)"],
        ["Audit report (Form 10B) filed", f"Yes - {n['auditor'][0]}"],
    ]))
    s.append(P("<b>Computation summary</b> (amounts in Rs.)", H2))
    rows = [["Particulars", "Amount"],
            ["Gross receipts / total income as per accounts", num(fin["income_total"])],
            ["Income applied to charitable purposes in India", num(fin["expenses"])],
            ["Percentage of income applied", f"{applied_pct}%"],
            ["Income accumulated / set apart (within 15% limit)", num(fin["surplus"])],
            ["Total income after exemption under sections 11 and 12", "0"],
            ["Tax payable", "Nil"]]
    s.append(table(rows, [120 * mm, 52 * mm]))
    s.append(Spacer(1, 8))
    s.append(P("The return has been electronically verified. This acknowledgement is system generated.", SMALL))
    build_pdf(path, s, "ITR-7 Acknowledgement", n)


def doc_budget(n, fin, path):
    g = n["budget_growth"]
    cw = [96 * mm, 38 * mm, 38 * mm]
    prog_budget = [round_k(x * g) for x in fin["prog_parts"]]
    admin_b = round_k(fin["admin_exp"] * g)
    fund_b = round_k(fin["fund_exp"] * g)
    total_b = sum(prog_budget) + admin_b + fund_b
    s = letterhead(n, f"ANNUAL FINANCIAL BUDGET - FY {NEXT_FY}", "Approved by the Board of Trustees on 12 March 2026")
    s.append(P(f"<b>1. Expenditure budget</b> (amounts in Rs.; actuals shown for FY {FY})", H2))
    rows = [["Head", f"Actual FY {FY}", f"Budget FY {NEXT_FY}"]]
    for prog, act, bud in zip(n["programmes"], fin["prog_parts"], prog_budget):
        rows.append([f"Programme: {prog['name']}", num(act), num(bud)])
    rows += [["Administration and overheads", num(fin["admin_exp"]), num(admin_b)],
             ["Fundraising and communications", num(fin["fund_exp"]), num(fund_b)],
             ["TOTAL", num(fin["expenses"]), num(total_b)]]
    s.append(table(rows, cw, bold_last=True))

    # funding plan
    s.append(P("<b>2. Funding plan</b>", H2))
    committed_share = 0.62
    srcs = list(fin["inc"].items())
    plan = []
    remaining = total_b
    for i, (k, v) in enumerate(srcs):
        amt = round_k(v * g)
        plan.append((k, amt))
    plan_total = sum(a for _, a in plan)
    committed = round_k(plan_total * committed_share)
    rows2 = [["Source", "Expected (Rs.)", "Status"]]
    running = 0
    for k, amt in plan:
        status = "Committed" if running + amt <= committed else "Expected / to be raised"
        if status == "Committed":
            running += amt
        rows2.append([k, num(amt), status])
    gap = total_b - plan_total
    rows2.append(["TOTAL EXPECTED FUNDING", num(plan_total), ""])
    s.append(table(rows2, [96 * mm, 38 * mm, 38 * mm], bold_last=True, align_right_from=1))
    s.append(Spacer(1, 6))
    verdict = (f"Expected funding exceeds the budget by {inr(-gap)} (retained as a reserve)." if gap <= 0
               else f"Funding gap to be raised during the year: {inr(gap)}.")
    s.append(P(verdict, BODY))
    s.append(P(f"Budget assumptions: programme costs grow about {int(round((g - 1) * 100))}% over FY {FY} actuals "
               "to cover expansion and salary revision; administration is held below 12% of total expenditure.", SMALL))
    build_pdf(path, s, "Annual Financial Budget", n)
    return dict(prog_budget=prog_budget, admin=admin_b, fund=fund_b, total=total_b)


# ---------------------------------------------------------------------------
# 3. impact documents
# ---------------------------------------------------------------------------
def doc_annual_report(n, fin, path):
    s = letterhead(n, f"ANNUAL REPORT {FY}", f"Our work between 1 April 2025 and 31 March 2026")
    s.append(P("<b>About us</b>", H2))
    s.append(P(f"{n['name']} was established on {n['inc_date']} and is registered under the {n['reg_act']} "
               f"(registration {n['reg_no']}). We hold NGO Darpan ID <b>{n['darpan']}</b>, 12A and 80G registration"
               + (", FCRA registration" if n["fcra"] else "") + f", and Form CSR-1 registration ({n['csr1'][0]}).", BODY))
    s.append(P(f"<b>Mission.</b> {n['mission']}", BODY))
    s.append(P(f"<b>Vision.</b> {n['vision']}", BODY))
    s.append(P(f"<b>Where we work.</b> {n['geography']}. During the year we employed {n['staff']} staff and "
               f"worked with {n['volunteers']} volunteers.", BODY))

    s.append(P("<b>Message from the leadership</b>", H2))
    s.append(P(f"<i>\"{n['quote']}\"</i> - {n['signatory'][0]}, {n['signatory'][1]}", BODY))

    s.append(P(f"<b>Reach at a glance</b>", H2))
    growth = round(100 * (n["beneficiaries"] / n["beneficiaries_prior"] - 1))
    s.append(P(f"In FY {FY} we directly reached <b>{num(n['beneficiaries'])} people</b>, compared with "
               f"{num(n['beneficiaries_prior'])} in FY {PRIOR_FY} (an increase of {growth}%).", BODY))

    s.append(P("<b>Programme highlights</b>", H2))
    for prog, cost in zip(n["programmes"], fin["prog_parts"]):
        block = [P(f"<b>{prog['name']}</b> (expenditure {inr(cost)})", BODY), P(prog["blurb"], BODY)]
        rows = [["Indicator", f"FY {FY}", f"FY {PRIOR_FY}"]] + [[lbl, num(a), num(b)] for lbl, a, b in prog["metrics"]]
        block += [Spacer(1, 3), table(rows, [100 * mm, 36 * mm, 36 * mm]), Spacer(1, 8)]
        s.append(KeepTogether(block))

    s.append(P("<b>A story from the field</b>", H2))
    s.append(P(n["story"], BODY))

    s.append(P("<b>Financial summary</b>", H2))
    s.append(table([["Item", f"FY {FY}", f"FY {PRIOR_FY}"],
                    ["Total income", inr(fin["income_total"]), inr(fin["prior_income_total"])],
                    ["Total expenditure", inr(fin["expenses"]), inr(fin["prior_expenses"])],
                    ["Surplus for the year", inr(fin["surplus"]), inr(fin["prior_surplus"])]],
                   [100 * mm, 36 * mm, 36 * mm]))
    s.append(Spacer(1, 4))
    s.append(P(f"Programme expenditure was {fin['prog_pct']}% of total expenditure; administration was "
               f"{round(100 * fin['admin_exp'] / fin['expenses'], 1)}%. Accounts were audited by {n['auditor'][0]} "
               "with an unqualified opinion.", BODY))

    s.append(P("<b>Our supporters</b>", H2))
    s.append(P("We thank our funders and partners: " + "; ".join(n["funders"]) + ".", BODY))

    s.append(P("<b>Governance</b>", H2))
    s.append(P("The Board met four times during the year, with an average attendance of 86%. Members of the Board:", BODY))
    s.append(table([["Name", "Role"]] + [[a, b] for a, b in n["trustees"]], [100 * mm, 72 * mm], align_right_from=9))
    build_pdf(path, s, f"Annual Report {FY}", n)


def doc_past_proposal(n, fin, path):
    prog = n["programmes"][0]
    cost = fin["prog_parts"][0]
    sanction = round_k(cost * 1.6)
    s = letterhead(n, "PROJECT PROPOSAL (FUNDED)", f"Submitted to {n['funder_name']} - Status: SANCTIONED")
    s.append(P(f"<b>{n['proposal_title']}</b>", H1))
    s.append(kv_table([
        ["Applicant", n["name"] + f" (Darpan ID {n['darpan']})"],
        ["Funder", n["funder_name"]],
        ["Project period", n["proposal_period"]],
        ["Amount sanctioned", f"<b>{inr(sanction)}</b>"],
        ["Contact", f"{n['signatory'][0]}, {n['signatory'][1]}"],
    ]))
    s.append(P("<b>1. Executive summary</b>", H2))
    s.append(P(f"This proposal sought support for the {prog['name']}, a two-year initiative in {n['geography'].split(' across ')[-1] if ' across ' in n['geography'] else n['geography']}. "
               f"{prog['blurb']} The funder approved {inr(sanction)} for the project period.", BODY))
    s.append(P("<b>2. Need</b>", H2))
    s.append(P("Communities in our area face persistent gaps in basic services and incomes. Baseline surveys "
               "carried out by our field teams in 2022 informed the targets below.", BODY))
    s.append(P("<b>3. Objectives</b>", H2))
    for lbl, a, b in prog["metrics"]:
        s.append(P(f"- Improve: {lbl}", BODY))
    s.append(P("<b>4. Budget summary</b> (amounts in Rs.)", H2))
    heads = split_int(sanction, [0.55, 0.20, 0.12, 0.08, 0.05])
    s.append(table([["Budget head", "Amount"],
                    ["Direct programme activities", num(heads[0])], ["Staff and field teams", num(heads[1])],
                    ["Training and capacity building", num(heads[2])], ["Monitoring and evaluation", num(heads[3])],
                    ["Administration (5%)", num(heads[4])], ["TOTAL", num(sanction)]],
                   [120 * mm, 52 * mm], bold_last=True))
    s.append(P("<b>5. Results achieved (as reported at project close, 31 March 2025)</b>", H2))
    rows = [["Indicator", "Result"]] + [[lbl, num(b)] for lbl, a, b in prog["metrics"]]
    s.append(table(rows, [120 * mm, 52 * mm]))
    s.append(Spacer(1, 6))
    s.append(P("The funder's closing review rated delivery as 'on target' and invited a follow-on proposal.", BODY))
    build_pdf(path, s, n["proposal_title"], n)


def doc_project_plan(n, fin, path, bud):
    prog = n["programmes"][0]
    years = 3 if n["slug"].startswith("arogya") else 2
    total = round_k(bud["prog_budget"][0] * years * 1.08)
    s = letterhead(n, "PROJECT PLAN", f"{n['plan_title']} ({n['plan_period']})")
    s.append(kv_table([
        ["Organisation", f"{n['name']} (Darpan ID {n['darpan']})"],
        ["Programme", prog["name"]],
        ["Duration", n["plan_period"]],
        ["Total project cost", f"<b>{inr(total)}</b>"],
        ["Project lead", f"{n['signatory'][0]}, {n['signatory'][1]}"],
    ]))
    s.append(P("<b>1. Background</b>", H2))
    s.append(P(f"{prog['blurb']} In FY {FY} the programme achieved the following results, which form the baseline for Phase II.", BODY))
    s.append(table([["Baseline indicator", f"FY {FY}"]] + [[lbl, num(a)] for lbl, a, _ in prog["metrics"]],
                   [120 * mm, 52 * mm]))
    s.append(P("<b>2. Logical framework</b>", H2))
    goal = {"sprout": "Secure water and stable incomes for tribal households",
            "book": "Young people from low-income families complete learning and enter decent work",
            "cross": "Affordable healthcare reaches underserved families"}[n["emblem"]]
    s.append(table([["Level", "Statement", "Means of verification"],
                    ["Goal", goal, "Annual impact survey"],
                    ["Outcome", f"Phase II expands {prog['metrics'][0][0].lower()} by at least 25% over the FY {FY} baseline", "MIS records, third-party audit"],
                    ["Output 1", "Field teams expanded and trained", "Training registers"],
                    ["Output 2", "Community structures strengthened", "Committee minutes"],
                    ["Output 3", "Quarterly monitoring and learning reviews held", "Review reports"]],
                   [24 * mm, 90 * mm, 58 * mm], align_right_from=9))
    s.append(P("<b>3. Timeline</b>", H2))
    s.append(table([["Period", "Milestone"],
                    ["Quarter 1-2", "Recruitment, baseline refresh, community mobilisation"],
                    ["Quarter 3-6", "Core delivery; mid-term review at the end of Quarter 4"],
                    ["Final 2 quarters", "Consolidation, handover to community institutions, final evaluation"]],
                   [40 * mm, 132 * mm], align_right_from=9))
    s.append(P("<b>4. Risks and mitigation</b>", H2))
    s.append(table([["Risk", "Mitigation"],
                    ["Staff turnover in remote locations", "Retention allowance and local hiring"],
                    ["Funding delay", "Reserve fund covers up to two months of expenditure"],
                    ["Weather / seasonal disruption", "Flexible work calendar and buffer months"]],
                   [70 * mm, 102 * mm], align_right_from=9))
    s.append(P("<b>5. Budget summary</b> (amounts in Rs.)", H2))
    heads = split_int(total, [0.58, 0.22, 0.08, 0.07, 0.05])
    s.append(table([["Budget head", "Amount"],
                    ["Direct programme activities", num(heads[0])], ["Staff and field teams", num(heads[1])],
                    ["Training and capacity building", num(heads[2])], ["Monitoring and evaluation", num(heads[3])],
                    ["Administration (5%)", num(heads[4])], ["TOTAL", num(total)]],
                   [120 * mm, 52 * mm], bold_last=True))
    build_pdf(path, s, n["plan_title"], n)


# ---------------------------------------------------------------------------
# 4. branding images (transparent PNGs)
# ---------------------------------------------------------------------------
def _font(size, bold=True):
    for p in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
              "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
              "/Library/Fonts/Arial Bold.ttf"):
        try:
            return ImageFont.truetype(p, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _leaf(img, center, length, width, angle, color):
    layer = Image.new("RGBA", (length * 2, length * 2), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.ellipse([length - width // 2, length - length, length + width // 2, length], fill=color)
    layer = layer.rotate(angle, resample=Image.BICUBIC)
    img.alpha_composite(layer, (int(center[0] - length), int(center[1] - length)))


def draw_emblem(img, kind, c1, c2):
    d = ImageDraw.Draw(img)
    cx, cy, R = 300, 230, 190
    d.ellipse([cx - R, cy - R, cx + R, cy + R], fill=c1 + (255,))
    d.ellipse([cx - R + 14, cy - R + 14, cx + R - 14, cy + R - 14], outline=(255, 255, 255, 255), width=5)
    white = (255, 255, 255, 255)
    if kind == "sprout":
        def lens(base, tip, width, color):
            pts_l, pts_r = [], []
            dx, dy = tip[0] - base[0], tip[1] - base[1]
            ln = math.hypot(dx, dy)
            nx, ny = -dy / ln, dx / ln
            for i in range(25):
                t = i / 24
                off = width * math.sin(math.pi * t) * (1 - 0.25 * t)
                bx, by = base[0] + dx * t, base[1] + dy * t
                pts_l.append((bx + nx * off, by + ny * off))
                pts_r.append((bx - nx * off, by - ny * off))
            d.polygon(pts_l + pts_r[::-1], fill=color)

        d.ellipse([cx - 105, cy + 85, cx + 105, cy + 135], fill=c2 + (255,))      # soil mound
        d.line([cx, cy + 100, cx, cy - 30], fill=white, width=13)                    # stem
        lens((cx, cy + 5), (cx - 112, cy - 70), 34, white)                           # left leaf
        lens((cx, cy - 30), (cx + 118, cy - 118), 38, white)                         # right leaf
        lens((cx, cy - 30), (cx + 8, cy - 130), 22, white)                           # centre bud
    elif kind == "book":
        d.polygon([(cx, cy + 70), (cx - 120, cy + 40), (cx - 120, cy - 70), (cx, cy - 40)], fill=white)
        d.polygon([(cx, cy + 70), (cx + 120, cy + 40), (cx + 120, cy - 70), (cx, cy - 40)], fill=(235, 235, 245, 255))
        d.line([cx, cy - 40, cx, cy + 70], fill=c1 + (255,), width=5)
        pts = []
        for i in range(10):
            ang = math.pi / 2 + i * math.pi / 5
            r = 42 if i % 2 == 0 else 18
            pts.append((cx + r * math.cos(ang), cy - 100 - r * math.sin(ang)))
        d.polygon(pts, fill=c2 + (255,))
    else:  # cross
        d.rounded_rectangle([cx - 28, cy - 100, cx + 28, cy + 100], radius=10, fill=white)
        d.rounded_rectangle([cx - 100, cy - 28, cx + 100, cy + 28], radius=10, fill=white)
        d.ellipse([cx - 18, cy - 18, cx + 18, cy + 18], fill=c2 + (255,))


def make_logo(n, path):
    c1, c2 = n["palette"]
    img = Image.new("RGBA", (600, 600), (0, 0, 0, 0))
    draw_emblem(img, n["emblem"], c1, c2)
    d = ImageDraw.Draw(img)
    f1 = _font(54 if len(n["short"]) < 10 else 44)
    f2 = _font(26)
    for text, font, y, col in ((n["short"], f1, 450, c1 + (255,)), (n["subtitle"], f2, 520, c2 + (255,))):
        w = d.textlength(text, font=font)
        d.text(((600 - w) / 2, y), text, font=font, fill=col)
    img.save(path)


def _arc_text(img, text, cx, cy, radius, center_deg, font, fill, top=True):
    total = sum(font.getlength(ch) for ch in text)
    span = math.degrees(total / radius)
    angle = center_deg - span / 2 if top else center_deg + span / 2
    for ch in text:
        w = font.getlength(ch)
        step = math.degrees(w / radius)
        mid = angle + step / 2 if top else angle - step / 2
        tile = Image.new("RGBA", (120, 120), (0, 0, 0, 0))
        ImageDraw.Draw(tile).text((60 - w / 2, 36), ch, font=font, fill=fill)
        rot = -mid if top else -mid + 180
        tile = tile.rotate(rot, resample=Image.BICUBIC, center=(60, 60))
        rad = math.radians(mid)
        x = cx + radius * math.sin(rad)
        y = cy - radius * math.cos(rad)
        img.alpha_composite(tile, (int(x - 60), int(y - 60)))
        angle = angle + step if top else angle - step


def _fit_font(text, radius, max_span_deg, start=40, floor=18):
    size = start
    while size > floor:
        f = _font(size)
        if math.degrees(sum(f.getlength(ch) for ch in text) / radius) <= max_span_deg:
            return f
        size -= 2
    return _font(floor)


def _short_reg(reg_no: str) -> str:
    import re
    m = re.search(r"[\w-]*\d[\w/\-]*", reg_no)
    return m.group(0) if m else reg_no


def make_stamp(n, path):
    rnd = np.random.RandomState(zlib.crc32(n["slug"].encode()))
    ink = (28, 52, 140, 225)
    S = 600
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    c = S // 2
    d.ellipse([10, 10, S - 10, S - 10], outline=ink, width=9)
    d.ellipse([34, 34, S - 34, S - 34], outline=ink, width=3)
    d.ellipse([150, 150, S - 150, S - 150], outline=ink, width=4)
    name = n["name"].upper()
    _arc_text(img, name, c, c, 215, 0, _fit_font(name, 215, 130), ink, top=True)
    bottom = f"REGD. NO. {_short_reg(n['reg_no']).upper()} * {n['state'].upper()}"
    _arc_text(img, bottom, c, c, 205, 180, _fit_font(bottom, 205, 125, start=30), ink, top=False)
    # centre block
    f_s, f_b = _font(26), _font(34)
    for text, font, y in (("REGISTERED", f_s, 205), ("NGO", f_b, 245), ("DARPAN ID", f_s, 300), (n["darpan"], _font(24), 335)):
        w = d.textlength(text, font=font)
        d.text(((S - w) / 2, y), text, font=font, fill=ink)
    # stars on the sides
    for sx in (92, S - 92):
        pts = []
        for i in range(10):
            ang = -math.pi / 2 + i * math.pi / 5
            r = 20 if i % 2 == 0 else 8
            pts.append((sx + r * math.cos(ang), c + r * math.sin(ang)))
        d.polygon(pts, fill=ink)
    # ink speckle so it looks stamped
    arr = np.array(img)
    mask = rnd.rand(S, S) > 0.12
    arr[..., 3] = (arr[..., 3] * mask).astype(np.uint8)
    img = Image.fromarray(arr).rotate(-7, resample=Image.BICUBIC, expand=False)
    img.save(path)


def make_signature(n, path):
    rnd = random.Random(n["slug"])
    SS = 4
    W, H = 600 * SS, 200 * SS
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    ink = (18, 28, 92, 240)
    # control points: big opening loop then a flowing baseline with spikes
    pts = [(40, 120)]
    x = 60
    while x < 520:
        pts.append((x, 100 + rnd.randint(-55, 45)))
        x += rnd.randint(28, 52)
    pts.append((560, 118 + rnd.randint(-12, 12)))
    pts = [(px * SS, py * SS) for px, py in pts]

    def cr(p0, p1, p2, p3, t):
        return tuple(0.5 * ((2 * p1[i]) + (-p0[i] + p2[i]) * t + (2 * p0[i] - 5 * p1[i] + 4 * p2[i] - p3[i]) * t ** 2
                            + (-p0[i] + 3 * p1[i] - 3 * p2[i] + p3[i]) * t ** 3) for i in (0, 1))

    path_pts = []
    ext = [pts[0]] + pts + [pts[-1]]
    for i in range(1, len(ext) - 2):
        for k in range(60):
            path_pts.append(cr(ext[i - 1], ext[i], ext[i + 1], ext[i + 2], k / 60))
    total = len(path_pts)
    for i, (px, py) in enumerate(path_pts):
        r = (2.6 + 2.2 * math.sin(math.pi * i / total)) * SS
        d.ellipse([px - r, py - r, px + r, py + r], fill=ink)
    # opening loop
    for k in range(120):
        a = k / 120 * 2 * math.pi
        px, py = 70 * SS + 46 * SS * math.cos(a) * 0.8, 92 * SS + 46 * SS * math.sin(a)
        r = 3.2 * SS
        d.ellipse([px - r, py - r, px + r, py + r], fill=ink)
    # underline flourish
    y0 = 168 * SS
    for k in range(400):
        t = k / 400
        px = (90 + 420 * t) * SS
        py = y0 + math.sin(t * 5) * 4 * SS - t * 10 * SS
        r = (3.4 - 2.4 * t) * SS
        d.ellipse([px - r, py - r, px + r, py + r], fill=ink)
    img = img.resize((600, 200), Image.LANCZOS)
    img.save(path)


# ---------------------------------------------------------------------------
# manifest + README
# ---------------------------------------------------------------------------
def write_manifest(n, files, dest):
    admin_name, admin_designation, phone = n["admin"]
    manifest = {
        "slug": n["slug"],
        "email_local": n["email_local"],
        "admin_name": admin_name,
        "admin_designation": admin_designation,
        "admin_phone": phone,
        "ngo_name": n["name"],
        "incorporation_year": n["inc_year"],
        "state": n["state"],
        "district": n["district"],
        "darpan_id": n["darpan"],
        "has_12a": True,
        "has_80g": True,
        "has_fcra": bool(n["fcra"]),
        "profile": {
            "mission": n["mission"],
            "sectors": n["sectors"],
            "registered_on": n["registered_on"],
            "reg_12a": n["reg12a"][0],
            "reg_80g": n["reg80g"][0],
            "reg_fcra": n["fcra"][0] if n["fcra"] else None,
            "fcra_status": "active" if n["fcra"] else "never_held",
            "fcra_valid_until": n["fcra"][3] if n["fcra"] else None,
        },
        "documents": files,  # doc_type -> relative path
        "branding": {"logo": "4_branding/logo.png", "stamp": "4_branding/stamp.png",
                     "signature": "4_branding/signature.png"},
        "absent_claims": n["absent_claims"],
    }
    (dest / "ngo.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")


def main():
    readme = ["# Synthetic NGO document pack", "",
              "Three **fictional** NGOs with complete, internally consistent document sets. Every number in every "
              "document comes from one data model, so the balance sheet, ITR-7, budget, annual report and proposals "
              "agree with each other. Nothing here is a real filing.", "",
              "Regenerate any time with `python generate_pack.py` (deterministic).", ""]
    for n in NGOS:
        fin = finance(n)
        root = OUT / n["folder"]
        for sub in ("1_statutory", "2_financial", "3_impact", "4_branding"):
            (root / sub).mkdir(parents=True, exist_ok=True)
        files = {}

        def add(doc_type, rel, fn, *args):
            fn(n, fin, root / rel, *args)
            files[doc_type] = rel

        add("darpan_certificate", "1_statutory/darpan_certificate.pdf", doc_darpan)
        add("cert_12a", "1_statutory/cert_12a.pdf", doc_12a)
        add("cert_80g", "1_statutory/cert_80g.pdf", doc_80g)
        if n["fcra"]:
            add("cert_fcra", "1_statutory/cert_fcra.pdf", doc_fcra)
        add("csr1", "1_statutory/csr1_registration.pdf", doc_csr1)
        add("audited_balance_sheet", f"2_financial/audited_balance_sheet_FY{FY}.pdf", doc_balance_sheet)
        add("itr7", f"2_financial/itr7_AY{AY}.pdf", doc_itr7)
        bud = doc_budget(n, fin, root / f"2_financial/annual_budget_FY{NEXT_FY}.pdf")
        files["annual_budget"] = f"2_financial/annual_budget_FY{NEXT_FY}.pdf"
        add("annual_report", f"3_impact/annual_report_FY{FY}.pdf", doc_annual_report)
        add("past_proposal", "3_impact/past_winning_proposal.pdf", doc_past_proposal)
        doc_project_plan(n, fin, root / "3_impact/project_plan_phase2.pdf", bud)
        files["project_plan"] = "3_impact/project_plan_phase2.pdf"
        make_logo(n, root / "4_branding/logo.png")
        make_stamp(n, root / "4_branding/stamp.png")
        make_signature(n, root / "4_branding/signature.png")
        write_manifest(n, files, root)

        readme += [f"## {n['folder'][:2]}. {n['name']} - {n['profile_label']}", "",
                   f"- **Darpan ID:** `{n['darpan']}`  |  **Registered:** {n['inc_date']}  |  {n['district']}, {n['state']}",
                   f"- **Statutory:** 12A + 80G + CSR-1" + (f" + FCRA ({n['fcra'][0]})" if n["fcra"] else " (no FCRA - good for eligibility-failure demos)"),
                   f"- **FY{FY}:** income {inr(fin['income_total'])}, expenditure {inr(fin['expenses'])}, surplus {inr(fin['surplus'])}",
                   f"- **Reach:** {num(n['beneficiaries'])} people  |  staff {n['staff']}",
                   "- **Claims deliberately NOT supported by any document** (use for the controlled fabrication test):"]
        readme += [f"  - {c}" for c in n["absent_claims"]]
        readme.append("")
    (OUT / "README.md").write_text("\n".join(readme), encoding="utf-8")
    print("Pack generated in", OUT)


if __name__ == "__main__":
    main()
