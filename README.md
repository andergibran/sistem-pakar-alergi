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




