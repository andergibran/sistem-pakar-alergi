"""
Mesin inferensi identifikasi awal jenis alergi: Forward Chaining + Certainty Factor.

Basis pengetahuan (Excel):
  Tabel1_Alergi, Tabel2_Indikator, Tabel3_Matriks (pembanding), Aturan_CF (basis aturan JIKA-MAKA + CF pakar)

Alur:
  1. Fakta   : indikator yang dipilih pengguna (beserta CF pengguna, 0..1).
  2. FC      : aturan "JIKA indikator MAKA jenis alergi" terpenuhi bila indikatornya ada di fakta.
  3. CF      : CF aturan = CF pakar x CF pengguna; CF aturan-aturan yang terpenuhi untuk satu alergi
               digabung berurutan: CF1 + CF2 x (1 - CF1).
  4. Hasil   : jenis alergi diurutkan menurut CF gabungan.
Modul ini murni Python/pandas, tanpa Streamlit.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

BOBOT_MIN = 0.1
RED_FLAG_KEYWORDS = ("anaphylaxis", "sesak napas", "mengi")
CLOSE_MARGIN = 0.05        # selisih CF dua teratas yang dianggap berdekatan
CF_USER_DEFAULT = 0.8      # keyakinan pengguna bila hanya mencentang ("Yakin")


@dataclass
class KnowledgeBase:
    allergies: pd.DataFrame   # kode, nama, nama_csv, tipe, prevalensi, keparahan, penanganan
    indicators: pd.DataFrame  # kode, nama, asal_en, kategori, sumber, status
    rules: pd.DataFrame       # aturan, p, alergi, g, indikator, cf_awal, cf_pakar, cf, rujukan, validasi
    matrix: pd.DataFrame      # pembanding: index = kode alergi, kolom = kode indikator

    @property
    def n_rules(self) -> int:
        return len(self.rules)

    @property
    def pakar_terisi(self) -> int:
        return int(self.rules["cf_pakar"].notna().sum())

    @property
    def tervalidasi(self) -> int:
        return int(self.rules["validasi"].astype(str).str.strip().str.lower().eq("tervalidasi").sum())

    @property
    def sepenuhnya_divalidasi(self) -> bool:
        return self.n_rules > 0 and self.pakar_terisi == self.n_rules and self.tervalidasi == self.n_rules


@dataclass
class Result:
    kode: str
    nama: str
    tipe: str
    prevalensi: str
    keparahan: str
    penanganan: str
    cf: float
    n_fired: int
    n_total: int
    fired: list[dict] = field(default_factory=list)        # aturan yang terpenuhi
    langkah: list[dict] = field(default_factory=list)      # langkah penggabungan CF
    tidak_cocok: list[str] = field(default_factory=list)   # dipilih pengguna, tidak ada aturannya utk alergi ini
    belum_dipilih: list[str] = field(default_factory=list)  # ada aturannya utk alergi ini, belum dipilih


def load_kb(path: str | Path) -> KnowledgeBase:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(
            f"File basis pengetahuan tidak ditemukan: {path}. Letakkan file Excel di folder yang sama dengan app.py.")

    t1 = pd.read_excel(path, sheet_name="Tabel1_Alergi").dropna(subset=["Kode"]).rename(columns={
        "Kode": "kode", "Jenis alergi (ID)": "nama", "Allergy (CSV)": "nama_csv", "Tipe (CSV)": "tipe",
        "Prevalensi": "prevalensi", "Potensi keparahan": "keparahan", "Penanganan (CSV)": "penanganan"})

    t2 = pd.read_excel(path, sheet_name="Tabel2_Indikator", usecols="A:F").dropna(subset=["Kode"]).rename(columns={
        "Kode": "kode", "Indikator (ID)": "nama", "Asal di CSV (EN)": "asal_en",
        "Kategori": "kategori", "Sumber": "sumber", "Status": "status"}).reset_index(drop=True)

    # --- matriks (hanya pembanding konsistensi)
    raw = pd.read_excel(path, sheet_name="Tabel3_Matriks", header=None)
    head = raw.index[raw[0].astype(str).str.strip().eq("Kode")][0]
    kode_g = [str(x) for x in raw.iloc[head, 2:] if str(x).startswith("G")]
    body = raw.iloc[head + 1:, :2 + len(kode_g)]
    body = body[body[0].astype(str).str.startswith("P")]
    matrix = body.set_index(0).iloc[:, 1:]
    matrix.columns = kode_g
    matrix = matrix.apply(pd.to_numeric, errors="coerce").fillna(0).astype(int)
    matrix.index = matrix.index.astype(str)

    # --- aturan dan CF
    ar = pd.read_excel(path, sheet_name="Aturan_CF").dropna(subset=["Kode aturan"]).rename(columns={
        "Kode aturan": "aturan", "Kode alergi": "p", "Jenis alergi (THEN)": "alergi",
        "Kode indikator": "g", "Indikator (IF)": "indikator", "CF awal (rumus)": "cf_awal",
        "CF pakar (isi)": "cf_pakar", "CF dipakai": "cf", "Rujukan (dari Tabel2)": "rujukan",
        "Status validasi pakar": "validasi"}).reset_index(drop=True)
    if "rujukan" not in ar.columns:
        ar["rujukan"] = ""
    if "validasi" not in ar.columns:
        ar["validasi"] = "Belum divalidasi"

    # Cadangan bila nilai rumus Excel tidak tersimpan: MAX(min ; 1 - jumlah alergi pemilik indikator / N)
    n_alergi = max(len(t1), 1)
    frek = ar.groupby("g")["p"].transform("nunique")
    cadangan = (1 - frek / n_alergi).clip(lower=BOBOT_MIN)
    ar["cf_awal"] = pd.to_numeric(ar["cf_awal"], errors="coerce").fillna(cadangan)
    ar["cf_pakar"] = pd.to_numeric(ar["cf_pakar"], errors="coerce").clip(0, 1)
    ar["cf"] = ar["cf_pakar"].where(ar["cf_pakar"].notna(), ar["cf_awal"]).astype(float).clip(0, 1)

    return KnowledgeBase(allergies=t1.reset_index(drop=True), indicators=t2, rules=ar, matrix=matrix)


def cek_konsistensi(kb: KnowledgeBase) -> list[str]:
    """Bandingkan pasangan (alergi, indikator) di Aturan_CF dengan Tabel3_Matriks. Kosong = konsisten."""
    dari_aturan = set(zip(kb.rules["p"], kb.rules["g"]))
    dari_matriks = {(p, g) for p in kb.matrix.index for g in kb.matrix.columns if kb.matrix.loc[p, g] == 1}
    msg = [f"Ada di matriks tapi tidak ada aturannya: {p}, {g}" for p, g in sorted(dari_matriks - dari_aturan)]
    msg += [f"Ada aturannya tapi tidak ada di matriks: {p}, {g}" for p, g in sorted(dari_aturan - dari_matriks)]
    return msg


# --------------------------------------------------------------------------
def combine_cf(cf_old: float, cf_new: float) -> float:
    """CFgabungan = CF1 + CF2 x (1 - CF1) untuk dua CF positif."""
    return cf_old + cf_new * (1.0 - cf_old)


def confidence_label(cf: float) -> str:
    if cf < 0.30:
        return "Rendah"
    if cf < 0.60:
        return "Sedang"
    if cf < 0.80:
        return "Cukup tinggi"
    return "Tinggi"


def to_facts(selected) -> dict[str, float]:
    """Terima daftar kode (dianggap CF pengguna = default) atau dict kode -> CF pengguna."""
    if isinstance(selected, dict):
        return {g: float(v) for g, v in selected.items() if v and v > 0}
    return {g: CF_USER_DEFAULT for g in selected}


def infer(kb: KnowledgeBase, selected) -> list[Result]:
    """Forward chaining: cocokkan fakta ke aturan, hitung CF, gabungkan per jenis alergi."""
    facts = to_facts(selected)
    if not facts:
        return []
    nama_ind = kb.indicators.set_index("kode")["nama"]

    fired = kb.rules[kb.rules["g"].isin(facts.keys())].copy()
    fired["cf_user"] = fired["g"].map(facts)
    fired["cf_aturan"] = fired["cf"] * fired["cf_user"]

    out: list[Result] = []
    for p, grp in fired.groupby("p"):
        info = kb.allergies[kb.allergies["kode"] == p].iloc[0]
        grp = grp.sort_values("cf_aturan", ascending=False)
        semua_g = set(kb.rules.loc[kb.rules["p"] == p, "g"])

        cf, langkah = 0.0, []
        for _, r in grp.iterrows():
            sebelum = cf
            cf = combine_cf(cf, float(r["cf_aturan"]))
            langkah.append({"aturan": r["aturan"], "indikator": r["indikator"],
                            "cf_aturan": float(r["cf_aturan"]), "sebelum": sebelum, "sesudah": cf})

        out.append(Result(
            kode=p, nama=info["nama"], tipe=info["tipe"], prevalensi=info["prevalensi"],
            keparahan=info["keparahan"], penanganan=info["penanganan"], cf=cf,
            n_fired=len(grp), n_total=len(semua_g),
            fired=grp[["aturan", "g", "indikator", "cf", "cf_user", "cf_aturan"]].to_dict("records"),
            langkah=langkah,
            tidak_cocok=[nama_ind.get(g, g) for g in facts if g not in semua_g],
            belum_dipilih=[nama_ind.get(g, g) for g in sorted(semua_g) if g not in facts],
        ))

    out.sort(key=lambda r: (r.cf, r.n_fired / max(r.n_total, 1)), reverse=True)
    return out


def red_flags(kb: KnowledgeBase, selected) -> list[str]:
    facts = to_facts(selected)
    ind = kb.indicators
    return [r["nama"] for _, r in ind[ind["kode"].isin(facts.keys())].iterrows()
            if any(k in str(r["nama"]).lower() for k in RED_FLAG_KEYWORDS)]


def top_close(results: list[Result]) -> bool:
    return len(results) >= 2 and (results[0].cf - results[1].cf) < CLOSE_MARGIN


def results_to_frame(results: list[Result]) -> pd.DataFrame:
    return pd.DataFrame([{
        "Peringkat": i + 1, "Kode": r.kode, "Jenis alergi": r.nama, "Tipe": r.tipe,
        "Potensi keparahan": r.keparahan, "CF (0-1)": round(r.cf, 4), "Persentase": f"{r.cf * 100:.1f}%",
        "Aturan terpenuhi": f"{r.n_fired}/{r.n_total}",
    } for i, r in enumerate(results)])


def group_indicators(kb: KnowledgeBase) -> dict[str, pd.DataFrame]:
    return {k: kb.indicators[kb.indicators["kategori"] == k] for k in kb.indicators["kategori"].drop_duplicates()}
