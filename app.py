import streamlit as st
import requests
import re
import json
import numpy as np

# --- BAGIAN 1: FUNGSI-FUNGSI PEMBUAT QUERY ---

def build_branded_query(brand, model, spec, exclusions, time_filter, use_condition_filter, use_url_filter):
    """Membangun query presisi tinggi khusus untuk BARANG BERMEREK."""
    search_keywords = f'jual {brand} "{model}" {spec}'
    query_parts = [search_keywords, "(bekas|second|seken)"]
    if use_condition_filter:
        query_parts.append("-BNIB -segel")
    if use_url_filter:
        query_parts.append("-inurl:search -inurl:shop (site:tokopedia.com OR site:shopee.co.id OR site:olx.co.id)")
    if exclusions:
        exclusion_keywords = " ".join([f"-{word.strip()}" for word in exclusions.split(',')])
        query_parts.append(exclusion_keywords)
    query = " ".join(query_parts)
    params = {"q": query.strip(), "engine": "google", "gl": "id", "hl": "id", "location": "Jakarta, Jakarta, Indonesia"}
    if time_filter != "Semua Waktu":
        params["tbs"] = time_filter
    return params

def build_scrap_query(scrap_type, unit, time_filter):
    """Membangun query optimal untuk kategori SCRAP."""
    search_keywords = f'harga {scrap_type} bekas {unit}'
    params = {"q": search_keywords.strip(), "engine": "google", "gl": "id", "hl": "id"}
    if time_filter != "Semua Waktu":
        params["tbs"] = time_filter
    return params

def build_common_query(keywords, time_filter):
    """Membangun query fleksibel untuk BARANG UMUM."""
    query = f'jual {keywords} (bekas|second|seken)'
    params = {"q": query.strip(), "engine": "google", "gl": "id", "hl": "id"}
    if time_filter != "Semua Waktu":
        params["tbs"] = time_filter
    return params

# --- BAGIAN 2: FUNGSI-FUNGSI PEMANGGILAN API & PENGOLAHAN DATA ---

def search_with_serpapi(params, api_key):
    """Melakukan pencarian menggunakan API."""
    params["api_key"] = api_key
    try:
        response = requests.get("https://serpapi.com/search.json", params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Gagal menghubungi API: {e}")
        return None

def extract_text_for_llm(serpapi_data):
    """Mengekstrak semua teks relevan dari JSON API menjadi satu string."""
    texts = []
    if 'ai_overview' in serpapi_data and 'text_blocks' in serpapi_data['ai_overview']:
        for block in serpapi_data['ai_overview']['text_blocks']:
            texts.append(block.get('snippet', ''))
    for result in serpapi_data.get('organic_results', []):
        texts.append(result.get('title', ''))
        texts.append(result.get('snippet', ''))
    for question in serpapi_data.get('related_questions', []):
        texts.append(question.get('question', ''))
        texts.append(question.get('snippet', ''))
        if 'table' in question:
            for row in question['table']:
                texts.append(" | ".join(row))
    return "\n".join(filter(None, texts))

def extract_prices_from_text(text):
    """Fungsi untuk mengekstrak harga dari teks menggunakan regex"""
    # Pola regex untuk menemukan format harga Indonesia (Rp. 100.000, Rp 500000, dll)
    price_pattern = r'Rp\s*\.?\s*(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)'
    prices = []
    
    # Temukan semua kecocokan dengan pola harga
    matches = re.findall(price_pattern, text)
    
    for match in matches:
        # Hapus titik (pemisah ribuan) dan ganti koma dengan titik untuk desimal
        price_str = match.replace('.', '').replace(',', '.')
        try:
            price = float(price_str)
            prices.append(price)
        except ValueError:
            continue
    
    return prices

def analyze_with_llm(context_text, product_name, api_key):
    """Mengirim teks yang sudah diproses ke OpenRouter untuk dianalisis."""
    prompt = f"""
    Anda adalah asisten ahli analisis harga barang bekas. Tugas Anda adalah menganalisis KONTEKS PENCARIAN berikut untuk menemukan harga pasaran.

    PRODUK YANG DICARI: "{product_name}"

    KONTEKS PENCARIAN:
    ---
    {context_text[:15000]}
    ---

    INSTRUKSI:
    1. Berdasarkan KONTEKS PENCARIAN, analisis harga pasaran untuk PRODUK YANG DICARI.
    2. Abaikan harga aksesoris atau barang lain yang tidak relevan.
    3. Berikan rangkuman singkat mengenai harga pasaran dalam format yang mudah dibaca.
    4. Sertakan analisis singkat terkait produk dan harga yang disarankan.
    5. Berikan rekomendasi harga berdasarkan temuan Anda.
    6. JAWABAN HARUS DALAM BENTUK TEKS BIAASA YANG JELAS DAN INFORMATIF, BUKAN JSON.

    JANGAN GUNAKAN FORMAT JSON SAMA SEKALI. HANYA BERIKAN TEKS ANALISIS.
    """
    try:
        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            data=json.dumps({
                "model": st.secrets.get("LLM_MODEL"),
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 800,
                "temperature": 0.3
            })
        )
        response.raise_for_status()
        
        return response.json()['choices'][0]['message']['content']

    except requests.exceptions.RequestException as e:
        st.error(f"Gagal menghubungi OpenRouter API: {e}")
        return None
    except (KeyError, IndexError) as e:
        st.error(f"Gagal mengolah respons dari AI: {e}")
        return None

# --- BAGIAN 3: UI STREAMLIT ---

st.set_page_config(page_title="Price Analyzer", layout="wide")
st.title("💡 AI Price Analyzer")
st.write("Aplikasi untuk menganalisis harga pasaran barang bekas menggunakan AI.")

