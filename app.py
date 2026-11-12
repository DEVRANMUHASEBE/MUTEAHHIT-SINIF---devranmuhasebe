import streamlit as st
from io import BytesIO
from datetime import datetime
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage, KeepTogether

st.set_page_config(
    page_title="Müteahhitlik Sınıf Hesaplama",
    page_icon="🏗️",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ---------------------------------------------------------
# 2026 VERİLERİ
# Kaynak:
# Çevre, Şehircilik ve İklim Değişikliği Bakanlığı
# 2026 Yapım Müteahhitliği Yeterlik Tablosu
# ---------------------------------------------------------

GROUPS = ["A", "B", "B1", "C", "C1", "D", "D1", "E", "E1", "F", "F1", "G", "G1", "H"]

BUILDING_CLASSES = {
    "II-B": "Basit yapılar, küçük depo/atölye benzeri yapılar",
    "II-C": "Standartları biraz daha yüksek basit yapılar",
    "III-A": "Basit konut ve benzeri yapılar",
    "III-B": "Konut yapıları (yapı yüksekliği 21,5 m'ye kadar)",
    "III-C": "Konut yapıları (yapı yüksekliği 21,5 m ile 30,5 m arası)",
    "IV-A": "Konut (yapı yüksekliği 30,5 m ile 51,5 m arası) • Alışveriş merkezleri (brüt inşaat alanı 25.000 m²'nin altı) • İş merkezleri/ticari amaçlı yapılar (yapı yüksekliği 21,5 m ile 30,5 m arası)",
    "IV-B": "Konut yapıları (yapı yüksekliği 51,5 m'den yukarı) • Düğün salonu • İş merkezleri/ticari amaçlı yapılar (yapı yüksekliği 30,5 m ile 51,5 m arası)",
    "IV-C": "Alışveriş merkezleri (brüt inşaat alanı 25.000 m²'nin üzeri yapılar)",
    "V-A": "İş merkezleri/ticari amaçlı yapılar (yapı yüksekliği 51,5 m ve üzeri)",
}


# 2026 Yapı Yaklaşık Birim Maliyetleri (TL/m²)
# Resmî 2026 Yapım Müteahhitliği Yeterlik Tablosu / 03.02.2026 tebliği
BUILDING_UNIT_COSTS = {
    "II-B": 12500,
    "II-C": 15100,
    "III-A": 19800,
    "III-B": 21050,
    "III-C": 23400,
    "IV-A": 26450,
    "IV-B": 33900,
    "IV-C": 40500,
    "V-A": 42350,
}

# 2026 yılı asgari iş deneyim tutarları (TL)
# H grubu için asgari iş deneyim tutarı şartı bulunmadığından fallback olarak kullanılır.
WORK_EXPERIENCE_MIN = {
    "A": 2476500000,
    "B": 1733550000,
    "B1": 1485900000,
    "C": 1238250000,
    "C1": 1031875000,
    "D": 825500000,
    "D1": 619125000,
    "E": 412750000,
    "E1": 247650000,
    "F": 123825000,
    "F1": 105251250,
    "G": 86677500,
    "G1": 61912500,
}

# Tek parselde üstlenilebilecek tek iş için azami toplam inşaat alanı (m²)
MAX_M2 = {
    "A":  {k: None for k in BUILDING_CLASSES},
    "B":  {"II-B":138684, "II-C":114805, "III-A":87553, "III-B":82354, "III-C":74083, "IV-A":65541, "IV-B":51137, "IV-C":42804, "V-A":40934},
    "B1": {"II-B":118872, "II-C":98404,  "III-A":75045, "III-B":70589, "III-C":63500, "IV-A":56178, "IV-B":43832, "IV-C":36689, "V-A":35086},
    "C":  {"II-B":99060,  "II-C":82003,  "III-A":62538, "III-B":58824, "III-C":52917, "IV-A":46815, "IV-B":36527, "IV-C":30574, "V-A":29238},
    "C1": {"II-B":82550,  "II-C":68336,  "III-A":52115, "III-B":49020, "III-C":44097, "IV-A":39012, "IV-B":30439, "IV-C":25478, "V-A":24365},
    "D":  {"II-B":66040,  "II-C":54669,  "III-A":41692, "III-B":39216, "III-C":35278, "IV-A":31210, "IV-B":24351, "IV-C":20383, "V-A":19492},
    "D1": {"II-B":49530,  "II-C":41002,  "III-A":31269, "III-B":29412, "III-C":26458, "IV-A":23407, "IV-B":18263, "IV-C":15287, "V-A":14619},
    "E":  {"II-B":37973,  "II-C":31435,  "III-A":23973, "III-B":22549, "III-C":20285, "IV-A":17946, "IV-B":14002, "IV-C":11720, "V-A":11208},
    "E1": {"II-B":26416,  "II-C":21868,  "III-A":16677, "III-B":15686, "III-C":14111, "IV-A":12484, "IV-B":9740,  "IV-C":8153,  "V-A":7797},
    "F":  {"II-B":19812,  "II-C":16401,  "III-A":12508, "III-B":11765, "III-C":10583, "IV-A":9363,  "IV-B":7305,  "IV-C":6115,  "V-A":5848},
    "F1": {"II-B":14735,  "II-C":12198,  "III-A":9303,  "III-B":8750,  "III-C":7871,  "IV-A":6964,  "IV-B":5433,  "IV-C":4548,  "V-A":4349},
    "G":  {"II-B":10401,  "II-C":8610,   "III-A":6566,  "III-B":6177,  "III-C":5556,  "IV-A":4916,  "IV-B":3835,  "IV-C":3210,  "V-A":3070},
    "G1": {"II-B":7430,   "II-C":6150,   "III-A":4690,  "III-B":4412,  "III-C":3969,  "IV-A":3511,  "IV-B":2739,  "IV-C":2293,  "V-A":2193},
    "H":  {"II-B":3538,   "II-C":2929,   "III-A":2233,  "III-B":2101,  "III-C":1890,  "IV-A":1672,  "IV-B":1305,  "IV-C":1092,  "V-A":1044},
}

# 2026 resmi yeterlik tablosundaki "İş Ortaklığı" sütunları:
# hedef_grup: (pilot ortağın en az grubu, diğer ortağın en az grubu)
JOINT_REQUIREMENTS = {
    "A":  ("B1", "E1"),
    "B":  ("C",  "E1"),
    "B1": ("C1", "E1"),
    "C":  ("D",  "F"),
    "C1": ("D1", "F1"),
    "D":  ("D1", "G"),
    "D1": ("E",  "G1"),
    "E":  ("E1", "G1"),
    "E1": ("E1", "H"),
    "F":  ("G",  "H"),
    "F1": ("G",  "H"),
    "G":  ("G1", "H"),
    "G1": ("G1", "H"),
    "H":  ("H",  "H"),
}

GROUP_RANK = {group: i for i, group in enumerate(GROUPS)}

def group_meets(actual, minimum):
    """Daha üst bir grup, alt grup şartını da karşılar."""
    return GROUP_RANK[actual] <= GROUP_RANK[minimum]

def best_joint_group(pilot_group, other_group):
    """İki ortak için 2026 resmi iş ortaklığı tablosuna göre ulaşılabilen en yüksek grubu bulur."""
    for target in GROUPS:
        pilot_min, other_min = JOINT_REQUIREMENTS[target]
        if group_meets(pilot_group, pilot_min) and group_meets(other_group, other_min):
            return target, pilot_min, other_min
    return "H", "H", "H"

def fmt_pdf_m2(value):
    """PDF'de m² değerini 2 ondalık ve Türkçe sayı biçimiyle gösterir."""
    try:
        return f"{float(value):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except (TypeError, ValueError):
        return "0,00"


def fmt_m2(value):
    return f"{value:,.0f}".replace(",", ".") + " m²"

def fmt_tl(value):
    return f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") + " ₺"

def work_experience_group(amount):
    """Yalnızca 2026 asgari iş deneyim tutarına göre ulaşılabilen en yüksek grubu döndürür."""
    for group in ["A", "B", "B1", "C", "C1", "D", "D1", "E", "E1", "F", "F1", "G", "G1"]:
        if amount >= WORK_EXPERIENCE_MIN[group]:
            return group
    return "H"

def building_class_label(code):
    return f"{code} — {BUILDING_CLASSES[code]}"

LOGO_PATH = Path(__file__).with_name("devran_logo.png")


def _pdf_fonts():
    """PDF için Türkçe karakter destekli fontları güvenli şekilde yükler.

    Öncelik ReportLab paketinin kendi içinde gelen Vera.ttf / VeraBd.ttf
    fontlarındadır. Böylece Streamlit Cloud ortamında sistem fontuna bağlı
    kalınmaz ve İ, ı, Ş, ş, Ğ, ğ, Ç, ç gibi karakterler bozulmaz.
    """
    import reportlab
    import os

    reportlab_fonts = Path(reportlab.__file__).resolve().parent / "fonts"

    regular_candidates = [
        reportlab_fonts / "Vera.ttf",
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf"),
        Path("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"),
    ]

    bold_candidates = [
        reportlab_fonts / "VeraBd.ttf",
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
        Path("/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf"),
        Path("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"),
    ]

    regular = next((p for p in regular_candidates if p.exists()), None)
    bold = next((p for p in bold_candidates if p.exists()), None)

    if regular is None or bold is None:
        raise RuntimeError(
            "Türkçe karakter destekli PDF fontu bulunamadı. "
            "Lütfen reportlab paketinin eksiksiz kurulduğunu kontrol edin."
        )

    if "DevranPDFRegular" not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont("DevranPDFRegular", str(regular)))

    if "DevranPDFBold" not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont("DevranPDFBold", str(bold)))

    return "DevranPDFRegular", "DevranPDFBold"


