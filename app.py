import streamlit as st
import requests
import re
import json
import numpy as np

# --- BAGIAN 1: FUNGSI-FUNGSI PEMBUAT QUERY (Tidak ada perubahan) ---

def build_common_query(keywords, time_filter, use_condition_filter, use_url_filter):
    """Membangun query fleksibel untuk BARANG UMUM."""
    query_parts = [f'jual {keywords}']
    
    if use_condition_filter:
        query_parts.append("(inurl:bekas OR inurl:second OR inurl:seken OR inurl:seperti-baru OR inurl:2nd OR inurl:like-new) -BNIB -segel")
        
    if use_url_filter:
        query_parts.append("(site:tokopedia.com OR site:shopee.co.id)")

    query = " ".join(query_parts)
    params = {"q": query.strip(), "engine": "google", "gl": "id", "hl": "id", "location": "Jakarta, Jakarta, Indonesia"}
    if time_filter != "Semua Waktu":
        params["tbs"] = time_filter
    return params

def build_spare_part_query(keywords, time_filter, use_condition_filter, use_url_filter):
    """Membangun query optimal untuk kategori SPARE PART."""
    query_parts = [f'jual {keywords}']

    if use_condition_filter:
        query_parts.append("(inurl:bekas OR inurl:second OR inurl:seken OR inurl:seperti-baru OR inurl:2nd OR inurl:copotan OR inurl:like-new) -BNIB -segel")

    if use_url_filter:
        query_parts.append("(site:tokopedia.com OR site:shopee.co.id OR site:monotaro.id OR site:olx.co.id)")
    
    query = " ".join(query_parts)
    params = {"q": query.strip(), "engine": "google", "gl": "id", "hl": "id"}
    if time_filter != "Semua Waktu":
        params["tbs"] = time_filter
    return params

def build_heavy_equipment_query(alat_type, brand, model, year, time_filter, use_condition_filter, use_url_filter):
    """Membangun query optimal untuk kategori ALAT BERAT."""
    search_keywords = f'jual {alat_type} {brand} {model} tahun {year}'
    query_parts = [search_keywords]

    if use_condition_filter:
        query_parts.append("(bekas|second) -sewa -rental -disewakan")
        
    if use_url_filter:
        query_parts.append("(site:olx.co.id OR site:indotrading.com OR site:alatberat.com OR site:jualo.com)")

    query = " ".join(query_parts)
    params = {"q": query.strip(), "engine": "google", "gl": "id", "hl": "id"}
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

# --- BAGIAN 2: FUNGSI-FUNGSI PEMANGGILAN API & PENGOLAHAN DATA (Fungsi LLM diperbarui) ---

