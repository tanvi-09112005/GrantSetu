"""Generate high-fidelity authentic replicas of:
1. NITI Aayog NGO-Darpan Certificate of Enrolment (matching media_1790918008358.png)
2. Income Tax Dept 12AA Registration Order (matching media_1790918064128.jpg)
3. Income Tax Dept 80G Approval Certificate
For Child Rights and You (CRY).
"""

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.pdfgen import canvas

BASE_DIR = Path(__file__).resolve().parents[2]
DOCS_DIR = BASE_DIR / "data" / "sample_documents" / "cry"
ASSETS_DIR = DOCS_DIR / "assets"
DOCS_DIR.mkdir(parents=True, exist_ok=True)
ASSETS_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# 1. Generate Supporting Graphic Assets with Pillow
# ---------------------------------------------------------------------------

def create_gold_emblem():
    """Ashok Stambh Emblem in gold/bronze for NITI Aayog header."""
    path = ASSETS_DIR / "emblem_gold.png"
    img = Image.new("RGBA", (140, 180), (255, 255, 255, 0))
    d = ImageDraw.Draw(img)
    gold = (180, 130, 20, 255)
    # Lions shape silhouette
    d.polygon([(70, 15), (45, 55), (95, 55)], fill=gold)
    d.polygon([(30, 45), (15, 80), (55, 80)], fill=gold)
    d.polygon([(110, 45), (85, 80), (125, 80)], fill=gold)
    d.rectangle([35, 85, 105, 115], fill=gold) # central body
    # Ashoka chakra base
    d.ellipse([50, 120, 90, 160], outline=gold, width=3)
    d.line([(70, 120), (70, 160)], fill=gold, width=2)
    d.line([(50, 140), (90, 140)], fill=gold, width=2)
    # Base pedestal
    d.rectangle([25, 165, 115, 175], fill=gold)
    d.text((36, 150), "सत्यमेव जयते", fill=gold)
    img.save(str(path))
    return str(path)

def create_g20_logo():
    """G20 Bharat 2023 India logo."""
    path = ASSETS_DIR / "g20_logo.png"
    img = Image.new("RGBA", (220, 140), (255, 255, 255, 0))
    d = ImageDraw.Draw(img)
    orange = (235, 100, 20, 255)
    blue = (25, 110, 190, 255)
    green = (25, 140, 40, 255)
    dark = (40, 50, 60, 255)
    # Draw G20 text
    d.text((20, 20), "G", fill=orange)
    d.text((60, 20), "2", fill=blue)
    # Globe / Lotus circle
    d.ellipse([95, 20, 145, 70], outline=blue, width=3)
    d.arc([95, 20, 145, 70], start=30, end=150, fill=green, width=4)
    # Bharat 2023 India text
    d.text((60, 85), "भारत 2023 INDIA", fill=dark)
    d.text((45, 108), "वयुधैव कुटुम्बकम्", fill=orange)
    img.save(str(path))
    return str(path)

def create_darpan_bottom_banner():
    """Blue rounded bottom banner with NGO Darpan branding."""
    path = ASSETS_DIR / "darpan_bottom_banner.png"
    img = Image.new("RGBA", (480, 100), (255, 255, 255, 0))
    d = ImageDraw.Draw(img)
    # Blue background with gradient look
    blue_bg = (24, 76, 158, 255)
    d.rounded_rectangle([10, 10, 470, 90], radius=12, fill=blue_bg)
    # Small white emblem silhouette
    d.rectangle([35, 25, 65, 75], outline=(255, 255, 255, 240), width=2)
    d.text((37, 77), "सत्यमेव", fill=(255, 255, 255, 240))
    # NGO text on tricolor card
    d.rectangle([110, 25, 190, 75], fill=(255, 255, 255, 255))
    d.text((120, 35), "NGO", fill=(30, 41, 59, 255))
    # Gold Darpan circle
    gold = (234, 179, 8, 255)
    d.ellipse([215, 28, 265, 72], fill=gold)
    d.text((233, 40), "D", fill=(24, 76, 158, 255))
    # DARPAN text
    d.text((275, 40), "ARPAN", fill=(255, 255, 255, 255))
    img.save(str(path))
    return str(path)

