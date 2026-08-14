import streamlit as st

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
    return f"{code} — {BUILDING_CLASSES[code]} — {BUILDING_UNIT_COSTS[code]:,.0f} TL/m²".replace(",", ".")

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
        '''
        <a class="click-card" href="?page=m2">
            <div class="title">1. Mevcut sınıfım ile kaç m² inşaat yapabilirim?</div>
            <div class="desc">Yetki belge grubunuzu ve yapı sınıfını seçin.</div>
        </a>
        ''',
        unsafe_allow_html=True
    )

    st.markdown(
        '''
        <a class="click-card" href="?page=joint">
            <div class="title">2. Hangi sınıfları birleştirsem hangi sınıfı elde ederiz?</div>
            <div class="desc">Büyük ve küçük belge sınıfı olan ortakları seçin.</div>
        </a>
        ''',
        unsafe_allow_html=True
    )

    st.markdown(
        '''
        <a class="click-card" href="?page=experience">
            <div class="title">3. Bitirdiğim inşaatlar ile hangi sınıfı alabilirim?</div>
            <div class="desc">Son 5 yıldaki işlerinizin toplamını veya son 15 yıldaki tek işinizi kullanın.</div>
        </a>
        ''',
        unsafe_allow_html=True
    )

    st.divider()
    st.caption("Veriler: Çevre, Şehircilik ve İklim Değişikliği Bakanlığı 2026 Yapım Müteahhitliği Yeterlik Tablosu.")
    st.caption("Bilgilendirme amaçlıdır. Resmî başvuru/ruhsat işlemlerinde güncel YAMBİS ve ilgili idare kayıtları esas alınmalıdır.")

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
        "İnşaat alanını m² olarak girip güncel yapı sınıfını seçmeniz yeterlidir."
    )

    if method.startswith("1"):
        st.subheader("Son 5 yılda bitirilen inşaatlar")

        total_experience = 0.0
        entered_rows = 0
        row_results = []

        for i in range(1, 11):
            st.markdown(f"**{i}. İNŞAAT**")
            col_parcel, col_area, col_class = st.columns([1.1, 1, 2])

            with col_parcel:
                ada_parsel = st.text_input(
                    "ADA PARSEL",
                    placeholder="Örn: 123 / 45",
                    key=f"exp5_parcel_{i}",
                )

            with col_area:
                area = st.number_input(
                    "İNŞAAT ALANI (m²)",
                    min_value=0.0,
                    step=1.0,
                    value=0.0,
                    key=f"exp5_area_{i}",
                )

            with col_class:
                bclass = st.selectbox(
                    "GÜNCEL İNŞAAT SINIFI",
                    list(BUILDING_UNIT_COSTS.keys()),
                    format_func=building_class_label,
                    index=list(BUILDING_UNIT_COSTS.keys()).index("III-B"),
                    key=f"exp5_class_{i}",
                )

            if area > 0:
                row_amount = area * BUILDING_UNIT_COSTS[bclass] * 0.85 * 0.90
                total_experience += row_amount
                entered_rows += 1

                row_results.append({
                    "row": i,
                    "ada_parsel": ada_parsel.strip() or f"{i}. İnşaat",
                    "area": area,
                    "class": bclass,
                    "amount": row_amount,
                })

                st.caption(
                    f"{fmt_m2(area)} × "
                    f"{fmt_tl(BUILDING_UNIT_COSTS[bclass]).replace(',00 ₺',' ₺')}/m² × "
                    f"0,85 × 0,90 = **{fmt_tl(row_amount)}**"
                )

            if i < 10:
                st.divider()

        if entered_rows > 0:
            # Normal toplamdan çıkan grup
            normal_group = work_experience_group(total_experience)

            # 3 kat kuralı:
            # En yüksek iş deneyim tutarına sahip tek satırın 3 katı,
            # 5 yıllık toplam iş deneyimi için üst sınırdır.
            largest_row = max(row_results, key=lambda x: x["amount"])
            three_times_limit = largest_row["amount"] * 3
            capped_experience = min(total_experience, three_times_limit)
            capped_group = work_experience_group(capped_experience)
            cap_applied = total_experience > three_times_limit

            st.markdown(f"""
            <div class="result-card">
                <div><b>NORMAL TOPLAM İŞ DENEYİM TUTARI</b></div>
                <div class="result-number">{fmt_tl(total_experience)}</div>
                <div>Normal toplama göre: <b>{normal_group} GRUBU</b></div>
            </div>
            """, unsafe_allow_html=True)

            st.info(
                f"**En büyük iş deneyimi:** {largest_row['ada_parsel']} — "
                f"{fmt_tl(largest_row['amount'])}\n\n"
                f"**3 katı üst sınırı:** {fmt_tl(three_times_limit)}"
            )

            if cap_applied:
                st.markdown(f"""
                <div class="joint-result">
                    <div><b>3 KATI KURALI UYGULANDI</b></div>
                    <div style="margin-top:.5rem;">Dikkate alınabilecek iş deneyim tutarı</div>
                    <div class="result-number">{fmt_tl(capped_experience)}</div>
                    <div style="font-size:1.8rem;font-weight:800;margin-top:.5rem;">{capped_group} GRUBU</div>
                </div>
                """, unsafe_allow_html=True)

                if normal_group != capped_group:
                    st.warning(
                        f"⚠️ **Normalde {normal_group} sınıfı alırsın; ancak en büyük inşaat deneyiminin "
                        f"3 katını geçememe kuralından dolayı {capped_group} sınıfı alabilirsin.**"
                    )
                else:
                    st.warning(
                        f"⚠️ Toplam iş deneyimi 3 kat sınırını aşıyor; dikkate alınan tutar "
                        f"{fmt_tl(capped_experience)}. Buna rağmen belge sınıfı **{capped_group}** olarak değişmiyor."
                    )
            else:
                st.success(
                    f"✅ Toplam iş deneyiminiz, en büyük iş deneyiminin 3 katı sınırını aşmıyor. "
                    f"Asgari iş deneyim tutarına göre **{normal_group} grubu** sonucu oluşuyor."
                )

            st.caption(
                "5 yıllık toplam hesabında dikkate alınabilecek tutar, girilen işlerin toplamı ile "
                "en yüksek tek iş deneyim tutarının 3 katından düşük olanıdır."
            )
        else:
            st.info("Hesaplama için en az bir inşaatın alanını girin.")

    else:
        st.subheader("Son 15 yıldaki tek inşaat")

        col_area, col_class = st.columns([1, 2])

        with col_area:
            area = st.number_input(
                "İNŞAAT ALANI (m²)",
                min_value=0.0,
                step=1.0,
                value=0.0,
                key="exp15_area",
            )

        with col_class:
            bclass = st.selectbox(
                "GÜNCEL İNŞAAT SINIFI",
                list(BUILDING_UNIT_COSTS.keys()),
                format_func=building_class_label,
                index=list(BUILDING_UNIT_COSTS.keys()).index("III-B"),
                key="exp15_class",
            )

        if area > 0:
            base_amount = area * BUILDING_UNIT_COSTS[bclass] * 0.85 * 0.90
            total_experience = base_amount * 2
            result_group = work_experience_group(total_experience)

            st.markdown(
                f"**Hesap:** {fmt_m2(area)} × "
                f"{fmt_tl(BUILDING_UNIT_COSTS[bclass]).replace(',00 ₺',' ₺')}/m² × "
                f"0,85 × 0,90 × 2"
            )

            st.markdown(f"""
            <div class="result-card">
                <div><b>İŞ DENEYİM TUTARI</b></div>
                <div class="result-number">{fmt_tl(total_experience)}</div>
                <div>Asgari iş deneyim tutarına göre</div>
                <div style="font-size:1.8rem;font-weight:800;margin-top:.5rem;">{result_group} GRUBU</div>
            </div>
            """, unsafe_allow_html=True)

            if result_group != "H":
                st.success(
                    f"İki kat dikkate alınan iş deneyim tutarı, iş deneyimi yönünden "
                    f"**{result_group} grubu** için 2026 asgari tutarı karşılıyor."
                )
            else:
                st.info(
                    "Hesaplanan tutar G1 grubunun 2026 asgari iş deneyim tutarının altında kaldığı için "
                    "iş deneyimi yönünden sonuç **H grubu** olarak gösterildi."
                )
        else:
            st.info("Hesaplama için inşaat alanını girin.")

    with st.expander("2026 asgari iş deneyim tutarlarını göster"):
        table_rows = [
            {"Belge Grubu": group, "Asgari İş Deneyim Tutarı": fmt_tl(amount)}
            for group, amount in WORK_EXPERIENCE_MIN.items()
        ]
        table_rows.append({"Belge Grubu": "H", "Asgari İş Deneyim Tutarı": "Asgari iş deneyimi aranmaz"})
        st.dataframe(table_rows, use_container_width=True, hide_index=True)

    st.caption(
        "Sonuç yalnızca asgari iş deneyim tutarı kriterine göre hesaplanır. "
        "Üst gruplarda ekonomik, mali, teknik personel ve diğer yeterlik şartları ayrıca aranabilir."
    )
