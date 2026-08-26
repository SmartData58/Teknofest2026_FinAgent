<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { gsap } from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import Lenis from 'lenis'

gsap.registerPlugin(ScrollTrigger)

const router = useRouter()
const { t } = useI18n()

useHead({
  title: computed(() => t('page_titles.home', 'Katılım Bankacılığı Kampanya & Finansman Asistanı'))
})

// Sohbet kutusu ve yönlendirme ayarları
const chatBoxRef = ref(null)
const isLoading = ref(true)
let ctx;
const hasNavigated = ref(false)
const isTransitioning = ref(false)

// 🚀 TOKAT: Geçişi temiz (hard) bir navigasyona çevirdik ki Chat sayfasının scroll motoru kilitlenmesin!
const startTransition = () => {
  if (hasNavigated.value) return
  hasNavigated.value = true
  isTransitioning.value = true

  // Önce Lenis'i kibarca kapatıyoruz
  if (lenis) {
    lenis.destroy()
    lenis = null
  }
  if (lenisRaf) {
    gsap.ticker.remove(lenisRaf)
  }

  setTimeout(() => {
    // ŞUNU SİL: window.location.href = '/chat'
    // ŞUNU YAZ:
    router.push('/chat')
  }, 750)
}

let scrollerEl = null
let onScrollHandler = null
let lenis = null
let lenisRaf = null

// Üst Menü Yönlendirmeleri
const navItems = computed(() => [
  { name: t('landing.nav.hero', 'Asistan'), id: 'hero' },
  { name: t('landing.nav.summary', 'Proje Özeti'), id: 'ozet' },
  { name: t('landing.nav.architecture', 'Sistem Mimarisi'), id: 'mimari' },
  { name: t('landing.nav.flow', 'Sistem Akışı'), id: 'akis' },
  { name: t('landing.nav.goals', 'Hedefler'), id: 'hedefler' },
  { name: t('landing.nav.team', 'Takım'), id: 'takim' }
])

const scrollTo = (id) => {
  const el = document.getElementById(id)
  if (!el) return
  // Lenis varsa onun yumuşak kaydırmasını kullan, yoksa native
  if (lenis) {
    lenis.scrollTo(el, { offset: -56, duration: 1.4 })
  } else {
    el.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }
}

// ---------------- VERİ SETLERİ ----------------
// 🛠️ GÜNCELLEME: Gerçek mimariyle eşleştirildi.
// - NER/ModernBERT-TR ADIMI KALDIRILDI: sistemde ayrı bir NER servisi
//   kullanılmıyor; alan çıkarımı regex + LLM tabanlı niyet/özet analiziyle
//   yapılıyor (bkz. chatbot/intent.py, generate_response.py).
// - PostgreSQL -> MongoDB: yapılandırılmış kampanya kayıtları MongoDB'de
//   tutuluyor (MONGO_URI), ilişkisel bir veritabanı kullanılmıyor.
// - Reranker adımı KALDIRILDI: sistemde reranker kodu mevcut ve bağlı
//   (EVREN_RERANK ile açılabiliyor) ama yarışma dokümantasyonunun kendi
//   ölçümü (R@1 0,95 -> 0,55) nedeniyle VARSAYILAN OLARAK KAPALI; bu yüzden
//   üretimde kullanılmayan bir bileşen olarak akıştan çıkarıldı.
// - LLM/Embedding modelleri artık yerel değil, yarışmanın "Evren" API'si
//   üzerinden (EVREN_MODEL=llm-large, EVREN_EMBED_MODEL=bge-m3-embed).
const flowSteps = computed(() => [
  { id: 1, title: t('landing.flow.1.title', 'Web Scraping'), desc: t('landing.flow.1.desc', 'BeautifulSoup, Playwright') },
  { id: 2, title: t('landing.flow.2.title', 'Ham Metin'), desc: t('landing.flow.2.desc', 'Kampanya metni, başlık, tarih') },
  { id: 3, title: t('landing.flow.3.title', 'Ön İşleme'), desc: t('landing.flow.3.desc', 'HTML temizliği, normalizasyon') },
  { id: 4, title: t('landing.flow.4.title', 'Regex Yakalama'), desc: t('landing.flow.4.desc', 'Oran, vade, tutar, taksit') },
  { id: 5, title: t('landing.flow.5.title', 'Veri Kaydı'), desc: t('landing.flow.5.desc', 'MongoDB') },
  { id: 6, title: t('landing.flow.6.title', 'Embedding'), desc: t('landing.flow.6.desc', 'Evren API (bge-m3-embed)') },
  { id: 7, title: t('landing.flow.7.title', 'Vektör İndeksleme'), desc: t('landing.flow.7.desc', 'Qdrant (Metadata ile)') },
  { id: 8, title: t('landing.flow.8.title', 'Kullanıcı Sorgusu'), desc: t('landing.flow.8.desc', 'Nuxt Arayüzü') },
  { id: 9, title: t('landing.flow.9.title', 'Sorgu İşleme'), desc: t('landing.flow.9.desc', 'Niyet Analizi (Regex + LLM)') },
  { id: 10, title: t('landing.flow.10.title', 'LLM Üretimi'), desc: t('landing.flow.10.desc', 'Evren API (llm-large)') },
  { id: 11, title: t('landing.flow.11.title', 'Formatlama'), desc: t('landing.flow.11.desc', 'JSON / Markdown Tablosu') },
  { id: 12, title: t('landing.flow.12.title', 'Kullanıcıya Sunum'), desc: t('landing.flow.12.desc', 'Dashboard & Chatbot') }
])

