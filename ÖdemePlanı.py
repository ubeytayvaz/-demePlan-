import streamlit as st
import pandas as pd
import io
import datetime
from dateutil.relativedelta import relativedelta

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
            'Min.': 0.0, # Bu alanlar kullanıcı tarafından doldurulabilir
            'Tam': 0.0,
            'Max': 0.0,
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
st.title("📊 Sıfırdan Ödeme Planı Oluşturucu")

st.header("1. Plan Parametrelerini Girin")
st.markdown("Aşağıdaki değerleri girip 'Planı Oluştur' butonuna basarak taslak bir tablo oluşturabilirsiniz.")

# Ayar girişleri için sütunlar
# Önceki excel'deki verileri varsayılan olarak kullanalım
col1, col2, col3, col4 = st.columns(4)

with col1:
    toplam_prim = st.number_input(
        "Toplam Prim", 
        value=100000.0,
        format="%.2f"
    )
with col2:
    taksit_sayisi = st.number_input(
        "Taksit Sayısı", 
        min_value=1, 
        step=1, 
        value=4
    )
with col3:
    # Örnek dosyadaki ilk ödeme tarihini varsayılan al
    ilk_odeme_tarihi = st.date_input(
        "İlk Ödeme Tarihi", 
        value=datetime.date(2025, 5, 10)
    )
with col4:
    # Örnek dosyanızdaki aralığı varsayılan al (Mayıs -> Temmuz = 2 ay)
    odeme_araligi_ay = st.number_input(
        "Ödeme Aralığı (Ay)", 
        min_value=1, 
        step=1, 
        value=2
    )

# Planı oluşturma butonu
if st.button("🔄 Planı Oluştur", type="primary", use_container_width=True):
    new_df = recalculate_plan(toplam_prim, taksit_sayisi, ilk_odeme_tarihi, odeme_araligi_ay)
    st.session_state.df = new_df # DataFrame'i session state'e kaydet
    st.success("Ödeme planı taslağı oluşturuldu. Şimdi aşağıdan düzenleyebilirsiniz.")

st.divider()

# 2. İnteraktif Tablo (Data Editor)
# Sadece plan oluşturulduysa (st.session_state.df varsa) göster
if 'df' in st.session_state:
    st.header("2. Planı Düzenleyin ve İndirin")
    st.info("Bu tabloyu Excel gibi çift tıklayarak düzenleyebilir, 'Min.', 'Tam', 'Max' alanlarını doldurabilir, satır ekleyebilir veya silebilirsiniz.")

    # st.data_editor, kullanıcıya tabloyu düzenleme imkanı verir.
    # Değişiklikler 'edited_df' değişkenine atanır.
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
            "Min.": st.column_config.NumberColumn("Min.", format="%.2f"),
            "Tam": st.column_config.NumberColumn("Tam", format="%.2f"),
            "Max": st.column_config.NumberColumn("Max", format="%.2f"),
            "Taksit Yüzdesi": st.column_config.ProgressColumn(
                "Taksit Yüzdesi",
                format="%.2f",
                min_value=0,
                max_value=1,
            ),
        }
    )
    
    # Kullanıcının yaptığı manuel değişiklikleri state'e geri kaydet
    # Bu, manuel değişikliklerin kalıcı olmasını sağlar.
    st.session_state.df = edited_df

    # 3. Güncel Veriyi İndirme
    st.divider()
    st.header("3. Güncel Planı İndir")
    
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
    st.info("Lütfen yukarıdaki formu doldurarak bir ödeme planı oluşturun.")

```

### Nasıl Çalışır?

1.  **Gerekli Kütüphaneleri Yükleyin** (Eğer daha önce yüklemediyseniz):
    ```bash
    pip install streamlit pandas
    ```

2.  **Kodu Kaydedin:**
    Yukarıdaki kodu `app.py` adıyla kaydedin.

3.  **Streamlit'i Başlatın:**
    Terminalde `app.py` dosyasının olduğu dizine gidin ve çalıştırın:
    ```bash
    streamlit run app.py
    
