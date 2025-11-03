import streamlit as st
import pandas as pd
import io
from datetime import datetime
from dateutil.relativedelta import relativedelta

def parse_file(uploaded_file):
    """
    Yüklenen CSV dosyasını okur, metadata'yı ve ana tabloyu ayıklar.
    """
    try:
        content = uploaded_file.getvalue().decode("utf-8")
        lines = content.splitlines()
        
        # 1. Metadata'yı (Başlık Bilgileri) Oku
        metadata = {}
        metadata['Baslangic'] = datetime.strptime(lines[1].split(',')[1], '%Y-%m-%d').date()
        metadata['Taksit Sayisi'] = int(lines[2].split(',')[1])
        metadata['Toplam Prim'] = float(lines[3].split(',')[1])
        
        # 2. Ana Tabloyu (DataFrame) Oku
        # 7. satır başlıklar (index 6), veriler 8. satırda (index 7) başlıyor
        table_content = "\n".join(lines[6:])
        
        # İlk sütunu (taksit no) index olarak kullan
        df = pd.read_csv(io.StringIO(table_content), index_col=0)
        
        # Ödeme Tarihi sütununu datetime formatına çevir
        df['Ödeme Tarihi'] = pd.to_datetime(df['Ödeme Tarihi'])
        
        return metadata, df
    except Exception as e:
        st.error(f"Dosya okunurken bir hata oluştu: {e}")
        st.error("Lütfen dosya formatınızın örnektekiyle aynı olduğundan emin olun.")
        return None, None

def recalculate_plan(toplam_prim, taksit_sayisi, ilk_odeme_tarihi, odeme_araligi_ay):
    """
    Verilen parametrelere göre ödeme planı tablosunu yeniden oluşturur.
    """
    new_data = []
    
    # Eşit taksit tutarını ve yüzdeyi hesapla
    taksit_tutari = round(toplam_prim / taksit_sayisi, 2)
    taksit_yuzdesi = 1 / taksit_sayisi
    
    current_date = ilk_odeme_tarihi
    
    for i in range(1, taksit_sayisi + 1):
        new_data.append({
            'Taksit Tutarı': taksit_tutari,
            'Ödeme Tarihi': current_date,
            'Min.': 0,  # Bu alanların mantığı bilinmediği için sıfırlandı
            'Tam': 0,
            'Max': 0,
            'Taksit Yüzdesi': taksit_yuzdesi
        })
        # Bir sonraki ödeme tarihini hesapla
        current_date = current_date + relativedelta(months=odeme_araligi_ay)
        
    # Yeni DataFrame'i oluştur (index 1'den başlasın)
    new_df = pd.DataFrame(new_data, index=pd.RangeIndex(start=1, stop=taksit_sayisi+1))
    new_df.index.name = "Taksit No"
    
    # 'Ödeme Tarihi' sütununun formatını düzelt (sadece tarih)
    new_df['Ödeme Tarihi'] = pd.to_datetime(new_df['Ödeme Tarihi']).dt.date
    
    return new_df

# --- Streamlit Uygulaması ---

st.set_page_config(layout="wide")
st.title("📊 İnteraktif Ödeme Planı Düzenleyici")

# 1. Dosya Yükleme
uploaded_file = st.file_uploader("Ödeme Planı CSV/Excel Dosyanızı Yükleyin", type=["csv"])

