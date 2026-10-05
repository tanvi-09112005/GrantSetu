"""Generate a fresh, unregistered NGO sample pack with authentic certificates
for testing the new registration and verification flow.

NGO: Samarpan Social Welfare Trust
Darpan ID: MH/2020/0789123 (Fresh - not registered in database)
State: Maharashtra, District: Nashik, Year: 2014
"""

from pathlib import Path
from PIL import Image, ImageDraw
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.pdfgen import canvas

BASE_DIR = Path(__file__).resolve().parents[2]
DOCS_DIR = BASE_DIR / "data" / "sample_documents" / "samarpan"
ASSETS_DIR = DOCS_DIR / "assets"
DOCS_DIR.mkdir(parents=True, exist_ok=True)
ASSETS_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# 1. Image Assets (Emblems, Seals, Stamps)
# ---------------------------------------------------------------------------

def create_gold_emblem():
    path = ASSETS_DIR / "emblem_gold.png"
    img = Image.new("RGBA", (140, 180), (255, 255, 255, 0))
    d = ImageDraw.Draw(img)
    gold = (180, 130, 20, 255)
    d.polygon([(70, 15), (45, 55), (95, 55)], fill=gold)
    d.polygon([(30, 45), (15, 80), (55, 80)], fill=gold)
    d.polygon([(110, 45), (85, 80), (125, 80)], fill=gold)
    d.rectangle([35, 85, 105, 115], fill=gold)
    d.ellipse([50, 120, 90, 160], outline=gold, width=3)
    d.line([(70, 120), (70, 160)], fill=gold, width=2)
    d.line([(50, 140), (90, 140)], fill=gold, width=2)
    d.rectangle([25, 165, 115, 175], fill=gold)
    d.text((36, 150), "सत्यमेव जयते", fill=gold)
    img.save(str(path))
    return str(path)

def create_g20_logo():
    path = ASSETS_DIR / "g20_logo.png"
    img = Image.new("RGBA", (220, 140), (255, 255, 255, 0))
    d = ImageDraw.Draw(img)
    orange = (235, 100, 20, 255)
    blue = (25, 110, 190, 255)
    green = (25, 140, 40, 255)
    dark = (40, 50, 60, 255)
    d.text((20, 20), "G", fill=orange)
    d.text((60, 20), "2", fill=blue)
    d.ellipse([95, 20, 145, 70], outline=blue, width=3)
    d.arc([95, 20, 145, 70], start=30, end=150, fill=green, width=4)
    d.text((60, 85), "भारत 2023 INDIA", fill=dark)
    d.text((45, 108), "वसुधैव कुटुम्बकम्", fill=orange)
    img.save(str(path))
    return str(path)

def create_darpan_bottom_banner():
    path = ASSETS_DIR / "darpan_bottom_banner.png"
    img = Image.new("RGBA", (480, 100), (255, 255, 255, 0))
    d = ImageDraw.Draw(img)
    blue_bg = (24, 76, 158, 255)
    d.rounded_rectangle([10, 10, 470, 90], radius=12, fill=blue_bg)
    d.rectangle([35, 25, 65, 75], outline=(255, 255, 255, 240), width=2)
    d.text((37, 77), "सत्यमेव", fill=(255, 255, 255, 240))
    d.rectangle([110, 25, 190, 75], fill=(255, 255, 255, 255))
    d.text((120, 35), "NGO", fill=(30, 41, 59, 255))
    gold = (234, 179, 8, 255)
    d.ellipse([215, 28, 265, 72], fill=gold)
    d.text((233, 40), "D", fill=(24, 76, 158, 255))
    d.text((275, 40), "ARPAN", fill=(255, 255, 255, 255))
    img.save(str(path))
    return str(path)

def create_it_black_emblem():
    path = ASSETS_DIR / "it_emblem_black.png"
    img = Image.new("RGBA", (100, 140), (255, 255, 255, 0))
    d = ImageDraw.Draw(img)
    ink = (30, 30, 30, 255)
    d.polygon([(50, 10), (30, 40), (70, 40)], fill=ink)
    d.polygon([(20, 35), (10, 60), (40, 60)], fill=ink)
    d.polygon([(80, 35), (60, 60), (90, 60)], fill=ink)
    d.rectangle([(25, 65), (75, 95)], fill=ink)
    d.ellipse([(35, 100), (65, 130)], outline=ink, width=2)
    d.rectangle([(15, 132), (85, 138)], fill=ink)
    img.save(str(path))
    return str(path)

