"""Generate an expanded, high-fidelity document pack for Samarpan Social Welfare Trust.

Includes:
1. Statutory:
   - Samarpan_CSR1_Registration_Certificate.pdf (Ministry of Corporate Affairs MCA Form CSR-1)
2. Financials:
   - Samarpan_ITR7_Acknowledgment_AY25.pdf (Income Tax Department ITR-7 Acknowledgment)
   - Samarpan_Annual_Budget_FY26.pdf (Board-Approved Program & Capital Budget FY 2025-26)
3. Past Impact & Plans:
   - Samarpan_Annual_Report_FY25.pdf (Comprehensive Multi-Page Annual Impact Report)
   - Samarpan_Past_Winning_Proposal_NABARD.pdf (Past funded CSR project proposal with track record)
   - Samarpan_Project_Plan_Logframe_FY26.pdf (Detailed Implementation Plan & Logical Framework Matrix)
"""

from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, HRFlowable, KeepTogether
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.pdfgen import canvas

BASE_DIR = Path(__file__).resolve().parents[2]
DOCS_DIR = BASE_DIR / "data" / "sample_documents" / "samarpan"
DOCS_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Numbered Canvas for "Page X of Y" and Running Headers
# ---------------------------------------------------------------------------
class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748B"))
        
        # Header (pages 2+)
        if self._pageNumber > 1:
            self.drawString(40, 805, "SAMARPAN SOCIAL WELFARE TRUST | Statutory & Impact Filing")
            self.drawRightString(555, 805, "Darpan: MH/2020/0789123")
            self.setStrokeColor(colors.HexColor("#CBD5E1"))
            self.setLineWidth(0.5)
            self.line(40, 800, 555, 800)

        # Footer (all pages)
        self.setStrokeColor(colors.HexColor("#E2E8F0"))
        self.setLineWidth(0.5)
        self.line(40, 35, 555, 35)
        self.drawString(40, 24, "CONFIDENTIAL & OFFICIAL DOCUMENT — GrantSetu Institutional Document Vault")
        self.drawRightString(555, 24, f"Page {self._pageNumber} of {page_count}")
        self.restoreState()


# Styles
styles = getSampleStyleSheet()

title_style = ParagraphStyle(
    "DocTitle",
    parent=styles["Heading1"],
    fontSize=16,
    leading=20,
    textColor=colors.HexColor("#0F2F64"),
    alignment=TA_CENTER,
    spaceAfter=4,
    fontName="Helvetica-Bold",
)
sub_style = ParagraphStyle(
    "DocSub",
    parent=styles["Normal"],
    fontSize=10,
    leading=14,
    textColor=colors.HexColor("#334155"),
    alignment=TA_CENTER,
    spaceAfter=10,
    fontName="Helvetica",
)
h2_style = ParagraphStyle(
    "H2",
    parent=styles["Heading2"],
    fontSize=11.5,
    leading=15,
    textColor=colors.HexColor("#0F2F64"),
    spaceBefore=10,
    spaceAfter=5,
    fontName="Helvetica-Bold",
)
h3_style = ParagraphStyle(
    "H3",
    parent=styles["Heading3"],
    fontSize=10,
    leading=13,
    textColor=colors.HexColor("#0F766E"),
    spaceBefore=7,
    spaceAfter=3,
    fontName="Helvetica-Bold",
)
body = ParagraphStyle(
    "Body",
    parent=styles["Normal"],
    fontSize=8.8,
    leading=12.5,
    textColor=colors.HexColor("#1E293B"),
    alignment=TA_JUSTIFY,
)
callout = ParagraphStyle(
    "Callout",
    parent=body,
    fontSize=8.5,
    leading=12,
    textColor=colors.HexColor("#0F766E"),
    fontName="Helvetica-Oblique",
)
meta_lbl = ParagraphStyle("MetaLbl", parent=body, fontSize=8, leading=11, fontName="Helvetica-Bold", textColor=colors.HexColor("#475569"))
meta_val = ParagraphStyle("MetaVal", parent=body, fontSize=8, leading=11, fontName="Helvetica", textColor=colors.HexColor("#0F172A"))
th_style = ParagraphStyle("TH", parent=body, fontSize=8, leading=10.5, fontName="Helvetica-Bold", textColor=colors.white, alignment=TA_CENTER)
td_style = ParagraphStyle("TD", parent=body, fontSize=7.8, leading=10, fontName="Helvetica")
td_num = ParagraphStyle("TDNum", parent=body, fontSize=7.8, leading=10, fontName="Helvetica-Bold", alignment=TA_RIGHT)