def _verify_turkish_pdf_font():
    """PDF üretmeden önce kritik Türkçe karakterlerin fontta kullanılabildiğini doğrular."""
    regular_font, bold_font = _pdf_fonts()
    # TTFont kayıtlıysa ReportLab Unicode metni fonta gömebilir.
    # Bu metin özellikle daha önce kutu çıkan karakterleri içerir.
    _ = "MÜTEAHHİTLİK - İnşaat - Sınıfı - İş - Değerlendirme - MÂLİ MÜŞAVİRLİK"
    return regular_font, bold_font


def _draw_pdf_footer(canvas, doc):
    """Her PDF sayfasının altında logo ve Devran ibaresi."""
    canvas.saveState()
    page_width, _ = A4

    # Logo
    if LOGO_PATH.exists():
        try:
            logo_width = 84 * mm
            logo_height = 52 * mm
            canvas.drawImage(
                str(LOGO_PATH),
                (page_width - logo_width) / 2,
                9 * mm,
                width=logo_width,
                height=logo_height,
                preserveAspectRatio=True,
                mask="auto",
                anchor="c",
            )
        except Exception:
            pass

    regular_font, _ = _pdf_fonts()
    canvas.setFont(regular_font, 6.4)
    canvas.setFillColor(colors.HexColor("#5f6673"))
    footer_text = "Bu belgenin hazırlanması DEVRAN MÂLİ MÜŞAVİRLİK tarafından sağlanmıştır"
    canvas.drawCentredString(page_width / 2, 4.8 * mm, footer_text)

    canvas.restoreState()



