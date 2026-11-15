"""
Mesin pencocokan gejala untuk identifikasi awal jenis alergi.

Tanpa basis aturan: setiap jenis alergi punya daftar indikator (matriks X di Excel).
Pengguna memilih indikator yang dialami, lalu sistem menghitung kecocokan tiap alergi.

Skor kecocokan = weighted Dice:
    2 * bobot(indikator terpilih yang dimiliki alergi) / (bobot(terpilih) + bobot(semua indikator alergi))
Bobot indikator = max(0,1 ; 1 - jumlah alergi pemilik indikator / jumlah alergi)
sehingga indikator yang jarang (lebih khas) lebih berpengaruh.
Modul ini murni Python/pandas, tanpa Streamlit.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

BOBOT_MIN = 0.1
RED_FLAG_KEYWORDS = ("anaphylaxis", "sesak napas", "mengi")
CLOSE_MARGIN = 0.03   # selisih skor dua teratas yang dianggap berdekatan


@dataclass
class KnowledgeBase:
    allergies: pd.DataFrame    # kode, nama, nama_csv, tipe, prevalensi, keparahan, penanganan
    indicators: pd.DataFrame   # kode, nama, asal_en, kategori, sumber, status, jumlah_alergi, bobot
    matrix: pd.DataFrame       # index = kode alergi, kolom = kode indikator, nilai 0/1


@dataclass
class Result:
    kode: str
    nama: str
    tipe: str
    prevalensi: str
    keparahan: str
    penanganan: str
    skor: float
    cocok: list[str] = field(default_factory=list)       # nama indikator terpilih yang dimiliki alergi
    tidak_cocok: list[str] = field(default_factory=list)  # indikator terpilih yang tidak dimiliki alergi
    belum_dipilih: list[str] = field(default_factory=list)  # indikator alergi ini yang tidak dipilih
    n_indikator: int = 0


def load_kb(path: str | Path) -> KnowledgeBase:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(
            f"File basis pengetahuan tidak ditemukan: {path}. "
            "Letakkan file Excel di folder yang sama dengan app.py.")

    t1 = pd.read_excel(path, sheet_name="Tabel1_Alergi").dropna(subset=["Kode"]).rename(columns={
        "Kode": "kode", "Jenis alergi (ID)": "nama", "Allergy (CSV)": "nama_csv", "Tipe (CSV)": "tipe",
        "Prevalensi": "prevalensi", "Potensi keparahan": "keparahan", "Penanganan (CSV)": "penanganan"})

    t2 = pd.read_excel(path, sheet_name="Tabel2_Indikator", usecols="A:F").dropna(subset=["Kode"]).rename(columns={
        "Kode": "kode", "Indikator (ID)": "nama", "Asal di CSV (EN)": "asal_en",
        "Kategori": "kategori", "Sumber": "sumber", "Status": "status"})

    raw = pd.read_excel(path, sheet_name="Tabel3_Matriks", header=None)
    head = raw.index[raw[0].astype(str).str.strip().eq("Kode")][0]      # baris "Kode, Jenis alergi, G001, ..."
    kode_g = [str(x) for x in raw.iloc[head, 2:] if str(x).startswith("G")]
    body = raw.iloc[head + 1:, :2 + len(kode_g)]
    body = body[body[0].astype(str).str.startswith("P")]
    matrix = body.set_index(0).iloc[:, 1:]
    matrix.columns = kode_g
    matrix = matrix.apply(pd.to_numeric, errors="coerce").fillna(0).astype(int)
    matrix.index = matrix.index.astype(str)

    n = max(len(matrix), 1)
    t2 = t2.reset_index(drop=True)
    t2["jumlah_alergi"] = t2["kode"].map(matrix.sum(axis=0)).fillna(0).astype(int)
    t2["bobot"] = (1 - t2["jumlah_alergi"] / n).clip(lower=BOBOT_MIN)

    return KnowledgeBase(allergies=t1.reset_index(drop=True), indicators=t2, matrix=matrix)


def confidence_label(skor: float) -> str:
    if skor < 0.25:
        return "Rendah"
    if skor < 0.50:
        return "Sedang"
    if skor < 0.75:
        return "Cukup tinggi"
    return "Tinggi"


def infer(kb: KnowledgeBase, selected: list[str]) -> list[Result]:
    """Hitung kecocokan semua jenis alergi terhadap indikator terpilih. Hanya alergi dengan >= 1 kecocokan yang dikembalikan."""
    sel = [g for g in selected if g in kb.matrix.columns]
    if not sel:
        return []
    w = kb.indicators.set_index("kode")["bobot"]
    nama = kb.indicators.set_index("kode")["nama"]
    w_sel = float(w[sel].sum())
    out: list[Result] = []
    for _, a in kb.allergies.iterrows():
        row = kb.matrix.loc[a["kode"]]
        miliki = [g for g in kb.matrix.columns if row[g] == 1]
        cocok = [g for g in sel if row[g] == 1]
        if not cocok:
            continue
        skor = 2 * float(w[cocok].sum()) / (w_sel + float(w[miliki].sum()))
        out.append(Result(
            kode=a["kode"], nama=a["nama"], tipe=a["tipe"], prevalensi=a["prevalensi"],
            keparahan=a["keparahan"], penanganan=a["penanganan"], skor=skor,
            cocok=[nama[g] for g in cocok],
            tidak_cocok=[nama[g] for g in sel if row[g] != 1],
            belum_dipilih=[nama[g] for g in miliki if g not in sel],
            n_indikator=len(miliki)))
    out.sort(key=lambda r: (r.skor, len(r.cocok)), reverse=True)
    return out


def red_flags(kb: KnowledgeBase, selected: list[str]) -> list[str]:
    ind = kb.indicators
    return [r["nama"] for _, r in ind[ind["kode"].isin(selected)].iterrows()
            if any(k in str(r["nama"]).lower() for k in RED_FLAG_KEYWORDS)]


def top_close(results: list[Result]) -> bool:
    return len(results) >= 2 and (results[0].skor - results[1].skor) < CLOSE_MARGIN


def results_to_frame(results: list[Result]) -> pd.DataFrame:
    return pd.DataFrame([{
        "Peringkat": i + 1, "Kode": r.kode, "Jenis alergi": r.nama, "Tipe": r.tipe,
        "Potensi keparahan": r.keparahan, "Skor kecocokan": round(r.skor, 4),
        "Persentase": f"{r.skor * 100:.1f}%",
        "Gejala cocok": f"{len(r.cocok)}/{r.n_indikator}",
    } for i, r in enumerate(results)])


def group_indicators(kb: KnowledgeBase) -> dict[str, pd.DataFrame]:
    return {k: kb.indicators[kb.indicators["kategori"] == k] for k in kb.indicators["kategori"].drop_duplicates()}
