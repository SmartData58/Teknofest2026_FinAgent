<script setup>
import { ref, computed, onMounted, onBeforeUnmount, watch, nextTick } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { useChatStore } from '~/stores/chatStore'
import { Chart as ChartJS, RadialLinearScale, PointElement, LineElement, Filler, Tooltip, Legend, BarElement, CategoryScale, LinearScale } from 'chart.js'
import { Radar, Bar, Line } from 'vue-chartjs'
import { gsap } from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'
import Lenis from 'lenis'

gsap.registerPlugin(ScrollTrigger)

let lenis = null
let lenisRafId = null


ChartJS.register(RadialLinearScale, PointElement, LineElement, Filler, Tooltip, Legend, BarElement, CategoryScale, LinearScale)

if (process.client) {
  import('chartjs-plugin-zoom').then((module) => {
    ChartJS.register(module.default)
  })
}


const { t, locale } = useI18n()
const router = useRouter()
const chatStore = useChatStore()

useHead({
  title: computed(() => t('page_titles.dashboard', 'Pazar Analizi')),
  link: [
    {
      rel: 'stylesheet',
      href: 'https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap'
    }
  ]
})

definePageMeta({
  layout: 'default'
})

const viewMode = useState('globalViewMode', () => 'musteri')
const isBankaci = computed(() => viewMode.value === 'bankaci')

const banks = ref([])
const campaigns = ref([])
const loading = ref(true)


const hiddenLine = ref([])
const customLegendClickLine = (e, legendItem) => {
  const label = legendItem.text
  if (hiddenLine.value.includes(label)) hiddenLine.value = hiddenLine.value.filter(x => x !== label)
  else hiddenLine.value = [...hiddenLine.value, label]
}

const hiddenRadar = ref([])
const customLegendClickRadar = (e, legendItem) => {
  const label = legendItem.text
  if (hiddenRadar.value.includes(label)) hiddenRadar.value = hiddenRadar.value.filter(x => x !== label)
  else hiddenRadar.value = [...hiddenRadar.value, label]
}

const hiddenBar = ref([])
const customLegendClickBar = (e, legendItem) => {
  const label = legendItem.text
  if (hiddenBar.value.includes(label)) hiddenBar.value = hiddenBar.value.filter(x => x !== label)
  else hiddenBar.value = [...hiddenBar.value, label]
}
const showSectorAverage = ref(true)
  const expandedCharts = ref({ line: false, radar: false, duration: false })
  const chartInteracts = ref({ line: false, radar: false, duration: false })
const selectedTier = ref(null)


const topCampaigns = ref({})
const lineChartRef = ref(null)
const radarChartRef = ref(null)
const barChartRef = ref(null)

const fetchTopAdvantageous = async () => {
  try {
    const res = await fetch('http://localhost:8003/campaigns/top-advantageous')
    if (res.ok) {
      topCampaigns.value = await res.json()
    }
  } catch (err) {
    console.error("En avantajlı kampanyalar çekilemedi", err)
  }
}


const selectedModalCampaign = ref(null)


const hasValue = (val) => {
  if (val === null || val === undefined) return false
  if (Array.isArray(val)) return val.length > 0 && val.some(v => hasValue(v))
  const s = String(val).trim().toLowerCase()
  return s !== '' && s !== '-' && s !== 'none' && s !== 'null' && s !== 'undefined'
}

const formatTarih = (val) => {
  if (!val) return ''
  try {
    const s = String(val).split('T')[0]
    const parts = s.split('-')
    if (parts.length === 3) {
      return `${parts[2]}.${parts[1]}.${parts[0]}`
    }
  } catch (e) {}
  return String(val).split('T')[0]
}

const openCampaignModal = async (id) => {
  if (!id) return
  
  // 1. Önce bellekteki listeden hızlıca paneli aç
  let camp = campaigns.value.find(c => {
    const cid = c._id || c.id
    return cid === id || String(cid) === String(id)
  })
  
  if (camp) {
    selectedModalCampaign.value = camp
  }
  
  // 2. Metin ve eksik alanların tam gelmesi için her zaman detay endpoint'ini çağır
  try {
    const res = await fetch(`http://localhost:8003/campaigns/${id}`)
    if (res.ok) {
      const data = await res.json()
      selectedModalCampaign.value = data
      if (camp) {
        Object.assign(camp, data)
      }
    }
  } catch (err) {
    console.error('Kampanya detayı çekilemedi:', err)
  }
}

// ===================== EXCEL (XLSX), VEKTÖREL PDF VE ULTRA-HD PNG DIŞA AKTARMA =====================
const betigiYukle = (src, globalName) => {
  return new Promise((resolve, reject) => {
    if (window[globalName]) return resolve()
    const s = document.createElement('script')
    s.src = src
    s.onload = resolve
    s.onerror = reject
    document.head.appendChild(s)
  })
}

let _renkOlcer = null
const oklchDonustur = (renk) => {
  if (!renk || typeof renk !== 'string') return renk
  if (!renk.includes('oklch') && !renk.includes('oklab')) return renk
  try {
    if (!_renkOlcer) {
      _renkOlcer = document.createElement('div')
      _renkOlcer.style.display = 'none'
      document.body.appendChild(_renkOlcer)
    }
    _renkOlcer.style.color = 'inherit'
    _renkOlcer.style.color = renk
    const computed = window.getComputedStyle(_renkOlcer).color
    return computed || '#2563eb'
  } catch (e) {
    return '#2563eb'
  }
}

const klonRenkleriniDuzelt = (orijinal, klon) => {
  if (!orijinal || !klon || orijinal.nodeType !== 1) return
  try {
    const stil = window.getComputedStyle(orijinal)
    if (stil.color && (stil.color.includes('oklch') || stil.color.includes('oklab'))) klon.style.color = oklchDonustur(stil.color)
    if (stil.backgroundColor && (stil.backgroundColor.includes('oklch') || stil.backgroundColor.includes('oklab'))) klon.style.backgroundColor = oklchDonustur(stil.backgroundColor)
    if (stil.borderColor && (stil.borderColor.includes('oklch') || stil.borderColor.includes('oklab'))) klon.style.borderColor = oklchDonustur(stil.borderColor)
    
    const oCocuklar = orijinal.children || []
    const kCocuklar = klon.children || []
    for (let i = 0; i < oCocuklar.length && i < kCocuklar.length; i++) {
      klonRenkleriniDuzelt(oCocuklar[i], kCocuklar[i])
    }
  } catch (e) { console.warn('Klon renk duzeltme atlandi:', e) }
}

const klonAnimasyonlariniDurdur = (klonDoc, klonKok) => {
  if (!klonDoc) return
  const stil = klonDoc.createElement('style')
  stil.textContent = '*, *::before, *::after { animation: none !important; animation-delay: 0s !important; animation-duration: 0s !important; transition: none !important; opacity: 1 !important; transform: none !important; filter: none !important; } .anim-bar { transform: scaleX(1) !important; }'
  ;(klonDoc.head || klonDoc.body || klonKok)?.appendChild(stil)
}

const tuvaliDuzlestir = (tuval, arkaPlan) => {
  const nihai = document.createElement('canvas')
  nihai.width = tuval.width
  nihai.height = tuval.height
  const ctx = nihai.getContext('2d')
  ctx.fillStyle = arkaPlan
  ctx.fillRect(0, 0, nihai.width, nihai.height)
  ctx.drawImage(tuval, 0, 0)
  return nihai
}

// --------------------------- 1. EXCEL (.XLSX) DIŞA AKTARMA (TEK SAYFADA TÜM TABLOLAR + AYRI SAYFALAR) ---------------------------
const exportToExcel = async (chartRefName) => {
  try {
    await betigiYukle('https://cdn.jsdelivr.net/npm/xlsx-js-style@1.2.0/dist/xlsx.bundle.js', 'XLSX')
    const XLSX = window.XLSX
    const wb = XLSX.utils.book_new()
    const bankName = activeCompareBanks.value.length === 1 ? activeCompareBanks.value[0].kisa_ad : 'Sektor_Karsilastirma'
    const cleanBankName = bankName.replace(/[^a-zA-Z0-9_À-ſ]/g, '_')
    const today = new Date().toLocaleDateString('tr-TR', { year: 'numeric', month: 'long', day: 'numeric' })
    const activeCamps = activeCompareBanks.value.flatMap(b => getBankCampaigns(b))
    const firstBank = activeCompareBanks.value[0]
    const baskin = firstBank ? getBaskinKategori(firstBank) : null

    if (chartRefName === 'all-comparison') {
      // === MASTER SAYFA: TÜM ANALİZ RAPORU (BÜTÜN TABLOLAR TEK BİR SAYFADA SIRAYLA) ===
      const masterRows = [
        ['FINAGENT - BANKACILIK PAZAR VE REKABET ANALİZ RAPORU'],
        [`Kurum: ${bankName}`, `Tarih: ${today}`, `Toplam Aktif Kampanya: ${activeCamps.length}`],
        [],
        ['=== 1. TEMEL PERFORMANS VE STATÜ GÖSTERGELERİ (KPI) ==='],
        ['Kurum', 'Statü (Tier)', 'Mülkiyet Türü', 'Aktif Büyüklük (Milyar TL)', 'Aktif Kampanya Sayısı', 'Baskın Kategori'],
        [
          firstBank?.kisa_ad || bankName,
          firstBank?.tier || 'Tier 1',
          firstBank?.mulkiyet_turu || 'Katılım Bankası',
          firstBank?.aktif_buyukluk_milyar_tl ? `${firstBank.aktif_buyukluk_milyar_tl} Milyar ₺` : '-',
          activeCamps.length,
          baskin ? `${baskin.ad} (%${baskin.yuzde})` : 'Dengeli'
        ],
        [],
        ['=== 2. SON 6 AY KAMPANYA BAŞLANGIÇ TRENDİ & İVME ==='],
        ['Ay', ...activeCompareBanks.value.map(b => b.kisa_ad), 'Sektör Ortalaması']
      ]

      last6Months.value.forEach((m, idx) => {
        const row = [m]
        activeCompareBanks.value.forEach(b => {
          const trendData = getBankTrend(getBankCampaigns(b))
          row.push(trendData[idx] || 0)
        })
        row.push(sektorAverages.value[idx] || 0)
        masterRows.push(row)
      })

      masterRows.push([])
      masterRows.push(['=== 3. KATEGORİ BAZLI KAMPANYA DAĞILIMI ==='])
      masterRows.push(['Kategori', ...activeCompareBanks.value.map(b => b.kisa_ad + ' (Adet)'), 'Sektör Ortalaması (Adet)'])

      categories.forEach((cat, idx) => {
        const row = [cat]
        activeCompareBanks.value.forEach(b => {
          const catCounts = getCategoryCounts(getBankCampaigns(b))
          row.push(catCounts[idx] || 0)
        })
        row.push(sektorAverages.value[idx] || 0)
        masterRows.push(row)
      })

      masterRows.push([])
      masterRows.push(['=== 4. KATEGORİ BAZLI ORTALAMA KAMPANYA YAYIN SÜRELERİ ==='])
      masterRows.push(['Kategori', ...activeCompareBanks.value.map(b => b.kisa_ad + ' (Ay)'), 'Sektör Ortalaması (Ay)'])

      categories.forEach((cat, idx) => {
        const row = [cat]
        activeCompareBanks.value.forEach(b => {
          const catDurs = getCategoryDurations(getBankCampaigns(b))
          row.push(catDurs[idx] || 0)
        })
        row.push(sektorDurations.value[idx] || 0)
        masterRows.push(row)
      })

      masterRows.push([])
      masterRows.push(['=== 5. AKTİF KAMPANYALAR LİSTESİ VE DETAYLARI ==='])
      masterRows.push(['Banka', 'Kampanya Adı', 'Tür', 'Kâr Payı (%)', 'Vade (Ay)', 'Taksit', 'Ödül (TL)', 'Bitiş Tarihi', 'Hedef Kitle', 'Kaynak URL'])

      activeCamps.forEach(c => {
        const gb = c.genel_bilgi || {}
        const fd = c.finansman_detay || {}
        const pd = c.promosyon_detay || {}
        masterRows.push([
          gb.banka_id || c.banka || '-',
          gb.kampanya_adi || c.baslik || '-',
          gb.kampanya_turu || c.tur || '-',
          fd.kar_payi_orani ?? '-',
          fd.vade_ay ?? '-',
          fd.taksit ?? '-',
          pd.odul_tutari ?? '-',
          formatTarih(gb.bitis_tarihi) || '-',
          Array.isArray(gb.hedef_kitle) ? gb.hedef_kitle.join(', ') : (gb.hedef_kitle || '-'),
          gb.kaynak_url || c.url || '-'
        ])
      })

      const wsMaster = XLSX.utils.aoa_to_sheet(masterRows)
      wsMaster['!cols'] = [{ wch: 22 }, { wch: 45 }, { wch: 22 }, { wch: 18 }, { wch: 14 }, { wch: 12 }, { wch: 14 }, { wch: 16 }, { wch: 24 }, { wch: 40 }]
      XLSX.utils.book_append_sheet(wb, wsMaster, 'Tum_Analiz_Raporu')

      // --- AYRI SEKME 1: Başlangıç Trendi ---
      const wsTrend = XLSX.utils.aoa_to_sheet([
        ['Ay', ...activeCompareBanks.value.map(b => b.kisa_ad), 'Sektör Ortalaması'],
        ...last6Months.value.map((m, idx) => [
          m,
          ...activeCompareBanks.value.map(b => getBankTrend(getBankCampaigns(b))[idx] || 0),
          sektorAverages.value[idx] || 0
        ])
      ])
      wsTrend['!cols'] = [{ wch: 15 }, ...activeCompareBanks.value.map(() => ({ wch: 22 })), { wch: 22 }]
      XLSX.utils.book_append_sheet(wb, wsTrend, '1_Baslangic_Trendi')

      // --- AYRI SEKME 2: Kampanya Dağılımı ---
      const wsDist = XLSX.utils.aoa_to_sheet([
        ['Kategori', ...activeCompareBanks.value.map(b => b.kisa_ad), 'Sektör Ortalaması'],
        ...categories.map((cat, idx) => [
          cat,
          ...activeCompareBanks.value.map(b => getCategoryCounts(getBankCampaigns(b))[idx] || 0),
          sektorAverages.value[idx] || 0
        ])
      ])
      wsDist['!cols'] = [{ wch: 18 }, ...activeCompareBanks.value.map(() => ({ wch: 22 })), { wch: 22 }]
      XLSX.utils.book_append_sheet(wb, wsDist, '2_Kampanya_Dagilimi')

      // --- AYRI SEKME 3: Kampanya Süreleri ---
      const wsDur = XLSX.utils.aoa_to_sheet([
        ['Kategori', ...activeCompareBanks.value.map(b => b.kisa_ad + ' (Ay)'), 'Sektör Ortalaması (Ay)'],
        ...categories.map((cat, idx) => [
          cat,
          ...activeCompareBanks.value.map(b => getCategoryDurations(getBankCampaigns(b))[idx] || 0),
          sektorDurations.value[idx] || 0
        ])
      ])
      wsDur['!cols'] = [{ wch: 18 }, ...activeCompareBanks.value.map(() => ({ wch: 24 })), { wch: 24 }]
      XLSX.utils.book_append_sheet(wb, wsDur, '3_Ortalama_Sureler')

      // --- AYRI SEKME 4: Kampanyalar Listesi ---
      const wsCamps = XLSX.utils.aoa_to_sheet([
        ['Banka', 'Kampanya Adı', 'Tür', 'Kâr Payı (%)', 'Vade (Ay)', 'Taksit', 'Ödül (TL)', 'Bitiş Tarihi', 'Hedef Kitle', 'Kaynak URL'],
        ...activeCamps.map(c => {
          const gb = c.genel_bilgi || {}
          const fd = c.finansman_detay || {}
          const pd = c.promosyon_detay || {}
          return [
            gb.banka_id || c.banka || '-',
            gb.kampanya_adi || c.baslik || '-',
            gb.kampanya_turu || c.tur || '-',
            fd.kar_payi_orani ?? '-',
            fd.vade_ay ?? '-',
            fd.taksit ?? '-',
            pd.odul_tutari ?? '-',
            formatTarih(gb.bitis_tarihi) || '-',
            Array.isArray(gb.hedef_kitle) ? gb.hedef_kitle.join(', ') : (gb.hedef_kitle || '-'),
            gb.kaynak_url || c.url || '-'
          ]
        })
      ])
      wsCamps['!cols'] = [{ wch: 16 }, { wch: 45 }, { wch: 20 }, { wch: 14 }, { wch: 12 }, { wch: 10 }, { wch: 14 }, { wch: 15 }, { wch: 22 }, { wch: 40 }]
      XLSX.utils.book_append_sheet(wb, wsCamps, '4_Kampanyalar_Listesi')

      XLSX.writeFile(wb, `FinAgent_${cleanBankName}_Tum_Analiz_Raporu.xlsx`)
    } else if (chartRefName === 'lineChartRef') {
      const rows = [['Ay', ...activeCompareBanks.value.map(b => b.kisa_ad), 'Sektör Ortalaması']]
      last6Months.value.forEach((m, idx) => {
        const row = [m]
        activeCompareBanks.value.forEach(b => {
          const trendData = getBankTrend(getBankCampaigns(b))
          row.push(trendData[idx] || 0)
        })
        row.push(sektorAverages.value[idx] || 0)
        rows.push(row)
      })
      const ws = XLSX.utils.aoa_to_sheet(rows)
      ws['!cols'] = [{ wch: 15 }, ...activeCompareBanks.value.map(() => ({ wch: 22 })), { wch: 22 }]
      XLSX.utils.book_append_sheet(wb, ws, 'Baslangic_Trendi')
      XLSX.writeFile(wb, `FinAgent_${cleanBankName}_Baslangic_Trendi.xlsx`)
    } else if (chartRefName === 'radarChartRef') {
      const rows = [['Kategori', ...activeCompareBanks.value.map(b => b.kisa_ad), 'Sektör Ortalaması']]
      categories.forEach((cat, idx) => {
        const row = [cat]
        activeCompareBanks.value.forEach(b => {
          const catCounts = getCategoryCounts(getBankCampaigns(b))
          row.push(catCounts[idx] || 0)
        })
        row.push(sektorAverages.value[idx] || 0)
        rows.push(row)
      })
      const ws = XLSX.utils.aoa_to_sheet(rows)
      ws['!cols'] = [{ wch: 18 }, ...activeCompareBanks.value.map(() => ({ wch: 22 })), { wch: 22 }]
      XLSX.utils.book_append_sheet(wb, ws, 'Kampanya_Dagilimi')
      XLSX.writeFile(wb, `FinAgent_${cleanBankName}_Kampanya_Dagilimi.xlsx`)
    } else if (chartRefName === 'barChartRef') {
      const rows = [['Kategori', ...activeCompareBanks.value.map(b => b.kisa_ad + ' (Ay)'), 'Sektör Ortalaması (Ay)']]
      categories.forEach((cat, idx) => {
        const row = [cat]
        activeCompareBanks.value.forEach(b => {
          const catDurs = getCategoryDurations(getBankCampaigns(b))
          row.push(catDurs[idx] || 0)
        })
        row.push(sektorDurations.value[idx] || 0)
        rows.push(row)
      })
      const ws = XLSX.utils.aoa_to_sheet(rows)
      ws['!cols'] = [{ wch: 18 }, ...activeCompareBanks.value.map(() => ({ wch: 24 })), { wch: 24 }]
      XLSX.utils.book_append_sheet(wb, ws, 'Ortalama_Sureler')
      XLSX.writeFile(wb, `FinAgent_${cleanBankName}_Ortalama_Sureler.xlsx`)
    }
  } catch (err) {
    console.error('Excel dışa aktarma hatası:', err)
  }
}