def search_with_serpapi(params, api_key):
    """Melakukan pencarian menggunakan API."""
    params["api_key"] = api_key
    try:
        response = requests.get("https://serpapi.com/search.json", params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Gagal menghubungi SerpAPI: {e}")
        return None

def filter_and_extract_text_for_llm(serpapi_data, product_name):
    """Mengekstrak teks relevan DARI HASIL YANG SUDAH DIFILTER untuk presisi."""
    texts = []
    main_keywords = [word.lower() for word in product_name.split() if len(word) > 2]
    negative_keywords = ['baru', 'bnib', 'resmi', 'official', 'store', 'casing', 'charger', 'aksesoris', 'sewa', 'rental']

    for result in serpapi_data.get('organic_results', []):
        title = result.get('title', '').lower()
        snippet = result.get('snippet', '').lower()
        full_text = title + " " + snippet

        if any(neg_word in full_text for neg_word in negative_keywords):
            continue
        if not any(main_word in full_text for main_word in main_keywords):
            continue

        texts.append(result.get('title', ''))
        texts.append(result.get('snippet', ''))

    for question in serpapi_data.get('related_questions', []):
        texts.append(question.get('question', ''))
        texts.append(question.get('snippet', ''))

    return "\n".join(filter(None, texts))

def extract_prices_from_text(text):
    """Fungsi untuk mengekstrak harga dari teks menggunakan regex."""
    price_pattern = r'Rp\s*\.?\s*(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)'
    prices = []
    matches = re.findall(price_pattern, text)
    for match in matches:
        price_str = match.replace('.', '').replace(',', '.')
        try:
            price = float(price_str)
            if price > 1000:
                prices.append(price)
        except ValueError:
            continue
    return prices

# --- DIUBAH ---
def analyze_with_llm(context_text, product_name, api_key, grade):
    """Mengirim teks yang sudah diproses ke OpenRouter untuk dianalisis dengan memperhitungkan grade."""
    llm_model = st.secrets.get("LLM_MODEL")
    
    # Menambahkan instruksi kalkulasi grade ke dalam prompt
    prompt = f"""
    Anda adalah asisten ahli analisis harga barang bekas yang bekerja di balai lelang digital LEGOAS.
    Tugas Anda adalah menganalisis KONTEKS PENCARIAN untuk menemukan harga pasaran wajar.

    PRODUK YANG DICARI: "{product_name}"
    GRADE KONDISI: "{grade}"

    KONTEKS PENCARIAN:
    ---
    {context_text[:15000]}
    ---

    INSTRUKSI UTAMA:
    1.  Fokus utama Anda adalah pada PRODUK YANG DICARI. Abaikan harga untuk produk atau aksesoris lain.
    2.  Berdasarkan data, berikan analisis singkat mengenai kondisi pasar dan variasi harga yang Anda temukan.
    3.  Berikan satu **rekomendasi harga jual wajar** untuk produk tersebut dalam kondisi bekas layak pakai (ini kita sebut sebagai "Harga Grade A"). Jelaskan alasan di balik angka ini.
    4.  Setelah menentukan Harga Grade A, hitung dan tampilkan harga untuk grade lainnya berdasarkan persentase berikut:
        -   **Harga Grade A (Kondisi Sangat Baik):** Tampilkan harga rekomendasi Anda.
        -   **Harga Grade B (Kondisi Baik):** Hitung 94% dari Harga Grade A.
        -   **Harga Grade C (Kondisi Cukup):** Hitung 80% dari Harga Grade A.
        -   **Harga Grade D (Kondisi Kurang):** Hitung 58% dari Harga Grade A.
        -   **Harga Grade E (Kondisi Apa Adanya):** Hitung 23% dari Harga Grade A.
    5.  Sajikan hasil akhir dalam format yang jelas, dimulai dengan analisis pasar, lalu diikuti oleh daftar harga berdasarkan grade. Beri penekanan (misalnya dengan bold) pada harga yang sesuai dengan **GRADE KONDISI** yang diminta pengguna.
    6.  JAWABAN HARUS DALAM BENTUK TEKS BIASA, BUKAN JSON.
    """
    try:
        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            data=json.dumps({
                "model": llm_model, "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 1200, "temperature": 0.2
            })
        )
        response.raise_for_status()
        response_data = response.json()
        if 'error' in response_data:
            st.error("API OpenRouter mengembalikan error:"); st.json(response_data)
            return None
        return response_data['choices'][0]['message']['content']
    except requests.exceptions.RequestException as e:
        st.error(f"Gagal menghubungi OpenRouter API: {e}")
        if e.response is not None: st.json(e.response.json())
        return None
    except (KeyError, IndexError) as e:
        st.error(f"Gagal mengolah respons dari AI: {e}"); st.json(response.json())
        return None

# --- BAGIAN 3: UI STREAMLIT (DIMODIFIKASI) ---

st.set_page_config(page_title="AI Price Analyzer", layout="wide")
st.title("💡 AI Price Analyzer")
st.write("Aplikasi untuk menganalisis harga pasaran barang bekas menggunakan AI.")

st.sidebar.header("Pengaturan Pencarian")
category = st.sidebar.selectbox(
    "1. Pilih Kategori Barang",
    ["Umum", "Spare Part", "Alat Berat", "Scrap"]
)
time_filter_options = {"Semua Waktu": "Semua Waktu", "Setahun Terakhir": "qdr:y", "Sebulan Terakhir": "qdr:m", "Seminggu Terakhir": "qdr:w"}
selected_time_filter = st.sidebar.selectbox("2. Filter Waktu", options=list(time_filter_options.keys()))
time_filter_value = time_filter_options[selected_time_filter]

st.sidebar.subheader("Filter Lanjutan")
use_condition_filter = st.sidebar.checkbox(
    "Fokus Barang Bekas", value=True,
    help="Jika aktif, AI akan fokus mencari barang bekas dan mengabaikan iklan barang baru atau segel."
)
use_url_filter = st.sidebar.checkbox(
    "Fokus Situs Jual-Beli", value=True,
    help="Jika aktif, pencarian akan diprioritaskan pada situs jual-beli utama untuk hasil yang lebih relevan."
)