if uploaded_file is not None:
    
    # Dosya her yüklendiğinde veya değiştiğinde state'i sıfırla
    if 'current_file_name' not in st.session_state or st.session_state.current_file_name != uploaded_file.name:
        st.session_state.current_file_name = uploaded_file.name
        metadata, df = parse_file(uploaded_file)
        if metadata and df is not None:
            st.session_state.metadata = metadata
            st.session_state.df = df # Düzenlenecek ana DataFrame
            st.success(f"'{uploaded_file.name}' başarıyla yüklendi ve ayrıştırıldı.")
        else:
            # Hata durumunda state'i temizle
            if 'df' in st.session_state:
                del st.session_state.df
    
    # Veri başarıyla yüklendiyse devam et
    if 'df' in st.session_state:
        
        st.header("Planı Yeniden Hesapla")
        st.markdown("Aşağıdaki değerleri değiştirip 'Planı Güncelle' butonuna basarak tabloyu yeniden oluşturabilirsiniz.")
        
        # Ayar girişleri için sütunlar
        col1, col2, col3, col4 = st.columns(4)
        
        # Dosyadan okunan değerleri varsayılan olarak ata
        with col1:
            toplam_prim = st.number_input(
                "Toplam Prim", 
                value=st.session_state.metadata['Toplam Prim']
            )
        with col2:
            taksit_sayisi = st.number_input(
                "Taksit Sayısı", 
                min_value=1, 
                step=1, 
                value=st.session_state.metadata['Taksit Sayisi']
            )
        with col3:
            # Dosyadaki ilk ödeme tarihini varsayılan al
            ilk_odeme_varsayilan = st.session_state.df.iloc[0]['Ödeme Tarihi'].date()
            ilk_odeme_tarihi = st.date_input(
                "İlk Ödeme Tarihi", 
                value=ilk_odeme_varsayilan
            )
        with col4:
            # Dosyadan ödeme aralığını tahmin et (ör: 2 ay)
            odeme_araligi = st.number_input(
                "Ödeme Aralığı (Ay)", 
                min_value=1, 
                step=1, 
                value=2 # Örnek dosyanıza göre (Mayıs -> Temmuz)
            )

        # Planı güncelleme butonu
        if st.button("🔄 Planı Güncelle", type="primary", use_container_width=True):
            new_df = recalculate_plan(toplam_prim, taksit_sayisi, ilk_odeme_tarihi, odeme_araligi)
            st.session_state.df = new_df # State'deki DataFrame'i güncelle
            st.success("Ödeme planı başarıyla güncellendi!")

        st.divider()
        
        # 2. İnteraktif Tablo (Data Editor)
        st.header("📝 Ödeme Planı Tablosu (Doğrudan Düzenleyin)")
        st.info("Bu tabloyu Excel gibi çift tıklayarak düzenleyebilir, satır ekleyebilir veya silebilirsiniz.")

        # st.data_editor, kullanıcıya tabloyu düzenleme imkanı verir.
        # Yapılan değişiklikler 'edited_df' değişkenine atanır.
        edited_df = st.data_editor(
            st.session_state.df,
            num_rows="dynamic", # Satır ekleme/silmeyi etkinleştir
            use_container_width=True,
            column_config={
                "Ödeme Tarihi": st.column_config.DateColumn(
                    "Ödeme Tarihi",
                    format="YYYY-MM-DD",
                ),
                "Taksit Tutarı": st.column_config.NumberColumn(
                    "Taksit Tutarı",
                    format="%.2f ₺",
                ),
                "Taksit Yüzdesi": st.column_config.ProgressColumn(
                    "Taksit Yüzdesi",
                    format="%.2f",
                    min_value=0,
                    max_value=1,
                ),
            }
        )
        
        # Kullanıcının yaptığı manuel değişiklikleri state'e geri kaydet
        # Bu, 'Planı Güncelle'ye basılmadığı sürece manuel değişikliklerin kalıcı olmasını sağlar.
        st.session_state.df = edited_df

        # 3. Güncel Veriyi İndirme
        st.divider()
        st.header("💾 Güncel Planı İndir")
        
        # Düzenlenen en son halini CSV'ye çevir
        csv_data = edited_df.to_csv(index=True, encoding='utf-8')
        
        st.download_button(
            label="📈 Güncel Planı CSV Olarak İndir",
            data=csv_data,
            file_name="guncel_odeme_plani.csv",
            mime="text/csv",
            use_container_width=True
        )

else:
    st.info("Lütfen başlamak için örnek formattaki CSV dosyanızı yükleyin.")