// --------------------------- 2. BEYAZ ŞABLONLU PDF DIŞA AKTARMA (chat.vue İLE BİREBİR AYNI ŞABLON) ---------------------------
const escapeHtml = (str) => {
  if (str === null || str === undefined) return ''
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;')
}

const exportToPDF = async (chartRefName) => {
  // 1. Kullanıcının mevcut görünüm durumunu yedekle
  const prevExpanded = { ...expandedCharts.value }

  // 2. PDF İÇİN TÜM GRAFİKLERİN GENİŞLETİLMİŞ GÖRÜNÜMÜNÜ AKTİF ET
  expandedCharts.value = { line: true, radar: true, duration: true }

  // Vue DOM ve Chart.js'in genişletilmiş modda render olması için bekle
  await nextTick()
  await new Promise(r => setTimeout(r, 450))

  try {
    await betigiYukle('https://cdnjs.cloudflare.com/ajax/libs/html2pdf.js/0.10.1/html2pdf.bundle.min.js', 'html2pdf')

    const bankName = activeCompareBanks.value.length === 1 ? activeCompareBanks.value[0].kisa_ad : 'Sektör Karşılaştırma Analizi'
    const today = new Date().toLocaleDateString('tr-TR', { year: 'numeric', month: 'long', day: 'numeric' })
    const activeCamps = activeCompareBanks.value.flatMap(b => getBankCampaigns(b))
    const firstBank = activeCompareBanks.value[0]
    const baskin = firstBank ? getBaskinKategori(firstBank) : null

    // Genişletilmiş grafiklerin canvas görüntülerinin yakalanması
    let lineImg = ''
    let radarImg = ''
    let barImg = ''
    try {
      const lineCanvas = document.querySelector('#chart-box-lineChartRef canvas')
      if (lineCanvas && lineCanvas.width > 0) lineImg = lineCanvas.toDataURL('image/png', 1.0)
    } catch (e) { console.warn('Line canvas alınamadı:', e) }
    try {
      const radarCanvas = document.querySelector('#chart-box-radarChartRef canvas')
      if (radarCanvas && radarCanvas.width > 0) radarImg = radarCanvas.toDataURL('image/png', 1.0)
    } catch (e) { console.warn('Radar canvas alınamadı:', e) }
    try {
      const barCanvas = document.querySelector('#chart-box-barChartRef canvas')
      if (barCanvas && barCanvas.width > 0) barImg = barCanvas.toDataURL('image/png', 1.0)
    } catch (e) { console.warn('Bar canvas alınamadı:', e) }

    const kutu = (etiket, deger) => `
      <div style="flex: 1; padding: 10px 14px; border: 1px solid #e5e7eb; border-radius: 8px; text-align: center; background-color: #f9fafb;">
          <strong style="font-size: 10px; color: #6b7280; display: block; margin-bottom: 4px; text-transform: uppercase;">${escapeHtml(etiket)}</strong>
          <span style="font-size: 16px; font-weight: bold; color: #1e40af;">${escapeHtml(deger)}</span>
      </div>`

    let html = `
      <div style="font-family: 'Segoe UI', Arial, sans-serif; color: #171717; background-color: #ffffff; padding: 25px; max-width: 800px; margin: 0 auto;">
          
          <!-- ÜST BAŞLIK (chat.vue ŞABLONU) -->
          <div style="border-bottom: 2px solid #2563eb; padding-bottom: 12px; margin-bottom: 20px;">
              <h1 style="color: #2563eb; margin: 0; font-size: 24px; font-weight: bold;">FinAgent Pazar Analizi Raporu (Genişletilmiş Detay)</h1>
              <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 6px;">
                  <p style="color: #1e40af; font-size: 13px; font-weight: bold; margin: 0;">Kurum: ${escapeHtml(bankName)}</p>
                  <p style="color: #6b7280; font-size: 12px; margin: 0;">Oluşturulma Tarihi: ${escapeHtml(today)}</p>
              </div>
          </div>

          <!-- İSTATİSTİK KUTULARI (chat.vue ŞABLONU) -->
          <div style="display: flex; gap: 12px; margin-bottom: 24px;">
              ${kutu('AKTİF KAMPANYA', `${activeCamps.length} Adet`)}
              ${kutu('BASKIN KATEGORİ', baskin ? `${baskin.ad} (%${baskin.yuzde})` : 'Dengeli')}
              ${kutu('KURUM STATÜSÜ', firstBank?.tier || 'Tier 1')}
              ${kutu('AKTİF BÜYÜKLÜK', firstBank?.aktif_buyukluk_milyar_tl ? `${firstBank.aktif_buyukluk_milyar_tl} Milyar ₺` : '-')}
          </div>`

    if (chartRefName === 'all-comparison' || chartRefName === 'lineChartRef') {
      // 1. LANSMAN TRENDİ
      html += `
          <div style="margin-bottom: 30px; page-break-inside: avoid;">
              <h2 style="font-size: 16px; color: #111827; margin: 0 0 4px 0; font-weight: bold;">1. Lansman Trendi</h2>
              <p style="font-size: 12px; color: #4b5563; margin: 0 0 12px 0;">Son 6 ayda başlayan yeni kampanya ivmesi ve sektör ortalaması kıyası</p>
              ${lineImg ? `<div style="text-align: center; margin-bottom: 14px; background: #ffffff; border: 1px solid #e5e7eb; border-radius: 8px; padding: 12px;"><img src="${lineImg}" style="max-width: 100%; height: auto; max-height: 280px; object-fit: contain; display: block; margin: 0 auto;" /></div>` : ''}
              
              <table style="width: 100%; border-collapse: collapse; font-size: 11px; margin-top: 8px;">
                  <thead>
                      <tr style="background-color: #f3f4f6;">
                          <th style="padding: 7px 10px; border: 1px solid #d1d5db; text-align: left; color: #1f2937;">Ay</th>
                          ${activeCompareBanks.value.map(b => `<th style="padding: 7px 10px; border: 1px solid #d1d5db; text-align: center; color: #1f2937;">${escapeHtml(b.kisa_ad)}</th>`).join('')}
                          <th style="padding: 7px 10px; border: 1px solid #d1d5db; text-align: center; color: #1f2937;">Sektör Ortalaması</th>
                      </tr>
                  </thead>
                  <tbody>
                      ${last6Months.value.map((m, idx) => `
                          <tr>
                              <td style="padding: 6px 10px; border: 1px solid #d1d5db; font-weight: bold;">${escapeHtml(m)}</td>
                              ${activeCompareBanks.value.map(b => `<td style="padding: 6px 10px; border: 1px solid #d1d5db; text-align: center;">${getBankTrend(getBankCampaigns(b))[idx] || 0}</td>`).join('')}
                              <td style="padding: 6px 10px; border: 1px solid #d1d5db; text-align: center; color: #059669; font-weight: bold;">${sektorAverages.value[idx] || 0}</td>
                          </tr>
                      `).join('')}
                  </tbody>
              </table>
          </div>`
    }

    if (chartRefName === 'all-comparison' || chartRefName === 'radarChartRef') {
      // 2. KATEGORİ DAĞILIMI
      html += `
          <div style="margin-bottom: 30px; page-break-inside: avoid;">
              <h2 style="font-size: 16px; color: #111827; margin: 0 0 4px 0; font-weight: bold;">2. Kategori Dağılımı</h2>
              <p style="font-size: 12px; color: #4b5563; margin: 0 0 12px 0;">Banka portföyünün alt kategoriler bazında derinlemesine çeşitlilik analizi</p>
              ${radarImg ? `<div style="text-align: center; margin-bottom: 14px; background: #ffffff; border: 1px solid #e5e7eb; border-radius: 8px; padding: 12px;"><img src="${radarImg}" style="max-width: 100%; height: auto; max-height: 300px; object-fit: contain; display: block; margin: 0 auto;" /></div>` : ''}
              
              <table style="width: 100%; border-collapse: collapse; font-size: 11px; margin-top: 8px;">
                  <thead>
                      <tr style="background-color: #f3f4f6;">
                          <th style="padding: 7px 10px; border: 1px solid #d1d5db; text-align: left; color: #1f2937;">Alt Kategori</th>
                          ${activeCompareBanks.value.map(b => `<th style="padding: 7px 10px; border: 1px solid #d1d5db; text-align: center; color: #1f2937;">${escapeHtml(b.kisa_ad)} (Adet)</th>`).join('')}
                          <th style="padding: 7px 10px; border: 1px solid #d1d5db; text-align: center; color: #1f2937;">Sektör Ortalaması</th>
                      </tr>
                  </thead>
                  <tbody>
                      ${categories.map((cat, idx) => `
                          <tr>
                              <td style="padding: 6px 10px; border: 1px solid #d1d5db; font-weight: bold;">${escapeHtml(cat)}</td>
                              ${activeCompareBanks.value.map(b => `<td style="padding: 6px 10px; border: 1px solid #d1d5db; text-align: center;">${getCategoryCounts(getBankCampaigns(b))[idx] || 0}</td>`).join('')}
                              <td style="padding: 6px 10px; border: 1px solid #d1d5db; text-align: center; color: #059669; font-weight: bold;">${sektorAverages.value[idx] || 0}</td>
                          </tr>
                      `).join('')}
                  </tbody>
              </table>
          </div>`
    }

    if (chartRefName === 'all-comparison' || chartRefName === 'barChartRef') {
      // 3. YAYIN SÜRELERİ
      html += `
          <div style="margin-bottom: 30px; page-break-inside: avoid;">
              <h2 style="font-size: 16px; color: #111827; margin: 0 0 4px 0; font-weight: bold;">3. Yayın Süreleri</h2>
              <p style="font-size: 12px; color: #4b5563; margin: 0 0 12px 0;">Alt kırılımlar bazında kampanyaların aktif yayında kalma süreleri (Ay)</p>
              ${barImg ? `<div style="text-align: center; margin-bottom: 14px; background: #ffffff; border: 1px solid #e5e7eb; border-radius: 8px; padding: 12px;"><img src="${barImg}" style="max-width: 100%; height: auto; max-height: 320px; object-fit: contain; display: block; margin: 0 auto;" /></div>` : ''}
              
              <table style="width: 100%; border-collapse: collapse; font-size: 11px; margin-top: 8px;">
                  <thead>
                      <tr style="background-color: #f3f4f6;">
                          <th style="padding: 7px 10px; border: 1px solid #d1d5db; text-align: left; color: #1f2937;">Kategori</th>
                          ${activeCompareBanks.value.map(b => `<th style="padding: 7px 10px; border: 1px solid #d1d5db; text-align: center; color: #1f2937;">${escapeHtml(b.kisa_ad)} (Ay)</th>`).join('')}
                          <th style="padding: 7px 10px; border: 1px solid #d1d5db; text-align: center; color: #1f2937;">Sektör Ortalaması (Ay)</th>
                      </tr>
                  </thead>
                  <tbody>
                      ${categories.map((cat, idx) => `
                          <tr>
                              <td style="padding: 6px 10px; border: 1px solid #d1d5db; font-weight: bold;">${escapeHtml(cat)}</td>
                              ${activeCompareBanks.value.map(b => `<td style="padding: 6px 10px; border: 1px solid #d1d5db; text-align: center;">${getCategoryDurations(getBankCampaigns(b))[idx] || 0} Ay</td>`).join('')}
                              <td style="padding: 6px 10px; border: 1px solid #d1d5db; text-align: center; color: #2563eb; font-weight: bold;">${sektorDurations.value[idx] || 0} Ay</td>
                          </tr>
                      `).join('')}
                  </tbody>
              </table>
          </div>`
    }

    if (chartRefName === 'all-comparison') {
      // 4. KAMPANYA LİSTESİ
      html += `
          <div style="margin-bottom: 25px;">
              <h2 style="font-size: 16px; color: #111827; margin: 0 0 4px 0; font-weight: bold;">4. Kampanya Listesi</h2>
              <p style="font-size: 12px; color: #4b5563; margin: 0 0 16px 0;">Seçili bankaların aktif kampanya parametre ve detay dökümleri</p>`

      activeCompareBanks.value.forEach((b, bIdx) => {
        const bankCamps = getBankCampaigns(b)
        html += `
          <div style="margin-bottom: 24px; page-break-inside: avoid;">
              <div style="display: flex; align-items: center; justify-content: space-between; background-color: #eff6ff; border-left: 4px solid #2563eb; padding: 8px 12px; border-radius: 4px; margin-bottom: 8px;">
                  <span style="font-size: 13px; font-weight: bold; color: #1e40af;">${escapeHtml(b.kisa_ad || b.resmi_ad)}</span>
                  <span style="font-size: 11px; font-weight: bold; color: #3b82f6; background-color: #ffffff; border: 1px solid #bfdbfe; padding: 2px 8px; border-radius: 12px;">${bankCamps.length} Aktif Kampanya</span>
              </div>
              
              <table style="width: 100%; border-collapse: collapse; font-size: 10.5px;">
                  <thead>
                      <tr style="background-color: #f3f4f6;">
                          <th style="padding: 6px 8px; border: 1px solid #d1d5db; text-align: left; color: #1f2937; width: 25px;">#</th>
                          <th style="padding: 6px 8px; border: 1px solid #d1d5db; text-align: left; color: #1f2937;">Kampanya Adı</th>
                          <th style="padding: 6px 8px; border: 1px solid #d1d5db; text-align: center; color: #1f2937; width: 85px;">Tür</th>
                          <th style="padding: 6px 8px; border: 1px solid #d1d5db; text-align: center; color: #1f2937; width: 65px;">Kâr Payı</th>
                          <th style="padding: 6px 8px; border: 1px solid #d1d5db; text-align: center; color: #1f2937; width: 55px;">Vade</th>
                          <th style="padding: 6px 8px; border: 1px solid #d1d5db; text-align: center; color: #1f2937; width: 80px;">Ödül</th>
                          <th style="padding: 6px 8px; border: 1px solid #d1d5db; text-align: center; color: #1f2937; width: 80px;">Bitiş Tarihi</th>
                      </tr>
                  </thead>
                  <tbody>
                      ${bankCamps.length === 0 ? `
                          <tr>
                              <td colspan="7" style="padding: 8px; border: 1px solid #d1d5db; text-align: center; color: #9ca3af; font-style: italic;">Bu bankaya ait aktif kampanya bulunamadı.</td>
                          </tr>` : bankCamps.slice(0, 50).map((c, i) => {
                        const gb = c.genel_bilgi || {}
                        const fd = c.finansman_detay || {}
                        const pd = c.promosyon_detay || {}
                        return `
                          <tr style="${i % 2 === 1 ? 'background-color: #f9fafb;' : ''}">
                              <td style="padding: 5px 8px; border: 1px solid #d1d5db; color: #6b7280; text-align: center;">${i + 1}</td>
                              <td style="padding: 5px 8px; border: 1px solid #d1d5db; font-weight: 600; color: #111827;">${escapeHtml(gb.kampanya_adi || c.baslik || '-')}</td>
                              <td style="padding: 5px 8px; border: 1px solid #d1d5db; text-align: center; color: #4b5563;">${escapeHtml(gb.kampanya_turu || c.tur || '-')}</td>
                              <td style="padding: 5px 8px; border: 1px solid #d1d5db; text-align: center; font-weight: bold; color: #059669;">${fd.kar_payi_orani !== null && fd.kar_payi_orani !== undefined ? `%${fd.kar_payi_orani}` : '-'}</td>
                              <td style="padding: 5px 8px; border: 1px solid #d1d5db; text-align: center;">${fd.vade_ay ? `${fd.vade_ay} Ay` : '-'}</td>
                              <td style="padding: 5px 8px; border: 1px solid #d1d5db; text-align: center; font-weight: bold; color: #2563eb;">${pd.odul_tutari ? `${Number(pd.odul_tutari).toLocaleString('tr-TR')} ₺` : '-'}</td>
                              <td style="padding: 5px 8px; border: 1px solid #d1d5db; text-align: center; color: #4b5563;">${formatTarih(gb.bitis_tarihi) || '-'}</td>
                          </tr>`
                      }).join('')}
                  </tbody>
              </table>
          </div>`
      })

      html += `</div>`
    }

    // ALTBİLGİ (chat.vue ŞABLONU)
    html += `
          <div style="margin-top: 30px; padding-top: 12px; border-top: 1px solid #e5e7eb; text-align: center; font-size: 11px; color: #9ca3af;">
              Bu rapor, FinAgent Yapay Zeka platformu tarafından otomatik olarak oluşturulmuştur.
          </div>
      </div>`

    const tempDiv = document.createElement('div')
    tempDiv.innerHTML = html

    const cleanBank = bankName.replace(/[^a-zA-Z0-9_À-ſ]/g, '_')
    await window.html2pdf().set({
        margin:       0.4,
        filename:     `FinAgent_${cleanBank}_Genisletilmis_Rapor_${Date.now()}.pdf`,
        image:        { type: 'jpeg', quality: 0.98 },
        html2canvas:  { scale: 2, backgroundColor: '#ffffff', useCORS: true },
        jsPDF:        { unit: 'in', format: 'a4', orientation: 'portrait' },
        pagebreak:    { mode: ['avoid-all', 'css', 'legacy'] },
    }).from(tempDiv).save()

  } catch (err) {
    console.error('PDF dışa aktarma hatası:', err)
  } finally {
    // 3. Kullanıcının önceki görünüm durumunu geri yükle
    expandedCharts.value = prevExpanded
  }
}