# ===========================================================================
# 1. CSR-1 Registration Certificate (Ministry of Corporate Affairs)
# ===========================================================================
def generate_csr1_certificate():
    pdf_path = DOCS_DIR / "Samarpan_CSR1_Registration_Certificate.pdf"
    doc = SimpleDocTemplate(str(pdf_path), pagesize=A4, leftMargin=36, rightMargin=36, topMargin=40, bottomMargin=40)
    story = [
        Paragraph("GOVERNMENT OF INDIA", ParagraphStyle("Gov", parent=title_style, fontSize=13, textColor=colors.HexColor("#854D0E"))),
        Paragraph("MINISTRY OF CORPORATE AFFAIRS", ParagraphStyle("MCA", parent=title_style, fontSize=15, textColor=colors.HexColor("#0F2F64"))),
        Paragraph("OFFICE OF THE REGISTRAR OF COMPANIES<br/>CENTRAL REGISTRATION CENTRE (CRC), MANESAR", sub_style),
        HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#0F2F64"), spaceAfter=12),
        
        Paragraph("<b>CERTIFICATE OF REGISTRATION FOR UNDERTAKING CSR ACTIVITIES</b>", title_style),
        Paragraph("[Pursuant to Rule 4(2) of the Companies (Corporate Social Responsibility Policy) Rules, 2014]", sub_style),
        Spacer(1, 10),
        
        Paragraph(
            "This is to certify that <b>SAMARPAN SOCIAL WELFARE TRUST</b>, having its registered office at "
            "Plot No. 14, Anand Nagar, Gangapur Road, Nashik, Maharashtra – 422013, has been officially registered with the "
            "Ministry of Corporate Affairs for the purpose of undertaking Corporate Social Responsibility (CSR) activities under "
            "Section 135 of the Companies Act, 2013.",
            body,
        ),
        Spacer(1, 12),
    ]

    csr_table = [
        [Paragraph("<b>CSR Registration Number (CSR-1):</b>", meta_lbl), Paragraph("<b>CSR00048219</b>", meta_val)],
        [Paragraph("<b>Entity Type:</b>", meta_lbl), Paragraph("Public Charitable Trust (Reg No. E-3412 / Nashik)", meta_val)],
        [Paragraph("<b>Permanent Account Number (PAN):</b>", meta_lbl), Paragraph("AAATS9876M", meta_val)],
        [Paragraph("<b>NITI Aayog Darpan Unique ID:</b>", meta_lbl), Paragraph("MH/2020/0789123", meta_val)],
        [Paragraph("<b>Income Tax 12A URN:</b>", meta_lbl), Paragraph("AAATS9876ME20211", meta_val)],
        [Paragraph("<b>Income Tax 80G URN:</b>", meta_lbl), Paragraph("AAATS9876MF20212", meta_val)],
        [Paragraph("<b>Date of Approval & Issuance:</b>", meta_lbl), Paragraph("12th May 2021", meta_val)],
        [Paragraph("<b>Validity Period:</b>", meta_lbl), Paragraph("Permanent / Active (Perpetual subject to statutory compliance)", meta_val)],
    ]
    t = Table(csr_table, colWidths=[2.2 * inch, 5.0 * inch])
    t.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#F8FAFC")),
        ("PADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(t)
    story.append(Spacer(1, 15))

    story.append(Paragraph(
        "<b>Important Statutory Notes:</b><br/>"
        "1. This registration grants eligibility to the Trust to partner with Corporates, Public Sector Undertakings (PSUs), and CSR Foundations for Schedule VII CSR programs.<br/>"
        "2. The entity must file its annual returns and maintain audited accounts in accordance with MCA & ICAI guidelines.<br/>"
        "3. Any alteration in the Trust deed, governing body, or PAN status must be reported within 30 days to the Registrar.",
        body,
    ))
    story.append(Spacer(1, 20))

    # Officer signature block
    sig_block = [
        [Paragraph("", body), Paragraph("<b>Digitally Signed By:</b><br/>Registrar of Companies<br/>Central Registration Centre, MCA<br/>Government of India", ParagraphStyle("R", parent=body, alignment=TA_RIGHT))]
    ]
    t_sig = Table(sig_block, colWidths=[4.0 * inch, 3.2 * inch])
    story.append(t_sig)

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"Generated: {pdf_path}")


