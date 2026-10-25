# Screen Translator

Ekranın herhangi bir bölgesini seçip içindeki İngilizce metni anında Türkçeye çeviren masaüstü aracı. Oyunlar, videolar, görseller veya kopyalanamayan arayüz metinleri için kullanışlıdır.

Her şey **yerel** çalışır: metin EasyOCR ile okunur, Hugging Face'ten indirilen bir çeviri modeliyle (MarianMT veya NLLB) çevrilir. İlk model indirmesinden sonra internet gerekmez.

## Nasıl çalışır

1. Kısayola basın (varsayılan `Ctrl+Shift+T`).
2. Ekran kararır; fareyle çevirmek istediğiniz alanı seçin.
3. Çeviri, seçtiğiniz alanın tam üzerinde açılır.

| Sonuç penceresinde | İşlem |
|---|---|
| Sol tık / `Esc` | Kapat |
| Sağ tık | Kopyala / Kapat menüsü |

Seçim ekranında sağ tık veya `Esc` seçimi iptal eder.

## Gereksinimler

- Windows 10/11
- Python 3.10+
- NVIDIA GPU önerilir (CUDA). GPU yoksa CPU'da da çalışır, sadece daha yavaştır.

## Kurulum

```bash
git clone https://github.com/AliEren3460/ScreenTranslator.git
cd ScreenTranslator

# 1) PyTorch — GPU sürümü için kendi CUDA sürümünüze uygun komutu
#    https://pytorch.org/get-started/locally/ adresinden alın. Örnek (CUDA 11.8):
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118

# 2) Diğer bağımlılıklar
pip install -r requirements.txt
```

## Kullanım

`translate.bat` dosyasına çift tıklayın veya:

```bash
cd src
python main.py
```

Açılışta konsolda kısa bir ayar menüsü çıkar:

```
  Ceviri Modeli:
  1. Helsinki-NLP/opus-mt-tc-big-en-tr (Hizli, Standart) [indirilmis]
  2. facebook/nllb-200-distilled-600M (Daha Iyi Kalite) [indirilmis]
  3. facebook/nllb-200-distilled-1.3B (Yuksek Kalite - AGIR) [ilk kullanimda ~5.5 GB indirilecek]
  4. facebook/nllb-200-3.3B (En Iyi Kalite - COK AGIR) [ilk kullanimda ~17.6 GB indirilecek]
  5. Son Kullanilan: Helsinki-NLP/opus-mt-tc-big-en-tr
```

- **Model:** Enter'a basarsanız en son başarıyla yüklenen model kullanılır.
- **OCR dilleri:** Ekrandaki metnin dilleri, virgülle (`en`, `en,tr` …). [Desteklenen diller](https://www.jaided.ai/easyocr/)
- **Kısayol:** `ctrl+shift+t`, `alt+t`, `ctrl+f5`, `win+q` gibi. Geçersiz bir kısayol girilirse tekrar sorulur.

Ayarlar `src/translator_config.json` dosyasına kaydedilir.

## Modeller

| Model | İndirme | GPU belleği (fp16) | Not |
|---|---|---|---|
| `Helsinki-NLP/opus-mt-tc-big-en-tr` | ~0,5 GB | ~0,3 GB | Hızlı, günlük kullanım için yeterli |
| `facebook/nllb-200-distilled-600M` | ~2,5 GB | ~1,3 GB | Kalite/hız dengesi iyi |
| `facebook/nllb-200-distilled-1.3B` | ~5,5 GB | ~2,7 GB | Daha akıcı çeviri |
| `facebook/nllb-200-3.3B` | ~17,6 GB | ~6,6 GB | En iyi kalite, yüklemesi uzun sürer |

Seçilen model önce bilgisayarda aranır:

1. Hugging Face önbelleği (`~/.cache/huggingface/hub`)
2. Proje içindeki `model_cache` klasörü
3. İndirilenler, Masaüstü ve Belgeler (model adıyla aynı isimli klasörler)

Bir kopyanın sayılması için **eksiksiz** olması gerekir (config, tokenizer ve tüm ağırlık dosyaları). Yarım kalmış indirmeler yok sayılır ve indirme kaldığı yerden devam eder. Hiçbir yerde bulunamazsa model otomatik indirilir; ilerleme konsolda görünür.

Model yüklenemezse bir pencere açılır ve elle indirilmiş bir model klasörü seçmenize izin verir.

## Sorun giderme

**İndirme `CERTIFICATE_VERIFY_FAILED` / `self-signed certificate` hatasıyla yarıda kalıyor**
Kaspersky, ESET, Avast gibi antivirüsler HTTPS trafiğini kendi sertifikalarıyla yeniden imzalar. Python'un kendi sertifika listesi bunlara güvenmez. Uygulama bu yüzden [`truststore`](https://pypi.org/project/truststore/) ile Windows'un sertifika deposunu kullanır; `pip install -r requirements.txt` ile kurulduğundan emin olun.

**"Modeller yükleniyor, lütfen bekleyin..." mesajı uzun sürüyor**
Model ilk kez indiriliyordur; konsoldaki ilerleme çubuğunu takip edin. Büyük NLLB modellerinin diskten belleğe yüklenmesi de bir dakikayı bulabilir.

**Esc ile seçim kapanmıyor**
Windows bazen kısayolla açılan pencereye klavye odağı vermez. Sağ tık her zaman iptal eder.

**Çok monitörlü sistemler**
Şu an yalnızca ana monitörde seçim yapılabilir.

## Proje yapısı

```
src/
  main.py        Ayar menüsü, kısayol dinleme, uygulama akışı
  sniper.py      Ekran bölgesi seçimi ve ekran görüntüsü
  ocr_engine.py  EasyOCR ile metin okuma
  translator.py  Model bulma / indirme / yükleme ve çeviri
  ui_overlay.py  Çeviri sonucu penceresi
  config.py      Ayar dosyası okuma/yazma
translate.bat    Windows başlatıcısı
```