// --------------------------- 3. GERÇEK NETLİKTE ULTRA-HD PNG DIŞA AKTARMA ---------------------------
const exportToPNG = async (chartRefName) => {
  const containerId = chartRefName === 'all-comparison' ? 'chart-box-all-comparison' : 'chart-box-' + chartRefName
  const el = document.getElementById(containerId)
  if (!el) { console.error('PNG container bulunamadı:', containerId); return }

  try {
    await betigiYukle('https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js', 'html2canvas')
    const karanlik = document.documentElement.classList.contains('dark')
    const arkaPlan = karanlik ? '#0a0a0a' : '#ffffff'

    // Orijinal canlı canvas piksellerini klona 1:1 netlikte kopyalayarak sahte bulanıklaşmayı engelliyoruz
    const yakala = async (sade) => {
      return await window.html2canvas(el, {
        scale: 3, // 3x Yüksek Çözünürlük
        backgroundColor: arkaPlan,
        useCORS: true,
        logging: false,
        letterRendering: true,
        allowTaint: true,
        ignoreElements: (eleman) => eleman?.hasAttribute?.('data-png-gizle'),
        onclone: (klonDoc, klonEleman) => {
          try {
            const kok = klonEleman || klonDoc.getElementById(containerId)
            klonAnimasyonlariniDurdur(klonDoc, kok)
            klonRenkleriniDuzelt(el, kok)
            
            // Canlı canvas verilerini klon tuvaline doğrudan kopyala
            const origCanvases = el.querySelectorAll('canvas')
            const cloneCanvases = kok.querySelectorAll('canvas')
            origCanvases.forEach((orig, i) => {
              const clone = cloneCanvases[i]
              if (clone && orig) {
                clone.width = orig.width
                clone.height = orig.height
                const ctx = clone.getContext('2d')
                if (ctx) ctx.drawImage(orig, 0, 0)
              }
            })

            if (sade) {
              const s = klonDoc.createElement('style')
              s.textContent = '* { background-image: none !important; box-shadow: none !important; text-shadow: none !important; }'
              ;(klonDoc.head || klonDoc.body)?.appendChild(s)
            }
            if (kok && kok.style) {
              kok.style.backgroundColor = arkaPlan
              kok.style.padding = '24px'
              kok.style.borderRadius = '24px'
              kok.style.maxWidth = 'none'
            }
          } catch (hata) { console.warn('PNG klon hazirlik:', hata) }
        }
      })
    }

    let canvas
    try { canvas = await yakala(false) }
    catch (ilkHata) {
      console.warn('PNG ilk deneme basarisiz, sade moda geciliyor:', ilkHata)
      canvas = await yakala(true)
    }

    const duzTuval = tuvaliDuzlestir(canvas, arkaPlan)
    const dataUrl = duzTuval.toDataURL('image/png', 1.0)
    if (!dataUrl || dataUrl === 'data:,') throw new Error('PNG Görseli oluşturulamadı')

    const bankName = activeCompareBanks.value.length === 1 ? activeCompareBanks.value[0].kisa_ad : 'Sektor_Karsilastirma'
    const cleanBank = bankName.replace(/[^a-zA-Z0-9_À-ſ]/g, '_')
    const link = document.createElement('a')
    link.download = `FinAgent_${cleanBank}_${chartRefName}_UltraHD_${Date.now()}.png`
    link.href = dataUrl
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
  } catch (e) {
    console.error('PNG export hatası:', e)
  }
}

// --------------------------- GENEL DIŞA AKTARMA YÖNLENDİRİCİSİ ---------------------------
const exportChart = async (chartRefName, format) => {
  if (format === 'csv' || format === 'excel' || format === 'xlsx') {
    await exportToExcel(chartRefName)
  } else if (format === 'pdf') {
    await exportToPDF(chartRefName)
  } else if (format === 'png') {
    await exportToPNG(chartRefName)
  }
}


const fetchVeriler = async () => {
  loading.value = true
  try {
    const [bRes, cRes] = await Promise.all([
      fetch('http://localhost:8003/banks').then(res => res.json()),
      fetch('http://localhost:8003/campaigns?limit=1000').then(res => res.json())
    ])
    fetchTopAdvantageous()
    banks.value = Array.isArray(bRes) ? bRes : []
    campaigns.value = Array.isArray(cRes) ? cRes : []
  } catch (error) {
    console.error("Veri çekilirken hata:", error)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchVeriler()
  if (process.client) {
    document.addEventListener('click', handleOutsideClick)

    nextTick(() => {
      const scrollerEl = document.getElementById('main-scroller')
      if (scrollerEl) {
        const content = scrollerEl.querySelector('main') || scrollerEl.firstElementChild
        lenis = new Lenis({
          wrapper: scrollerEl,
          content: content,
          duration: 1.15,
          easing: (t) => Math.min(1, 1.001 - Math.pow(2, -10 * t)),
          smoothWheel: true,
          gestureOrientation: 'vertical',
          touchMultiplier: 1.6
        })
        lenis.on('scroll', ScrollTrigger.update)
        const raf = (time) => {
          lenis?.raf(time)
          lenisRafId = requestAnimationFrame(raf)
        }
        lenisRafId = requestAnimationFrame(raf)
      }
    })
  }
})

onBeforeUnmount(() => {
  if (process.client) {
    document.removeEventListener('click', handleOutsideClick)
    if (lenisRafId) {
      cancelAnimationFrame(lenisRafId)
      lenisRafId = null
    }
    if (lenis) {
      lenis.destroy()
      lenis = null
    }
    ScrollTrigger.getAll().forEach(t => t.kill())
  }
})

const tiers = computed(() => {
  const uniqueTiers = new Set(banks.value.map(b => b.tier).filter(t => t))
  const sortedTiers = Array.from(uniqueTiers).sort()
  return sortedTiers.length > 0 ? sortedTiers : ['Tier 1', 'Tier 2', 'Tier 3']
})

// --- Müşteri Modu ---
const finansmanKampanyalari = computed(() => {
  return campaigns.value.filter(c => c.finansman_detay && c.genel_bilgi && c.genel_bilgi.kampanya_turu && c.genel_bilgi.kampanya_turu.includes('finansman'))
})

const getBankaAd = (banka_id) => {
  const b = banks.value.find(x => x._id === banka_id || x.kisa_ad?.toLowerCase().replace(/ /g, '') === banka_id)
  return b ? (b.kisa_ad || b.resmi_ad) : banka_id
}

const getBankaLogo = (banka_id) => {
  const b = banks.value.find(x => x._id === banka_id || x.kisa_ad?.toLowerCase().replace(/ /g, '') === banka_id)
  return b?.logo_url || null
}

const minKarPayi = computed(() => {
  if (!finansmanKampanyalari.value.length) return 0
  const oranlar = finansmanKampanyalari.value.map(c => parseFloat(c.finansman_detay.kar_payi_orani)).filter(x => !isNaN(x) && x > 0 && x < 100)
  return oranlar.length ? Math.min(...oranlar) : 0
})

const avgVade = computed(() => {
  if (!finansmanKampanyalari.value.length) return 0
  const vadeler = finansmanKampanyalari.value.map(c => parseInt(c.finansman_detay.vade_ay)).filter(x => !isNaN(x) && x > 0)
  if (!vadeler.length) return 0
  const total = vadeler.reduce((sum, v) => sum + v, 0)
  return Math.round(total / vadeler.length)
})

// --- Banka Çalışanı Modu ---
const filteredBanks = computed(() => {
  if (!selectedTier.value || selectedTier.value === 'Tümü') return banks.value
  return banks.value.filter(b => b.tier === selectedTier.value)
})

const selectedBanks = ref([])

const toggleBank = (bId) => {
  if (selectedBanks.value.includes(bId)) {
    selectedBanks.value = selectedBanks.value.filter(id => id !== bId)
  } else {
    selectedBanks.value.push(bId)
  }
}

watch(selectedTier, () => {
  selectedBanks.value = [] 
})

const activeCompareBanks = computed(() => {
  if (selectedBanks.value.length > 0) {
    return banks.value.filter(b => selectedBanks.value.includes(b._id))
  }
  if (selectedTier.value && selectedTier.value !== 'Tümü') {
    return filteredBanks.value
  }
  return []
})

const getBankCampaigns = (b) => {
  return campaigns.value.filter(c => c.genel_bilgi?.banka_id === b._id || c.genel_bilgi?.banka_id === b.kisa_ad?.toLowerCase().replace(/ /g, ''))
}

const bankCampaignCounts = computed(() => {
  const counts = {}
  campaigns.value.forEach(c => {
    const bId = c.genel_bilgi?.banka_id
    if (bId) {
      counts[bId] = (counts[bId] || 0) + 1
    }
  })
  return counts
})

const getBankCount = (b) => {
  return bankCampaignCounts.value[b._id] || bankCampaignCounts.value[b.kisa_ad?.toLowerCase().replace(/ /g, '')] || 0
}

const nf = new Intl.NumberFormat('tr-TR', { maximumFractionDigits: 2 })
const fmt = (n) => nf.format(n)

// --- AI Modülü ---
const showAiPopover = ref(false)
const aiMenuRef = ref(null)
const selectedAiPrompt = ref('rekabet_durumu')
const customPrompt = ref('')
// Analiz koprusunun dondurdugu dogrulama sonuclari (kullaniciya gosterilir)
const aiHata = ref('')
const aiUyarilar = ref([])
const aiYukleniyor = ref(false)

const handleOutsideClick = (e) => {
  if (aiMenuRef.value && !aiMenuRef.value.contains(e.target)) {
    showAiPopover.value = false
  }
}

watch(activeCompareBanks, (newVal) => {
  if (newVal.length === 1) {
    selectedAiPrompt.value = 'rekabet_durumu'
  } else if (newVal.length > 1) {
    selectedAiPrompt.value = 'karsilastirma'
  }
}, { immediate: true })

const executePrompt = async (promptKey) => {
  selectedAiPrompt.value = promptKey
  aiHata.value = ''
  aiUyarilar.value = []
  await goToChat()
}

/*
 * FinAgent'a Sor — ARTIK PROMPT BURADA KURULMUYOR.
 *
 * Eski hâli, sohbete gidecek metnin tamamını burada üretiyordu ve içine bu
 * sayfanın KENDİ hesapladığı rakamları (kampanya sayısı, kategori dağılımı,
 * 6 aylık trend) gömüyordu. İki sorun vardı:
 *
 *   1) O rakamlar backend'in Mongo verisiyle çakışabiliyordu — örneğin
 *      getCategoryCounts() kategoriyi kampanya ADINDA "konut"/"taşıt" arayarak
 *      tahmin ediyor, backend ise gerçek `kampanya_turu` alanını okuyor.
 *      Çakıştığında model, YANLIŞ bir rakamı "kesin veri" diye sunulmuş hâlde
 *      alıp güvenle tekrarlıyordu.
 *   2) 500+ karakterlik veri bloğu bir SORU gibi görünmediği için niyet motoru
 *      onu sınıflandıramıyor, dolayısıyla sohbette tablo/grafik hiç
 *      üretilmiyordu — yani butonun vaat ettiği analiz gelmiyordu.
 *
 * Artık yalnızca YAPILANDIRILMIŞ istek gönderiliyor (analiz türü + banka
 * kodları). Backend (/api/analiz-koprusu) bankaları kendi verisiyle doğrular,
 * tanımadığını reddeder ve kısa/doğal bir soru döner; tabloyu ve piyasa
 * analizini /api/chat kendi doğrulanmış verisinden üretir.
 */
