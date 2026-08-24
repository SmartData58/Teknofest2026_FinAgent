<script setup>
import { ref, onMounted, nextTick } from 'vue'
import DotMatrix from "~/components/loaders/DotMatrix.vue"
import { useChatStore } from '~/stores/chatStore'
import { useI18n } from 'vue-i18n'

const { locale, t } = useI18n()

const mounted = ref(false)
const chatHistory = ref([])
const userMessage = ref('')
const isLoading = ref(false)
const isStreaming = ref(false)

const chatStore = useChatStore()

const showSourceModal = ref(false)
const activeSource = ref(null)
const activeFile = ref(null) 
const activeModalType = ref('source') 

const toastMessage = ref('')
const showToast = (msg) => {
  toastMessage.value = msg
  setTimeout(() => {
    toastMessage.value = ''
  }, 3000)
}

// TOKAT 5: TABLOYA TIKLANDIĞINDA KAYIT BULUNAMADI DEMEYECEK!
// Direkt Python'un hazırladığı metni (full_texts) basacak.
const openModalFromText = (text) => {
    activeSource.value = { icerik: text || 'Detay bulunamadı.' }
    activeModalType.value = 'source'
    showSourceModal.value = true
}

const openUserFile = (file) => {
  activeFile.value = { ...file, isUserFile: true }
  activeModalType.value = 'file'
  showSourceModal.value = true
}

const downloadFile = (file, event) => {
  event.stopPropagation() 
  if (!file.isReport) {
    const a = document.createElement('a')
    a.href = file.url
    a.download = file.name || 'download'
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
  }
}

const toggleStatus = (msg) => {
  if (msg && msg.statuses && msg.statuses.length > 0) {
    msg.isStatusExpanded = !msg.isStatusExpanded;
  }
}

// YENİ: Kaynak bölümü artık native <details>/<summary> DEĞİL — tarayıcı
// bunu animasyonsuz, anında açıp kapatıyordu (CSS transition <details>'ın
// açık/kapalı durumları arasında çalışmaz). Bunun yerine msg üzerinde tutulan
// bu bayrakla elle kontrol ediliyor; şablonda CSS grid-rows (0fr/1fr) tekniğiyle
// içerik yüksekliği ne olursa olsun (dinamik) yumuşak bir açılış/kapanış elde
// ediliyor.
const toggleSources = (msg) => {
  if (msg && msg.sources && msg.sources.length > 0) {
    msg.isSourcesExpanded = !msg.isSourcesExpanded;
  }
}

const isExpectingChart = (msg) => {
  if (!msg) return false;
  const check = (s) => s && (s.icon === 'database' || (s.text && (s.text.toLowerCase().includes('mongo') || s.text.toLowerCase().includes('redis') || s.text.toLowerCase().includes('veritabanı'))));
  return check(msg.currentStatus) || (msg.statuses && msg.statuses.some(check));
}

const getChartColorHex = (index) => {
    const colors = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#06b6d4', '#14b8a6', '#f43f5e', '#84cc16'];
    return colors[index % colors.length];
}

const getChartColorClass = (index) => {
    const colors = ['bg-blue-500', 'bg-green-500', 'bg-amber-500', 'bg-red-500', 'bg-purple-500', 'bg-pink-500', 'bg-cyan-500', 'bg-teal-500', 'bg-rose-500', 'bg-lime-500'];
    return colors[index % colors.length];
}

const getSvgPaths = (chart) => {
    if (!chart || !chart.values || chart.values.length === 0) return [];
    const total = chart.values.reduce((a, b) => a + b, 0);
    if (total === 0) return [];

    const paths = [];
    let currentAngle = 0; 
    
    chart.values.forEach((val, i) => {
        const sliceAngle = (val / total) * 360;
        const color = getChartColorHex(i);
        const label = chart.labels[i];
        const percent = ((val / total) * 100).toFixed(1);
        const camp = chart.sub_labels ? chart.sub_labels[i] : '';
        const prefix = chart.prefix || '';
        const suffix = chart.suffix || '';
        const tooltipText = `${label} - ${camp} : ${prefix}${val}${suffix} (%${percent})`;

        if (sliceAngle === 360) {
            paths.push({ isCircle: true, color, tooltipText });
            return;
        }

        const startAngle = (currentAngle - 90) * (Math.PI / 180);
        const endAngle = (currentAngle + sliceAngle - 90) * (Math.PI / 180);

        const cx = 50, cy = 50, r = 50;
        const x1 = cx + r * Math.cos(startAngle);
        const y1 = cy + r * Math.sin(startAngle);
        const x2 = cx + r * Math.cos(endAngle);
        const y2 = cy + r * Math.sin(endAngle);

        const largeArcFlag = sliceAngle > 180 ? 1 : 0;
        const d = `M 50 50 L ${x1} ${y1} A 50 50 0 ${largeArcFlag} 1 ${x2} ${y2} Z`;

        paths.push({ isCircle: false, d, color, tooltipText });
        currentAngle += sliceAngle;
    });
    return paths;
};

// Akışta bölünmüş olabilecek arayüz etiketleri. Tampon bunlardan birinin
// ÖN EKİYLE bitiyorsa, etiket tamamlanana kadar metne yazmayı bekletiriz.
const BILINEN_ETIKETLER = [
  '[STATUS]', '[/STATUS]',
  '[CHART]', '[/CHART]',
  '[SOURCES]', '[/SOURCES]',
  '[SUGGESTIONS]', '[/SUGGESTIONS]',
  '[SUGGESTION]', '[/SUGGESTION]',
];

const kismiEtiketMi = (buf) => {
  if (!buf) return false;
  return BILINEN_ETIKETLER.some((etiket) => {
    const maks = Math.min(buf.length, etiket.length);
    for (let n = maks; n >= 1; n--) {
      if (buf.endsWith(etiket.slice(0, n))) return true;
    }
    return false;
  });
};

// Bar genişliği güvenli hesap. Şablonda doğrudan
//   msg.chart.values[i] / (stats ? stats.max : Math.max(...values)) * 100
// yazıyordu. values[i] eksikse NaN%, max 0 ise Infinity% üretiyordu
// (tarayıcı bunları sessizce yok sayıp barı hiç çizmiyordu).
const barGenislik = (chart, i) => {
  const degerler = Array.isArray(chart?.values) ? chart.values : [];
  const v = degerler[i];
  if (typeof v !== 'number' || Number.isNaN(v)) return '0%';
  const sayilar = degerler.filter(x => typeof x === 'number' && !Number.isNaN(x));
  const maks = (chart?.stats && typeof chart.stats.max === 'number' && chart.stats.max > 0)
    ? chart.stats.max
    : (sayilar.length ? Math.max(...sayilar) : 0);
  if (!maks || !Number.isFinite(maks) || maks <= 0) return '0%';
  return Math.max(0, Math.min(100, (v / maks) * 100)) + '%';
};

// Kademeli (stagger) animasyon gecikmesi — üst sınırla ki uzun listelerde
// son satırlar dakikalarca beklemesin.
const gecikme = (i, adim = 45, maks = 600) => ({ animationDelay: Math.min(i * adim, maks) + 'ms' });

const isExporting = ref({})
const isExportingExcel = ref({})
const isExportingPNG = ref({})

// =============================================================================
// DIŞA AKTARMA ORTAK YARDIMCILARI
//
// GRAFİK / ÇIKTI AYRIMI — buradaki en büyük hata buydu:
// Şablonda dışa aktarma butonları İKİ AYRI YERDE duruyor:
//   1) Grafik kartının üstünde (v-if="msg.chart")      -> bağlam: GRAFİK
//   2) Cevap metninin altında (v-if="msg.content...")  -> bağlam: METİN
// Ama ikisi de AYNI fonksiyonu çağırıyordu ve o fonksiyonlar YALNIZCA grafik
// verisini dışa aktarıyordu. Sonuç: kullanıcı cevabın altındaki "Raporu
// Görüntüle"ye bastığında, okuduğu analiz metni rapora HİÇ girmiyor; grafiği
// olmayan bir mesajda ise "dışa aktarılacak veri bulunamadı" hatası alıyordu —
// ekranda kocaman bir cevap dururken.
// Artık her iki çıktı da mesajın SAHİP OLDUĞU her şeyi içeriyor: analiz metni
// varsa metin, grafik varsa grafik verisi, ikisi de varsa ikisi birden.
// (PNG bunun istisnası: o, grafiğin görüntüsünü yakaladığı için grafiğe özeldir.)
// =============================================================================