# ===========================================================================
# 2. ITR-7 Return Acknowledgment (Income Tax Department AY 2024-25)
# ===========================================================================
def generate_itr7_acknowledgment():
    pdf_path = DOCS_DIR / "Samarpan_ITR7_Acknowledgment_AY25.pdf"
    doc = SimpleDocTemplate(str(pdf_path), pagesize=A4, leftMargin=36, rightMargin=36, topMargin=40, bottomMargin=40)
    story = [
        Paragraph("INCOME TAX DEPARTMENT, GOVT. OF INDIA", title_style),
        Paragraph("INDIAN INCOME TAX RETURN ACKNOWLEDGEMENT [ITR-7]<br/>Assessment Year 2024-25 (Financial Year 2023-24)", sub_style),
        HRFlowable(width="100%", thickness=1, color=colors.HexColor("#0F2F64"), spaceAfter=10),
        
        Paragraph("<b>Filing Section:</b> 139(4A) / 139(4C) — Charitable or Religious Trusts & Institutions", body),
        Spacer(1, 8),
    ]

    t_data = [
        [Paragraph("<b>PAN:</b>", meta_lbl), Paragraph("AAATS9876M", meta_val), Paragraph("<b>Status:</b>", meta_lbl), Paragraph("Trust / AOP", meta_val)],
        [Paragraph("<b>Name of Assessee:</b>", meta_lbl), Paragraph("SAMARPAN SOCIAL WELFARE TRUST", meta_val), Paragraph("<b>Return Type:</b>", meta_lbl), Paragraph("Original (u/s 139(1))", meta_val)],
        [Paragraph("<b>NITI Aayog Darpan ID:</b>", meta_lbl), Paragraph("MH/2020/0789123", meta_val), Paragraph("<b>12A URN:</b>", meta_lbl), Paragraph("AAATS9876ME20211", meta_val)],
        [Paragraph("<b>Ack Number:</b>", meta_lbl), Paragraph("284910284710294", meta_val), Paragraph("<b>Date of Filing:</b>", meta_lbl), Paragraph("28-10-2024", meta_val)],
    ]
    t = Table(t_data, colWidths=[1.8 * inch, 2.0 * inch, 1.6 * inch, 1.8 * inch])
    t.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
        ("PADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(t)
    story.append(Spacer(1, 12))

    story.append(Paragraph("<b>Computation of Income & Application of Funds (in INR)</b>", h2_style))

    comp_table = [
        [Paragraph("<b>Particulars</b>", th_style), Paragraph("<b>Schedule</b>", th_style), Paragraph("<b>Amount (₹)</b>", th_style)],
        [Paragraph("Gross Voluntary Contributions (CSR & Donations)", td_style), Paragraph("Schedule VC", td_style), Paragraph("3,42,80,000", td_num)],
        [Paragraph("Income from Trust Property / Bank Interest", td_style), Paragraph("Schedule AI", td_style), Paragraph("14,25,000", td_num)],
        [Paragraph("<b>Total Gross Receipts / Inflow</b>", td_style), Paragraph("-", td_style), Paragraph("<b>3,57,05,000</b>", td_num)],
        [Paragraph("Amount Applied to Charitable Objects (Health & Edu)", td_style), Paragraph("Schedule ER", td_style), Paragraph("2,65,40,000", td_num)],
        [Paragraph("Amount Applied for Capital Assets / Clinics", td_style), Paragraph("Schedule EC", td_style), Paragraph("42,50,000", td_num)],
        [Paragraph("Accumulation / Set Apart u/s 11(1)(a) (≤ 15%)", td_style), Paragraph("Section 11(1)", td_style), Paragraph("49,15,000", td_num)],
        [Paragraph("<b>Total Application & Permissible Accumulation</b>", td_style), Paragraph("-", td_style), Paragraph("<b>3,57,05,000</b>", td_num)],
        [Paragraph("<b>Taxable Income</b>", td_style), Paragraph("Total", td_style), Paragraph("<b>NIL (₹ 0)</b>", td_num)],
        [Paragraph("<b>Net Tax Payable</b>", td_style), Paragraph("-", td_style), Paragraph("<b>₹ 0</b>", td_num)],
    ]
    t2 = Table(comp_table, colWidths=[4.2 * inch, 1.3 * inch, 1.7 * inch])
    t2.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F2F64")),
        ("BACKGROUND", (0, -2), (-1, -1), colors.HexColor("#ECFDF5")),
        ("PADDING", (0, 0), (-1, -1), 4.5),
    ]))
    story.append(t2)
    story.append(Spacer(1, 14))

    story.append(Paragraph(
        "<b>Auditor Verification:</b> Accounts audited under Form 10B by Joshi & Kulkarni, Chartered Accountants (M. No. 045129, FRN 104522W). "
        "Verified that administrative expenses stand at <b>4.6%</b>, conforming to Section 135 & Section 11 statutory norms.",
        body,
    ))

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"Generated: {pdf_path}")


