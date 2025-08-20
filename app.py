import streamlit as st

# --- Kumpulan Fungsi Pembuat Query ---

def build_branded_query(brand, model, spec, exclusions, time_filter, use_condition_filter, use_url_filter):
    """
    Membangun query presisi tinggi khusus untuk BARANG BERMEREK.
    """
    # Model selalu di dalam tanda kutip untuk presisi
    search_keywords = f'Jual {brand} "{model}" {spec}'
    
    query_parts = [search_keywords, "(bekas|second|seken)"]
    
    # Filter ditambahkan secara kondisional
    if use_condition_filter:
        query_parts.append("-BNIB -segel")
    
    if use_url_filter:
        query_parts.append("-inurl:search -inurl:shop (site:tokopedia.com OR site:shopee.co.id OR site:olx.co.id)")
        
    # Menambahkan kata kunci pengecualian dari input pengguna
    if exclusions:
        exclusion_keywords = " ".join([f"-{word.strip()}" for word in exclusions.split(',')])
        query_parts.append(exclusion_keywords)
        
    query = " ".join(query_parts)
    
    params = {
        "q": query.strip(), "engine": "google", "gl": "id", "hl": "id",
        "location": "Jakarta, Jakarta, Indonesia"
    }
    
    if time_filter != "Semua Waktu":
        params["tbs"] = time_filter
        
    return params

def build_scrap_query(scrap_type, unit, time_filter):
    """Membangun query optimal untuk kategori SCRAP."""
    search_keywords = f'harga {scrap_type} bekas {unit}'
    params = {
        "q": search_keywords.strip(), "engine": "google", "gl": "id", "hl": "id",
    }
    if time_filter != "Semua Waktu":
        params["tbs"] = time_filter
    return params

def build_common_query(keywords, time_filter):
    """Membangun query fleksibel untuk BARANG UMUM."""
    # Untuk barang umum, kita gabungkan keyword dengan kata "bekas"
    query = f'{keywords} (bekas|second|seken)'
    params = {
        "q": query.strip(), "engine": "google", "gl": "id", "hl": "id",
    }
    if time_filter != "Semua Waktu":
        params["tbs"] = time_filter
    return params

# --- UI STREAMLIT ---

st.set_page_config(page_title="Query Generator", layout="centered")
st.title("🚀 SerpApi Query Generator")
st.write(
    "Alat bantu untuk membuat query pencarian yang optimal sebelum digunakan."
)

st.sidebar.header("Pengaturan Pencarian")

# --- PERUBAHAN: Kategori disederhanakan menjadi 3 jenis ---
category = st.sidebar.selectbox(
    "1. Pilih Jenis Pencarian",
    ["Barang Bermerek", "Barang Umum", "Scrap"]
)

time_filter_options = {
    "Semua Waktu": "Semua Waktu", "Setahun Terakhir": "qdr:y",
    "Sebulan Terakhir": "qdr:m", "Seminggu Terakhir": "qdr:w"
}
selected_time_filter = st.sidebar.selectbox(
    "2. Filter Waktu", options=list(time_filter_options.keys())
)
time_filter_value = time_filter_options[selected_time_filter]

# Filter lanjutan hanya relevan untuk Barang Bermerek
if category == "Barang Bermerek":
    st.sidebar.subheader("Filter Lanjutan (Opsional)")
    use_condition_filter = st.sidebar.checkbox("Filter Kondisi (BNIB, baru, dll.)", value=True)
    use_url_filter = st.sidebar.checkbox("Filter URL (search, shop)", value=True)
else:
    use_condition_filter, use_url_filter = False, False

# --- Input Dinamis Berdasarkan Kategori ---
final_params = None

if category == "Barang Bermerek":
    st.header("📱 Detail Barang Bermerek")
    st.caption("Contoh: Smartphone, Laptop, Kamera, AC, Kulkas, dll.")
    
    brand = st.text_input("Merek", "Apple")
    model = st.text_input("Model / Seri", "iPhone 15 Pro")
    spec = st.text_input("Spesifikasi (Opsional)", "256GB")
    exclusions = st.text_input("Kecualikan Varian (pisahkan koma)", "Max, Plus")

    if st.button("Generate Query"):
        final_params = build_branded_query(brand, model, spec, exclusions, time_filter_value, use_condition_filter, use_url_filter)

elif category == "Barang Umum":
    st.header("📦 Detail Barang Umum")
    st.caption("Contoh: Bonsai Cemara Udang, Meja Kantor, Sepeda Polygon, dll.")
    keywords = st.text_input("Masukkan Nama Barang", "Bonsai Cemara Udang Ukuran Medium")
    
    if st.button("Generate Query"):
        final_params = build_common_query(keywords, time_filter_value)

elif category == "Scrap":
    st.header("♻️ Detail Limbah (Scrap)")
    scrap_options = ["Besi Tua", "Tembaga", "Aluminium", "Kuningan", "Aki Bekas", "Kabel Bekas", "Minyak Jelantah", "Oli Bekas", "Kardus Bekas", "Botol Plastik PET", "Komputer Bekas"]
    scrap_type = st.selectbox("Pilih Jenis Limbah", scrap_options)
    unit_options = ["per kg", "per liter", "per drum", "per unit", "per ton", "per bal"]
    unit = st.selectbox("Pilih Satuan Harga", unit_options)
    if st.button("Generate Query"):
        final_params = build_scrap_query(scrap_type, unit, time_filter_value)

# --- Tampilkan Hasil ---
if final_params:
    st.balloons()
    st.subheader("✅ Query Siap Digunakan!")
    st.write("Ini adalah parameter yang akan dikirim ke SerpApi. Anda bisa fokus pada nilai `q` untuk diuji coba.")
    st.json(final_params)
    st.subheader("Query untuk Playground SerpApi:")
    st.code(final_params['q'], language='text')
    st.caption("Salin query di atas dan coba di playground SerpApi.")