const goToChat = async () => {
  if (activeCompareBanks.value.length === 0) return

  const tur = selectedAiPrompt.value === 'custom' ? 'serbest' : (selectedAiPrompt.value || 'karsilastirma')
  const bankalar = activeCompareBanks.value
    .map(b => b?.id || b?._id || b?.kisa_ad)
    .filter(Boolean)

  aiYukleniyor.value = true
  try {
    const res = await fetch('http://localhost:8003/api/analiz-koprusu', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        kaynak: 'dashboard',
        tur,
        bankalar,
        soru: customPrompt.value?.trim() || null,
        dil: (locale?.value || 'tr').startsWith('en') ? 'en' : 'tr'
      })
    })
    if (!res.ok) throw new Error('HTTP ' + res.status)
    const veri = await res.json()

    aiUyarilar.value = veri?.dogrulama?.uyarilar || []

    if (!veri?.dogrulama?.gecerli || !veri?.prompt) {
      // Doğrulama başarısızsa SOHBETE GİTMİYORUZ. Doğrulanmamış bir soruyu
      // yine de göndermek, tam olarak kaçındığımız şeydir.
      aiHata.value = aiUyarilar.value.join(' ') ||
        t('dashboard.ai_error', 'Analiz isteği doğrulanamadı.')
      return
    }

    showAiPopover.value = false
    chatStore.setChatData(veri.prompt, [])
    router.push('/chat')
  } catch (e) {
    // Köprüye ulaşılamadıysa SESSİZCE eski davranışa dönmüyoruz: kullanıcı
    // doğrulanmamış bir analiz aldığını bilmeli.
    console.error('Analiz köprüsü hatası:', e)
    aiHata.value = t('dashboard.ai_bridge_down',
      'Analiz servisine ulaşılamadı, lütfen tekrar deneyin.')
  } finally {
    aiYukleniyor.value = false
  }
}

// --- Grafikler İçin Veri ---
const categories = ['Konut', 'Taşıt', 'İhtiyaç', 'Kart', 'MGM', 'Yatırım', 'Diğer']

const getCategoryCounts = (camps) => {
  const counts = [0, 0, 0, 0, 0, 0, 0]
  camps.forEach(c => {
    const t = c.genel_bilgi?.kampanya_turu || ''
    const adi = c.genel_bilgi?.kampanya_adi?.toLowerCase() || ''
    
    if (t.includes('finansman') || adi.includes('konut') || adi.includes('taşıt') || adi.includes('ihtiyaç')) {
      if (adi.includes('taşıt') || adi.includes('arac')) counts[1]++
      else if (adi.includes('konut') || adi.includes('ev')) counts[0]++
      else counts[2]++
    }
    else if (t.includes('kart') || adi.includes('kart') || adi.includes('puan')) counts[3]++
    else if (adi.includes('davet') || adi.includes('mgm') || adi.includes('getir') || c.mgm_detay?.is_mgm) counts[4]++
    else if (adi.includes('yatırım') || adi.includes('mevduat') || adi.includes('katılma')) counts[5]++
    else counts[6]++
  })
  return counts
}

const getBaskinKategori = (b) => {
  // 1. Backend'deki banks.yaml dosyasından gelen baskın kategori varsa öncelikli olarak onu kullan
  if (b && b.baskin_kategori) {
    return {
      ad: b.baskin_kategori,
      yuzde: b.baskin_kategori_yuzde || null
    }
  }
  // 2. banks.yaml'da belirtilmemişse kampanyalar üzerinden dinamik hesapla
  const camps = getBankCampaigns(b)
  if (camps.length === 0) return null
  const counts = getCategoryCounts(camps)
  const total = counts.reduce((a, v) => a + v, 0)
  if (total === 0) return null
  let maxIdx = 0
  let maxVal = counts[0]
  for (let i = 1; i < counts.length; i++) {
    if (counts[i] > maxVal) {
      maxVal = counts[i]
      maxIdx = i
    }
  }
  return {
    ad: categories[maxIdx],
    yuzde: Math.round((maxVal / total) * 100)
  }
}

// Süre Analizi
const getCategoryDurations = (camps) => {
  const sums = [0, 0, 0, 0, 0, 0, 0]
  const counts = [0, 0, 0, 0, 0, 0, 0]
  
  camps.forEach(c => {
    const t = c.genel_bilgi?.kampanya_turu || ''
    const adi = c.genel_bilgi?.kampanya_adi?.toLowerCase() || ''
    
    let months = 1.5 
    const bas = c.genel_bilgi?.baslangic_tarihi || c.genel_bilgi?.cekilis_tarihi
    const bit = c.genel_bilgi?.bitis_tarihi
    if (bas && bit) {
      let d1 = new Date(bas)
      let d2 = new Date(bit)
      if(isNaN(d1)) {
         const p = bas.split('.')
         if(p.length===3) d1 = new Date(`${p[2]}-${p[1]}-${p[0]}`)
      }
      if(isNaN(d2)) {
         const p = bit.split('.')
         if(p.length===3) d2 = new Date(`${p[2]}-${p[1]}-${p[0]}`)
      }
      if (!isNaN(d1) && !isNaN(d2)) {
         months = Math.max(0.1, (d2 - d1) / (1000 * 60 * 60 * 24 * 30))
      }
    }
    
    let idx = 6
    if (t.includes('finansman') || adi.includes('konut') || adi.includes('taşıt') || adi.includes('ihtiyaç')) {
      if (adi.includes('taşıt') || adi.includes('arac')) idx = 1
      else if (adi.includes('konut') || adi.includes('ev')) idx = 0
      else idx = 2
    }
    else if (t.includes('kart') || adi.includes('kart') || adi.includes('puan')) idx = 3
    else if (adi.includes('davet') || adi.includes('mgm') || adi.includes('getir') || c.mgm_detay?.is_mgm) idx = 4
    else if (adi.includes('yatırım') || adi.includes('mevduat') || adi.includes('katılma')) idx = 5
    
    sums[idx] += months
    counts[idx]++
  })
  
  return sums.map((s, i) => counts[i] > 0 ? Math.round((s / counts[i]) * 10) / 10 : 0)
}

// Trend Analizi
const last6Months = computed(() => {
  const months = ['Oca', 'Şub', 'Mar', 'Nis', 'May', 'Haz', 'Tem', 'Ağu', 'Eyl', 'Eki', 'Kas', 'Ara']
  const result = []
  const d = new Date()
  for (let i = 5; i >= 0; i--) {
    let m = d.getMonth() - i
    if (m < 0) m += 12
    result.push(months[m])
  }
  return result
})


const getCampaignMonthIndex = (c) => {
  let mIndex = -1
  // 1. Öncelik: Kampanya metninden çıkarılmış baslangic_tarihi
  // 2. Yedek: Başlangıç tarihi olmayanlarda genel_bilgi.cekilis_tarihi
  const dStr = c.genel_bilgi?.baslangic_tarihi || c.genel_bilgi?.cekilis_tarihi || c.cekilis_tarihi
  if (dStr) {
     let d = new Date(dStr)
     if (isNaN(d)) {
        const p = dStr.split('.')
        if (p.length === 3) d = new Date(`${p[2]}-${p[1]}-${p[0]}`)
     }
     if (isNaN(d)) {
        const p = dStr.split('/')
        if (p.length === 3) d = new Date(`${p[2]}-${p[1]}-${p[0]}`)
     }
     if (!isNaN(d)) {
       const now = new Date()
       const diffMonths = (now.getFullYear() - d.getFullYear()) * 12 + (now.getMonth() - d.getMonth())
       if (diffMonths >= 0 && diffMonths <= 5) mIndex = 5 - diffMonths
     }
  }
  return mIndex
}
const getBankTrend = (camps) => {
  const counts = [0,0,0,0,0,0]
  camps.forEach(c => {
    const mIndex = getCampaignMonthIndex(c)
    if (mIndex !== -1) counts[mIndex]++
  })
  return counts
}

// Sektör Ortalaması
const sektorAverages = computed(() => {
  const allCamps = campaigns.value
  const totalBanks = banks.value.length || 1
  const counts = getCategoryCounts(allCamps)
  return counts.map(c => Math.round((c / totalBanks) * 10) / 10)
})

const sektorDurations = computed(() => {
  return getCategoryDurations(campaigns.value)
})

const colors = [
  { bg: 'rgba(59, 130, 246, 0.2)', border: 'rgba(59, 130, 246, 1)' }, // Blue
  { bg: 'rgba(16, 185, 129, 0.2)', border: 'rgba(16, 185, 129, 1)' }, // Emerald
  { bg: 'rgba(245, 158, 11, 0.2)', border: 'rgba(245, 158, 11, 1)' }, // Amber
  { bg: 'rgba(99, 102, 241, 0.2)', border: 'rgba(99, 102, 241, 1)' }, // Indigo
  { bg: 'rgba(236, 72, 153, 0.2)', border: 'rgba(236, 72, 153, 1)' }, // Pink
  { bg: 'rgba(139, 92, 246, 0.2)', border: 'rgba(139, 92, 246, 1)' }, // Violet
  { bg: 'rgba(20, 184, 166, 0.2)', border: 'rgba(20, 184, 166, 1)' }, // Teal
  { bg: 'rgba(239, 68, 68, 0.2)', border: 'rgba(239, 68, 68, 1)' }    // Red
]

