"""
Sistem Pakar Identifikasi Awal Jenis Alergi
Metode: pencocokan gejala langsung (tanpa basis aturan) | Antarmuka: Streamlit

Jalankan:  streamlit run app.py
"""
from pathlib import Path

from html import escape

import streamlit as st

import engine as E
import tampilan as T

KB_PATH = Path(__file__).parent / "basis_pengetahuan_sistem_pakar_alergi.xlsx"

st.set_page_config(page_title="Identifikasi Awal Alergi", page_icon="🩺", layout="wide")
st.markdown(T.css_block(), unsafe_allow_html=True)


@st.cache_resource(show_spinner=False)
def get_kb(path: str, mtime: float) -> E.KnowledgeBase:
    return E.load_kb(path)


try:
    kb = get_kb(str(KB_PATH), KB_PATH.stat().st_mtime if KB_PATH.exists() else 0.0)
except Exception as exc:
    st.error(f"Basis pengetahuan tidak bisa dibaca. {exc}")
    st.stop()

if "hasil" not in st.session_state:
    st.session_state.hasil = None

GEJALA_ORDER = ["Kulit", "Pernapasan", "Mata", "Pencernaan", "Sistemik"]


def kat_label(kat: str) -> str:
    return kat.replace("Pemicu: ", "").capitalize()


def status_chips() -> str:
        n_usulan = 0
    return (T.chip(f"{len(kb.allergies)} jenis alergi", "teal") + T.chip(f"{len(kb.indicators)} gejala dan pemicu", "teal")
            + (T.chip(f"{n_usulan} indikator usulan belum diverifikasi pakar", "amber") if n_usulan else ""))


# ---------------------------------------------------------------- sidebar
with st.sidebar:
    st.markdown('<div class="brand">Identifikasi Awal Alergi<small>Sistem pakar pencocokan gejala</small></div>',
                unsafe_allow_html=True)
    st.write("")
    page = st.radio("Menu", ["Konsultasi", "Basis pengetahuan", "Metode dan rujukan"], label_visibility="collapsed")
    st.write("")
    st.markdown(T.alert("warn", "Bukan pengganti dokter",
                        "Hasil hanya skrining awal. Diagnosis pasti memerlukan pemeriksaan dokter."), unsafe_allow_html=True)


# ---------------------------------------------------------------- konsultasi
def render_form() -> None:
    st.markdown(T.hero(
        "Cari tahu kemungkinan jenis alergimu",
        "Centang pemicu dan gejala yang kamu alami. Sistem mencocokkannya dengan ciri tiap jenis alergi "
        "lalu menampilkan yang paling mirip.", status_chips()), unsafe_allow_html=True)
    st.markdown(T.alert("info", "Cara menjawab",
                        "Centang hanya yang benar-benar kamu alami. Tidak perlu mengisi semuanya. "
                        "Makin lengkap yang kamu centang, makin tajam hasilnya."), unsafe_allow_html=True)

    groups = E.group_indicators(kb)
    pemicu = [k for k in groups if k.startswith("Pemicu")]
    waktu = [k for k in groups if k.startswith("Waktu")]
    gejala = [k for k in GEJALA_ORDER if k in groups]

    def box(kat: str) -> None:
        df = groups[kat]
        with st.container(border=True):
            st.markdown(f'<div class="grp">{kat_label(kat)}<small>{len(df)} pilihan</small></div>', unsafe_allow_html=True)
            cols = st.columns(2)
            for i, (_, row) in enumerate(df.iterrows()):
                with cols[i % 2]:
                    st.checkbox(row["nama"], key=f"g_{row['kode']}")

    with st.form("konsultasi", border=False):
        st.markdown(T.step(1, "Apa yang terjadi sebelum gejala muncul?", "Centang pemicu yang kamu curigai."), unsafe_allow_html=True)
        for k in pemicu:
            box(k)
        st.markdown(T.step(2, "Kapan gejala muncul setelah terpapar?", "Seberapa cepat gejala terasa."), unsafe_allow_html=True)
        for k in waktu:
            box(k)
        st.markdown(T.step(3, "Gejala apa yang kamu rasakan?", "Centang semua yang sesuai."), unsafe_allow_html=True)
        for k in gejala:
            box(k)
        submitted = st.form_submit_button("Hitung kemungkinan", type="primary")

    if submitted:
        selected = [r["kode"] for _, r in kb.indicators.iterrows() if st.session_state.get(f"g_{r['kode']}")]
        if not selected:
            st.warning("Belum ada yang dicentang. Pilih minimal satu pemicu atau gejala.")
            return
        st.session_state.hasil = {"selected": selected, "results": E.infer(kb, selected)}
        st.rerun()