# --- Sidebar untuk input ---
st.sidebar.header("Pengaturan Pencarian")
category = st.sidebar.selectbox("1. Pilih Jenis Pencarian", ["Barang Bermerek", "Barang Umum", "Scrap"])
time_filter_options = {"Semua Waktu": "Semua Waktu", "Setahun Terakhir": "qdr:y", "Sebulan Terakhir": "qdr:m", "Seminggu Terakhir": "qdr:w"}
selected_time_filter = st.sidebar.selectbox("2. Filter Waktu", options=list(time_filter_options.keys()))
time_filter_value = time_filter_options[selected_time_filter]

if category == "Barang Bermerek":
    st.sidebar.subheader("Filter Lanjutan")
    use_condition_filter = st.sidebar.checkbox("Filter Kondisi (BNIB, dll.)", value=True)
    use_url_filter = st.sidebar.checkbox("Filter URL (search, shop)", value=True)
else:
    use_condition_filter, use_url_filter = False, False

# --- Form Input Utama ---
with st.form("main_form"):
    if category == "Barang Bermerek":
        st.header("📱 Detail Barang Bermerek")
        brand = st.text_input("Merek", "Apple")
        model = st.text_input("Model / Seri", "iPhone 14 Pro")
        spec = st.text_input("Spesifikasi (Opsional)", "256GB")
        exclusions = st.text_input("Kecualikan Varian (pisahkan koma)", "Max, Plus")
        product_name_display = f"{brand} {model} {spec}".strip()
    elif category == "Barang Umum":
        st.header("📦 Detail Barang Umum")
        keywords = st.text_input("Masukkan Nama Barang", "Bonsai Cemara Udang Ukuran Medium")
        product_name_display = keywords
    elif category == "Scrap":
        st.header("♻️ Detail Limbah (Scrap)")
        scrap_options = ["Besi Tua", "Tembaga", "Aluminium", "Kuningan", "Aki Bekas", "Minyak Jelantah", "Oli Bekas", "Kardus Bekas", "Botol Plastik PET"]
        scrap_type = st.selectbox("Pilih Jenis Limbah", scrap_options)
        unit_options = ["per kg", "per liter", "per drum", "per unit"]
        unit = st.selectbox("Pilih Satuan Harga", unit_options)
        product_name_display = f"{scrap_type} ({unit})"

    submitted = st.form_submit_button("Analisis Harga Sekarang!")

# --- ALUR KERJA UTAMA ---
if submitted:
    SERPAPI_API_KEY = st.secrets.get("SERPAPI_API_KEY")
    OPENROUTER_API_KEY = st.secrets.get("OPENROUTER_API_KEY")
    if not SERPAPI_API_KEY or not OPENROUTER_API_KEY:
        st.error("Harap konfigurasikan SERPAPI_API_KEY dan OPENROUTER_API_KEY di Streamlit Secrets!")
    else:
        # 1. Bangun Query
        if category == "Barang Bermerek":
            params = build_branded_query(brand, model, spec, exclusions, time_filter_value, use_condition_filter, use_url_filter)
        elif category == "Barang Umum":
            params = build_common_query(keywords, time_filter_value)
        elif category == "Scrap":
            params = build_scrap_query(scrap_type, unit, time_filter_value)
        
        with st.spinner(f"Menganalisis harga untuk '{product_name_display}'... Proses ini bisa memakan waktu 10-20 detik."):
            # 2. Panggil SerpApi
            st.info("Langkah 1/3: Mengambil data pencarian dari API...")
            serpapi_data = search_with_serpapi(params, SERPAPI_API_KEY)

            if serpapi_data:
                # 3. Pra-pemrosesan Teks
                st.info("Langkah 2/3: Mengekstrak teks relevan untuk dianalisis...")
                context_text = extract_text_for_llm(serpapi_data)

                if context_text:
                    # Ekstrak harga dari teks untuk analisis statistik
                    extracted_prices = extract_prices_from_text(context_text)
                    
                    # 4. Panggil OpenRouter (AI)
                    st.info("Langkah 3/3: Mengirim data ke AI untuk analisis harga...")
                    ai_analysis = analyze_with_llm(context_text, product_name_display, OPENROUTER_API_KEY)

                    if ai_analysis:
                        # 5. Tampilkan Hasil
                        st.balloons()
                        st.success("Analisis Harga Selesai!")
                        st.subheader(f"📊 Analisis Harga untuk {product_name_display}")
                        
                        # Tampilkan analisis dari AI
                        st.markdown("### Analisis AI")
                        st.write(ai_analysis)
                        
                        # Tampilkan statistik harga yang diekstrak
                        if extracted_prices:
                            st.markdown("### Statistik Harga yang Ditemukan")
                            
                            harga_rata_rata = np.mean(extracted_prices)
                            harga_median = np.median(extracted_prices)
                            harga_terendah = np.min(extracted_prices)
                            harga_tertinggi = np.max(extracted_prices)
                            
                            col1, col2, col3, col4 = st.columns(4)
                            col1.metric("Harga Rata-rata", f"Rp {int(harga_rata_rata):,}")
                            col2.metric("Harga Tengah (Median)", f"Rp {int(harga_median):,}")
                            col3.metric("Harga Terendah", f"Rp {int(harga_terendah):,}")
                            col4.metric("Harga Tertinggi", f"Rp {int(harga_tertinggi):,}")
                            
                            # Tampilkan distribusi harga
                            st.markdown("### Distribusi Harga")
                            st.bar_chart(extracted_prices)
                        else:
                            st.warning("Tidak dapat menemukan harga yang dapat diekstrak dari data pencarian.")
