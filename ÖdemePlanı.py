import streamlit as st
import requests
from bs4 import BeautifulSoup
import re

def fetch_ad_details(url):
    """
    Verilen sahibinden.com URL'sinden ilan detaylarını çekmeyi dener.
    """
    try:
        # Sahibinden.com'un bot engellemesini aşmak için bir tarayıcı gibi davranıyoruz.
        # 403 Hatasını (Forbidden) aşmak için User-Agent ve diğer başlıkları güncelledik.
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36',
            'Accept-Language': 'tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Referer': 'https://www.sahibinden.com/', # Nereden geldiğimizi belirtmek (ana sayfa)
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1', # HTTPS'e yükseltme talebi
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status() # Hata varsa (404, 500 vb.) yakala
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        details = {
            "title": "Bulunamadı",
            "price": "Bulunamadı",
            "plate": None,
            "painted": [],
            "replaced": [],
            "description": "Açıklama bulunamadı."
        }

        # İlan Başlığı
        title_tag = soup.find('h1', class_='classifiedDetailTitle')
        if title_tag:
            details['title'] = title_tag.get_text(strip=True)
            
        # Fiyat
        price_tag = soup.find('div', class_='classifiedInfo').find('h3')
        if price_tag:
            details['price'] = price_tag.get_text(strip=True).replace('TL', '').strip() + " TL"
            
        # Plaka (Genellikle "Teknik Özellikler" veya "Özellikler" listesinde olur)
        # Bazen satıcılar plakayı "Belirtilmemiş" olarak girer veya hiç girmez.
        properties_list = soup.select('div.classifiedProperties ul li')
        
        for item in properties_list:
            strong_tag = item.find('strong')
            if strong_tag and 'Plaka' in strong_tag.get_text():
                span_tag = item.find('span')
                if span_tag:
                    plate_text = span_tag.get_text(strip=True)
                    # "Belirtilmemiş", "Yabancı Plaka" gibi durumları filtrele
                    if plate_text and "Belirtilmemiş" not in plate_text and "Yabancı" not in plate_text:
                        # Plakayı temizle (örn: 34 ABC 123 -> 34ABC123)
                        details['plate'] = re.sub(r'\s+', '', plate_text).upper()
                        break

        # --- YENİ BÖLÜM: Boya/Değişen ve Açıklama ---
        
        # 1. Boya & Değişen Bilgisi
        # Sahibinden'in yapısı: <h3>Boya & Değişen</h3>, sonra <ul><li><h4>Boyalı..</h4><ul><li>...</li></ul></li><li><h4>Değişen..</h4><ul>...</ul></li></ul>
        paint_header = soup.find('h3', string=re.compile(r'Boya & Değişen'))
        if paint_header:
            main_ul = paint_header.find_next_sibling('ul')
            if main_ul:
                # Boyalı Parçalar
                boyali_li = main_ul.find('h4', string=re.compile(r'Boyalı Parçalar'))
                if boyali_li:
                    boyali_ul = boyali_li.find_next_sibling('ul')
                    if boyali_ul:
                        selected = boyali_ul.find_all('li', class_='selected')
                        details['painted'] = [li.get_text(strip=True) for li in selected]

                # Değişen Parçalar
                degisen_li = main_ul.find('h4', string=re.compile(r'Değişen Parçalar'))
                if degisen_li:
                    degisen_ul = degisen_li.find_next_sibling('ul')
                    if degisen_ul:
                        selected = degisen_ul.find_all('li', class_='selected')
                        details['replaced'] = [li.get_text(strip=True) for li in selected]

        if not details['painted']:
            details['painted'] = ["Satıcı tarafından belirtilmemiş."]
        if not details['replaced']:
            details['replaced'] = ["Satıcı tarafından belirtilmemiş."]

        # 2. İlan Açıklaması
        description_div = soup.find('div', id='classifiedDescription')
        if description_div:
            # Metni al ve gereksiz boşlukları temizle
            details['description'] = ' '.join(description_div.get_text(strip=True).split())
        
        # --- BİTİŞ: Yeni Bölüm ---
                        
        return details

    except requests.exceptions.RequestException as e:
        st.error(f"İlana ulaşılamadı. Sahibinden.com erişimi engellemiş olabilir veya link hatalı. Hata: {e}")
        return None
    except Exception as e:
        st.error(f"Veri ayrıştırılırken bir hata oluştu: {e}")
        return None

# --- Streamlit Arayüzü ---

st.set_page_config(layout="wide", page_title="Sahibinden İlan Yardımcısı")

st.title("🚗 Sahibinden İlan Yardımcısı")
st.markdown("---")

st.info(
    "**ÖNEMLİ UYARI:** Bu uygulama, satıcının ilana girdiği **beyanları** (işaretlediği boya/değişen durumu) ve **ilan açıklamasını** çeker."
    "\n\nBu bilgiler satıcının kendi girdiği bilgilerdir, **resmi kayıt DEĞİLDİR**."
    "\nResmi Hasar Kaydı (TRAMER) sorgusu için plakayı alıp **5664**'e SMS atmanız (ücretli) gerekir."
)

