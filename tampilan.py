"""
Tampilan (CSS + potongan HTML) untuk aplikasi Streamlit.
Semua fungsi mengembalikan string; teks dinamis selalu di-escape.
"""
from __future__ import annotations

from html import escape

# --------------------------------------------------------------------------
# Terjemahan label dari data sumber
# --------------------------------------------------------------------------
TIPE_ID = {"food": "Makanan", "environmental": "Lingkungan", "drug": "Obat",
           "skin": "Kontak kulit", "insect": "Serangga"}
KEPARAHAN_ID = {"mild": "Ringan", "moderate": "Sedang", "severe": "Berat"}
PREVALENSI_ID = {"common": "Umum", "uncommon": "Jarang"}

# --------------------------------------------------------------------------
# CSS
# --------------------------------------------------------------------------
CSS = """
@import url('https://fonts.googleapis.com/css2?family=Figtree:wght@400;500;600;700&family=Newsreader:opsz,wght@6..72,500;6..72,600&display=swap');

:root{
  --ink:#10303A; --muted:#546E7A; --paper:#F3F8F7; --surface:#FFFFFF;
  --teal:#0E8A86; --teal-dark:#0A6B68; --teal-soft:#DDF0EE; --line:#D3E2E0;
  --amber:#8A5A00; --amber-bg:#FFF3D6; --amber-line:#F0D28A;
  --coral:#B3263A; --coral-bg:#FDEAEC; --coral-line:#F1B5BD;
  --green:#1F6F4A; --green-bg:#E3F4EA;
}
html, body, .stApp{ background:var(--paper); color:var(--ink); font-family:'Figtree','Segoe UI',system-ui,sans-serif; }
.stApp p, .stApp li, .stApp label, .stApp button, .stApp input, .stApp textarea{ font-family:'Figtree','Segoe UI',system-ui,sans-serif; }
span[data-testid="stIconMaterial"], .material-symbols-rounded{ font-family:'Material Symbols Rounded' !important; }
#MainMenu, footer{ visibility:hidden; }
header[data-testid="stHeader"]{ background:var(--paper); height:3rem; }
.block-container{ max-width:1100px; padding-top:4.2rem; padding-bottom:4rem; }

h1,h2,h3{ font-family:'Newsreader',Georgia,serif; color:var(--ink); letter-spacing:-0.01em; }
h2{ font-size:1.55rem; margin-top:1.6rem; }
h3{ font-size:1.2rem; }

/* sidebar */
section[data-testid="stSidebar"]{ background:var(--surface); border-right:1px solid var(--line); }
.brand{ font-family:'Newsreader',Georgia,serif; font-size:1.35rem; font-weight:600; color:var(--ink); line-height:1.2; }
.brand small{ display:block; font-family:'Figtree',sans-serif; font-size:.8rem; font-weight:500; color:var(--muted); margin-top:.25rem; }

/* hero */
.hero{ position:relative; overflow:hidden; background:var(--surface); border:1px solid var(--line);
  border-radius:16px; padding:1.9rem 2rem 1.7rem; margin-bottom:1.4rem; box-shadow:0 1px 0 rgba(16,48,58,.04), 0 12px 30px -18px rgba(16,48,58,.25); }
.hero h1{ font-size:2.15rem; margin:0 0 .5rem; max-width:34ch; line-height:1.15; }
.hero p{ color:var(--muted); max-width:62ch; margin:0 0 1rem; font-size:1.02rem; line-height:1.55; }
.hero .ecg{ position:absolute; right:-6px; top:14px; width:34%; max-width:380px; opacity:.35; pointer-events:none; z-index:0; }
.hero h1, .hero p, .hero .chips{ position:relative; z-index:1; }
@media (max-width:760px){ .hero{ padding:1.3rem 1.2rem; } .hero h1{ font-size:1.55rem; } .hero .ecg{ display:none; } }

/* chip */
.chip{ display:inline-block; padding:.18rem .7rem; border-radius:999px; font-size:.8rem; font-weight:600;
  border:1px solid var(--line); background:var(--paper); color:var(--ink); margin:0 .35rem .35rem 0; }
.chip.teal{ background:var(--teal-soft); border-color:#B7DEDA; color:var(--teal-dark); }
.chip.amber{ background:var(--amber-bg); border-color:var(--amber-line); color:var(--amber); }
.chip.coral{ background:var(--coral-bg); border-color:var(--coral-line); color:var(--coral); }
.chip.green{ background:var(--green-bg); border-color:#B5DEC6; color:var(--green); }

/* alert */
.alert{ border-radius:10px; padding:.95rem 1.15rem; margin:.4rem 0 1.1rem; border:1px solid; line-height:1.5; }
.alert b.t{ display:block; font-size:1.02rem; margin-bottom:.2rem; }
.alert.danger{ background:var(--coral-bg); border-color:var(--coral-line); color:#6E1420; }
.alert.warn{ background:var(--amber-bg); border-color:var(--amber-line); color:#5C3C00; }
.alert.info{ background:var(--teal-soft); border-color:#B7DEDA; color:#0B4A48; }

/* kartu langkah */
.step{ display:flex; gap:.9rem; align-items:flex-start; margin:1.5rem 0 .6rem; }
.step .no{ flex:0 0 auto; width:2rem; height:2rem; border-radius:8px; background:var(--teal); color:#fff;
  font-weight:700; display:flex; align-items:center; justify-content:center; }
.step .tx b{ display:block; font-family:'Newsreader',Georgia,serif; font-size:1.25rem; color:var(--ink); }
.step .tx span{ color:var(--muted); font-size:.93rem; }

/* kotak kelompok gejala */
div[data-testid="stVerticalBlockBorderWrapper"]{ background:var(--surface); border-radius:12px; }
.grp{ font-weight:700; color:var(--ink); font-size:1rem; margin:0 0 .4rem; }
.grp small{ font-weight:500; color:var(--muted); margin-left:.4rem; }
div[data-testid="stCheckbox"] label{ padding:.1rem 0; align-items:flex-start; }
div[data-testid="stCheckbox"] label p{ white-space:normal !important; overflow:visible !important; text-overflow:clip !important; line-height:1.35; }

/* input */
div[data-baseweb="select"] > div{ border-radius:8px; border-color:var(--line); background:var(--surface); }
.stSelectbox label p{ font-size:.93rem; color:var(--ink); }

/* tombol */
.stButton > button, div[data-testid="stFormSubmitButton"] > button{
  border-radius:10px; font-weight:600; border:1px solid var(--line); padding:.55rem 1.3rem; }
.stButton > button[kind="primary"], div[data-testid="stFormSubmitButton"] > button[kind="primary"], .stButton > button[kind="primaryFormSubmit"]{
  background:var(--teal); border-color:var(--teal); color:#fff; }
.stButton > button[kind="primary"]:hover, div[data-testid="stFormSubmitButton"] > button[kind="primary"]:hover{
  background:var(--teal-dark); border-color:var(--teal-dark); color:#fff; }
button:focus-visible{ outline:3px solid #7CC9C5 !important; outline-offset:2px; }

/* hasil utama */
.result-hero{ background:var(--surface); border:1px solid var(--line); border-left:6px solid var(--teal);
  border-radius:14px; padding:1.4rem 1.6rem; margin:.6rem 0 1.2rem; }
.result-hero .kicker{ color:var(--muted); font-size:.92rem; margin-bottom:.15rem; }
.result-hero .name{ font-family:'Newsreader',Georgia,serif; font-size:2rem; line-height:1.15; color:var(--ink); }
.result-hero .meta{ margin-top:.8rem; }

/* angka hasil dan peringkat */
.result-hero .row{ display:flex; justify-content:space-between; align-items:flex-end; gap:1rem; flex-wrap:wrap; }
.result-hero .big{ font-family:'Newsreader',Georgia,serif; font-size:2.8rem; line-height:1; color:var(--teal-dark); text-align:right; }
.result-hero .bigcap{ color:var(--muted); font-size:.85rem; text-align:right; }
.rank{ display:grid; grid-template-columns:minmax(0,1.5fr) minmax(0,2fr) 64px; gap:1rem; align-items:center;
  padding:.75rem 0; border-bottom:1px solid var(--line); }
.rank:last-child{ border-bottom:0; }
.rank .nm{ font-weight:600; color:var(--ink); }
.rank .nm .d{ display:block; font-weight:400; color:var(--muted); font-size:.82rem; }
.rank .bar{ height:10px; background:var(--teal-soft); border-radius:6px; overflow:hidden; }
.rank .bar .f{ display:block; height:100%; background:var(--teal); border-radius:6px; }
.rank.lead .bar .f{ background:var(--teal-dark); }
.rank .pc{ text-align:right; font-weight:700; }
@media (max-width:640px){ .rank{ grid-template-columns:minmax(0,1fr) 56px; } .rank .bar{ grid-column:1 / -1; order:3; } }

/* ringkasan pilihan */
.rankbox{ background:var(--surface); border:1px solid var(--line); border-radius:12px; padding:.4rem 1.2rem; }
.ans{ display:flex; justify-content:space-between; gap:1rem; padding:.45rem 0; border-bottom:1px dashed var(--line); font-size:.93rem; }
.ans:last-child{ border-bottom:0; }
.ans em{ font-style:normal; color:var(--teal-dark); font-weight:600; white-space:nowrap; }

/* rujukan */
.ref{ padding:.7rem 0; border-bottom:1px solid var(--line); font-size:.93rem; line-height:1.5; }
.ref a{ color:var(--teal-dark); text-decoration:none; border-bottom:1px solid #9AD0CC; }
.ref a:hover{ border-bottom-color:var(--teal-dark); }

@media (prefers-reduced-motion: reduce){ *{ transition:none !important; animation:none !important; } }
"""

