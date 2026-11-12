import streamlit as st
from io import BytesIO
from datetime import datetime, date, timedelta
import os
import re
import requests
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


# ---------------------------------------------------------
# SÖZLEŞME TARİHİNE GÖRE İŞ DENEYİMİ GÜNCELLEME
# ---------------------------------------------------------
# Yİ-ÜFE aylık endeksleri için yerleşik güvenli kopya.
# Canlı TCMB EVDS bağlantısı varsa bu değerlerin üstüne yeni yayımlanan aylar eklenir.
# Seri: TP.TUFE1YI.T1 (Yurt İçi Üretici Fiyat Endeksi, 2003=100)
_YI_UFE_YEARLY = {
    2011: [182.75,185.90,188.17,189.32,189.61,189.62,189.57,192.91,195.89,199.03,200.32,202.33],
    2012: [203.10,202.91,203.64,203.81,204.89,201.83,201.20,201.71,203.79,204.15,207.54,207.29],
    2013: [206.91,206.65,208.33,207.27,209.34,212.39,214.50,214.59,216.48,217.97,219.31,221.74],
    2014: [229.10,232.27,233.98,234.18,232.96,233.09,234.79,235.78,237.79,239.97,237.65,235.84],
    2015: [236.61,239.46,241.97,245.42,248.15,248.78,247.99,250.43,254.25,253.74,250.13,249.31],
    2016: [250.67,250.16,251.17,252.47,256.21,257.27,257.81,258.01,258.77,260.94,266.16,274.09],
    2017: [284.99,288.59,291.58,293.79,295.31,295.52,297.65,300.18,300.90,306.04,312.21,316.48],
    2018: [319.60,328.17,333.21,341.88,354.85,365.60,372.06,396.62,439.78,443.78,432.55,422.94],
    2019: [424.86,425.26,431.98,444.85,456.74,457.16,452.63,449.96,450.55,451.31,450.97,454.08],
    2020: [462.42,464.64,468.69,474.69,482.02,485.37,490.33,501.85,515.13,533.44,555.18,568.27],
    2021: [583.38,590.52,614.93,641.63,666.79,693.54,710.61,730.28,741.58,780.45,858.43,1022.25],
    2022: [1129.03,1210.60,1321.90,1423.27,1548.01,1652.75,1738.21,1780.05,1865.09,2011.13,2026.08,2021.19],
    2023: [2105.17,2138.04,2147.44,2164.94,2179.02,2320.72,2511.75,2659.60,2749.98,2803.29,2882.04,2915.02],
    2024: [3035.59,3149.03,3252.79,3369.98,3435.96,3483.25,3550.88,3610.51,3659.84,3707.10,3731.43,3746.52],
    2025: [3861.33,3943.01,4017.30,4128.19,4230.69,4334.94,4409.73,4518.89,4632.89,4708.20,4747.63,4783.04],
    2026: [4910.53,5029.76,5145.36,5308.46,5454.58,5552.52,5637.14,5781.74,5901.26,5998.51],
}
YI_UFE_FALLBACK = {
    f"{year}-{month:02d}": value
    for year, values in _YI_UFE_YEARLY.items()
    for month, value in enumerate(values, start=1)
}

# Sözleşme dönemindeki yapı yaklaşık birim maliyetleri.
# 2025-2026 yeni sınıflandırma; önceki yıllarda eşdeğer yapı grupları kullanılır.
CONTRACT_COST_2026 = BUILDING_UNIT_COSTS.copy()
CONTRACT_COST_2025 = {
    "II-B": 10200, "II-C": 12400, "III-A": 17100, "III-B": 18200,
    "III-C": 19150, "IV-A": 21500, "IV-B": 27500, "IV-C": 32600, "V-A": 34400,
}
CONTRACT_COST_2024 = {
    "II-B": 5250, "II-C": 7750, "III-A": 12250, "III-B": 14400,
    "III-C": 15300, "IV-A": 18700, "IV-B": 21300,
}
CONTRACT_COST_2023_1 = {
    "II-B": 3200, "II-C": 3575, "III-A": 4600, "III-B": 6350,
    "III-C": 6825, "IV-A": 8825, "IV-B": 10650, "V-A": 10650,
}
CONTRACT_COST_2023_2 = {
    "II-B": 3800, "II-C": 5350, "III-A": 7500, "III-B": 9000,
    "III-C": 10200, "IV-A": 12450, "IV-B": 13800, "V-A": 13800,
}
CONTRACT_COST_2022_1 = {
    "II-B": 1550, "II-C": 1700, "III-A": 2250, "III-B": 3000,
    "III-C": 3200, "IV-A": 4100, "IV-B": 4950, "V-A": 4950,
}
# 02.06.2022-30.06.2022 ara döneminde güvenle teyit edilen III-B tutarı.
CONTRACT_COST_2022_2 = {"III-B": 4275}
CONTRACT_COST_2022_3 = {
    "II-B": 2400, "III-A": 3450, "III-B": 4650,
    "III-C": 4950, "IV-A": 6400, "IV-B": 7700, "V-A": 7700,
}
CONTRACT_COST_2021 = {
    "II-B": 940, "II-C": 1030, "III-A": 1360, "III-B": 1800,
    "III-C": 1920, "IV-A": 2480, "IV-B": 2970, "V-A": 2970,
}

MONTH_NAMES_TR = {
    1:"Ocak",2:"Şubat",3:"Mart",4:"Nisan",5:"Mayıs",6:"Haziran",
    7:"Temmuz",8:"Ağustos",9:"Eylül",10:"Ekim",11:"Kasım",12:"Aralık",
}

def previous_month(d):
    first = date(d.year, d.month, 1)
    return first - timedelta(days=1)

def month_key(d):
    return f"{d.year}-{d.month:02d}"

def month_label(d):
    return f"{MONTH_NAMES_TR[d.month]} {d.year}"

