<template>
  <div class="relative w-full min-h-full overflow-hidden">
    <!-- SAYFA ZEMİNİ -->
    <div class="fixed inset-0 -z-20 bg-neutral-50 dark:bg-neutral-950 pointer-events-none"></div>

    <!-- ================= ANİMASYONLU ARKA PLAN ================= -->
    <div class="pointer-events-none absolute inset-0 -z-0 overflow-hidden">
      <div class="bg-blob blob-1"></div>
      <div class="bg-blob blob-2"></div>
      <div class="bg-blob blob-3"></div>
      <div class="bg-grid"></div>
    </div>

    <!-- ================= İÇERİK ================= -->
    <div class="relative z-10 p-6 md:p-8 space-y-10 w-full max-w-[1400px] mx-auto">

      <!-- ORTALANMIŞ BAŞLIK -->
      <div class="flex flex-col items-center text-center gap-3 pt-2">
        <h1 class="reveal-title text-4xl md:text-5xl font-bold bg-clip-text text-transparent gradient-text pb-1">
          {{ $t('dashboard.title', 'Sistem Özeti') }}
        </h1>
        <p class="text-sm md:text-base text-neutral-500 dark:text-neutral-400 max-w-xl">
          Katılım Bankacılığı Yapay Zeka Ajanı Analiz Paneli
        </p>
        <div class="h-1 w-24 rounded-full bg-gradient-to-r from-blue-500 to-cyan-400 mt-1 title-underline"></div>
      </div>

      <!-- METRİK KARTLARI (TAMAMEN DİNAMİK) -->
      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">

        <template v-if="pending">
          <div v-for="i in 4" :key="`skel-metric-${i}`" class="p-6 bg-white/60 dark:bg-neutral-800/40 backdrop-blur-md border border-neutral-200/50 dark:border-neutral-700/50 rounded-2xl shadow-sm flex flex-col gap-3 relative overflow-hidden">
            <div class="shimmer h-4 bg-neutral-200/80 dark:bg-neutral-700/80 rounded-md w-3/4"></div>
            <div class="shimmer h-10 bg-neutral-300/80 dark:bg-neutral-600/80 rounded-md w-1/3 mt-auto"></div>
          </div>
        </template>

        <template v-else>
          <div
            v-for="(metric, index) in metrics"
            :key="index"
            :style="{ transitionDelay: `${index * 90}ms` }"
            :class="revealed ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-6'"
            class="metric-card group relative p-6 bg-white/80 dark:bg-neutral-800/60 backdrop-blur-md border border-neutral-200/50 dark:border-neutral-700/50 rounded-2xl shadow-sm hover:shadow-xl hover:-translate-y-1.5 hover:border-blue-300/60 dark:hover:border-blue-700/60 transition-all duration-500 overflow-hidden"
          >
            <div class="absolute -top-16 -right-16 w-40 h-40 rounded-full bg-cyan-400/0 group-hover:bg-cyan-400/20 blur-3xl transition-colors duration-500 pointer-events-none"></div>

            <div class="flex items-start justify-between relative z-10">
              <h3 class="text-sm font-medium text-neutral-500 dark:text-neutral-400 pr-2">{{ metric.title }}</h3>
              <span class="flex-shrink-0 w-9 h-9 rounded-xl flex items-center justify-center text-blue-600 dark:text-cyan-300 bg-blue-50 dark:bg-blue-900/30 group-hover:scale-110 group-hover:rotate-6 transition-transform duration-300" v-html="metric.icon"></span>
            </div>

            <p class="text-4xl font-bold text-blue-600 dark:text-cyan-400 mt-3 tabular-nums relative z-10">
              {{ display[index].toLocaleString('tr-TR') }}
            </p>

            <p class="text-xs mt-2 font-medium relative z-10" :class="metric.trendUp ? 'text-emerald-500' : 'text-neutral-400'">
              <span v-if="metric.trend">{{ metric.trend }}</span>
            </p>
          </div>
        </template>
      </div>

      <!-- ÇIKARIM KAPSAMASI: TAM GENİŞLİK ANİMASYONLU BAR GRAFİK -->
      <div class="reveal-on-scroll p-6 md:p-8 bg-white/80 dark:bg-neutral-800/60 backdrop-blur-md border border-neutral-200/50 dark:border-neutral-700/50 rounded-2xl shadow-sm">
        <div class="flex items-center justify-between mb-1">
          <h2 class="text-lg font-bold text-neutral-800 dark:text-neutral-100">{{ $t('dashboard.coverage', 'Alan Bazlı Çıkarım Dağılımı') }}</h2>
          <span class="text-xs font-semibold text-blue-600 dark:text-cyan-400 bg-blue-50 dark:bg-blue-900/30 px-2.5 py-1 rounded-full">Gerçek Zamanlı AI Çıkarımı</span>
        </div>
        <p class="text-sm text-neutral-500 dark:text-neutral-400 mb-6">Veritabanındaki kampanyalardan başarıyla çıkarılan özelliklerin sayısı.</p>

        <div v-if="pending" class="space-y-4 mt-4">
          <div v-for="i in 7" :key="`skel-bar-${i}`" class="flex items-center gap-4">
            <div class="shimmer h-4 bg-neutral-200 dark:bg-neutral-700 rounded-md w-28 sm:w-36"></div>
            <div class="shimmer h-7 bg-blue-100/50 dark:bg-cyan-900/30 rounded-md flex-1" :style="`max-width: ${110 - i * 8}%`"></div>
          </div>
        </div>

        <div v-else class="space-y-3 mt-2">
          <div v-for="(item, i) in fieldCounts" :key="item.label" class="flex items-center gap-3">
            <span class="w-28 sm:w-36 text-sm font-medium text-neutral-600 dark:text-neutral-300 flex-shrink-0 text-right">{{ item.label }}</span>
            <div class="flex-1 h-7 rounded-lg bg-neutral-100 dark:bg-neutral-900/50 overflow-hidden relative">
              <div
                class="h-full rounded-lg bg-gradient-to-r from-blue-500 to-cyan-400 flex items-center justify-end pr-2 bar-fill relative overflow-hidden"
                :style="{ width: barsReady ? (item.count / maxCount * 100) + '%' : '0%', transitionDelay: `${i * 90}ms` }"
              >
                <span class="bar-sheen"></span>
                <span class="text-[11px] font-bold text-white/95 tabular-nums z-10">{{ item.count }}</span>
              </div>
            </div>
          </div>
          
          <div v-if="fieldCounts.length === 0" class="text-center text-neutral-500 text-sm py-4">
            Veritabanında analiz edilecek kampanya verisi bulunamadı.
          </div>
        </div>
      </div>

      <!-- ERİŞİLEBİLİRLİK TABLOSU -->
      <div class="reveal-on-scroll bg-white/80 dark:bg-neutral-800/60 backdrop-blur-md border border-neutral-200/50 dark:border-neutral-700/50 rounded-2xl shadow-sm overflow-hidden">
        <button
          type="button"
          @click="tableOpen = !tableOpen"
          class="w-full cursor-pointer select-none px-6 py-4 flex items-center gap-2 text-sm font-semibold text-neutral-700 dark:text-neutral-200 hover:bg-neutral-50 dark:hover:bg-neutral-700/30 transition-colors focus:outline-none"
        >
          <svg class="h-4 w-4 text-neutral-400 transition-transform duration-300" :class="tableOpen ? 'rotate-180' : ''" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M19 9l-7 7-7-7" /></svg>
          Tablo görünümü (erişilebilirlik)
        </button>

        <div class="grid transition-all duration-500 ease-in-out" :class="tableOpen ? 'grid-rows-[1fr] opacity-100' : 'grid-rows-[0fr] opacity-0'">
          <div class="overflow-hidden">
            <div class="overflow-x-auto border-t border-neutral-200/70 dark:border-neutral-700/70">
              <table class="w-full text-sm">
                <thead>
                  <tr class="text-left text-neutral-500 dark:text-neutral-400 bg-neutral-50/70 dark:bg-neutral-900/40">
                    <th class="px-6 py-3 font-semibold">Alan</th>
                    <th class="px-6 py-3 font-semibold text-right">Başarılı Çıkarım Sayısı</th>
                  </tr>
                </thead>
                <tbody>
                  <tr
                    v-for="(item, i) in fieldCounts"
                    :key="item.label"
                    class="border-t border-neutral-100 dark:border-neutral-700/50 hover:bg-blue-50/50 dark:hover:bg-blue-900/10 transition-colors"
                  >
                    <td class="px-6 py-3 text-neutral-700 dark:text-neutral-200">{{ item.label }}</td>
                    <td class="px-6 py-3 text-right font-bold text-blue-600 dark:text-cyan-400 tabular-nums">{{ item.count }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>

    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import Lenis from 'lenis'

const pending = ref(true)
const revealed = ref(false)
const barsReady = ref(false)
const tableOpen = ref(false)

let lenis = null
let lenisRafId = null
let observer = null

const metrics = ref([])
const display = ref([0, 0, 0, 0])
const fieldCounts = ref([])

const maxCount = computed(() => Math.max(...fieldCounts.value.map(f => f.count), 1))

const icons = {
  bank: '<svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M3 21h18M3 10h18M5 6l7-3 7 3M4 10v11m16-11v11M8 14v3m4-3v3m4-3v3"/></svg>',
  db: '<svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M4 7c0 1.657 3.582 3 8 3s8-1.343 8-3-3.582-3-8-3-8 1.343-8 3zm0 0v10c0 1.657 3.582 3 8 3s8-1.343 8-3V7"/></svg>',
  campaign: '<svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M11 5.882V19.24a1.76 1.76 0 01-3.417.592l-2.147-6.15M18 13a3 3 0 100-6M5.436 13.683A4.001 4.001 0 017 6h1.832c4.1 0 7.625-1.234 9.168-3v14c-1.543-1.766-5.067-3-9.168-3H7a3.988 3.988 0 01-1.564-.317z"/></svg>',
  check: '<svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>'
}

const runCountUp = () => {
  const targets = metrics.value.map(m => m.value)
  const duration = 1100
  const start = performance.now()
  const tick = (now) => {
    const p = Math.min((now - start) / duration, 1)
    const eased = 1 - Math.pow(1 - p, 3)
    display.value = targets.map(t => Math.round(t * eased))
    if (p < 1) requestAnimationFrame(tick)
    else display.value = targets
  }
  requestAnimationFrame(tick)
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

const fetchDashboardData = async () => {
  try {
    // 🚀 Yeni APIRouter ucu olan /campaigns 'e istek atıyoruz
    // Limiti 500 yapıyoruz ve tarihi geçenleri de (sadece_gecerli=false) getirmesini söylüyoruz!
    const res = await fetch('http://localhost:8003/campaigns?limit=500&sadece_gecerli=false')
    if (!res.ok) throw new Error('API Hatası')
    
    // 🚀 Yeni API yapısı doğrudan bir liste dönüyor (data.kampanyalar değil)
    const camps = await res.json() || []

    const uniqueBanks = new Set(camps.map(c => c.banka).filter(b => b && b !== 'Bilinmiyor')).size
    
    // 🚀 Yeni Pydantic şemasındaki (KampanyaOzet) doğru isimlendirmeler
    const uniqueTypes = new Set(camps.map(c => c.kampanya_turu).filter(t => t)).size
    const totalCampaigns = camps.length
    
    let countHedefKitle = 0, countBitis = 0, countOdul = 0, countTaksit = 0, countVade = 0, countKarPayi = 0, countTur = 0
    let totalExtractedFields = 0

    camps.forEach(c => {
      const isValid = (val) => val !== null && val !== undefined && val !== '' && val !== 'None'
      
      if (isValid(c.hedef_kitle)) { countHedefKitle++; totalExtractedFields++; }
      if (isValid(c.bitis_tarihi)) { countBitis++; totalExtractedFields++; }
      if (isValid(c.odul_miktari)) { countOdul++; totalExtractedFields++; }
      if (isValid(c.taksit_sayisi)) { countTaksit++; totalExtractedFields++; }
      if (isValid(c.vade_ay)) { countVade++; totalExtractedFields++; }
      if (isValid(c.kar_payi_orani)) { countKarPayi++; totalExtractedFields++; }
      if (isValid(c.kampanya_turu)) { countTur++; totalExtractedFields++; }
    })

    metrics.value = [
      { title: 'Veri Toplanan Banka', value: uniqueBanks, icon: icons.bank, trend: 'Aktif Sistemler', trendUp: true },
      { title: 'Kampanya Kategorisi', value: uniqueTypes, icon: icons.db, trend: '(Belirtilmemiş Dahil)', trendUp: true },
      { title: 'Toplam Kampanya', value: totalCampaigns, icon: icons.campaign, trend: 'Veritabanı Kaydı', trendUp: true },
      { title: 'Çıkarılan Alan (AI)', value: totalExtractedFields, icon: icons.check, trend: 'Başarılı Tespit', trendUp: true }
    ]
    display.value = [0, 0, 0, 0]

    const rawFields = [
      { label: 'Kampanya Türü', count: countTur },
      { label: 'Hedef Kitle', count: countHedefKitle },
      { label: 'Bitiş Tarihi', count: countBitis },
      { label: 'Ödül Miktarı (TL)', count: countOdul },
      { label: 'Taksit Sayısı', count: countTaksit },
      { label: 'Vade (Ay)', count: countVade },
      { label: 'Kâr Payı Oranı (%)', count: countKarPayi }
    ]
    
    fieldCounts.value = rawFields.sort((a, b) => b.count - a.count)

  } catch (err) {
    console.error("Dashboard istatistikleri çekilemedi:", err)
  } finally {
    pending.value = false
    nextTick(() => {
      revealed.value = true
      runCountUp()
      setTimeout(() => { barsReady.value = true }, 250)
      setTimeout(() => { tableOpen.value = true }, 500)
      
      const scrollerEl = document.getElementById('main-scroller')
      setupObserver(scrollerEl)
    })
  }
}

onMounted(() => {
  const scrollerEl = document.getElementById('main-scroller')
  if (scrollerEl) {
    const content = scrollerEl.querySelector('main') || scrollerEl.firstElementChild
    lenis = new Lenis({ wrapper: scrollerEl, content: content, duration: 1.15, easing: (t) => Math.min(1, 1.001 - Math.pow(2, -10 * t)), smoothWheel: true, gestureOrientation: 'vertical', touchMultiplier: 1.6 })
    const raf = (time) => { lenis.raf(time); lenisRafId = requestAnimationFrame(raf) }
    lenisRafId = requestAnimationFrame(raf)
  }

  fetchDashboardData()
})

onUnmounted(() => {
  if (lenisRafId) cancelAnimationFrame(lenisRafId)
  if (lenis) { lenis.destroy(); lenis = null }
  if (observer) { observer.disconnect(); observer = null }
})
</script>

<style scoped>
.gradient-text { background-image: linear-gradient(90deg, #2563eb, #06b6d4, #6366f1, #2563eb); background-size: 300% 100%; animation: gradShift 7s ease infinite; }
@keyframes gradShift { 0% { background-position: 0% 50%; } 50% { background-position: 100% 50%; } 100% { background-position: 0% 50%; } }
.reveal-title { animation: titleIn 0.8s cubic-bezier(0.22, 1, 0.36, 1) both; }
@keyframes titleIn { from { opacity: 0; transform: translateY(16px); letter-spacing: 0.08em; } to { opacity: 1; transform: translateY(0); letter-spacing: 0; } }
.title-underline { animation: underlineGrow 0.9s ease 0.3s both; transform-origin: center; }
@keyframes underlineGrow { from { transform: scaleX(0); opacity: 0; } to { transform: scaleX(1); opacity: 1; } }

.bg-blob { position: absolute; border-radius: 9999px; filter: blur(80px); opacity: 0.5; will-change: transform; }
.blob-1 { width: 32rem; height: 32rem; top: -8rem; left: -6rem; background: radial-gradient(circle at center, rgba(59,130,246,0.45), transparent 70%); animation: floatBlob 18s ease-in-out infinite; }
.blob-2 { width: 28rem; height: 28rem; top: 20%; right: -8rem; background: radial-gradient(circle at center, rgba(6,182,212,0.40), transparent 70%); animation: floatBlob 22s ease-in-out infinite reverse; }
.blob-3 { width: 26rem; height: 26rem; bottom: -6rem; left: 30%; background: radial-gradient(circle at center, rgba(99,102,241,0.35), transparent 70%); animation: floatBlob 26s ease-in-out infinite; }
:global(.dark) .bg-blob { opacity: 0.35; }
@keyframes floatBlob { 0%, 100% { transform: translate(0, 0) scale(1); } 33% { transform: translate(60px, -50px) scale(1.12); } 66% { transform: translate(-40px, 40px) scale(0.94); } }

.bg-grid { position: absolute; inset: 0; background-image: linear-gradient(to right, rgba(100,116,139,0.06) 1px, transparent 1px), linear-gradient(to bottom, rgba(100,116,139,0.06) 1px, transparent 1px); background-size: 44px 44px; animation: gridDrift 30s linear infinite; mask-image: radial-gradient(ellipse 80% 60% at 50% 30%, #000 40%, transparent 100%); -webkit-mask-image: radial-gradient(ellipse 80% 60% at 50% 30%, #000 40%, transparent 100%); }
@keyframes gridDrift { 0% { background-position: 0 0, 0 0; } 100% { background-position: 44px 44px, 44px 44px; } }

.reveal-on-scroll { opacity: 0; transform: translateY(28px); transition: opacity 0.6s cubic-bezier(0.22,1,0.36,1), transform 0.6s cubic-bezier(0.22,1,0.36,1); }
.reveal-on-scroll.is-visible { opacity: 1; transform: none; }

.bar-fill { transition: width 1.1s cubic-bezier(0.22, 1, 0.36, 1); min-width: 1.8rem; }
.bar-sheen { position: absolute; inset: 0; background: linear-gradient(100deg, transparent 20%, rgba(255,255,255,0.35) 50%, transparent 80%); transform: translateX(-100%); animation: sheen 2.4s ease-in-out infinite; }
@keyframes sheen { 0% { transform: translateX(-100%); } 60%, 100% { transform: translateX(100%); } }

.a11y-table[open] .chevron { transform: rotate(180deg); }
.shimmer { position: relative; overflow: hidden; }
.shimmer::after { content: ''; position: absolute; inset: 0; transform: translateX(-100%); background: linear-gradient(90deg, transparent, rgba(255,255,255,0.25), transparent); animation: shimmer 1.4s infinite; }
@keyframes shimmer { 100% { transform: translateX(100%); } }
</style>