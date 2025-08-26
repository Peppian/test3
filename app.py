import streamlit as st
import requests
import re
import json
import numpy as np

# --- BAGIAN 1: FUNGSI-FUNGSI PEMBUAT QUERY (DIPERKUAT) ---

# ⭐ PERUBAHAN DISARANKAN: Menambahkan lebih banyak kata kunci negatif pada branded query
def build_branded_query(brand, model, spec, exclusions, time_filter, use_condition_filter, use_url_filter):
    """Membangun query presisi tinggi khusus untuk BARANG BERMEREK."""
    search_keywords = f'jual {brand} "{model}" {spec}'
    # Menambahkan "kondisi bekas" untuk memperkuat sinyal
    query_parts = [search_keywords, '(bekas|second|seken|"kondisi bekas")']

    if use_condition_filter:
        # Menambahkan lebih banyak kata kunci negatif untuk barang baru dan aksesoris
        query_parts.append("-BNIB -segel -baru -resmi -garansi -official -store -casing -charger -aksesoris")

    if use_url_filter:
        # Menambahkan beberapa marketplace relevan lainnya
        query_parts.append("-inurl:search -inurl:shop (site:tokopedia.com OR site:shopee.co.id OR site:olx.co.id OR site:bukalapak.com OR site:carousell.co.id)")

    if exclusions:
        exclusion_keywords = " ".join([f"-{word.strip()}" for word in exclusions.split(',')])
        query_parts.append(exclusion_keywords)

    query = " ".join(query_parts)
    params = {"q": query.strip(), "engine": "google", "gl": "id", "hl": "id", "location": "Jakarta, Jakarta, Indonesia"}
    if time_filter != "Semua Waktu":
        params["tbs"] = time_filter
    return params

# ⭐ PERUBAHAN DISARANKAN: Menambahkan kata kunci negatif pada query alat berat
def build_heavy_equipment_query(alat_type, brand, model, year, time_filter):
    """Membangun query optimal untuk kategori ALAT BERAT."""
    search_keywords = f'jual {alat_type} {brand} {model} tahun {year}'
    query_parts = [
        search_keywords,
        "(bekas|second)",
        # Tambahkan kata kunci negatif yang relevan untuk alat berat
        "-sewa -rental -disewakan",
        "(site:olx.co.id OR site:indotrading.com OR site:alatberat.com OR site:jualo.com)"
    ]
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

def build_common_query(keywords, time_filter):
    """Membangun query fleksibel untuk BARANG UMUM."""
    query = f'jual {keywords} (bekas|second|seken) -baru -resmi' # Tambah filter dasar
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
        st.error(f"Gagal menghubungi SerpAPI: {e}")
        return None

# ⭐ PERUBAHAN DISARANKAN: Fungsi baru untuk memfilter hasil sebelum dikirim ke AI
def filter_and_extract_text_for_llm(serpapi_data, product_name):
    """
    Mengekstrak teks relevan DARI HASIL YANG SUDAH DIFILTER.
    Ini adalah langkah krusial untuk meningkatkan presisi.
    """
    texts = []
    # Kata kunci utama dari nama produk untuk validasi (dibuat lowercase)
    # Contoh: "iPhone 14 Pro" -> ['iphone', '14', 'pro']
    main_keywords = [word.lower() for word in product_name.split() if len(word) > 2]
    # Kata kunci negatif untuk memfilter setiap hasil individu
    negative_keywords = ['baru', 'bnib', 'resmi', 'official', 'store', 'casing', 'charger', 'aksesoris', 'sewa', 'rental']

    for result in serpapi_data.get('organic_results', []):
        title = result.get('title', '').lower()
        snippet = result.get('snippet', '').lower()
        full_text = title + " " + snippet

        # --- LOGIKA FILTER ---
        # 1. Cek apakah mengandung kata kunci negatif
        if any(neg_word in full_text for neg_word in negative_keywords):
            continue # Lewati hasil ini jika mengandung kata kunci negatif

        # 2. Cek apakah mengandung SEMUA kata kunci utama (validasi dasar)
        if not all(main_word in full_text for main_word in main_keywords):
             continue # Lewati jika tidak mengandung kata kunci utama

        # Jika lolos filter, tambahkan title dan snippet ke konteks
        texts.append(result.get('title', ''))
        texts.append(result.get('snippet', ''))

    # Tambahkan juga "related questions" karena seringkali informatif
    for question in serpapi_data.get('related_questions', []):
        texts.append(question.get('question', ''))
        texts.append(question.get('snippet', ''))

    return "\n".join(filter(None, texts))


def extract_prices_from_text(text):
    """Fungsi untuk mengekstrak harga dari teks menggunakan regex"""
    # Regex ini lebih toleran terhadap format seperti Rp1.500.000 atau Rp 1.500.000
    price_pattern = r'Rp\s*\.?\s*(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)'
    prices = []
    matches = re.findall(price_pattern, text)
    for match in matches:
        # Membersihkan format angka sebelum konversi
        price_str = match.replace('.', '').replace(',', '.')
        try:
            price = float(price_str)
            # Filter harga yang tidak masuk akal (misal: di bawah 1000)
            if price > 1000:
                prices.append(price)
        except ValueError:
            continue
    return prices