def _get_evds_api_key():
    try:
        key = str(st.secrets.get("EVDS_API_KEY", "")).strip()
        if key:
            return key
    except Exception:
        pass
    return os.environ.get("EVDS_API_KEY", "").strip()

def _parse_evds_month(text):
    text = str(text or "").strip()
    for fmt in ("%d-%m-%Y", "%Y-%m-%d", "%Y-%m", "%m-%Y", "%Y/%m", "%m/%Y"):
        try:
            d = datetime.strptime(text, fmt).date()
            return f"{d.year}-{d.month:02d}"
        except ValueError:
            pass
    m = re.search(r"(20\d{2}|19\d{2})\D+(\d{1,2})", text)
    if m:
        return f"{int(m.group(1)):04d}-{int(m.group(2)):02d}"
    return None

@st.cache_data(ttl=21600, show_spinner=False)
def fetch_live_yiufe(api_key):
    """TCMB EVDS'den aylık Yİ-ÜFE serisini çeker. Hata olursa boş sözlük döndürür."""
    if not api_key:
        return {}
    end_date = date.today().strftime("%d-%m-%Y")
    path = (
        "series=TP.TUFE1YI.T1&startDate=01-01-2011&"
        f"endDate={end_date}&type=json"
    )
    endpoints = [
        f"https://evds2.tcmb.gov.tr/service/evds/{path}",
        f"https://evds3.tcmb.gov.tr/igmevdsms-dis/{path}",
    ]
    headers = {"key": api_key}
    for url in endpoints:
        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            payload = response.json()
            items = payload.get("items", []) if isinstance(payload, dict) else payload
            if not isinstance(items, list):
                continue
            parsed = {}
            for item in items:
                if not isinstance(item, dict):
                    continue
                key = _parse_evds_month(item.get("Tarih") or item.get("DATE") or item.get("Date"))
                if not key:
                    continue
                raw = None
                for field, value in item.items():
                    if "TUFE1YI" in str(field).upper():
                        raw = value
                        break
                if raw in (None, "", "null", "-"):
                    continue
                try:
                    value = float(str(raw).replace(".", "").replace(",", ".")) if "," in str(raw) else float(raw)
                except (TypeError, ValueError):
                    continue
                parsed[key] = value
            if parsed:
                return parsed
        except Exception:
            continue
    return {}

def get_yiufe_series():
    series = dict(YI_UFE_FALLBACK)
    api_key = _get_evds_api_key()
    live = fetch_live_yiufe(api_key) if api_key else {}
    series.update(live)
    return series, live, bool(api_key)

def get_yiufe_index(d, series, live):
    key = month_key(d)
    value = series.get(key)
    source = "TCMB EVDS" if key in live else "Yerleşik veri"
    return value, source

def historical_contract_cost(contract_date, building_class):
    """Sözleşme tarihinde geçerli/eşdeğer m² maliyetini ve dönem etiketini döndürür."""
    y = contract_date.year
    if y >= 2026:
        return CONTRACT_COST_2026.get(building_class), "2026"
    if y == 2025:
        return CONTRACT_COST_2025.get(building_class), "2025"
    if y == 2024:
        return CONTRACT_COST_2024.get(building_class), "2024 (eşdeğer yapı grubu)"
    if y == 2023:
        if contract_date < date(2023, 7, 1):
            return CONTRACT_COST_2023_1.get(building_class), "2023/1"
        return CONTRACT_COST_2023_2.get(building_class), "2023/2 (01.07.2023 sonrası)"
    if y == 2022:
        if contract_date < date(2022, 2, 18):
            return CONTRACT_COST_2021.get(building_class), "2021 tarifesi (18.02.2022 öncesi)"
        if contract_date < date(2022, 6, 2):
            return CONTRACT_COST_2022_1.get(building_class), "2022/1"
        if contract_date < date(2022, 7, 1):
            return CONTRACT_COST_2022_2.get(building_class), "2022/2 ara dönem"
        return CONTRACT_COST_2022_3.get(building_class), "2022/3 (01.07.2022 sonrası)"
    if y == 2021:
        return CONTRACT_COST_2021.get(building_class), "2021"
    return None, "Otomatik tarihsel m² maliyeti bulunamadı"

def synced_contract_cost_input(key_prefix, auto_cost, token):
    """Tarih/sınıf değişirse otomatik maliyeti yeniler; kullanıcı isterse değeri elle değiştirebilir."""
    value_key = f"{key_prefix}_value"
    token_key = f"{key_prefix}_token"
    if st.session_state.get(token_key) != token:
        st.session_state[token_key] = token
        st.session_state[value_key] = float(auto_cost or 0.0)
    return st.number_input(
        "SÖZLEŞME TARİHİ m² MALİYETİ",
        min_value=0.0,
        step=50.0,
        format="%.2f",
        key=value_key,
        help="Otomatik gelen tutarı gerekiyorsa elle değiştirebilirsiniz.",
    )