def reset_konsultasi() -> None:
    """Mulai dari awal: semua centang dikosongkan."""
    for _, r in kb.indicators.iterrows():
        st.session_state.pop(f"g_{r['kode']}", None)
    st.session_state.hasil = None


def ubah_pilihan() -> None:
    """Kembali ke formulir dengan centang sebelumnya tetap terisi, supaya bisa dikoreksi."""
    h = st.session_state.hasil
    pilihan = set(h["selected"]) if h else set()
    for _, r in kb.indicators.iterrows():
        st.session_state[f"g_{r['kode']}"] = r["kode"] in pilihan
    st.session_state.hasil = None


def tombol_rujuk_ulang(prefix: str) -> None:
    c1, c2, _ = st.columns([1, 1, 2])
    c1.button("Ubah pilihan", on_click=ubah_pilihan, type="primary", key=f"{prefix}_ubah")
    c2.button("Mulai dari awal", on_click=reset_konsultasi, key=f"{prefix}_reset")


def render_result() -> None:
    h = st.session_state.hasil
    results: list[E.Result] = h["results"]
    names = kb.indicators.set_index("kode")["nama"]

    st.markdown(T.hero("Hasil identifikasi awal",
                       "Hasil dihitung dari pemicu dan gejala yang kamu centang.",
                       status_chips()), unsafe_allow_html=True)

    if not results:
        st.markdown(T.alert("warn", "Pilihanmu tidak valid menurut basis pengetahuan",
                            "Tidak ada jenis alergi yang memiliki satu pun dari pemicu dan gejala yang kamu centang. "
                            "Kemungkinan ada salah centang, atau keluhanmu bukan alergi yang ada di data. "
                            "Periksa kembali pilihanmu, atau konsultasikan ke dokter."), unsafe_allow_html=True)
        tombol_rujuk_ulang("kosong")
        return

    top = results[0]
    seri = [r for r in results if abs(r.skor - top.skor) < 1e-9]
    kurang_cocok = top.tidak_cocok
    skor_rendah = top.skor < 0.40

    if kurang_cocok:
        daftar = ", ".join(kurang_cocok)
        st.markdown(T.alert(
            "warn", "Ada pilihan yang tidak sesuai dengan ciri alergi teratas",
            f"Menurut basis pengetahuan, {escape(daftar)} bukan ciri khas {escape(top.nama)}. "
            "Bisa jadi salah centang, atau gejalanya memang tidak khas untuk jenis alergi ini. "
            "Hasil di bawah hanya yang paling mendekati. Periksa kembali lalu ubah pilihanmu bila perlu.",
            body_is_html=True), unsafe_allow_html=True)
    elif skor_rendah:
        st.markdown(T.alert(
            "warn", "Kecocokan masih rendah",
            "Pilihanmu baru sedikit yang sesuai dengan ciri jenis alergi mana pun. "
            "Tambahkan gejala lain yang kamu alami, atau periksa kembali pilihanmu."), unsafe_allow_html=True)

    st.markdown(T.result_hero(top, "Jenis alergi yang paling mendekati" if (kurang_cocok or skor_rendah)
                              else "Kemungkinan jenis alergimu"), unsafe_allow_html=True)
    if len(seri) > 1:
        st.markdown(T.alert(
            "info", "Ada jenis alergi lain yang sama cocok",
            "Dengan pilihanmu, data tidak bisa membedakan: " + ", ".join(escape(r.nama) for r in seri)
            + ". Tambahkan gejala yang lebih khas agar hasilnya lebih jelas.",
            body_is_html=True), unsafe_allow_html=True)
    st.markdown(f"**Penanganan umum (dari data sumber):** {top.penanganan}")
    st.markdown("**Cocok dengan pilihanmu:** " + ", ".join(top.cocok))

    st.subheader("Yang kamu pilih")
    st.markdown(f'<div class="rankbox">{T.answers_summary([(names[g], "Dipilih") for g in h["selected"]])}</div>',
                unsafe_allow_html=True)

    st.markdown(T.alert("info", "Penting",
                        "Sistem ini alat skrining awal, bukan diagnosis. Jenis alergi yang pasti ditentukan dokter "
                        "lewat riwayat, pemeriksaan, dan tes alergi."), unsafe_allow_html=True)
    tombol_rujuk_ulang("hasil")