const projectGoals = computed(() => [
  t('landing.goals.1', "Veri Toplama: En az 5 farklı katılım bankasının resmî web sitesinden, en az 3 farklı ürün kategorisine ait 100’den fazla kampanya metnini toplamak."),
  t('landing.goals.2', "Bilgi Çıkarımı Başarımı: Çıkarılan kâr payı oranı, vade, masraf ve ödül bilgilerinde %90 üzeri doğruluk oranına ulaşmak."),
  t('landing.goals.3', "Dashboard Geliştirme: Kullanıcıların bankalar arası karşılaştırma yapabilmesine olanak sağlayan, filtreleme ve sıralama özellikleri bulunan interaktif bir dashboard’u tamamlamak."),
  t('landing.goals.4', "Chatbot İşlevselliği: Kullanıcıların doğal dilde sorduğu “A Bankası’nın konut oranı ne?” veya “En düşük kâr payı hangi bankada?” gibi sorulara cevap verebilen bir chatbot’u çalışır hale getirmek."),
  t('landing.goals.5', "On-Premise Uygunluk: Sistemin, harici servislere bağımlı olmadan, tek bir lokal sunucuda çalışabilir olduğunu doğrulamak.")
])

const teamMembers = computed(() => [
  {
    name: 'Fadime Nisa Baysal',
    role: t('landing.team.1.role', 'Takım Kaptanı'),
    university: t('landing.team.1.university', 'Bilgisayar Mühendisliği 4. Sınıf - Giresun Üniversitesi'),
    desc: t('landing.team.1.desc', 'Python, Java, JavaScript programlama dilleri ile veritabanı yönetim sistemlerinde yetkindir. Daha önce yapay zekâ destekli görüntü işleme, full-stack web geliştirme ve makine öğrenmesi tabanlı zaman serisi analizi projelerinde aktif roller üstlenmiştir. FinAgent projesinde; katılım bankacılığı kampanya metinlerinin ön işlenmesi, doğal dil işleme mimarilerinin araştırılması, bilgi çıkarımı ve derin öğrenme modellerinin geliştirilmesi süreçlerinden sorumludur.')
  },
  {
    name: 'Mehmet Emre Ayçiçek',
    role: t('landing.team.2.role', 'Backend & Sistem'),
    university: t('landing.team.2.university', 'Bilgisayar Mühendisliği 3. Sınıf - Sivas Cumhuriyet Üniversitesi'),
    desc: t('landing.team.2.desc', 'Veritabanı sistemleri, Python programlama, algoritma geliştirme, yapay zekâ ve veri analizi alanlarında çalışmalar yürütmektedir. FinAgent projesinde; katılım bankalarının web sitelerinden otomatik veri toplama (web scraping), backend altyapısının kurulması, dashboard entegrasyonu ve sistem entegrasyon testlerinin yürütülmesinde aktif rol oynamaktadır.')
  },
  {
    name: 'Musa Ayçiçek',
    role: t('landing.team.3.role', 'Veri Analitiği'),
    university: t('landing.team.3.university', 'Yönetim Bilişim Sistemleri Mezunu - Sivas Cumhuriyet Üniversitesi'),
    desc: t('landing.team.3.desc', 'Veri işleme ve görüntü işleme alanlarında kendini geliştirmiştir. Python ve Kotlin dillerinde bilgi sahibidir. FinAgent projesinde; katılım bankacılığı kampanya metinlerinin ön işlenmesi, yapay zekâ modelleri için veri setlerinin düzenlenmesi ve bilgi çıkarımı süreçlerine uygun veri analitiği aşamalarının yürütülmesinden sorumludur.')
  },
  {
    name: 'Ahmet Salik Göksu',
    role: t('landing.team.4.role', 'Yapay Zeka & Arayüz'),
    university: t('landing.team.4.university', 'Yapay Zeka Mühendisliği 2. Sınıf - Adana Alparslan Türkeş BTÜ'),
    desc: t('landing.team.4.desc', 'Java eğitimi almış olup, C# ve Python programlama dilleri hakkında da bilgi sahibidir. FinAgent projesinde; kullanıcı dostu arayüzlerin geliştirilmesi, web arayüz bileşenlerinin kurgulanması ve ön yüz ile yapay zekâ model entegrasyonu süreçlerinde görev almaktadır.')
  }
])