st.markdown("### 1. Adım: İlan Linkini Yapıştırın")
url = st.text_input("Sahibinden.com araç ilanının tam URL'sini buraya yapıştırın:", placeholder="https://www.sahibinden.com/ilan/...")

if st.button("İlan Bilgilerini Getir", type="primary"):
    if not url or "sahibinden.com" not in url:
        st.warning("Lütfen geçerli bir sahibinden.com ilanı URL'si girin.")
    else:
        with st.spinner("İlan bilgileri getiriliyor..."):
            details = fetch_ad_details(url)
            st.session_state.details = details # Detayları oturumda sakla

if 'details' in st.session_state and st.session_state.details:
    details = st.session_state.details
    
    st.markdown("---")
    st.subheader("İlandan Alınan Bilgiler")
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric(label="İlan Başlığı", value=details['title'])
    with col2:
        st.metric(label="Fiyat", value=details['price'])

    # --- YENİ BÖLÜM: Satıcı Beyanı ---
    st.markdown("---")
    st.subheader("Satıcının Boya/Değişen Beyanı (İlanda İşaretledikleri)")
    
    col_boya, col_degisen = st.columns(2)
    
    with col_boya:
        st.write("🎨 **Boyalı Parçalar**")
        if details['painted'] and details['painted'][0] != "Satıcı tarafından belirtilmemiş.":
            # Liste olarak göster
            st.markdown('\n'.join(f'- {p}' for p in details['painted']))
        else:
            st.info("Satıcı boyalı parça belirtmemiş.")
            
    with col_degisen:
        st.write("🛠️ **Değişen Parçalar**")
        if details['replaced'] and details['replaced'][0] != "Satıcı tarafından belirtilmemiş.":
            # Liste olarak göster
            st.markdown('\n'.join(f'- {p}' for p in details['replaced']))
        else:
            st.info("Satıcı değişen parça belirtmemiş.")

    # --- YENİ BÖLÜM: İlan Açıklaması ---
    st.markdown("---")
    st.subheader("İlan Açıklaması Analizi")
    
    desc_lower = details['description'].lower()
    # "kaydı" kelimesini ekleyerek "hasar kaydı" tamlamasını daha iyi yakalayabiliriz
    damage_keywords = ['tramer', 'hasar kaydı', 'hasar', 'kaydı', 'boyalı', 'değişen', 'lokal', 'çizik', 'kaza', 'boya', 'değişim']
    # Tekrar eden kelimeleri kaldır
    found_keywords = sorted(list(set([k for k in damage_keywords if k in desc_lower])))
    
    if found_keywords:
        st.write("**Açıklamada Bulunan Hasar/Boya İlgili Anahtar Kelimeler:**")
        # Kelimeleri daha okunaklı göster
        st.warning(f"`{', '.join(found_keywords)}`")
    else:
        st.success("**Açıklamada Hasar Belirten Anahtar Kelime Bulunmadı.**")
        
    with st.expander("Açıklamanın tamamını görmek için tıklayın..."):
        st.info(details['description'])


    st.markdown("---")
    st.markdown("### 2. Adım: Resmi Hasar Kaydı (TRAMER) Sorgusu")
    st.write("Yukarıdaki bilgiler satıcının beyanıdır. Doğrulamak için 5664'e SMS gönderebilirsiniz.")

    plate_to_query = None

    if details['plate']:
        st.success(f"**Plaka ilanda bulundu:** {details['plate']}")
        plate_to_query = details['plate']
    else:
        st.warning("Plaka ilanda bulunamadı, gizlenmiş veya 'Belirtilmemiş' olarak girilmiş.")
        st.write("Lütfen plakayı ilandaki fotoğraflardan veya satıcıdan alarak aşağıdaki kutuya manuel girin.")
        
    manual_plate = st.text_input("Plakayı Girin (Bitişik, örn: 34ABC1234)", 
                                 value=details['plate'] if details['plate'] else "",
                                 help="Plakayı bitişik olarak yazın.")
                                 
    if manual_plate:
        plate_to_query = re.sub(r'\s+', '', manual_plate).upper()

    if plate_to_query:
        st.markdown("---")
        st.subheader("Hazır SMS Metni")
        st.write("Aşağıdaki metnin tamamını kopyalayıp telefonunuzdan **5664**'e SMS olarak gönderin (Ücretlidir).")
        
        st.code(f"DETAY {plate_to_query}", language=None)
        
        st.write("Diğer sorgu türleri:")
        st.code(f"PARCA {plate_to_query} [Tarih (gg/aa/yyyy)]", language=None)
        st.code(f"SASENO [Şasi Numarası]", language=None)

