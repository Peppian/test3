import streamlit as st

# --- Kumpulan Fungsi Pembuat Query ---

def build_smartphone_query(brand, model, spec, time_filter):
    """Membangun query optimal untuk kategori Smartphone."""
    search_keywords = f'{brand} "{model}" {spec}'
    used_keywords = "(bekas|second|seken)"
    negative_keywords = "-BNIB -segel -resmi -baru -official"
    negative_url_patterns = "-inurl:search -inurl:shop"
    query = f'{search_keywords} {used_keywords} {negative_keywords} {negative_url_patterns}'
    params = {
        "q": query.strip(),
        "engine": "google",
        "gl": "id",
        "hl": "id",
        "location": "Jakarta, Jakarta, Indonesia"
    }
    if time_filter != "Semua Waktu":
        params["tbs"] = time_filter
    return params

def build_scrap_query(scrap_type, unit, time_filter):
    """Membangun query optimal untuk kategori Scrap/Limbah."""
    search_keywords = f'harga {scrap_type} bekas {unit}'
    params = {
        "q": search_keywords.strip(),
        "engine": "google",
        "gl": "id",
        "hl": "id",
    }
    if time_filter != "Semua Waktu":
        params["tbs"] = time_filter
    return params

# --- UI STREAMLIT ---

st.set_page_config(page_title="Query Generator", layout="centered")
st.title("🚀 SerpApi Query Generator")
st.write(
    "Gunakan alat ini untuk membuat query pencarian yang optimal. "
    "Salin hasilnya dan uji coba secara gratis di playground website SerpApi."
)

st.sidebar.header("Pengaturan Pencarian")

category = st.sidebar.selectbox(
    "1. Pilih Kategori Barang",
    ["Smartphone", "Scrap", "Lainnya (Umum)"]
)

time_filter_options = {
    "Semua Waktu": "Semua Waktu",
    "Setahun Terakhir": "qdr:y",
    "Sebulan Terakhir": "qdr:m",
    "Seminggu Terakhir": "qdr:w"
}
selected_time_filter = st.sidebar.selectbox(
    "2. Filter Waktu (Opsional)",
    options=list(time_filter_options.keys())
)
time_filter_value = time_filter_options[selected_time_filter]


# --- Input Dinamis Berdasarkan Kategori ---

final_params = None

if category == "Smartphone":
    st.header("📱 Detail Smartphone")
    brand = st.text_input("Merek", "Samsung")
    model = st.text_input("Model Inti", "Galaxy S24 Ultra")
    spec = st.text_input("Spesifikasi", "512GB")
    
    if st.button("Generate Query"):
        final_params = build_smartphone_query(brand, model, spec, time_filter_value)

elif category == "Scrap":
    st.header("♻️ Detail Limbah (Scrap)")
    
    scrap_options = [
        "Besi Tua", "Tembaga", "Aluminium", "Kuningan", 
        "Aki Bekas", "Kabel Bekas", "Minyak Jelantah", "Oli Bekas", 
        "Kardus Bekas", "Botol Plastik PET", "Komputer Bekas"
    ]
    scrap_type = st.selectbox("Pilih Jenis Limbah", scrap_options)
    
    # --- PERUBAHAN DI SINI ---
    unit_options = ["per kg", "per liter", "per drum", "per unit", "per ton", "per bal"]
    unit = st.selectbox("Pilih Satuan Harga", unit_options)

    if st.button("Generate Query"):
        final_params = build_scrap_query(scrap_type, unit, time_filter_value)
        
elif category == "Lainnya (Umum)":
    st.header("📦 Pencarian Umum")
    keywords = st.text_input("Masukkan Kata Kunci", "Meja kantor bekas")
    
    if st.button("Generate Query"):
        final_params = {
            "q": keywords,
            "engine": "google",
            "gl": "id",
            "hl": "id",
        }
        if time_filter_value != "Semua Waktu":
            final_params["tbs"] = time_filter_value

# --- Tampilkan Hasil ---

if final_params:
    st.balloons()
    st.subheader("✅ Query Siap Digunakan!")
    st.write("Ini adalah parameter yang akan dikirim ke SerpApi. Anda bisa fokus pada nilai `q` untuk diuji coba.")
    
    st.json(final_params)

    st.subheader("Query untuk Playground SerpApi:")
    st.code(final_params['q'], language='text')
    st.caption("Salin query di atas dan coba di playground SerpApi.")