def create_it_black_emblem():
    """Black national emblem for Income Tax Department header."""
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
    """Purple ink rubber stamp for Commissioner of Income Tax."""
    path = ASSETS_DIR / "it_round_seal.png"
    img = Image.new("RGBA", (280, 280), (255, 255, 255, 0))
    d = ImageDraw.Draw(img)
    ink = (70, 50, 140, 200) # authentic faded purple/violet official stamp ink
    d.ellipse([10, 10, 270, 270], outline=ink, width=3)
    d.ellipse([24, 24, 256, 256], outline=ink, width=1)
    # Circular text
    d.text((32, 50), "COMMISSIONER OF INCOME-TAX", fill=ink)
    d.text((80, 75), "(EXEMPTIONS)", fill=ink)
    # Center emblem & text
    d.rectangle([115, 110, 165, 165], outline=ink, width=2)
    d.text((105, 172), "सत्यमेव जयते", fill=ink)
    d.text((95, 210), "NEW DELHI", fill=ink)
    # Add slight rotation angle for authentic stamped effect
    img = img.rotate(8, resample=Image.BICUBIC)
    img.save(str(path))
    return str(path)

def create_despatched_stamp():
    """Rectangular authentic 'प्रेषण / DESPATCHED' ink stamp."""
    path = ASSETS_DIR / "despatch_stamp.png"
    img = Image.new("RGBA", (220, 80), (255, 255, 255, 0))
    d = ImageDraw.Draw(img)
    ink = (40, 50, 90, 210) # faded blue-black stamp
    d.rectangle([5, 5, 215, 75], outline=ink, width=3)
    d.text((65, 12), "प्रेषण", fill=ink)
    d.text((25, 42), "DESPATCHED", fill=ink)
    img = img.rotate(-4, resample=Image.BICUBIC)
    img.save(str(path))
    return str(path)

def create_commissioner_signature():
    """Authentic officer signature."""
    path = ASSETS_DIR / "commissioner_sig.png"
    img = Image.new("RGBA", (260, 100), (255, 255, 255, 0))
    d = ImageDraw.Draw(img)
    ink = (15, 23, 42, 230)
    d.line([(20, 60), (45, 20), (60, 85), (90, 35), (130, 70), (170, 25), (210, 60), (245, 55)], fill=ink, width=2)
    d.line([(40, 55), (220, 65)], fill=ink, width=2)
    img.save(str(path))
    return str(path)


# ---------------------------------------------------------------------------
# 2. Build Authentic NITI Aayog Darpan Certificate of Enrolment PDF
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
            self.draw_page_decorations()
            super().showPage()
        super().save()

    def draw_page_decorations(self):
        # Draw the yellow/gold patterned border from media_1790918008358.png
        self.saveState()
        gold_outer = colors.HexColor("#EAB308")
        gold_inner = colors.HexColor("#CA8A04")
        # Thick patterned outer border
        self.setStrokeColor(gold_outer)
        self.setLineWidth(7)
        self.rect(18, 18, 559, 806)
        # Inner fine line
        self.setStrokeColor(gold_inner)
        self.setLineWidth(1)
        self.rect(25, 25, 545, 792)
        self.restoreState()


def build_darpan_pdf():
    pdf_path = DOCS_DIR / "CRY_Darpan_Registration_Certificate.pdf"
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
        "HeaderLeft",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=14,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#1E3A8A"), # NITI blue
    )

    header_sub = ParagraphStyle(
        "HeaderSub",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=7.5,
        leading=10.5,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#1E3A8A"),
    )

    cert_title = ParagraphStyle(
        "CertTitle",
        parent=styles["Normal"],
        fontName="Times-BoldItalic",
        fontSize=26,
        leading=32,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#0F172A"),
    )

    to_style = ParagraphStyle(
        "ToStyle",
        parent=styles["Normal"],
        fontName="Times-Roman",
        fontSize=13,
        leading=18,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#0F172A"),
    )

    ngo_name_style = ParagraphStyle(
        "NgoNameStyle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#0F172A"),
    )

    body_desc = ParagraphStyle(
        "BodyDesc",
        parent=styles["Normal"],
        fontName="Times-Roman",
        fontSize=11,
        leading=17,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#1E293B"),
    )

    unique_id_style = ParagraphStyle(
        "UniqueIdStyle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=17,
        leading=22,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#000000"),
    )

    story = []
    story.append(Spacer(1, 10))

    # Top Header Grid: [Emblem + NITI Aayog text] | [Vertical line] | [G20 Logo]
    left_block = [
        RLImage(emblem_path, width=0.55 * inch, height=0.72 * inch),
        Paragraph("<b>NITI Aayog</b>", header_left),
        Paragraph("(National Institution for Transforming India)<br/>(राष्ट्रीय भारत परिवर्तन संस्थान)<br/><b>(Govt. of India)</b>", header_sub),
    ]

    right_block = [
        RLImage(g20_path, width=1.6 * inch, height=1.0 * inch),
    ]

    header_table = Table(
        [[left_block, "", right_block]],
        colWidths=[3.2 * inch, 0.1 * inch, 3.2 * inch]
    )
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

    story.append(Paragraph("CHILD RIGHTS AND YOU (CRY)", ngo_name_style))
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

    # Big Unique ID matching user's image exactly
    story.append(Paragraph("<b>Unique Id: DL/2009/0014766</b>", unique_id_style))
    story.append(Spacer(1, 35))

    # Bottom blue banner matching image
    story.append(RLImage(banner_path, width=4.5 * inch, height=0.95 * inch))

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"Generated authentic Darpan PDF: {pdf_path}")