onMounted(() => {
  document.fonts.ready.then(() => {
    setTimeout(() => {
      isLoading.value = false
      nextTick(() => {

        scrollerEl = document.getElementById('main-scroller')

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
          lenisRaf = (time) => { lenis.raf(time * 1000) }
          gsap.ticker.add(lenisRaf)
          gsap.ticker.lagSmoothing(0)
        }

        ctx = gsap.context(() => {
          gsap.utils.toArray('.scroll-section').forEach((section) => {
            gsap.fromTo(section,
              { opacity: 0, y: 60 },
              {
                opacity: 1, y: 0, ease: "none",
                scrollTrigger: { trigger: section, scroller: "#main-scroller", start: "top 92%", end: "top 55%", scrub: true }
              }
            )
          })

          gsap.utils.toArray('.stagger-group').forEach((group) => {
            const items = group.querySelectorAll('.stagger-item')
            if (!items.length) return
            gsap.fromTo(items,
              { opacity: 0, y: 46, scale: 0.92 },
              {
                opacity: 1, y: 0, scale: 1, ease: "power2.out", stagger: 0.2,
                scrollTrigger: { trigger: group, scroller: "#main-scroller", start: "top 88%", end: "bottom 65%", scrub: true }
              }
            )
          })

          gsap.utils.toArray('.anim-heading').forEach((h) => {
            gsap.fromTo(h,
              { opacity: 0, y: 28, letterSpacing: '0.12em' },
              {
                opacity: 1, y: 0, letterSpacing: '0em', ease: "none",
                scrollTrigger: { trigger: h, scroller: "#main-scroller", start: "top 92%", end: "top 62%", scrub: true }
              }
            )
          })

          gsap.utils.toArray('[data-parallax]').forEach((el) => {
            const speed = parseFloat(el.getAttribute('data-parallax')) || 0.1
            gsap.to(el, {
              yPercent: speed * 100,
              ease: "none",
              scrollTrigger: { trigger: el, scroller: "#main-scroller", start: "top bottom", end: "bottom top", scrub: true }
            })
          })

          gsap.utils.toArray('.parallax-blob').forEach((blob, i) => {
            gsap.to(blob, {
              yPercent: i % 2 === 0 ? -40 : 45,
              xPercent: i % 2 === 0 ? -15 : 20,
              ease: "none",
              scrollTrigger: { trigger: ".gradient-band", scroller: "#main-scroller", start: "top bottom", end: "bottom top", scrub: 1 }
            })
          })
        })

        ScrollTrigger.refresh()

        if (scrollerEl) {
          onScrollHandler = () => {
            if (hasNavigated.value) return
            const box = chatBoxRef.value
            if (!box) return
            const rect = box.getBoundingClientRect()
            const boxCenter = rect.top + rect.height / 2
            const viewportCenter = window.innerHeight / 2
            const passedCenter = boxCenter <= viewportCenter - 5
            const nearBottom = scrollerEl.scrollTop + scrollerEl.clientHeight >= scrollerEl.scrollHeight - 8

            // Kullanıcı chat kısmına ulaştığında geçişi tetikle
            if (passedCenter || nearBottom) startTransition()
          }
          scrollerEl.addEventListener('scroll', onScrollHandler, { passive: true })
        }
      })
    }, 300)
  })
})

