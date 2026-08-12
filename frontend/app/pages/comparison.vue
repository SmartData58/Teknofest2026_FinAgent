<template>
  <div class="p-6 md:p-8 space-y-12 w-full max-w-[1400px] mx-auto min-h-full">

    <!-- BAŞLIK -->
    <div class="flex flex-col items-center text-center gap-3 max-w-2xl mx-auto">
      <h1 class="reveal-title text-4xl md:text-5xl font-bold bg-clip-text text-transparent gradient-text pb-1">
        {{ $t('comparison.title', 'Karşılaştırma') }}
      </h1>
      <p class="text-sm md:text-base text-neutral-500 dark:text-neutral-400">
        Şartnamedeki kriterlere göre kampanya kıyası. Bir alan 'Belirtilmemiş' ise o kampanya ilgili kritere dahil edilmez.
      </p>
      <div class="h-1 w-24 rounded-full bg-gradient-to-r from-blue-500 to-cyan-400 mt-1 title-underline"></div>
    </div>

    <!-- KRİTER SEKSİYONLARI -->
    <div v-for="(criterion, index) in criteriaConfig" :key="index" class="reveal-on-scroll space-y-4">

      <!-- Kriter Başlığı -->
      <h2 class="text-xl font-bold text-neutral-800 dark:text-neutral-100 border-b border-neutral-200 dark:border-neutral-700 pb-2 flex items-center gap-2">
        <span class="inline-block w-1.5 h-5 rounded-full bg-gradient-to-b from-blue-500 to-cyan-400"></span>
        {{ criterion.title }}
      </h2>

      <!-- Skeleton Yükleniyor Ekranı -->
      <div v-if="pending" class="bg-white/80 dark:bg-neutral-800/50 backdrop-blur-md border border-neutral-200/50 dark:border-neutral-700/50 rounded-xl overflow-hidden">
        <div class="p-4 border-b border-neutral-200/50 dark:border-neutral-700/50 flex gap-4">
          <div v-for="i in 4" :key="i" class="h-4 bg-neutral-200 dark:bg-neutral-700 rounded w-24 shimmer"></div>
        </div>
        <div class="p-4 space-y-4">
          <div v-for="i in 3" :key="`row-${i}`" class="h-6 bg-neutral-200 dark:bg-neutral-700 rounded w-full shimmer"></div>
        </div>
      </div>

      <!-- Gerçek Tablo ve Öne Çıkan -->
      <div v-else>
        <div v-if="getSortedData(criterion).length === 0" class="p-6 bg-neutral-50/50 dark:bg-neutral-900/30 border border-dashed border-neutral-300 dark:border-neutral-700 rounded-xl text-center text-sm text-neutral-500">
          Bu kriter için veritabanında uygun kampanya bulunamadı.
        </div>

        <div v-else class="space-y-4">
          <!-- Scroll Kutusu -->
          <div class="bg-white/80 dark:bg-neutral-800/50 backdrop-blur-md border border-neutral-200/50 dark:border-neutral-700/50 rounded-xl shadow-sm overflow-hidden relative">
            <div class="overflow-x-auto overflow-y-auto max-h-[320px] custom-scrollbar" data-lenis-prevent="true">
              <table class="w-full text-left border-collapse whitespace-nowrap min-w-max relative">
                <!-- Sticky Thead -->
                <thead class="sticky top-0 z-20 bg-neutral-100/95 dark:bg-neutral-900/95 backdrop-blur-md shadow-sm after:absolute after:inset-x-0 after:bottom-0 after:border-b after:border-neutral-200/50 dark:after:border-neutral-700/50">
                  <tr class="text-xs uppercase text-neutral-500 dark:text-neutral-400">
                    <th v-for="col in criterion.columns" :key="col.key" class="p-4 font-semibold">
                      {{ col.label }}
                    </th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-neutral-200/50 dark:divide-neutral-700/50 text-sm">
                  <!-- Tablo Verileri -->
                  <tr v-for="(row, ri) in getSortedData(criterion)" :key="row.id"
                      class="hover:bg-cyan-50/40 dark:hover:bg-cyan-900/10 transition-colors"
                      :class="ri === 0 ? 'bg-blue-50/40 dark:bg-cyan-900/10' : ''">
                    <td v-for="col in criterion.columns" :key="col.key" class="p-4 text-neutral-700 dark:text-neutral-300">
                      <span class="inline-flex items-center gap-2">
                        <span v-if="ri === 0 && col.key === 'banka'" class="text-[10px] font-bold px-1.5 py-0.5 rounded bg-gradient-to-r from-blue-500 to-cyan-400 text-white">1</span>
                        <span :class="{'font-medium text-neutral-900 dark:text-neutral-100': col.key === 'banka'}">
                          {{ col.key === 'baslik' && row[col.key] && row[col.key].length > 60 ? row[col.key].substring(0, 60) + '...' : (row[col.key] ?? '-') }}
                        </span>
                      </span>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          <!-- Öne Çıkan (Şampiyon) Kutusu -->
          <div class="inline-flex items-center gap-2 px-4 py-3 bg-blue-50/50 dark:bg-cyan-900/20 border border-blue-200/50 dark:border-cyan-800/50 rounded-lg text-sm text-neutral-700 dark:text-neutral-300">
            <span class="font-bold text-blue-600 dark:text-cyan-400">En Avantajlı:</span>
            <span>
              <strong class="text-neutral-900 dark:text-white">{{ getTopItem(criterion).banka }}</strong> —
              {{ getTopItem(criterion).baslik }}
              <span class="opacity-75 font-semibold text-blue-600 dark:text-blue-400 ml-1">
                ({{ getMetricLabel(criterion.sortKey) }}: {{ getTopItem(criterion)[criterion.sortKey] }})
              </span>
            </span>
          </div>
        </div>
      </div>
    </div>

    <!-- YASAL UYARI FOOTER -->
    <div class="reveal-on-scroll mt-8 p-5 border-l-4 border-neutral-300 dark:border-neutral-600 bg-neutral-100/50 dark:bg-neutral-800/30 text-xs sm:text-sm text-neutral-500 dark:text-neutral-400 italic rounded-r-lg">
      Bu bilgiler yatırım tavsiyesi değildir. Karşılaştırmalar yalnızca metinlerden otomatik çıkarılan alanlara dayanır; kampanya koşullarının tamamı için bankaların resmî sayfaları esastır.
    </div>

  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