def create_experience_pdf(
    method_name,
    rows,
    total_amount,
    result_group,
    normal_total=None,
    normal_group=None,
    largest_row=None,
    three_times_limit=None,
    cap_applied=False,
    notes=None,
    total_amount_no90=None,
    result_group_no90=None,
    normal_total_no90=None,
    normal_group_no90=None,
    largest_row_no90=None,
    three_times_limit_no90=None,
    cap_applied_no90=False,
):
    """Sade PDF dökümü oluşturur: detaylı hesaplama yok, sadece özet tablo ve sonuç."""
    buffer = BytesIO()
    font_regular, font_bold = _verify_turkish_pdf_font()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=11 * mm,
        leftMargin=11 * mm,
        topMargin=12 * mm,
        bottomMargin=61 * mm,
        title="Müteahhitlik Sınıf Hesaplama",
        author="DEVRAN MÂLİ MÜŞAVİRLİK",
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "PDFTitle",
        parent=styles["Title"],
        fontName=font_bold,
        fontSize=15.5,
        leading=17.5,
        alignment=TA_LEFT,
        textColor=colors.black,
        spaceAfter=2,
    )
    sub_style = ParagraphStyle(
        "PDFSub",
        parent=styles["Normal"],
        fontName=font_regular,
        fontSize=9.0,
        leading=10.5,
        alignment=TA_LEFT,
        textColor=colors.black,
        spaceAfter=6,
    )
    section_style = ParagraphStyle(
        "PDFSection",
        parent=styles["Heading2"],
        fontName=font_bold,
        fontSize=11.5,
        leading=13,
        textColor=colors.black,
        spaceAfter=4,
        spaceBefore=2,
    )
    body_style = ParagraphStyle(
        "PDFBody",
        parent=styles["Normal"],
        fontName=font_regular,
        fontSize=9.2,
        leading=12,
        textColor=colors.black,
        spaceAfter=3,
    )
    small_style = ParagraphStyle(
        "PDFSmall",
        parent=styles["Normal"],
        fontName=font_regular,
        fontSize=8.2,
        leading=10,
        textColor=colors.black,
        spaceAfter=2,
    )
    center_bold = ParagraphStyle(
        "PDFCenterBold",
        parent=styles["Normal"],
        fontName=font_bold,
        fontSize=11,
        leading=13,
        alignment=TA_CENTER,
        textColor=colors.black,
    )
    big_result = ParagraphStyle(
        "PDFBigResult",
        parent=styles["Normal"],
        fontName=font_bold,
        fontSize=25,
        leading=27,
        alignment=TA_CENTER,
        textColor=colors.black,
    )
    value_style = ParagraphStyle(
        "PDFValue",
        parent=styles["Normal"],
        fontName=font_bold,
        fontSize=17.5,
        leading=19,
        alignment=TA_CENTER,
        textColor=colors.black,
    )
    table_ada_style = ParagraphStyle(
        "PDFTableAda",
        parent=styles["Normal"],
        fontName=font_regular,
        fontSize=6.35,
        leading=7.2,
        alignment=TA_LEFT,
        textColor=colors.black,
    )
    table_total_style = ParagraphStyle(
        "PDFTableTotal",
        parent=styles["Normal"],
        fontName=font_bold,
        fontSize=6.35,
        leading=7.2,
        alignment=TA_LEFT,
        textColor=colors.black,
    )

    report_no = f"MH-{datetime.now().strftime('%Y%m%d-%H%M')}"
    result_min_amount = WORK_EXPERIENCE_MIN.get(result_group)

    story = []
    # Header: sade başlık + yıl
    header = Table(
        [[
            Paragraph("MÜTEAHHİTLİK SINIF HESAPLAMA", title_style),
            Paragraph("2026", ParagraphStyle(
                "YearStyle",
                parent=styles["Normal"],
                fontName=font_bold,
                fontSize=18,
                leading=20,
                alignment=TA_CENTER,
                textColor=colors.black,
            )),
        ]],
        colWidths=[155 * mm, 25 * mm],
        hAlign="LEFT",
    )
    header.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (1, 0), (1, 0), "CENTER"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    story.append(header)
    story.append(Paragraph("Bitirdiğim İnşaatlar ile Hangi Sınıfı Alabilirim?", sub_style))
    story.append(Spacer(1, 1.2 * mm))

    # Method/Note box
    method_table = Table(
        [
            ["Yöntem", method_name],
            ["Hesap", "İş deneyimi hem %90 uygulanarak hem de %90 uygulanmadan ayrı ayrı gösterilmiştir."],
            ["Not", "Toplam tutar, en büyük iş deneyiminin 3 katını geçemez (Yönetmelik)."],
        ],
        colWidths=[30 * mm, 147 * mm],
        hAlign="LEFT",
    )
    method_table.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.8, colors.black),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.black),
        ("FONTNAME", (0, 0), (0, -1), font_bold),
        ("FONTNAME", (1, 0), (-1, -1), font_regular),
        ("FONTSIZE", (0, 0), (-1, -1), 8.7),
        ("LEADING", (0, 0), (-1, -1), 12),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3.4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3.4),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(method_table)
    story.append(Spacer(1, 1.5 * mm))

    # Data table
    story.append(Paragraph("İNŞAAT BİLGİLERİ", section_style))
    data = [[
        "Sıra",
        "Ada Parsel",
        "İnşaat Alanı (m²)",
        "Yapı Sınıfı",
        "m² Maliyeti",
        "İş Deneyimi\n(%90 Uyg.)",
        "İş Deneyimi\n(%90 Yok)",
    ]]
    max_rows = max(len(rows), 1)
    summary_row_indexes = []
    project_row_indexes = {}

    if rows:
        for idx, row in enumerate(rows):
            data.append([
                str(row.get("row", idx + 1)),
                Paragraph(str(row.get("ada_parsel", "")), table_ada_style),
                fmt_pdf_m2(row.get("area", 0)),
                str(row.get("class", "")),
                f"{int(row.get('unit_cost', BUILDING_UNIT_COSTS.get(row.get('class'), 0))):,}".replace(",", "."),
                fmt_tl(row.get("amount_90", row.get("amount", 0))).replace(" ₺", " TL"),
                fmt_tl(row.get("amount_no90", row.get("amount", 0))).replace(" ₺", " TL"),
            ])

            current_project = row.get("project_id")

            if current_project is not None:
                project_row_indexes.setdefault(current_project, []).append(len(data) - 1)

            next_project = (
                rows[idx + 1].get("project_id")
                if idx + 1 < len(rows)
                else None
            )

            # Aynı inşaatın son blok/bölüm satırından sonra PARSEL TOPLAMI ekle.
            if current_project is not None and current_project != next_project:
                project_rows = [
                    r for r in rows
                    if r.get("project_id") == current_project
                ]
                project_label = (
                    row.get("project_label")
                    or project_rows[0].get("project_label")
                    or f"{current_project}. İnşaat"
                )
                project_area_total = sum(float(r.get("area", 0) or 0) for r in project_rows)
                project_experience_total_90 = row.get(
                    "project_total_90",
                    sum(float(r.get("amount_90", r.get("amount", 0)) or 0) for r in project_rows),
                )
                project_experience_total_no90 = row.get(
                    "project_total_no90",
                    sum(float(r.get("amount_no90", r.get("amount", 0)) or 0) for r in project_rows),
                )
                part_count = len(project_rows)

                data.append([
                    f"{current_project}.T",
                    Paragraph(
                        f"<b>{project_label} PARSEL TOPLAMI ({part_count} BLOK/BÖLÜM)</b>",
                        table_total_style,
                    ),
                    fmt_pdf_m2(project_area_total),
                    "",
                    "",
                    fmt_tl(project_experience_total_90).replace(" ₺", " TL"),
                    fmt_tl(project_experience_total_no90).replace(" ₺", " TL"),
                ])
                summary_row_indexes.append(len(data) - 1)
                project_row_indexes.setdefault(current_project, []).append(len(data) - 1)
    else:
        data.append(["1", "", "", "", "", "", ""])

    info_table = Table(
        data,
        colWidths=[9 * mm, 37 * mm, 24 * mm, 17 * mm, 20 * mm, 33 * mm, 33 * mm],
        repeatRows=1,
        hAlign="LEFT",
    )

    info_style = [
        ("BOX", (0, 0), (-1, -1), 0.8, colors.black),
        ("INNERGRID", (0, 0), (-1, -1), 0.45, colors.black),
        ("FONTNAME", (0, 0), (-1, 0), font_bold),
        ("FONTNAME", (0, 1), (-1, -1), font_regular),
        ("FONTSIZE", (0, 0), (-1, -1), 6.15),
        ("LEADING", (0, 0), (-1, -1), 8.2),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("ALIGN", (1, 1), (1, -1), "LEFT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 1.25),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1.25),
        ("LEFTPADDING", (0, 0), (-1, -1), 2.3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 2.3),
    ]

    # İnşaat gruplarını görsel olarak ayır:
    # 1., 3., 5. ... inşaat açık mavi; 2., 4., 6. ... inşaat beyaz.
    light_blue = colors.HexColor("#EAF4FF")
    white_bg = colors.white

    for project_id, row_indexes in project_row_indexes.items():
        bg_color = light_blue if int(project_id) % 2 == 1 else white_bg
        for table_row in row_indexes:
            info_style.append(
                ("BACKGROUND", (0, table_row), (-1, table_row), bg_color)
            )

    for summary_row in summary_row_indexes:
        info_style.extend([
            ("FONTNAME", (0, summary_row), (-1, summary_row), font_bold),
            ("LINEABOVE", (0, summary_row), (-1, summary_row), 0.9, colors.black),
            ("LINEBELOW", (0, summary_row), (-1, summary_row), 0.9, colors.black),
            ("TOPPADDING", (0, summary_row), (-1, summary_row), 1.6),
            ("BOTTOMPADDING", (0, summary_row), (-1, summary_row), 1.6),
        ])

    info_table.setStyle(TableStyle(info_style))
    story.append(info_table)
    story.append(Spacer(1, 1.5 * mm))

    # Kullanıcının inşaat bazında yazdığı notlar.
    clean_notes = [
        n for n in (notes or [])
        if str(n.get("note", "")).strip()
    ]

    if clean_notes:
        story.append(Paragraph("NOTLAR", section_style))

        notes_data = [["Ada / Parsel", "Not"]]
        for n in clean_notes:
            notes_data.append([
                Paragraph(
                    str(n.get("ada_parsel", "-")),
                    small_style,
                ),
                Paragraph(
                    str(n.get("note", "")),
                    small_style,
                ),
            ])

        notes_table = Table(
            notes_data,
            colWidths=[48 * mm, 111 * mm],
            repeatRows=1,
            hAlign="LEFT",
        )
        notes_table.setStyle(TableStyle([
            ("BOX", (0, 0), (-1, -1), 0.7, colors.black),
            ("INNERGRID", (0, 0), (-1, -1), 0.35, colors.black),
            ("FONTNAME", (0, 0), (-1, 0), font_bold),
            ("FONTNAME", (0, 1), (-1, -1), font_regular),
            ("FONTSIZE", (0, 0), (-1, -1), 7.2),
            ("LEADING", (0, 0), (-1, -1), 8.5),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ALIGN", (0, 0), (0, -1), "LEFT"),
            ("TOPPADDING", (0, 0), (-1, -1), 2.5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ]))

        story.append(notes_table)
        story.append(Spacer(1, 1.5 * mm))

    # Result section - iki senaryo birlikte gösterilir.
    dual_mode = total_amount_no90 is not None and result_group_no90 is not None

    if not dual_mode:
        total_amount_no90 = total_amount
        result_group_no90 = result_group
        normal_total_no90 = normal_total
        normal_group_no90 = normal_group
        largest_row_no90 = largest_row
        three_times_limit_no90 = three_times_limit
        cap_applied_no90 = cap_applied

    experience_rows = [
        ("A", WORK_EXPERIENCE_MIN["A"]),
        ("B", WORK_EXPERIENCE_MIN["B"]),
        ("B1", WORK_EXPERIENCE_MIN["B1"]),
        ("C", WORK_EXPERIENCE_MIN["C"]),
        ("C1", WORK_EXPERIENCE_MIN["C1"]),
        ("D", WORK_EXPERIENCE_MIN["D"]),
        ("D1", WORK_EXPERIENCE_MIN["D1"]),
        ("E", WORK_EXPERIENCE_MIN["E"]),
        ("E1", WORK_EXPERIENCE_MIN["E1"]),
        ("F", WORK_EXPERIENCE_MIN["F"]),
        ("F1", WORK_EXPERIENCE_MIN["F1"]),
        ("G", WORK_EXPERIENCE_MIN["G"]),
        ("G1", WORK_EXPERIENCE_MIN["G1"]),
        ("H", None),
    ]

    scenario_title_style = ParagraphStyle(
        "PDFScenarioTitle",
        parent=center_bold,
        fontSize=9.3,
        leading=10.5,
    )
    scenario_value_style = ParagraphStyle(
        "PDFScenarioValue",
        parent=value_style,
        fontSize=13.2,
        leading=14.5,
    )
    scenario_group_style = ParagraphStyle(
        "PDFScenarioGroup",
        parent=big_result,
        fontSize=21,
        leading=22,
    )
    tiny_center = ParagraphStyle(
        "PDFTinyCenter",
        parent=styles["Normal"],
        fontName=font_regular,
        fontSize=6.5,
        leading=7.5,
        alignment=TA_CENTER,
        textColor=colors.black,
    )

    def _scenario_box(label, final_amount, final_group, normal_amount, largest, limit, cap_used, amount_key):
        display_normal = normal_amount if normal_amount is not None else final_amount
        rows_local = [
            [Paragraph(label, scenario_title_style)],
            [Paragraph(fmt_tl(display_normal).replace(" ₺", " TL"), scenario_value_style)],
        ]

        if cap_used:
            source_parcel = str((largest or {}).get("ada_parsel", "-"))
            source_amount = (largest or {}).get(amount_key, (largest or {}).get("amount", 0))
            rows_local.extend([
                [Paragraph(
                    "3 KATI KURALI SONRASI DİKKATE ALINAN TUTAR",
                    scenario_title_style,
                )],
                [Paragraph(
                    f"Esas alınan inşaat: {source_parcel}<br/>"
                    f"{fmt_tl(source_amount).replace(' ₺', ' TL')} x 3",
                    tiny_center,
                )],
                [Paragraph(fmt_tl(final_amount).replace(" ₺", " TL"), scenario_value_style)],
            ])
        else:
            rows_local.append([
                Paragraph("3 kat sınırı aşılmadı", tiny_center)
            ])

        rows_local.extend([
            [Paragraph("ULAŞILABİLEN BELGE GRUBU", scenario_title_style)],
            [Paragraph(final_group, scenario_group_style)],
            [Paragraph("GRUBU", scenario_title_style)],
        ])

        box = Table(rows_local, colWidths=[86 * mm], hAlign="CENTER")
        box.setStyle(TableStyle([
            ("BOX", (0, 0), (-1, -1), 0.8, colors.black),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 1.5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5),
            ("LINEABOVE", (0, 2), (-1, 2), 0.45, colors.black),
        ]))
        return box

    box_90 = _scenario_box(
        "%90 UYGULANIRSA",
        total_amount,
        result_group,
        normal_total,
        largest_row,
        three_times_limit,
        cap_applied,
        "amount_90",
    )
    box_no90 = _scenario_box(
        "%90 UYGULANMAZSA",
        total_amount_no90,
        result_group_no90,
        normal_total_no90,
        largest_row_no90,
        three_times_limit_no90,
        cap_applied_no90,
        "amount_no90",
    )

    story.append(Paragraph("HESAPLAMA SONUÇLARI", section_style))
    dual_result = Table(
        [[box_90, box_no90]],
        colWidths=[88 * mm, 88 * mm],
        hAlign="LEFT",
    )
    dual_result.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    story.append(dual_result)

    # Kullanıcının istediği mevcut görsel mesafeyi koru.
    story.append(Spacer(1, 30 * mm))

    threshold_data = [[
        Paragraph(f"{datetime.now().year} YILI ASGARİ İŞ DENEYİM TUTARLARI", center_bold),
        "",
    ]]

    for group_name, min_amount in experience_rows:
        amount_text = (
            "Asgari iş deneyimi aranmaz."
            if min_amount is None
            else fmt_tl(min_amount).replace(",00 ₺", " TL")
        )
        threshold_data.append([group_name, amount_text])

    threshold_result = Table(
        threshold_data,
        colWidths=[45 * mm, 95 * mm],
        hAlign="CENTER",
    )

    threshold_style = [
        ("BOX", (0, 0), (-1, -1), 0.8, colors.black),
        ("SPAN", (0, 0), (1, 0)),
        ("FONTNAME", (0, 0), (-1, 0), font_bold),
        ("FONTNAME", (0, 1), (-1, -1), font_regular),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("FONTSIZE", (0, 1), (-1, -1), 6.15),
        ("INNERGRID", (0, 1), (-1, -1), 0.32, colors.black),
        ("TOPPADDING", (0, 0), (-1, 0), 1.1),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 1.1),
        ("TOPPADDING", (0, 1), (-1, -1), 0.20),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 0.20),
    ]

    # Her iki senaryonun ulaştığı grubu tabloda belirginleştir.
    for grp in {result_group, result_group_no90}:
        threshold_row = 1 + [g for g, _ in experience_rows].index(grp)
        threshold_style.extend([
            ("FONTNAME", (0, threshold_row), (-1, threshold_row), font_bold),
            ("LINEABOVE", (0, threshold_row), (-1, threshold_row), 0.75, colors.black),
            ("LINEBELOW", (0, threshold_row), (-1, threshold_row), 0.75, colors.black),
        ])

    threshold_result.setStyle(TableStyle(threshold_style))

    # Ayrı flowable: yer varsa aynı sayfada kalır, sığmazsa sonraki sayfaya geçer.
    story.append(KeepTogether([threshold_result]))
    story.append(Spacer(1, 1 * mm))

    note_box = Table(
        [[Paragraph("<b>Önemli Not:</b> Bu rapor bilgilendirme amaçlıdır. Resmî başvurularda ilgili mevzuat hükümleri ve idare değerlendirmesi esastır.", small_style)]],
        colWidths=[180 * mm],
        hAlign="LEFT",
    )
    note_box.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.8, colors.black),
        ("TOPPADDING", (0, 0), (-1, -1), 1.2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1.2),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(note_box)
    story.append(Spacer(1, 1 * mm))
    footer_left = Paragraph(
        f"<b>Düzenleme Tarihi</b><br/>{datetime.now().strftime('%d.%m.%Y')}",
        small_style
    )

    footer_table = Table(
        [[footer_left]],
        colWidths=[180 * mm],
        hAlign="LEFT",
    )
    footer_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("LINEABOVE", (0, 0), (-1, 0), 0.8, colors.black),
        ("TOPPADDING", (0, 0), (-1, -1), 1.0),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
    ]))
    story.append(footer_table)

    doc.build(
        story,
        onFirstPage=_draw_pdf_footer,
        onLaterPages=_draw_pdf_footer,
    )
    buffer.seek(0)
    return buffer.getvalue()