with st.form("main_form"):
    product_name_display = ""
    grade_input = "A" # Default grade

    if category in ["Umum", "Spare Part", "Alat Berat"]:
        st.header("⭐ Pilih Grade Kondisi Barang")
        grade_input = st.selectbox(
            "Grade", 
            options=["A", "B", "C", "D", "E"],
            help="Pilih kondisi barang: A (Sangat Baik), B (Baik), C (Cukup), D (Kurang), E (Apa Adanya)."
        )

    if category == "Umum":
        st.header("📦 Detail Barang Umum")
        keywords = st.text_input("Masukkan Nama Barang", "iPhone 14 Pro 256GB", help="Tips: Coba sespesifik mungkin untuk hasil terbaik.")
        product_name_display = keywords.lower()
    elif category == "Spare Part":
        st.header("⚙️ Detail Spare Part")
        keywords = st.text_input("Masukkan Nama Spare Part", "Busi Honda Vario 125", help="Contoh: 'Kampas rem Avanza', 'Filter oli Xenia 1.3'")
        product_name_display = keywords.lower()
    elif category == "Alat Berat":
        st.header("🛠️ Detail Alat Berat")
        alat_type = st.text_input("Jenis Alat", "Excavator")
        brand = st.text_input("Merek", "Komatsu")
        model = st.text_input("Model / Kapasitas", "PC200-8")
        year = st.text_input("Tahun (Wajib)", "2015")
        product_name_display = f"{alat_type} {brand} {model} {year}".strip().lower()
    elif category == "Scrap":
        st.header("♻️ Detail Limbah (Scrap)")
        scrap_options = ["Besi Tua", "Tembaga", "Aluminium", "Kuningan", "Aki Bekas", "Minyak Jelantah", "Oli Bekas", "Kardus Bekas", "Botol Plastik PET"]
        scrap_type = st.selectbox("Pilih Jenis Limbah", scrap_options)
        unit_options = ["per kg", "per liter", "per drum", "per unit"]
        unit = st.selectbox("Pilih Satuan Harga", unit_options)
        product_name_display = f"{scrap_type} ({unit})"

    submitted = st.form_submit_button("Analisis Harga Sekarang!")

# --- BAGIAN 4: ALUR KERJA UTAMA (DIMODIFIKASI) ---
if submitted:
    SERPAPI_API_KEY = st.secrets.get("SERPAPI_API_KEY")
    OPENROUTER_API_KEY = st.secrets.get("OPENROUTER_API_KEY")
    LLM_MODEL = st.secrets.get("LLM_MODEL")

    if not all([SERPAPI_API_KEY, OPENROUTER_API_KEY, LLM_MODEL]):
        st.error("Harap konfigurasikan SERPAPI_API_KEY, OPENROUTER_API_KEY, dan LLM_MODEL di Streamlit Secrets!")
    else:
        params = {}
        if category == "Umum":
            params = build_common_query(keywords, time_filter_value, use_condition_filter, use_url_filter)
        elif category == "Spare Part":
            params = build_spare_part_query(keywords, time_filter_value, use_condition_filter, use_url_filter)
        elif category == "Alat Berat":
            params = build_heavy_equipment_query(alat_type, brand, model, year, time_filter_value, use_condition_filter, use_url_filter)
        elif category == "Scrap":
            params = build_scrap_query(scrap_type, unit, time_filter_value)

        with st.spinner(f"Menganalisis harga untuk '{product_name_display}' (Grade {grade_input if category != 'Scrap' else 'N/A'})..."):
            st.info("Langkah 1/4: Mengambil data pencarian dari API...")
            serpapi_data = search_with_serpapi(params, SERPAPI_API_KEY)

            if serpapi_data:
                st.info("Langkah 2/4: Memfilter hasil pencarian untuk akurasi...")
                context_text = filter_and_extract_text_for_llm(serpapi_data, product_name_display)

                if context_text:
                    st.info("Langkah 3/4: Mengirim data bersih ke AI untuk analisis harga...")
                    # --- DIUBAH ---
                    # Melewatkan nilai grade_input ke fungsi analisis AI
                    ai_analysis = analyze_with_llm(context_text, product_name_display, OPENROUTER_API_KEY, grade_input)

                    if ai_analysis:
                        st.info("Langkah 4/4: Menyiapkan laporan hasil analisis...")
                        st.balloons()
                        st.success("Analisis Harga Selesai!")
                        
                        st.subheader(f"📝 Analisis AI LEGOAS untuk Harga {product_name_display}")
                        st.markdown("### Rekomendasi & Analisis AI")
                        st.write(ai_analysis)

                        extracted_prices = extract_prices_from_text(context_text)
                        if not extracted_prices:
                            st.info("Catatan: AI tidak menemukan angka harga spesifik dalam hasil pencarian, analisis mungkin bersifat lebih umum.")
                    else:
                        st.error("Analisis Gagal: Tidak menerima respons dari AI.")
                else:
                    st.error("Ekstraksi Teks Gagal: Tidak ada hasil pencarian yang relevan ditemukan setelah filtering.")
                    st.warning("**Saran:** Coba sederhanakan nama barang Anda, periksa kembali ejaan, atau nonaktifkan filter di sidebar untuk memperluas pencarian.")
            else:
                st.error("Pengambilan Data Gagal: Tidak menerima data dari SerpAPI.")