import Lenis from 'lenis'

const pending = ref(true)
const campaigns = ref([])

let lenis = null
let lenisRafId = null
let observer = null

// --- DİNAMİK YAPILANDIRMA ---
const criteriaConfig = [
  {
    id: 'lowest_profit',
    title: 'En Düşük Kâr Payı Oranı',
    sortKey: 'karPayi',
    sortAsc: true, // Kâr payında düşük olan iyidir
    columns: [
      { key: 'banka', label: 'Banka' },
      { key: 'baslik', label: 'Kampanya' },
      { key: 'karPayi', label: 'Kâr Payı (%)' },
      { key: 'vade', label: 'Vade (ay)' },
      { key: 'hedefKitle', label: 'Hedef Kitle' }
    ]
  },
  {
    id: 'highest_reward',
    title: 'En Yüksek Ödül Miktarı',
    sortKey: 'odul',
    sortAsc: false, // Ödülde yüksek olan iyidir
    columns: [
      { key: 'banka', label: 'Banka' },
      { key: 'baslik', label: 'Kampanya' },
      { key: 'odul', label: 'Ödül (TL)' },
      { key: 'bitisTarihi', label: 'Bitiş Tarihi' },
      { key: 'hedefKitle', label: 'Hedef Kitle' }
    ]
  },
  {
    id: 'longest_term',
    title: 'En Uzun Vade',
    sortKey: 'vade',
    sortAsc: false, // Vadede uzun olan iyidir (finansman için genelde böyle istenir)
    columns: [
      { key: 'banka', label: 'Banka' },
      { key: 'baslik', label: 'Kampanya' },
      { key: 'vade', label: 'Vade (ay)' },
      { key: 'karPayi', label: 'Kâr Payı (%)' },
      { key: 'hedefKitle', label: 'Hedef Kitle' }
    ]
  },
  {
    id: 'lowest_fee',
    title: 'En Düşük Tahsis Ücreti',
    sortKey: 'tahsisUcreti',
    sortAsc: true, // Ücrette düşük olan iyidir
    columns: [
      { key: 'banka', label: 'Banka' },
      { key: 'baslik', label: 'Kampanya' },
      { key: 'tahsisUcreti', label: 'Tahsis Ücreti (TL)' },
      { key: 'karPayi', label: 'Kâr Payı (%)' },
      { key: 'vade', label: 'Vade (ay)' }
    ]
  }
]

const getMetricLabel = (key) => {
  const labels = {
    'karPayi': 'Kâr Payı (%)',
    'odul': 'Ödül (TL)',
    'vade': 'Vade (ay)',
    'tahsisUcreti': 'Tahsis Ücreti (TL)'
  }
  return labels[key] || key
}

