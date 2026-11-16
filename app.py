"""
Sistem Pakar Identifikasi Awal Jenis Alergi
Metode: Forward Chaining + Certainty Factor | Antarmuka: Streamlit

Jalankan:  streamlit run app.py
"""
from pathlib import Path

from html import escape

import pandas as pd
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
    return T.chip(f"{len(kb.allergies)} jenis alergi", "teal") + T.chip(f"{len(kb.indicators)} gejala dan pemicu", "teal")


# ---------------------------------------------------------------- sidebar
with st.sidebar:
    st.markdown('<div class="brand">Identifikasi Awal Alergi<small>Sistem pakar Forward Chaining dan Certainty Factor</small></div>',
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
        "lalu menghitung jenis alergi yang paling mungkin.", status_chips()), unsafe_allow_html=True)
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
        if len(selected) < E.MIN_PILIHAN:
            st.warning(f"Pilih minimal {E.MIN_PILIHAN} pemicu atau gejala yang kamu alami.")
            return
        st.session_state.hasil = {"selected": selected, "results": E.infer(kb, selected), "flags": E.red_flags(kb, selected)}
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
                       "Hasil dihitung dari pemicu dan gejala yang kamu centang. Buka rincian untuk melihat aturan yang dipakai.",
                       status_chips()), unsafe_allow_html=True)

    if h.get("flags"):
        st.markdown(T.alert(
            "danger", "Tanda bahaya terdeteksi",
            "Kamu memilih " + ", ".join(h["flags"]).lower() + ". Gejala seperti ini bisa menjadi tanda reaksi alergi berat "
            "(anafilaksis). Segera ke IGD terdekat atau hubungi layanan darurat setempat, jangan menunggu hasil aplikasi ini."),
            unsafe_allow_html=True)

    n_pilih = len(h["selected"])
    if not results or not E.hasil_valid(results, n_pilih):
        cocok = results[0].n_fired if results else 0
        st.markdown(T.alert("warn", "Tidak ada jenis alergi yang cocok",
                            f"Pilihanmu tidak konsisten dengan ciri jenis alergi mana pun di basis pengetahuan "
                            f"(paling banyak {cocok} dari {n_pilih} pilihan yang cocok pada satu jenis alergi). "
                            "Sistem tidak menampilkan hasil. Periksa kembali pilihanmu, atau konsultasikan ke dokter."),
                    unsafe_allow_html=True)
        tombol_rujuk_ulang("kosong")
        return

    top = results[0]
    st.markdown(T.result_hero(top, "Kemungkinan terkuat dari pilihanmu", E.confidence_label(top.cf)), unsafe_allow_html=True)

    if E.top_close(results):
        st.markdown(T.alert("warn", "Hasil teratas nilainya berdekatan",
                            f"{escape(results[0].nama)} dan {escape(results[1].nama)} hampir setara. Gejala saja belum cukup "
                            "membedakannya. Tambahkan pemicu atau gejala yang lebih khas, dan konsultasikan ke dokter.",
                            body_is_html=True), unsafe_allow_html=True)
    if top.n_fired == 1:
        st.markdown(T.alert("info", "Bukti masih sedikit",
                            "Hasil teratas baru didukung satu aturan. Tambahkan gejala dan pemicu lain agar hasil lebih tajam."),
                    unsafe_allow_html=True)
    if top.tidak_cocok:
        st.markdown(T.alert("warn", "Ada pilihan yang tidak sesuai dengan alergi teratas",
                            f"{escape(', '.join(top.tidak_cocok))} tidak punya aturan untuk {escape(top.nama)}. "
                            "Bisa jadi salah centang, atau gejalanya memang tidak khas untuk jenis alergi ini.",
                            body_is_html=True), unsafe_allow_html=True)

    left, right = st.columns([3, 2], gap="large")
    with left:
        st.subheader("Peringkat kemungkinan")
        st.markdown(T.rank_rows(results, 5), unsafe_allow_html=True)
        st.caption("Persentase adalah tingkat keyakinan sistem (Certainty Factor), bukan peluang medis. "
                   "Nilainya cenderung naik bila banyak aturan terpenuhi.")
    with right:
        st.subheader("Yang kamu pilih")
        st.markdown(f'<div class="rankbox">{T.answers_summary([(names[g], "Dipilih") for g in h["selected"]])}</div>',
                    unsafe_allow_html=True)

    st.subheader("Rincian dan penjelasan")
    for i, r in enumerate(results[:3]):
        with st.expander(f"{r.nama}: {r.cf * 100:.1f}%", expanded=(i == 0)):
            st.markdown(T.meta_chips(r), unsafe_allow_html=True)
            st.markdown(f"**Penanganan umum (dari data sumber):** {r.penanganan}")
            st.markdown("**Aturan yang terpenuhi oleh pilihanmu**")
            df = pd.DataFrame([{"Aturan": f["aturan"], "Jika (indikator)": f["indikator"],
                                "CF pakar": f"{f['cf']:.2f}", "Keyakinanmu": f"{f['cf_user']:.1f}",
                                "CF aturan": f"{f['cf_aturan']:.3f}"} for f in r.fired]).set_index("Aturan")
            st.table(df)
            st.markdown("**Cara nilainya digabung** (dari CF aturan terbesar):")
            for l in r.langkah:
                st.markdown(f"- {l['aturan']}: {l['sebelum']:.3f} + {l['cf_aturan']:.3f} × (1 − {l['sebelum']:.3f}) = **{l['sesudah']:.3f}**")
            if r.belum_dipilih:
                st.markdown("**Ciri lain alergi ini yang belum kamu pilih:** " + ", ".join(r.belum_dipilih))

    st.download_button("Unduh hasil (CSV)", E.results_to_frame(results).to_csv(index=False).encode("utf-8-sig"),
                       file_name="hasil_identifikasi_alergi.csv", mime="text/csv")

    if not kb.sepenuhnya_divalidasi:
        st.markdown(T.alert("warn", "Catatan prototipe",
                            "Nilai CF pakar belum diisi sehingga sistem memakai bobot awal dari data sumber. "
                            "Hasil ini belum divalidasi pakar dan tidak boleh dipakai untuk keputusan medis."), unsafe_allow_html=True)
    st.markdown(T.alert("info", "Penting",
                        "Sistem ini alat skrining awal, bukan diagnosis. Jenis alergi yang pasti ditentukan dokter "
                        "lewat riwayat, pemeriksaan, dan tes alergi."), unsafe_allow_html=True)
    tombol_rujuk_ulang("hasil")


