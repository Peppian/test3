import streamlit as st

# --- Kumpulan Fungsi Pembuat Query ---

def build_general_query(part1, part2, part3, exclusions, time_filter, category, use_condition_filter, use_url_filter):
    """
    Membangun query seragam untuk barang umum dengan filter opsional dan pengecualian.
    """
    if category in ["Smartphone", "Laptop", "Kamera"]:
        search_keywords = f'jual {part1} "{part2}" {part3}'
    else:
        search_keywords = f'jual {part1} {part2} {part3}'
    
    query_parts = [search_keywords, "(bekas|second|seken)"]
    
    # Filter ditambahkan secara kondisional
    if use_condition_filter:
        query_parts.append("-BNIB -segel")
    
    if use_url_filter:
        query_parts.append("-inurl:search -inurl:shop (site:tokopedia.com OR site:shopee.co.id OR site:olx.co.id)")
        
    # --- PENYESUAIAN: Menambahkan kata kunci pengecualian dari input pengguna ---
    if exclusions:
        # Ubah "Max, Plus, Ultra" menjadi "-Max -Plus -Ultra"
        exclusion_keywords = " ".join([f"-{word.strip()}" for word in exclusions.split(',')])
        query_parts.append(exclusion_keywords)
        
    query = " ".join(query_parts)
    
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
    ["Smartphone", "Laptop", "Kamera", "Tanaman Hias", "Scrap", "Lainnya (Umum)"]
)

time_filter_options = {
    "Semua Waktu": "Semua Waktu", 
    "Setahun Terakhir": "qdr:y",
    "Sebulan Terakhir": "qdr:m", 
    "Seminggu Terakhir": "qdr:w"
}
selected_time_filter = st.sidebar.selectbox(
    "2. Filter Waktu",
    options=list(time_filter_options.keys())
)
time_filter_value = time_filter_options[selected_time_filter]

st.sidebar.subheader("Filter Lanjutan (Opsional)")
use_condition_filter = st.sidebar.checkbox("Filter Kondisi (BNIB, baru, dll.)", value=True)
use_url_filter = st.sidebar.checkbox("Filter URL (search, shop)", value=True)


# --- Input Dinamis Berdasarkan Kategori ---

final_params = None

if category in ["Smartphone", "Laptop", "Kamera", "Tanaman Hias"]:
    
    if category == "Smartphone":
        st.header("📱 Detail Smartphone")
        label1, placeholder1 = "Merek", "Apple"
        label2, placeholder2 = "Model Inti", "iPhone 14 Pro"
        label3, placeholder3 = "Spesifikasi", "256GB"
        # --- PENYESUAIAN: Input baru untuk pengecualian ---
        label4, placeholder4 = "Kecualikan Varian (pisahkan dengan koma)", "Max, Plus"
    elif category == "Laptop":
        st.header("💻 Detail Laptop")
        label1, placeholder1 = "Merek", "Lenovo"
        label2, placeholder2 = "Model / Seri", "Thinkpad T480"
        label3, placeholder3 = "Spesifikasi (CPU/RAM, dll.)", "Core i7 16GB"
        label4, placeholder4 = "Kecualikan Varian (Opsional)", "Yoga, Slim" # Contoh untuk laptop
    # ... (Kategori lain bisa ditambahkan input pengecualian jika perlu) ...
    else: # Default untuk Kamera & Tanaman Hias
        label4 = None

    part1 = st.text_input(label1, placeholder1)
    part2 = st.text_input(label2, placeholder2)
    part3 = st.text_input(label3, placeholder3)
    
    # Tampilkan input ke-4 hanya jika labelnya ada
    exclusions = ""
    if label4:
        exclusions = st.text_input(label4, placeholder4)

    if st.button("Generate Query"):
        final_params = build_general_query(part1, part2, part3, exclusions, time_filter_value, category, use_condition_filter, use_url_filter)

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