def create_it_round_seal():
    path = ASSETS_DIR / "it_round_seal.png"
    img = Image.new("RGBA", (280, 280), (255, 255, 255, 0))
    d = ImageDraw.Draw(img)
    ink = (70, 50, 140, 200)
    d.ellipse([10, 10, 270, 270], outline=ink, width=3)
    d.ellipse([24, 24, 256, 256], outline=ink, width=1)
    d.text((32, 50), "COMMISSIONER OF INCOME-TAX", fill=ink)
    d.text((80, 75), "(EXEMPTIONS)", fill=ink)
    d.rectangle([115, 110, 165, 165], outline=ink, width=2)
    d.text((105, 172), "सत्यमेव जयते", fill=ink)
    d.text((95, 210), "NASHIK / PUNE", fill=ink)
    img = img.rotate(6, resample=Image.BICUBIC)
    img.save(str(path))
    return str(path)

def create_despatched_stamp():
    path = ASSETS_DIR / "despatch_stamp.png"
    img = Image.new("RGBA", (220, 80), (255, 255, 255, 0))
    d = ImageDraw.Draw(img)
    ink = (40, 50, 90, 210)
    d.rectangle([5, 5, 215, 75], outline=ink, width=3)
    d.text((65, 12), "प्रेषण", fill=ink)
    d.text((25, 42), "DESPATCHED", fill=ink)
    img = img.rotate(-3, resample=Image.BICUBIC)
    img.save(str(path))
    return str(path)

def create_branding_assets():
    # 1. Logo
    logo_path = DOCS_DIR / "logo.png"
    img = Image.new("RGBA", (500, 160), (255, 255, 255, 0))
    d = ImageDraw.Draw(img)
    teal = (13, 148, 136, 255)
    d.ellipse([20, 20, 140, 140], fill=teal)
    d.text((165, 30), "SAMARPAN", fill=(15, 23, 42, 255))
    d.text((165, 80), "SOCIAL WELFARE TRUST", fill=(71, 85, 105, 255))
    d.text((165, 115), "MH/2020/0789123  •  NASHIK, MAHARASHTRA", fill=(100, 116, 139, 255))
    img.save(str(logo_path), "PNG")

    # 2. Stamp / Seal
    stamp_path = DOCS_DIR / "stamp.png"
    s_img = Image.new("RGBA", (320, 320), (255, 255, 255, 0))
    sd = ImageDraw.Draw(s_img)
    blue_ink = (26, 54, 93, 220)
    sd.ellipse([10, 10, 310, 310], outline=blue_ink, width=4)
    sd.ellipse([22, 22, 298, 298], outline=blue_ink, width=2)
    sd.text((45, 60), "SAMARPAN WELFARE TRUST", fill=blue_ink)
    sd.text((85, 95), "* NASHIK *", fill=blue_ink)
    sd.text((85, 150), "OFFICIAL SEAL", fill=blue_ink)
    sd.text((60, 185), "DARPAN: MH/2020/0789123", fill=blue_ink)
    sd.text((95, 220), "ESTD. 2014", fill=blue_ink)
    s_img.save(str(stamp_path), "PNG")

    # 3. Signature
    sig_path = DOCS_DIR / "signature.png"
    sig_img = Image.new("RGBA", (360, 140), (255, 255, 255, 0))
    sig_d = ImageDraw.Draw(sig_img)
    sig_color = (15, 23, 42, 240)
    sig_d.line([(30, 80), (55, 25), (75, 105), (110, 45), (150, 85), (190, 40), (230, 75), (310, 70)], fill=sig_color, width=3)
    sig_d.line([(60, 60), (270, 80)], fill=sig_color, width=2)
    sig_d.text((40, 105), "Sunita Deshmukh (Managing Trustee)", fill=(71, 85, 105, 255))
    sig_img.save(str(sig_path), "PNG")


# ---------------------------------------------------------------------------
# 2. Authentic Darpan Certificate PDF (Matches NITI Aayog Enrolment)
# ---------------------------------------------------------------------------

class GoldBorderCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations()
            super().showPage()
        super().save()

    def draw_page_decorations(self):
        self.saveState()
        self.setStrokeColor(colors.HexColor("#EAB308"))
        self.setLineWidth(7)
        self.rect(18, 18, 559, 806)
        self.setStrokeColor(colors.HexColor("#CA8A04"))
        self.setLineWidth(1)
        self.rect(25, 25, 545, 792)
        self.restoreState()


