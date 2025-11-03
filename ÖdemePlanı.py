import streamlit as st
import pandas as pd
import io

# Sayfa yapılandırmasını ayarla
st.set_page_config(page_title="Ödeme Planı Simülatörü", layout="wide")

# Başlık
st.title("İnteraktif Ödeme Planı Simülatörü")

# 1. Dosya Yükleme Alanı
uploaded_file = st.file_uploader("Lütfen ödeme planı CSV dosyanızı buraya yükleyin:", type="csv")

# Dosya yüklendiyse devam et
if uploaded_file is not None:
    try:
        # --- 2. Veri Okuma ve İşleme ---

        # --- A. Metadata Okuma (Satır 2, 3, 4) ---
        # Dosya buffer'ını sıfırla
        uploaded_file.seek(0)
        # Veri, CSV'nin 2. satırından (index 1) başlıyor
        metadata_df = pd.read_csv(
            uploaded_file,
            header=None,       # Başlık satırı yok
            skiprows=1,        # İlk satırı (boş) atla
            nrows=3,           # 3 satır (Başlangıç, Taksit, Toplam) oku
            usecols=[0, 1],    # Sadece ilk iki sütunu al
            encoding='utf-8',  # Türkçe karakterler için
            engine='python'    # Hatalı satırları daha iyi işlemesi için
        )
        
        # Okunan metadatayı bir sözlük (dictionary) yapısına çevir
        # { 'Başlangıç': '2025-02-01', ... }
        metadata = metadata_df.set_index(0)[1].to_dict()

        # --- B. Ana Veri Tablosunu Okuma ---
        # Dosya buffer'ını tekrar sıfırla
        uploaded_file.seek(0)
        
        # Asıl tablo 6. satırda (index 5) başlıyor (başlık)
        df = pd.read_csv(
            uploaded_file,
            header=5,          # 6. satır (index 5) başlık satırıdır
            index_col=0,       # İlk sütunu (1, 2, 3, 4) index yap
            encoding='utf-8',
            decimal='.',
            thousands=None,
            engine='python'
        )

        # Okuduktan sonra, 'Unnamed' gibi istenmeyen sütunları kaldır
        df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
        # Tamamen NaN olan satırları (varsa) kaldır
        df.dropna(how='all', inplace=True)


        # --- 3. Veri Temizleme ve Dönüştürme ---
        
        # Metadatadan gelen değerleri al ve doğru tiplere dönüştür
        baslangic_tarihi_str = metadata.get('Başlangıç')
        toplam_prim = pd.to_numeric(metadata.get('Toplam Prim'))
        taksit_sayisi = pd.to_numeric(metadata.get('Taksit Sayısı'))
        baslangic_tarihi = pd.to_datetime(baslangic_tarihi_str)

        # Ana DataFrame'deki sütunları sayısal değerlere dönüştür
        df['Taksit Tutarı'] = pd.to_numeric(df['Taksit Tutarı'], errors='coerce')
        df['Min.'] = pd.to_numeric(df['Min.'], errors='coerce')
        df['Tam'] = pd.to_numeric(df['Tam'], errors='coerce')
        df['Max'] = pd.to_numeric(df['Max'], errors='coerce')
        if 'Taksit Yüzdesi' in df.columns:
            df['Taksit Yüzdesi'] = pd.to_numeric(df['Taksit Yüzdesi'], errors='coerce')

        # Tüm olası ödeme tarihlerini en başta hesapla
        min_gun_farki = pd.to_timedelta(df['Min.'], unit='D')
        tam_gun_farki = pd.to_timedelta(df['Tam'], unit='D')
        max_gun_farki = pd.to_timedelta(df['Max.'], unit='D')
        
        df['Min. Ödeme Tarihi'] = (baslangic_tarihi + min_gun_farki)
        df['Tam Ödeme Tarihi'] = (baslangic_tarihi + tam_gun_farki)
        df['Max. Ödeme Tarihi'] = (baslangic_tarihi + max_gun_farki)

        # --- 4. Arayüzü Oluşturma (Streamlit UI) ---

        st.header("Poliçe Özeti ve Ödeme Simülatörü")
        
        # Özeti Excel'e benzer şekilde (Başlık - Değer) göster
        col1, col2, col3 = st.columns([1, 2, 3]) # Sütun genişlikleri
        with col1:
            st.markdown("---") # Ayırıcı
            st.markdown(f"**Başlangıç Tarihi:**")
            st.markdown(f"**Taksit Sayısı:**")
            st.markdown(f"**Toplam Prim:**")
            st.markdown("---") # Ayırıcı
        with col2:
            st.markdown("---") # Ayırıcı
            st.markdown(f"{baslangic_tarihi.strftime('%d-%m-%Y')}")
            st.markdown(f"{int(taksit_sayisi)}")
            st.markdown(f"{toplam_prim:,.2f} TL")
            st.markdown("---") # Ayırıcı

        # --- 5. Etkileşimli Plan Seçimi ---
        
        st.subheader("Ödeme Planı Seçimi")
        
        # Seçenekleri ve karşılık gelen sütun adlarını eşleştir
        plan_mapping = {
            "Minimum (En Erken)": "Min.",
            "Tam Zamanında": "Tam",
            "Maksimum (En Geç)": "Max"
        }
        
        # Kullanıcıdan plan seçmesini iste (radio button)
        secilen_plan_adi = st.radio(
            "Hangi ödeme planını görmek istersiniz?",
            options=plan_mapping.keys(), # Seçenekler: "Minimum", "Tam Zamanında", ...
            horizontal=True,
            key="plan_secimi"
        )
        
        # Seçilen plana göre ilgili sütun adlarını al
        secilen_sutun_gun = plan_mapping[secilen_plan_adi] # "Min.", "Tam" veya "Max"
        secilen_sutun_tarih = f"{secilen_sutun_gun} Ödeme Tarihi" # "Min. Ödeme Tarihi", ...
        
        # --- 6. Hesaplama ve Sonuçları Gösterme ---

        # Gösterilecek DataFrame'i oluştur
        gosterilecek_df = pd.DataFrame(index=df.index)
        gosterilecek_df['Taksit Tutarı'] = df['Taksit Tutarı']
        if 'Taksit Yüzdesi' in df.columns:
            gosterilecek_df['Taksit Yüzdesi'] = df['Taksit Yüzdesi']
        
        # Orijinal 'Tam' plana göre tarihi ekle (Excel'deki 'Ödeme Tarihi' sütunu)
        gosterilecek_df['Varsayılan Vade (Tam)'] = df['Tam Ödeme Tarihi']
        
        # Seçilen plana göre sütunları ekle
        gosterilecek_df[f'Seçilen Plan ({secilen_sutun_gun}) - Gün'] = df[secilen_sutun_gun]
        gosterilecek_df['Hesaplanan Vade'] = df[secilen_sutun_tarih]
        
        # 'Tam' plana göre fark
        gosterilecek_df['Vade Farkı (Gün)'] = df[secilen_sutun_gun] - df['Tam']

        st.subheader(f"'{secilen_plan_adi}' Planına Göre Ödeme Tablosu")
        
        # Stilleri ve formatı tanımla
        format_dict = {
            "Taksit Tutarı": "{:,.2f} TL",
            "Taksit Yüzdesi": "{:.0%}",
            "Varsayılan Vade (Tam)": lambda dt: dt.strftime('%d-%m-%Y'),
            f'Seçilen Plan ({secilen_sutun_gun}) - Gün': "{:.0f}",
            "Hesaplanan Vade": lambda dt: dt.strftime('%d-%m-%Y'),
            "Vade Farkı (Gün)": "{:+.0f}" # Artı/eksi işaretiyle göster
        }

        # Sadece 'Taksit Yüzdesi' varsa formatlamaya dahil et
        if 'Taksit Yüzdesi' not in gosterilecek_df.columns:
            del format_dict['Taksit Yüzdesi']

        # DataFrame'i formatlayarak göster
        st.dataframe(gosterilecek_df.style.format(format_dict))
        
        # Ek bir bilgi notu
        ortalama_fark = gosterilecek_df['Vade Farkı (Gün)'].mean()
        if ortalama_fark < 0:
            st.info(f"Bu plan, 'Tam Zamanında' plana göre taksit başı ortalama {abs(ortalama_fark):.1f} gün **erken** ödeme yapmanızı sağlar.")
        elif ortalama_fark > 0:
            st.info(f"Bu plan, 'Tam Zamanında' plana göre taksit başı ortalama {ortalama_fark:.1f} gün **geç** ödeme yapmanızı sağlar.")
        else:
            st.info("Bu, 'Tam Zamanında' planıdır.")

    except Exception as e:
        # Hata olması durumunda kullanıcıyı bilgilendir
        st.error(f"Dosya okunurken veya işlenirken bir hata oluştu: {e}")
        st.warning("Lütfen yüklediğiniz dosyanın formatının beklenen yapıda olduğundan emin olun.")
        st.exception(e) # Detaylı hata dökümü için

else:
    # Dosya yüklenmediyse bilgilendirme mesajı göster
    st.info("Lütfen başlamak için bir CSV dosyası yükleyin.")