# ---------------------------------------------------------------- basis pengetahuan
def render_kb() -> None:
    st.markdown(T.hero("Basis pengetahuan",
                       "Jenis alergi, indikator, dan matriks yang dipakai untuk pencocokan. Data dibaca langsung dari file Excel.",
                       status_chips()), unsafe_allow_html=True)
    t1, t2, t3 = st.tabs(["Jenis alergi", "Indikator", "Matriks X"])

    with t1:
        df = kb.allergies[["kode", "nama", "tipe", "prevalensi", "keparahan", "penanganan"]].copy()
        df["tipe"] = df["tipe"].map(lambda x: T.TIPE_ID.get(x, x))
        df["prevalensi"] = df["prevalensi"].map(lambda x: T.PREVALENSI_ID.get(x, x))
        df["keparahan"] = df["keparahan"].map(lambda x: T.KEPARAHAN_ID.get(str(x).lower(), x))
        df.columns = ["Kode", "Jenis alergi", "Tipe", "Prevalensi", "Potensi keparahan", "Penanganan (sumber data)"]
        st.dataframe(df, hide_index=True)

    with t2:
        kat = st.selectbox("Kategori", ["Semua"] + list(kb.indicators["kategori"].drop_duplicates()))
        df = kb.indicators if kat == "Semua" else kb.indicators[kb.indicators["kategori"] == kat]
        df = df[["kode", "nama", "kategori", "jumlah_alergi", "bobot", "status"]].copy()
        df["bobot"] = df["bobot"].round(2)
        df.columns = ["Kode", "Indikator", "Kategori", "Dimiliki (jenis alergi)", "Bobot", "Status"]
        st.dataframe(df, hide_index=True)
        st.caption("Indikator berstatus \"Usulan\" belum diverifikasi pakar. Bobot lebih tinggi berarti indikator lebih khas.")

    with t3:
        mat = kb.matrix.replace({1: "✓", 0: ""})
        mat.index.name = None
        mat.insert(0, "Jenis alergi", kb.allergies.set_index("kode")["nama"])
        st.dataframe(mat)
        st.caption("Baris: jenis alergi. Kolom: kode indikator (lihat tab Indikator). ✓ berarti indikator berlaku.")


# ---------------------------------------------------------------- metode
REFERENSI_KLINIS = [
    ("Santos AF, et al. EAACI guidelines on the diagnosis of IgE-mediated food allergy. Allergy. 2023;78:3057-3076.", "10.1111/all.15902"),
    ("Khan DA, et al. Drug allergy: a 2022 practice parameter update. J Allergy Clin Immunol. 2022;150(6):1333-1393.", "10.1016/j.jaci.2022.08.028"),
    ("Golden DBK, et al. Stinging insect hypersensitivity: a practice parameter update 2016. Ann Allergy Asthma Immunol. 2017;118(1):28-54.", "10.1016/j.anai.2016.10.031"),
    ("Dykewicz MS, et al. Rhinitis 2020: a practice parameter update. J Allergy Clin Immunol. 2020;146(4):721-767.", "10.1016/j.jaci.2020.07.007"),
    ("Fonacier L, et al. Contact dermatitis: a practice parameter update 2015. J Allergy Clin Immunol Pract. 2015;3(3 Suppl):S1-S39.", "10.1016/j.jaip.2015.02.009"),
    ("Cardona V, et al. World Allergy Organization anaphylaxis guidance 2020. World Allergy Organ J. 2020;13:100472.", "10.1016/j.waojou.2020.100472"),
    ("World Allergy Organization Anaphylaxis Committee. Revised definition and criteria for anaphylaxis. World Allergy Organ J. 2019;12(10):100066.", "10.1016/j.waojou.2019.100066"),
    ("Pawankar R, et al. (eds). WAO White Book on Allergy: Update 2013. World Allergy Organization.", None),
]
REFERENSI_METODE = [
    ("Sistem Pakar Diagnosa Penyakit Alergi dan Dermatitis Atopi Menggunakan Forward Chaining Berbasis Web. Elsains Jurnal Elektro.", "10.30996/elsains.v5i1.8539"),
    ("Fale MI, Abdulsalam YG. Dr. Flynxz: a first aid Mamdani-Sugeno-type fuzzy expert system for differential symptoms-based diagnosis. J King Saud Univ Comput Inf Sci. 2022;34(4):1138-1149.", "10.1016/j.jksuci.2020.04.016"),
    ("Sekti BA, Tandianto D, Sutjahyono A. Percepatan diagnosis gejala penyakit batuk dengan metoda Forward Chaining dan Certainty Factor. JTIK. 2024;10(2):401-412.", "10.37012/jtik.v10i2.2252"),
    ("Implementasi Forward Chaining dan Certainty Factor pada aplikasi sistem pakar diagnosa penyakit kulit wajah. Algoritma. 2024;22(1).", "10.33364/algoritma/v.22-1.2096"),
    ("Irfan M, et al. Diagnosis of asthma disease and the levels using Forward Chaining and Certainty Factor. Jurnal RESTI. 2022.", None),
]


