import streamlit as st

# --- Kumpulan Fungsi Pembuat Query ---

def build_smartphone_query(brand, model, spec, time_filter):
    """Membangun query optimal untuk kategori Smartphone."""
    search_keywords = f'{brand} "{model}" {spec}'
    used_keywords = "(bekas|second|seken)"
    negative_keywords = "-BNIB -segel -resmi -baru -official"
    negative_url_patterns = "-inurl:search -inurl:shop"

    # Gabungkan semua bagian
    query = f'{search_keywords} {used_keywords} {negative_keywords} {negative_url_patterns}'
    
    # Buat dictionary parameter untuk SerpApi
    params = {
        "q": query.strip(),
        "engine": "google",
        "gl": "id",
        "hl": "id",
        "location": "Jakarta, Jakarta, Indonesia"
    }
    
    # Tambahkan filter waktu jika dipilih
    if time_filter != "Semua Waktu":
        params["tbs"] = time_filter
        
    return params


def build_scrap_query(material, unit, time_filter):
    """Membangun query optimal untuk kategori Scrap/Limbah."""
    # Contoh "bahasa" untuk scrap: harga per kg, per liter, dll.
    search_keywords = f'harga {material} bekas {unit}'
    
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
    ["Smartphone", "Logam Bekas (Scrap)", "Lainnya (Umum)"]
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

elif category == "Logam Bekas (Scrap)":
    st.header("🔩 Detail Scrap")
    material = st.text_input("Jenis Material", "Besi Bekas")
    unit = st.text_input("Satuan Harga", "per kg")

    if st.button("Generate Query"):
        final_params = build_scrap_query(material, unit, time_filter_value)
        
elif category == "Lainnya (Umum)":
    st.header("📦 Pencarian Umum")
    keywords = st.text_input("Masukkan Kata Kunci", "Laptop Lenovo Thinkpad T480 i7 bekas")
    
    if st.button("Generate Query"):
        # Untuk umum, kita hanya gabungkan dengan filter waktu
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
    
    # Tampilkan dalam format yang mudah dibaca
    st.json(final_params)

    st.subheader("Query untuk Playground SerpApi:")
    st.code(final_params['q'], language='text')
    st.caption("Salin query di atas dan coba di playground website SerpApi.")
