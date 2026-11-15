# Sistem Pakar Identifikasi Awal Jenis Alergi (pencocokan gejala)

## Menjalankan
    pip install -r requirements.txt
    streamlit run app.py

## File
- app.py      : antarmuka Streamlit (konsultasi, basis pengetahuan, metode dan rujukan)
- engine.py   : mesin pencocokan gejala (tanpa Streamlit, tanpa basis aturan)
- tampilan.py : CSS dan komponen HTML
- basis_pengetahuan_sistem_pakar_alergi.xlsx : letakkan sefolder dengan app.py.
  Yang dibaca aplikasi: Tabel1_Alergi, Tabel2_Indikator, Tabel3_Matriks. Sheet Aturan_CF tidak dipakai.

## Cara kerja
Pengguna mencentang pemicu dan gejala. Tiap jenis alergi diberi skor weighted Dice terhadap pilihan itu,
dengan bobot indikator = max(0,1; 1 - jumlah alergi pemilik indikator / jumlah alergi).
Mengubah ciri sebuah alergi cukup dengan mengubah sel 1/0 di Tabel3_Matriks, lalu jalankan ulang aplikasi.

## Catatan
Alat skrining awal, bukan diagnosis. Indikator berstatus "Usulan" belum diverifikasi pakar.
