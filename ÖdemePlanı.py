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

        # Dosya buffer'ını sıfırla (birden fazla okuma için)
        uploaded_file.seek(0)
        
        # --- A. Metadata Okuma (İlk 3 Satır) ---
        # Dosyanın ilk 3 satırından A ve B sütunlarını (index 0 ve 1) oku
        metadata_df = pd.read_csv(
            uploaded_file,
            header=None,       # Başlık satırı yok
            nrows=3,           # Sadece ilk 3 satırı oku
            usecols=[0, 1],    # Sadece ilk iki sütunu al
            encoding='utf-8'   # Türkçe karakterler için
        )
        
        # Okunan metadatayı bir sözlük (dictionary) yapısına çevir
        # { 'Başlangıç': '2025-02-01', ... }
        metadata = metadata_df.set_index(0)[1].to_dict()

        # --- B. Ana Veri Tablosunu Okuma ---
        # Dosya buffer'ını tekrar sıfırla
        uploaded_file.seek(0)
        
        # Asıl tablo 6. satırda başlıyor (0'dan sayınca)
        # 7. satır başlık (header) oluyor, bu yüzden skiprows=6
        df = pd.read_csv(
            uploaded_file,
            skiprows=6,        # İlk 6 satırı atla
            index_col=0,       # İlk sütunu (1, 2, 3, 4) index yap
            encoding='utf-8',
            decimal='.',       # Ondalık ayıracı
            thousands=None     # Binlik ayıracı yok
        )

        # --- 3. Veri Temizleme ve Dönüştürme ---
        
        # Metadatadan gelen değerleri al ve doğru tiplere dönüştür
        baslangic_tarihi_str = metadata.get('Başlangıç')
        toplam_prim = pd.to_numeric(metadata.get('Toplam Prim'))
        taksit_sayisi = pd.to_numeric(metadata.get('Taksit Sayısı'))
        baslangic_tarihi = pd.to_datetime(baslangic_tarihi_str)

        # Ana DataFrame'deki sütunları sayısal değerlere dönüştür
        # Hata olursa zorlama (errors='coerce'), bu sayede hatalı veri varsa NaN olur
        df['Taksit Tutarı'] = pd.to_numeric(df['Taksit Tutarı'], errors='coerce')
        df['Min.'] = pd.to_numeric(df['Min.'], errors='coerce')
        df['Tam'] = pd.to_numeric(df['Tam'], errors='coerce')
        df['Max'] = pd.to_numeric(df['Max'], errors='coerce')

        # --- 4. Arayüzü Oluşturma (Streamlit UI) ---

        st.header("Poliçe Özeti")
        
        # Özeti 3 sütunda göster
        col1, col2, col3 = st.columns(3)
        col1.metric("Toplam Prim", f"{toplam_prim:,.2f} TL")
        col2.metric("Taksit Sayısı", int(taksit_sayisi))
        col3.metric("Başlangıç Tarihi", baslangic_tarihi.strftime('%d-%m-%Y'))

        st.subheader("Orijinal Taksit Planı Verileri")
        # DataFrame'i formatlayarak göster
        st.dataframe(df.style.format({
            "Taksit Tutarı": "{:,.2f} TL",
            "Taksit Yüzdesi": "{:.0%}"
        }))

        # --- 5. Etkileşimli Plan Seçimi ---

        st.header("Ödeme Planı Simülatörü")
        
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
        
        # Seçilen plana göre ilgili sütun adını al (örn: "Min.")
        secilen_sutun = plan_mapping[secilen_plan_adi]
        
        # --- 6. Hesaplama ve Sonuçları Gösterme ---

        # Sonuçları göstermek için yeni bir DataFrame oluştur
        plan_df = pd.DataFrame(index=df.index)
        plan_df['Taksit Tutarı'] = df['Taksit Tutarı'].copy()
        
        # Seçilen plandaki gün farkını 'timedelta' objesine çevir
        # Örn: 89 -> 89 gün
        gun_farki = pd.to_timedelta(df[secilen_sutun], unit='D')
        
        # Yeni ödeme tarihini hesapla: Başlangıç Tarihi + Gün Farkı
        plan_df['Hesaplanan Ödeme Tarihi'] = (baslangic_tarihi + gun_farki)
        
        # 'Tam' plana göre ne kadar erken/geç olduğunu hesapla
        plan_df['Fark (Güne Göre)'] = df[secilen_sutun] - df['Tam']
        
        st.subheader(f"'{secilen_plan_adi}' Planına Göre Hesaplanan Tarihler")
        
        # Hesaplanan yeni planı formatlayarak göster
        st.dataframe(plan_df.style.format({
            "Taksit Tutarı": "{:,.2f} TL",
            "Hesaplanan Ödeme Tarihi": lambda dt: dt.strftime('%d-%m-%Y') # Tarih formatı
        }))
        
        # Ek bir bilgi notu
        ortalama_fark = plan_df['Fark (Güne Göre)'].mean()
        if ortalama_fark < 0:
            st.info(f"Bu plan, 'Tam Zamanında' plana göre taksit başı ortalama {abs(ortalama_fark):.1f} gün **erken** ödeme yapmanızı sağlar.")
        elif ortalama_fark > 0:
            st.info(f"Bu plan, 'Tam Zamanında' plana göre taksit başı ortalama {ortalama_fark:.1f} gün **geç** ödeme yapmanızı sağlar.")
        else:
            st.info("Bu, 'Tam Zamanında' planıdır.")

    except Exception as e:
        # Hata olması durumunda kullanıcıyı bilgilendir
        st.error(f"Dosya okunurken bir hata oluştu: {e}")
        st.warning("Lütfen yüklediğiniz dosyanın formatının örnekteki gibi olduğundan emin olun.")
        st.code(
            """
            Örnek CSV Formatı:
            
            Başlangıç,2025-02-01,,,,,
            Taksit Sayısı,4,,,,,
            Toplam Prim,100000,,,,,
            (Boş Satır)
            (Boş Satır)
            (Boş Satır)
            ,Taksit Tutarı,Ödeme Tarihi,Min.,Tam,Max,Taksit Yüzdesi
            1,25000,2025-05-10,89,98,119,0.25
            2,25000,2025-07-10,150,159,180,0.25
            ...
            """,
            language="text"
        )

else:
    # Dosya yüklenmediyse bilgilendirme mesajı göster
    st.info("Lütfen başlamak için bir CSV dosyası yükleyin.")