def render_metode() -> None:
    st.markdown(T.hero("Metode dan rujukan",
                       "Cara sistem mencocokkan gejala, keterbatasannya, dan rujukan ilmiah yang mendasarinya.",
                       status_chips()), unsafe_allow_html=True)

    st.subheader("Cara kerja")
    st.markdown(
        "1. **Masukan.** Pengguna mencentang pemicu, waktu muncul, dan gejala yang dialami.\n"
        "2. **Pencocokan.** Pilihan dibandingkan dengan ciri tiap jenis alergi pada matriks X (Excel). "
        "Tidak ada aturan JIKA-MAKA terpisah, matriks itu sendiri yang menjadi basis pengetahuan.\n"
        "3. **Skor.** Tiap alergi diberi skor kecocokan 0 sampai 1 (rumus di bawah).\n"
        "4. **Keluaran.** Jenis alergi dengan skor tertinggi ditampilkan beserta penanganan umum dan gejala yang cocok.")
    st.markdown("Bobot tiap indikator, makin jarang dimiliki alergi makin besar (lantai 0,1):")
    st.latex(r"w_i = \max\left(0{,}1;\ 1 - \frac{n_i}{N}\right)")
    st.markdown("Skor kecocokan alergi *k* terhadap pilihan *S* (weighted Dice), dengan *A* adalah ciri alergi *k*:")
    st.latex(r"skor_k = \frac{2\sum_{i \in S \cap A_k} w_i}{\sum_{i \in S} w_i + \sum_{i \in A_k} w_i}")
    st.markdown("$n_i$ adalah jumlah jenis alergi yang memiliki indikator *i*, dan $N$ jumlah seluruh jenis alergi.")

    st.subheader("Keterbatasan")
    st.markdown(
        "- Basis pengetahuan berasal dari 20 jenis alergi dengan sedikit gejala tiap jenis, sehingga pemetaannya sederhana.\n"
        "- Indikator pemicu dan waktu muncul gejala adalah usulan penyusun dan perlu diverifikasi pakar.\n"
        "- Bobot dihitung dari seberapa sering indikator muncul di data, bukan dari ukuran kekhasan klinis.\n"
        "- Dua alergi bisa bernilai sama persis bila ciri yang dipilih dimiliki keduanya (misalnya tungau debu dan bulu hewan "
        "untuk bersin, hidung meler, mata gatal). Itu keterbatasan data, bukan galat program.\n"
        "- Skor bukan probabilitas. Sistem tidak menggantikan anamnesis, pemeriksaan fisik, dan tes alergi oleh dokter.")

    st.subheader("Rujukan klinis")
    st.markdown("".join(T.reference(t, d) for t, d in REFERENSI_KLINIS), unsafe_allow_html=True)
    st.subheader("Rujukan metode sistem pakar")
    st.markdown("".join(T.reference(t, d) for t, d in REFERENSI_METODE), unsafe_allow_html=True)
    st.caption("Baca teks lengkap setiap rujukan sebelum mengutipnya di laporan.")


if page == "Konsultasi":
    if st.session_state.hasil is None:
        render_form()
    else:
        try:
            render_result()
        except Exception as exc:  # jaring pengaman: jangan tampilkan layar merah ke pengguna
            st.markdown(T.alert("warn", "Hasil tidak dapat ditampilkan",
                                "Terjadi masalah saat menyusun hasil. Coba ubah pilihanmu atau mulai dari awal."),
                        unsafe_allow_html=True)
            with st.expander("Detail teknis"):
                st.code(f"{type(exc).__name__}: {exc}")
            tombol_rujuk_ulang("galat")
elif page == "Basis pengetahuan":
    render_kb()
else:
    render_metode()