# ---------------------------------------------------------------------------
# 3. Build Authentic Income Tax Dept 12AA Registration Order PDF
# ---------------------------------------------------------------------------

def build_12a_pdf():
    pdf_path = DOCS_DIR / "CRY_12A_Registration_Certificate.pdf"
    emblem_black = create_it_black_emblem()
    round_seal = create_it_round_seal()
    despatch_stamp = create_despatched_stamp()
    sig = create_commissioner_signature()

    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=A4,
        leftMargin=40,
        rightMargin=40,
        topMargin=40,
        bottomMargin=40,
    )

    styles = getSampleStyleSheet()

    dept_hdr = ParagraphStyle(
        "DeptHdr",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=9.5,
        leading=13,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#1A202C"),
    )

    dept_sub = ParagraphStyle(
        "DeptSub",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=11,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#2D3748"),
    )

    ref_style = ParagraphStyle(
        "RefStyle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor("#1A202C"),
    )

    box_title = ParagraphStyle(
        "BoxTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=10,
        leading=14,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#000000"),
    )

    body_para = ParagraphStyle(
        "BodyPara",
        parent=styles["Normal"],
        fontName="Times-Roman",
        fontSize=9.5,
        leading=14.5,
        alignment=TA_JUSTIFY,
        textColor=colors.HexColor("#1A202C"),
    )

    officer_style = ParagraphStyle(
        "OfficerStyle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8.5,
        leading=12,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#1A202C"),
    )

    story = []

    # Top Header with Ashok Stambh + Office Title
    hdr_table = Table([
        [RLImage(emblem_black, width=0.45 * inch, height=0.62 * inch),
         [Paragraph("OFFICE OF THE COMMISSIONER OF INCOME TAX (EXEMPTIONS)", dept_hdr),
          Paragraph("6TH FLOOR, MAYUR BHAWAN, CONNAUGHT CIRCUS, NEW DELHI – 110 001<br/>Phone: 011-23412345 • Fax: 011-23412346", dept_sub)]]
    ], colWidths=[0.8 * inch, 6.2 * inch])
    hdr_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (0, 0), "CENTER"),
    ]))
    story.append(hdr_table)
    story.append(Spacer(1, 12))

    # Reference Number and Date
    ref_table = Table([
        [Paragraph("<b>No.DEL/CIT(E)/12A(a)/516/2013-14 / 4530 (a)</b>", ref_style),
         Paragraph("<b>Date : 18.03.2014.</b>", ref_style)]
    ], colWidths=[4.5 * inch, 2.5 * inch])
    ref_table.setStyle(TableStyle([
        ("ALIGN", (1, 0), (1, 0), "RIGHT"),
    ]))
    story.append(ref_table)
    story.append(Spacer(1, 10))

    # Bordered Title Box matching image 2
    title_box = Table([
        [Paragraph("<b>REGISTRATION UNDER SECTION 12AA OF THE INCOME TAX ACT, 1961</b>", box_title)]
    ], colWidths=[7.0 * inch])
    title_box.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#000000")),
        ("PADDING", (0, 0), (-1, -1), 4),
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FAFAFA")),
    ]))
    story.append(title_box)
    story.append(Spacer(1, 14))

    # Body Paragraph matching image 2 verbatim
    p1 = (
        "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<b>Child Rights and You (CRY)</b>, "
        "c/o 630, Anand Bhavan, South Delhi, Delhi, 110049, was incorporated by the Trust Deed "
        "registered with the Charity Commissioner / Sub-Registrar on 18.04.1979 and has filed application "
        "in Form No. 10A for grant of registration as a charitable or religious trust under section 12 A(a) "
        "of the I.T. Act, 1961 on 07.08.2013."
    )
    story.append(Paragraph(p1, body_para))
    story.append(Spacer(1, 10))

    p2 = "2.&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;The Trust is registered as a Charitable / Religious Trust w.e.f. <b>01.04.2013</b>."
    story.append(Paragraph(p2, body_para))
    story.append(Spacer(1, 8))

    p3 = (
        "3.&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;The application has been entered at <b>No. 516</b> in the register "
        "of application under section 12AA maintained in this office. Unique Registration Number (URN): <b>AAATC1234A</b>."
    )
    story.append(Paragraph(p3, body_para))
    story.append(Spacer(1, 14))

    # Commissioner Signature block with Round Ink Seal side-by-side
    sig_block = Table([
        ["",
         RLImage(round_seal, width=1.4 * inch, height=1.4 * inch),
         [RLImage(sig, width=1.6 * inch, height=0.5 * inch),
          Paragraph("<b>( PRAMOD KUMAR )</b><br/>Commissioner of Income-tax (Exemptions),<br/>NEW DELHI", officer_style)]]
    ], colWidths=[2.5 * inch, 2.0 * inch, 2.5 * inch])
    sig_block.setStyle(TableStyle([
        ("ALIGN", (1, 0), (1, 0), "CENTER"),
        ("ALIGN", (2, 0), (2, 0), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(sig_block)
    story.append(Spacer(1, 10))

    # Copy to Section
    c_head = Paragraph("<b>Copy to :</b>", ref_style)
    c1 = (
        "1.&nbsp;&nbsp;&nbsp;&nbsp;<b>Child Rights and You (CRY)</b>,<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;630, Anand Bhavan, South Delhi, Delhi, 110049<br/><br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<i>It may be noted that registration of a Trust / Society u/s 12AA of the Income-tax Act, 1961, is one of the necessary conditions for grant of an exemption certificates u/s 80G(5) of the Act, registration u/s 12AA of the Act does not automatically entitles a Trust/ Society for grant of a Certificate u/s 80G(5) of the Act and that other conditions for such an entitlement has to be satisfied.</i>"
    )
    c2 = "2.&nbsp;&nbsp;&nbsp;&nbsp;The Jt. CIT, Exemptions Range, New Delhi."
    c3 = "3.&nbsp;&nbsp;&nbsp;&nbsp;The ACIT, Circle-1 (Exemptions), New Delhi."

    story.append(c_head)
    story.append(Spacer(1, 4))
    story.append(Paragraph(c1, body_para))
    story.append(Spacer(1, 6))
    story.append(Paragraph(c2, body_para))
    story.append(Spacer(1, 4))
    story.append(Paragraph(c3, body_para))
    story.append(Spacer(1, 16))

    # Bottom Officers + Despatched Ink Stamp
    bottom_table = Table([
        [RLImage(despatch_stamp, width=1.5 * inch, height=0.55 * inch),
         [Paragraph("<b>( A.D. Jadhav )</b><br/>Income-tax Officer (HQ)<br/>for Commissioner of Income-tax (Exemptions),<br/>NEW DELHI", officer_style)]]
    ], colWidths=[3.5 * inch, 3.5 * inch])
    bottom_table.setStyle(TableStyle([
        ("ALIGN", (0, 0), (0, 0), "LEFT"),
        ("ALIGN", (1, 0), (1, 0), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(bottom_table)

    doc.build(story)
    print(f"Generated authentic 12AA PDF: {pdf_path}")


# ---------------------------------------------------------------------------
# 4. Build Authentic Income Tax Dept 80G Approval Certificate PDF
# ---------------------------------------------------------------------------

def build_80g_pdf():
    pdf_path = DOCS_DIR / "CRY_80G_Certificate.pdf"
    emblem_black = ASSETS_DIR / "it_emblem_black.png"
    round_seal = ASSETS_DIR / "it_round_seal.png"
    despatch_stamp = ASSETS_DIR / "despatch_stamp.png"
    sig = ASSETS_DIR / "commissioner_sig.png"

    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=A4,
        leftMargin=40,
        rightMargin=40,
        topMargin=40,
        bottomMargin=40,
    )

    styles = getSampleStyleSheet()

    dept_hdr = ParagraphStyle("Hdr80G", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=9.5, leading=13, alignment=TA_CENTER)
    dept_sub = ParagraphStyle("Sub80G", parent=styles["Normal"], fontName="Helvetica", fontSize=8, leading=11, alignment=TA_CENTER)
    ref_style = ParagraphStyle("Ref80G", parent=styles["Normal"], fontName="Helvetica", fontSize=8.5, leading=12)
    box_title = ParagraphStyle("Box80G", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=10, leading=14, alignment=TA_CENTER)
    body_para = ParagraphStyle("Body80G", parent=styles["Normal"], fontName="Times-Roman", fontSize=9.5, leading=14.5, alignment=TA_JUSTIFY)
    officer_style = ParagraphStyle("Off80G", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=8.5, leading=12, alignment=TA_CENTER)

    story = []

    hdr_table = Table([
        [RLImage(str(emblem_black), width=0.45 * inch, height=0.62 * inch),
         [Paragraph("OFFICE OF THE COMMISSIONER OF INCOME TAX (EXEMPTIONS)", dept_hdr),
          Paragraph("6TH FLOOR, MAYUR BHAWAN, CONNAUGHT CIRCUS, NEW DELHI – 110 001<br/>Phone: 011-23412345 • Fax: 011-23412346", dept_sub)]]
    ], colWidths=[0.8 * inch, 6.2 * inch])
    hdr_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (0, 0), "CENTER"),
    ]))
    story.append(hdr_table)
    story.append(Spacer(1, 12))

    ref_table = Table([
        [Paragraph("<b>No.DEL/CIT(E)/80G(5)(vi)/2014-15 / 5120 (b)</b>", ref_style),
         Paragraph("<b>Date : 24.09.2014.</b>", ref_style)]
    ], colWidths=[4.5 * inch, 2.5 * inch])
    ref_table.setStyle(TableStyle([("ALIGN", (1, 0), (1, 0), "RIGHT")]))
    story.append(ref_table)
    story.append(Spacer(1, 10))

    title_box = Table([
        [Paragraph("<b>CERTIFICATE OF APPROVAL UNDER SECTION 80G(5)(vi) OF THE INCOME TAX ACT, 1961</b>", box_title)]
    ], colWidths=[7.0 * inch])
    title_box.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#000000")),
        ("PADDING", (0, 0), (-1, -1), 4),
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FAFAFA")),
    ]))
    story.append(title_box)
    story.append(Spacer(1, 14))

    p1 = (
        "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Approval is hereby granted to <b>Child Rights and You (CRY)</b>, "
        "630, Anand Bhavan, South Delhi, Delhi, 110049, under Section 80G(5)(vi) of the Income-tax Act, 1961. "
        "Donations made to the institution are entitled to deduction in the hands of the donors as specified under Section 80G."
    )
    story.append(Paragraph(p1, body_para))
    story.append(Spacer(1, 10))

    p2 = "2.&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;The approval is granted in perpetuity subject to continued compliance with statutory provisions."
    story.append(Paragraph(p2, body_para))
    story.append(Spacer(1, 8))

    p3 = (
        "3.&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Unique Registration Number (URN) for 80G deduction receipts: "
        "<b>AAATC1234B</b>. Receipts issued to donors shall quote this order and URN."
    )
    story.append(Paragraph(p3, body_para))
    story.append(Spacer(1, 14))

    sig_block = Table([
        ["",
         RLImage(str(round_seal), width=1.4 * inch, height=1.4 * inch),
         [RLImage(str(sig), width=1.6 * inch, height=0.5 * inch),
          Paragraph("<b>( PRAMOD KUMAR )</b><br/>Commissioner of Income-tax (Exemptions),<br/>NEW DELHI", officer_style)]]
    ], colWidths=[2.5 * inch, 2.0 * inch, 2.5 * inch])
    sig_block.setStyle(TableStyle([
        ("ALIGN", (1, 0), (1, 0), "CENTER"),
        ("ALIGN", (2, 0), (2, 0), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(sig_block)
    story.append(Spacer(1, 14))

    bottom_table = Table([
        [RLImage(str(despatch_stamp), width=1.5 * inch, height=0.55 * inch),
         [Paragraph("<b>( A.D. Jadhav )</b><br/>Income-tax Officer (HQ)<br/>for Commissioner of Income-tax (Exemptions),<br/>NEW DELHI", officer_style)]]
    ], colWidths=[3.5 * inch, 3.5 * inch])
    bottom_table.setStyle(TableStyle([
        ("ALIGN", (0, 0), (0, 0), "LEFT"),
        ("ALIGN", (1, 0), (1, 0), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(bottom_table)

    doc.build(story)
    print(f"Generated authentic 80G PDF: {pdf_path}")


if __name__ == "__main__":
    build_darpan_pdf()
    build_12a_pdf()
    build_80g_pdf()
    print("\nAll authentic visual replicas generated successfully!")