onUnmounted(() => {
  if (ctx) ctx.revert()
  if (scrollerEl && onScrollHandler) scrollerEl.removeEventListener('scroll', onScrollHandler)
  if (lenisRaf) gsap.ticker.remove(lenisRaf)
  if (lenis) { lenis.destroy(); lenis = null }
})
</script>

<template>
  <div class="relative w-full">

    <!-- SAYFA ZEMİNİ: dark modda gri değil, siyaha yakın koyu bir taban -->
    <div class="fixed inset-0 -z-20 bg-neutral-50 dark:bg-neutral-950 pointer-events-none"></div>

    <!-- SAYFA GEÇİŞ OVERLAY'İ -->
    <Transition name="chat-transition">
      <div v-if="isTransitioning" class="fixed inset-0 z-[100] flex flex-col items-center justify-center bg-gradient-to-br from-blue-600 via-blue-600 to-cyan-500 text-white overflow-hidden">
        <div class="absolute w-40 h-40 rounded-full bg-white/20 animate-ping"></div>
        <div class="absolute w-64 h-64 rounded-full border border-white/20 animate-pulse"></div>
        <div class="relative flex flex-col items-center gap-5">
          <svg class="h-12 w-12 animate-spin text-white/90" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
            <path class="opacity-90" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
          </svg>
          <p class="text-xl font-semibold tracking-wide">{{ t('landing.transition.title', 'Yapay Zeka Hazırlanıyor...') }}</p>
          <p class="text-sm text-blue-100/80">{{ t('landing.transition.subtitle', 'FinAgent sohbet arayüzüne yönlendiriliyorsunuz') }}</p>
        </div>
      </div>
    </Transition>

    <!-- SKELETON LOADER -->
    <Transition name="fade">
      <SkeletonPage v-if="isLoading" class="absolute inset-0 z-50 bg-neutral-50 dark:bg-neutral-900" />
    </Transition>

    <div v-if="!isLoading" class="relative w-full transition-opacity duration-500 ease-in">

      <div class="relative z-10 w-full">

        <!-- ================= BÖLÜM 1: HERO ================= -->
        <section id="hero" class="scroll-section snap-start snap-always min-h-screen flex flex-col px-6 relative pt-14 overflow-hidden">
          
          <!-- SADECE BEYAZ KISIM (HERO) İÇİN SÜZÜLEN PARTİKÜLLER -->
          <FloatingParticles />

          <div class="sticky top-14 w-full flex flex-wrap justify-center gap-3 pt-6 pb-2 z-30">
            <div v-for="item in navItems" :key="item.id" class="relative group">
              <button @click="scrollTo(item.id)" class="px-5 py-2 text-sm font-medium rounded-full bg-white/60 dark:bg-neutral-800/60 backdrop-blur-md border border-neutral-200/50 dark:border-neutral-700/50 text-neutral-600 dark:text-neutral-300 hover:border-blue-400 hover:text-blue-600 hover:-translate-y-0.5 transition-all shadow-sm focus:outline-none">{{ item.name }}</button>
            </div>
          </div>
          <div class="flex-1 flex flex-col items-center justify-center pb-24 z-20 w-full max-w-4xl mx-auto text-center">
            <h1 data-parallax="0.14" class="text-5xl md:text-7xl font-bold bg-clip-text text-transparent gradient-text pb-2 tracking-tight mb-12">{{ t('landing.hero.title', 'Akıllı Finans Asistanı') }}</h1>
            <div class="w-full pointer-events-auto animate-float-soft"><ChatPrompt /></div>
          </div>
        </section>

        <!-- ================= BÖLÜM 2: PROJE ÖZETİ ================= -->
        <section id="ozet" class="scroll-section snap-start snap-always min-h-screen flex items-center justify-center px-6 py-20 bg-neutral-900/80 backdrop-blur-lg">
          <div class="max-w-5xl w-full">
            <h2 class="anim-heading text-3xl font-bold text-center mb-12 text-white">{{ t('landing.summary.heading', 'Proje Özeti') }}</h2>
            <div class="stagger-group w-full bg-white/5 border border-white/10 rounded-2xl overflow-hidden shadow-2xl flex flex-col">

              <div class="stagger-item grid grid-cols-1 md:grid-cols-[1fr,3fr] border-b border-white/10">
                <div class="p-6 bg-white/5 font-bold text-cyan-300 flex items-center">{{ t('landing.summary.name_label', 'Proje Adı') }}</div>
                <div class="p-6 text-white font-medium text-lg">FinAgent</div>
              </div>

              <div class="stagger-item grid grid-cols-1 md:grid-cols-[1fr,3fr] border-b border-white/10">
                <div class="p-6 bg-white/5 font-bold text-cyan-300 flex items-center">{{ t('landing.summary.purpose_label', 'Projenin Amacı') }}</div>
                <div class="p-6 text-neutral-300">{{ t('landing.summary.purpose_text', 'Katılım bankalarının web sitelerinde yayınlanan doğal dildeki kampanya metinlerinden kâr payı oranı, vade, ücret, ödül gibi finansal bilgileri otomatik çıkararak, bu bilgileri standartlaştırıp dashboard ve chatbot aracılığıyla kullanıcılara sunmak.') }}</div>
              </div>

              <div class="stagger-item grid grid-cols-1 md:grid-cols-[1fr,3fr] border-b border-white/10">
                <div class="p-6 bg-white/5 font-bold text-cyan-300 flex items-center">{{ t('landing.summary.problem_label', 'Problemin Tanımı') }}</div>
                <div class="p-6 text-neutral-300">{{ t('landing.summary.problem_text', 'Katılım bankacılığında kampanya metinleri farklı formatlarda, farklı terminolojilerle yazılmakta ve manuel karşılaştırma zorlaşmaktadır. Bu durum banka çalışanlarının ve müşterilerin en avantajlı ürünü seçmesini geciktirmektedir.') }}</div>
              </div>

              <div class="stagger-item grid grid-cols-1 md:grid-cols-[1fr,3fr]">
                <div class="p-6 bg-white/5 font-bold text-cyan-300 flex items-center">{{ t('landing.summary.solution_label', 'Çözüm Yaklaşımı') }}</div>
                <div class="p-6 text-neutral-300">{{ t('landing.summary.solution_text', 'Web scraping ile veri toplama, Türkçe metin ön işleme ve regex tabanlı bilgi çıkarımı, yarışmanın Evren API üzerinden sunduğu büyük dil modeli ile niyet analizi ve doğal dilde yanıt üretimi, çıkarılan verileri standart formata dönüştürüp karşılaştırılabilir hale getirme, sonuçları interaktif dashboard ve soru-cevap chatbotu ile kullanıcıya sunma.') }}</div>
              </div>

            </div>
          </div>
        </section>

        <!-- ORTA BLOK: MAVİ GRADIENT ARKA PLAN -->
        <div class="relative overflow-hidden gradient-band text-white">
          <div class="parallax-blob pointer-events-none absolute -top-32 -left-32 w-96 h-96 rounded-full bg-cyan-400/30 blur-3xl animate-blob"></div>
          <div class="parallax-blob pointer-events-none absolute top-1/3 -right-32 w-[28rem] h-[28rem] rounded-full bg-blue-300/20 blur-3xl animate-blob animation-delay-2000"></div>
          <div class="parallax-blob pointer-events-none absolute bottom-0 left-1/4 w-80 h-80 rounded-full bg-indigo-400/25 blur-3xl animate-blob animation-delay-4000"></div>

          <!-- ================= BÖLÜM 3: SİSTEM MİMARİSİ ================= -->
          <section id="mimari" class="scroll-section snap-start snap-always min-h-screen flex items-center justify-center px-6 py-20 relative">
            <div class="max-w-5xl w-full text-center">
              <h2 class="anim-heading text-3xl font-bold mb-12 text-white drop-shadow-sm">{{ t('landing.architecture.heading', 'Sistem Mimarisi Katmanları') }}</h2>

              <div class="stagger-group flex flex-col gap-5 w-full max-w-4xl mx-auto">
                <div class="stagger-item p-5 bg-white/10 backdrop-blur-md border border-white/20 rounded-2xl shadow-lg relative overflow-hidden hover:bg-white/15 hover:-translate-y-1 transition-all duration-300">
                  <div class="absolute top-0 left-0 w-1 bg-cyan-300 h-full"></div>
                  <h3 class="text-sm uppercase tracking-widest text-cyan-200 mb-4 font-bold flex items-center justify-center gap-2">
                    <span class="w-6 h-6 rounded-full bg-cyan-500/30 flex items-center justify-center text-xs">3</span>
                    {{ t('landing.architecture.ui.title', 'Kullanıcı Arayüzü') }}
                  </h3>
                  <div class="flex flex-col sm:flex-row justify-center gap-4">
                    <div class="px-6 py-3 bg-white/10 border border-white/10 rounded-xl text-sm font-medium text-white w-full sm:w-1/2">
                      <span class="block text-cyan-300 font-bold mb-1">{{ t('landing.architecture.ui.web', 'Nuxt Web Arayüzü') }}</span>
                      <span class="text-xs text-white/70">{{ t('landing.architecture.ui.web_desc', 'Dashboard, Filtreleme ve Karşılaştırma') }}</span>
                    </div>
                    <div class="px-6 py-3 bg-white/10 border border-white/10 rounded-xl text-sm font-medium text-white w-full sm:w-1/2 flex items-center justify-center">
                      <span class="text-cyan-300 font-bold">{{ t('landing.architecture.ui.chat', 'Vue Chatbot') }}</span>
                    </div>
 
                  
                 </div>
                </div>

                <div class="stagger-item p-5 bg-white/10 backdrop-blur-md border border-white/20 rounded-2xl shadow-lg relative overflow-hidden hover:bg-white/15 hover:-translate-y-1 transition-all duration-300">
                  <div class="absolute top-0 left-0 w-1 bg-blue-300 h-full"></div>
                  <h3 class="text-sm uppercase tracking-widest text-blue-200 mb-4 font-bold flex items-center justify-center gap-2">
                    <span class="w-6 h-6 rounded-full bg-blue-500/30 flex items-center justify-center text-xs">2</span>
                    {{ t('landing.architecture.backend.title', 'FastAPI Backend') }}
                  </h3>
                  <div class="flex flex-col sm:flex-row justify-center gap-4">
                    <div class="px-6 py-3 bg-white/10 border border-white/10 rounded-xl text-sm font-medium text-white w-full sm:w-1/2">
                      <span class="block text-blue-300 font-bold mb-1">{{ t('landing.architecture.backend.engine', 'RAG Motoru') }}</span>
                      <span class="text-xs text-white/70">{{ t('landing.architecture.backend.engine_desc', 'Getirme (Retrieve) + Üretim (Generate)') }}</span>
                    </div>
                    <div class="px-6 py-3 bg-white/10 border border-white/10 rounded-xl text-sm font-medium text-white w-full sm:w-1/2 flex items-center justify-center">
                      <span class="text-xs font-mono text-white/80">/api/chat, /api/campaigns/compare, /api/campaigns/top-advantageous, /admin/reindex, /health</span>
                    </div>
                  </div>
                </div>

                <div class="stagger-item p-5 bg-white/10 backdrop-blur-md border border-white/20 rounded-2xl shadow-lg relative overflow-hidden hover:bg-white/15 hover:-translate-y-1 transition-all duration-300">
                  <div class="absolute top-0 left-0 w-1 bg-indigo-300 h-full"></div>
                  <h3 class="text-sm uppercase tracking-widest text-indigo-200 mb-4 font-bold flex items-center justify-center gap-2">
                    <span class="w-6 h-6 rounded-full bg-indigo-500/30 flex items-center justify-center text-xs">2</span>
                    {{ t('landing.architecture.ai.title', 'Yapay Zeka Servis Katmanı (Evren API)') }}
                  </h3>
                  <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div class="p-3 bg-white/10 border border-white/10 rounded-xl flex flex-col items-center text-center">
                      <span class="text-indigo-300 text-[10px] font-bold mb-1 uppercase tracking-wider">LLM</span>
                      <span class="text-xs text-white font-medium">llm-large</span>
                    </div>
                    <div class="p-3 bg-white/10 border border-white/10 rounded-xl flex flex-col items-center text-center">
                      <span class="text-indigo-300 text-[10px] font-bold mb-1 uppercase tracking-wider">{{ t('landing.architecture.ai.embedding', 'Embedding') }}</span>
                      <span class="text-xs text-white font-medium">bge-m3-embed</span>
                    </div>
                  </div>
                </div>

                <div class="stagger-item p-5 bg-white/10 backdrop-blur-md border border-white/20 rounded-2xl shadow-lg relative overflow-hidden hover:bg-white/15 hover:-translate-y-1 transition-all duration-300">
                  <div class="absolute top-0 left-0 w-1 bg-teal-300 h-full"></div>
                  <h3 class="text-sm uppercase tracking-widest text-teal-200 mb-4 font-bold flex items-center justify-center gap-2">
                    <span class="w-6 h-6 rounded-full bg-teal-500/30 flex items-center justify-center text-xs">1</span>
                    {{ t('landing.architecture.data.title', 'Veri Katmanı') }}
                  </h3>
                  <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div class="p-2 bg-white/10 border border-white/10 rounded-xl flex flex-col items-center text-center">
                      <span class="text-teal-300 text-sm font-bold">MongoDB</span>
                      <span class="text-[10px] text-white/70">{{ t('landing.architecture.data.mongo', 'Kampanya Verisi') }}</span>
                    </div>
                    <div class="p-2 bg-white/10 border border-white/10 rounded-xl flex flex-col items-center text-center">
                      <span class="text-teal-300 text-sm font-bold">Qdrant</span>
                      <span class="text-[10px] text-white/70">{{ t('landing.architecture.data.qdrant', 'Vektör DB') }}</span>
                    </div>
                    <div class="p-2 bg-white/10 border border-white/10 rounded-xl flex flex-col items-center text-center">
                      <span class="text-teal-300 text-sm font-bold">Redis</span>
                      <span class="text-[10px] text-white/70">{{ t('landing.architecture.data.redis', 'Önbellek') }}</span>
                    </div>
                    <div class="p-2 bg-white/10 border border-white/10 rounded-xl flex flex-col items-center text-center">
                      <span class="text-teal-300 text-sm font-bold">{{ t('landing.architecture.data.scraper', 'Web Scraper') }}</span>
                      <span class="text-[10px] text-white/70">BS4 + Playwright</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </section>

          <!-- ================= BÖLÜM 4: SİSTEM AKIŞI ================= -->
          <section id="akis" class="scroll-section snap-start snap-always min-h-screen flex items-center justify-center px-6 py-20 relative">
            <div class="max-w-6xl w-full text-center">
              <h2 class="anim-heading text-3xl font-bold mb-12 text-white drop-shadow-sm">{{ t('landing.flow_heading', 'Sistem Akış Diyagramı') }}</h2>

              <div class="stagger-group grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-6 gap-4">
                <div v-for="step in flowSteps" :key="step.id" class="stagger-item p-4 bg-white/5 backdrop-blur-sm border border-white/10 rounded-xl flex flex-col items-center text-center relative group hover:bg-white/15 hover:-translate-y-1 transition-all duration-300">
                  <div class="w-8 h-8 rounded-full bg-cyan-500/20 text-cyan-300 border border-cyan-400/30 flex items-center justify-center font-bold text-sm mb-3 group-hover:scale-110 transition-transform">
                    {{ step.id }}
                  </div>
                  <h4 class="text-xs font-bold text-white mb-1 h-8 flex items-center justify-center">{{ step.title }}</h4>
                  <p class="text-[10px] text-white/70 leading-tight">{{ step.desc }}</p>
                  <div v-if="step.id !== 6 && step.id !== 12" class="hidden lg:block absolute top-1/2 -right-3 w-4 h-0.5 bg-white/20 -translate-y-1/2"></div>
                </div>
              </div>
            </div>
          </section>

          <!-- ================= BÖLÜM 5: PROJE HEDEFLERİ ================= -->
          <section id="hedefler" class="scroll-section snap-start snap-always min-h-screen flex items-center justify-center px-6 py-20 relative">
            <div class="max-w-4xl w-full">
              <h2 class="anim-heading text-3xl font-bold text-center mb-12 text-white drop-shadow-sm">{{ t('landing.goals_heading', 'Proje Hedefleri') }}</h2>
              <div class="stagger-group space-y-4">
                <div v-for="(goal, index) in projectGoals" :key="index" class="stagger-item flex items-start gap-4 p-5 bg-white/10 backdrop-blur-md border border-white/20 rounded-2xl hover:bg-white/15 hover:translate-x-1 transition-all duration-300">
                  <span class="text-cyan-400 text-xl mt-0.5">◆</span>
                  <p class="text-neutral-100 text-sm md:text-base leading-relaxed">
                    <span class="font-bold text-white">{{ goal.split(':')[0] }}:</span>
                    {{ goal.split(':')[1] }}
                  </p>
                </div>
              </div>
            </div>
          </section>
        </div>

        <!-- ================= BÖLÜM 6: TAKIM KARTLARI ================= -->
        <section id="takim" class="scroll-section snap-start snap-always min-h-screen flex items-center justify-center py-20 px-6 bg-neutral-900/90 backdrop-blur-lg">
          <div class="max-w-6xl w-full mx-auto">
            <h2 class="anim-heading text-3xl font-bold text-center mb-12 text-white">{{ t('landing.team_heading', 'SmartData Takımı') }}</h2>

            <div class="stagger-group grid md:grid-cols-2 gap-6">
              <div v-for="member in teamMembers" :key="member.name" class="stagger-item p-6 bg-white/5 border border-white/10 rounded-2xl flex flex-col justify-between hover:border-cyan-500/50 hover:-translate-y-1 transition-all duration-300">
                <div>
                  <h3 class="text-xl font-bold text-cyan-300 text-center">{{ member.role }}</h3>
                  <h4 class="text-lg font-bold text-white text-center mt-1">{{ member.name }}</h4>
                  <p class="text-xs text-center text-white/70 mt-2 mb-4 font-semibold">{{ member.university }}</p>
                </div>
                <p class="text-sm text-neutral-300 text-justify leading-relaxed border-t border-white/10 pt-4">
                  {{ member.desc }}
                </p>
              </div>
            </div>
          </div>
        </section>

        <!-- ================= BÖLÜM 7: KAPANIŞ & SİHİRLİ CHAT ================= -->
        <section class="scroll-section snap-start snap-always px-6 relative bg-transparent">
          <div class="w-full h-[180vh] relative">
            <div ref="chatBoxRef" class="sticky top-1/2 -translate-y-1/2 w-full max-w-4xl mx-auto pointer-events-auto z-10">
              <ChatPrompt />
              <p class="mt-6 text-center text-sm font-medium text-neutral-400 animate-pulse">{{ t('landing.closing.hint', 'Sohbete başlamak için aşağı kaydırmaya devam edin veya arama yapın.') }}</p>
            </div>
          </div>
        </section>

      </div>
    </div>
  </div>