# ---------------------------------------------------------
# TASARIM
# ---------------------------------------------------------

st.markdown("""
<style>
    .stApp {
        background: linear-gradient(180deg, #f7f9fc 0%, #ffffff 50%);
    }

    .block-container {
        max-width: 850px;
        padding-top: 1.7rem;
        padding-bottom: 3rem;
    }

    .hero {
        padding: 1.4rem 1.2rem;
        border-radius: 22px;
        background: #172033;
        color: white;
        margin-bottom: 1.3rem;
        box-shadow: 0 8px 24px rgba(0,0,0,.10);
    }

    .hero h1 {
        font-size: 1.85rem;
        margin: 0 0 .3rem 0;
    }

    .hero p {
        margin: 0;
        opacity: .86;
        font-size: .98rem;
    }

    .question-card {
        padding: 1rem 1.05rem;
        border: 1px solid #e6e9ef;
        border-radius: 18px;
        background: white;
        margin-bottom: .9rem;
        box-shadow: 0 4px 16px rgba(0,0,0,.04);
    }

    .click-card {
        display: block;
        text-decoration: none !important;
        color: inherit !important;
        padding: 1rem 1.05rem;
        border: 1px solid #e6e9ef;
        border-radius: 18px;
        background: white;
        margin-bottom: .9rem;
        box-shadow: 0 4px 16px rgba(0,0,0,.04);
        transition: all .18s ease;
    }

    .click-card:hover {
        border-color: #cfd8ea;
        box-shadow: 0 10px 22px rgba(0,0,0,.07);
        transform: translateY(-1px);
    }

    .click-card .title {
        font-weight: 700;
        font-size: 1.06rem;
        margin-bottom: .35rem;
        color: #1d2a44;
    }

    .click-card .desc {
        font-size: .92rem;
        color: #6b7485;
    }

    .result-card {
        padding: 1.25rem;
        border-radius: 20px;
        background: #eef8f1;
        border: 1px solid #cde7d4;
        text-align: center;
        margin: 1rem 0;
    }

    .result-number {
        font-size: 2.25rem;
        font-weight: 800;
        line-height: 1.15;
        margin: .4rem 0;
    }

    .joint-result {
        padding: 1.2rem;
        border-radius: 20px;
        background: #eef4ff;
        border: 1px solid #cbdcf8;
        text-align: center;
        margin: 1rem 0;
    }

    .small-note {
        font-size: .84rem;
        opacity: .75;
    }

    div.stButton > button {
        border-radius: 14px;
        min-height: 3.2rem;
        font-weight: 700;
        width: 100%;
    }

    /* BLOK EKLE: koyu gri + küçük */
    [class*="st-key-add_exp5_block_"] div.stButton > button,
    .st-key-add_exp15_block div.stButton > button {
        background: #4b4f56 !important;
        color: #ffffff !important;
        border: 1px solid #3f4349 !important;
        width: auto !important;
        min-height: 2.35rem !important;
        padding: .35rem .85rem !important;
        border-radius: 9px !important;
        font-size: .86rem !important;
        font-weight: 800 !important;
        box-shadow: none !important;
    }

    [class*="st-key-add_exp5_block_"] div.stButton > button:hover,
    .st-key-add_exp15_block div.stButton > button:hover {
        background: #3d4147 !important;
        border-color: #34383d !important;
        color: #ffffff !important;
    }

    /* İNŞAAT EKLE: yeşil */
    .st-key-add_exp5_row div.stButton > button {
        background: #1f9d55 !important;
        color: #ffffff !important;
        border: 1px solid #188447 !important;
        min-height: 2.8rem !important;
        border-radius: 11px !important;
        font-weight: 800 !important;
        box-shadow: 0 4px 12px rgba(31, 157, 85, .18) !important;
    }

    .st-key-add_exp5_row div.stButton > button:hover {
        background: #198447 !important;
        border-color: #146e3b !important;
        color: #ffffff !important;
    }

    /* Sonradan eklenen inşaat / blokları kaldırma X butonu */
    [class*="st-key-remove_exp5_project_"] div.stButton > button,
    [class*="st-key-remove_exp5_block_"] div.stButton > button,
    [class*="st-key-remove_exp15_block_"] div.stButton > button {
        background: #d64545 !important;
        color: #ffffff !important;
        border: 1px solid #bd3434 !important;
        width: 2.15rem !important;
        min-width: 2.15rem !important;
        height: 2.15rem !important;
        min-height: 2.15rem !important;
        padding: 0 !important;
        border-radius: 8px !important;
        font-size: .95rem !important;
        font-weight: 900 !important;
        line-height: 1 !important;
        box-shadow: none !important;
    }

    [class*="st-key-remove_exp5_project_"] div.stButton > button:hover,
    [class*="st-key-remove_exp5_block_"] div.stButton > button:hover,
    [class*="st-key-remove_exp15_block_"] div.stButton > button:hover {
        background: #b93434 !important;
        border-color: #a42d2d !important;
        color: #ffffff !important;
    }

    .brand-footer {
        text-align: center;
        margin-top: 1.2rem;
        padding-top: .8rem;
        color: #656d7b;
        font-size: .88rem;
    }

    .brand-footer strong {
        color: #172033;
    }

    .apply-btn-wrap {
        margin: .25rem 0 1rem 0;
    }

    .apply-btn {
        display: inline-block;
        background: #d92828;
        color: #ffffff !important;
        text-decoration: none !important;
        font-weight: 800;
        font-size: .98rem;
        padding: .72rem 1.25rem;
        border-radius: 12px;
        box-shadow: 0 6px 16px rgba(217, 40, 40, .22);
        border: 1px solid #be1f1f;
    }

    .apply-btn:hover {
        background: #bf1f1f;
        color: #ffffff !important;
    }

    .visual-card {
        border-radius: 22px;
        padding: 1rem;
    }

    .visual-card-row {
        display: flex;
        align-items: center;
        gap: .9rem;
    }

    .visual-icon {
        width: 66px;
        min-width: 66px;
        height: 66px;
        border-radius: 50%;
        background: #f7f6f3;
        border: 1px solid #ebe7df;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.7rem;
        font-weight: 800;
        color: #172033;
    }

    .visual-text {
        flex: 1;
        min-width: 0;
    }

    .visual-card .title {
        font-weight: 800;
        line-height: 1.3;
    }

    .visual-card .desc {
        line-height: 1.4;
    }

    .visual-arrow {
        color: #c49a3a;
        font-size: 2rem;
        font-weight: 700;
    }

    @media (max-width: 640px) {
        .visual-icon {
            width: 58px;
            min-width: 58px;
            height: 58px;
            font-size: 1.5rem;
        }
        .visual-card-row {
            gap: .7rem;
        }
        .visual-arrow {
            font-size: 1.7rem;
        }
    }
</style>
""", unsafe_allow_html=True)