ECG_SVG = (
    '<svg class="ecg" viewBox="0 0 520 80" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">'
    '<path d="M0 44 H70 L84 44 L96 14 L110 70 L124 44 H190 L202 44 L212 26 L222 44 H300 L312 44 L324 8 L338 72 L352 44 H430 L442 44 L452 30 L462 44 H520" '
    'stroke="#0E8A86" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/></svg>'
)


def css_block() -> str:
    return f"<style>{CSS}</style>"


# --------------------------------------------------------------------------
# Potongan HTML
# --------------------------------------------------------------------------
def chip(text: str, kind: str = "") -> str:
    return f'<span class="chip {kind}">{escape(str(text))}</span>'


def hero(title: str, subtitle: str, chips_html: str = "") -> str:
    return (
        f'<div class="hero">{ECG_SVG}'
        f'<h1>{escape(title)}</h1><p>{escape(subtitle)}</p>'
        f'<div class="chips">{chips_html}</div></div>'
    )


def alert(kind: str, title: str, body: str, body_is_html: bool = False) -> str:
    body_out = body if body_is_html else escape(body)
    return f'<div class="alert {kind}"><b class="t">{escape(title)}</b>{body_out}</div>'


def step(no: int, title: str, hint: str) -> str:
    return (f'<div class="step"><div class="no">{no}</div>'
            f'<div class="tx"><b>{escape(title)}</b><span>{escape(hint)}</span></div></div>')