# ⭐ PERUBAHAN DISARANKAN: Prompt LLM yang lebih tegas dan spesifik
def analyze_with_llm(context_text, product_name, api_key):
    """Mengirim teks yang sudah diproses ke OpenRouter untuk dianalisis."""
    llm_model = st.secrets.get("LLM_MODEL")
    prompt = f"""
    Anda adalah asisten ahli analisis harga barang bekas yang bekerja di sebuah balai lelang digital LEGOAS. Tugas Anda adalah menganalisis KONTEKS PENCARIAN yang SUDAH DIFILTER berikut untuk menemukan harga pasaran wajar.

    PRODUK YANG DICARI: "{product_name}"

    KONTEKS PENCARIAN (hanya berisi hasil yang relevan):
    ---
    {context_text[:15000]}
    ---

    INSTRUKSI UTAMA:
    1.  Fokus utama Anda adalah pada PRODUK YANG DICARI. Abaikan secara TEGAS semua penyebutan harga untuk produk lain, bahkan jika modelnya mirip (misal: jika mencari "iPhone 14 Pro", abaikan harga "iPhone 14 Pro Max").
    2.  Abaikan juga semua harga yang jelas-jelas untuk aksesoris (seperti casing, charger), suku cadang, atau jasa perbaikan.
    3.  Berdasarkan data yang paling relevan dalam konteks, berikan analisis singkat mengenai kondisi pasar dan variasi harga yang Anda temukan.
    4.  Berikan satu **rekomendasi harga jual wajar** untuk produk tersebut dalam kondisi bekas layak pakai. Jelaskan secara singkat alasan di balik angka rekomendasi Anda (misal: "berdasarkan beberapa iklan yang menawarkan di kisaran X hingga Y").
    5.  Gaya bahasa Anda harus profesional, jelas, dan informatif.
    6.  JAWABAN HARUS DALAM BENTUK TEKS BIASA (PARAGRAF NARASI), BUKAN JSON.

    JANGAN GUNAKAN FORMAT JSON.
    """
    try:
        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            data=json.dumps({
                "model": llm_model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 800,
                "temperature": 0.2 # Temperature lebih rendah untuk jawaban lebih konsisten
            })
        )
        response.raise_for_status()
        response_data = response.json()
        if 'error' in response_data:
            st.error("API OpenRouter mengembalikan error:")
            st.json(response_data)
            return None
        return response_data['choices'][0]['message']['content']

    except requests.exceptions.RequestException as e:
        st.error(f"Gagal menghubungi OpenRouter API: {e}")
        if e.response is not None:
            st.json(e.response.json())
        return None
    except (KeyError, IndexError) as e:
        st.error(f"Gagal mengolah respons dari AI: {e}")
        st.json(response.json())
        return None

# --- BAGIAN 3: UI STREAMLIT (Tidak ada perubahan signifikan) ---
# Kode UI Anda sudah bagus dan tidak perlu diubah.
# ... (Salin dan tempel BAGIAN 3 dari skrip asli Anda di sini) ...
st.set_page_config(page_title="Price Analyzer", layout="wide")
st.title("💡 AI Price Analyzer")
st.write("Aplikasi untuk menganalisis harga pasaran barang bekas menggunakan AI.")

st.sidebar.header("Pengaturan Pencarian")
# Tambahkan "Alat Berat" ke dalam list
category = st.sidebar.selectbox(
    "1. Pilih Jenis Pencarian",
    ["Barang Bermerek", "Barang Umum", "Scrap", "Alat Berat"]
)
time_filter_options = {"Semua Waktu": "Semua Waktu", "Setahun Terakhir": "qdr:y", "Sebulan Terakhir": "qdr:m", "Seminggu Terakhir": "qdr:w"}
selected_time_filter = st.sidebar.selectbox("2. Filter Waktu", options=list(time_filter_options.keys()))
time_filter_value = time_filter_options[selected_time_filter]

if category == "Barang Bermerek":
    st.sidebar.subheader("Filter Lanjutan")
    use_condition_filter = st.sidebar.checkbox("Filter Kondisi (BNIB, dll.)", value=True)
    use_url_filter = st.sidebar.checkbox("Filter URL (search, shop)", value=True)
else:
    use_condition_filter, use_url_filter = False, False

