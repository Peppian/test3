import streamlit as st

# --- Kumpulan Fungsi Pembuat Query ---

def build_general_query(part1, part2, part3, time_filter):
    """
    Membangun query seragam untuk barang umum (Smartphone, Laptop, dll.).
    Strategi ini menggunakan query presisi tinggi yang terbukti efektif.
    """
    # Model/Nama Spesifik (part2) selalu di dalam tanda kutip untuk presisi
    search_keywords = f'{part1} "{part2}" {part3}'
    
    # Kata kunci standar untuk memastikan hasil yang relevan
    used_keywords = "(bekas|second|seken)"
    negative_keywords = "-BNIB -segel -resmi -baru -official"
    negative_url_patterns = "-inurl:search -inurl:shop"
    
    # Menggabungkan semua komponen menjadi satu string query yang kuat
    query = f'{search_keywords} {used_keywords} {negative_keywords} {negative_url_patterns}'
    
    # Membuat dictionary parameter untuk dikirim ke SerpApi
    params = {
        "q": query.strip(),
        "engine": "google",
        "gl": "id",
        "hl": "id",
        "location": "Jakarta, Jakarta, Indonesia"
    }
    
    # Menambahkan filter waktu jika dipilih oleh pengguna
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

# Daftar kategori yang didukung
category = st.sidebar.selectbox(
    "1. Pilih Kategori Barang",
    ["Smartphone", "Laptop", "Kamera", "Tanaman Hias", "Scrap", "Lainnya (Umum)"]
)

# Opsi filter waktu
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

# Blok ini menangani semua kategori barang umum dengan input 3 bagian
if category in ["Smartphone", "Laptop", "Kamera", "Tanaman Hias"]:
    
    # Label dan placeholder akan berubah sesuai kategori yang dipilih
    if category == "Smartphone":
        st.header("📱 Detail Smartphone")
        label1, placeholder1 = "Merek", "Apple"
        label2, placeholder2 = "Model Inti", "iPhone 15 Pro"
        label3, placeholder3 = "Spesifikasi (Opsional)", "256GB"
    elif category == "Laptop":
        st.header("💻 Detail Laptop")
        label1, placeholder1 = "Merek", "Lenovo"
        label2, placeholder2 = "Model / Seri", "Thinkpad T480"
        label3, placeholder3 = "Spesifikasi (CPU/RAM, dll.)", "Core i7 16GB"
    elif category == "Kamera":
        st.header("📷 Detail Kamera")
        label1, placeholder1 = "Merek", "Sony"
        label2, placeholder2 = "Model", "Alpha A7 III"
        label3, placeholder3 = "Paket (Opsional)", "Body Only"
    elif category == "Tanaman Hias":
        st.header("🌳 Detail Tanaman Hias")
        label1, placeholder1 = "Jenis Tanaman", "Bonsai"
        label2, placeholder2 = "Nama Spesifik / Varian", "Cemara Udang"
        label3, placeholder3 = "Deskripsi (Ukuran/Gaya, dll.)", "Ukuran Medium"
        
    part1 = st.text_input(label1, placeholder1)
    part2 = st.text_input(label2, placeholder2)
    part3 = st.text_input(label3, placeholder3)

    if st.button("Generate Query"):
        final_params = build_general_query(part1, part2, part3, time_filter_value)

elif category == "Scrap":
    st.header("♻️ Detail Limbah (Scrap)")
    scrap_options = ["Besi Tua", "Tembaga", "Aluminium", "Kuningan", "Aki Bekas", "Kabel Bekas", "Minyak Jelantah", "Oli Bekas", "Kardus Bekas", "Botol Plastik PET", "Komputer Bekas"]
    scrap_type = st.selectbox("Pilih Jenis Limbah", scrap_options)
    unit_options = ["per kg", "per liter", "per drum", "per unit", "per ton", "per bal"]
    unit = st.selectbox("Pilih Satuan Harga", unit_options)
    if st.button("Generate Query"):
        final_params = build_scrap_query(scrap_type, unit, time_filter_value)
        
elif category == "Lainnya (Umum)":
    st.header("📦 Pencarian Umum")
    keywords = st.text_input("Masukkan Kata Kunci", "Meja kantor bekas")
    if st.button("Generate Query"):
        final_params = {"q": keywords, "engine": "google", "gl": "id", "hl": "id"}
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