// 1. Radar Chart (Kampanya Dağılımı)
  const radarChartData = computed(() => {
    const datasets = activeCompareBanks.value.map((b, i) => {
      const c = colors[i % colors.length]
      return {
        label: b.kisa_ad,
        hidden: hiddenRadar.value.includes(b.kisa_ad),
        backgroundColor: c.bg,
        borderColor: c.border,
        pointBackgroundColor: c.border,
        pointBorderColor: '#fff',
        pointHoverBackgroundColor: '#fff',
        pointHoverBorderColor: c.border,
        data: getCategoryCounts(getBankCampaigns(b))
      }
    })
    
    if (showSectorAverage.value) {
      datasets.push({
        label: 'Sektör Ortalaması',
        hidden: hiddenRadar.value.includes('Sektör Ortalaması'),
        backgroundColor: 'rgba(148, 163, 184, 0.1)',
        borderColor: 'rgba(148, 163, 184, 0.6)',
        borderDash: [5, 5],
        pointBackgroundColor: 'rgba(148, 163, 184, 0.6)',
        pointBorderColor: '#fff',
        data: sektorAverages.value
      })
    }
  
    return { labels: categories, datasets }
  })
  
  const radarOptions = {
    devicePixelRatio: 2.5,
    responsive: true,
    maintainAspectRatio: false,
    scales: {
      r: {
        angleLines: { color: 'rgba(156, 163, 175, 0.2)' },
        grid: { color: 'rgba(156, 163, 175, 0.2)' },
        pointLabels: {
          font: { family: "'Plus Jakarta Sans', sans-serif", size: 9, weight: 'bold' },
          color: '#6b7280'
        },
        ticks: { display: false }
      }
    },
    plugins: {
      legend: {
        onClick: customLegendClickRadar,
        position: 'bottom',
        labels: { font: { family: "'Plus Jakarta Sans', sans-serif", size: 11, weight: 'bold' }, usePointStyle: true, boxWidth: 8 }
      }
    }
  }

  const detailedRadarOptions = {
    devicePixelRatio: 2.5,
    responsive: true,
    maintainAspectRatio: false,
    scales: {
      r: {
        angleLines: { color: 'rgba(0, 0, 0, 0.05)' },
        grid: { color: 'rgba(0, 0, 0, 0.05)', circular: true },
        ticks: { display: false, stepSize: 5 },
        pointLabels: {
          font: { family: "'Plus Jakarta Sans', sans-serif", size: 9, weight: '500' },
          color: '#6b7280'
        }
      }
    },
    plugins: {
      legend: { onClick: customLegendClickRadar, position: 'bottom', labels: { font: { family: "'Plus Jakarta Sans', sans-serif", size: 12, weight: 'bold' }, usePointStyle: true, boxWidth: 10 } },

    zoom: {
      pan: {
        enabled: true,
        mode: 'xy'
      },
      zoom: {
        wheel: {
          enabled: true,
        },
        pinch: {
          enabled: true
        },
        mode: 'xy',
      }
    },

    }
  }

  // 2. Bar Chart (Süre)
  const durationBarChartData = computed(() => {
    const datasets = activeCompareBanks.value.map((b, i) => {
      const c = colors[i % colors.length]
      return {
        label: b.kisa_ad,
        hidden: hiddenBar.value.includes(b.kisa_ad),
        backgroundColor: c.border,
        borderRadius: 4,
        data: getCategoryDurations(getBankCampaigns(b))
      }
    })
  
    if (showSectorAverage.value) {
      datasets.push({
        label: 'Sektör Ortalaması',
        hidden: hiddenBar.value.includes('Sektör Ortalaması'),
        backgroundColor: '#94a3b8',
        borderRadius: 4,
        data: sektorDurations.value
      })
    }
  
    return { labels: categories, datasets }
  })
  
  const durationBarOptions = computed(() => ({
    devicePixelRatio: 2.5,
    responsive: true,
    maintainAspectRatio: false,
    indexAxis: 'y',
    scales: {
      x: { grid: { color: 'rgba(156, 163, 175, 0.1)' }, ticks: { font: { family: "'Plus Jakarta Sans', sans-serif", size: 11 } } },
      y: { grid: { display: false }, ticks: { font: { family: "'Plus Jakarta Sans', sans-serif", size: 11, weight: '600' } } }
    },
    plugins: {
      legend: {
        onClick: customLegendClickBar,
        position: 'bottom',
        labels: { font: { family: "'Plus Jakarta Sans', sans-serif", size: 11, weight: 'bold' }, usePointStyle: true, boxWidth: 8 }
      },
      zoom: {
        pan: { enabled: true, mode: 'xy' },
        zoom: { wheel: { enabled: chartInteracts.value.duration }, pinch: { enabled: true }, mode: 'xy' }
      }
    }
  }))
  
  // 3. Line Chart (Trend)
  const lineChartData = computed(() => {
    const datasets = activeCompareBanks.value.map((b, i) => {
      const c = colors[i % colors.length]
      return {
        label: b.kisa_ad,
        hidden: hiddenLine.value.includes(b.kisa_ad),
        borderColor: c.border,
        backgroundColor: c.border,
        pointBackgroundColor: c.border,
        pointBorderColor: '#fff',
        pointHoverBackgroundColor: '#fff',
        pointHoverBorderColor: c.border,
        tension: 0.4,
        data: getBankTrend(getBankCampaigns(b))
      }
    })
  
    if (showSectorAverage.value) {
      datasets.push({
        label: 'Sektör Ortalaması',
        hidden: hiddenLine.value.includes('Sektör Ortalaması'),
        borderColor: 'rgba(16, 185, 129, 0.8)',
        backgroundColor: 'rgba(16, 185, 129, 0.8)',
        borderDash: [5, 5],
        pointBackgroundColor: 'rgba(16, 185, 129, 0.8)',
        pointBorderColor: '#fff',
        tension: 0.4,
        data: getBankTrend(campaigns.value).map(x => Math.round(x / Math.max(1, banks.value.length)))
      })
    }
  
    return { labels: last6Months.value, datasets }
  })
  
  const lineOptions = computed(() => ({
    devicePixelRatio: 2.5,
    responsive: true,
    maintainAspectRatio: false,
    scales: {
      x: { grid: { display: false }, ticks: { font: { family: "'Plus Jakarta Sans', sans-serif", size: 11, weight: 'bold' } } },
      y: { grid: { color: 'rgba(156, 163, 175, 0.1)' }, ticks: { font: { family: "'Plus Jakarta Sans', sans-serif", size: 11 } } }
    },
    plugins: {
      legend: {
        onClick: customLegendClickLine,
        position: 'bottom',
        labels: { font: { family: "'Plus Jakarta Sans', sans-serif", size: 11, weight: 'bold' }, usePointStyle: true, boxWidth: 8 }
      },
      zoom: {
        pan: { enabled: true, mode: 'xy' },
        zoom: { wheel: { enabled: chartInteracts.value.line }, pinch: { enabled: true }, mode: 'xy' }
      }
    }
  }))
  
  const activeCampaignsList = computed(() => {
    let camps = []
    activeCompareBanks.value.forEach(b => {
      camps = camps.concat(getBankCampaigns(b))
    })
    return camps
  })
  
  const cleanMainCategory = (name) => {
    if (!name || name === 'Bilinmiyor') return 'Genel'
    let n = name.toLowerCase().replace(/_kampanyasi|_kampanyalari|_urunu/g, '').replace(/_/g, ' ')
    const map = {
      'alisveris puani': 'Alışveriş',
      'finansman diger': 'Finansman',
      'ihtiyac finansmani': 'İhtiyaç',
      'kart': 'Kart',
      'konut finansmani': 'Konut',
      'mgm': 'MGM',
      'tasit finansmani': 'Taşıt',
      'yatirim': 'Yatırım',
      'yeni musteri': 'Yeni Müşteri'
    }
    if (map[n]) return map[n]
    return n.split(' ').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ')
  }

  const cleanCategoryName = (name) => {
    if (!name) return 'Diğer'
    let n = name.toLowerCase()
    n = n.replace(/_kampanyalari|_kampanyasi|-fon/g, '')
    n = n.replace(/_/g, ' ')
    
    const map = {
      'yatirim': 'Yatırım',
      'ticari': 'Ticari',
      'kobi': 'KOBİ',
      'bireysel': 'Bireysel',
      'dijital': 'Dijital',
      'finansman': 'Finansman',
      'odeme': 'Ödeme',
      'musteri ol': 'Müşteri Ol',
      'seyahat': 'Seyahat',
      'pos': 'POS',
      'sigorta': 'Sigorta',
      'kart': 'Kart',
      'ihtiyac': 'İhtiyaç'
    }
    
    if (map[n]) return map[n]
    return n.split(' ').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ')
  }

  const getCombinedCategory = (turu, alt) => {
      const main = cleanMainCategory(turu)
      const sub = cleanCategoryName(alt)
      if (main === sub) return main
      if (sub === 'Genel' || sub === 'Diğer') return main
      if (main === 'Genel') return sub
      
      // Chart.js'de alt alta (multiline) yazması için Dizi döndürüyoruz!
      return [main, `(${sub})`] 
  }
  
  // Eşleştirme için label dizisini tek bir stringe çeviren yardımcı
  const stringifyLabel = (l) => Array.isArray(l) ? l.join(' ') : String(l)

  const uniqueAltKategoriler = computed(() => {
    const s = new Map() // Use map to keep unique by stringified key
    activeCampaignsList.value.forEach(c => {
      const turu = c.genel_bilgi?.kampanya_turu
      const alt = c.genel_bilgi?.alt_kategori
      if (turu || alt) {
         const comb = getCombinedCategory(turu, alt)
         const key = stringifyLabel(comb)
         s.set(key, comb)
      }
    })
    const arr = Array.from(s.values()).sort((a, b) => stringifyLabel(a).localeCompare(stringifyLabel(b)))
    return arr.length > 0 ? arr : ['Veri Yok']
  })
  
  const detailedRadarData = computed(() => {
    const labels = uniqueAltKategoriler.value
    const datasets = activeCompareBanks.value.map((b, i) => {
      const c = colors[i % colors.length]
      const bCamps = getBankCampaigns(b)
      const data = labels.map(label => {
         const targetKey = stringifyLabel(label)
         return bCamps.filter(camp => stringifyLabel(getCombinedCategory(camp.genel_bilgi?.kampanya_turu, camp.genel_bilgi?.alt_kategori)) === targetKey).length
      })
      return {
        label: b.kisa_ad,
        hidden: hiddenRadar.value.includes(b.kisa_ad),
        backgroundColor: c.bg,
        borderColor: c.border,
        pointBackgroundColor: c.border,
        pointBorderColor: '#fff',
        pointHoverBackgroundColor: '#fff',
        pointHoverBorderColor: c.border,
        data
      }
    })
    
    if (showSectorAverage.value) {
      const sectorData = labels.map(label => {
        const targetKey = stringifyLabel(label)
        const total = campaigns.value.filter(camp => stringifyLabel(getCombinedCategory(camp.genel_bilgi?.kampanya_turu, camp.genel_bilgi?.alt_kategori)) === targetKey).length
        const uniqueBanks = new Set(campaigns.value.filter(camp => stringifyLabel(getCombinedCategory(camp.genel_bilgi?.kampanya_turu, camp.genel_bilgi?.alt_kategori)) === targetKey).map(c => c.banka_id)).size
        return uniqueBanks > 0 ? Math.round(total / uniqueBanks) : 0
      })
      
      datasets.push({
          label: 'Sektör Ortalaması',
          hidden: hiddenRadar.value.includes('Sektör Ortalaması'),
          backgroundColor: 'rgba(156, 163, 175, 0.2)',
          borderColor: '#9ca3af',
          pointBackgroundColor: '#9ca3af',
          pointBorderColor: '#fff',
          data: sectorData
      })
    }
    
    return { labels, datasets }
  })
  
  const detailedBarData = computed(() => {
    const labels = uniqueAltKategoriler.value
    const datasets = activeCompareBanks.value.map((b, i) => {
      const c = colors[i % colors.length]
      const bCamps = getBankCampaigns(b)
      
      const data = labels.map(label => {
        const targetKey = stringifyLabel(label)
        const camps = bCamps.filter(camp => stringifyLabel(getCombinedCategory(camp.genel_bilgi?.kampanya_turu, camp.genel_bilgi?.alt_kategori)) === targetKey)
        if (camps.length === 0) return 0
        
        let totalMonths = 0
        let count = 0
        camps.forEach(camp => {
          const bas = camp.genel_bilgi?.baslangic_tarihi
          const bit = camp.genel_bilgi?.bitis_tarihi
          if (bas && bit) {
            let d1 = new Date(bas)
            let d2 = new Date(bit)
            if(isNaN(d1)) {
               const p = bas.split('.')
               if(p.length===3) d1 = new Date(`${p[2]}-${p[1]}-${p[0]}`)
            }
            if(isNaN(d2)) {
               const p = bit.split('.')
               if(p.length===3) d2 = new Date(`${p[2]}-${p[1]}-${p[0]}`)
            }
            if (!isNaN(d1) && !isNaN(d2)) {
               totalMonths += Math.max(0.1, (d2 - d1) / (1000 * 60 * 60 * 24 * 30))
               count++
            }
          }
        })
        return count > 0 ? Math.round((totalMonths / count) * 10) / 10 : 0
      })
      return {
        label: b.kisa_ad,
        hidden: hiddenBar.value.includes(b.kisa_ad),
        backgroundColor: c.border,
        borderRadius: 4,
        data
      }
    })
    
    if (showSectorAverage.value) {
      const sectorData = labels.map(label => {
        const targetKey = stringifyLabel(label)
        const camps = campaigns.value.filter(camp => stringifyLabel(getCombinedCategory(camp.genel_bilgi?.kampanya_turu, camp.genel_bilgi?.alt_kategori)) === targetKey)
        if (camps.length === 0) return 0
        
        let totalMonths = 0
        let count = 0
        camps.forEach(camp => {
          const bas = camp.genel_bilgi?.baslangic_tarihi
          const bit = camp.genel_bilgi?.bitis_tarihi
          if (bas && bit) {
            let d1 = new Date(bas)
            let d2 = new Date(bit)
            if(isNaN(d1) || isNaN(d2)) return
            totalMonths += Math.max(0.1, (d2 - d1) / (1000 * 60 * 60 * 24 * 30))
            count++
          }
        })
        return count > 0 ? Math.round((totalMonths / count) * 10) / 10 : 0
      })
      
      datasets.push({
          label: 'Sektör Ortalaması',
          hidden: hiddenBar.value.includes('Sektör Ortalaması'),
          backgroundColor: '#94a3b8',
          borderRadius: 4,
          data: sectorData
      })
    }
    
    return { labels, datasets }
  })
  
  const detailedLineData = computed(() => {
    const labels = last6Months.value
    const topAltKats = uniqueAltKategoriler.value.slice(0, 8)
    
    const datasets = topAltKats.map((ak, i) => {
      const c = colors[i % colors.length]
      const counts = [0,0,0,0,0,0]
      
      activeCampaignsList.value.forEach(camp => {
        if (camp.genel_bilgi?.alt_kategori !== ak) return
        const mIndex = getCampaignMonthIndex(camp)
        if (mIndex !== -1) counts[mIndex]++
      })
      
      return {
        label: ak,
        borderColor: c.border,
        backgroundColor: c.border,
        pointBackgroundColor: c.border,
        pointBorderColor: '#fff',
        tension: 0.4,
        data: counts
      }
    })
    return { labels, datasets }
  })
  
  const detailedChartOptions = computed(() => ({
    devicePixelRatio: 2.5,
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { onClick: customLegendClickBar, position: 'bottom', labels: { font: { family: "'Plus Jakarta Sans', sans-serif", size: 12, weight: 'bold' }, usePointStyle: true, boxWidth: 10 } },
      zoom: {
        pan: { enabled: true, mode: 'xy' },
        zoom: { wheel: { enabled: chartInteracts.value.line }, pinch: { enabled: true }, mode: 'xy' }
      }
    }
  }))
  const temp_detailedChartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { onClick: customLegendClickBar, position: 'bottom', labels: { font: { family: "'Plus Jakarta Sans', sans-serif", size: 12, weight: 'bold' }, usePointStyle: true, boxWidth: 10 } },

    zoom: {
      pan: {
        enabled: true,
        mode: 'xy'
      },
      zoom: {
        wheel: {
          enabled: true,
        },
        pinch: {
          enabled: true
        },
        mode: 'xy',
      }
    },

    }
  }
  const detailedBarOptions = computed(() => ({ ...detailedChartOptions.value, indexAxis: 'y', plugins: { ...detailedChartOptions.value.plugins, zoom: { pan: { enabled: true, mode: 'xy' }, zoom: { wheel: { enabled: chartInteracts.value.duration }, pinch: { enabled: true }, mode: 'xy' } } } }))

// MGM Kampanyaları
// MGM Kampanyaları
const mgmCampaigns = computed(() => {
  if (activeCompareBanks.value.length === 0) return []
  const bankIds = activeCompareBanks.value.map(b => String(b._id))
  const bankNames = activeCompareBanks.value.map(b => b.kisa_ad?.toLowerCase().replace(/ /g, ''))
  
  return campaigns.value.filter(c => {
    const bId = String(c.genel_bilgi?.banka_id)
      if (!bankIds.includes(bId) && !bankNames.includes(bId)) return false
      
      // Kullanıcı talebi: Sadece veritabanında is_mgm bayrağı true olanları çek
      return c.mgm_detay && (c.mgm_detay.is_mgm === true || c.mgm_detay.is_mgm === 'true')
    })
})

</script>

<template>
  <div class="pro-dashboard max-w-7xl mx-auto px-6 pt-16 pb-12 space-y-8 animate-fade-in antialiased text-neutral-800 dark:text-neutral-200 transition-transform duration-500 ease-[cubic-bezier(0.2,0.8,0.2,1)]"
       :class="selectedModalCampaign ? 'lg:-translate-x-28 xl:-translate-x-32' : 'translate-x-0'">
    
    <!-- ================= ORTALANMIŞ BAŞLIK ================= -->
    <div class="flex flex-col items-center text-center gap-3">
      <div class="flex flex-wrap items-center justify-center gap-3">
        <h1 class="reveal-title text-4xl md:text-5xl font-bold bg-clip-text text-transparent gradient-text pb-1">
          {{ isBankaci ? $t('dashboard.title_banker', 'Pazar Analizi') : $t('dashboard.title_customer', 'Pazar Analizi') }}
        </h1>
        <span v-if="isBankaci" class="px-2 py-0.5 text-[10px] font-bold uppercase tracking-widest bg-blue-50 text-blue-600 dark:bg-blue-950/50 dark:text-blue-400 border border-blue-200/60 dark:border-blue-800/40 rounded-full shrink-0">
          {{ $t('dashboard.banker_badge', 'Banka Çalışanı') }}
        </span>
      </div>
      <p class="text-sm md:text-base text-neutral-500 dark:text-neutral-400 max-w-2xl">
        {{ isBankaci ? $t('dashboard.subtitle_banker', 'Katılım bankacılığı sektöründeki kampanya hareketlerini ve pazar rekabetini takip edin.') : $t('dashboard.subtitle_customer', 'Tüm katılım bankalarındaki en güncel ve size en uygun oranları karşılaştırın.') }}
      </p>
      <div class="h-1 w-24 rounded-full bg-gradient-to-r from-blue-500 to-cyan-400 mt-1 title-underline"></div>
    </div>

    <!-- SKELETON LOADERS -->
    <div v-if="loading" class="space-y-8">
      <div class="grid grid-cols-1 sm:grid-cols-3 gap-5">
        <div v-for="i in 3" :key="'kpi-skel-'+i" class="p-6 rounded-2xl border border-neutral-200 dark:border-neutral-800 bg-white dark:bg-neutral-900 shadow-sm animate-pulse">
          <div class="h-4 bg-neutral-200 dark:bg-neutral-800 rounded w-1/2 mb-4"></div>
          <div class="flex items-end gap-2">
            <div class="h-10 bg-neutral-200 dark:bg-neutral-800 rounded w-1/3"></div>
            <div class="h-4 bg-neutral-200 dark:bg-neutral-800 rounded w-1/4 mb-1"></div>
          </div>
        </div>
      </div>
    </div>

    <!-- YÜKLENDİ İÇERİK -->
    <template v-else>
      
      <!-- MÜŞTERİ MODU -->
      <div v-if="!isBankaci" class="space-y-6 animate-fade-in">
        <!-- EN AVANTAJLI KAMPANYALAR VİTRİNİ (ALT ALTA) -->
        <div v-if="!loading && Object.keys(topCampaigns).length > 0" class="flex flex-col gap-6">
          
          <template v-for="(category, key) in {
            lowest_profit: { title: $t('dashboard.lowest_profit', 'En Düşük Kâr Payı'), icon: 'M13 10V3L4 14h7v7l9-11h-7z', color: 'blue', suffix: '%', isPrefix: true, unit: '' },
            highest_reward: { title: $t('dashboard.highest_reward', 'En Yüksek Ödül'), icon: 'M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z', color: 'emerald', suffix: '₺', isPrefix: false, unit: '' },
            longest_term: { title: $t('dashboard.longest_term', 'En Uzun Vade'), icon: 'M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z', color: 'indigo', suffix: '', isPrefix: false, unit: 'Ay' },
            lowest_fee: { title: $t('dashboard.lowest_fee', 'En Düşük Ücret'), icon: 'M17 9V7a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2m2 4h10a2 2 0 002-2v-6a2 2 0 00-2-2H9a2 2 0 00-2 2v6a2 2 0 002 2zm7-5a2 2 0 11-4 0 2 2 0 014 0z', color: 'orange', suffix: '₺', isPrefix: false, unit: '' },
            highest_loan: { title: $t('dashboard.highest_loan', 'En Yüksek Tutar'), icon: 'M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z', color: 'cyan', suffix: '₺', isPrefix: false, unit: '' },
            highest_mgm: { title: $t('dashboard.highest_mgm', 'En Yüksek MGM (Davet)'), icon: 'M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z', color: 'purple', suffix: '₺', isPrefix: false, unit: '' },
            highest_cashback: { title: $t('dashboard.highest_cashback', 'En Yüksek Nakit İade'), icon: 'M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15', color: 'pink', suffix: '%', isPrefix: true, unit: '' }
          }" :key="key">
            
            <div v-if="topCampaigns[key]?.length" :class="`bg-white/80 dark:bg-neutral-800/50 backdrop-blur-md border border-${category.color}-200 dark:border-${category.color}-800/50 rounded-xl p-6 shadow-sm hover:shadow-md transition-shadow relative overflow-hidden`">
              <div :class="`absolute right-0 top-0 w-32 h-32 bg-${category.color}-100 dark:bg-${category.color}-900/20 rounded-bl-full opacity-50`"></div>
              <div :class="`relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-${category.color}-100 dark:border-${category.color}-900/50 pb-4 mb-4`">
                <h3 :class="`text-lg font-bold text-${category.color}-600 dark:text-${category.color}-400 flex items-center gap-2`">
                  <span :class="`p-2 bg-${category.color}-100 dark:bg-${category.color}-900/50 rounded-lg`">
                    <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" :d="category.icon"/></svg>
                  </span>
                  {{ category.title }}
                </h3>
              </div>
              <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 relative z-10">
                <div v-for="(camp, i) in topCampaigns[key].slice(0,3)" :key="key+i" @click="openCampaignModal(camp.id)" :class="`cursor-pointer bg-white dark:bg-neutral-900 border border-neutral-200/80 dark:border-neutral-800 rounded-2xl p-5 flex flex-col justify-between hover:border-${category.color}-400 dark:hover:border-${category.color}-500 hover:shadow-lg hover:-translate-y-1 active:scale-[0.99] transition-all duration-200 group relative`">
                  <div>
                    <div class="flex items-center justify-between gap-2 mb-1.5">
                      <span class="text-xs font-bold uppercase tracking-wider text-neutral-500 dark:text-neutral-400">{{ camp.banka }}</span>
                      <svg class="w-4 h-4 text-neutral-300 dark:text-neutral-600 group-hover:text-neutral-600 dark:group-hover:text-neutral-300 group-hover:translate-x-0.5 transition-all" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"/></svg>
                    </div>
                    <div class="font-bold text-sm text-neutral-800 dark:text-neutral-100 line-clamp-2 group-hover:text-neutral-950 dark:group-hover:text-white transition-colors" :title="camp.baslik">{{ camp.baslik }}</div>
                  </div>
                  <div class="mt-4 pt-3 border-t border-neutral-100 dark:border-neutral-800 flex justify-between items-end">
                    <span class="text-xs font-medium text-neutral-400">{{ $t('dashboard.value', 'Değer') }}</span>
                    <span :class="`text-xl font-black tracking-tight text-${category.color}-600 dark:text-${category.color}-400`">
                      <template v-if="category.isPrefix">{{ category.suffix }}{{ Number(camp.deger).toLocaleString('tr-TR') }} {{ category.unit }}</template>
                      <template v-else>{{ Number(camp.deger).toLocaleString('tr-TR') }} {{ category.suffix }} {{ category.unit }}</template>
                    </span>
                  </div>
                </div>
              </div>
            </div>
            
          </template>