# ===========================================================================
# 3. Approved Annual Financial Budget (FY 2025-26)
# ===========================================================================
def generate_annual_budget():
    pdf_path = DOCS_DIR / "Samarpan_Annual_Budget_FY26.pdf"
    doc = SimpleDocTemplate(str(pdf_path), pagesize=A4, leftMargin=36, rightMargin=36, topMargin=40, bottomMargin=40)
    story = [
        Paragraph("SAMARPAN SOCIAL WELFARE TRUST", title_style),
        Paragraph("BOARD-APPROVED ANNUAL PROGRAMMATIC & CAPITAL BUDGET<br/>Financial Year 2025-26 (Resolution No. BOT/2025/04)", sub_style),
        HRFlowable(width="100%", thickness=1, color=colors.HexColor("#0F2F64"), spaceAfter=10),
        
        Paragraph(
            "The Board of Trustees in its meeting dated 24th March 2025 reviewed programmatic deliverables and approved the annual "
            "expenditure budget of <b>₹ 4,15,00,000 (Four Crores Fifteen Lakhs Only)</b> across ongoing healthcare, education, "
            "rural water resilience, and solar energy initiatives in Nashik, Dhule, and Nandurbar districts.",
            body,
        ),
        Spacer(1, 10),
    ]

    budget_data = [
        [Paragraph("<b>Sr.</b>", th_style), Paragraph("<b>Strategic Pillar / Program</b>", th_style), Paragraph("<b>Target Focus Blocks</b>", th_style), Paragraph("<b>Allocated (₹)</b>", th_style), Paragraph("<b>% Share</b>", th_style)],
        [Paragraph("1", td_style), Paragraph("<b>Project Aarogya Vardhini</b> (Mobile Health Clinics, Maternal Checkups, Malnutrition)", td_style), Paragraph("Trimbakeshwar, Surgana, Peint (42 hamlets)", td_style), Paragraph("₹ 1,45,00,000", td_num), Paragraph("34.9%", td_num)],
        [Paragraph("2", td_style), Paragraph("<b>Project Gyan Deep</b> (Early Education Balwadis, FLN Kits, Tribal Slum Children)", td_style), Paragraph("Nashik Urban Slums, Dindori tribal belts", td_style), Paragraph("₹ 95,00,000", td_num), Paragraph("22.9%", td_num)],
        [Paragraph("3", td_style), Paragraph("<b>Project Samriddhi</b> (Women SHGs, Dairy Micro-enterprise, Financial Inclusion)", td_style), Paragraph("Igatpuri, Sinnar, Kalwan blocks", td_style), Paragraph("₹ 65,00,000", td_num), Paragraph("15.7%", td_num)],
        [Paragraph("4", td_style), Paragraph("<b>Project Jal & Urja Setu</b> (Solar Pump Mobilization, Check Dams, PM-KUSUM Outreach)", td_style), Paragraph("Nashik, Niphad, Deola drought pockets", td_style), Paragraph("₹ 55,00,000", td_num), Paragraph("13.3%", td_num)],
        [Paragraph("5", td_style), Paragraph("<b>Monitoring, Evaluation & Digital MIS</b> (KAP surveys, cloud tracking, field audits)", td_style), Paragraph("All operational blocks", td_style), Paragraph("₹ 35,00,000", td_num), Paragraph("8.4%", td_num)],
        [Paragraph("6", td_style), Paragraph("<b>Statutory, Audit & Administrative Overheads</b> (Audit, reporting, compliance)", td_style), Paragraph("Headquarters & Field Offices", td_style), Paragraph("₹ 20,00,000", td_num), Paragraph("4.8%", td_num)],
        [Paragraph("<b>TOTAL</b>", td_style), Paragraph("<b>Comprehensive Operational Budget FY 2025-26</b>", td_style), Paragraph("<b>All Focus Areas</b>", td_style), Paragraph("<b>₹ 4,15,00,000</b>", td_num), Paragraph("<b>100.0%</b>", td_num)],
    ]
    t = Table(budget_data, colWidths=[0.4 * inch, 2.8 * inch, 2.0 * inch, 1.3 * inch, 0.7 * inch])
    t.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F2F64")),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#F1F5F9")),
        ("PADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(t)
    story.append(Spacer(1, 14))

    story.append(Paragraph(
        "<b>Governance & Financial Controls:</b> Administrative overhead is tightly capped at <b>4.8%</b>, ensuring statutory compliance with the "
        "&le; 5% cap under MCA CSR Rules. Unutilized capital funds are parked in AAA-rated fixed deposits with State Bank of India.",
        body,
    ))

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"Generated: {pdf_path}")