const escapeHtml = (s) => String(s ?? '')
  .replace(/&/g, '&amp;')
  .replace(/</g, '&lt;')
  .replace(/>/g, '&gt;')
  .replace(/"/g, '&quot;')
  .replace(/'/g, '&#39;');

// Betik yükleyici: eski kod `await new Promise(resolve => script.onload = resolve)`
// kullanıyordu — onerror YOKTU. CDN engelliyse/çevrimdışıysa promise ASLA
// çözülmüyor, fonksiyon sonsuza kadar asılı kalıyor ve `isExporting[index]`
// true kaldığı için buton kalıcı olarak devre dışı kalıyordu. Artık hata
// yakalanıyor, aynı betik iki kez indirilmiyor ve başarısız denemeler
// önbellekten düşürülüyor (tekrar denenebilsin diye).
const _betekOnbellek = {};
const betigiYukle = (src, globalAd) => {
  if (window[globalAd]) return Promise.resolve();
  if (_betekOnbellek[src]) return _betekOnbellek[src];
  _betekOnbellek[src] = new Promise((resolve, reject) => {
    const s = document.createElement('script');
    s.src = src;
    s.onload = () => window[globalAd]
      ? resolve()
      : reject(new Error(`${globalAd} yüklendi ama tanımlı değil`));
    s.onerror = () => {
      delete _betekOnbellek[src];
      reject(new Error(`Betik indirilemedi (internet/CDN erişimi yok): ${src}`));
    };
    document.head.appendChild(s);
  });
  return _betekOnbellek[src];
};

// Cevap metnini düz metne çevirir. Ham içerikte arayüz etiketleri
// ([CHART], [SOURCES], [SUGGESTIONS], [STATUS]) ve markdown işaretleri kalmış
// olabiliyor; bunlar rapora sızmasın diye temizleniyor.
const cevabiDuzMetneCevir = (ham) => {
  if (!ham) return '';
  return String(ham)
    .replace(/\[CHART\][\s\S]*?\[\/CHART\]/gi, '')
    .replace(/\[SOURCES\][\s\S]*?\[\/SOURCES\]/gi, '')
    .replace(/\[SUGGESTIONS?\][\s\S]*?\[\/SUGGESTIONS?\]/gi, '')
    .replace(/\[STATUS\][\s\S]*?\[\/STATUS\]/gi, '')
    .replace(/```[a-zA-Z]*\n?([\s\S]*?)```/g, '$1')
    .replace(/^#{1,6}\s*/gm, '')
    .replace(/\*\*(.*?)\*\*/g, '$1')
    // Kalın (**) zaten yukarıda temizlendiği için burada kalan tek yıldızlar
    // italik demektir. (Lookbehind kullanmıyoruz — eski Safari sürümleri
    // desteklemiyor ve tüm regex bloğu sessizce patlardı.)
    .replace(/\*([^*\n]+)\*/g, '$1')
    .replace(/`([^`\n]+)`/g, '$1')
    .replace(/^\s*[-*]\s+/gm, '• ')
    .replace(/^\s*>\s?/gm, '')
    .replace(/\n{3,}/g, '\n\n')
    .trim();
};

// Değer biçimlendirme: `chart.prefix || ''` yerine `?? ''`.
// PDF'te `chart.prefix || '%'` yazıyordu; prefix BOŞ STRING olduğunda ("" falsy)
// bu ifade '%' üretiyordu. Ödül grafiklerinde backend prefix="" / suffix=" TL"
// gönderdiği için PDF'te değerler "%500 TL" diye çıkıyordu (arayüz ve Excel
// doğru gösterirken). ?? yalnızca null/undefined'da devreye girer.
const degeriBicimlendir = (chart, v) =>
  (v === null || v === undefined || Number.isNaN(v))
    ? '-'
    : `${chart.prefix ?? ''}${v}${chart.suffix ?? ''}`;

// Grafik dizilerini güvenli satırlara çevirir. Eski kod chart.labels
// üzerinde dönüp chart.values[i] okuyordu; diziler farklı uzunluktaysa
// `undefined` değerler "undefined" metni olarak çıktıya yazılıyordu.
const grafikSatirlari = (chart) => {
  if (!chart || !Array.isArray(chart.labels)) return [];
  const degerler = Array.isArray(chart.values) ? chart.values : [];
  const altBaslik = Array.isArray(chart.sub_labels) ? chart.sub_labels : [];
  return chart.labels.map((label, i) => {
    const ham = degerler[i];
    return {
      banka: label ?? '-',
      kampanya: altBaslik[i] || '-',
      hamDeger: (typeof ham === 'number' && !Number.isNaN(ham)) ? ham : null,
      metinDeger: degeriBicimlendir(chart, ham),
    };
  });
};

const birimEtiketi = (chart) =>
  `${chart?.prefix ?? ''}${chart?.suffix ?? ''}`.trim() || '-';

// ---------------------------------------------------------------------------
// YENİ ÖZELLİK — "Detaylı Kampanya Kıyaslaması" için banka filtresi.
//
// Kart başlığının (ör. "Kampanya Verileri") sağında, o sonuç kümesinde GEÇEN
// bankaların isimleri çip olarak listelenir. Bir veya BİRDEN FAZLA banka
// seçilebilir (çoklu seçim); seçim yapıldığında yalnızca sağdaki "Detaylı
// Kampanya Kıyaslaması" bölümü daralır. Pasta grafik, ortalama/en düşük/en
// yüksek kutuları ve alttaki "Eksiksiz Veri Tablosu" BİLEREK filtrelenmez —
// istenen davranış "grafik değişmesin" idi; grafik hep tüm sonuç kümesini
// göstermeye devam eder, filtre sadece kıyaslama listesinin odağını değiştirir.
// ---------------------------------------------------------------------------

// Sonuç kümesindeki benzersiz banka adları (ilk görülme sırasını korur).
const bankaSecenekleri = (chart) => {
  if (!chart || !Array.isArray(chart.labels)) return [];
  const gorulen = new Set();
  const liste = [];
  chart.labels.forEach((label) => {
    const ad = (label ?? '').toString().trim();
    if (ad && !gorulen.has(ad)) {
      gorulen.add(ad);
      liste.push(ad);
    }
  });
  return liste;
};

const bankaSecili = (msg, banka) =>
  Array.isArray(msg?.selectedBanks) && msg.selectedBanks.includes(banka);

const bankaFiltresiDegistir = (msg, banka) => {
  if (!msg) return;
  if (!Array.isArray(msg.selectedBanks)) msg.selectedBanks = [];
  const yer = msg.selectedBanks.indexOf(banka);
  if (yer === -1) msg.selectedBanks.push(banka);
  else msg.selectedBanks.splice(yer, 1);
};

const bankaFiltresiTemizle = (msg) => {
  if (msg) msg.selectedBanks = [];
};

// Kıyaslama bölümünde gösterilecek satır indeksleri. Hiçbir banka seçili
// değilse TÜM satırlar döner (filtre yok) — böylece varsayılan görünüm
// eskisiyle birebir aynı kalır.
const filtreliIndeksler = (msg) => {
  const etiketler = Array.isArray(msg?.chart?.labels) ? msg.chart.labels : [];
  const secili = Array.isArray(msg?.selectedBanks) ? msg.selectedBanks : [];
  const tumu = etiketler.map((_, i) => i);
  if (secili.length === 0) return tumu;
  const filtreli = tumu.filter(
    (i) => secili.includes((etiketler[i] ?? '').toString().trim())
  );
  // Güvenlik ağı: filtre hiçbir şeyle eşleşmezse boş bir liste göstermek
  // yerine tümüne geri dön (kullanıcı asla boş bir panelle karşılaşmasın).
  return filtreli.length ? filtreli : tumu;
};

// Mesajda dışa aktarılabilir ne var? (grafik / metin / ikisi / hiçbiri)
const mesajIcerigi = (index) => {
  const msg = chatHistory.value[index] || {};
  const chart = msg.chart || null;
  const metin = cevabiDuzMetneCevir(msg.content);
  return { msg, chart, metin, bosMu: !chart && !metin };
};

// =============================================================================
// PNG DIŞA AKTARMA — SAYDAM ÇIKTI DÜZELTMESİ
//
// 🛠️ Bildirilen sorun: kaydedilen PNG'ler saydam (arka planı yok) çıkıyordu.
// İki ayrı sebebi vardı, ikisi de aşağıda çözüldü:
//
// 1) MODERN RENK FONKSİYONLARI (oklch/oklab/lab/lch/color-mix)
//    Tailwind'in güncel renk paleti `oklch()` üretiyor. html2canvas 1.4.1 bu
//    fonksiyonları AYRIŞTIRAMIYOR; ayrıştıramadığı her rengi "transparent"
//    sayıyor. Sonuç: kartın `bg-white` zemini, kenarlıklar ve çubukların
//    gradyanları tuvale HİÇ çizilmiyor — yani görüntünün gövdesi saydam
//    kalıyor. Çözüm: yakalamadan hemen önce (onclone) klonlanan ağaçtaki her
//    elemanın hesaplanmış renkleri okunup, modern renk fonksiyonları tarayıcının
//    KENDİ canvas ayrıştırıcısıyla rgb/hex'e çevrilerek satır içi stil olarak
//    yazılıyor. Böylece html2canvas'ın eline yalnızca anlayabildiği renkler
//    geçiyor. Gradyanlar da (bar dolguları) tek tek renk durakları çevrilerek
//    korunuyor.
//
// 2) TUVALİN KENDİSİNDE ALFA KANALI KALMASI
//    `backgroundColor` seçeneği yalnızca html2canvas'ın kendi zeminini boyar;
//    ayrıştırılamayan bir üst katman ya da yuvarlatılmış köşeler yüzünden
//    çıktıda yine saydam pikseller kalabiliyor. Çözüm: yakalanan tuval, ikinci
//    bir OPAK tuvale (önce düz renkle doldurulmuş) çizilerek düzleştiriliyor.
//    Bu adım tek başına "saydam PNG" ihtimalini tamamen ortadan kaldırır.
//
// Ayrıca: dışa aktarma butonlarının kendisi de görüntüye giriyordu (Excel/PDF/
// PNG ikonları). Artık `data-png-gizle` işaretli elemanlar yakalamadan
// çıkarılıyor.
// =============================================================================

// Tarayıcının kendi renk ayrıştırıcısı: canvas 2D bağlamı oklch/lab/color()
// dahil modern renkleri anlayıp bize rgb/hex olarak geri verir.
let _renkOlcer = null;
const _renkOlcerGetir = () => {
    if (_renkOlcer === null && typeof document !== 'undefined') {
        _renkOlcer = document.createElement('canvas').getContext('2d');
    }
    return _renkOlcer;
};

const MODERN_RENK_DESENI = /(oklch|oklab|color-mix|\blch\(|\blab\(|\bcolor\()/i;

/** Modern bir renk ifadesini rgb/hex'e çevirir; çeviremezse null döner. */
const renkiCevir = (deger) => {
    const olcer = _renkOlcerGetir();
    if (!olcer || typeof deger !== 'string' || !MODERN_RENK_DESENI.test(deger)) return null;
    try {
        // Nöbetçi değer: ayrıştırma başarısız olursa fillStyle DEĞİŞMEZ,
        // böylece başarısızlığı güvenle tespit edebiliyoruz.
        const nobetci = '#010203';
        olcer.fillStyle = nobetci;
        olcer.fillStyle = deger;
        const sonuc = olcer.fillStyle;
        return sonuc === nobetci ? null : sonuc;
    } catch (e) {
        return null;
    }
};

/** Gradyan/gölge gibi bileşik değerlerin İÇİNDEKİ modern renkleri tek tek çevirir. */
const bilesikDegeriCevir = (deger) => {
    if (typeof deger !== 'string' || !MODERN_RENK_DESENI.test(deger)) return null;
    const cevrilmis = deger.replace(/(oklch|oklab|lch|lab|color)\([^()]*\)/gi,
        (parca) => renkiCevir(parca) || 'rgba(0,0,0,0)');
    return cevrilmis === deger ? null : cevrilmis;
};

// Klonda düzeltilecek renk özellikleri.
const _DUZ_RENK_OZELLIKLERI = [
    'color', 'backgroundColor', 'borderTopColor', 'borderRightColor',
    'borderBottomColor', 'borderLeftColor', 'outlineColor', 'textDecorationColor',
    'fill', 'stroke', 'caretColor', 'columnRuleColor',
];
const _BILESIK_OZELLIKLER = ['backgroundImage', 'boxShadow', 'textShadow'];

/**
 * Klonlanan ağaçtaki modern renkleri html2canvas'ın anlayacağı biçime çevirir.
 * Orijinal elemanlardan hesaplanmış stiller okunur (klon henüz sayfada
 * yerleşmemiş olabilir), klona satır içi stil olarak yazılır.
 */
const klonRenkleriniDuzelt = (orijinalKok, klonKok) => {
    if (!orijinalKok || !klonKok || typeof window === 'undefined') return;
    const orijinaller = [orijinalKok, ...orijinalKok.querySelectorAll('*')];
    const klonlar = [klonKok, ...klonKok.querySelectorAll('*')];
    const adet = Math.min(orijinaller.length, klonlar.length);

    for (let i = 0; i < adet; i++) {
        let hesaplanan;
        try {
            hesaplanan = window.getComputedStyle(orijinaller[i]);
        } catch (e) {
            continue;
        }
        const klon = klonlar[i];
        if (!klon || !klon.style) continue;

        for (const ozellik of _DUZ_RENK_OZELLIKLERI) {
            const cevrilmis = renkiCevir(hesaplanan[ozellik]);
            if (cevrilmis) klon.style[ozellik] = cevrilmis;
        }
        for (const ozellik of _BILESIK_OZELLIKLER) {
            const cevrilmis = bilesikDegeriCevir(hesaplanan[ozellik]);
            if (cevrilmis) klon.style[ozellik] = cevrilmis;
        }
    }
};

/** Yakalanan tuvali OPAK bir zemine düzleştirir — saydam piksel bırakmaz. */
const tuvaliDuzlestir = (tuval, arkaPlan) => {
    const nihai = document.createElement('canvas');
    nihai.width = tuval.width;
    nihai.height = tuval.height;
    const ctx = nihai.getContext('2d');
    ctx.fillStyle = arkaPlan;
    ctx.fillRect(0, 0, nihai.width, nihai.height);
    ctx.drawImage(tuval, 0, 0);
    return nihai;
};

const exportToPNG = async (index) => {
    if (isExportingPNG.value[index]) return;

    // PNG grafiğin GÖRÜNTÜSÜNÜ yakalar; grafik yoksa yakalanacak bir şey yoktur.
    // (Diğer iki çıktının aksine bu, bilinçli olarak grafiğe özeldir.)
    const el = document.getElementById('chart-container-' + index);
    if (!chatHistory.value[index]?.chart || !el) {
        showToast(t('chat.png_no_chart', "Bu mesajda görüntü olarak kaydedilecek bir grafik yok."));
        return;
    }

    isExportingPNG.value[index] = true;
    showToast(t('chat.png_preparing', "PNG görseli hazırlanıyor..."));

    try {
        await betigiYukle('https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js', 'html2canvas');

        const karanlik = document.documentElement.classList.contains('dark');
        const arkaPlan = karanlik ? '#171717' : '#ffffff';

        const canvas = await window.html2canvas(el, {
            scale: 2,
            backgroundColor: arkaPlan,
            useCORS: true,
            logging: false,
            // Dışa aktarma butonları görüntüye girmesin.
            ignoreElements: (eleman) => eleman?.hasAttribute?.('data-png-gizle'),
            // 🛠️ Asıl düzeltme: oklch/lab renkleri html2canvas'a verilmeden önce
            // rgb'ye çevriliyor (bkz. yukarıdaki uzun not).
            onclone: (klonDoc, klonEleman) => {
                try {
                    const kok = klonEleman || klonDoc.getElementById('chart-container-' + index);
                    klonRenkleriniDuzelt(el, kok);
                    if (kok && kok.style) {
                        // Konteynerin kendi zemini yoktu; kartın etrafındaki boşluk
                        // bu yüzden saydam kalıyordu.
                        kok.style.backgroundColor = arkaPlan;
                        kok.style.padding = '16px';
                        kok.style.maxWidth = 'none';
                    }
                } catch (hata) {
                    console.warn('PNG renk normalizasyonu atlandı:', hata);
                }
            },
        });

        // Alfa kanalını tamamen ortadan kaldır (saydamlığa karşı ikinci savunma).
        const duzTuval = tuvaliDuzlestir(canvas, arkaPlan);

        // toDataURL bazı tarayıcılarda büyük tuvallerde boş string döndürebiliyor;
        // sessizce bozuk dosya indirmek yerine hata veriyoruz.
        const dataUrl = duzTuval.toDataURL('image/png');
        if (!dataUrl || dataUrl === 'data:,') throw new Error('Görüntü oluşturulamadı (tuval çok büyük olabilir)');

        const link = document.createElement('a');
        link.download = `FinAgent_Grafik_${new Date().getTime()}.png`;
        link.href = dataUrl;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    } catch(e) {
        console.error('PNG dışa aktarma hatası:', e);
        showToast(`${t('chat.png_error', "PNG oluşturulamadı")}: ${e.message}`);
    } finally {
        isExportingPNG.value[index] = false;
    }
}

const exportToExcel = async (index) => {
  if (isExportingExcel.value[index]) return;

  const { msg, chart, metin, bosMu } = mesajIcerigi(index);
  if (bosMu) {
      showToast(t('chat.no_data_export', "Bu mesajda dışa aktarılacak içerik bulunamadı."));
      return;
  }

  isExportingExcel.value[index] = true;

  try {
      await betigiYukle('https://cdn.jsdelivr.net/npm/xlsx-js-style@1.2.0/dist/xlsx.bundle.js', 'XLSX');

      const wb = window.XLSX.utils.book_new();

      // --- SAYFA 1: Kampanya verileri (yalnızca grafik varsa) ---
      if (chart) {
          const satirlar = grafikSatirlari(chart);
          const wsData = [[
              t('chat.bank_institution', 'Banka / Kurum'),
              t('chat.campaign_detail', 'Kampanya Detayı'),
              t('chat.value', 'Değer'),
              t('chat.unit', 'Birim'),
          ]];

          // Değerler artık METİN değil SAYI olarak yazılıyor.
          // Eskiden "%2.99" / "500 TL" gibi birleştirilmiş metinler yazılıyordu;
          // Excel bunları metin sayıp toplayamıyor, sıralayamıyor, grafik
          // çizemiyordu — yani tablo Excel'de işe yaramıyordu. Birim ayrı sütuna
          // alındı, sayı sayı olarak kaldı.
          satirlar.forEach(r => wsData.push([
              r.banka,
              r.kampanya,
              r.hamDeger !== null ? r.hamDeger : r.metinDeger,
              birimEtiketi(chart),
          ]));

          if (chart.stats) {
              wsData.push([]);
              wsData.push([t('chat.average', 'Ortalama Değer'), '-', chart.stats.avg ?? '-', birimEtiketi(chart)]);
              wsData.push([t('chat.min_value', 'En Düşük'), '-', chart.stats.min ?? '-', birimEtiketi(chart)]);
              wsData.push([t('chat.max_value', 'En Yüksek'), '-', chart.stats.max ?? '-', birimEtiketi(chart)]);
          }

          const ws = window.XLSX.utils.aoa_to_sheet(wsData);
          ws['!cols'] = [{ wch: 28 }, { wch: 46 }, { wch: 14 }, { wch: 10 }];
          window.XLSX.utils.book_append_sheet(wb, ws, 'Kampanya_Verileri');
      }

      // --- SAYFA 2: Analiz metni (yalnızca metin varsa) ---
      // Bu sayfa TAMAMEN YENİ. Kullanıcı cevabın altındaki "Excel İndir"e
      // bastığında okuduğu analiz metni dosyaya hiç girmiyordu.
      if (metin) {
          const metinData = [[t('chat.analysis', 'Analiz')]];
          metin.split('\n').forEach(satir => metinData.push([satir]));
          metinData.push([]);
          metinData.push([t('chat.report_footer', 'Bu rapor, FinAgent Yapay Zeka asistanı tarafından otomatik olarak oluşturulmuştur.')]);

          const wsMetin = window.XLSX.utils.aoa_to_sheet(metinData);
          wsMetin['!cols'] = [{ wch: 120 }];
          window.XLSX.utils.book_append_sheet(wb, wsMetin, 'Analiz');
      }

      window.XLSX.writeFile(wb, `FinAgent_Rapor_${new Date().getTime()}.xlsx`);
  } catch (err) {
      console.error('Excel oluşturulurken hata:', err);
      showToast(`${t('chat.excel_error', "Excel oluşturulamadı")}: ${err.message}`);
  } finally {
      isExportingExcel.value[index] = false;
  }
}

const exportToPDF = async (index) => {
  if (isExporting.value[index]) return;

  const { chart, metin, bosMu } = mesajIcerigi(index);
  if (bosMu) {
      // Eskiden bu kontrol, ağır html2pdf kütüphanesi İNDİRİLDİKTEN SONRA
      // `throw new Error("Veri Yok")` ile yapılıyordu ve kullanıcıya genel bir
      // "Rapor oluşturulurken hata" mesajı gösteriliyordu. Artık en başta,
      // anlaşılır bir mesajla duruyor.
      showToast(t('chat.no_data_export', "Bu mesajda dışa aktarılacak içerik bulunamadı."));
      return;
  }

  isExporting.value[index] = true;
  showToast(t('chat.pdf_preparing', "PDF raporu hazırlanıyor..."));

  try {
      await betigiYukle('https://cdnjs.cloudflare.com/ajax/libs/html2pdf.js/0.10.1/html2pdf.bundle.min.js', 'html2pdf');

      const tarih = new Date().toLocaleDateString(t('locale', 'tr-TR'), { year: 'numeric', month: 'long', day: 'numeric' });

      let html = `
        <div style="font-family: 'Segoe UI', Arial, sans-serif; color: #171717; padding: 20px;">
            <div style="border-bottom: 2px solid #2563eb; padding-bottom: 10px; margin-bottom: 20px;">
                <h1 style="color: #2563eb; margin: 0; font-size: 24px;">FinAgent Raporu</h1>
                <p style="color: #6b7280; font-size: 12px; margin: 5px 0 0 0;">Oluşturulma Tarihi: ${escapeHtml(tarih)}</p>
            </div>`;

      // --- BÖLÜM 1: Analiz metni ---
      // TAMAMEN YENİ. Rapor eskiden sadece grafik tablosundan ibaretti;
      // kullanıcının ekranda okuduğu analiz metni PDF'e hiç girmiyordu.
      if (metin) {
          html += `<h2 style="font-size: 16px; margin: 0 0 8px 0;">Analiz</h2>`;
          metin.split(/\n{2,}/).forEach(p => {
              // escapeHtml: kampanya adları/metin & < > " gibi karakterler
              // içerebiliyor; ham yapıştırılırsa PDF'in HTML'ini bozar.
              html += `<p style="font-size: 12px; line-height: 1.6; margin: 0 0 10px 0; text-align: justify;">${escapeHtml(p).replace(/\n/g, '<br>')}</p>`;
          });
      }

      // --- BÖLÜM 2: Grafik verileri ---
      if (chart) {
          const satirlar = grafikSatirlari(chart);
          html += `<h2 style="font-size: 16px; margin: ${metin ? '22px' : '0'} 0 4px 0;">${escapeHtml(chart.title || 'Pazar Analizi')}</h2>
                   <p style="font-size: 12px; color: #4b5563; margin: 0 0 14px 0;">${escapeHtml(chart.subtitle || 'Bankalar Arası Veri Kıyaslaması')}</p>`;

          if (chart.stats) {
              const kutu = (etiket, deger) => `
                  <div style="flex: 1; padding: 10px; border: 1px solid #e5e7eb; border-radius: 8px; text-align: center;">
                      <strong style="font-size: 10px; color: #6b7280; display: block;">${etiket}</strong>
                      <span style="font-size: 18px; font-weight: bold;">${escapeHtml(degeriBicimlendir(chart, deger))}</span>
                  </div>`;
              html += `<div style="display: flex; gap: 15px; margin-bottom: 20px;">
                  ${kutu('ORTALAMA', chart.stats.avg)}
                  ${kutu('EN DÜŞÜK', chart.stats.min)}
                  ${kutu('EN YÜKSEK', chart.stats.max)}
              </div>`;
          }

          if (satirlar.length) {
              html += `<table style="width: 100%; border-collapse: collapse; font-size: 12px;">
                  <thead><tr style="background-color: #f3f4f6;">
                      <th style="padding: 8px; border: 1px solid #d1d5db; text-align: left;">Banka / Kurum</th>
                      <th style="padding: 8px; border: 1px solid #d1d5db; text-align: left;">Kampanya Detayı</th>
                      <th style="padding: 8px; border: 1px solid #d1d5db; text-align: right;">Değer</th>
                  </tr></thead><tbody>`;
              satirlar.forEach(r => {
                  html += `<tr>
                      <td style="padding: 8px; border: 1px solid #d1d5db;"><strong>${escapeHtml(r.banka)}</strong></td>
                      <td style="padding: 8px; border: 1px solid #d1d5db;">${escapeHtml(r.kampanya)}</td>
                      <td style="padding: 8px; border: 1px solid #d1d5db; text-align: right; font-weight: bold;">${escapeHtml(r.metinDeger)}</td>
                  </tr>`;
              });
              html += `</tbody></table>`;
          }
      }

      html += `</div>`;

      const tempDiv = document.createElement('div');
      tempDiv.innerHTML = html;

      await window.html2pdf().set({
          margin:       0.5,
          filename:     `FinAgent_Rapor_${new Date().getTime()}.pdf`,
          image:        { type: 'jpeg', quality: 0.98 },
          html2canvas:  { scale: 2 },
          jsPDF:        { unit: 'in', format: 'a4', orientation: 'portrait' },
          // Uzun analiz metni + tablo birden fazla sayfaya taşabiliyor;
          // satırların sayfa ortasından bölünmemesi için sayfa sonu kuralı.
          pagebreak:    { mode: ['avoid-all', 'css', 'legacy'] },
      }).from(tempDiv).save();

  } catch (err) {
      console.error('Rapor oluşturulurken hata:', err);
      showToast(`${t('chat.report_error', "Rapor oluşturulamadı")}: ${err.message}`);
  } finally {
      isExporting.value[index] = false;
  }
}

const fileInput = ref(null)
const selectedFiles = ref([])
const maxFiles = 3
const isDragging = ref(false)
const dragCount = ref(0) 

const chatContainer = ref(null)
const scrollAnchor = ref(null) 

const getObjectUrl = (file) => {
  try { return URL.createObjectURL(file); } 
  catch (e) { return ''; }
}

// HATA DÜZELTMESİ (gerçek chatStore.js görülünce doğrulandı): Bu onMounted
// önceden useState('sharedPrompt')/useState('sharedFiles')'ı okuyordu — ama
// ChatPrompt.vue verileri Pinia store'un `initialPrompt`/`initialFiles`
// alanlarına yazıyor (bkz. chatStore.js: setChatData(prompt, files) bunları
// dolduruyor). Bu iki mekanizma birbirinden habersizdi; `chatStore` bu dosyada
// zaten import edilip oluşturuluyordu (üstte, satır 15) ama BİR KEZ bile
// kullanılmıyordu. Artık asıl kaynak — Pinia store — okunuyor ve tüketildikten
// sonra store'un kendi clearChatData() eylemiyle temizleniyor (aynı sayfaya
// tekrar dönüldüğünde eski prompt/dosyaların yeniden gönderilmemesi için).
onMounted(() => {
  requestAnimationFrame(() => { mounted.value = true })
  if (chatStore.initialPrompt || chatStore.initialFiles.length > 0) {
    userMessage.value = chatStore.initialPrompt
    selectedFiles.value = [...chatStore.initialFiles]
    chatStore.clearChatData()
    setTimeout(() => { sendMessage() }, 500)
  }
})

const goHome = () => navigateTo('/')
const triggerFileInput = () => fileInput.value.click()

const handleFileSelect = (event) => {
  const files = Array.from(event.target.files)
  if (selectedFiles.value.length + files.length > maxFiles) {
    showToast(t('chat.max_files', 'En fazla {max} dosya yükleyebilirsiniz.', { max: maxFiles }))
    event.target.value = '' 
    return
  }
  selectedFiles.value.push(...files)
  event.target.value = '' 
}

const handlePaste = (e) => {
  const items = (e.clipboardData || window.clipboardData).items;
  let hasFile = false;
  
  for (let item of items) {
    if (item.kind === 'file') {
      const file = item.getAsFile();
      if (file) {
        if (selectedFiles.value.length >= maxFiles) {
          showToast(t('chat.max_files', 'En fazla {max} dosya yükleyebilirsiniz.', { max: maxFiles }));
          return;
        }
        isDragging.value = true;
        setTimeout(() => { isDragging.value = false }, 300);
        selectedFiles.value.push(file);
        hasFile = true;
      }
    }
  }
}

const handleDragEnter = (e) => { e.preventDefault(); dragCount.value++; isDragging.value = true; }
const handleDragLeave = (e) => { e.preventDefault(); dragCount.value--; if (dragCount.value === 0) isDragging.value = false; }
const handleDrop = (event) => {
  event.preventDefault()
  dragCount.value = 0
  isDragging.value = false
  if (event.dataTransfer && event.dataTransfer.files) {
      const files = Array.from(event.dataTransfer.files)
      if (selectedFiles.value.length + files.length > maxFiles) {
        showToast(t('chat.max_files', 'En fazla {max} dosya yükleyebilirsiniz.', { max: maxFiles }))
        return
      }
      selectedFiles.value.push(...files)
  }
}

const removeFile = (index) => {
  selectedFiles.value.splice(index, 1)
  if (selectedFiles.value.length === 0 && fileInput.value) fileInput.value.value = ''
}

const clearFiles = () => {
  selectedFiles.value = []
  if (fileInput.value) fileInput.value.value = ''
}

const scrollToBottom = () => {
  nextTick(() => {
    if (scrollAnchor.value) {
      scrollAnchor.value.scrollIntoView({ behavior: 'smooth', block: 'end' })
    }
  })
}

const sendSuggestedPrompt = (text) => {
    userMessage.value = text;
    sendMessage();
}

const determineIcon = (text) => {
    if (!text) return 'robot';
    const lower = text.toLowerCase();
    if (lower.includes('mongo') || lower.includes('veritabanı') || lower.includes('redis') || lower.includes('cache')) return 'database';
    if (lower.includes('qdrant') || lower.includes('vektör') || lower.includes('taranıyor')) return 'search';
    if (lower.includes('rerank') || lower.includes('optimize')) return 'sort';
    if (lower.includes('dosya') || lower.includes('belge') || lower.includes('işlem')) return 'file';
    if (lower.includes('düşünme') || lower.includes('analiz') || lower.includes('karar')) return 'brain';
    return 'robot';
}

const formatMessage = (text, hasChart = false) => {
  if (!text) return '';
  let html = text.trim().replace(/</g, '&lt;').replace(/>/g, '&gt;');
  html = html.replace(/\n{3,}/g, '\n\n');
  html = html.replace(/```(?:mermaid|pie)[\s\S]*?```/gi, ''); 
  html = html.replace(/pie chart title[\s\S]*?(?=\n\n|\n[A-Z])/gi, ''); 

  // TOKAT 6: EĞER CHART GELDİYSE LLM'İN ÇİZİM YAPMASINI (Markdown Tablo) ENGELLİYORUZ
  if (hasChart) {
      html = html.replace(/(?:^[ \t]*\|.*(?:\n|$))+/gm, '');
  } else {
      html = html.replace(/(?:^[ \t]*\|.*(?:\n|$))+/gm, (match) => {
        const lines = match.trim().split('\n');
        if (lines.length === 0) return match; 
        let tableHtml = '<div class="overflow-x-auto my-6 shadow-sm rounded-xl border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-800/80 transition-all duration-300"><table class="w-full text-sm text-left border-collapse">';
        let isBody = false;
        lines.forEach((line, index) => {
          if (line.match(/^[ \t]*\|[\s\-\.:]+\|/)) { isBody = true; return; }
          let rowContent = line.replace(/^[ \t]*\||\|[ \t]*$/g, ''); 
          rowContent = rowContent.replace(/&lt;br\s*\/?[&gt;]?/gi, '<br class="mt-2 mb-1">');
          rowContent = rowContent.replace(/(?:&amp;)?(?:&gt;|gt;)\s*[\*•-]?/gi, '<br class="mt-2 mb-1"><span class="text-blue-500 font-bold mr-1.5">•</span>');
          rowContent = rowContent.replace(/&lt;\/?span[^&]*&gt;/gi, '');
          rowContent = rowContent.replace(/&lt;\/?small[^&]*&gt;/gi, '');
          rowContent = rowContent.replace(/&lt;\/?ins[^&]*&gt;/gi, '');
          const cells = rowContent.split('|');
          tableHtml += '<tr class="border-b border-neutral-200 dark:border-neutral-700 hover:bg-neutral-50 dark:hover:bg-neutral-800/40 transition-colors">';
          cells.forEach(cell => {
            if (!isBody && index === 0) { 
              tableHtml += `<th class="px-5 py-4 bg-neutral-100/80 dark:bg-neutral-800/90 font-bold text-neutral-800 dark:text-neutral-200 border-r border-neutral-200 dark:border-neutral-700 last:border-0 align-top whitespace-nowrap min-w-[120px]">${cell.trim()}</th>`;
            } else { 
              tableHtml += `<td class="px-5 py-4 text-neutral-600 dark:text-neutral-300 border-r border-neutral-200 dark:border-neutral-700 last:border-0 align-top leading-relaxed break-words min-w-[120px]">${cell.trim()}</td>`;
            }
          });
          tableHtml += '</tr>';
        });
        tableHtml += '</table></div>\n';
        return tableHtml;
      });
  }
  
  html = html
    .replace(/```[a-zA-Z]*\n?([\s\S]*?)```/g, '<pre class="bg-neutral-800 text-neutral-100 p-4 rounded-xl my-3 overflow-x-auto text-sm font-mono shadow-inner border border-neutral-700 hover:shadow-lg transition-shadow duration-300"><code>$1</code></pre>')
    .replace(/`([^`\n]+)`/g, '<code class="bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 px-1 py-0.5 rounded text-sm font-mono">$1</code>')
    .replace(/^#### (.*$)/gm, '<h4 class="text-base font-bold mt-4 mb-1 text-neutral-800 dark:text-neutral-200">$1</h4>')
    .replace(/^### (.*$)/gm, '<h3 class="text-lg font-bold mt-4 mb-1.5 text-blue-600 dark:text-blue-400">$1</h3>')
    .replace(/^## (.*$)/gm, '<h2 class="text-xl font-bold mt-5 mb-2 text-neutral-900 dark:text-white border-b border-neutral-200 dark:border-neutral-700 pb-1">$1</h2>')
    .replace(/^# (.*$)/gm, '<h1 class="text-2xl font-bold mt-5 mb-2 text-blue-600 dark:text-blue-400">$1</h1>')
    .replace(/\*\*(.*?)\*\*/g, '<strong class="font-bold text-neutral-900 dark:text-white">$1</strong>')
    .replace(/\b_(.*?)_\b/g, '<em class="italic text-neutral-700 dark:text-neutral-300">$1</em>')
    .replace(/^\s*[\-\*]\s+(.*$)/gm, '<li class="ml-5 list-disc marker:text-blue-500 mb-0.5 hover:text-blue-600 transition-colors cursor-default">$1</li>')
    .replace(/^>\s+(.*$)/gm, '<blockquote class="border-l-4 border-blue-500 pl-4 my-2 text-neutral-600 dark:text-neutral-400 italic bg-blue-50 dark:bg-blue-900/10 py-2 rounded-r-lg hover:border-l-8 transition-all duration-300">$1</blockquote>');
    
  html = html.replace(/(<\/h[1-4]>|<\/li>|<\/blockquote>|<\/pre>|<\/div>)\n+/g, '$1\n');
  html = html.replace(/\n+(<h[1-4]|<li|<blockquote|<pre|<div class="overflow-x-auto)/g, '\n$1');
  html = html.replace(/&lt;br\s*\/?[&gt;]/gi, '<br>');
  return html;
}

const sendMessage = async () => {
  if (!userMessage.value.trim() && selectedFiles.value.length === 0) return

  const text = userMessage.value || `${selectedFiles.value.length} ${t('chat.files_sent', 'dosya gönderildi.')}`
  
  const attachedFiles = selectedFiles.value.map(f => ({ name: f.name, type: f.type, isImage: f.type.startsWith('image/'), url: getObjectUrl(f) }))
  
  chatHistory.value.push({ role: 'user', content: text, files: attachedFiles })
  const historyToSend = chatHistory.value.slice(0, -1).map(msg => ({ role: msg.role, content: msg.content }))

  const formData = new FormData()
  formData.append('prompt', text)
  formData.append('model', 'qwen3.5:4b') 
  formData.append('thinking', 'auto') 
  formData.append('history', JSON.stringify(historyToSend))
  
  let finalLang = 'tr'
  let finalMode = 'musteri'
  
  if (typeof window !== 'undefined') {
      finalLang = localStorage.getItem('language') || locale.value || 'tr'
      finalMode = localStorage.getItem('viewMode') || 'musteri'
  }

  formData.append('view_mode', finalMode)
  formData.append('language', finalLang)

  selectedFiles.value.forEach(file => formData.append('files', file))

  chatHistory.value.push({
    role: 'assistant', content: '', sources: null, chart: null, statuses: [],
    currentStatus: null, activeTimer: '0.0', isStatusExpanded: false, isFinished: false,
    isSourcesExpanded: false, suggestions: [],
    // YENİ: "Detaylı Kampanya Kıyaslaması" bölümü için banka filtresi.
    // Boş dizi = filtre yok (hepsi görünür). Bu alan SADECE o bölümü etkiler;
    // pasta grafik, istatistik kutuları ve alttaki tam veri tablosu
    // kasıtlı olarak filtreden ETKİLENMEZ (kullanıcı isteği: "grafik değişmesin").
    selectedBanks: []
  });
  const aIdx = chatHistory.value.length - 1;

  // DÜRÜST STATUS: Buradaki etiketler istek GÖNDERİLMEDEN ÖNCE basılıyor,
  // yani gerçek bir işin süresini ölçmüyorlar.
  //   - "Sohbet geçmişi taranıyor" KALDIRILDI: sadece historyToSend.length > 0
  //     kontrolüydü, arkasında hiçbir iş yoktu; bu yüzden hep 0.0s görünüyordu.
  //     Geçmiş gerçekten kullanıldığında artık backend [STATUS] gönderiyor.
  //   - "Belgeler analiz ediliyor" KALDI: dosyalar bu aşamada (istek gövdesi
  //     yüklenirken ve sunucuda parse edilirken) gerçekten işleniyor.
  let activeTasks = [];
  if (selectedFiles.value.length > 0) activeTasks.push(t('chat.docs_analyzing', "Belgeler analiz ediliyor"));

  userMessage.value = ''
  isLoading.value = true 
  isStreaming.value = true
  clearFiles()
  scrollToBottom()

  let statusInterval = null;
  const startTimer = () => {
      clearInterval(statusInterval);
      chatHistory.value[aIdx].activeTimer = '0.0';
      statusInterval = setInterval(() => {
          const cur = chatHistory.value[aIdx].currentStatus;
          if (cur) chatHistory.value[aIdx].activeTimer = ((performance.now() - cur.startTime) / 1000).toFixed(1);
      }, 100);
  };

  const updateStatus = (statusText) => {
      if (chatHistory.value[aIdx].isFinished) return;
      const now = performance.now();
      const cur = chatHistory.value[aIdx].currentStatus;
      if (cur) { 
          cur.endTime = now;
          cur.duration = ((now - cur.startTime) / 1000).toFixed(1);
          chatHistory.value[aIdx].statuses.push({...cur});
      }
      chatHistory.value[aIdx].currentStatus = {
          text: statusText, startTime: now, endTime: null, duration: '0.0', icon: determineIcon(statusText)
      };
      startTimer();
  };

  const finishStatus = () => {
      if (chatHistory.value[aIdx].isFinished) return;
      const now = performance.now();
      const cur = chatHistory.value[aIdx].currentStatus;
      if (cur) {
          cur.endTime = now;
          cur.duration = ((now - cur.startTime) / 1000).toFixed(1);
          chatHistory.value[aIdx].statuses.push({...cur});
          chatHistory.value[aIdx].currentStatus = null;
      }
      chatHistory.value[aIdx].isFinished = true;
      clearInterval(statusInterval);
  };

  if (activeTasks.length > 0) updateStatus(activeTasks.join(" > ") + " " + t('chat.starting', 'başlatılıyor...'));
  else updateStatus(t('chat.process_starting', "İşlem başlatılıyor..."));

  let buffer = '';

  try {
    const response = await fetch('http://localhost:8003/api/chat', { method: 'POST', body: formData })
    if (!response.body) throw new Error('Akış başlatılamadı.')
    const reader = response.body.getReader()
    const decoder = new TextDecoder()

    while (true) {
      const { value, done } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })

      let statusRegex = /\[STATUS\]([\s\S]*?)\[\/STATUS\]/g;
      let match;
      while ((match = statusRegex.exec(buffer)) !== null) { updateStatus(match[1]); }
      buffer = buffer.replace(/\[STATUS\][\s\S]*?\[\/STATUS\]/g, '');

      let sourceRegex = /\[SOURCES\]([\s\S]*?)\[\/SOURCES\]/g;
      let matchSource;
      while ((matchSource = sourceRegex.exec(buffer)) !== null) {
          try { chatHistory.value[aIdx].sources = JSON.parse(matchSource[1]); scrollToBottom(); } 
          catch(e) { console.error("Kaynak parse hatası", e) }
      }
      buffer = buffer.replace(/\[SOURCES\][\s\S]*?\[\/SOURCES\]/g, '');

      let chartRegex = /\[CHART\]([\s\S]*?)\[\/CHART\]/g;
      let matchChart;
      while ((matchChart = chartRegex.exec(buffer)) !== null) {
          try { chatHistory.value[aIdx].chart = JSON.parse(matchChart[1]); scrollToBottom(); } 
          catch(e) { console.error("Grafik Parse Hatası", e) }
      }
      buffer = buffer.replace(/\[CHART\][\s\S]*?\[\/CHART\]/g, '');

      let sugRegex = /\[SUGGESTIONS?\]([\s\S]*?)\[\/SUGGESTIONS?\]/g;
      let matchSug;
      while ((matchSug = sugRegex.exec(buffer)) !== null) {
          try {
              const parsedSug = JSON.parse(matchSug[1].trim());
              if (Array.isArray(parsedSug)) {
                  chatHistory.value[aIdx].suggestions = parsedSug;
              }
              scrollToBottom();
          } catch(e) { console.error("Öneri JSON parse hatası:", e) }
      }
      buffer = buffer.replace(/\[SUGGESTIONS?\][\s\S]*?\[\/SUGGESTIONS?\]/g, '');

      let pSourceIdx = buffer.lastIndexOf('[SOURCES');
      if (pSourceIdx !== -1 && buffer.indexOf('[/SOURCES]', pSourceIdx) === -1) continue;
      let pChartIdx = buffer.lastIndexOf('[CHART');
      if (pChartIdx !== -1 && buffer.indexOf('[/CHART]', pChartIdx) === -1) continue;
      let pStatIdx = buffer.lastIndexOf('[STATUS');
      if (pStatIdx !== -1 && buffer.indexOf('[/STATUS]', pStatIdx) === -1) continue; 
      let pSugIdx = buffer.lastIndexOf('[SUGGESTION');
      if (pSugIdx !== -1 && buffer.indexOf('[/SUGGESTION', pSugIdx) === -1) continue;

      // Elle yazılmış kısmi etiket listesi EKSİKTİ: "[SO", "[SOU", "[SOUR",
      // "[SOURC", "[SOURCE", "[SOURCES", "[SOURCES]" ve "[SUGGESTIONS]" listede
      // yoktu. Akış parçası tam o noktalarda bölünürse yarım etiket cevabın
      // içine yazılıyordu (ekranda "...oluyor?[SOURCES" gibi artıklar).
      // Artık liste elle tutulmuyor; bilinen etiketlerin TÜM ön ekleri
      // otomatik kontrol ediliyor.
      if (kismiEtiketMi(buffer)) continue;

      if (buffer.length > 0) {
        chatHistory.value[aIdx].content += buffer;
        buffer = '';
        scrollToBottom();
      }
    }
    if (buffer.length > 0) {
        chatHistory.value[aIdx].content += buffer;
    }
  } catch (error) {
    console.error('Akış sırasında hata:', error)
    chatHistory.value[aIdx].content = t('chat.server_error', 'Üzgünüm, sunucuyla iletişim kurulamadı.')
  } finally {
    finishStatus(); 
    isLoading.value = false
    isStreaming.value = false 
    scrollToBottom()
  }
}
</script>

<template>
  <div class="relative w-full h-screen flex flex-col transition-colors duration-500 ease-in-out bg-neutral-50 dark:bg-neutral-900 overflow-hidden" 
       @dragenter.prevent="handleDragEnter" 
       @dragover.prevent 
       @dragleave.prevent="handleDragLeave" 
       @drop.prevent="handleDrop">

    <!-- EKSİK ÖZELLİK: isDragging/handleDragEnter/handleDragLeave/handleDrop
         script'te zaten vardı ve dış div'e bağlıydı (sürükleme TEKNİK OLARAK
         çalışıyordu) ama hiçbir GÖRSEL geri bildirimi yoktu — kullanıcı bir dosyayı
         sayfanın üzerine sürüklediğinde hiçbir şey olmuyormuş gibi görünüyordu
         (ChatPrompt.vue'deki "Buraya Bırakın" katmanının burada karşılığı yoktu). -->
    <Transition
      enter-active-class="transition duration-200 ease-out"
      enter-from-class="opacity-0"
      enter-to-class="opacity-100"
      leave-active-class="transition duration-150 ease-in"
      leave-from-class="opacity-100"
      leave-to-class="opacity-0"
    >
      <div v-if="isDragging" class="fixed inset-4 z-[150] flex items-center justify-center border-2 border-dashed border-blue-500 bg-blue-500/10 dark:bg-blue-500/15 rounded-[32px] pointer-events-none backdrop-blur-[2px]">
        <div class="flex flex-col items-center gap-3 text-blue-600 dark:text-blue-400">
          <svg class="w-10 h-10" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13"></path></svg>
          <span class="text-base font-bold">{{ t('chat.drop_here', 'Dosyaları buraya bırakın') }}</span>
        </div>
      </div>
    </Transition>

    <Transition enter-active-class="transition duration-300 ease-out" enter-from-class="opacity-0 -translate-y-4" enter-to-class="opacity-100 translate-y-0" leave-active-class="transition duration-200 ease-in" leave-from-class="opacity-100 translate-y-0" leave-to-class="opacity-0 -translate-y-4">
      <div v-if="toastMessage" class="fixed top-10 left-1/2 -translate-x-1/2 z-[200] bg-neutral-800 text-white px-6 py-3 rounded-full shadow-2xl flex items-center gap-3">
        <svg class="w-5 h-5 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
        <span class="text-sm font-medium">{{ toastMessage }}</span>
      </div>
    </Transition>

    <div class="flex-1 w-full relative flex overflow-hidden">
      <div class="flex-1 h-full flex flex-col transition-all duration-500 ease-[cubic-bezier(0.4,0,0.2,1)]" :class="showSourceModal ? 'lg:pr-[380px] lg:mr-[10px]' : 'pr-0'">
        <div ref="chatContainer" class="flex-1 overflow-y-auto px-4 py-6 custom-scrollbar scroll-smooth">
          
          <div class="w-full flex flex-col space-y-6 pb-4" :class="mounted ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-10'">
            
            <TransitionGroup name="msg" appear>
              <div v-for="(msg, index) in chatHistory" :key="index" class="w-full flex flex-col msg-item">
                
                <!-- KULLANICI MESAJI -->
                <div v-if="msg.role === 'user'" class="flex justify-end w-full max-w-4xl mx-auto">
                  <div class="bg-gradient-to-tr from-blue-600 to-blue-500 text-white rounded-t-2xl rounded-bl-2xl rounded-br-sm px-5 py-3.5 max-w-[85%] shadow-md text-left leading-relaxed flex flex-col gap-3 group transform transition-all duration-300 hover:-translate-y-0.5 hover:shadow-lg">
                    
                    <div v-if="msg.files && msg.files.length > 0" class="flex flex-wrap gap-3 mb-1">
                      <div v-for="(file, fIdx) in msg.files" :key="fIdx" 
                           @click="openUserFile(file)"
                           class="relative group/file overflow-hidden rounded-xl cursor-pointer transform transition-all duration-500 hover:-translate-y-1 hover:shadow-[0_10px_20px_rgba(0,0,0,0.2)] ring-2 ring-transparent hover:ring-white/30">
                        
                        <template v-if="file.isImage">
                          <img :src="file.url" class="max-w-[140px] max-h-[140px] sm:max-w-[180px] sm:max-h-[180px] object-cover transition-transform duration-700 group-hover/file:scale-110" />
                          <div class="absolute inset-0 bg-gradient-to-t from-black/60 via-black/20 to-transparent opacity-0 group-hover/file:opacity-100 transition-opacity duration-300 flex flex-col justify-end p-2">
                             <div class="flex items-center justify-center absolute inset-0">
                                 <svg class="w-8 h-8 text-white drop-shadow-md scale-50 group-hover/file:scale-100 transition-transform duration-300 ease-out-back" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0zM10 7v3m0 0v3m0-3h3m-3 0H7"></path></svg>
                             </div>
                          </div>
                        </template>
                        
                        <template v-else>
                          <div class="flex flex-col items-center justify-center gap-2 bg-blue-700/50 backdrop-blur-md px-4 py-4 w-[140px] h-[140px] transition-colors duration-300 group-hover/file:bg-blue-800/80 relative">
                            <svg class="w-10 h-10 text-white/80 group-hover/file:text-white transition-all group-hover/file:scale-110 group-hover/file:-translate-y-1 duration-300" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z"></path></svg>
                            <span class="text-[10px] text-center line-clamp-2 font-medium text-white/90 group-hover/file:text-white transition-colors" :title="file.name">{{ file.name }}</span>
                            <div class="absolute inset-0 bg-black/40 opacity-0 group-hover/file:opacity-100 transition-opacity duration-300 flex items-center justify-center">
                                <svg class="w-8 h-8 text-white scale-50 group-hover/file:scale-100 transition-transform duration-300 ease-out-back" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4-4m0 0l-4-4m4 4V4"></path></svg>
                            </div>
                          </div>
                        </template>

                      </div>
                    </div>

                    <span class="whitespace-pre-wrap">{{ msg.content }}</span>
                  </div>
                </div>

                <!-- ASİSTAN MESAJI -->
                <div v-else class="flex flex-col w-full py-2 space-y-4">
                    
                    <div class="flex gap-4 w-full max-w-4xl mx-auto text-neutral-800 dark:text-neutral-100">
                        <div class="mt-1 flex-shrink-0 w-8 h-8 flex items-center justify-center rounded-full bg-gradient-to-br from-blue-500 to-cyan-500 text-white shadow-lg ring-4 ring-blue-50 dark:ring-blue-900/30 transform transition-transform hover:scale-110 hover:rotate-3 duration-300">
                            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"></path></svg>
                        </div>
                        <div class="flex-1 min-w-0">
                            <div v-if="msg.statuses?.length > 0 || msg.currentStatus" class="max-w-[24rem]"> 
                                
                                <div class="bg-white dark:bg-neutral-800/80 border border-neutral-200 dark:border-neutral-700/60 rounded-xl w-full transition-all duration-300 flex flex-col relative overflow-hidden"
                                     :class="!msg.isFinished ? 'shadow-[0_0_15px_rgba(59,130,246,0.15)] ring-1 ring-blue-400/30' : 'shadow-sm'">
                                    
                                    <div v-if="!msg.isFinished" class="absolute inset-0 bg-gradient-to-r from-blue-50/50 via-cyan-50/50 to-blue-50/50 dark:from-blue-900/10 dark:via-cyan-900/10 dark:to-blue-900/10 opacity-50 animate-gradient-x pointer-events-none"></div>

                                    <div class="flex items-center justify-between px-3 py-2.5 relative z-10 bg-white dark:bg-neutral-800/80" 
                                        :class="[msg.statuses?.length > 0 ? 'cursor-pointer hover:bg-neutral-50 dark:hover:bg-neutral-700/40' : '', msg.isStatusExpanded && msg.statuses?.length > 0 ? 'border-b border-neutral-100 dark:border-neutral-700/50' : '']"
                                        @click="toggleStatus(msg)">
                                        <div class="flex items-center gap-2.5 flex-1 min-w-0" v-if="!msg.isFinished && msg.currentStatus">
                                            <div class="w-4 h-4 flex items-center justify-center shrink-0">
                                                <svg v-if="msg.currentStatus.icon === 'database'" class="w-3.5 h-3.5 text-blue-500 animate-pulse" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4"></path></svg>
                                                <svg v-else-if="msg.currentStatus.icon === 'search'" class="w-3.5 h-3.5 text-purple-500 animate-[spin_3s_linear_infinite]" fill="none" viewBox="0 0 24 24" stroke="currentColor"><circle cx="11" cy="11" r="8" stroke-width="2"></circle><line x1="21" y1="21" x2="16.65" y2="16.65" stroke-width="2"></line></svg>
                                                <svg v-else-if="msg.currentStatus.icon === 'sort'" class="w-3.5 h-3.5 text-amber-500 animate-pulse" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h7"></path></svg>
                                                <svg v-else-if="msg.currentStatus.icon === 'file'" class="w-3.5 h-3.5 text-emerald-500 animate-pulse" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z"></path></svg>
                                                <svg v-else-if="msg.currentStatus.icon === 'brain'" class="w-3.5 h-3.5 text-pink-500 animate-pulse" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"></path></svg>
                                                <DotMatrix v-else :size="2" :dot-size="4" :gap="2" color="#3b82f6" :speed="1.2" />
                                            </div>
                                            <Transition name="fade-text" mode="out-in">
                                                <span :key="msg.currentStatus.text" class="text-[12px] font-medium text-neutral-800 dark:text-neutral-200 truncate">{{ msg.currentStatus.text }}</span>
                                            </Transition>
                                        </div>
                                        <div class="flex items-center gap-2.5 flex-1 min-w-0" v-else-if="msg.isFinished">
                                            <svg class="w-3.5 h-3.5 text-emerald-500 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path></svg>
                                            <span class="text-[12px] font-medium text-neutral-700 dark:text-neutral-300 truncate">{{ msg.statuses?.length > 0 ? msg.statuses[msg.statuses.length - 1].text : t('chat.process_completed', 'İşlem tamamlandı') }}</span>
                                        </div>
                                        <div class="flex items-center gap-1.5 pl-2 shrink-0">
                                            <span v-if="!msg.isFinished && msg.currentStatus" class="text-[10px] font-mono text-neutral-400 w-6 text-right">{{ msg.activeTimer }}s</span>
                                            <span v-else-if="msg.isFinished && msg.statuses?.length > 0" class="text-[10px] font-mono text-neutral-400 w-8 text-right">{{ (msg.statuses.reduce((acc, s) => acc + parseFloat(s.duration), 0)).toFixed(1) }}s</span>
                                            <div v-if="msg.statuses?.length > 0" class="bg-neutral-100 dark:bg-[#2a2a2a] border border-neutral-200 dark:border-[#3a3a3a] w-6 h-4 rounded-md flex items-center justify-center transition-transform duration-500" :class="{'rotate-180': msg.isStatusExpanded}">
                                                <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" class="text-neutral-500 dark:text-[#a3a3a3]" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"></polyline></svg>
                                            </div>
                                        </div>
                                    </div>
                                    <div class="grid transition-all duration-500 ease-in-out bg-neutral-50/50 dark:bg-neutral-900/30" :class="msg.isStatusExpanded && msg.statuses?.length > 0 ? 'grid-rows-[1fr] opacity-100' : 'grid-rows-[0fr] opacity-0'">
                                        <div class="overflow-hidden">
                                            <div class="flex flex-col max-h-40 overflow-y-auto custom-scrollbar">
                                                <div v-for="(stat, idx) in msg.statuses" :key="idx" class="flex items-center justify-between px-3 py-1.5 border-b border-neutral-100 dark:border-neutral-700/50 last:border-0 hover:bg-neutral-100/50 dark:hover:bg-neutral-700/30 transition-colors">
                                                    <div class="flex items-center gap-2 text-neutral-500 dark:text-neutral-400 min-w-0">
                                                        <svg class="w-3 h-3 text-emerald-500 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path></svg>
                                                        <span class="text-[11px] truncate">{{ stat.text }}</span>
                                                    </div>
                                                    <span class="text-[10px] font-mono text-neutral-400 shrink-0">{{ stat.duration }}s</span>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>

                    <Transition enter-active-class="transition-all duration-700 ease-out" leave-active-class="transition-all duration-500 ease-in absolute w-full" enter-from-class="opacity-0 translate-y-4" leave-to-class="opacity-0 -translate-y-4">
                        <div v-if="!msg.isFinished && !msg.chart && isExpectingChart(msg) && !msg.content" class="w-full max-w-[98%] 2xl:max-w-[1600px] mx-auto bg-white dark:bg-neutral-800/50 rounded-2xl border border-neutral-200 dark:border-neutral-700 shadow-sm p-6 overflow-hidden relative z-0 hover:shadow-md transition-shadow duration-300">
                            <div class="absolute inset-0 -translate-x-full animate-[shimmer_1.5s_infinite] bg-gradient-to-r from-transparent via-white/40 dark:via-white/5 to-transparent z-10"></div>
                            <div class="flex items-center justify-between gap-4 mb-8 relative z-0">
                                <div class="flex items-center gap-3">
                                    <div class="w-10 h-10 rounded-xl bg-neutral-200 dark:bg-neutral-700 animate-pulse"></div>
                                    <div class="space-y-2">
                                        <div class="h-3 w-32 bg-neutral-200 dark:bg-neutral-700 rounded-md animate-pulse"></div>
                                        <div class="h-2 w-48 bg-neutral-200 dark:bg-neutral-700 rounded-md animate-pulse"></div>
                                    </div>
                                </div>
                            </div>
                            <div class="flex flex-col md:flex-row gap-6 relative z-0">
                                <div class="w-full md:w-1/3 flex flex-col items-center pr-4 md:border-r border-neutral-100 dark:border-neutral-700/50">
                                    <div class="w-40 h-40 rounded-full border-8 border-neutral-100 dark:border-neutral-700 animate-pulse shrink-0 mb-6"></div>
                                    <div class="w-full space-y-3">
                                        <div v-for="i in 4" :key="'sk-leg-'+i" class="flex items-center gap-2">
                                            <div class="w-2 h-2 rounded-full bg-neutral-200 dark:bg-neutral-700 animate-pulse shrink-0"></div>
                                            <div class="h-2 w-full bg-neutral-200 dark:bg-neutral-700 rounded animate-pulse"></div>
                                        </div>
                                    </div>
                                </div>
                                <div class="w-full md:w-2/3 flex flex-col space-y-4">
                                    <div class="h-3 w-40 bg-neutral-200 dark:bg-neutral-700 rounded animate-pulse mb-2"></div>
                                    <div v-for="i in 8" :key="'sk-bar-'+i" class="space-y-1.5">
                                        <div class="flex justify-between">
                                            <div class="h-2 bg-neutral-200 dark:bg-neutral-700 rounded animate-pulse" :style="`width: ${30 + ((i * 7) % 30)}%`"></div>
                                            <div class="h-2 w-8 bg-neutral-200 dark:bg-neutral-700 rounded animate-pulse"></div>
                                        </div>
                                        <div class="h-2 w-full bg-neutral-100 dark:bg-neutral-700/50 rounded-full overflow-hidden">
                                            <div class="h-full bg-neutral-200 dark:bg-neutral-600 rounded-full animate-pulse" :style="`width: ${40 + ((i * 13) % 45)}%`"></div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </Transition>

                    <Transition enter-active-class="transition-all duration-700 ease-out" enter-from-class="opacity-0 scale-95 translate-y-4" enter-to-class="opacity-100 scale-100 translate-y-0">
                        <div v-if="msg.chart" :id="'chart-container-' + index" class="w-full max-w-[98%] 2xl:max-w-[1600px] mx-auto relative z-20 mb-6">
                            
                            <div data-png-gizle class="flex justify-end gap-2 mb-2 w-full">
                                <button @click="exportToExcel(index)" :title="t('chat.download_excel_title', 'Excel Olarak İndir')" class="p-2 bg-green-50 dark:bg-green-900/20 text-green-600 dark:text-green-400 border border-green-200 dark:border-green-800/50 rounded-lg hover:bg-green-100 dark:hover:bg-green-900/40 transition-all shadow-sm hover:shadow active:scale-95 disabled:opacity-50 group">
                                    <svg class="w-4 h-4 group-hover:-translate-y-0.5 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 10h18M3 14h18m-9-4v8m-7 0h14a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"></path></svg>
                                </button>
                                <button @click="exportToPDF(index)" :title="t('chat.create_pdf_title', 'PDF Raporu Oluştur')" class="p-2 bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 border border-red-200 dark:border-red-800/50 rounded-lg hover:bg-red-100 dark:hover:bg-red-900/40 transition-all shadow-sm hover:shadow active:scale-95 disabled:opacity-50 group">
                                    <svg class="w-4 h-4 group-hover:-translate-y-0.5 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path></svg>
                                </button>
                                <button @click="exportToPNG(index)" :title="t('chat.save_png_title', 'Grafiği PNG Olarak Kaydet')" class="p-2 bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400 border border-blue-200 dark:border-blue-800/50 rounded-lg hover:bg-blue-100 dark:hover:bg-blue-900/40 transition-all shadow-sm hover:shadow active:scale-95 disabled:opacity-50 group">
                                    <svg v-if="!isExportingPNG[index]" class="w-4 h-4 group-hover:-translate-y-0.5 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"></path></svg>
                                    <svg v-else class="animate-spin w-4 h-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>
                                </button>
                            </div>

                            <div class="anim-card bg-white dark:bg-neutral-800/90 rounded-2xl border border-neutral-200 dark:border-neutral-700 shadow-md hover:shadow-lg transition-shadow duration-300 overflow-hidden relative">
                                <div class="p-5 sm:p-6 border-b border-neutral-100 dark:border-neutral-700/50 flex flex-col sm:flex-row justify-between gap-4 items-start sm:items-center bg-neutral-50/50 dark:bg-neutral-800/50">
                                    <div class="flex items-center gap-3">
                                        <div class="flex items-center justify-center w-10 h-10 rounded-xl bg-blue-600 text-white shadow-sm shrink-0">
                                            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012-2v14a2 2 0 01-2-2h-2a2 2 0 01-2-2z"></path></svg>
                                        </div>
                                        <div>
                                            <h4 class="text-base sm:text-lg font-bold text-neutral-800 dark:text-neutral-100">{{ msg.chart.title || t('chat.market_analysis', 'Pazar Analizi') }}</h4>
                                            <p class="text-xs text-neutral-500 mt-0.5">{{ msg.chart.subtitle || t('chat.bank_comparison', 'Bankalar Arası Veri Kıyaslaması') }}</p>
                                        </div>
                                    </div>

                                    <!-- YENİ: Banka filtresi çipleri. Başlığın SAĞINDA durur; bir veya
                                         birden fazla banka seçilebilir. Seçim SADECE "Detaylı Kampanya
                                         Kıyaslaması" bölümünü daraltır — pasta grafik, istatistik
                                         kutuları ve alttaki tam veri tablosu değişmez. -->
                                    <div v-if="bankaSecenekleri(msg.chart).length > 1" class="flex flex-wrap items-center gap-1.5 flex-1 min-w-0 sm:px-2 order-3 sm:order-none">
                                        <span class="text-[9px] font-bold uppercase tracking-wider text-neutral-400 shrink-0">{{ t('chat.filter_banks', 'Bankalar') }}</span>
                                        <button
                                            v-for="bankaAdi in bankaSecenekleri(msg.chart)"
                                            :key="'bankfilter-' + index + '-' + bankaAdi"
                                            type="button"
                                            @click="bankaFiltresiDegistir(msg, bankaAdi)"
                                            :aria-pressed="bankaSecili(msg, bankaAdi) ? 'true' : 'false'"
                                            :title="bankaAdi"
                                            :class="bankaSecili(msg, bankaAdi)
                                                ? 'bg-blue-600 border-blue-600 text-white shadow-sm'
                                                : 'bg-white dark:bg-neutral-800 border-neutral-200 dark:border-neutral-700 text-neutral-600 dark:text-neutral-300 hover:border-blue-400 hover:text-blue-600 dark:hover:text-blue-400'"
                                            class="px-2.5 py-1 rounded-full border text-[10px] font-bold whitespace-nowrap transition-all active:scale-95">
                                            {{ bankaAdi }}
                                        </button>
                                        <button
                                            v-if="(msg.selectedBanks || []).length > 0"
                                            type="button"
                                            @click="bankaFiltresiTemizle(msg)"
                                            class="px-2 py-1 rounded-full border border-transparent text-[10px] font-bold text-neutral-400 hover:text-red-500 transition-colors whitespace-nowrap">
                                            {{ t('chat.filter_clear', 'Temizle') }}
                                        </button>
                                    </div>

                                    <div class="flex flex-wrap items-center gap-2 sm:gap-3 w-full sm:w-auto">
                                        <div v-if="msg.chart.stats" class="flex flex-wrap items-center gap-2 sm:gap-3 w-full sm:w-auto">
                                            <div :style="gecikme(0, 90)" class="anim-tile flex-1 sm:flex-none bg-white dark:bg-neutral-800 px-4 py-2 rounded-xl border border-blue-100 dark:border-blue-900/50 shadow-sm text-center transform transition-transform hover:-translate-y-0.5">
                                                <span class="block text-[8px] text-blue-500 font-bold uppercase tracking-wider mb-0.5">{{ t('chat.avg_value', 'Ortalama Değer') }}</span>
                                                <span class="text-sm font-black text-neutral-800 dark:text-neutral-100">{{ msg.chart.prefix || '' }}{{ msg.chart.stats.avg }}{{ msg.chart.suffix || '' }}</span>
                                            </div>
                                            <div :style="gecikme(1, 90)" class="anim-tile flex-1 sm:flex-none bg-white dark:bg-neutral-800 px-4 py-2 rounded-xl border border-green-100 dark:border-green-900/50 shadow-sm text-center relative overflow-hidden transform transition-transform hover:-translate-y-0.5">
                                                <div class="absolute top-0 right-0 w-6 h-6 bg-green-500/10 rounded-bl-full"></div>
                                                <span class="block text-[8px] text-green-500 font-bold uppercase tracking-wider mb-0.5">{{ t('chat.min_value', 'En Düşük') }}</span>
                                                <span class="text-sm font-black text-green-600 dark:text-green-400">{{ msg.chart.prefix || '' }}{{ msg.chart.stats.min }}{{ msg.chart.suffix || '' }}</span>
                                            </div>
                                            <div :style="gecikme(2, 90)" class="anim-tile flex-1 sm:flex-none bg-white dark:bg-neutral-800 px-4 py-2 rounded-xl border border-red-100 dark:border-red-900/50 shadow-sm text-center relative overflow-hidden transform transition-transform hover:-translate-y-0.5">
                                                <div class="absolute top-0 right-0 w-6 h-6 bg-red-500/10 rounded-bl-full"></div>
                                                <span class="block text-[8px] text-red-500 font-bold uppercase tracking-wider mb-0.5">{{ t('chat.max_value', 'En Yüksek') }}</span>
                                                <span class="text-sm font-black text-red-600 dark:text-red-400">{{ msg.chart.prefix || '' }}{{ msg.chart.stats.max }}{{ msg.chart.suffix || '' }}</span>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                                
                                <div v-if="msg.chart.type !== 'table'" class="p-5 sm:p-6 flex flex-col md:flex-row gap-8">
                                    <div class="w-full md:w-1/3 flex flex-col items-center md:border-r border-neutral-100 dark:border-neutral-700/50 pr-0 md:pr-4">
                                        <div class="anim-donut relative w-48 h-48 sm:w-52 sm:h-52 shrink-0 flex items-center justify-center mb-6">
                                            <svg :id="'doughnut-svg-' + index" viewBox="0 0 100 100" class="w-full h-full transform -rotate-90 filter drop-shadow-md">
                                                <template v-for="(slice, i) in getSvgPaths(msg.chart)" :key="'slice-'+i">
                                                    <circle v-if="slice.isCircle" cx="50" cy="50" r="40" fill="transparent" :stroke="slice.color" stroke-width="20">
                                                        <title>{{ slice.tooltipText }}</title>
                                                    </circle>
                                                    <path v-else :d="slice.d" :fill="slice.color" class="hover:opacity-80 transition-opacity cursor-pointer stroke-white dark:stroke-neutral-800" stroke-width="1.5">
                                                        <title>{{ slice.tooltipText }}</title>
                                                    </path>
                                                </template>
                                                <circle cx="50" cy="50" r="30" class="fill-white dark:fill-[#1e1e1e]" />
                                            </svg>
                                            <div class="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
                                                <span class="block text-[10px] font-bold text-neutral-400">{{ t('chat.average', 'Ortalama') }}</span>
                                                <span class="text-xl font-black text-neutral-800 dark:text-white">{{ msg.chart.prefix || '' }}{{ msg.chart.stats?.avg }}{{ msg.chart.suffix || '' }}</span>
                                            </div>
                                        </div>
                                        
                                        <div class="flex flex-col gap-2 w-full max-h-[220px] overflow-y-auto custom-scrollbar pr-2">
                                            <div v-for="(label, i) in msg.chart.labels" :key="'pie-'+i" :style="gecikme(i, 40)" class="anim-row flex items-center gap-2.5 hover:bg-neutral-50 dark:hover:bg-neutral-800 p-1.5 rounded-lg transition-colors cursor-default" :title="`${label} - ${msg.chart.sub_labels ? msg.chart.sub_labels[i] : ''} : ${msg.chart.prefix || ''}${msg.chart.values[i]}${msg.chart.suffix || ''}`">
                                                <div class="w-2.5 h-2.5 rounded-full shrink-0" :class="getChartColorClass(i)"></div>
                                                <div class="flex flex-col flex-1 min-w-0">
                                                    <div class="flex justify-between items-center gap-2">
                                                        <span class="text-[11px] font-bold text-neutral-700 dark:text-neutral-200 truncate">{{ label }}</span>
                                                        <span class="text-[11px] font-black text-neutral-900 dark:text-white shrink-0">{{ msg.chart.prefix || '' }}{{ msg.chart.values[i] }}{{ msg.chart.suffix || '' }}</span>
                                                    </div>
                                                    <span class="text-[9px] text-neutral-400 truncate">{{ msg.chart.sub_labels ? msg.chart.sub_labels[i] : '' }}</span>
                                                </div>
                                            </div>
                                        </div>
                                    </div>

                                    <div class="w-full md:w-2/3 flex flex-col max-h-[450px] overflow-y-auto custom-scrollbar pr-3 relative">
                                        <h4 class="text-xs font-bold text-neutral-800 dark:text-neutral-200 mb-4 flex items-center gap-2 sticky top-0 bg-white dark:bg-neutral-800/90 z-10 py-1.5">
                                            <svg class="w-4 h-4 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 10h16M4 14h16M4 18h16"></path></svg>
                                            {{ t('chat.detailed_comparison', 'Detaylı Kampanya Kıyaslaması') }}
                                            <!-- Filtre etkinken kaç kampanyanın gösterildiğini belirt -->
                                            <span v-if="(msg.selectedBanks || []).length > 0" class="ml-1 px-1.5 py-0.5 rounded-full bg-blue-50 dark:bg-blue-900/30 border border-blue-100 dark:border-blue-800/50 text-[9px] font-bold text-blue-600 dark:text-blue-400 normal-case">
                                                {{ filtreliIndeksler(msg).length }} / {{ msg.chart.labels.length }}
                                            </span>
                                        </h4>

                                        <div class="space-y-4 pb-2">
                                            <div v-for="i in filtreliIndeksler(msg)" :key="'bar-'+i" class="relative group" :title="`${msg.chart.labels[i]} - ${msg.chart.sub_labels ? msg.chart.sub_labels[i] : ''} : ${msg.chart.prefix || ''}${msg.chart.values[i]}${msg.chart.suffix || ''}`">
                                                <div class="flex justify-between items-end mb-1.5">
                                                    <div class="flex flex-col min-w-0 pr-2">
                                                        <button 
                                                            @click="openModalFromText(msg.chart.full_texts[i])"
                                                            class="text-xs font-bold text-neutral-700 dark:text-neutral-300 flex items-center gap-1 hover:text-blue-600 dark:hover:text-blue-400 transition-colors text-left"
                                                            :title="t('chat.view_db_source', 'Veritabanı kaynağını görüntüle')">
                                                            <span class="truncate">{{ msg.chart.labels[i] }}</span>
                                                            <svg class="w-3 h-3 text-blue-500 opacity-0 group-hover:opacity-100 transition-opacity shrink-0 transform group-hover:translate-x-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"></path></svg>
                                                        </button>
                                                        <span class="text-[9px] text-neutral-400 font-medium truncate">{{ msg.chart.sub_labels ? msg.chart.sub_labels[i] : '' }}</span>
                                                    </div>
                                                    <span class="text-[10px] font-black text-blue-700 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/30 border border-blue-100 dark:border-blue-800/50 px-1.5 py-0.5 rounded shadow-sm shrink-0">{{ msg.chart.prefix || '' }}{{ msg.chart.values[i] }}{{ msg.chart.suffix || '' }}</span>
                                                </div>
                                                <div class="h-2 sm:h-2.5 bg-neutral-100 dark:bg-neutral-900/60 rounded-full overflow-hidden shadow-inner relative group-hover:bg-neutral-200 dark:group-hover:bg-neutral-800 transition-colors">
                                                    <div class="h-full relative rounded-full anim-bar"
                                                         :class="msg.chart.stats && msg.chart.values[i] === msg.chart.stats.min ? 'bg-gradient-to-r from-green-500 via-green-400 to-emerald-400' : 'bg-gradient-to-r from-blue-600 via-blue-500 to-cyan-400'"
                                                         :style="{ width: barGenislik(msg.chart, i), ...gecikme(i, 60) }">
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                </div>

                                <div :class="msg.chart.type === 'table' ? 'p-5 sm:p-6' : 'mt-8 pt-4 border-t border-neutral-100 dark:border-neutral-700/50'">
                                     <h4 class="text-xs font-bold text-neutral-800 dark:text-neutral-200 mb-3 flex items-center gap-2">
                                        <svg class="w-4 h-4 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 10h18M3 14h18m-9-4v8m-7 0h14a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"></path></svg>
                                        {{ msg.chart.type === 'table' ? 'Kampanya Listesi (Tablo Görünümü)' : t('chat.full_data_table', 'Eksiksiz Veri Tablosu') }}
                                    </h4>
                                    <div class="overflow-x-auto shadow-sm rounded-xl border border-neutral-200 dark:border-neutral-700 hover:shadow-md transition-shadow duration-300">
                                        <table class="w-full text-xs text-left border-collapse bg-white dark:bg-neutral-800/80">
                                            <thead>
                                                <tr class="bg-neutral-100/80 dark:bg-neutral-800/90 border-b border-neutral-200 dark:border-neutral-700">
                                                    <th class="px-3 py-2 font-bold text-neutral-800 dark:text-neutral-200 border-r border-neutral-200 dark:border-neutral-700 whitespace-nowrap min-w-[120px]">{{ t('chat.bank_institution', 'Banka / Kurum') }}</th>
                                                    <th class="px-3 py-2 font-bold text-neutral-800 dark:text-neutral-200 border-r border-neutral-200 dark:border-neutral-700 whitespace-nowrap min-w-[120px]">{{ t('chat.campaign_detail', 'Kampanya Detayı') }}</th>
                                                    <th class="px-3 py-2 font-bold text-neutral-800 dark:text-neutral-200 text-right whitespace-nowrap">{{ t('chat.value', 'Değer') }}</th>
                                                </tr>
                                            </thead>
                                            <tbody>
                                                <tr v-for="(label, i) in msg.chart.labels" :key="'table-'+i" 
                                                    @click="openModalFromText(msg.chart.full_texts[i])"
                                                    :style="gecikme(i, 35)"
                                                    class="anim-row border-b border-neutral-200 dark:border-neutral-700 hover:bg-blue-50 dark:hover:bg-neutral-800/40 last:border-0 transition-colors cursor-pointer group/tr">
                                                    <td class="px-3 py-2 text-neutral-600 dark:text-neutral-300 font-medium border-r border-neutral-200 dark:border-neutral-700 break-words min-w-[120px] group-hover/tr:text-blue-600 transition-colors">{{ label }}</td>
                                                    <td class="px-3 py-2 text-neutral-500 dark:text-neutral-400 border-r border-neutral-200 dark:border-neutral-700 break-words min-w-[120px]">{{ msg.chart.sub_labels ? msg.chart.sub_labels[i] : '-' }}</td>
                                                    <td class="px-3 py-2 font-bold text-blue-600 dark:text-blue-400 text-right whitespace-nowrap">{{ msg.chart.prefix || '' }}{{ msg.chart.values[i] }}{{ msg.chart.suffix || '' }}</td>
                                                </tr>
                                            </tbody>
                                        </table>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </Transition>
                    
                    <div v-if="msg.content || (msg.sources && msg.sources.length > 0)" class="flex gap-4 w-full max-w-4xl mx-auto mt-2">
                        <div class="flex-1 min-w-0">
                            
                            <div :id="'message-content-' + index" class="whitespace-pre-wrap leading-relaxed text-[15px] relative z-10 markdown-body" v-html="formatMessage(msg.content, !!msg.chart)"></div>

                            <div class="mt-4 pt-4 border-t border-neutral-200 dark:border-neutral-700/50 flex flex-col gap-4 relative z-10">
                              <div class="flex items-center justify-end gap-2">
                                <button v-if="msg.content.trim() !== ''" :disabled="isExportingExcel[index] || (isStreaming && index === chatHistory.length - 1)" @click="exportToExcel(index)" class="text-xs flex items-center gap-1.5 text-green-700 dark:text-green-400 hover:text-green-800 dark:hover:text-green-300 transition-all px-3 py-1.5 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800/50 rounded-lg shadow-sm hover:bg-green-100 dark:hover:bg-green-900/40 hover:-translate-y-0.5 active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none">
                                  <template v-if="!isExportingExcel[index]"><svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 10h18M3 14h18m-9-4v8m-7 0h14a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"></path></svg> {{ t('chat.download_excel', 'Excel İndir') }}</template>
                                  <template v-else><svg class="animate-spin w-4 h-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg> {{ t('chat.generating', 'Oluşturuluyor...') }}</template>
                                </button>
                                <button v-if="msg.content.trim() !== ''" :disabled="isExporting[index] || (isStreaming && index === chatHistory.length - 1)" @click="exportToPDF(index)" class="text-xs flex items-center gap-1.5 text-neutral-600 dark:text-neutral-300 hover:text-blue-600 dark:hover:text-blue-400 transition-all px-3 py-1.5 bg-white dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 rounded-lg shadow-sm hover:shadow-md hover:-translate-y-0.5 active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none">
                                  <template v-if="!isExporting[index]"><svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path></svg> {{ t('chat.view_report', 'Raporu Görüntüle') }}</template>
                                  <template v-else><svg class="animate-spin w-4 h-4 text-blue-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg> {{ t('chat.generating', 'Oluşturuluyor...') }}</template>
                                </button>
                              </div>

                              <!-- HATA DÜZELTMESİ: native <details>/<summary> tarayıcının kendi
                                   açık/kapalı geçişini kullanıyordu — bu geçiş animasyonsuzdur
                                   (CSS transition <details> için çalışmaz), yani açılıp kapanma
                                   sert ve anlıktı. Artık msg.isSourcesExpanded ile elle kontrol
                                   ediliyor ve CSS grid-rows (0fr <-> 1fr) tekniğiyle, içerik kısa da
                                   uzun da olsa yüksekliğe göre DİNAMİK, yumuşak bir açılış/kapanış
                                   animasyonu uygulanıyor. Ayrıca "MongoDB (NoSQL)" etiketi artık
                                   kaynağı teknik olarak isimlendirmek yerine sade "Kaynak" diyor. -->
                              <div v-if="msg.sources && msg.sources.length > 0" class="w-full hover:-translate-y-0.5 transition-transform duration-300">
                                  <div class="bg-neutral-50 dark:bg-neutral-800/50 rounded-xl border border-neutral-200 dark:border-neutral-700/80 overflow-hidden shadow-sm hover:shadow-md transition-shadow w-full">
                                      <button type="button" @click="toggleSources(msg)" class="w-full flex justify-between items-center font-medium cursor-pointer px-4 py-3 text-sm text-neutral-700 dark:text-neutral-200 hover:bg-neutral-100 dark:hover:bg-neutral-800 transition-colors">
                                          <div class="flex items-center gap-2.5">
                                              <svg class="w-4 h-4 text-emerald-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4"></path></svg>
                                              <span class="font-bold tracking-wide text-emerald-600 dark:text-emerald-400">Kaynak</span>
                                          </div>
                                          <span class="transition-transform duration-300 bg-white dark:bg-neutral-700 rounded-full p-1 shadow-sm border border-neutral-200 dark:border-neutral-600" :class="msg.isSourcesExpanded ? 'rotate-180' : ''"><svg class="w-4 h-4 text-neutral-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"></path></svg></span>
                                      </button>
                                      <div class="grid transition-all duration-300 ease-in-out" :class="msg.isSourcesExpanded ? 'grid-rows-[1fr]' : 'grid-rows-[0fr]'">
                                        <div class="overflow-hidden">
                                          <div class="p-4 bg-white dark:bg-neutral-900 border-t border-neutral-200 dark:border-neutral-700/80">
                                              <div class="text-xs text-neutral-500 dark:text-neutral-400 mb-2">Sistemin analiz için kullandığı kaynak logları ve detayları:</div>
                                              <div class="space-y-2 mt-3">
                                                  <div v-for="(src, sIdx) in msg.sources" :key="sIdx" class="text-xs p-3 bg-neutral-50 dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700 font-mono text-neutral-600 dark:text-neutral-300">
                                                      {{ src.icerik }}
                                                  </div>
                                              </div>
                                          </div>
                                        </div>
                                      </div>
                                  </div>
                              </div>
                            </div>
                            
                            <div v-if="msg.suggestions && msg.suggestions.length > 0" class="mt-4 flex flex-wrap gap-2 relative z-10 animate-[msgPopIn_0.4s_ease-out]">
                                <button v-for="(sug, sIdx) in msg.suggestions" :key="'sug-'+sIdx" @click="sendSuggestedPrompt(sug)" :style="gecikme(sIdx, 70)" class="anim-chip text-[11px] font-medium px-3 py-1.5 bg-blue-50/80 dark:bg-blue-900/20 text-blue-600 dark:text-blue-300 border border-blue-200/60 dark:border-blue-700/50 rounded-full hover:bg-blue-100 dark:hover:bg-blue-900/40 hover:-translate-y-0.5 transition-all shadow-sm active:scale-95 flex items-center gap-1.5 cursor-pointer">
                                    <svg class="w-3.5 h-3.5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"></path></svg>
                                    {{ sug }}
                                </button>
                            </div>
                            
                        </div>
                    </div>

                </div>
              </div>
            </TransitionGroup>
            
            <div ref="scrollAnchor" class="h-4 w-full"></div>
          </div>
        </div>

        <div class="w-full max-w-4xl mx-auto px-4 pb-4 pointer-events-auto relative z-20">
          
          <form @submit.prevent="sendMessage" class="flex flex-col w-full p-2 rounded-2xl border transition-all duration-300 relative bg-white dark:bg-neutral-800 border-neutral-200 dark:border-neutral-700 shadow-sm focus-within:shadow-lg focus-within:border-blue-400 dark:focus-within:border-blue-600 focus-within:ring-4 focus-within:ring-blue-500/10 dark:focus-within:ring-blue-500/20 focus-within:-translate-y-1">

            <!-- EKSİK ÖZELLİK: selectedFiles seçim/sürükle-bırak/yapıştırma ile
                 zaten doluyordu (script'te tüm mantık vardı) ama ŞABLONDA hiçbir
                 yerde gösterilmiyordu — kullanıcı gönder'e basana kadar bir dosyanın
                 eklendiğine dair hiçbir görsel geri bildirim yoktu. Bu tam olarak
                 "dosya yükleme fonksiyonu" kullanıcıya kayboldu diye görünen kısımdı.
                 ChatPrompt.vue'deki aynı önizleme deseni buraya da eklendi. -->
            <Transition
              enter-active-class="transition-all duration-300 ease-out"
              enter-from-class="opacity-0 translate-y-2 scale-95"
              enter-to-class="opacity-100 translate-y-0 scale-100"
              leave-active-class="transition-all duration-200 ease-in"
              leave-from-class="opacity-100 translate-y-0 scale-100"
              leave-to-class="opacity-0 translate-y-2 scale-95"
            >
              <div v-if="selectedFiles.length > 0" class="flex items-center gap-2 flex-wrap px-1.5 pb-2">
                <div v-for="(file, index) in selectedFiles" :key="index" class="flex items-center gap-1.5 bg-neutral-50 dark:bg-neutral-700/60 px-3 py-1.5 rounded-xl border border-neutral-200 dark:border-neutral-600 shadow-sm">
                  <svg class="w-3.5 h-3.5 text-blue-500 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path></svg>
                  <span class="text-[12px] font-medium text-neutral-600 dark:text-neutral-300 truncate max-w-[140px]">{{ file.name }}</span>
                  <button @click.prevent="removeFile(index)" type="button" :disabled="isStreaming" class="ml-0.5 p-0.5 text-neutral-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/30 rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed">
                    <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg>
                  </button>
                </div>
              </div>
            </Transition>

            <div class="flex gap-2 items-center relative z-20">
              <input type="file" multiple ref="fileInput" class="hidden" @change="handleFileSelect" accept=".pdf, image/*, .xls, .xlsx, .doc, .docx, .ppt, .pptx" />
              <button type="button" @click="triggerFileInput" :disabled="isStreaming" class="p-3 text-neutral-400 hover:text-blue-500 transition-all duration-300 rounded-xl hover:bg-neutral-100 dark:hover:bg-neutral-700 active:scale-90 disabled:opacity-50 disabled:cursor-not-allowed hover:-translate-y-0.5 hover:shadow-sm">
                <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13"></path></svg>
              </button>
              <input v-model="userMessage" type="text" @paste="handlePaste" :placeholder="t('chat.placeholder', 'Bir şeyler sorun, yapıştırın (Ctrl+V) veya dosya bırakın...')" class="flex-1 bg-transparent px-2 py-3 text-neutral-900 dark:text-white outline-none placeholder:text-neutral-400 transition-all text-sm sm:text-base disabled:opacity-50" :disabled="isStreaming" />
              <button type="submit" :disabled="isStreaming || (!userMessage.trim() && selectedFiles.length === 0)" class="px-5 py-3 bg-gradient-to-r from-blue-600 to-blue-500 text-white rounded-xl hover:from-blue-700 hover:to-blue-600 transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center group active:scale-90 hover:shadow-lg hover:shadow-blue-500/30">
                <svg class="w-5 h-5 transform group-hover:translate-x-1 group-hover:-translate-y-1 transition-transform duration-300" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"></path></svg>
              </button>
            </div>
          </form>
        </div>
      </div>

      <Transition enter-active-class="transform transition-all duration-500 ease-[cubic-bezier(0.2,0.8,0.2,1)]" enter-from-class="translate-x-[120%] opacity-0 scale-95" enter-to-class="translate-x-0 opacity-100 scale-100" leave-active-class="transform transition-all duration-300 ease-in" leave-from-class="translate-x-0 opacity-100 scale-100" leave-to-class="translate-x-[120%] opacity-0 scale-95">
        <div v-if="showSourceModal" class="absolute right-4 top-4 bottom-4 w-[340px] lg:w-[480px] bg-white dark:bg-[#121212] rounded-[24px] shadow-[0_8px_30px_rgb(0,0,0,0.2)] dark:shadow-[0_8px_30px_rgb(0,0,0,0.6)] border border-neutral-200 dark:border-neutral-700 flex flex-col z-50 overflow-hidden">
          <div class="flex justify-between items-center p-4 border-b border-neutral-200 dark:border-neutral-700 bg-neutral-50 dark:bg-neutral-800">
            <h3 class="text-[14px] font-bold flex items-center gap-2 text-neutral-800 dark:text-white">
              <template v-if="activeModalType === 'file'">
                <svg class="w-4 h-4 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path></svg> {{ activeFile?.isUserFile ? t('chat.file_preview', 'Dosya Önizleme') : t('chat.report_preview', 'Rapor Önizleme') }}
              </template>
              <template v-else>
                <!-- Yukarıdaki kaynak bölümünün etiketiyle tutarlı olsun diye
                     ("Kaynak" düğmesine basınca burası hâlâ "MongoDB (NoSQL)" derse
                     kafa karıştırır) burası da aynı şekilde sadeleştirildi. -->
                <svg class="w-4 h-4 text-emerald-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4"></path></svg> Kaynak Kaydı
              </template>
            </h3>
            <div class="flex items-center gap-2">
              <button @click="showSourceModal = false" class="p-1 text-neutral-500 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/30 rounded transition-colors active:scale-90 transform duration-200"><svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg></button>
            </div>
          </div>
          
          <div class="flex-1 overflow-hidden bg-white dark:bg-neutral-900 flex flex-col relative p-4 lg:p-6 items-start justify-start">
                <template v-if="activeModalType === 'file' && activeFile">
                    <iframe id="report-iframe" :srcdoc="activeFile.htmlContent" class="w-full h-full border border-neutral-200 dark:border-neutral-700 bg-white rounded-xl shadow-inner animate-[msgPopIn_0.5s_ease-out]"></iframe>
                </template>
                <template v-else>
                    <div class="w-full h-full overflow-y-auto p-2 custom-scrollbar text-left">
                        <div class="whitespace-pre-wrap text-[13px] font-medium leading-relaxed text-neutral-800 dark:text-neutral-200 break-words" v-html="formatMessage(activeSource?.icerik || '{}')"></div>
                    </div>
                </template>
          </div>
        </div>
      </Transition>
    </div>
  </div>
</template>

<style scoped>
@keyframes msgPopIn { 0% { opacity: 0; transform: translateY(20px) scale(0.95); } 60% { opacity: 1; transform: translateY(-3px) scale(1.01); } 100% { opacity: 1; transform: translateY(0) scale(1); } }
.msg-enter-active { animation: msgPopIn 0.5s cubic-bezier(0.34, 1.56, 0.64, 1) forwards; }
.msg-leave-active { transition: all 0.3s ease-in; }
.msg-leave-to { opacity: 0; transform: translateY(-10px) scale(0.95); }
.custom-scrollbar::-webkit-scrollbar { width: 6px; }
.custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
.custom-scrollbar::-webkit-scrollbar-thumb { background-color: #cbd5e1; border-radius: 20px; }
.dark .custom-scrollbar::-webkit-scrollbar-thumb { background-color: #404040; }
.markdown-body p, .markdown-body li { word-break: break-word; }

/* HATA DÜZELTMESİ: Durum metni (currentStatus.text) için <Transition name="fade-text">
   kullanılıyordu ama karşılık gelen .fade-text-* sınıfları hiçbir yerde tanımlı değildi.
   Vue, tanımsız transition sınıflarında sessizce hiçbir şey yapmaz — yani "HyDE: ...",
   "Step-Back: ...", "MongoDB Ajanı Sorgulanıyor..." gibi durum metinleri birbirinin üstüne
   anında (crossfade olmadan) "atlıyordu". Eksik sınıflar eklendi. */
.fade-text-enter-active,
.fade-text-leave-active {
  transition: opacity 0.25s ease, transform 0.25s ease;
}
.fade-text-enter-from {
  opacity: 0;
  transform: translateY(4px);
}
.fade-text-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}
.fade-text-leave-active {
  position: absolute;
}

/* HATA DÜZELTMESİ: Şablonda kullanılan animate-[shimmer_1.5s_infinite],
   animate-gradient-x ve ease-out-back sınıfları Tailwind'in varsayılan
   yardımcı sınıfları DEĞİL — projenin tailwind.config'inde tanımlı olmalıydı.
   Burada tanımlı değilse (veya config'te unutulduysa) animasyonlar sessizce
   çalışmıyordu (analiz iskeleti üzerindeki ışıltı taraması ve "işlem devam
   ediyor" kartının nabız gibi atan gradienti gibi). Keyframes/utility'ler
   component-seviyesinde de tanımlanarak garanti altına alındı. */
@keyframes shimmer {
  100% { transform: translateX(200%); }
}
@keyframes gradient-x {
  0%, 100% { background-position: 0% 50%; }
  50% { background-position: 100% 50%; }
}
.animate-gradient-x {
  background-size: 200% 200%;
  animation: gradient-x 3s ease infinite;
}
.ease-out-back {
  transition-timing-function: cubic-bezier(0.34, 1.56, 0.64, 1);
}

/* =========================================================================
   DİNAMİK GİRİŞ ANİMASYONLARI
   Hepsi `both` fill-mode ile: animasyon başlamadan önce eleman başlangıç
   durumunda bekler, bittiğinde son durumda kalır — böylece stagger
   (kademeli gecikme) sırasında titreme/atlama olmaz.
   ========================================================================= */

/* Bar grafik: şablonda `transition-all duration-1000` yazıyordu ama CSS
   geçişleri ÖNCEKİ bir değer olmadan çalışmaz — eleman doğrudan son
   genişliğinde doğduğu için o "1 saniyelik animasyon" hiç görünmüyordu.
   Genişlik inline kalıp scaleX animasyonu uygulanarak gerçek bir dolum
   animasyonu elde ediliyor (transform GPU'da çalışır, layout tetiklemez). */
@keyframes barGrow { from { transform: scaleX(0); } to { transform: scaleX(1); } }
.anim-bar {
  transform-origin: left center;
  animation: barGrow 0.9s cubic-bezier(0.22, 1, 0.36, 1) both;
}

@keyframes rowIn { from { opacity: 0; transform: translateY(6px); } to { opacity: 1; transform: none; } }
.anim-row { animation: rowIn 0.45s ease-out both; }

@keyframes chipIn { from { opacity: 0; transform: translateY(8px) scale(0.94); } to { opacity: 1; transform: none; } }
.anim-chip { animation: chipIn 0.4s cubic-bezier(0.34, 1.56, 0.64, 1) both; }

@keyframes tileIn { from { opacity: 0; transform: translateY(-8px) scale(0.9); } to { opacity: 1; transform: none; } }
.anim-tile { animation: tileIn 0.5s cubic-bezier(0.34, 1.56, 0.64, 1) both; }

@keyframes donutIn { from { opacity: 0; transform: scale(0.85); } to { opacity: 1; transform: scale(1); } }
.anim-donut { animation: donutIn 0.6s cubic-bezier(0.22, 1, 0.36, 1) both; }

@keyframes cardIn { from { opacity: 0; transform: translateY(14px); } to { opacity: 1; transform: none; } }
.anim-card { animation: cardIn 0.55s cubic-bezier(0.22, 1, 0.36, 1) both; }

/* ERİŞİLEBİLİRLİK: İşletim sisteminde "hareketi azalt" seçili kullanıcılar
   için tüm giriş animasyonları kapatılır. Vestibüler rahatsızlığı olan
   kullanıcılarda kademeli/zıplayan animasyonlar baş dönmesi yapabiliyor;
   içerik yine tam görünür kalır, sadece hareket olmaz. */
@media (prefers-reduced-motion: reduce) {
  .anim-bar, .anim-row, .anim-chip, .anim-tile, .anim-donut, .anim-card,
  .msg-enter-active, .msg-leave-active,
  .fade-text-enter-active, .fade-text-leave-active {
    animation: none !important;
    transition: none !important;
  }
  .animate-gradient-x { animation: none !important; }
}
</style>