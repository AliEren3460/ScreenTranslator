# Screen Translator

Ekranın herhangi bir bölgesini seçip içindeki İngilizce metni anında Türkçeye çeviren masaüstü aracı. Oyunlar, videolar, görseller veya kopyalanamayan arayüz metinleri için kullanışlıdır.

Her şey **yerel** çalışır: metin EasyOCR ile okunur, yalnızca İngilizce→Türkçe çeviri yapan küçük bir modelle çevrilir. İlk model indirmesinden sonra internet gerekmez.

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

# 2) Diğer bağımlılıklar (Töz-Çevir GitHub'dan kurulduğu için git gerekir)
pip install -r requirements.txt

# 3) Sadece CUDA 11 torch kullanıyorsanız: hızlı modelin GPU'da çalışması için
pip install nvidia-cublas-cu12
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
  1. Helsinki-NLP/opus-mt-tc-big-en-tr (Hizli - GPU varsa GPU, yoksa CPU) [indirilmis]
  2. TozAI/Toz-Cevir-1 (En Iyi Kalite - GPU varsa GPU, yoksa CPU) [ilk kullanimda ~0.3 GB indirilecek]
  3. Son Kullanilan: Helsinki-NLP/opus-mt-tc-big-en-tr
```

- **Model:** Enter'a basarsanız en son başarıyla yüklenen model kullanılır.
- **OCR dilleri:** Ekrandaki metnin dilleri, virgülle (`en`, `en,tr` …). [Desteklenen diller](https://www.jaided.ai/easyocr/)
- **Kısayol:** `ctrl+shift+t`, `alt+t`, `ctrl+f5`, `win+q` gibi. Geçersiz bir kısayol girilirse tekrar sorulur.

Ayarlar `src/translator_config.json` dosyasına kaydedilir. Çeviri ve OCR'ı GPU yerine işlemcide çalıştırmak için bu dosyaya `"device": "cpu"` ekleyin (`"auto"` varsayılan, `"cuda"` GPU'yu zorunlu kılar).

## Modeller

| Model | Nasıl çalışır | Cümle başına | Bellek |
|---|---|---|---|
| `Helsinki-NLP/opus-mt-tc-big-en-tr` | [CTranslate2](https://github.com/OpenNMT/CTranslate2) int8, GPU varsa GPU | ~30 ms (GPU), ~135 ms (CPU) | ~0,5 GB VRAM |
| [`TozAI/Toz-Cevir-1`](https://huggingface.co/TozAI/Toz-Cevir-1) | Kendi paketi, GPU varsa GPU | ~85 ms (GPU), ~140 ms (CPU) | ~0,3 GB VRAM |

İkisi de yalnızca İngilizce→Türkçe çeviri yapar. Bu yüzden 200 dilli NLLB modellerinden hem daha hızlı hem daha isabetlidir. RTX 3080 Ti Laptop üzerinde chrF++ puanları (yüksek olan daha iyi):

| Model | FLORES-200 | WMT17 | Tatoeba |
|---|---|---|---|
| Töz-Çevir-1 | **59,7** | 54,7 | **68,8** |
| opus-mt-tc-big-en-tr (CTranslate2 int8) | 59,4 | **54,8** | 66,1 |
| nllb-200-3.3B | 58,2 | 53,6 | 67,7 |
| nllb-200-distilled-1.3B | 57,4 | 52,7 | 66,6 |
| nllb-200-distilled-600M | 53,7 | 50,4 | 62,7 |

Opus modeli ilk açılışta bir kez CTranslate2 biçimine dönüştürülür (birkaç saniye) ve `~/.cache/screentranslator` altında saklanır. İki model de GPU'da çalıştırılamazsa otomatik olarak işlemciye geçer. Süreler kısa arayüz cümleleri içindir; uzun cümlelerde Töz-Çevir GPU'da ~330 ms, CPU'da ~950 ms sürer.

Seçilen model önce bilgisayarda aranır:

1. Hugging Face önbelleği (`~/.cache/huggingface/hub`)
2. Proje içindeki `model_cache` klasörü
3. İndirilenler, Masaüstü ve Belgeler (model adıyla aynı isimli klasörler)

Bir kopyanın sayılması için **eksiksiz** olması gerekir (config, tokenizer ve tüm ağırlık dosyaları). Yarım kalmış indirmeler yok sayılır ve indirme kaldığı yerden devam eder. Hiçbir yerde bulunamazsa model otomatik indirilir; ilerleme konsolda görünür.

Model yüklenemezse bir pencere açılır ve elle indirilmiş bir model klasörü seçmenize izin verir. Hugging Face biçimindeki diğer MarianMT ve NLLB modelleri de bu yolla kullanılabilir.

## Sorun giderme

**İndirme `CERTIFICATE_VERIFY_FAILED` / `self-signed certificate` hatasıyla yarıda kalıyor**
Kaspersky, ESET, Avast gibi antivirüsler HTTPS trafiğini kendi sertifikalarıyla yeniden imzalar. Python'un kendi sertifika listesi bunlara güvenmez. Uygulama bu yüzden [`truststore`](https://pypi.org/project/truststore/) ile Windows'un sertifika deposunu kullanır; `pip install -r requirements.txt` ile kurulduğundan emin olun.

**"Modeller yükleniyor, lütfen bekleyin..." mesajı uzun sürüyor**
Model ilk kez indiriliyordur; konsoldaki ilerleme çubuğunu takip edin.

**`CUDA error: illegal instruction` / `CUBLAS_STATUS_EXECUTION_FAILED` gibi hatalar veya uygulama aniden kapanıyor**
Bu hatalar genelde GPU'nun yük altında kararsız çalıştığını gösterir (Windows Olay Görüntüleyicisi'nde `nvlddmkm` kaynaklı Event 13 kayıtları). Hız aşırtma/performans modlarını kapatmayı ve NVIDIA sürücüsünü temiz kurulumla yeniden yüklemeyi deneyin. Bu arada `translator_config.json` dosyasına `"device": "cpu"` ekleyerek GPU'yu tamamen devre dışı bırakabilirsiniz.

**`GPU kullanilamadi, CPU'ya geciliyor: Library cublas64_12.dll is not found`**
CUDA 11 torch kurulu. GPU için `pip install nvidia-cublas-cu12`; işlemcide de çalışmaya devam eder.

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
  translator.py  Model bulma / indirme / dönüştürme / yükleme ve çeviri
  ui_overlay.py  Çeviri sonucu penceresi
  config.py      Ayar dosyası okuma/yazma
translate.bat    Windows başlatıcısı
```