# ===========================================================================
# 4. Multi-Page Comprehensive Annual Impact Report (FY 2024-25)
# ===========================================================================
def generate_comprehensive_annual_report():
    pdf_path = DOCS_DIR / "Samarpan_Annual_Report_FY25.pdf"
    doc = SimpleDocTemplate(str(pdf_path), pagesize=A4, leftMargin=36, rightMargin=36, topMargin=40, bottomMargin=40)
    story = []

    # Page 1: Header, Message & Statutory Overview
    story.append(Paragraph("SAMARPAN SOCIAL WELFARE TRUST", title_style))
    story.append(Paragraph("ANNUAL ACTIVITY & IMPACT REPORT (FY 2024–2025)<br/><i>Ten Years of Grassroots Service: 2014 – 2024</i>", sub_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#0F2F64"), spaceAfter=12))

    story.append(Paragraph(
        "<b>Statutory Identity & Governance:</b><br/>"
        "• Reg No: E-3412 / Nashik (Registered under Maharashtra Public Trusts Act, 1950)<br/>"
        "• NITI Aayog Darpan Unique ID: <b>MH/2020/0789123</b><br/>"
        "• Income Tax Status: Active 12A (URN: <b>AAATS9876ME20211</b>) | 80G Approval (URN: <b>AAATS9876MF20212</b> dated 14.10.2020)<br/>"
        "• MCA CSR-1 Registration: <b>CSR00048219</b> | FCRA Status: Never Held (100% Domestic Operation)",
        body,
    ))
    story.append(Spacer(1, 10))

    story.append(Paragraph("1. Message from the Managing Trustee", h2_style))
    story.append(Paragraph(
        "<i>\"Completing over a decade of community transformation across Northern Maharashtra has reinforced our foundational conviction: "
        "sustainable social change happens when marginalized communities become active partners rather than passive recipients. "
        "In FY 2024-25, our mobile clinics traversed more than 36,000 kilometers across rugged tribal terrain, providing primary maternal "
        "and pediatric care to families who had never previously seen a physician. As we embark on renewable energy and climate-smart "
        "agriculture initiatives such as PM-KUSUM solarization, our commitment to financial transparency and audited impact remains absolute.\"</i><br/>"
        "— <b>Sunita Deshmukh</b>, Managing Trustee",
        callout,
    ))
    story.append(Spacer(1, 12))

    story.append(Paragraph("2. Strategic Pillars & Programmatic Achievements in FY25", h2_style))
    story.append(Paragraph(
        "<b>Pillar A: Community Health & Maternal Care ('Project Aarogya Vardhini')</b><br/>"
        "Operating 4 customized Mobile Medical Units (MMUs) equipped with diagnostic blood analyzers, ultrasound, and emergency obstetric kits. "
        "Across 42 remote tribal hamlets in Trimbakeshwar and Surgana talukas, the team conducted 240 village medical camps, examining <b>18,540 patients</b>. "
        "Maternal health monitoring ensured 1,420 pregnant women received antenatal checkups, achieving a <b>98.4% institutional delivery rate</b> (up from 64% baseline).",
        body,
    ))
    story.append(Spacer(1, 8))

    story.append(Paragraph(
        "<b>Pillar B: Foundational Literacy & Tribal Education ('Project Gyan Deep')</b><br/>"
        "Running 32 Community Learning Centers (Balwadis) catering to <b>1,280 tribal children</b>. Distributed bilingual Foundational Literacy and "
        "Numeracy (FLN) kits, established 14 village libraries, and served 85,000 fortified nutritional meals combating severe acute malnutrition.",
        body,
    ))
    story.append(Spacer(1, 8))

    story.append(Paragraph(
        "<b>Pillar C: Women's Economic Empowerment & Dairy Cooperatives ('Project Samriddhi')</b><br/>"
        "Mobilized 45 Women Self-Help Groups (SHGs) comprising 520 marginalized women. Facilitated ₹ 48.5 Lakhs in credit linkage through "
        "nationalized banks for dairy cattle procurement and organic millet processing, maintaining a flawless <b>100% repayment record</b>.",
        body,
    ))
    story.append(Spacer(1, 8))

    story.append(Paragraph(
        "<b>Pillar D: Water Harvesting & Solar Agriculture ('Project Jal & Urja Setu')</b><br/>"
        "Constructed 14 earthen check dams and de-silted 8 community percolation tanks, recharging 45 open wells. Conducted renewable energy "
        "and solar irrigation awareness sessions in 50 agrarian villages, paving the way for PM-KUSUM solar pump adoption.",
        body,
    ))

    # Page Break for Page 2
    story.append(PageBreak())

    story.append(Paragraph("3. FY 2024-25 Key Performance Indicators (KPI Dashboard)", h2_style))
    
    kpi_table = [
        [Paragraph("<b>Program Metric / Key Performance Indicator</b>", th_style), Paragraph("<b>FY25 Target</b>", th_style), Paragraph("<b>FY25 Achieved</b>", th_style), Paragraph("<b>Variance / Status</b>", th_style)],
        [Paragraph("Rural patients screened & treated at Mobile Medical Units", td_style), Paragraph("16,000", td_style), Paragraph("<b>18,540</b>", td_num), Paragraph("+15.8% (Exceeded)", td_style)],
        [Paragraph("Maternal antenatal checkups & institutional deliveries", td_style), Paragraph("1,200", td_style), Paragraph("<b>1,420</b>", td_num), Paragraph("+18.3% (Exceeded)", td_style)],
        [Paragraph("Tribal children enrolled in Community Balwadis & FLN", td_style), Paragraph("1,200", td_style), Paragraph("<b>1,280</b>", td_num), Paragraph("+6.7% (Achieved)", td_style)],
        [Paragraph("Hot fortified nutritious meals served to children", td_style), Paragraph("75,000", td_style), Paragraph("<b>85,000</b>", td_num), Paragraph("+13.3% (Exceeded)", td_style)],
        [Paragraph("Women SHG members trained in micro-dairy & millets", td_style), Paragraph("450", td_style), Paragraph("<b>520</b>", td_num), Paragraph("+15.5% (Exceeded)", td_style)],
        [Paragraph("Village check dams de-silted / percolation tanks built", td_style), Paragraph("12", td_style), Paragraph("<b>14</b>", td_num), Paragraph("+16.7% (Achieved)", td_style)],
        [Paragraph("Administrative & overhead expense ratio (Statutory &le; 5%)", td_style), Paragraph("&le; 5.0%", td_style), Paragraph("<b>4.6%</b>", td_num), Paragraph("Fully Compliant", td_style)],
    ]
    t_kpi = Table(kpi_table, colWidths=[3.2 * inch, 1.2 * inch, 1.3 * inch, 1.5 * inch])
    t_kpi.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F2F64")),
        ("PADDING", (0, 0), (-1, -1), 4.5),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
    ]))
    story.append(t_kpi)
    story.append(Spacer(1, 14))

    story.append(Paragraph("4. Audited Financial Highlights (FY 2024-25)", h2_style))
    
    fin_table = [
        [Paragraph("<b>Financial Metric</b>", th_style), Paragraph("<b>FY 2024-25 (₹)</b>", th_style), Paragraph("<b>FY 2023-24 (₹)</b>", th_style), Paragraph("<b>Growth %</b>", th_style)],
        [Paragraph("Total Corpus Fund & Reserves", td_style), Paragraph("₹ 1,45,20,000", td_num), Paragraph("₹ 1,18,50,000", td_num), Paragraph("+22.5%", td_style)],
        [Paragraph("Total Balance Sheet Assets (Clinics & Equipment)", td_style), Paragraph("₹ 4,83,40,000", td_num), Paragraph("₹ 4,03,60,000", td_num), Paragraph("+19.8%", td_style)],
        [Paragraph("Annual Program Expenditure Applied", td_style), Paragraph("₹ 2,65,40,000", td_num), Paragraph("₹ 2,15,80,000", td_num), Paragraph("+23.0%", td_style)],
        [Paragraph("Cash & Bank Balances (State Bank of India)", td_style), Paragraph("₹ 35,50,000", td_num), Paragraph("₹ 27,60,000", td_num), Paragraph("+28.6%", td_style)],
        [Paragraph("Administrative Cost Ratio", td_style), Paragraph("4.6%", td_num), Paragraph("4.8%", td_num), Paragraph("Cost-Efficient", td_style)],
    ]
    t_fin = Table(fin_table, colWidths=[3.0 * inch, 1.6 * inch, 1.6 * inch, 1.0 * inch])
    t_fin.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F2F64")),
        ("PADDING", (0, 0), (-1, -1), 4.5),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
    ]))
    story.append(t_fin)
    story.append(Spacer(1, 14))

    story.append(Paragraph(
        "<b>Auditor Attestation:</b> Books of accounts audited by <b>Joshi & Kulkarni, Chartered Accountants (Membership No. 045129, FRN 104522W)</b>. "
        "The statutory audit confirmed complete compliance with the Maharashtra Public Trusts Act, Section 12A/80G of the Income Tax Act, and MCA CSR guidelines.",
        body,
    ))
    story.append(Spacer(1, 15))

    story.append(Paragraph("5. Partner & Funder Acknowledgments", h2_style))
    story.append(Paragraph(
        "Samarpan Social Welfare Trust gratefully acknowledges the collaborative support of the <b>District Collectorate Nashik</b>, "
        "<b>Zilla Parishad Health Department</b>, <b>National Bank for Agriculture and Rural Development (NABARD)</b>, "
        "and our corporate CSR partners for their sustained commitment to rural empowerment.",
        body,
    ))

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"Generated: {pdf_path}")