def make_darpan_pdf():
    pdf_path = DOCS_DIR / "Samarpan_Darpan_Certificate.pdf"
    emblem_path = create_gold_emblem()
    g20_path = create_g20_logo()
    banner_path = create_darpan_bottom_banner()

    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=A4,
        leftMargin=35,
        rightMargin=35,
        topMargin=40,
        bottomMargin=35,
    )

    styles = getSampleStyleSheet()

    header_left = ParagraphStyle(
        "HL", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=11, leading=14,
        alignment=TA_CENTER, textColor=colors.HexColor("#1E3A8A"),
    )
    header_sub = ParagraphStyle(
        "HS", parent=styles["Normal"], fontName="Helvetica", fontSize=7.5, leading=10.5,
        alignment=TA_CENTER, textColor=colors.HexColor("#1E3A8A"),
    )
    cert_title = ParagraphStyle(
        "CT", parent=styles["Normal"], fontName="Times-BoldItalic", fontSize=26, leading=32,
        alignment=TA_CENTER, textColor=colors.HexColor("#0F172A"),
    )
    to_style = ParagraphStyle(
        "TS", parent=styles["Normal"], fontName="Times-Roman", fontSize=13, leading=18,
        alignment=TA_CENTER, textColor=colors.HexColor("#0F172A"),
    )
    ngo_name_style = ParagraphStyle(
        "NNS", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=18, leading=22,
        alignment=TA_CENTER, textColor=colors.HexColor("#0F172A"),
    )
    body_desc = ParagraphStyle(
        "BD", parent=styles["Normal"], fontName="Times-Roman", fontSize=11, leading=17,
        alignment=TA_CENTER, textColor=colors.HexColor("#1E293B"),
    )
    unique_id_style = ParagraphStyle(
        "UIS", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=18, leading=22,
        alignment=TA_CENTER, textColor=colors.HexColor("#000000"),
    )

    story = [Spacer(1, 10)]

    left_block = [
        RLImage(emblem_path, width=0.55 * inch, height=0.72 * inch),
        Paragraph("<b>NITI Aayog</b>", header_left),
        Paragraph("(National Institution for Transforming India)<br/>(राष्ट्रीय भारत परिवर्तन संस्थान)<br/><b>(Govt. of India)</b>", header_sub),
    ]
    right_block = [RLImage(g20_path, width=1.6 * inch, height=1.0 * inch)]

    header_table = Table([[left_block, "", right_block]], colWidths=[3.2 * inch, 0.1 * inch, 3.2 * inch])
    header_table.setStyle(TableStyle([
        ("ALIGN", (0, 0), (0, 0), "CENTER"),
        ("ALIGN", (2, 0), (2, 0), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LINEBEFORE", (2, 0), (2, 0), 1, colors.HexColor("#CBD5E1")),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 35))

    story.append(Paragraph("Certificate of Enrolment", cert_title))
    story.append(Spacer(1, 20))
    story.append(Paragraph("To", to_style))
    story.append(Spacer(1, 22))

    story.append(Paragraph("SAMARPAN SOCIAL WELFARE TRUST", ngo_name_style))
    story.append(Spacer(1, 22))
    story.append(Paragraph("is", to_style))
    story.append(Spacer(1, 18))

    desc_text = (
        "enrolled with NGO Darpan Portal Offered by the NITI Aayog in Association "
        "with National Information Centre to bring about greater partnership between "
        "government &amp; Voluntary Sector and faster better transparency, efficiency "
        "and accountability with"
    )
    story.append(Paragraph(desc_text, body_desc))
    story.append(Spacer(1, 30))

    story.append(Paragraph("<b>Unique Id: MH/2020/0789123</b>", unique_id_style))
    story.append(Spacer(1, 35))

    story.append(RLImage(banner_path, width=4.5 * inch, height=0.95 * inch))

    doc.build(story, canvasmaker=GoldBorderCanvas)
    print(f"Generated: {pdf_path}")


# ---------------------------------------------------------------------------
# 3. Authentic Income Tax Department 12A/80G Certificates
# ---------------------------------------------------------------------------

def make_12a_pdf():
    pdf_path = DOCS_DIR / "Samarpan_12A_Certificate.pdf"
    emblem_black = create_it_black_emblem()
    round_seal = create_it_round_seal()
    despatch_stamp = create_despatched_stamp()

    doc = SimpleDocTemplate(str(pdf_path), pagesize=A4, leftMargin=40, rightMargin=40, topMargin=40, bottomMargin=40)
    styles = getSampleStyleSheet()

    dept_hdr = ParagraphStyle("DH", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=9.5, leading=13, alignment=TA_CENTER)
    dept_sub = ParagraphStyle("DS", parent=styles["Normal"], fontName="Helvetica", fontSize=8, leading=11, alignment=TA_CENTER)
    ref_style = ParagraphStyle("RS", parent=styles["Normal"], fontName="Helvetica", fontSize=8.5, leading=12)
    box_title = ParagraphStyle("BT", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=10, leading=14, alignment=TA_CENTER)
    body_para = ParagraphStyle("BP", parent=styles["Normal"], fontName="Times-Roman", fontSize=9.5, leading=14.5, alignment=TA_JUSTIFY)
    officer_style = ParagraphStyle("OS", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=8.5, leading=12, alignment=TA_CENTER)

    story = []

    hdr_table = Table([
        [RLImage(emblem_black, width=0.45 * inch, height=0.62 * inch),
         [Paragraph("OFFICE OF THE COMMISSIONER OF INCOME TAX (EXEMPTIONS)", dept_hdr),
          Paragraph("AAYAKAR BHAWAN, BODHLE NAGAR, NASHIK – 422 001<br/>Phone: 0253-2501234 • Fax: 0253-2501235", dept_sub)]]
    ], colWidths=[0.8 * inch, 6.2 * inch])
    hdr_table.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("ALIGN", (0, 0), (0, 0), "CENTER")]))
    story.append(hdr_table)
    story.append(Spacer(1, 12))

    ref_table = Table([
        [Paragraph("<b>No.NSK/CIT(E)/12A(a)/2020-21 / 7891 (a)</b>", ref_style),
         Paragraph("<b>Date : 14.10.2020.</b>", ref_style)]
    ], colWidths=[4.5 * inch, 2.5 * inch])
    ref_table.setStyle(TableStyle([("ALIGN", (1, 0), (1, 0), "RIGHT")]))
    story.append(ref_table)
    story.append(Spacer(1, 10))

    title_box = Table([[Paragraph("<b>REGISTRATION UNDER SECTION 12AA OF THE INCOME TAX ACT, 1961</b>", box_title)]], colWidths=[7.0 * inch])
    title_box.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#000000")), ("PADDING", (0, 0), (-1, -1), 4), ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FAFAFA"))]))
    story.append(title_box)
    story.append(Spacer(1, 14))

    p1 = (
        "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<b>Samarpan Social Welfare Trust</b>, "
        "Plot No. 42, Anand Nagar, Gangapur Road, Nashik, Maharashtra, 422013, was incorporated by the Trust Deed "
        "registered with the Charity Commissioner, Nashik on 12.08.2014 and has filed application "
        "in Form No. 10A for grant of registration as a charitable trust under section 12A(a) of the I.T. Act, 1961."
    )
    story.append(Paragraph(p1, body_para))
    story.append(Spacer(1, 10))

    p2 = "2.&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;The Trust is registered as a Charitable Trust w.e.f. <b>01.04.2014</b>."
    story.append(Paragraph(p2, body_para))
    story.append(Spacer(1, 8))

    p3 = (
        "3.&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Unique Registration Number (URN): <b>AAATS9876ME20211</b>. "
        "NITI Aayog Darpan Unique ID: <b>MH/2020/0789123</b>."
    )
    story.append(Paragraph(p3, body_para))
    story.append(Spacer(1, 14))

    sig_block = Table([
        ["", RLImage(round_seal, width=1.4 * inch, height=1.4 * inch),
         Paragraph("<b>( VIJAY SHEKHAWAT )</b><br/>Commissioner of Income-tax (Exemptions),<br/>NASHIK", officer_style)]
    ], colWidths=[3.0 * inch, 1.8 * inch, 2.2 * inch])
    sig_block.setStyle(TableStyle([("ALIGN", (1, 0), (2, 0), "CENTER"), ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
    story.append(sig_block)
    story.append(Spacer(1, 14))

    bottom_table = Table([
        [RLImage(despatch_stamp, width=1.5 * inch, height=0.55 * inch),
         Paragraph("<b>( R.K. Patil )</b><br/>Income-tax Officer (HQ)<br/>NASHIK", officer_style)]
    ], colWidths=[3.5 * inch, 3.5 * inch])
    story.append(bottom_table)

    doc.build(story)
    print(f"Generated: {pdf_path}")


def make_80g_pdf():
    pdf_path = DOCS_DIR / "Samarpan_80G_Certificate.pdf"
    emblem_black = ASSETS_DIR / "it_emblem_black.png"
    round_seal = ASSETS_DIR / "it_round_seal.png"
    despatch_stamp = ASSETS_DIR / "despatch_stamp.png"

    doc = SimpleDocTemplate(str(pdf_path), pagesize=A4, leftMargin=40, rightMargin=40, topMargin=40, bottomMargin=40)
    styles = getSampleStyleSheet()

    dept_hdr = ParagraphStyle("DH8", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=9.5, leading=13, alignment=TA_CENTER)
    dept_sub = ParagraphStyle("DS8", parent=styles["Normal"], fontName="Helvetica", fontSize=8, leading=11, alignment=TA_CENTER)
    ref_style = ParagraphStyle("RS8", parent=styles["Normal"], fontName="Helvetica", fontSize=8.5, leading=12)
    box_title = ParagraphStyle("BT8", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=10, leading=14, alignment=TA_CENTER)
    body_para = ParagraphStyle("BP8", parent=styles["Normal"], fontName="Times-Roman", fontSize=9.5, leading=14.5, alignment=TA_JUSTIFY)
    officer_style = ParagraphStyle("OS8", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=8.5, leading=12, alignment=TA_CENTER)

    story = []

    hdr_table = Table([
        [RLImage(str(emblem_black), width=0.45 * inch, height=0.62 * inch),
         [Paragraph("OFFICE OF THE COMMISSIONER OF INCOME TAX (EXEMPTIONS)", dept_hdr),
          Paragraph("AAYAKAR BHAWAN, BODHLE NAGAR, NASHIK – 422 001", dept_sub)]]
    ], colWidths=[0.8 * inch, 6.2 * inch])
    hdr_table.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("ALIGN", (0, 0), (0, 0), "CENTER")]))
    story.append(hdr_table)
    story.append(Spacer(1, 12))

    ref_table = Table([
        [Paragraph("<b>No.NSK/CIT(E)/80G(5)(vi)/2020-21 / 8912 (b)</b>", ref_style),
         Paragraph("<b>Date : 14.10.2020.</b>", ref_style)]
    ], colWidths=[4.5 * inch, 2.5 * inch])
    ref_table.setStyle(TableStyle([("ALIGN", (1, 0), (1, 0), "RIGHT")]))
    story.append(ref_table)
    story.append(Spacer(1, 10))

    title_box = Table([[Paragraph("<b>CERTIFICATE OF APPROVAL UNDER SECTION 80G(5)(vi) OF THE INCOME TAX ACT, 1961</b>", box_title)]], colWidths=[7.0 * inch])
    title_box.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#000000")), ("PADDING", (0, 0), (-1, -1), 4), ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FAFAFA"))]))
    story.append(title_box)
    story.append(Spacer(1, 14))

    p1 = (
        "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Approval is hereby granted to <b>Samarpan Social Welfare Trust</b>, "
        "Plot No. 42, Anand Nagar, Gangapur Road, Nashik, Maharashtra, 422013, under Section 80G(5)(vi) of the Income-tax Act, 1961. "
        "Unique Registration Number (URN): <b>AAATS9876MF20212</b>. Darpan ID: <b>MH/2020/0789123</b>."
    )
    story.append(Paragraph(p1, body_para))
    story.append(Spacer(1, 14))

    sig_block = Table([
        ["", RLImage(str(round_seal), width=1.4 * inch, height=1.4 * inch),
         Paragraph("<b>( VIJAY SHEKHAWAT )</b><br/>Commissioner of Income-tax (Exemptions),<br/>NASHIK", officer_style)]
    ], colWidths=[3.0 * inch, 1.8 * inch, 2.2 * inch])
    sig_block.setStyle(TableStyle([("ALIGN", (1, 0), (2, 0), "CENTER"), ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
    story.append(sig_block)
    story.append(Spacer(1, 14))

    bottom_table = Table([
        [RLImage(str(despatch_stamp), width=1.5 * inch, height=0.55 * inch),
         Paragraph("<b>( R.K. Patil )</b><br/>Income-tax Officer (HQ)<br/>NASHIK", officer_style)]
    ], colWidths=[3.5 * inch, 3.5 * inch])
    story.append(bottom_table)

    doc.build(story)
    print(f"Generated: {pdf_path}")


def make_audit_and_report_pdfs():
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("T", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=14, leading=18, alignment=TA_CENTER, textColor=colors.HexColor("#1A365D"))
    sub_style = ParagraphStyle("S", parent=styles["Normal"], fontName="Helvetica", fontSize=9, leading=13, alignment=TA_CENTER, textColor=colors.HexColor("#4A5568"))
    body = ParagraphStyle("B", parent=styles["Normal"], fontName="Times-Roman", fontSize=9.5, leading=14, alignment=TA_JUSTIFY)
    bold = ParagraphStyle("BL", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=9, leading=13)
    val = ParagraphStyle("V", parent=styles["Normal"], fontName="Helvetica", fontSize=9, leading=13)

    # 1. Balance Sheet
    bs_path = DOCS_DIR / "Samarpan_Audited_Balance_Sheet_FY25.pdf"
    doc_bs = SimpleDocTemplate(str(bs_path), pagesize=A4, leftMargin=40, rightMargin=40, topMargin=40, bottomMargin=40)
    story_bs = [
        Paragraph("SAMARPAN SOCIAL WELFARE TRUST", title_style),
        Paragraph("AUDITED BALANCE SHEET AS ON 31ST MARCH 2025 (FY 2024-25)", sub_style),
        Paragraph("Darpan ID: <b>MH/2020/0789123</b> • 12A URN: <b>AAATS9876ME20211</b>", sub_style),
        Spacer(1, 12),
        HRFlowable(width="100%", thickness=1, color=colors.HexColor("#CBD5E1"), spaceAfter=10),
    ]
    data_bs = [
        [Paragraph("<b>Particulars</b>", bold), Paragraph("<b>FY 2024-25 (₹)</b>", bold), Paragraph("<b>FY 2023-24 (₹)</b>", bold)],
        [Paragraph("Corpus Fund & Reserves", val), Paragraph("₹ 1,45,20,000", val), Paragraph("₹ 1,18,50,000", val)],
        [Paragraph("Grant / Project Funds (Education & Health)", val), Paragraph("₹ 3,25,80,000", val), Paragraph("₹ 2,75,30,000", val)],
        [Paragraph("Current Liabilities", val), Paragraph("₹ 12,40,000", val), Paragraph("₹ 9,80,000", val)],
        [Paragraph("<b>Total Liabilities & Funds</b>", bold), Paragraph("<b>₹ 4,83,40,000</b>", bold), Paragraph("<b>₹ 4,03,60,000</b>", bold)],
        [Paragraph("Fixed Assets (Community Centers & Clinics)", val), Paragraph("₹ 1,82,50,000", val), Paragraph("₹ 1,60,20,000", val)],
        [Paragraph("Program Expenditure Applied", val), Paragraph("₹ 2,65,40,000", val), Paragraph("₹ 2,15,80,000", val)],
        [Paragraph("Cash & Bank Balances (SBI Nashik)", val), Paragraph("₹ 35,50,000", val), Paragraph("₹ 27,60,000", val)],
        [Paragraph("<b>Total Assets</b>", bold), Paragraph("<b>₹ 4,83,40,000</b>", bold), Paragraph("<b>₹ 4,03,60,000</b>", bold)],
    ]
    t_bs = Table(data_bs, colWidths=[3.2 * inch, 1.9 * inch, 1.9 * inch])
    t_bs.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")), ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F1F5F9")), ("PADDING", (0, 0), (-1, -1), 5)]))
    story_bs.append(t_bs)
    story_bs.append(Spacer(1, 15))
    story_bs.append(Paragraph("<b>Auditor Attestation:</b> Certified that administrative expenses stand at <b>4.6%</b>, within statutory CSR limits (&le; 5%). Audited by Joshi & Kulkarni, Chartered Accountants (M. No. 045129).", body))
    doc_bs.build(story_bs)
    print(f"Generated: {bs_path}")

    # 2. Annual Report
    ar_path = DOCS_DIR / "Samarpan_Annual_Report_FY25.pdf"
    doc_ar = SimpleDocTemplate(str(ar_path), pagesize=A4, leftMargin=40, rightMargin=40, topMargin=40, bottomMargin=40)
    story_ar = [
        Paragraph("SAMARPAN SOCIAL WELFARE TRUST", title_style),
        Paragraph("ANNUAL ACTIVITY & IMPACT REPORT 2024-25", sub_style),
        Spacer(1, 12),
        HRFlowable(width="100%", thickness=1, color=colors.HexColor("#CBD5E1"), spaceAfter=10),
        Paragraph("<b>1. Executive Summary & Mission:</b> Samarpan Social Welfare Trust operates across Nashik, Dhule, and Nandurbar districts in Maharashtra, focusing on maternal healthcare, tribal education, and women-led dairy cooperatives. In FY25, the trust directly supported 14,200 rural families.", body),
        Spacer(1, 8),
        Paragraph("<b>2. Key Program Achievements:</b><br/>• Mobile Health Clinics: Conducted 240 medical camps screening 18,500 villagers.<br/>• Balwadi Early Education: Supported 32 community learning centers with 1,250 tribal children enrolled.<br/>• Women Self-Help Groups (SHGs): Facilitated micro-enterprise training for 450 women with 98% loan repayment rate.", body),
        Spacer(1, 8),
        Paragraph("<b>3. Governance & Transparency:</b> Registered under Maharashtra Public Trusts Act, 1950 (Reg No. E-3412/Nashik). Darpan Unique ID: <b>MH/2020/0789123</b>. 12A & 80G compliant.", body),
    ]
    doc_ar.build(story_ar)
    print(f"Generated: {ar_path}")