allowed_pages = {"home", "m2", "joint", "experience"}
page_from_query = st.query_params.get("page", "home")
if page_from_query not in allowed_pages:
    page_from_query = "home"
st.session_state.page = page_from_query

def go(page):
    st.query_params["page"] = page
    st.session_state.page = page
    st.rerun()

st.markdown("""
<div class="hero">
    <h1>🏗️ Müteahhitlik Sınıf Hesaplama</h1>
    <p>2026 yılı yapı müteahhitliği yetki belge grupları için hızlı hesaplama</p>
</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# ANA EKRAN
# ---------------------------------------------------------
if st.session_state.page == "home":
    st.subheader("Ne hesaplamak istiyorsunuz?")

    st.markdown(
        """
        <a class="click-card visual-card" href="?page=m2" target="_self">
            <div class="visual-card-row">
                <div class="visual-icon">㎡</div>
                <div class="visual-text">
                    <div class="title">1. Mevcut sınıfım ile kaç m² inşaat yapabilirim?</div>
                    <div class="desc">Yetki belge grubunuzu ve yapı sınıfını seçin.</div>
                </div>
                <div class="visual-arrow">›</div>
            </div>
        </a>
        """,
        unsafe_allow_html=True
    )

    st.markdown(
        """
        <a class="click-card visual-card" href="?page=joint" target="_self">
            <div class="visual-card-row">
                <div class="visual-icon">👥</div>
                <div class="visual-text">
                    <div class="title">2. Hangi sınıfları birleştirsem hangi sınıfı elde ederiz?</div>
                    <div class="desc">Büyük ve küçük belge sınıfı olan ortakları seçin.</div>
                </div>
                <div class="visual-arrow">›</div>
            </div>
        </a>
        """,
        unsafe_allow_html=True
    )

    st.markdown(
        """
        <a class="click-card visual-card" href="?page=experience" target="_self">
            <div class="visual-card-row">
                <div class="visual-icon">📋</div>
                <div class="visual-text">
                    <div class="title">3. Bitirdiğim inşaatlar ile hangi sınıfı alabilirim?</div>
                    <div class="desc">Son 5 yıldaki işlerinizin toplamını veya son 15 yıldaki tek işinizi kullanın.</div>
                </div>
                <div class="visual-arrow">›</div>
            </div>
        </a>
        """,
        unsafe_allow_html=True
    )

    st.markdown(
        """
        <div class="apply-btn-wrap">
            <a class="apply-btn"
               href="https://ankara.csb.gov.tr/muteahhitlik-belgesi-islemleri-icin-iletisim-i-98574"
               target="_blank">
                BAŞVURU
            </a>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.divider()
    st.caption("Veriler: Çevre, Şehircilik ve İklim Değişikliği Bakanlığı 2026 Yapım Müteahhitliği Yeterlik Tablosu.")
    st.caption("Bilgilendirme amaçlıdır. Resmî başvuru/ruhsat işlemlerinde güncel YAMBİS ve ilgili idare kayıtları esas alınmalıdır.")

    st.divider()
    if LOGO_PATH.exists():
        brand_cols = st.columns([1.4, 1, 1.4])
        with brand_cols[1]:
            st.image(str(LOGO_PATH), use_container_width=True)

    st.markdown(
        """
        <div class="brand-footer">
            Bu uygulamanın hazırlanması <strong>DEVRAN MÂLİ MÜŞAVİRLİK</strong> tarafından sağlanmıştır
        </div>
        """,
        unsafe_allow_html=True,
    )

# ---------------------------------------------------------
# 1. M² HESAPLAMA
# ---------------------------------------------------------
elif st.session_state.page == "m2":
    if st.button("← Ana Sayfa"):
        go("home")

    st.header("📐 Mevcut sınıfımla kaç m² yapabilirim?")

    group = st.selectbox(
        "Müteahhitlik yetki belge grubunuz",
        GROUPS,
        index=GROUPS.index("H"),
    )

    building_class = st.selectbox(
        "Yapının sınıfı",
        list(BUILDING_CLASSES.keys()),
        format_func=lambda x: f"{x} — {BUILDING_CLASSES[x]}",
    )

    st.info(f"**{building_class}:** {BUILDING_CLASSES[building_class]}")

    if st.button("HESAPLA", type="primary", use_container_width=True):
        limit = MAX_M2[group][building_class]

        if group == "A":
            st.markdown(f"""
            <div class="result-card">
                <div><b>{group} Grubu • {building_class}</b></div>
                <div class="result-number">SINIRSIZ</div>
                <div>Resmî 2026 tablosunda A grubu için m² sınırı bulunmuyor.</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="result-card">
                <div><b>{group} Grubu • {building_class}</b></div>
                <div class="result-number">{fmt_m2(limit)}</div>
                <div>Tek parselde üstlenilebilecek azami toplam inşaat alanı</div>
            </div>
            """, unsafe_allow_html=True)

        st.warning(
            "Bu değer **tek parseldeki toplam inşaat metrekaresi** içindir. "
            "Resmî 2026 tablosuna göre, tabloda belirtilen m² sınırı aşılmamak kaydıyla "
            "farklı ada/parsellerde yapılabilecek iş adedi için ayrıca bir sınır belirtilmemiştir."
        )

# ---------------------------------------------------------
# 2. İŞ ORTAKLIĞI / SINIF BİRLEŞTİRME
# ---------------------------------------------------------
elif st.session_state.page == "joint":
    if st.button("← Ana Sayfa"):
        go("home")

    st.header("🤝 Sınıfları birleştirirsem hangi sınıf olur?")

    # 1. ortak her zaman belge grubu daha yüksek olan ortak olarak seçilir.
    # H grubu en düşük grup olduğu için kendisinden daha küçük grup bulunmadığından
    # birinci ortak seçiminde H gösterilmez.
    big_group_options = GROUPS[:-1]

    big_group = st.selectbox(
        "BÜYÜK BELGE SINIFI OLAN ORTAK",
        big_group_options,
        index=big_group_options.index("G"),
        key="big_group",
    )

    # Yalnızca seçilen büyük gruptan daha düşük belge gruplarını göster.
    big_index = GROUP_RANK[big_group]
    small_group_options = GROUPS[big_index + 1:]

    small_group = st.selectbox(
        "KÜÇÜK BELGE SINIFI OLAN ORTAK",
        small_group_options,
        index=0,
        key=f"small_group_for_{big_group}",
    )

    st.caption(
        f"**{big_group}** grubundan daha düşük belge grupları arasından seçim yapabilirsiniz. "
        "Büyük belge sınıfı olan ortak hesaplamada pilot ortak kabul edilir."
    )

    if st.button("ORTAKLIK GRUBUNU BUL", type="primary", use_container_width=True):
        result, required_pilot, required_other = best_joint_group(big_group, small_group)

        st.markdown(f"""
        <div class="joint-result">
            <div><b>Büyük belge sınıfı: {big_group} &nbsp; + &nbsp; Küçük belge sınıfı: {small_group}</b></div>
            <div style="margin-top:.6rem;">Ulaşılabilecek en yüksek ortaklık grubu</div>
            <div class="result-number">{result} GRUBU</div>
        </div>
        """, unsafe_allow_html=True)

        st.success(
            f"**{result} grubu** için 2026 tablosundaki asgari eşleşme: "
            f"Büyük belge sınıfı olan ortak **en az {required_pilot}**, "
            f"küçük belge sınıfı olan ortak **en az {required_other}**."
        )

        st.warning(
            "Bu hesap seçilen iki ortağın mevcut yetki belge grupları üzerinden "
            "2026 iş ortaklığı yeterlik tablosunu uygular. Ortaklık oranı, iş deneyim belgeleri, "
            "YAMBİS kayıtları ve diğer başvuru şartları resmî değerlendirmede ayrıca kontrol edilir."
        )

    with st.expander("2026 iş ortaklığı asgari grup tablosunu göster"):
        rows = []
        for target in GROUPS:
            p, o = JOINT_REQUIREMENTS[target]
            rows.append({
                "Hedef Grup": target,
                "Büyük Belge Sınıfı En Az": p,
                "Küçük Belge Sınıfı En Az": o
            })
        st.dataframe(rows, use_container_width=True, hide_index=True)



# ---------------------------------------------------------
# 3. BİTİRİLEN İNŞAATLARDAN BELGE SINIFI HESABI
# ---------------------------------------------------------
elif st.session_state.page == "experience":

    # -----------------------------------------------------
    # Dinamik satır kaldırma yardımcıları
    # -----------------------------------------------------
    def _copy_state_key(src_key, dst_key):
        if src_key in st.session_state:
            st.session_state[dst_key] = st.session_state[src_key]
        else:
            st.session_state.pop(dst_key, None)

    def _clear_exp5_block(project_i, block_j):
        for prefix in ("exp5_row_parcel", "exp5_area", "exp5_class"):
            st.session_state.pop(f"{prefix}_{project_i}_{block_j}", None)

    def _copy_exp5_block(src_project, src_block, dst_project, dst_block):
        for prefix in ("exp5_row_parcel", "exp5_area", "exp5_class"):
            _copy_state_key(
                f"{prefix}_{src_project}_{src_block}",
                f"{prefix}_{dst_project}_{dst_block}",
            )

    def _clear_exp5_project(project_i):
        for prefix in ("exp5_parcel", "exp5_share", "exp5_note", "exp5_block_count"):
            st.session_state.pop(f"{prefix}_{project_i}", None)

        for block_j in range(1, 11):
            _clear_exp5_block(project_i, block_j)

    def _copy_exp5_project(src_i, dst_i):
        # Önce hedefte kalmış eski verileri temizle.
        _clear_exp5_project(dst_i)

        for prefix in ("exp5_parcel", "exp5_share", "exp5_note", "exp5_block_count"):
            _copy_state_key(f"{prefix}_{src_i}", f"{prefix}_{dst_i}")

        for block_j in range(1, 11):
            _copy_exp5_block(src_i, block_j, dst_i, block_j)

    def _remove_exp5_project(remove_i):
        visible = int(st.session_state.get("exp5_visible_rows", 1))
        if remove_i <= 1 or remove_i > visible:
            return

        # Silinen inşaatın altındakileri bir sıra yukarı taşı.
        for project_i in range(remove_i, visible):
            _copy_exp5_project(project_i + 1, project_i)

        _clear_exp5_project(visible)
        st.session_state.exp5_visible_rows = max(1, visible - 1)

    def _remove_exp5_block(project_i, remove_j):
        count_key = f"exp5_block_count_{project_i}"
        count = int(st.session_state.get(count_key, 1))

        if remove_j <= 1 or remove_j > count:
            return

        # Silinen bloğun altındaki blokları yukarı kaydır.
        for block_j in range(remove_j, count):
            _copy_exp5_block(project_i, block_j + 1, project_i, block_j)

        _clear_exp5_block(project_i, count)
        st.session_state[count_key] = max(1, count - 1)

    def _clear_exp15_block(block_j):
        for prefix in ("exp15_row_parcel", "exp15_area", "exp15_class"):
            st.session_state.pop(f"{prefix}_{block_j}", None)

    def _copy_exp15_block(src_block, dst_block):
        for prefix in ("exp15_row_parcel", "exp15_area", "exp15_class"):
            _copy_state_key(
                f"{prefix}_{src_block}",
                f"{prefix}_{dst_block}",
            )

    def _remove_exp15_block(remove_j):
        count = int(st.session_state.get("exp15_block_count", 1))

        if remove_j <= 1 or remove_j > count:
            return

        for block_j in range(remove_j, count):
            _copy_exp15_block(block_j + 1, block_j)

        _clear_exp15_block(count)
        st.session_state.exp15_block_count = max(1, count - 1)

    if st.button("← Ana Sayfa", key="exp_home"):
        go("home")

    st.header("🏢 Bitirdiğim inşaatlar ile hangi sınıfı alabilirim?")

    method = st.radio(
        "Hesaplama yöntemini seçin",
        [
            "1 - Son 5 yılda bitirdiğim inşaatları toplayacağım",
            "2 - Son 15 yılda bitirdiğim 1 inşaatı kullanacağım",
        ],
        key="experience_method",
    )

    st.caption(
        "2026 güncel yapı yaklaşık birim maliyetleri otomatik kullanılır. "
        "İlk açılışta normal tek inşaat satırı gelir. "
        "Aynı ada/parselde farklı yapı sınıfında blok/bölüm varsa BLOK EKLE ile ilave satır açabilirsiniz. "
        "Ada/parsel alanına isterseniz blok adını da yazabilirsiniz. "
        "Aynı inşaat altındaki satırlar birlikte toplanır ve inşaat hissesi uygulanır. "
        "Sonuçlar hem %90 uygulanarak hem de %90 uygulanmadan ayrı ayrı hesaplanır."
    )

    # ---------------------------------------------------------
    # SON 5 YIL
    # ---------------------------------------------------------
    if method.startswith("1"):
        st.subheader("Son 5 yılda bitirilen inşaatlar")

        total_experience_90 = 0.0
        total_experience_no90 = 0.0
        entered_projects = 0
        row_results = []       # PDF için blok bazlı satırlar
        project_results = []   # 3 kat kuralı için inşaat/ada-parsel bazlı toplamlar

        if "exp5_visible_rows" not in st.session_state:
            st.session_state.exp5_visible_rows = 1

        visible_rows = min(max(int(st.session_state.exp5_visible_rows), 1), 10)

        for i in range(1, visible_rows + 1):
            title_col, remove_col = st.columns([8.8, 0.7])

            with title_col:
                st.markdown(f"### {i}. İNŞAAT")

            with remove_col:
                if i > 1:
                    st.button(
                        "✕",
                        key=f"remove_exp5_project_{i}",
                        help=f"{i}. inşaatı kaldır",
                        on_click=_remove_exp5_project,
                        args=(i,),
                    )

            # İnşaat üst bilgileri: ada/parsel + hisse
            col_parcel, col_share = st.columns([1.7, 0.8])

            with col_parcel:
                ada_parsel = st.text_input(
                    "ADA PARSEL / BLOK BİLGİSİ",
                    placeholder="Örn: 123 / 45 veya 123 / 45 A Blok",
                    key=f"exp5_parcel_{i}",
                )

            with col_share:
                share = st.number_input(
                    "İNŞAAT HİSSESİ (%)",
                    min_value=0.0,
                    max_value=100.0,
                    value=100.0,
                    step=0.01,
                    format="%.2f",
                    key=f"exp5_share_{i}",
                )

            # Her inşaat ilk açılışta tek normal satırla başlar.
            # BLOK EKLE ile ilave satırlar açılır.
            block_count_key = f"exp5_block_count_{i}"
            if block_count_key not in st.session_state:
                st.session_state[block_count_key] = 1

            block_count = min(max(int(st.session_state[block_count_key]), 1), 10)

            project_gross_90 = 0.0
            project_gross_no90 = 0.0
            project_has_area = False

            for j in range(1, block_count + 1):
                # İlk satır normal inşaat satırıdır; otomatik blok adı yoktur.
                # İkinci ve sonraki satırlar yalnızca BLOK EKLE ile açılır.
                if j == 1:
                    st.markdown("**İNŞAAT BİLGİLERİ**")
                else:
                    block_title_col, block_remove_col = st.columns([8.8, 0.7])
                    with block_title_col:
                        st.markdown(f"**EK BLOK / BÖLÜM {j - 1}**")
                    with block_remove_col:
                        st.button(
                            "✕",
                            key=f"remove_exp5_block_{i}_{j}",
                            help="Bu bloğu/bölümü kaldır",
                            on_click=_remove_exp5_block,
                            args=(i, j),
                        )

                if j == 1:
                    row_ada_parsel = ada_parsel
                else:
                    row_ada_parsel = st.text_input(
                        "ADA PARSEL / BLOK BİLGİSİ",
                        value=ada_parsel,
                        placeholder="Örn: 123 / 45 A Blok",
                        key=f"exp5_row_parcel_{i}_{j}",
                    )

                col_area, col_class, col_cost = st.columns([0.95, 1.65, 1.0])

                with col_area:
                    area = st.number_input(
                        "İNŞAAT ALANI (m²)",
                        min_value=0.0,
                        step=1.0,
                        value=0.0,
                        key=f"exp5_area_{i}_{j}",
                    )

                with col_class:
                    bclass = st.selectbox(
                        "GÜNCEL İNŞAAT SINIFI",
                        list(BUILDING_UNIT_COSTS.keys()),
                        format_func=lambda x: f"{x} — {BUILDING_CLASSES[x]}",
                        index=list(BUILDING_UNIT_COSTS.keys()).index("III-B"),
                        key=f"exp5_class_{i}_{j}",
                    )

                unit_cost = BUILDING_UNIT_COSTS[bclass]

                with col_cost:
                    st.markdown("**GÜNCEL m² MALİYETİ**")
                    st.markdown(
                        f"<div style='padding:0.55rem 0.7rem;border:1px solid #d9dee8;"
                        f"border-radius:10px;background:#f7f9fc;font-weight:800;text-align:center;'>"
                        f"{fmt_tl(unit_cost).replace(',00 ₺',' ₺')}/m²</div>",
                        unsafe_allow_html=True,
                    )

                if area > 0:
                    project_has_area = True

                    # İki senaryo:
                    # 1) m² x birim maliyet x %85 x %90
                    # 2) m² x birim maliyet x %85
                    base_85 = area * unit_cost * 0.85
                    block_90 = base_85 * 0.90
                    block_no90 = base_85

                    project_gross_90 += block_90
                    project_gross_no90 += block_no90

                    share_ratio = share / 100.0

                    # PDF'de iki iş deneyimi tutarı yan yana gösterilir.
                    row_results.append({
                        "row": f"{i}.{j}",
                        "project_id": i,
                        "project_label": ada_parsel.strip() or f"{i}. İnşaat",
                        "ada_parsel": (
                            f"{row_ada_parsel.strip() or ada_parsel.strip() or f'{i}. İnşaat'} "
                            f"(%{share:g})"
                        ),
                        "area": area,
                        "class": bclass,
                        "unit_cost": unit_cost,
                        "amount": block_90 * share_ratio,
                        "amount_90": block_90 * share_ratio,
                        "amount_no90": block_no90 * share_ratio,
                    })

                if j < block_count:
                    st.markdown("---")

            # Aynı ada/parselde yeni blok
            if block_count < 10:
                if st.button(
                    "＋ BLOK EKLE",
                    key=f"add_exp5_block_{i}",
                    use_container_width=False,
                ):
                    st.session_state[block_count_key] = block_count + 1
                    st.rerun()
            else:
                st.caption("Bu inşaat için en fazla 10 blok ekleyebilirsiniz.")

            construction_note = st.text_input(
                "NOT",
                placeholder="Bu inşaatla ilgili notunuzu yazabilirsiniz...",
                key=f"exp5_note_{i}",
            )

            if project_has_area:
                entered_projects += 1
                share_ratio = share / 100.0
                project_amount_90 = project_gross_90 * share_ratio
                project_amount_no90 = project_gross_no90 * share_ratio

                total_experience_90 += project_amount_90
                total_experience_no90 += project_amount_no90

                project_results.append({
                    "row": i,
                    "ada_parsel": ada_parsel.strip() or f"{i}. İnşaat",
                    "share": share,
                    "note": construction_note.strip(),
                    "amount": project_amount_90,
                    "amount_90": project_amount_90,
                    "amount_no90": project_amount_no90,
                    "gross_amount_90": project_gross_90,
                    "gross_amount_no90": project_gross_no90,
                    "block_count": block_count,
                })

                for pdf_row in row_results:
                    if pdf_row.get("project_id") == i:
                        pdf_row["project_total"] = project_amount_90
                        pdf_row["project_total_90"] = project_amount_90
                        pdf_row["project_total_no90"] = project_amount_no90

                st.info(
                    f"**{i}. inşaat - %90 uygulanırsa:** {fmt_tl(project_amount_90)}  |  "
                    f"**%90 uygulanmazsa:** {fmt_tl(project_amount_no90)}  "
                    f"— Hisse: **%{share:g}**"
                )

            if i < visible_rows:
                st.divider()

        st.write("")

        if visible_rows < 10:
            if st.button(
                "＋ İNŞAAT EKLE",
                key="add_exp5_row",
                use_container_width=True,
            ):
                st.session_state.exp5_visible_rows = visible_rows + 1
                st.rerun()
        else:
            st.caption("En fazla 10 inşaat ekleyebilirsiniz.")

        if entered_projects > 0:
            # ---------------- %90 UYGULANAN SENARYO ----------------
            normal_group_90 = work_experience_group(total_experience_90)
            largest_project_90 = max(project_results, key=lambda x: x["amount_90"])
            three_times_limit_90 = largest_project_90["amount_90"] * 3
            capped_experience_90 = min(total_experience_90, three_times_limit_90)
            capped_group_90 = work_experience_group(capped_experience_90)
            cap_applied_90 = total_experience_90 > three_times_limit_90

            # ---------------- %90 UYGULANMAYAN SENARYO --------------
            normal_group_no90 = work_experience_group(total_experience_no90)
            largest_project_no90 = max(project_results, key=lambda x: x["amount_no90"])
            three_times_limit_no90 = largest_project_no90["amount_no90"] * 3
            capped_experience_no90 = min(total_experience_no90, three_times_limit_no90)
            capped_group_no90 = work_experience_group(capped_experience_no90)
            cap_applied_no90 = total_experience_no90 > three_times_limit_no90

            st.markdown("### İki Senaryolu Sonuç")

            result_col_90, result_col_no90 = st.columns(2)

            with result_col_90:
                st.markdown(f"""
                <div class="result-card">
                    <div><b>%90 UYGULANIRSA</b></div>
                    <div style="font-size:.88rem;margin-top:.35rem;">Normal toplam</div>
                    <div style="font-size:1.35rem;font-weight:800;">{fmt_tl(total_experience_90)}</div>
                    <div style="margin-top:.45rem;">Dikkate alınan tutar</div>
                    <div class="result-number">{fmt_tl(capped_experience_90)}</div>
                    <div style="font-size:1.8rem;font-weight:800;">{capped_group_90} GRUBU</div>
                </div>
                """, unsafe_allow_html=True)

                if cap_applied_90:
                    st.caption(
                        f"3 kat kuralı: {largest_project_90['ada_parsel']} - "
                        f"{fmt_tl(largest_project_90['amount_90'])} x 3"
                    )
                else:
                    st.caption("3 kat sınırı aşılmadı.")

            with result_col_no90:
                st.markdown(f"""
                <div class="joint-result">
                    <div><b>%90 UYGULANMAZSA</b></div>
                    <div style="font-size:.88rem;margin-top:.35rem;">Normal toplam</div>
                    <div style="font-size:1.35rem;font-weight:800;">{fmt_tl(total_experience_no90)}</div>
                    <div style="margin-top:.45rem;">Dikkate alınan tutar</div>
                    <div class="result-number">{fmt_tl(capped_experience_no90)}</div>
                    <div style="font-size:1.8rem;font-weight:800;">{capped_group_no90} GRUBU</div>
                </div>
                """, unsafe_allow_html=True)

                if cap_applied_no90:
                    st.caption(
                        f"3 kat kuralı: {largest_project_no90['ada_parsel']} - "
                        f"{fmt_tl(largest_project_no90['amount_no90'])} x 3"
                    )
                else:
                    st.caption("3 kat sınırı aşılmadı.")

            if capped_group_90 != capped_group_no90:
                st.warning(
                    f"Belge grubu iki hesaba göre değişiyor: "
                    f"**%90 uygulanırsa {capped_group_90}**, "
                    f"**%90 uygulanmazsa {capped_group_no90}**. "
                    f"Başvuruda sözleşme yılına göre geçerli hesap dikkate alınmalıdır."
                )
            else:
                st.success(
                    f"Her iki hesapta da sonuç **{capped_group_90} grubu**. "
                    f"Tutarlar farklı olsa da belge grubu değişmiyor."
                )

            st.caption(
                "Aynı inşaat altında eklenen tüm satırlar tek inşaat olarak birlikte değerlendirilir. "
                "İnşaat hissesi toplam üzerine uygulanır. 3 kat sınırı her senaryo için ayrı hesaplanır."
            )

            pdf_notes = [
                {
                    "ada_parsel": p["ada_parsel"],
                    "note": p["note"],
                }
                for p in project_results
                if p.get("note", "").strip()
            ]

            pdf_bytes = create_experience_pdf(
                method_name="Son 5 yılda bitirilen inşaatların toplamı",
                rows=row_results,
                total_amount=capped_experience_90,
                result_group=capped_group_90,
                normal_total=total_experience_90,
                normal_group=normal_group_90,
                largest_row=largest_project_90,
                three_times_limit=three_times_limit_90,
                cap_applied=cap_applied_90,
                notes=pdf_notes,
                total_amount_no90=capped_experience_no90,
                result_group_no90=capped_group_no90,
                normal_total_no90=total_experience_no90,
                normal_group_no90=normal_group_no90,
                largest_row_no90=largest_project_no90,
                three_times_limit_no90=three_times_limit_no90,
                cap_applied_no90=cap_applied_no90,
            )

            st.download_button(
                "📄 DÖKÜM AL",
                data=pdf_bytes,
                file_name=f"muteahhitlik_is_deneyim_dokumu_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
                mime="application/pdf",
                use_container_width=True,
                type="primary",
                key="download_exp5_pdf",
            )
        else:
            st.info("Hesaplama için en az bir inşaatın/blokun alanını girin.")

    # ---------------------------------------------------------
    # SON 15 YIL - TEK İNŞAAT
    # ---------------------------------------------------------
    else:
        st.subheader("Son 15 yıldaki tek inşaat")

        col_parcel, col_share = st.columns([1.7, 0.8])

        with col_parcel:
            ada_parsel = st.text_input(
                "ADA PARSEL / BLOK BİLGİSİ",
                placeholder="Örn: 123 / 45 veya 123 / 45 A Blok",
                key="exp15_parcel",
            )

        with col_share:
            share = st.number_input(
                "İNŞAAT HİSSESİ (%)",
                min_value=0.0,
                max_value=100.0,
                value=100.0,
                step=0.01,
                format="%.2f",
                key="exp15_share",
            )

        if "exp15_block_count" not in st.session_state:
            st.session_state.exp15_block_count = 1

        block_count = min(max(int(st.session_state.exp15_block_count), 1), 10)
        project_gross_90 = 0.0
        project_gross_no90 = 0.0
        single_rows = []

        for j in range(1, block_count + 1):
            if j == 1:
                st.markdown("**İNŞAAT BİLGİLERİ**")
            else:
                block_title_col, block_remove_col = st.columns([8.8, 0.7])
                with block_title_col:
                    st.markdown(f"**EK BLOK / BÖLÜM {j - 1}**")
                with block_remove_col:
                    st.button(
                        "✕",
                        key=f"remove_exp15_block_{j}",
                        help="Bu bloğu/bölümü kaldır",
                        on_click=_remove_exp15_block,
                        args=(j,),
                    )

            if j == 1:
                row_ada_parsel = ada_parsel
            else:
                row_ada_parsel = st.text_input(
                    "ADA PARSEL / BLOK BİLGİSİ",
                    value=ada_parsel,
                    placeholder="Örn: 123 / 45 A Blok",
                    key=f"exp15_row_parcel_{j}",
                )

            col_area, col_class, col_cost = st.columns([0.95, 1.65, 1.0])

            with col_area:
                area = st.number_input(
                    "İNŞAAT ALANI (m²)",
                    min_value=0.0,
                    step=1.0,
                    value=0.0,
                    key=f"exp15_area_{j}",
                )

            with col_class:
                bclass = st.selectbox(
                    "GÜNCEL İNŞAAT SINIFI",
                    list(BUILDING_UNIT_COSTS.keys()),
                    format_func=lambda x: f"{x} — {BUILDING_CLASSES[x]}",
                    index=list(BUILDING_UNIT_COSTS.keys()).index("III-B"),
                    key=f"exp15_class_{j}",
                )

            unit_cost = BUILDING_UNIT_COSTS[bclass]

            with col_cost:
                st.markdown("**GÜNCEL m² MALİYETİ**")
                st.markdown(
                    f"<div style='padding:0.55rem 0.7rem;border:1px solid #d9dee8;"
                    f"border-radius:10px;background:#f7f9fc;font-weight:800;text-align:center;'>"
                    f"{fmt_tl(unit_cost).replace(',00 ₺',' ₺')}/m²</div>",
                    unsafe_allow_html=True,
                )

            if area > 0:
                base_85 = area * unit_cost * 0.85
                block_90 = base_85 * 0.90
                block_no90 = base_85
                project_gross_90 += block_90
                project_gross_no90 += block_no90

                share_ratio = share / 100.0

                single_rows.append({
                    "row": f"1.{j}",
                    "project_id": 1,
                    "project_label": ada_parsel.strip() or "1. İnşaat",
                    "ada_parsel": (
                        f"{row_ada_parsel.strip() or ada_parsel.strip() or '1. İnşaat'} "
                        f"(%{share:g})"
                    ),
                    "area": area,
                    "class": bclass,
                    "unit_cost": unit_cost,
                    "amount": block_90 * share_ratio * 2,
                    "amount_90": block_90 * share_ratio * 2,
                    "amount_no90": block_no90 * share_ratio * 2,
                })

            if j < block_count:
                st.markdown("---")

        if block_count < 10:
            if st.button(
                "＋ BLOK EKLE",
                key="add_exp15_block",
                use_container_width=False,
            ):
                st.session_state.exp15_block_count = block_count + 1
                st.rerun()

        construction_note = st.text_input(
            "NOT",
            placeholder="Bu inşaatla ilgili notunuzu yazabilirsiniz...",
            key="exp15_note",
        )

        if project_gross_90 > 0:
            share_ratio = share / 100.0

            share_adjusted_90 = project_gross_90 * share_ratio
            share_adjusted_no90 = project_gross_no90 * share_ratio

            total_experience_90 = share_adjusted_90 * 2
            total_experience_no90 = share_adjusted_no90 * 2

            result_group_90 = work_experience_group(total_experience_90)
            result_group_no90 = work_experience_group(total_experience_no90)

            for pdf_row in single_rows:
                pdf_row["project_total"] = total_experience_90
                pdf_row["project_total_90"] = total_experience_90
                pdf_row["project_total_no90"] = total_experience_no90

            st.markdown("### İki Senaryolu Sonuç")
            result_col_90, result_col_no90 = st.columns(2)

            with result_col_90:
                st.markdown(f"""
                <div class="result-card">
                    <div><b>%90 UYGULANIRSA</b></div>
                    <div style="margin-top:.4rem;">2 kat dikkate alınan tutar</div>
                    <div class="result-number">{fmt_tl(total_experience_90)}</div>
                    <div style="font-size:1.8rem;font-weight:800;">{result_group_90} GRUBU</div>
                </div>
                """, unsafe_allow_html=True)

            with result_col_no90:
                st.markdown(f"""
                <div class="joint-result">
                    <div><b>%90 UYGULANMAZSA</b></div>
                    <div style="margin-top:.4rem;">2 kat dikkate alınan tutar</div>
                    <div class="result-number">{fmt_tl(total_experience_no90)}</div>
                    <div style="font-size:1.8rem;font-weight:800;">{result_group_no90} GRUBU</div>
                </div>
                """, unsafe_allow_html=True)

            if result_group_90 != result_group_no90:
                st.warning(
                    f"Belge grubu iki hesaba göre değişiyor: "
                    f"**%90 uygulanırsa {result_group_90}**, "
                    f"**%90 uygulanmazsa {result_group_no90}**."
                )
            else:
                st.success(
                    f"Her iki hesapta da sonuç **{result_group_90} grubu**."
                )

            pdf_notes = []
            if construction_note.strip():
                pdf_notes.append({
                    "ada_parsel": ada_parsel.strip() or "1. İnşaat",
                    "note": construction_note.strip(),
                })

            pdf_bytes = create_experience_pdf(
                method_name="Son 15 yıldaki tek inşaatın 2 kat dikkate alınması",
                rows=single_rows,
                total_amount=total_experience_90,
                result_group=result_group_90,
                normal_total=total_experience_90,
                normal_group=result_group_90,
                notes=pdf_notes,
                total_amount_no90=total_experience_no90,
                result_group_no90=result_group_no90,
                normal_total_no90=total_experience_no90,
                normal_group_no90=result_group_no90,
            )

            st.download_button(
                "📄 DÖKÜM AL",
                data=pdf_bytes,
                file_name=f"muteahhitlik_is_deneyim_dokumu_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
                mime="application/pdf",
                use_container_width=True,
                type="primary",
                key="download_exp15_pdf",
            )
        else:
            st.info("Hesaplama için en az bir blok/inşaat alanını girin.")

    with st.expander("2026 asgari iş deneyim tutarlarını göster"):
        table_rows = [
            {"Belge Grubu": group, "Asgari İş Deneyim Tutarı": fmt_tl(amount)}
            for group, amount in WORK_EXPERIENCE_MIN.items()
        ]
        table_rows.append({"Belge Grubu": "H", "Asgari İş Deneyim Tutarı": "Asgari iş deneyimi aranmaz"})
        st.dataframe(table_rows, use_container_width=True, hide_index=True)

    st.caption(
        "Sonuç yalnızca asgari iş deneyim tutarı kriterine göre hesaplanır. "
        "%90 oranının uygulanıp uygulanmayacağı sözleşme yılı ve ilgili başvuru şartlarına göre değerlendirilmelidir. "
        "Üst gruplarda ekonomik, mali, teknik personel ve diğer yeterlik şartları ayrıca aranabilir."
    )