</div>
      </div>

      <!-- BANKA ÇALIŞANI MODU -->
      <div v-else class="space-y-8 animate-fade-in">
        
        <!-- Üst Kontrol Barı: Tier Butonları -->
        <div class="flex items-center p-1 rounded-lg border border-neutral-300/50 dark:border-neutral-600/50 bg-white/40 dark:bg-neutral-800/40 backdrop-blur-md shadow-sm w-fit">
          <button 
            v-for="tier in tiers" 
            :key="tier"
            @click="selectedTier = (selectedTier === tier ? null : tier)"
            :class="selectedTier === tier ? 'bg-white dark:bg-neutral-700 shadow-sm text-blue-600 dark:text-cyan-400 font-bold' : 'text-neutral-600 dark:text-neutral-300 hover:text-neutral-900 dark:hover:text-white font-medium'"
            class="px-4 py-1.5 text-xs rounded-md transition-all whitespace-nowrap cursor-pointer select-none"
          >
            {{ tier }}
          </button>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
          <div v-for="b in filteredBanks" :key="b._id" 
            @click="toggleBank(b._id)"
            class="p-6 rounded-2xl border bg-white dark:bg-neutral-900 shadow-sm hover:shadow-lg hover:border-blue-300 transition-all relative group overflow-hidden cursor-pointer"
            :class="selectedBanks.includes(b._id) ? 'border-blue-500 ring-2 ring-blue-500/20 shadow-blue-500/10' : 'border-neutral-200 dark:border-neutral-800'"
          >
            
            <div class="flex justify-between items-start mb-6">
              <div class="w-14 h-14 rounded-xl bg-white dark:bg-neutral-800 border border-neutral-100 dark:border-neutral-700 flex items-center justify-center p-2 shadow-sm group-hover:scale-105 transition-transform duration-300">
                <img v-if="b.logo_url" :src="b.logo_url" class="w-full h-full object-contain" />
                <span v-else class="text-xl font-extrabold text-neutral-400">{{ b.kisa_ad?.charAt(0) }}</span>
              </div>
              <div class="flex flex-row items-start gap-1.5">
                <span class="px-2.5 py-1 text-[10px] font-extrabold uppercase tracking-widest rounded-md shadow-sm"
                  :class="b.tier === 'Tier 1' ? 'bg-blue-100 text-blue-800 dark:bg-blue-900/50 dark:text-blue-300' : (b.tier === 'Tier 2' ? 'bg-indigo-100 text-indigo-800 dark:bg-indigo-900/50 dark:text-indigo-300' : 'bg-sky-100 text-sky-800 dark:bg-sky-900/50 dark:text-sky-300')">
                  {{ b.tier || 'Bilinmiyor' }}
                </span>
                <span class="px-2.5 py-1 text-[10px] font-extrabold uppercase tracking-widest rounded-md border shadow-sm border-neutral-200 bg-neutral-50 text-neutral-700 dark:border-neutral-700 dark:bg-neutral-800 dark:text-neutral-300">
                  {{ b.mulkiyet_turu || 'Bilinmiyor' }}
                </span>
              </div>
            </div>

            <div>
              <h3 class="text-xl font-extrabold text-neutral-900 dark:text-white truncate tracking-tight" :title="b.resmi_ad">{{ b.kisa_ad || b.resmi_ad }}</h3>
              <p class="text-sm text-neutral-500 dark:text-neutral-400 mt-1 font-medium">{{ $t('dashboard.asset_size', 'Aktif Büyüklük') }}: <span class="font-bold text-neutral-800 dark:text-neutral-200">{{ b.aktif_buyukluk_milyar_tl }} Milyar ₺</span></p>
            </div>

            <div class="mt-6 pt-5 border-t border-neutral-100 dark:border-neutral-800 flex justify-between items-end">
              <div>
                <p class="text-[10px] font-bold uppercase tracking-widest text-neutral-400 mb-1.5">{{ $t('dashboard.dominant_category', 'Baskın Kategori') }}</p>
                <p class="text-[13px] font-bold text-neutral-700 dark:text-neutral-300">
                  <span v-if="getBaskinKategori(b)">
                    {{ getBaskinKategori(b).ad }} 
                    <span class="text-emerald-500 font-extrabold ml-1">%{{ getBaskinKategori(b).yuzde }}</span>
                  </span>
                  <span v-else>-</span>
                </p>
              </div>
              <div class="text-right">
                <p class="text-[10px] font-bold uppercase tracking-widest text-neutral-400 mb-1.5">{{ $t('dashboard.active_campaign', 'Aktif Kampanya') }}</p>
                <p class="text-3xl font-extrabold text-blue-600 dark:text-blue-400 tabular-nums tracking-tighter">{{ getBankCount(b) }}</p>
              </div>
            </div>
            
            <div class="mt-4 pt-4 border-t border-neutral-100 dark:border-neutral-800 flex justify-between items-center">
              <div>
                <p class="text-[10px] font-bold uppercase tracking-widest text-neutral-400 mb-0.5">{{ $t('dashboard.last_scan', 'Son Tarama') }}</p>
                <p class="text-[11px] font-medium text-neutral-500 flex items-center gap-1">
                  <span :class="b.aktif === false ? 'w-1.5 h-1.5 rounded-full bg-red-500' : 'w-1.5 h-1.5 rounded-full bg-emerald-500'"></span>
                  {{ b.aktif === false ? 'Pasif' : 'Bugün' }}
                </p>
              </div>
              <a v-if="b.web_sitesi" :href="b.web_sitesi" target="_blank" @click.stop class="flex items-center gap-1 text-[11px] font-bold text-blue-600 hover:text-blue-700 transition-colors">
                {{ $t('dashboard.official_site', 'Resmi Site') }}
                <svg class="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5"><path stroke-linecap="round" stroke-linejoin="round" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" /></svg>
              </a>
            </div>
            
          </div>
        </div>

        <!-- YENİ: GRAFİKLİ KARŞILAŞTIRMA ALANI -->
        <div id="chart-box-all-comparison" v-if="activeCompareBanks.length > 0" class="mt-8 rounded-3xl border border-blue-200 dark:border-blue-900/50 bg-neutral-50/50 dark:bg-neutral-900 shadow-sm animate-fade-in relative">
          
          <!-- Üst Bilgi Çubuğu (AI Butonu & İndirme Butonları) -->
          <div class="px-6 lg:px-8 py-5 border-b border-blue-100 dark:border-blue-900 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
            <h2 class="text-xl font-extrabold text-neutral-900 dark:text-white tracking-tight">
              {{ activeCompareBanks.length === 1 ? activeCompareBanks[0].kisa_ad + ' - Detay Analiz' : 'Rekabet Analizi' }}
            </h2>
            
            <div class="flex flex-wrap items-center gap-3 w-full sm:w-auto justify-between sm:justify-end">
              
              <!-- FinAgent AI Balon / Popover Menüsü -->
              <div class="relative" ref="aiMenuRef" data-png-gizle>
                <button 
                  @click="showAiPopover = !showAiPopover" 
                  :title="$t('dashboard.ask_finagent', 'FinAgent Yapay Zeka Analizi')" 
                  class="flex items-center gap-2 px-3.5 py-2 bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-blue-950/50 dark:to-indigo-950/50 hover:from-blue-100 hover:to-indigo-100 dark:hover:from-blue-900/50 dark:hover:to-indigo-900/50 text-blue-600 dark:text-cyan-400 border border-blue-200 dark:border-blue-800/60 rounded-xl font-bold text-xs shadow-sm hover:shadow active:scale-95 transition-all duration-200 group"
                >
                  <img src="/logo.svg" class="w-5 h-5 object-contain group-hover:scale-110 transition-transform duration-200" alt="FinAgent" />
                  <span>{{ $t('dashboard.ask_finagent', "FinAgent'a Sor") }}</span>
                  <svg class="w-3.5 h-3.5 text-blue-500 transition-transform duration-200" :class="showAiPopover ? 'rotate-180' : ''" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
                  </svg>
                </button>

                <!-- Açılır Balon (Dropdown Popover) -->
                <Transition
                  enter-active-class="transition-all duration-200 ease-out"
                  enter-from-class="opacity-0 scale-95 -translate-y-2"
                  enter-to-class="opacity-100 scale-100 translate-y-0"
                  leave-active-class="transition-all duration-150 ease-in"
                  leave-from-class="opacity-100 scale-100 translate-y-0"
                  leave-to-class="opacity-0 scale-95 -translate-y-2"
                >
                  <div v-if="showAiPopover" class="absolute left-0 sm:left-auto sm:right-0 top-full mt-2 w-[calc(100vw-3.5rem)] max-w-[340px] sm:max-w-none sm:w-96 bg-white dark:bg-neutral-900 border border-neutral-200 dark:border-neutral-800 rounded-2xl shadow-2xl z-50 p-4 space-y-3">
                    
                    <!-- Balon Üst Başlığı -->
                    <div class="flex items-center justify-between pb-2.5 border-b border-neutral-100 dark:border-neutral-800">
                      <div class="flex items-center gap-2">
                        <div class="w-6 h-6 rounded-lg bg-blue-50 dark:bg-blue-900/30 flex items-center justify-center p-1">
                          <img src="/logo.svg" class="w-full h-full object-contain" alt="" />
                        </div>
                        <span class="text-xs font-extrabold text-neutral-800 dark:text-white">{{ $t('dashboard.market_intelligence', 'FinAgent Pazar Zekası') }}</span>
                      </div>
                      <span class="text-[11px] font-semibold text-neutral-400">
                        {{ activeCompareBanks.length === 1 ? activeCompareBanks[0].kisa_ad : activeCompareBanks.length + ' ' + $t('dashboard.banks_selected', 'Banka Seçili') }}
                      </span>
                    </div>

                    <!-- 3 Soru + 1 Soru Giriş Alanı -->
                    <div class="space-y-2">
                      
                      <!-- Tek Banka: 3 Soru -->
                      <template v-if="activeCompareBanks.length === 1">
                        <button @click="executePrompt('rekabet_durumu')" class="w-full text-left p-2.5 rounded-xl bg-neutral-50/70 dark:bg-neutral-800/40 hover:bg-blue-50 dark:hover:bg-blue-900/30 border border-neutral-200/70 dark:border-neutral-800 hover:border-blue-200 dark:hover:border-blue-800 transition-all text-xs font-semibold text-neutral-800 dark:text-neutral-200 hover:text-blue-600 dark:hover:text-blue-400">
                          {{ $t('dashboard.ai_q_single_1', 'Pazar konumunu ve rekabet stratejisini analiz et') }}
                        </button>

                        <button @click="executePrompt('baskin_kategori')" class="w-full text-left p-2.5 rounded-xl bg-neutral-50/70 dark:bg-neutral-800/40 hover:bg-blue-50 dark:hover:bg-blue-900/30 border border-neutral-200/70 dark:border-neutral-800 hover:border-blue-200 dark:hover:border-blue-800 transition-all text-xs font-semibold text-neutral-800 dark:text-neutral-200 hover:text-blue-600 dark:hover:text-blue-400">
                          {{ $t('dashboard.ai_q_single_2', 'Baskın kategorideki ağırlığını ve büyüme fırsatlarını değerlendir') }}
                        </button>

                        <button @click="executePrompt('trend_analizi')" class="w-full text-left p-2.5 rounded-xl bg-neutral-50/70 dark:bg-neutral-800/40 hover:bg-blue-50 dark:hover:bg-blue-900/30 border border-neutral-200/70 dark:border-neutral-800 hover:border-blue-200 dark:hover:border-blue-800 transition-all text-xs font-semibold text-neutral-800 dark:text-neutral-200 hover:text-blue-600 dark:hover:text-blue-400">
                          {{ $t('dashboard.ai_q_single_3', 'Son 6 aylık lansman trendini ve kampanya sürelerini sektöre göre incele') }}
                        </button>
                      </template>

                      <!-- Çoklu Banka: 3 Soru -->
                      <template v-else>
                        <button @click="executePrompt('karsilastirma')" class="w-full text-left p-2.5 rounded-xl bg-neutral-50/70 dark:bg-neutral-800/40 hover:bg-blue-50 dark:hover:bg-blue-900/30 border border-neutral-200/70 dark:border-neutral-800 hover:border-blue-200 dark:hover:border-blue-800 transition-all text-xs font-semibold text-neutral-800 dark:text-neutral-200 hover:text-blue-600 dark:hover:text-blue-400">
                          {{ $t('dashboard.ai_q_multi_1', 'Seçili bankaların kampanya portföylerini ve pazar rekabetini karşılaştır') }}
                        </button>

                        <button @click="executePrompt('pazar_lideri')" class="w-full text-left p-2.5 rounded-xl bg-neutral-50/70 dark:bg-neutral-800/40 hover:bg-blue-50 dark:hover:bg-blue-900/30 border border-neutral-200/70 dark:border-neutral-800 hover:border-blue-200 dark:hover:border-blue-800 transition-all text-xs font-semibold text-neutral-800 dark:text-neutral-200 hover:text-blue-600 dark:hover:text-blue-400">
                          {{ $t('dashboard.ai_q_multi_2', 'Kampanya ivmesi ve çeşitlilik bakımından pazar lideri kimdir?') }}
                        </button>

                        <button @click="executePrompt('kategori_ayrisim')" class="w-full text-left p-2.5 rounded-xl bg-neutral-50/70 dark:bg-neutral-800/40 hover:bg-blue-50 dark:hover:bg-blue-900/30 border border-neutral-200/70 dark:border-neutral-800 hover:border-blue-200 dark:hover:border-blue-800 transition-all text-xs font-semibold text-neutral-800 dark:text-neutral-200 hover:text-blue-600 dark:hover:text-blue-400">
                          {{ $t('dashboard.ai_q_multi_3', 'Kategori bazında ortak ve ayrışan stratejileri analiz et') }}
                        </button>
                      </template>

                      <!-- Doğrulama geri bildirimi (analiz köprüsünden) -->
                      <div v-if="aiHata" class="p-2.5 rounded-xl bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800/50 text-[11px] font-semibold text-red-700 dark:text-red-300">
                        {{ aiHata }}
                      </div>
                      <div v-else-if="aiUyarilar.length" class="p-2.5 rounded-xl bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800/50 text-[11px] font-medium text-amber-800 dark:text-amber-300 space-y-1">
                        <div v-for="(u, i) in aiUyarilar" :key="i">• {{ u }}</div>
                      </div>
                      <div v-if="aiYukleniyor" class="text-[11px] font-semibold text-neutral-500 px-1">
                        {{ $t('dashboard.ai_verifying', 'Veriler doğrulanıyor...') }}
                      </div>

                      <!-- Soru Girme Yeri -->
                      <div class="pt-2 border-t border-neutral-100 dark:border-neutral-800">
                        <div class="flex items-center gap-1.5">
                          <input 
                            v-model="customPrompt" 
                            @keyup.enter="executePrompt('custom')" 
                            type="text" 
                            :placeholder="activeCompareBanks.length === 1 ? $t('dashboard.ai_placeholder_single', 'Bu banka hakkında soru yazın...') : $t('dashboard.ai_placeholder_multi', 'Seçili bankalar hakkında soru yazın...')" 
                            class="w-full text-xs px-3 py-2 rounded-xl border border-neutral-300 dark:border-neutral-700 bg-neutral-50/50 dark:bg-neutral-950 text-neutral-800 dark:text-neutral-200 outline-none focus:ring-2 focus:ring-blue-500 focus:bg-white dark:focus:bg-neutral-900 transition-all" 
                          />
                          <button 
                            @click="executePrompt('custom')" 
                            :disabled="!customPrompt.trim()" 
                            class="p-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-40 text-white rounded-xl transition-all shrink-0 active:scale-95 shadow-sm"
                            :title="$t('chat.send', 'Gönder')"
                          >
                            <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14 5l7 7m0 0l-7 7m7-7H3"/>
                            </svg>
                          </button>
                        </div>
                      </div>

                    </div>

                  </div>
                </Transition>
              </div>

              <!-- İndirme Butonları -->
              <div class="flex items-center gap-1.5" data-png-gizle>
                <button @click="exportChart('all-comparison', 'csv')" :title="$t('dashboard.export_all_excel', 'Tüm Analizi Excel Olarak İndir')" class="p-2 bg-green-50 dark:bg-green-900/20 text-green-600 dark:text-green-400 border border-green-200 dark:border-green-800/50 rounded-lg hover:bg-green-100 dark:hover:bg-green-900/40 transition-all shadow-sm hover:shadow active:scale-95 group">
                  <svg class="w-4 h-4 group-hover:-translate-y-0.5 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 10h18M3 14h18m-9-4v8m-7 0h14a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"></path></svg>
                </button>
                <button @click="exportChart('all-comparison', 'pdf')" :title="$t('dashboard.export_all_pdf', 'Tüm Analizi PDF Olarak İndir')" class="p-2 bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 border border-red-200 dark:border-red-800/50 rounded-lg hover:bg-red-100 dark:hover:bg-red-900/40 transition-all shadow-sm hover:shadow active:scale-95 group">
                  <svg class="w-4 h-4 group-hover:-translate-y-0.5 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path></svg>
                </button>
                <button @click="exportChart('all-comparison', 'png')" :title="$t('dashboard.export_all_png', 'Tüm Analizi PNG Olarak Kaydet')" class="p-2 bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400 border border-blue-200 dark:border-blue-800/50 rounded-lg hover:bg-blue-100 dark:hover:bg-blue-900/40 transition-all shadow-sm hover:shadow active:scale-95 group">
                  <svg class="w-4 h-4 group-hover:-translate-y-0.5 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"></path></svg>
                </button>
              </div>

              <!-- Seçimi Temizle -->
              <button v-if="selectedBanks.length > 0" @click="selectedBanks = []" class="text-sm font-bold text-neutral-400 hover:text-neutral-700 dark:hover:text-white transition-colors ml-1">
                {{ $t('dashboard.clear_selection', 'Seçimi Temizle') }}
              </button>
            </div>
          </div>
          
          <div class="p-6 md:p-8 space-y-8">
            
            <!-- Satır 1: Trend ve Radar -->
            <div class="grid grid-cols-1 lg:grid-cols-2 gap-8">
              <!-- Line Grafiği (Başlangıç Trendi) -->
              <div id="chart-box-lineChartRef" class="bg-white dark:bg-neutral-950 p-6 rounded-2xl border border-neutral-200 dark:border-neutral-800 shadow-sm transition-all duration-300 flex flex-col justify-between">
                <div class="flex justify-between items-center mb-1">
                  <h3 class="text-base font-bold text-neutral-900 dark:text-white">{{ $t('dashboard.trend_title', 'Kampanya Başlangıç Trendi') }} <span v-if="expandedCharts.line" class="text-blue-600 font-extrabold">({{ $t('dashboard.expanded_view', 'Genişletilmiş Görünüm') }})</span></h3>
                  
                  <div class="flex items-center gap-1.5" data-png-gizle>
                    <button @click="exportChart('lineChartRef', 'csv')" :title="$t('dashboard.export_excel', 'Excel Olarak İndir')" class="p-2 bg-green-50 dark:bg-green-900/20 text-green-600 dark:text-green-400 border border-green-200 dark:border-green-800/50 rounded-lg hover:bg-green-100 dark:hover:bg-green-900/40 transition-all shadow-sm hover:shadow active:scale-95 group">
                      <svg class="w-4 h-4 group-hover:-translate-y-0.5 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 10h18M3 14h18m-9-4v8m-7 0h14a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"></path></svg>
                    </button>
                    <button @click="exportChart('lineChartRef', 'pdf')" :title="$t('dashboard.export_pdf', 'PDF Raporu Oluştur')" class="p-2 bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 border border-red-200 dark:border-red-800/50 rounded-lg hover:bg-red-100 dark:hover:bg-red-900/40 transition-all shadow-sm hover:shadow active:scale-95 group">
                      <svg class="w-4 h-4 group-hover:-translate-y-0.5 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path></svg>
                    </button>
                    <button @click="exportChart('lineChartRef', 'png')" :title="$t('dashboard.export_png', 'PNG Olarak Kaydet')" class="p-2 bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400 border border-blue-200 dark:border-blue-800/50 rounded-lg hover:bg-blue-100 dark:hover:bg-blue-900/40 transition-all shadow-sm hover:shadow active:scale-95 group">
                      <svg class="w-4 h-4 group-hover:-translate-y-0.5 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"></path></svg>
                    </button>
                    <button @click="expandedCharts.line = !expandedCharts.line" class="outline-none ml-1">
                      <span class="text-xs font-bold px-3 py-2 rounded-lg transition-colors inline-block" :class="expandedCharts.line ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-400' : 'bg-neutral-100 text-neutral-600 hover:bg-neutral-200 dark:bg-neutral-800 dark:text-neutral-300 dark:hover:bg-neutral-700'">{{ expandedCharts.line ? $t('dashboard.collapse', 'Daralt') : $t('dashboard.detail', 'Detay') }}</span>
                    </button>
                  </div>
                </div>
                <p class="text-xs font-semibold text-neutral-500 mb-6">{{ $t('dashboard.trend_subtitle', 'Son 6 ayda başlayan yeni kampanya ivmesi') }}</p>
                <div @click="chartInteracts.radar = true" @mouseleave="chartInteracts.radar = false" class="relative transition-all duration-300 w-full" :class="(expandedCharts.line || expandedCharts.radar) ? 'h-[550px]' : 'h-64'">
                   <Line ref="lineChartRef" v-if="expandedCharts.line" :data="lineChartData" :options="lineOptions" />
                   <Line ref="lineChartRef" v-else :data="lineChartData" :options="lineOptions" />
                </div>
              </div>
              
              <!-- Radar Grafiği -->
              <div id="chart-box-radarChartRef" class="bg-white dark:bg-neutral-950 p-6 rounded-2xl border border-neutral-200 dark:border-neutral-800 shadow-sm transition-all duration-300 flex flex-col justify-between">
                <div class="flex justify-between items-center mb-1">
                  <h3 class="text-base font-bold text-neutral-900 dark:text-white">{{ $t('dashboard.distribution_title', 'Kampanya Dağılımı') }} <span v-if="expandedCharts.radar" class="text-blue-600 font-extrabold">({{ $t('dashboard.sub_breakdowns', 'Alt Kırılımlar') }})</span></h3>
                  
                  <div class="flex items-center gap-1.5" data-png-gizle>
                    <button @click="exportChart('radarChartRef', 'csv')" :title="$t('dashboard.export_excel', 'Excel Olarak İndir')" class="p-2 bg-green-50 dark:bg-green-900/20 text-green-600 dark:text-green-400 border border-green-200 dark:border-green-800/50 rounded-lg hover:bg-green-100 dark:hover:bg-green-900/40 transition-all shadow-sm hover:shadow active:scale-95 group">
                      <svg class="w-4 h-4 group-hover:-translate-y-0.5 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 10h18M3 14h18m-9-4v8m-7 0h14a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"></path></svg>
                    </button>
                    <button @click="exportChart('radarChartRef', 'pdf')" :title="$t('dashboard.export_pdf', 'PDF Raporu Oluştur')" class="p-2 bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 border border-red-200 dark:border-red-800/50 rounded-lg hover:bg-red-100 dark:hover:bg-red-900/40 transition-all shadow-sm hover:shadow active:scale-95 group">
                      <svg class="w-4 h-4 group-hover:-translate-y-0.5 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path></svg>
                    </button>
                    <button @click="exportChart('radarChartRef', 'png')" :title="$t('dashboard.export_png', 'PNG Olarak Kaydet')" class="p-2 bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400 border border-blue-200 dark:border-blue-800/50 rounded-lg hover:bg-blue-100 dark:hover:bg-blue-900/40 transition-all shadow-sm hover:shadow active:scale-95 group">
                      <svg class="w-4 h-4 group-hover:-translate-y-0.5 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"></path></svg>
                    </button>
                    <button @click="expandedCharts.radar = !expandedCharts.radar" class="outline-none ml-1">
                      <span class="text-xs font-bold px-3 py-2 rounded-lg transition-colors inline-block" :class="expandedCharts.radar ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-400' : 'bg-neutral-100 text-neutral-600 hover:bg-neutral-200 dark:bg-neutral-800 dark:text-neutral-300 dark:hover:bg-neutral-700'">{{ expandedCharts.radar ? $t('dashboard.collapse', 'Daralt') : $t('dashboard.detail', 'Detay') }}</span>
                    </button>
                  </div>
                </div>
                <p class="text-xs font-semibold text-neutral-500 mb-6">{{ $t('dashboard.distribution_subtitle', 'Banka vs Sektör Ortalaması - Çeşitlilik') }}</p>
                <div @click="chartInteracts.line = true" @mouseleave="chartInteracts.line = false" class="relative transition-all duration-300 flex items-center justify-center w-full" :class="(expandedCharts.line || expandedCharts.radar) ? 'h-[550px]' : 'h-64'">
                   <Radar ref="radarChartRef" v-if="expandedCharts.radar" :data="detailedRadarData" :options="detailedRadarOptions" />
                   <Radar ref="radarChartRef" v-else :data="radarChartData" :options="radarOptions" />
                </div>
              </div>
            </div>

            <!-- Satır 2: Ortalama Süre -->
            <div class="grid grid-cols-1 gap-8">
              <!-- Bar Grafiği -->
              <div id="chart-box-barChartRef" class="bg-white dark:bg-neutral-950 p-6 rounded-2xl border border-neutral-200 dark:border-neutral-800 shadow-sm transition-all duration-300 flex flex-col justify-between">
                <div class="flex justify-between items-center mb-1">
                  <h3 class="text-base font-bold text-neutral-900 dark:text-white">{{ $t('dashboard.duration_title', 'Ortalama Kampanya Süresi & Hedef Kitle') }} <span v-if="expandedCharts.duration" class="text-blue-600 font-extrabold">({{ $t('dashboard.sub_breakdowns', 'Alt Kırılımlar') }})</span></h3>
                  
                  <div class="flex items-center gap-1.5" data-png-gizle>
                    <button @click="exportChart('barChartRef', 'csv')" :title="$t('dashboard.export_excel', 'Excel Olarak İndir')" class="p-2 bg-green-50 dark:bg-green-900/20 text-green-600 dark:text-green-400 border border-green-200 dark:border-green-800/50 rounded-lg hover:bg-green-100 dark:hover:bg-green-900/40 transition-all shadow-sm hover:shadow active:scale-95 group">
                      <svg class="w-4 h-4 group-hover:-translate-y-0.5 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 10h18M3 14h18m-9-4v8m-7 0h14a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"></path></svg>
                    </button>
                    <button @click="exportChart('barChartRef', 'pdf')" :title="$t('dashboard.export_pdf', 'PDF Raporu Oluştur')" class="p-2 bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 border border-red-200 dark:border-red-800/50 rounded-lg hover:bg-red-100 dark:hover:bg-red-900/40 transition-all shadow-sm hover:shadow active:scale-95 group">
                      <svg class="w-4 h-4 group-hover:-translate-y-0.5 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path></svg>
                    </button>
                    <button @click="exportChart('barChartRef', 'png')" :title="$t('dashboard.export_png', 'PNG Olarak Kaydet')" class="p-2 bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400 border border-blue-200 dark:border-blue-800/50 rounded-lg hover:bg-blue-100 dark:hover:bg-blue-900/40 transition-all shadow-sm hover:shadow active:scale-95 group">
                      <svg class="w-4 h-4 group-hover:-translate-y-0.5 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"></path></svg>
                    </button>
                    <button @click="expandedCharts.duration = !expandedCharts.duration" class="outline-none ml-1">
                      <span class="text-xs font-bold px-3 py-2 rounded-lg transition-colors inline-block" :class="expandedCharts.duration ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-400' : 'bg-neutral-100 text-neutral-600 hover:bg-neutral-200 dark:bg-neutral-800 dark:text-neutral-300 dark:hover:bg-neutral-700'">{{ expandedCharts.duration ? $t('dashboard.collapse', 'Daralt') : $t('dashboard.detail', 'Detay') }}</span>
                    </button>
                  </div>
                </div>
                <p class="text-xs font-semibold text-neutral-500 mb-6">{{ $t('dashboard.duration_subtitle', 'Tür bazında kampanya yayın süresi dağılımı (ay)') }}</p>
                <div @click="chartInteracts.duration = true" @mouseleave="chartInteracts.duration = false" class="relative transition-all duration-300" :class="expandedCharts.duration ? 'h-[550px]' : 'h-80'">
                   <Bar ref="barChartRef" v-if="expandedCharts.duration" :data="detailedBarData" :options="detailedBarOptions" />
                   <Bar ref="barChartRef" v-else :data="durationBarChartData" :options="durationBarOptions" />
                </div>
              </div>
            </div>
            
            <!-- Satır 3: MGM Analizi (Eğer Varsa) -->
            <div v-if="mgmCampaigns.length > 0" class="bg-white dark:bg-neutral-950 rounded-2xl border border-neutral-200 dark:border-neutral-800 shadow-sm overflow-hidden">
              <div class="p-6 border-b border-neutral-100 dark:border-neutral-800">
                <h3 class="text-base font-bold text-neutral-900 dark:text-white mb-1">{{ $t('dashboard.highest_mgm', 'Yakınını Davet Et / MGM Analizi') }}</h3>
                <p class="text-xs font-semibold text-neutral-500">{{ $t('dashboard.mgm_subtitle', 'Üye getir üye kazan kampanyalarının karşılaştırması') }}</p>
              </div>
              <div class="overflow-x-auto">
                <table class="w-full text-sm text-left">
                  <thead>
                    <tr class="text-[11px] font-extrabold text-neutral-400 dark:text-neutral-500 uppercase tracking-widest bg-neutral-50/50 dark:bg-neutral-900/50 border-b border-neutral-100 dark:border-neutral-800">
                      <th class="py-4 px-6">{{ $t('comparison.columns.banka', 'Banka') }}</th>
                      <th class="py-4 px-6">{{ $t('comparison.columns.kampanya', 'Kampanya') }}</th>
                      <th class="py-4 px-6">{{ $t('comparison.columns.mgm', 'Davet Başına Kazanç') }}</th>
                      <th class="py-4 px-6">{{ $t('dashboard.highest_loan', 'Maksimum Limit') }}</th>
                      <th class="py-4 px-6">{{ $t('comparison.columns.hedefKitle', 'Şartlar') }}</th>
                    </tr>
                  </thead>
                  <tbody class="divide-y divide-neutral-100 dark:divide-neutral-800">
                    <tr v-for="c in mgmCampaigns" :key="c._id" class="hover:bg-blue-50/30 dark:hover:bg-blue-900/10">
                      <td class="py-4 px-6 font-bold flex items-center gap-3">
                        <img v-if="getBankaLogo(c.genel_bilgi?.banka_id)" :src="getBankaLogo(c.genel_bilgi?.banka_id)" class="w-6 h-6 object-contain" />
                        {{ getBankaAd(c.genel_bilgi?.banka_id) }}
                      </td>
                      <td class="py-4 px-6 font-semibold">{{ c.genel_bilgi?.kampanya_adi }}</td>
                      <td class="py-4 px-6 font-extrabold text-emerald-600 dark:text-emerald-400">{{ c.mgm_detay?.kisi_basi_kazanc ? c.mgm_detay.kisi_basi_kazanc + ' TL' : '-' }}</td>
                      <td class="py-4 px-6 font-medium text-neutral-600 dark:text-neutral-300">{{ c.mgm_detay?.mgm_limit_tl ? c.mgm_detay.mgm_limit_tl + ' TL' : ($t('dashboard.unlimited', 'Sınırsız')) }}</td>
                      <td class="py-4 px-6 font-medium text-neutral-500 text-xs">{{ c.genel_bilgi?.hedef_kitle?.join(', ') || '-' }}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>

          </div>
        </div>

      </div>
    </template>
  
    <!-- Kampanya Detay Yan Panel (Teleport to Body) -->
    <Teleport to="body">
      <!-- Kampanya Detay Yan Panel (chat.vue tarzı) -->
    <Transition 
      enter-active-class="transform transition-all duration-500 ease-[cubic-bezier(0.2,0.8,0.2,1)]" 
      enter-from-class="translate-x-[120%] opacity-0 scale-95" 
      enter-to-class="translate-x-0 opacity-100 scale-100" 
      leave-active-class="transform transition-all duration-300 ease-in" 
      leave-from-class="translate-x-0 opacity-100 scale-100" 
      leave-to-class="translate-x-[120%] opacity-0 scale-95"
    >
      <div v-if="selectedModalCampaign" class="fixed right-4 top-4 bottom-4 w-[340px] sm:w-[420px] lg:w-[480px] bg-white dark:bg-[#121212] rounded-[24px] shadow-[0_12px_40px_rgba(0,0,0,0.15)] dark:shadow-[0_12px_40px_rgba(0,0,0,0.7)] border border-neutral-200 dark:border-neutral-700 flex flex-col z-[100] overflow-hidden">
        
        <!-- Header -->
        <div class="flex justify-between items-center p-4 border-b border-neutral-200 dark:border-neutral-700 bg-neutral-50 dark:bg-neutral-800">
          <h3 class="text-[14px] font-bold flex items-center gap-2 text-neutral-800 dark:text-white">
            <svg class="w-4 h-4 text-emerald-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4"></path></svg>
            {{ $t('chat.campaign_detail', 'Kampanya Detayları') }}
          </h3>
          <div class="flex items-center gap-2">
            <button @click="selectedModalCampaign = null" class="p-1 text-neutral-500 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/30 rounded transition-colors active:scale-90 transform duration-200" :title="$t('chat.close', 'Kapat')">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg>
            </button>
          </div>
        </div>
        
        <!-- Body -->
        <div class="flex-1 overflow-y-auto p-4 lg:p-6 custom-scrollbar space-y-4">
          
          <!-- Kaynak Link (chat.vue gibi) -->
          <a v-if="hasValue(selectedModalCampaign.genel_bilgi?.kaynak_url)" 
             :href="selectedModalCampaign.genel_bilgi.kaynak_url" target="_blank" rel="noopener noreferrer"
             class="flex items-center gap-2 px-3 py-2.5 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800/50 rounded-xl text-sm font-semibold text-blue-600 dark:text-blue-400 hover:bg-blue-100 dark:hover:bg-blue-900/40 transition-colors w-fit">
            <svg class="w-4 h-4 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"></path></svg>
            {{ $t('chat.visit_source', 'Kaynak sayfaya git') }}
          </a>
          
          <!-- Banka & Kampanya Adı -->
          <div class="border-b border-neutral-100 dark:border-neutral-800 pb-3">
            <div v-if="hasValue(selectedModalCampaign.genel_bilgi?.banka_id)" class="text-xs font-bold text-indigo-500 dark:text-indigo-400 uppercase tracking-wider mb-1">{{ selectedModalCampaign.genel_bilgi?.banka_id }}</div>
            <h2 class="text-lg font-black text-neutral-900 dark:text-white leading-snug">{{ selectedModalCampaign.genel_bilgi?.kampanya_adi }}</h2>
          </div>
          
          <!-- SADECE OLAN METRİKLER DİZİLİYOR -->
          <div class="grid grid-cols-2 gap-2.5">
            <!-- Tür -->
            <div v-if="hasValue(selectedModalCampaign.genel_bilgi?.kampanya_turu)" class="bg-neutral-50 dark:bg-neutral-800/50 p-3 rounded-xl border border-neutral-100 dark:border-neutral-800">
              <div class="text-[10px] font-bold text-neutral-400 uppercase tracking-wider mb-0.5">{{ $t('comparison.columns.tur', 'Tür') }}</div>
              <div class="text-xs font-semibold text-neutral-800 dark:text-neutral-200 truncate">{{ selectedModalCampaign.genel_bilgi?.kampanya_turu }}</div>
            </div>

            <!-- Kategori -->
            <div v-if="hasValue(selectedModalCampaign.genel_bilgi?.kategori)" class="bg-neutral-50 dark:bg-neutral-800/50 p-3 rounded-xl border border-neutral-100 dark:border-neutral-800">
              <div class="text-[10px] font-bold text-neutral-400 uppercase tracking-wider mb-0.5">{{ $t('comparison.columns.kategori', 'Kategori') }}</div>
              <div class="text-xs font-semibold text-neutral-800 dark:text-neutral-200 truncate">{{ selectedModalCampaign.genel_bilgi?.kategori }}</div>
            </div>

            <!-- Kâr Payı -->
            <div v-if="hasValue(selectedModalCampaign.finansman_detay?.kar_payi_orani)" class="bg-neutral-50 dark:bg-neutral-800/50 p-3 rounded-xl border border-neutral-100 dark:border-neutral-800">
              <div class="text-[10px] font-bold text-neutral-400 uppercase tracking-wider mb-0.5">{{ $t('comparison.columns.karPayi', 'Kâr Payı') }}</div>
              <div class="text-xs font-bold text-blue-600 dark:text-blue-400">%{{ selectedModalCampaign.finansman_detay?.kar_payi_orani }}</div>
            </div>

            <!-- Vade -->
            <div v-if="hasValue(selectedModalCampaign.finansman_detay?.vade_ay)" class="bg-neutral-50 dark:bg-neutral-800/50 p-3 rounded-xl border border-neutral-100 dark:border-neutral-800">
              <div class="text-[10px] font-bold text-neutral-400 uppercase tracking-wider mb-0.5">{{ $t('campaigns.columns.vade', 'Vade') }}</div>
              <div class="text-xs font-bold text-indigo-600 dark:text-indigo-400">{{ selectedModalCampaign.finansman_detay?.vade_ay }} {{ $t('financing.term_months', 'Ay') }}</div>
            </div>

            <!-- Taksit -->
            <div v-if="hasValue(selectedModalCampaign.finansman_detay?.taksit)" class="bg-neutral-50 dark:bg-neutral-800/50 p-3 rounded-xl border border-neutral-100 dark:border-neutral-800">
              <div class="text-[10px] font-bold text-neutral-400 uppercase tracking-wider mb-0.5">{{ $t('comparison.columns.taksit', 'Taksit') }}</div>
              <div class="text-xs font-semibold text-neutral-800 dark:text-neutral-200">{{ selectedModalCampaign.finansman_detay?.taksit }}</div>
            </div>

            <!-- Tahsis Ücreti -->
            <div v-if="hasValue(selectedModalCampaign.finansman_detay?.tahsis_ucreti)" class="bg-neutral-50 dark:bg-neutral-800/50 p-3 rounded-xl border border-neutral-100 dark:border-neutral-800">
              <div class="text-[10px] font-bold text-neutral-400 uppercase tracking-wider mb-0.5">{{ $t('comparison.columns.tahsisUcreti', 'Tahsis Ücreti') }}</div>
              <div class="text-xs font-bold text-orange-600 dark:text-orange-400">{{ Number(selectedModalCampaign.finansman_detay?.tahsis_ucreti).toLocaleString('tr-TR') }} ₺</div>
            </div>

            <!-- Finansman Tutarı -->
            <div v-if="hasValue(selectedModalCampaign.finansman_detay?.finansman_tutari)" class="bg-neutral-50 dark:bg-neutral-800/50 p-3 rounded-xl border border-neutral-100 dark:border-neutral-800">
              <div class="text-[10px] font-bold text-neutral-400 uppercase tracking-wider mb-0.5">{{ $t('comparison.columns.finansmanTutari', 'Finansman Tutarı') }}</div>
              <div class="text-xs font-bold text-cyan-600 dark:text-cyan-400">{{ Number(selectedModalCampaign.finansman_detay?.finansman_tutari).toLocaleString('tr-TR') }} ₺</div>
            </div>

            <!-- Ödül -->
            <div v-if="hasValue(selectedModalCampaign.promosyon_detay?.odul_tutari)" class="bg-neutral-50 dark:bg-neutral-800/50 p-3 rounded-xl border border-neutral-100 dark:border-neutral-800">
              <div class="text-[10px] font-bold text-neutral-400 uppercase tracking-wider mb-0.5">{{ $t('comparison.columns.odul', 'Ödül') }}</div>
              <div class="text-xs font-bold text-emerald-600 dark:text-emerald-400">{{ Number(selectedModalCampaign.promosyon_detay?.odul_tutari).toLocaleString('tr-TR') }} ₺</div>
            </div>

            <!-- Ödül Tipi -->
            <div v-if="hasValue(selectedModalCampaign.promosyon_detay?.odul_tip)" class="bg-neutral-50 dark:bg-neutral-800/50 p-3 rounded-xl border border-neutral-100 dark:border-neutral-800">
              <div class="text-[10px] font-bold text-neutral-400 uppercase tracking-wider mb-0.5">{{ $t('comparison.columns.odul', 'Ödül Tipi') }}</div>
              <div class="text-xs font-semibold text-neutral-800 dark:text-neutral-200 truncate">{{ selectedModalCampaign.promosyon_detay?.odul_tip }}</div>
            </div>

            <!-- Nakit İade -->
            <div v-if="hasValue(selectedModalCampaign.promosyon_detay?.nakit_iade_yuzde)" class="bg-neutral-50 dark:bg-neutral-800/50 p-3 rounded-xl border border-neutral-100 dark:border-neutral-800">
              <div class="text-[10px] font-bold text-neutral-400 uppercase tracking-wider mb-0.5">{{ $t('dashboard.highest_cashback', 'Nakit İade') }}</div>
              <div class="text-xs font-bold text-pink-600 dark:text-pink-400">%{{ selectedModalCampaign.promosyon_detay?.nakit_iade_yuzde }}</div>
            </div>

            <!-- MGM Kazanç -->
            <div v-if="hasValue(selectedModalCampaign.mgm_detay?.kisi_basi_kazanc)" class="bg-neutral-50 dark:bg-neutral-800/50 p-3 rounded-xl border border-neutral-100 dark:border-neutral-800">
              <div class="text-[10px] font-bold text-neutral-400 uppercase tracking-wider mb-0.5">{{ $t('comparison.columns.mgm', 'MGM Kazanç') }}</div>
              <div class="text-xs font-bold text-purple-600 dark:text-purple-400">{{ Number(selectedModalCampaign.mgm_detay?.kisi_basi_kazanc).toLocaleString('tr-TR') }} ₺</div>
            </div>

            <!-- Bitiş Tarihi -->
            <div v-if="hasValue(selectedModalCampaign.genel_bilgi?.bitis_tarihi)" class="bg-neutral-50 dark:bg-neutral-800/50 p-3 rounded-xl border border-neutral-100 dark:border-neutral-800">
              <div class="text-[10px] font-bold text-neutral-400 uppercase tracking-wider mb-0.5">{{ $t('campaigns.columns.bitisTarihi', 'Bitiş Tarihi') }}</div>
              <div class="text-xs font-semibold text-neutral-800 dark:text-neutral-200">{{ formatTarih(selectedModalCampaign.genel_bilgi?.bitis_tarihi) }}</div>
            </div>
          </div>

          <!-- Hedef Kitle -->
          <div v-if="hasValue(selectedModalCampaign.genel_bilgi?.hedef_kitle)" class="bg-neutral-50 dark:bg-neutral-800/50 p-3 rounded-xl border border-neutral-100 dark:border-neutral-800">
            <div class="text-[10px] font-bold text-neutral-400 uppercase tracking-wider mb-1">{{ $t('comparison.columns.hedefKitle', 'Hedef Kitle') }}</div>
            <div class="text-xs font-medium text-neutral-700 dark:text-neutral-300">
              {{ Array.isArray(selectedModalCampaign.genel_bilgi.hedef_kitle) ? selectedModalCampaign.genel_bilgi.hedef_kitle.join(', ') : selectedModalCampaign.genel_bilgi.hedef_kitle }}
            </div>
          </div>

          <!-- Masraf Bilgisi -->
          <div v-if="hasValue(selectedModalCampaign.finansman_detay?.masraf_bilgi)" class="bg-neutral-50 dark:bg-neutral-800/50 p-3 rounded-xl border border-neutral-100 dark:border-neutral-800">
            <div class="text-[10px] font-bold text-neutral-400 uppercase tracking-wider mb-1">{{ $t('comparison.columns.masrafBilgisi', 'Masraf Bilgisi') }}</div>
            <div class="text-xs font-medium text-neutral-700 dark:text-neutral-300">{{ selectedModalCampaign.finansman_detay.masraf_bilgi }}</div>
          </div>

          <!-- Kampanya Metni (chat.vue pre formatında) -->
          <div v-if="hasValue(selectedModalCampaign.genel_bilgi?.metin || selectedModalCampaign.metin || selectedModalCampaign.ham_metin)" class="pt-3 border-t border-neutral-200 dark:border-neutral-800">
            <div class="text-[10px] font-bold text-neutral-400 uppercase tracking-wider mb-2">{{ $t('comparison.columns.kampanyaMetni', 'Kampanya Metni') }}</div>
            <pre class="font-mono text-xs whitespace-pre-wrap leading-relaxed text-neutral-600 dark:text-neutral-300 break-words bg-neutral-50 dark:bg-neutral-900/80 p-3.5 rounded-xl border border-neutral-200/80 dark:border-neutral-800 max-h-72 overflow-y-auto custom-scrollbar">{{ selectedModalCampaign.genel_bilgi?.metin || selectedModalCampaign.metin || selectedModalCampaign.ham_metin }}</pre>
          </div>
        </div>
      </div>
    </Transition>
    </Teleport>
</div>
</template>

<style scoped>
.pro-dashboard {
  font-family: 'Plus Jakarta Sans', system-ui, -apple-system, sans-serif;
}
.animate-fade-in { animation: fadeIn 0.5s cubic-bezier(0.4, 0, 0.2, 1); }
@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

.gradient-text {
  background-image: linear-gradient(90deg, #2563eb, #06b6d4, #6366f1, #2563eb);
  background-size: 300% 100%;
  animation: gradShift 7s ease infinite;
}
@keyframes gradShift { 0% { background-position: 0% 50%; } 50% { background-position: 100% 50%; } 100% { background-position: 0% 50%; } }

.reveal-title { animation: titleIn 0.8s cubic-bezier(0.22,1,0.36,1) both; }
@keyframes titleIn { from { opacity: 0; transform: translateY(16px); letter-spacing: 0.08em; } to { opacity: 1; transform: translateY(0); letter-spacing: 0; } }
.title-underline { animation: underlineGrow 0.9s ease 0.3s both; transform-origin: center; }
@keyframes underlineGrow { from { transform: scaleX(0); opacity: 0; } to { transform: scaleX(1); opacity: 1; } }
</style>