</template>

<style scoped>
.fade-enter-active, .fade-leave-active { transition: opacity 0.4s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }

/* Sohbete geçiş overlay animasyonu */
.chat-transition-enter-active { transition: opacity 0.35s ease, transform 0.35s ease; }
.chat-transition-leave-active { transition: opacity 0.3s ease; }
.chat-transition-enter-from { opacity: 0; transform: scale(1.04); }
.chat-transition-leave-to { opacity: 0; }

/* Orta blok: hareketli mavi gradient bandı */
.gradient-band {
  background: linear-gradient(135deg, #1d4ed8, #2563eb, #0891b2, #2563eb);
  background-size: 300% 300%;
  animation: gradientShift 14s ease infinite;
}
@keyframes gradientShift {
  0% { background-position: 0% 50%; }
  50% { background-position: 100% 50%; }
  100% { background-position: 0% 50%; }
}

/* Hero başlığı: akan gradient metin */
.gradient-text {
  background-image: linear-gradient(90deg, #2563eb, #06b6d4, #6366f1, #2563eb);
  background-size: 300% 100%;
  animation: textShift 8s ease infinite;
}
@keyframes textShift {
  0% { background-position: 0% 50%; }
  50% { background-position: 100% 50%; }
  100% { background-position: 0% 50%; }
}

/* Hero sohbet kutusu: yavaş süzülme */
@keyframes floatSoft {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-8px); }
}
.animate-float-soft { animation: floatSoft 5s ease-in-out infinite; }

/* Yüzen ışık lekeleri */
@keyframes blob {
  0%, 100% { transform: translate(0, 0) scale(1); }
  33% { transform: translate(30px, -40px) scale(1.1); }
  66% { transform: translate(-25px, 25px) scale(0.95); }
}
.animate-blob { animation: blob 12s ease-in-out infinite; }
.animation-delay-2000 { animation-delay: 2s; }
.animation-delay-4000 { animation-delay: 4s; }
</style>