def severity_kind(keparahan: str) -> str:
    return {"severe": "coral", "moderate": "amber", "mild": "green"}.get(str(keparahan).lower(), "")


def meta_chips(r) -> str:
    return (
        chip(f"Tipe: {TIPE_ID.get(r.tipe, r.tipe)}", "teal")
        + chip(f"Potensi keparahan: {KEPARAHAN_ID.get(str(r.keparahan).lower(), r.keparahan)}", severity_kind(r.keparahan))
        + chip(f"Prevalensi: {PREVALENSI_ID.get(str(r.prevalensi).lower(), r.prevalensi)}")
        + chip(f"Aturan terpenuhi: {r.n_fired} dari {r.n_total}")
    )


def result_hero(r, label: str = "Kemungkinan jenis alergimu", conf: str = "") -> str:
    return (
        '<div class="result-hero"><div class="row"><div>'
        f'<div class="kicker">{escape(label)}</div>'
        f'<div class="name">{escape(r.nama)}</div></div>'
        f'<div><div class="big">{r.cf * 100:.0f}%</div>'
        f'<div class="bigcap">Tingkat keyakinan: {escape(conf)}</div></div></div>'
        f'<div class="meta">{meta_chips(r)}</div></div>'
    )


def rank_rows(results, top_n: int = 5) -> str:
    rows = []
    for i, r in enumerate(results[:top_n]):
        lead = " lead" if i == 0 else ""
        rows.append(
            f'<div class="rank{lead}"><div class="nm">{escape(r.nama)}'
            f'<span class="d">{escape(TIPE_ID.get(r.tipe, r.tipe))}, {r.n_fired} dari {r.n_total} aturan terpenuhi</span></div>'
            f'<div class="bar"><span class="f" style="width:{min(r.cf, 1) * 100:.1f}%"></span></div>'
            f'<div class="pc">{r.cf * 100:.1f}%</div></div>'
        )
    return f'<div class="rankbox">{"".join(rows)}</div>'


def answers_summary(items: list[tuple[str, str]]) -> str:
    return "".join(f'<div class="ans"><span>{escape(n)}</span><em>{escape(l)}</em></div>' for n, l in items)


def reference(text: str, doi: str | None = None, url: str | None = None) -> str:
    link = ""
    if doi:
        link = f' <a href="https://doi.org/{escape(doi)}" target="_blank" rel="noopener">doi:{escape(doi)}</a>'
    elif url:
        link = f' <a href="{escape(url)}" target="_blank" rel="noopener">tautan</a>'
    return f'<div class="ref">{escape(text)}{link}</div>'