def date_based_block_calculation(area, current_cost, contract_cost, contract_date, application_date, yiufe_series, yiufe_live):
    """%90-%130 sınırları içinde sözleşme tarihine göre güncellenmiş blok iş deneyimini hesaplar."""
    if not area or area <= 0 or not contract_cost or contract_cost <= 0:
        return None
    base_month = previous_month(contract_date)
    target_month = previous_month(application_date)
    base_index, base_source = get_yiufe_index(base_month, yiufe_series, yiufe_live)
    target_index, target_source = get_yiufe_index(target_month, yiufe_series, yiufe_live)
    if not base_index or not target_index:
        return None

    yiufe_coeff = target_index / base_index
    cost_ratio = current_cost / contract_cost
    lower_coeff = cost_ratio * 0.90
    upper_coeff = cost_ratio * 1.30
    applied_coeff = max(lower_coeff, min(yiufe_coeff, upper_coeff))

    if yiufe_coeff < lower_coeff:
        reason = "%90 alt sınır uygulandı"
    elif yiufe_coeff > upper_coeff:
        reason = "%130 üst sınır uygulandı"
    else:
        reason = "Yİ-ÜFE katsayısı uygulandı"

    contract_base = area * contract_cost * 0.85
    amount = contract_base * applied_coeff
    return {
        "amount": amount,
        "yiufe_coeff": yiufe_coeff,
        "cost_ratio": cost_ratio,
        "lower_coeff": lower_coeff,
        "upper_coeff": upper_coeff,
        "applied_coeff": applied_coeff,
        "reason": reason,
        "base_month": base_month,
        "target_month": target_month,
        "base_index": base_index,
        "target_index": target_index,
        "base_source": base_source,
        "target_source": target_source,
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
    total_amount_auto=None,
    result_group_auto=None,
    normal_total_auto=None,
    normal_group_auto=None,
    largest_row_auto=None,
    three_times_limit_auto=None,
    cap_applied_auto=False,
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
            ["Hesap", Paragraph("Üç sonuç birlikte gösterilir: %90 alt sınır, %90'sız referans ve sözleşme tarihine göre.", small_style)],
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
        "Yapı",
        "m² Maliyeti",
        "İş Deneyimi\n(%90)",
        "İş Deneyimi\n(%90 Yok)",
        "Sözleşmeye\nGöre",
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
                (fmt_tl(row.get("amount_auto")).replace(" ₺", " TL") if row.get("amount_auto") is not None else "-"),
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
                auto_values = [r.get("amount_auto") for r in project_rows]
                project_experience_total_auto = row.get("project_total_auto")
                if project_experience_total_auto is None and all(v is not None for v in auto_values):
                    project_experience_total_auto = sum(float(v or 0) for v in auto_values)
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
                    (fmt_tl(project_experience_total_auto).replace(" ₺", " TL") if project_experience_total_auto is not None else "-"),
                ])
                summary_row_indexes.append(len(data) - 1)
                project_row_indexes.setdefault(current_project, []).append(len(data) - 1)
    else:
        data.append(["1", "", "", "", "", "", "", ""])

    info_table = Table(
        data,
        colWidths=[8 * mm, 36 * mm, 21 * mm, 14 * mm, 17 * mm, 27 * mm, 27 * mm, 27 * mm],
        repeatRows=1,
        hAlign="LEFT",
    )

    info_style = [
        ("BOX", (0, 0), (-1, -1), 0.8, colors.black),
        ("INNERGRID", (0, 0), (-1, -1), 0.45, colors.black),
        ("FONTNAME", (0, 0), (-1, 0), font_bold),
        ("FONTNAME", (0, 1), (-1, -1), font_regular),
        ("FONTSIZE", (0, 0), (-1, -1), 5.55),
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

    # Result section - üç sonuç birlikte gösterilir.
    if total_amount_no90 is None:
        total_amount_no90 = total_amount
        result_group_no90 = result_group
        normal_total_no90 = normal_total
        normal_group_no90 = normal_group
        largest_row_no90 = largest_row
        three_times_limit_no90 = three_times_limit
        cap_applied_no90 = cap_applied

    experience_rows = [
        ("A", WORK_EXPERIENCE_MIN["A"]), ("B", WORK_EXPERIENCE_MIN["B"]),
        ("B1", WORK_EXPERIENCE_MIN["B1"]), ("C", WORK_EXPERIENCE_MIN["C"]),
        ("C1", WORK_EXPERIENCE_MIN["C1"]), ("D", WORK_EXPERIENCE_MIN["D"]),
        ("D1", WORK_EXPERIENCE_MIN["D1"]), ("E", WORK_EXPERIENCE_MIN["E"]),
        ("E1", WORK_EXPERIENCE_MIN["E1"]), ("F", WORK_EXPERIENCE_MIN["F"]),
        ("F1", WORK_EXPERIENCE_MIN["F1"]), ("G", WORK_EXPERIENCE_MIN["G"]),
        ("G1", WORK_EXPERIENCE_MIN["G1"]), ("H", None),
    ]

    scenario_title_style = ParagraphStyle(
        "PDFScenarioTitle", parent=center_bold, fontSize=7.5, leading=8.3,
    )
    scenario_value_style = ParagraphStyle(
        "PDFScenarioValue", parent=value_style, fontSize=10.4, leading=11.3,
    )
    scenario_group_style = ParagraphStyle(
        "PDFScenarioGroup", parent=big_result, fontSize=18, leading=19,
    )
    tiny_center = ParagraphStyle(
        "PDFTinyCenter", parent=styles["Normal"], fontName=font_regular,
        fontSize=5.7, leading=6.4, alignment=TA_CENTER, textColor=colors.black,
    )

    def _scenario_box(label, final_amount, final_group, normal_amount, largest, cap_used, amount_key, auto=False):
        if final_amount is None or final_group is None:
            rows_local = [
                [Paragraph(label, scenario_title_style)],
                [Paragraph("HESAPLANAMADI", scenario_value_style)],
                [Paragraph("Sözleşme tarihi / tarihsel m² maliyeti / Yİ-ÜFE verisini kontrol edin.", tiny_center)],
            ]
        else:
            display_normal = normal_amount if normal_amount is not None else final_amount
            rows_local = [
                [Paragraph(label, scenario_title_style)],
                [Paragraph(fmt_tl(display_normal).replace(" ₺", " TL"), scenario_value_style)],
            ]
            if cap_used:
                source_parcel = str((largest or {}).get("ada_parsel", "-"))
                source_amount = (largest or {}).get(amount_key, (largest or {}).get("amount", 0))
                rows_local.extend([
                    [Paragraph("3 KATI SONRASI", scenario_title_style)],
                    [Paragraph(
                        f"{source_parcel}<br/>{fmt_tl(source_amount).replace(' ₺', ' TL')} x 3",
                        tiny_center,
                    )],
                    [Paragraph(fmt_tl(final_amount).replace(" ₺", " TL"), scenario_value_style)],
                ])
            else:
                rows_local.append([Paragraph("3 kat sınırı aşılmadı", tiny_center)])
            rows_local.extend([
                [Paragraph("ULAŞILABİLEN BELGE GRUBU", scenario_title_style)],
                [Paragraph(final_group, scenario_group_style)],
                [Paragraph("GRUBU", scenario_title_style)],
            ])
        box = Table(rows_local, colWidths=[56 * mm], hAlign="CENTER")
        box.setStyle(TableStyle([
            ("BOX", (0, 0), (-1, -1), 0.8, colors.black),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 1.2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 1.2),
        ]))
        return box

    box_90 = _scenario_box("%90 ALT SINIR", total_amount, result_group, normal_total, largest_row, cap_applied, "amount_90")
    box_no90 = _scenario_box("%90 UYGULANMAZSA", total_amount_no90, result_group_no90, normal_total_no90, largest_row_no90, cap_applied_no90, "amount_no90")
    box_auto = _scenario_box("SÖZLEŞME TARİHİNE GÖRE", total_amount_auto, result_group_auto, normal_total_auto, largest_row_auto, cap_applied_auto, "amount_auto", auto=True)

    story.append(Paragraph("HESAPLAMA SONUÇLARI", section_style))
    result_table = Table([[box_90, box_no90, box_auto]], colWidths=[58 * mm, 58 * mm, 58 * mm], hAlign="LEFT")
    result_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    story.append(result_table)
    story.append(Spacer(1, 30 * mm))

    threshold_data = [[Paragraph(f"{datetime.now().year} YILI ASGARİ İŞ DENEYİM TUTARLARI", center_bold), ""]]
    for group_name, min_amount in experience_rows:
        amount_text = "Asgari iş deneyimi aranmaz." if min_amount is None else fmt_tl(min_amount).replace(",00 ₺", " TL")
        threshold_data.append([group_name, amount_text])
    threshold_result = Table(threshold_data, colWidths=[45 * mm, 95 * mm], hAlign="CENTER")
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
    for grp in {g for g in (result_group, result_group_no90, result_group_auto) if g}:
        threshold_row = 1 + [g for g, _ in experience_rows].index(grp)
        threshold_style.extend([
            ("FONTNAME", (0, threshold_row), (-1, threshold_row), font_bold),
            ("LINEABOVE", (0, threshold_row), (-1, threshold_row), 0.75, colors.black),
            ("LINEBELOW", (0, threshold_row), (-1, threshold_row), 0.75, colors.black),
        ])
    threshold_result.setStyle(TableStyle(threshold_style))
    story.append(threshold_result)
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
            _copy_state_key(f"{prefix}_{src_project}_{src_block}", f"{prefix}_{dst_project}_{dst_block}")

    def _clear_exp5_project(project_i):
        for prefix in ("exp5_parcel", "exp5_share", "exp5_note", "exp5_block_count", "exp5_contract_date"):
            st.session_state.pop(f"{prefix}_{project_i}", None)
        for block_j in range(1, 11):
            _clear_exp5_block(project_i, block_j)

    def _copy_exp5_project(src_i, dst_i):
        _clear_exp5_project(dst_i)
        for prefix in ("exp5_parcel", "exp5_share", "exp5_note", "exp5_block_count", "exp5_contract_date"):
            _copy_state_key(f"{prefix}_{src_i}", f"{prefix}_{dst_i}")
        for block_j in range(1, 11):
            _copy_exp5_block(src_i, block_j, dst_i, block_j)

    def _remove_exp5_project(remove_i):
        visible = int(st.session_state.get("exp5_visible_rows", 1))
        if remove_i <= 1 or remove_i > visible:
            return
        for project_i in range(remove_i, visible):
            _copy_exp5_project(project_i + 1, project_i)
        _clear_exp5_project(visible)
        st.session_state.exp5_visible_rows = max(1, visible - 1)

    def _remove_exp5_block(project_i, remove_j):
        count_key = f"exp5_block_count_{project_i}"
        count = int(st.session_state.get(count_key, 1))
        if remove_j <= 1 or remove_j > count:
            return
        for block_j in range(remove_j, count):
            _copy_exp5_block(project_i, block_j + 1, project_i, block_j)
        _clear_exp5_block(project_i, count)
        st.session_state[count_key] = max(1, count - 1)

    def _clear_exp15_block(block_j):
        for prefix in ("exp15_row_parcel", "exp15_area", "exp15_class"):
            st.session_state.pop(f"{prefix}_{block_j}", None)

    def _copy_exp15_block(src_block, dst_block):
        for prefix in ("exp15_row_parcel", "exp15_area", "exp15_class"):
            _copy_state_key(f"{prefix}_{src_block}", f"{prefix}_{dst_block}")

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

    # Başvuru tarihi ve otomatik aylık Yİ-ÜFE
    application_date = st.date_input(
        "BAŞVURU TARİHİ",
        value=date.today(),
        min_value=date(2011, 2, 1),
        key="experience_application_date",
        help="Yİ-ÜFE hesabında başvuru tarihinden bir önceki ay esas alınır.",
    )
    yiufe_series, yiufe_live, evds_key_present = get_yiufe_series()
    target_month = previous_month(application_date)
    target_index, target_source = get_yiufe_index(target_month, yiufe_series, yiufe_live)

    if target_index:
        st.caption(
            f"📈 Yİ-ÜFE hedef ayı: **{month_label(target_month)}** — "
            f"**{target_index:,.2f}** ({target_source})"
        )
    else:
        st.warning(
            f"{month_label(target_month)} Yİ-ÜFE verisi bulunamadı. "
            "Sözleşme tarihine göre otomatik sonuç hesaplanamayacak."
        )

    if application_date.year != 2026:
        st.warning(
            "Bu uygulamadaki belge grubu eşikleri ve güncel yapı maliyetleri 2026 tablosudur. "
            "Başvuru tarihi farklı bir yıl ise o yılın yeterlik tablosu ayrıca güncellenmelidir."
        )

    st.caption(
        "Sonuçlar üç şekilde gösterilir: %90 alt sınır, %90 uygulanmayan referans ve "
        "sözleşme tarihine göre Yİ-ÜFE + %90/%130 sınırlarıyla otomatik güncellenen tutar."
    )

    # ---------------------------------------------------------
    # SON 5 YIL
    # ---------------------------------------------------------
    if method.startswith("1"):
        st.subheader("Son 5 yılda bitirilen inşaatlar")

        total_90 = 0.0
        total_no90 = 0.0
        total_auto = 0.0
        auto_all_valid = True
        entered_projects = 0
        row_results = []
        project_results = []

        if "exp5_visible_rows" not in st.session_state:
            st.session_state.exp5_visible_rows = 1
        visible_rows = min(max(int(st.session_state.exp5_visible_rows), 1), 10)

        for i in range(1, visible_rows + 1):
            title_col, remove_col = st.columns([8.8, 0.7])
            with title_col:
                st.markdown(f"### {i}. İNŞAAT")
            with remove_col:
                if i > 1:
                    st.button("✕", key=f"remove_exp5_project_{i}", help=f"{i}. inşaatı kaldır", on_click=_remove_exp5_project, args=(i,))

            col_parcel, col_share, col_contract = st.columns([1.45, 0.65, 0.90])
            with col_parcel:
                ada_parsel = st.text_input(
                    "ADA PARSEL / BLOK BİLGİSİ",
                    placeholder="Örn: 123 / 45 veya 123 / 45 A Blok",
                    key=f"exp5_parcel_{i}",
                )
            with col_share:
                share = st.number_input(
                    "İNŞAAT HİSSESİ (%)", min_value=0.0, max_value=100.0,
                    value=100.0, step=0.01, format="%.2f", key=f"exp5_share_{i}",
                )
            with col_contract:
                default_contract = date(max(2011, min(application_date.year - 1, 2025)), 1, 1)
                contract_date = st.date_input(
                    "SÖZLEŞME TARİHİ",
                    value=default_contract,
                    min_value=date(2011, 2, 1),
                    max_value=application_date,
                    key=f"exp5_contract_date_{i}",
                )

            base_month = previous_month(contract_date)
            base_index, base_source = get_yiufe_index(base_month, yiufe_series, yiufe_live)
            if base_index:
                st.caption(
                    f"Sözleşme Yİ-ÜFE ayı: {month_label(base_month)} = {base_index:,.2f} ({base_source})"
                )
            else:
                st.warning(f"{month_label(base_month)} Yİ-ÜFE verisi bulunamadı.")

            block_count_key = f"exp5_block_count_{i}"
            if block_count_key not in st.session_state:
                st.session_state[block_count_key] = 1
            block_count = min(max(int(st.session_state[block_count_key]), 1), 10)

            gross_90 = 0.0
            gross_no90 = 0.0
            gross_auto = 0.0
            project_auto_valid = True
            project_has_area = False

            for j in range(1, block_count + 1):
                if j == 1:
                    st.markdown("**İNŞAAT BİLGİLERİ**")
                else:
                    btitle, bremove = st.columns([8.8, 0.7])
                    with btitle:
                        st.markdown(f"**EK BLOK / BÖLÜM {j - 1}**")
                    with bremove:
                        st.button("✕", key=f"remove_exp5_block_{i}_{j}", help="Bu bloğu/bölümü kaldır", on_click=_remove_exp5_block, args=(i, j))

                if j == 1:
                    row_ada_parsel = ada_parsel
                else:
                    row_ada_parsel = st.text_input(
                        "ADA PARSEL / BLOK BİLGİSİ", value=ada_parsel,
                        placeholder="Örn: 123 / 45 A Blok", key=f"exp5_row_parcel_{i}_{j}",
                    )

                col_area, col_class, col_current, col_contract_cost = st.columns([0.78, 1.35, 0.78, 0.90])
                with col_area:
                    area = st.number_input(
                        "İNŞAAT ALANI (m²)", min_value=0.0, step=0.01, value=0.0,
                        format="%.2f", key=f"exp5_area_{i}_{j}",
                    )
                with col_class:
                    bclass = st.selectbox(
                        "GÜNCEL İNŞAAT SINIFI", list(BUILDING_UNIT_COSTS.keys()),
                        format_func=lambda x: f"{x} — {BUILDING_CLASSES[x]}",
                        index=list(BUILDING_UNIT_COSTS.keys()).index("III-B"),
                        key=f"exp5_class_{i}_{j}",
                    )
                current_cost = BUILDING_UNIT_COSTS[bclass]
                with col_current:
                    st.markdown("**2026 m² MALİYETİ**")
                    st.markdown(
                        f"<div style='padding:.55rem .5rem;border:1px solid #d9dee8;border-radius:10px;"
                        f"background:#f7f9fc;font-weight:800;text-align:center;'>{fmt_tl(current_cost).replace(',00 ₺',' TL')}</div>",
                        unsafe_allow_html=True,
                    )

                auto_contract_cost, cost_period = historical_contract_cost(contract_date, bclass)
                with col_contract_cost:
                    contract_cost = synced_contract_cost_input(
                        f"exp5_contract_cost_{i}_{j}", auto_contract_cost,
                        f"{contract_date.isoformat()}|{bclass}|{auto_contract_cost}",
                    )
                if auto_contract_cost:
                    st.caption(f"Sözleşme m² maliyeti kaynağı/dönemi: **{cost_period}**. Gerekirse elle değiştirilebilir.")
                else:
                    st.warning(
                        f"{cost_period}. Bu blok için sözleşme tarihindeki m² maliyetini elle girin."
                    )

                if area > 0:
                    project_has_area = True
                    base_85 = area * current_cost * 0.85
                    block_90 = base_85 * 0.90
                    block_no90 = base_85
                    gross_90 += block_90
                    gross_no90 += block_no90

                    auto_calc = date_based_block_calculation(
                        area, current_cost, contract_cost, contract_date, application_date,
                        yiufe_series, yiufe_live,
                    )
                    if auto_calc:
                        block_auto = auto_calc["amount"]
                        gross_auto += block_auto
                        st.caption(
                            f"📌 {month_label(auto_calc['base_month'])} {auto_calc['base_index']:,.2f} → "
                            f"{month_label(auto_calc['target_month'])} {auto_calc['target_index']:,.2f} | "
                            f"Yİ-ÜFE: {auto_calc['yiufe_coeff']:.4f} | Alt: {auto_calc['lower_coeff']:.4f} | "
                            f"Üst: {auto_calc['upper_coeff']:.4f} | Uygulanan: {auto_calc['applied_coeff']:.4f} — "
                            f"**{auto_calc['reason']}**"
                        )
                    else:
                        block_auto = None
                        project_auto_valid = False

                    share_ratio = share / 100.0
                    row_results.append({
                        "row": f"{i}.{j}", "project_id": i,
                        "project_label": ada_parsel.strip() or f"{i}. İnşaat",
                        "ada_parsel": (
                            f"{row_ada_parsel.strip() or ada_parsel.strip() or f'{i}. İnşaat'} (%{share:g})"
                            f"<br/><font size='5'>Söz: {contract_date.strftime('%d.%m.%Y')}</font>"
                        ),
                        "area": area, "class": bclass, "unit_cost": current_cost,
                        "amount": block_90 * share_ratio,
                        "amount_90": block_90 * share_ratio,
                        "amount_no90": block_no90 * share_ratio,
                        "amount_auto": (block_auto * share_ratio if block_auto is not None else None),
                    })

                if j < block_count:
                    st.markdown("---")

            if block_count < 10:
                if st.button("＋ BLOK EKLE", key=f"add_exp5_block_{i}", use_container_width=False):
                    st.session_state[block_count_key] = block_count + 1
                    st.rerun()
            else:
                st.caption("Bu inşaat için en fazla 10 blok ekleyebilirsiniz.")

            construction_note = st.text_input(
                "NOT", placeholder="Bu inşaatla ilgili notunuzu yazabilirsiniz...", key=f"exp5_note_{i}",
            )

            if project_has_area:
                entered_projects += 1
                share_ratio = share / 100.0
                amount_90 = gross_90 * share_ratio
                amount_no90 = gross_no90 * share_ratio
                amount_auto = gross_auto * share_ratio if project_auto_valid else None
                total_90 += amount_90
                total_no90 += amount_no90
                if amount_auto is not None:
                    total_auto += amount_auto
                else:
                    auto_all_valid = False

                project_results.append({
                    "row": i, "ada_parsel": ada_parsel.strip() or f"{i}. İnşaat",
                    "share": share, "note": construction_note.strip(),
                    "contract_date": contract_date,
                    "amount": amount_90, "amount_90": amount_90,
                    "amount_no90": amount_no90, "amount_auto": amount_auto,
                    "block_count": block_count,
                })
                for pdf_row in row_results:
                    if pdf_row.get("project_id") == i:
                        pdf_row["project_total"] = amount_90
                        pdf_row["project_total_90"] = amount_90
                        pdf_row["project_total_no90"] = amount_no90
                        pdf_row["project_total_auto"] = amount_auto

                auto_text = fmt_tl(amount_auto) if amount_auto is not None else "HESAPLANAMADI"
                st.info(
                    f"**{i}. inşaat:** %90 = {fmt_tl(amount_90)} | %90 yok = {fmt_tl(amount_no90)} | "
                    f"**Sözleşme tarihine göre = {auto_text}**"
                )

            if i < visible_rows:
                st.divider()

        st.write("")
        if visible_rows < 10:
            if st.button("＋ İNŞAAT EKLE", key="add_exp5_row", use_container_width=True):
                st.session_state.exp5_visible_rows = visible_rows + 1
                st.rerun()
        else:
            st.caption("En fazla 10 inşaat ekleyebilirsiniz.")

        if entered_projects > 0:
            # %90
            normal_group_90 = work_experience_group(total_90)
            largest_90 = max(project_results, key=lambda x: x["amount_90"])
            limit_90 = largest_90["amount_90"] * 3
            final_90 = min(total_90, limit_90)
            group_90 = work_experience_group(final_90)
            cap_90 = total_90 > limit_90

            # %90 yok
            normal_group_no90 = work_experience_group(total_no90)
            largest_no90 = max(project_results, key=lambda x: x["amount_no90"])
            limit_no90 = largest_no90["amount_no90"] * 3
            final_no90 = min(total_no90, limit_no90)
            group_no90 = work_experience_group(final_no90)
            cap_no90 = total_no90 > limit_no90

            # Sözleşme tarihine göre otomatik
            if auto_all_valid and all(p.get("amount_auto") is not None for p in project_results):
                normal_group_auto = work_experience_group(total_auto)
                largest_auto = max(project_results, key=lambda x: x["amount_auto"])
                limit_auto = largest_auto["amount_auto"] * 3
                final_auto = min(total_auto, limit_auto)
                group_auto = work_experience_group(final_auto)
                cap_auto = total_auto > limit_auto
            else:
                normal_group_auto = None
                largest_auto = None
                limit_auto = None
                final_auto = None
                group_auto = None
                cap_auto = False

            st.markdown("### Hesaplama Sonuçları")
            c1, c2, c3 = st.columns(3)
            with c1:
                st.markdown(f"""
                <div class="result-card"><div><b>%90 ALT SINIR</b></div>
                <div class="result-number">{fmt_tl(final_90)}</div>
                <div style="font-size:1.65rem;font-weight:800;">{group_90} GRUBU</div></div>
                """, unsafe_allow_html=True)
                st.caption(f"Normal toplam: {fmt_tl(total_90)}" + (f" | 3 kat: {largest_90['ada_parsel']}" if cap_90 else " | 3 kat sınırı aşılmadı"))
            with c2:
                st.markdown(f"""
                <div class="joint-result"><div><b>%90 UYGULANMAZSA</b></div>
                <div class="result-number">{fmt_tl(final_no90)}</div>
                <div style="font-size:1.65rem;font-weight:800;">{group_no90} GRUBU</div></div>
                """, unsafe_allow_html=True)
                st.caption(f"Normal toplam: {fmt_tl(total_no90)}" + (f" | 3 kat: {largest_no90['ada_parsel']}" if cap_no90 else " | 3 kat sınırı aşılmadı"))
            with c3:
                if final_auto is not None:
                    st.markdown(f"""
                    <div style="padding:1.25rem;border-radius:20px;background:#fff7e8;border:1px solid #efd49d;text-align:center;margin:1rem 0;">
                    <div><b>SÖZLEŞME TARİHİNE GÖRE</b></div>
                    <div class="result-number">{fmt_tl(final_auto)}</div>
                    <div style="font-size:1.65rem;font-weight:800;">{group_auto} GRUBU</div></div>
                    """, unsafe_allow_html=True)
                    st.caption(f"Normal toplam: {fmt_tl(total_auto)}" + (f" | 3 kat: {largest_auto['ada_parsel']}" if cap_auto else " | 3 kat sınırı aşılmadı"))
                else:
                    st.error("SÖZLEŞME TARİHİNE GÖRE sonuç hesaplanamadı. Eksik tarihsel m² maliyeti veya Yİ-ÜFE verisini tamamlayın.")

            if group_auto:
                st.success(
                    f"📌 **Başvuruda kontrol edilecek otomatik sonuç: {group_auto} GRUBU — {fmt_tl(final_auto)}**"
                )

            pdf_notes = [
                {"ada_parsel": p["ada_parsel"], "note": p["note"]}
                for p in project_results if p.get("note", "").strip()
            ]
            pdf_bytes = create_experience_pdf(
                method_name="Son 5 yılda bitirilen inşaatların toplamı",
                rows=row_results,
                total_amount=final_90, result_group=group_90,
                normal_total=total_90, normal_group=normal_group_90,
                largest_row=largest_90, three_times_limit=limit_90, cap_applied=cap_90,
                notes=pdf_notes,
                total_amount_no90=final_no90, result_group_no90=group_no90,
                normal_total_no90=total_no90, normal_group_no90=normal_group_no90,
                largest_row_no90=largest_no90, three_times_limit_no90=limit_no90, cap_applied_no90=cap_no90,
                total_amount_auto=final_auto, result_group_auto=group_auto,
                normal_total_auto=total_auto if final_auto is not None else None,
                normal_group_auto=normal_group_auto, largest_row_auto=largest_auto,
                three_times_limit_auto=limit_auto, cap_applied_auto=cap_auto,
            )
            st.download_button(
                "📄 DÖKÜM AL", data=pdf_bytes,
                file_name=f"muteahhitlik_is_deneyim_dokumu_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
                mime="application/pdf", use_container_width=True, type="primary", key="download_exp5_pdf",
            )
        else:
            st.info("Hesaplama için en az bir inşaatın/blokun alanını girin.")

    # ---------------------------------------------------------
    # SON 15 YIL - TEK İNŞAAT
    # ---------------------------------------------------------
    else:
        st.subheader("Son 15 yıldaki tek inşaat")

        col_parcel, col_share, col_contract = st.columns([1.45, 0.65, 0.90])
        with col_parcel:
            ada_parsel = st.text_input("ADA PARSEL / BLOK BİLGİSİ", placeholder="Örn: 123 / 45", key="exp15_parcel")
        with col_share:
            share = st.number_input("İNŞAAT HİSSESİ (%)", min_value=0.0, max_value=100.0, value=100.0, step=0.01, format="%.2f", key="exp15_share")
        with col_contract:
            default_contract = date(max(2011, min(application_date.year - 1, 2025)), 1, 1)
            contract_date = st.date_input(
                "SÖZLEŞME TARİHİ", value=default_contract, min_value=date(2011, 2, 1),
                max_value=application_date, key="exp15_contract_date",
            )

        base_month = previous_month(contract_date)
        base_index, base_source = get_yiufe_index(base_month, yiufe_series, yiufe_live)
        if base_index:
            st.caption(f"Sözleşme Yİ-ÜFE ayı: {month_label(base_month)} = {base_index:,.2f} ({base_source})")

        if "exp15_block_count" not in st.session_state:
            st.session_state.exp15_block_count = 1
        block_count = min(max(int(st.session_state.exp15_block_count), 1), 10)
        gross_90 = gross_no90 = gross_auto = 0.0
        auto_valid = True
        single_rows = []

        for j in range(1, block_count + 1):
            if j == 1:
                st.markdown("**İNŞAAT BİLGİLERİ**")
            else:
                btitle, bremove = st.columns([8.8, 0.7])
                with btitle:
                    st.markdown(f"**EK BLOK / BÖLÜM {j - 1}**")
                with bremove:
                    st.button("✕", key=f"remove_exp15_block_{j}", help="Bu bloğu/bölümü kaldır", on_click=_remove_exp15_block, args=(j,))

            row_ada_parsel = ada_parsel if j == 1 else st.text_input(
                "ADA PARSEL / BLOK BİLGİSİ", value=ada_parsel, key=f"exp15_row_parcel_{j}",
            )
            col_area, col_class, col_current, col_contract_cost = st.columns([0.78, 1.35, 0.78, 0.90])
            with col_area:
                area = st.number_input("İNŞAAT ALANI (m²)", min_value=0.0, step=0.01, value=0.0, format="%.2f", key=f"exp15_area_{j}")
            with col_class:
                bclass = st.selectbox(
                    "GÜNCEL İNŞAAT SINIFI", list(BUILDING_UNIT_COSTS.keys()),
                    format_func=lambda x: f"{x} — {BUILDING_CLASSES[x]}",
                    index=list(BUILDING_UNIT_COSTS.keys()).index("III-B"), key=f"exp15_class_{j}",
                )
            current_cost = BUILDING_UNIT_COSTS[bclass]
            with col_current:
                st.markdown("**2026 m² MALİYETİ**")
                st.markdown(f"<div style='padding:.55rem .5rem;border:1px solid #d9dee8;border-radius:10px;background:#f7f9fc;font-weight:800;text-align:center;'>{fmt_tl(current_cost).replace(',00 ₺',' TL')}</div>", unsafe_allow_html=True)
            auto_contract_cost, cost_period = historical_contract_cost(contract_date, bclass)
            with col_contract_cost:
                contract_cost = synced_contract_cost_input(
                    f"exp15_contract_cost_{j}", auto_contract_cost,
                    f"{contract_date.isoformat()}|{bclass}|{auto_contract_cost}",
                )
            if auto_contract_cost:
                st.caption(f"Sözleşme m² maliyeti dönemi: **{cost_period}**. Gerekirse elle değiştirilebilir.")
            else:
                st.warning(f"{cost_period}. Sözleşme tarihindeki m² maliyetini elle girin.")

            if area > 0:
                base_85 = area * current_cost * 0.85
                b90, bno90 = base_85 * 0.90, base_85
                gross_90 += b90
                gross_no90 += bno90
                auto_calc = date_based_block_calculation(area, current_cost, contract_cost, contract_date, application_date, yiufe_series, yiufe_live)
                if auto_calc:
                    bauto = auto_calc["amount"]
                    gross_auto += bauto
                    st.caption(
                        f"📌 Yİ-ÜFE {auto_calc['yiufe_coeff']:.4f} | Alt {auto_calc['lower_coeff']:.4f} | "
                        f"Üst {auto_calc['upper_coeff']:.4f} | Uygulanan {auto_calc['applied_coeff']:.4f} — **{auto_calc['reason']}**"
                    )
                else:
                    bauto = None
                    auto_valid = False
                sr = share / 100.0
                single_rows.append({
                    "row": f"1.{j}", "project_id": 1, "project_label": ada_parsel.strip() or "1. İnşaat",
                    "ada_parsel": f"{row_ada_parsel.strip() or ada_parsel.strip() or '1. İnşaat'} (%{share:g})<br/><font size='5'>Söz: {contract_date.strftime('%d.%m.%Y')}</font>",
                    "area": area, "class": bclass, "unit_cost": current_cost,
                    "amount": b90 * sr * 2, "amount_90": b90 * sr * 2,
                    "amount_no90": bno90 * sr * 2,
                    "amount_auto": (bauto * sr * 2 if bauto is not None else None),
                })
            if j < block_count:
                st.markdown("---")

        if block_count < 10:
            if st.button("＋ BLOK EKLE", key="add_exp15_block", use_container_width=False):
                st.session_state.exp15_block_count = block_count + 1
                st.rerun()

        construction_note = st.text_input("NOT", placeholder="Bu inşaatla ilgili notunuzu yazabilirsiniz...", key="exp15_note")

        if gross_90 > 0:
            sr = share / 100.0
            total_90 = gross_90 * sr * 2
            total_no90 = gross_no90 * sr * 2
            total_auto = gross_auto * sr * 2 if auto_valid else None
            group_90 = work_experience_group(total_90)
            group_no90 = work_experience_group(total_no90)
            group_auto = work_experience_group(total_auto) if total_auto is not None else None
            for r in single_rows:
                r["project_total"] = total_90
                r["project_total_90"] = total_90
                r["project_total_no90"] = total_no90
                r["project_total_auto"] = total_auto

            st.markdown("### Hesaplama Sonuçları")
            c1, c2, c3 = st.columns(3)
            for col, title, amount, grp, bg in [
                (c1, "%90 ALT SINIR", total_90, group_90, "#eef8f1"),
                (c2, "%90 UYGULANMAZSA", total_no90, group_no90, "#eef4ff"),
                (c3, "SÖZLEŞME TARİHİNE GÖRE", total_auto, group_auto, "#fff7e8"),
            ]:
                with col:
                    if amount is not None:
                        st.markdown(f"<div style='padding:1.1rem;border-radius:20px;background:{bg};border:1px solid #d7d7d7;text-align:center;margin:1rem 0;'><div><b>{title}</b></div><div class='result-number'>{fmt_tl(amount)}</div><div style='font-size:1.6rem;font-weight:800;'>{grp} GRUBU</div></div>", unsafe_allow_html=True)
                    else:
                        st.error(f"{title}: Hesaplanamadı")

            pdf_notes = []
            if construction_note.strip():
                pdf_notes.append({"ada_parsel": ada_parsel.strip() or "1. İnşaat", "note": construction_note.strip()})
            pdf_bytes = create_experience_pdf(
                method_name="Son 15 yıldaki tek inşaatın 2 kat dikkate alınması",
                rows=single_rows,
                total_amount=total_90, result_group=group_90, normal_total=total_90, normal_group=group_90,
                notes=pdf_notes,
                total_amount_no90=total_no90, result_group_no90=group_no90, normal_total_no90=total_no90, normal_group_no90=group_no90,
                total_amount_auto=total_auto, result_group_auto=group_auto, normal_total_auto=total_auto, normal_group_auto=group_auto,
            )
            st.download_button(
                "📄 DÖKÜM AL", data=pdf_bytes,
                file_name=f"muteahhitlik_is_deneyim_dokumu_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
                mime="application/pdf", use_container_width=True, type="primary", key="download_exp15_pdf",
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
        "Sözleşme tarihine göre otomatik hesap; sözleşmeden önceki ay ve başvurudan önceki ay Yİ-ÜFE endekslerini, "
        "yapı maliyeti artışının %90 alt ve %130 üst sınırlarını birlikte değerlendirir. "
        "Resmî başvuruda ilgili idarenin değerlendirmesi esastır."
    )