def make_cheatsheet():
    txt_path = DOCS_DIR / "Registration_CheatSheet.txt"
    content = """=============================================================================
GRANTSETU — FRESH NGO REGISTRATION CHEATSHEET: SAMARPAN SOCIAL WELFARE TRUST
Use these exact details to test http://localhost:5173/register
(This Darpan ID and NGO are 100% FRESH and UNREGISTERED in the database)
=============================================================================

STEP 1: ADMIN & IDENTITY
---------------------------------
Admin Full Name:        Sunita Deshmukh
Official Designation:   Managing Trustee (or select from dropdown)
Contact Mobile Number:  9822334455
Login Work Email:       sunita.deshmukh@samarpantrust.org  (or any fresh email you choose)
Account Password:       SamarpanTest@123

STEP 2: STATUTORY NGO CREDENTIALS
---------------------------------
Official NGO Name:      Samarpan Social Welfare Trust
Incorporation Year:     2014
State:                  Maharashtra
District:               Nashik
NGO Darpan ID:          MH/2020/0789123

Legal Status Checkboxes:
  [X] 12A Registration Active     (URN: AAATS9876ME20211)
  [X] 80G Tax Exemption Active    (URN: AAATS9876MF20212)
  [ ] FCRA Approved               (Leave UNCHECKED - Domestic NGO)

STEP 3: VERIFICATION PROOF UPLOADS (Files located in data/sample_documents/samarpan/)
------------------------------------------------------------------------------------
1. Darpan Certificate (Mandatory):
   -> Choose File: Samarpan_Darpan_Certificate.pdf
   (Contains "MH/2020/0789123" and "Samarpan Social Welfare Trust" -> triggers "document_matched ✓")

2. 12A Certificate (Optional / Recommended):
   -> Choose File: Samarpan_12A_Certificate.pdf

3. 80G Certificate (Optional / Recommended):
   -> Choose File: Samarpan_80G_Certificate.pdf

ADDITIONAL DOCUMENTS FOR THE DOCUMENT VAULT (data/sample_documents/samarpan/):
-----------------------------------------------------------------------------
- Financials:   Samarpan_Audited_Balance_Sheet_FY25.pdf
- Past Impact:  Samarpan_Annual_Report_FY25.pdf
- Branding:
  * Official Logo:              logo.png (Transparent teal emblem)
  * Rubber Stamp / Seal:        stamp.png (Official double-circle seal)
  * Authorized Signature:       signature.png (Sunita Deshmukh signature)
=============================================================================
"""
    txt_path.write_text(content, encoding="utf-8")
    print(f"Generated: {txt_path}")


if __name__ == "__main__":
    make_darpan_pdf()
    make_12a_pdf()
    make_80g_pdf()
    make_audit_and_report_pdfs()
    create_branding_assets()
    make_cheatsheet()
    print("\nAll Samarpan sample documents generated successfully in data/sample_documents/samarpan/")