with st.form("main_form"):
    if category == "Barang Bermerek":
        st.header("📱 Detail Barang Bermerek")
        brand = st.text_input("Merek", "Apple")
        model = st.text_input("Model / Seri", "iPhone 14 Pro")
        spec = st.text_input("Spesifikasi (Opsional)", "256GB")
        exclusions = st.text_input("Kecualikan Varian (pisahkan koma)", "Max, Plus, casing, charger") # Menambahkan contoh eksklusi
        product_name_display = f"{brand} {model} {spec}".strip()
    elif category == "Barang Umum":
        st.header("📦 Detail Barang Umum")
        keywords = st.text_input("Masukkan Nama Barang", "Bonsai Cemara Udang Ukuran Medium")
        product_name_display = keywords
    elif category == "Alat Berat":
        st.header("🛠️ Detail Alat Berat")
        alat_type = st.text_input("Jenis Alat", "Excavator")
        brand = st.text_input("Merek", "Komatsu")
        model = st.text_input("Model / Kapasitas", "PC200-8")
        year = st.text_input("Tahun (Wajib)", "2015")
        product_name_display = f"{alat_type} {brand} {model} {year}".strip()
    elif category == "Scrap":
        st.header("♻️ Detail Limbah (Scrap)")
        scrap_options = ["Besi Tua", "Tembaga", "Aluminium", "Kuningan", "Aki Bekas", "Minyak Jelantah", "Oli Bekas", "Kardus Bekas", "Botol Plastik PET"]
        scrap_type = st.selectbox("Pilih Jenis Limbah", scrap_options)
        unit_options = ["per kg", "per liter", "per drum", "per unit"]
        unit = st.selectbox("Pilih Satuan Harga", unit_options)
        product_name_display = f"{scrap_type} ({unit})"

    submitted = st.form_submit_button("Analisis Harga Sekarang!")


# --- ⭐ PERUBAHAN DISARANKAN: ALUR KERJA UTAMA DENGAN LANGKAH FILTERING ---
if submitted:
    SERPAPI_API_KEY = st.secrets.get("SERPAPI_API_KEY")
    OPENROUTER_API_KEY = st.secrets.get("OPENROUTER_API_KEY")
    LLM_MODEL = st.secrets.get("LLM_MODEL")

    if not SERPAPI_API_KEY or not OPENROUTER_API_KEY or not LLM_MODEL:
        st.error("Harap konfigurasikan SERPAPI_API_KEY, OPENROUTER_API_KEY, dan LLM_MODEL di Streamlit Secrets!")
    else:
        # Bangun Query
        params = {}
        if category == "Barang Bermerek":
            params = build_branded_query(brand, model, spec, exclusions, time_filter_value, use_condition_filter, use_url_filter)
        elif category == "Barang Umum":
            params = build_common_query(keywords, time_filter_value)
        elif category == "Alat Berat":
            params = build_heavy_equipment_query(alat_type, brand, model, year, time_filter_value)
        elif category == "Scrap":
            params = build_scrap_query(scrap_type, unit, time_filter_value)

        with st.spinner(f"Menganalisis harga untuk '{product_name_display}'... Proses ini bisa memakan waktu 10-20 detik."):
            # Langkah 1: Panggil SerpApi
            st.info("Langkah 1/4: Mengambil data pencarian dari API...")
            serpapi_data = search_with_serpapi(params, SERPAPI_API_KEY)

            if serpapi_data:
                # Langkah 2: FILTER hasil pencarian
                st.info("Langkah 2/4: Memfilter hasil pencarian untuk akurasi...")
                # Ganti extract_text_for_llm dengan fungsi baru kita
                context_text = filter_and_extract_text_for_llm(serpapi_data, product_name_display)

                if context_text:
                    # Langkah 3: Panggil OpenRouter (AI)
                    st.info("Langkah 3/4: Mengirim data bersih ke AI untuk analisis harga...")
                    ai_analysis = analyze_with_llm(context_text, product_name_display, OPENROUTER_API_KEY)

                    if ai_analysis:
                        # Langkah 4: Tampilkan Hasil
                        st.info("Langkah 4/4: Menyiapkan laporan hasil analisis...")
                        st.balloons()
                        st.success("Analisis Harga Selesai!")
                        st.subheader(f"📊 Analisis AI LEGOAS untuk Harga {product_name_display}")

                        st.markdown("### Rekomendasi & Analisis AI")
                        st.write(ai_analysis)

                        # Ekstraksi harga dari teks yang sudah difilter
                        extracted_prices = extract_prices_from_text(context_text)
                        if extracted_prices:
                            st.markdown("### Statistik Harga dari Data Relevan")
                            harga_rata_rata = np.mean(extracted_prices)
                            harga_median = np.median(extracted_prices)
                            harga_terendah = np.min(extracted_prices)
                            harga_tertinggi = np.max(extracted_prices)

                            col1, col2, col3, col4 = st.columns(4)
                            col1.metric("Harga Rata-rata", f"Rp {int(harga_rata_rata):,}")
                            col2.metric("Harga Tengah (Median)", f"Rp {int(harga_median):,}")
                            col3.metric("Harga Terendah", f"Rp {int(harga_terendah):,}")
                            col4.metric("Harga Tertinggi", f"Rp {int(harga_tertinggi):,}")

                            st.markdown("### Distribusi Harga")
                            st.bar_chart(extracted_prices)
                        else:
                            st.warning("Tidak ditemukan data harga numerik yang relevan setelah proses filtering.")
                    else:
                        st.error("Analisis Gagal: Tidak menerima respons dari AI.")
                else:
                    st.error("Ekstraksi Teks Gagal: Tidak ada hasil pencarian yang relevan ditemukan setelah filtering. Coba perlebar kriteria pencarian Anda.")
            else:
                st.error("Pengambilan Data Gagal: Tidak menerima data dari SerpAPI.")