# ===========================================================================
# 5. Past Winning Proposal (NABARD Rural Healthcare Initiative)
# ===========================================================================
def generate_past_winning_proposal():
    pdf_path = DOCS_DIR / "Samarpan_Past_Winning_Proposal_NABARD.pdf"
    doc = SimpleDocTemplate(str(pdf_path), pagesize=A4, leftMargin=36, rightMargin=36, topMargin=40, bottomMargin=40)
    story = [
        Paragraph("AWARDED GRANT PROPOSAL & COMPLETION DOSSIER", ParagraphStyle("Aw", parent=title_style, fontSize=14, textColor=colors.HexColor("#15803D"))),
        Paragraph("<b>Project:</b> Mobile Health Outreach & Tribal Mother-Child Care Initiative<br/><b>Funding Agency:</b> National Bank for Agriculture and Rural Development (NABARD)", sub_style),
        HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#15803D"), spaceAfter=10),
        
        Paragraph("<b>Project Summary & Award Details:</b>", h2_style),
    ]

    award_meta = [
        [Paragraph("<b>Sanction Letter Ref:</b>", meta_lbl), Paragraph("NABARD/MRO/RDA/2023-24/G-118", meta_val), Paragraph("<b>Sanction Date:</b>", meta_lbl), Paragraph("15th June 2023", meta_val)],
        [Paragraph("<b>Grant Amount Awarded:</b>", meta_lbl), Paragraph("<b>₹ 45,00,000 (Forty-Five Lakhs)</b>", meta_val), Paragraph("<b>Project Duration:</b>", meta_lbl), Paragraph("18 Months (Completed)", meta_val)],
        [Paragraph("<b>Implementing Agency:</b>", meta_lbl), Paragraph("Samarpan Social Welfare Trust", meta_val), Paragraph("<b>Darpan ID:</b>", meta_lbl), Paragraph("MH/2020/0789123", meta_val)],
        [Paragraph("<b>Target Geography:</b>", meta_lbl), Paragraph("Trimbakeshwar & Surgana, Nashik", meta_val), Paragraph("<b>Audit Status:</b>", meta_lbl), Paragraph("100% Utilized & Certified", meta_val)],
    ]
    t = Table(award_meta, colWidths=[1.8 * inch, 2.0 * inch, 1.6 * inch, 1.8 * inch])
    t.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
        ("PADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(t)
    story.append(Spacer(1, 10))

    story.append(Paragraph("Key Milestones & Certified Deliverables:", h2_style))
    story.append(Paragraph(
        "1. <b>Mobile Medical Unit Procurement:</b> Procured and fabricated 2 customized Force Traveller medical vans equipped with telemedicine connectivity, cold-chain vaccine storage, and battery-powered portable ultrasound.<br/>"
        "2. <b>Field Clinic Execution:</b> Successfully conducted 180 scheduled medical visits reaching 14,200 unique tribal beneficiaries.<br/>"
        "3. <b>Maternal Health Tracking:</b> Registered 850 high-risk pregnancies and facilitated zero maternal mortality across the target cluster.<br/>"
        "4. <b>Institutional Handover & Sustainability:</b> Formed 18 Village Health Committees (VHCs) with ASHAs and Anganwadi workers to ensure sustained monitoring.",
        body,
    ))
    story.append(Spacer(1, 12))

    story.append(Paragraph("Certified Financial Utilization Summary:", h2_style))
    fin_util = [
        [Paragraph("<b>Budget Head</b>", th_style), Paragraph("<b>Approved (₹)</b>", th_style), Paragraph("<b>Actual Spent (₹)</b>", th_style), Paragraph("<b>Variance (₹)</b>", th_style)],
        [Paragraph("Capital: Mobile Medical Vans & Equipment", td_style), Paragraph("₹ 22,00,000", td_num), Paragraph("₹ 21,85,000", td_num), Paragraph("₹ +15,000", td_style)],
        [Paragraph("Operational: Doctor, Nurse & Field Mobilizers", td_style), Paragraph("₹ 14,00,000", td_num), Paragraph("₹ 14,00,000", td_num), Paragraph("₹ 0", td_style)],
        [Paragraph("Medicines, Consumables & Lab Reagents", td_style), Paragraph("₹ 7,00,000", td_num), Paragraph("₹ 7,15,000", td_num), Paragraph("₹ -15,000", td_style)],
        [Paragraph("Administrative & External Audit (Joshi & Kulkarni)", td_style), Paragraph("₹ 2,00,000", td_num), Paragraph("₹ 2,00,000", td_num), Paragraph("₹ 0", td_style)],
        [Paragraph("<b>Total Project Outlay</b>", td_style), Paragraph("<b>₹ 45,00,000</b>", td_num), Paragraph("<b>₹ 45,00,000</b>", td_num), Paragraph("<b>100% Utilized</b>", td_style)],
    ]
    t2 = Table(fin_util, colWidths=[3.2 * inch, 1.4 * inch, 1.4 * inch, 1.2 * inch])
    t2.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#15803D")),
        ("PADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(t2)
    story.append(Spacer(1, 14))

    story.append(Paragraph(
        "<b>Evaluation Rating:</b> NABARD Third-Party Monitoring Agency scored project execution at <b>94.5 / 100</b>, commending Samarpan "
        "for zero fund diversion, pristine documentation, and exemplary community trust.",
        body,
    ))

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"Generated: {pdf_path}")


# ===========================================================================
# 6. Detailed Project Implementation Plan & Logframe (FY 2025-26)
# ===========================================================================
def generate_project_plan_logframe():
    pdf_path = DOCS_DIR / "Samarpan_Project_Plan_Logframe_FY26.pdf"
    doc = SimpleDocTemplate(str(pdf_path), pagesize=A4, leftMargin=36, rightMargin=36, topMargin=40, bottomMargin=40)
    story = [
        Paragraph("SAMARPAN SOCIAL WELFARE TRUST", title_style),
        Paragraph("PROJECT IMPLEMENTATION PLAN & LOGICAL FRAMEWORK (LOGFRAME)<br/>Scalable Rural Energy & Livelihood Transition (2025–2027)", sub_style),
        HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#0F2F64"), spaceAfter=10),
        
        Paragraph("1. Theory of Change & Logical Framework Matrix (Logframe)", h2_style),
    ]

    logframe_data = [
        [Paragraph("<b>Hierarchy of Objectives</b>", th_style), Paragraph("<b>Objectively Verifiable Indicators (OVIs)</b>", th_style), Paragraph("<b>Means of Verification (MoV)</b>", th_style), Paragraph("<b>Critical Assumptions / Risks</b>", th_style)],
        [
            Paragraph("<b>Goal:</b><br/>Alleviate rural poverty and enhance climate resilience among smallholder farmers.", td_style),
            Paragraph("• Net farm household income increases by &ge; 30%<br/>• 500 pump sets shifted to solar energy", td_style),
            Paragraph("• Baseline/Endline socio-economic survey<br/>• MSEDCL/MEDA commissioning logs", td_style),
            Paragraph("Stable state agrarian policy and continuous grid power parity.", td_style),
        ],
        [
            Paragraph("<b>Outcomes:</b><br/>1. Overcome information asymmetry on PM-KUSUM.<br/>2. Facilitate institutional co-finance for farmers.", td_style),
            Paragraph("• 15,000 farming households reached<br/>• 1,200 verified applications submitted<br/>• 400 bank credit sanctions", td_style),
            Paragraph("• Online portal registration receipts<br/>• Bank sanction letters from SBI & Gramin Bank", td_style),
            Paragraph("Cooperation of local Gram Panchayats and regional rural bank managers.", td_style),
        ],
        [
            Paragraph("<b>Outputs:</b><br/>• 100 Village Chaupals & Gram Sabhas<br/>• 15 Banking Credit Linkage Camps<br/>• 150 Solar Caretakers certified", td_style),
            Paragraph("• 100 event attendance registers<br/>• 15 credit camp dossiers<br/>• 150 training completion certificates", td_style),
            Paragraph("• GPS-tagged event photographs<br/>• Attendance rosters signed by Sarpanch<br/>• Vendor training evaluation scores", td_style),
            Paragraph("Favorable weather conditions and seasonal farm labor availability.", td_style),
        ],
    ]
    t = Table(logframe_data, colWidths=[1.8 * inch, 2.0 * inch, 1.8 * inch, 1.6 * inch])
    t.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F2F64")),
        ("PADDING", (0, 0), (-1, -1), 4),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(t)
    story.append(Spacer(1, 14))

    story.append(Paragraph("2. Risk Mitigation & Governance Matrix", h2_style))
    risk_data = [
        [Paragraph("<b>Identified Risk</b>", th_style), Paragraph("<b>Severity</b>", th_style), Paragraph("<b>Proactive Mitigation Strategy</b>", th_style)],
        [Paragraph("Farmer reluctance for 30% beneficiary capital contribution", td_style), Paragraph("Medium", td_style), Paragraph("Structure joint credit camps with SBI & Maharashtra Gramin Bank for low-interest, collateral-free priority sector agricultural loans.", td_style)],
        [Paragraph("Delays in state nodal agency portal verification (Mahaurja)", td_style), Paragraph("Medium", td_style), Paragraph("Form a dedicated liaison help desk with weekly physical coordination meets at the MEDA / MSEDCL district office.", td_style)],
        [Paragraph("Post-installation technical breakdowns of solar pump sets", td_style), Paragraph("Low", td_style), Paragraph("Train 150 local youth as Community Solar Caretakers with toolkits for rapid response (turnaround time < 48 hours).", td_style)],
    ]
    t_risk = Table(risk_data, colWidths=[2.6 * inch, 1.0 * inch, 3.6 * inch])
    t_risk.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F2F64")),
        ("PADDING", (0, 0), (-1, -1), 4.5),
    ]))
    story.append(t_risk)

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"Generated: {pdf_path}")


def main():
    print("Generating expanded institutional document pack for Samarpan Social Welfare Trust...")
    generate_csr1_certificate()
    generate_itr7_acknowledgment()
    generate_annual_budget()
    generate_comprehensive_annual_report()
    generate_past_winning_proposal()
    generate_project_plan_logframe()
    print("All documents generated successfully in data/sample_documents/samarpan/")


if __name__ == "__main__":
    main()