// 0'ı Silme Mantığı Düzeltildi + Veri Dönüşümleri Geliştirildi
const getSortedData = (criterion) => {
  const validData = campaigns.value.filter(c => {
    let val = c[criterion.sortKey]
    
    // Değer boş mu? null mu? undefined mı? 'None' (metin olarak) mi?
    if (val === null || val === undefined || val === '' || String(val).trim().toLowerCase() === 'none') {
      return false
    }

    // Virgüllü sayıları noktaya çevir (1,99 -> 1.99) hesaplama hatasını engellemek için
    if (typeof val === 'string') {
        val = val.replace(',', '.')
    }

    const floatVal = parseFloat(val)
    if (isNaN(floatVal)) return false
    
    // Eğer Vade veya Ödül 0 ise bunları ele. 
    if ((criterion.sortKey === 'vade' || criterion.sortKey === 'odul') && floatVal <= 0) {
      return false
    }

    // Kar Payı ve Tahsis ücretinde < 0 (eksi değer) olamaz, onları ele
    if ((criterion.sortKey === 'karPayi' || criterion.sortKey === 'tahsisUcreti') && floatVal < 0) {
      return false
    }

    return true
  })
  
  // Sıralama Algoritması
  const sorted = validData.sort((a, b) => {
    let valA = parseFloat(String(a[criterion.sortKey]).replace(',', '.')) || 0
    let valB = parseFloat(String(b[criterion.sortKey]).replace(',', '.')) || 0
    return criterion.sortAsc ? (valA - valB) : (valB - valA)
  })
  
  return sorted
}

const getTopItem = (criterion) => {
  const sorted = getSortedData(criterion)
  return sorted.length > 0 ? sorted[0] : {}
}

const setupObserver = (scrollerEl) => {
  observer = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        entry.target.classList.add('is-visible')
        observer.unobserve(entry.target)
      }
    })
  }, { root: scrollerEl || null, threshold: 0.12, rootMargin: '0px 0px -8% 0px' })

  document.querySelectorAll('.reveal-on-scroll').forEach(el => observer.observe(el))
}

const fetchCampaigns = async () => {
  try {
    const response = await fetch('http://localhost:8003/campaigns?limit=500&sadece_gecerli=false')
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }
    
    const data = await response.json()
    
    // 🚀 İŞTE BÜTÜN HATANIN KAYNAĞI BURASIYDI! 
    // API'den gelen kar_payi_orani ve vade_ay isimleri burada eksikti, şimdi %100 düzeltildi.
    campaigns.value = data.map(c => ({
      id: c.id || c.kampanya_id,
      banka: c.banka || c.banka_adi,
      baslik: c.baslik || c.kampanya_adi,
      karPayi: c.kar_payi_orani !== undefined ? c.kar_payi_orani : c.kar_payi,
      vade: c.vade_ay !== undefined ? c.vade_ay : c.maksimum_vade,
      tahsisUcreti: c.tahsis_ucreti,
      odul: c.odul_miktari,
      bitisTarihi: c.bitis_tarihi || c.son_gecerlilik_tarihi || '-',
      hedefKitle: c.hedef_kitle || c.hedefKitle || 'Belirtilmemiş'
    }))

  } catch (error) {
    console.error('Kampanya verileri çekilirken hata oluştu:', error)
    campaigns.value = []
  } finally {
    pending.value = false
    nextTick(() => {
      setupObserver(document.getElementById('main-scroller'))
    })
  }
}

onMounted(() => {
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
    const raf = (time) => { lenis.raf(time); lenisRafId = requestAnimationFrame(raf) }
    lenisRafId = requestAnimationFrame(raf)
  }

  fetchCampaigns()
})

onUnmounted(() => {
  if (lenisRafId) cancelAnimationFrame(lenisRafId)
  if (lenis) { lenis.destroy(); lenis = null }
  if (observer) { observer.disconnect(); observer = null }
})
</script>

<style scoped>
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

.reveal-on-scroll {
  opacity: 0;
  transform: translateY(28px);
  transition: opacity 0.6s cubic-bezier(0.22,1,0.36,1), transform 0.6s cubic-bezier(0.22,1,0.36,1);
}
.reveal-on-scroll.is-visible { opacity: 1; transform: none; }

.row-reveal {
  opacity: 0;
  transform: translateY(12px);
  transition: opacity 0.5s ease, transform 0.5s ease;
}
.reveal-on-scroll.is-visible .row-reveal { opacity: 1; transform: none; }

.shimmer { position: relative; overflow: hidden; }
.shimmer::after {
  content: ''; position: absolute; inset: 0; transform: translateX(-100%);
  background: linear-gradient(90deg, transparent, rgba(255,255,255,0.25), transparent);
  animation: shimmer 1.4s infinite;
}
@keyframes shimmer { 100% { transform: translateX(100%); } }

.custom-scrollbar::-webkit-scrollbar { width: 6px; height: 6px; }
.custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
.custom-scrollbar::-webkit-scrollbar-thumb { background: #cbd5e1; border-radius: 10px; }
:global(.dark) .custom-scrollbar::-webkit-scrollbar-thumb { background: #475569; }
.custom-scrollbar::-webkit-scrollbar-thumb:hover { background: #94a3b8; }
</style>