# ---------------------------------------------------------------- basis pengetahuan
def render_kb() -> None:
    st.markdown(T.hero("Basis pengetahuan",
                       "Jenis alergi, indikator, matriks, dan aturan beserta CF yang dipakai mesin inferensi. Data dibaca langsung dari file Excel.",
                       status_chips()), unsafe_allow_html=True)
    t1, t2, t3, t4 = st.tabs(["Jenis alergi", "Indikator", "Matriks X", "Aturan dan CF"])

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
        df = df[["kode", "nama", "kategori", "sumber", "status"]].copy()
        df.columns = ["Kode", "Indikator", "Kategori", "Sumber", "Status"]
        st.dataframe(df, hide_index=True)
        st.caption("Indikator berstatus \"Usulan\" belum diverifikasi pakar.")

    with t3:
        mat = kb.matrix.replace({1: "✓", 0: ""})
        mat.index.name = None
        mat.insert(0, "Jenis alergi", kb.allergies.set_index("kode")["nama"])
        st.dataframe(mat)
        st.caption("Baris: jenis alergi. Kolom: kode indikator (lihat tab Indikator). ✓ berarti ada aturan untuk pasangan itu.")

    with t4:
        selisih = E.cek_konsistensi(kb)
        if selisih:
            st.warning("Aturan_CF dan Tabel3_Matriks tidak sama persis. Periksa: " + "; ".join(selisih[:5]))
        pilih = st.selectbox("Jenis alergi", ["Semua"] + list(kb.allergies["nama"]))
        df = kb.rules if pilih == "Semua" else kb.rules[kb.rules["alergi"] == pilih]
        df = df[["aturan", "alergi", "indikator", "cf_awal", "cf_pakar", "cf", "validasi"]].copy()
        df.columns = ["Aturan", "Maka (alergi)", "Jika (indikator)", "CF awal", "CF pakar", "CF dipakai", "Status validasi"]
        st.dataframe(df, hide_index=True)


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
                       "Cara sistem bernalar, status validasinya, keterbatasannya, dan rujukan ilmiahnya.",
                       status_chips()), unsafe_allow_html=True)

    st.subheader("Status validasi pakar")
    c1, c2, c3 = st.columns(3)
    c1.metric("Jumlah aturan", kb.n_rules)
    c2.metric("CF pakar terisi", f"{kb.pakar_terisi} dari {kb.n_rules}")
    c3.metric("Aturan tervalidasi", f"{kb.tervalidasi} dari {kb.n_rules}")
    if not kb.sepenuhnya_divalidasi:
        st.markdown(T.alert("warn", "Belum sepenuhnya divalidasi",
                            "Isi kolom \"CF pakar (isi)\" dan \"Status validasi pakar\" di sheet Aturan_CF bersama pakar, "
                            "lalu jalankan ulang aplikasi."), unsafe_allow_html=True)

    st.subheader("Cara kerja")
    st.markdown(
        "1. **Fakta masuk.** Pemicu dan gejala yang dicentang menjadi fakta (working memory). "
        f"Setiap centang dianggap keyakinan {E.CF_USER_DEFAULT:.1f} (\"Yakin\").\n"
        "2. **Forward Chaining.** Sistem memeriksa semua aturan *JIKA indikator MAKA jenis alergi*. "
        "Aturan terpenuhi bila indikatornya ada di fakta.\n"
        "3. **Certainty Factor.** Tiap aturan yang terpenuhi diberi CF, lalu digabung per jenis alergi.\n"
        "4. **Validasi pilihan.** Hasil hanya ditampilkan bila pilihan cukup konsisten: minimal "
        f"{E.MIN_PILIHAN} pilihan dan sedikitnya {E.KONSISTENSI_MIN:.0%} pilihan cocok dengan jenis alergi teratas. "
        "Pilihan sembarang yang tidak sesuai ciri alergi mana pun tidak menghasilkan jawaban.\n"
        "5. **Keluaran.** Jenis alergi diurutkan menurut CF gabungan, disertai aturan yang dipakai dan peringatan tanda bahaya.")
    st.latex(r"CF_{aturan} = CF_{pakar} \times CF_{pengguna}")
    st.latex(r"CF_{gabungan} = CF_1 + CF_2 \times (1 - CF_1)")
    st.markdown("CF pakar diisi pakar di sheet Aturan_CF. Bila kosong, dipakai CF awal yang dihitung dari seberapa jarang "
                "indikator muncul di seluruh jenis alergi:")
    st.latex(r"CF_{awal} = \max\left(0{,}1;\ 1 - \frac{n_i}{N}\right)")
    st.markdown("$n_i$ adalah jumlah jenis alergi yang memiliki indikator *i*, dan $N$ jumlah seluruh jenis alergi.")

    st.subheader("Keterbatasan")
    st.markdown(
        "- Basis pengetahuan berasal dari 20 jenis alergi dengan sedikit gejala tiap jenis, sehingga pemetaannya sederhana.\n"
        "- Indikator pemicu dan waktu muncul gejala adalah usulan penyusun dan perlu diverifikasi pakar.\n"
        "- Sebelum CF pakar diisi, bobot hanya mencerminkan kelangkaan indikator di data, bukan kekhasan klinis.\n"
        "- Dua alergi bisa bernilai sama persis bila ciri yang dipilih dimiliki keduanya (misalnya tungau debu dan bulu hewan "
        "untuk bersin, hidung meler, mata gatal). Itu keterbatasan data, bukan galat program.\n"
        "- CF gabungan cenderung tinggi bila banyak aturan terpenuhi. Nilainya bukan probabilitas.\n"
        "- Sistem tidak menggantikan anamnesis, pemeriksaan fisik, dan tes alergi oleh dokter.")

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
