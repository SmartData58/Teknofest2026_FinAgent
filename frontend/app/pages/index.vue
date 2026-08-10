<script setup>
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
import { gsap } from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'
import { useRoute, useRouter } from 'vue-router'
import Lenis from 'lenis'

gsap.registerPlugin(ScrollTrigger)

const router = useRouter()

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
const navItems = [
  { name: 'Asistan', id: 'hero' },
  { name: 'Proje Özeti', id: 'ozet' },
  { name: 'Sistem Mimarisi', id: 'mimari' },
  { name: 'Sistem Akışı', id: 'akis' },
  { name: 'Hedefler', id: 'hedefler' },
  { name: 'Takım', id: 'takim' }
]

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

const flowSteps = [
  { id: 1, title: 'Web Scraping', desc: 'BeautifulSoup, Selenium' },
  { id: 2, title: 'Ham Metin', desc: 'Kampanya metni, başlık, tarih' },
  { id: 3, title: 'Ön İşleme', desc: 'HTML temizliği, normalizasyon' },
  { id: 4, title: 'Regex Yakalama', desc: 'Oran, vade, tutar, taksit' },
  { id: 5, title: 'NER & Sınıflandırma', desc: 'ModernBERT-TR' },
  { id: 6, title: 'Veri Kaydı', desc: 'PostgreSQL' },
  { id: 7, title: 'Embedding', desc: 'Qwen3-Embedding-0.6B' },
  { id: 8, title: 'Vektör İndeksleme', desc: 'Qdrant (Metadata ile)' },
  { id: 9, title: 'Kullanıcı Sorgusu', desc: 'Nuxt/React Arayüzü' },
  { id: 10, title: 'Sorgu İşleme', desc: 'LlamaIndex' },
  { id: 11, title: 'Reranking', desc: 'Qwen3-Reranker-0.6B' },
  { id: 12, title: 'LLM Üretimi', desc: 'Qwen3.5-9B-Base' },
  { id: 13, title: 'Formatlama', desc: 'JSON / Markdown Tablosu' },
  { id: 14, title: 'Kullanıcıya Sunum', desc: 'Dashboard & Chatbot' }
]

const projectGoals = [
  "Veri Toplama: En az 5 farklı katılım bankasının resmî web sitesinden, en az 3 farklı ürün kategorisine ait 100’den fazla kampanya metnini toplamak.",
  "Bilgi Çıkarımı Başarımı: Çıkarılan kâr payı oranı, vade, masraf ve ödül bilgilerinde %90 üzeri doğruluk oranına ulaşmak.",
  "Dashboard Geliştirme: Kullanıcıların bankalar arası karşılaştırma yapabilmesine olanak sağlayan, filtreleme ve sıralama özellikleri bulunan interaktif bir dashboard’u tamamlamak.",
  "Chatbot İşlevselliği: Kullanıcıların doğal dilde sorduğu “A Bankası’nın konut oranı ne?” veya “En düşük kâr payı hangi bankada?” gibi sorulara cevap verebilen bir chatbot’u çalışır hale getirmek.",
  "On-Premise Uygunluk: Sistemin, harici servislere bağımlı olmadan, tek bir lokal sunucuda çalışabilir olduğunu doğrulamak."
]

const teamMembers = [
  {
    name: 'Fadime Nisa Baysal',
    role: 'Takım Kaptanı',
    university: 'Bilgisayar Mühendisliği 4. Sınıf - Giresun Üniversitesi',
    desc: 'Python, Java, JavaScript programlama dilleri ile SQL veritabanı yönetim sistemlerinde yetkindir. Daha önce yapay zekâ destekli görüntü işleme, full-stack web geliştirme ve makine öğrenmesi tabanlı zaman serisi analizi projelerinde aktif roller üstlenmiştir. FinAgent projesinde; katılım bankacılığı kampanya metinlerinin ön işlenmesi, doğal dil işleme mimarilerinin araştırılması, bilgi çıkarımı ve derin öğrenme modellerinin geliştirilmesi süreçlerinden sorumludur.'
  },
  {
    name: 'Mehmet Emre Ayçiçek',
    role: 'Backend & Sistem',
    university: 'Bilgisayar Mühendisliği 3. Sınıf - Sivas Cumhuriyet Üniversitesi',
    desc: 'Veritabanı sistemleri, Python programlama, algoritma geliştirme, yapay zekâ ve veri analizi alanlarında çalışmalar yürütmektedir. FinAgent projesinde; katılım bankalarının web sitelerinden otomatik veri toplama (web scraping), backend altyapısının kurulması, dashboard entegrasyonu ve sistem entegrasyon testlerinin yürütülmesinde aktif rol oynamaktadır.'
  },
  {
    name: 'Musa Ayçiçek',
    role: 'Veri Analitiği',
    university: 'Yönetim Bilişim Sistemleri Mezunu - Sivas Cumhuriyet Üniversitesi',
    desc: 'Veri işleme ve görüntü işleme alanlarında kendini geliştirmiştir. Python ve Kotlin dillerinde bilgi sahibidir. FinAgent projesinde; katılım bankacılığı kampanya metinlerinin ön işlenmesi, yapay zekâ modelleri için veri setlerinin düzenlenmesi ve bilgi çıkarımı süreçlerine uygun veri analitiği aşamalarının yürütülmesinden sorumludur.'
  },
  {
    name: 'Ahmet Salik Göksu',
    role: 'Yapay Zeka & Arayüz',
    university: 'Yapay Zeka Mühendisliği 2. Sınıf - Adana Alparslan Türkeş BTÜ',
    desc: 'Java eğitimi almış olup, C# ve Python programlama dilleri hakkında da bilgi sahibidir. FinAgent projesinde; kullanıcı dostu arayüzlerin geliştirilmesi, web arayüz bileşenlerinin kurgulanması ve ön yüz ile yapay zekâ model entegrasyonu süreçlerinde görev almaktadır.'
  }
]

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
          <p class="text-xl font-semibold tracking-wide">Yapay Zeka Hazırlanıyor...</p>
          <p class="text-sm text-blue-100/80">FinAgent sohbet arayüzüne yönlendiriliyorsunuz</p>
        </div>
      </div>
    </Transition>

    <!-- SKELETON LOADER -->
    <Transition name="fade">
      <SkeletonPage v-if="isLoading" class="absolute inset-0 z-50 bg-neutral-50 dark:bg-neutral-900" />
    </Transition>

    <div v-if="!isLoading" class="relative w-full transition-opacity duration-500 ease-in">

      <!-- 3D ARKA PLAN (parallax ile derinlik) -->
      <div data-parallax="0.12" class="fixed top-0 left-0 w-full h-screen pointer-events-none -z-10 opacity-30 dark:opacity-25">
        <ClientOnly>
          <CyberHead />
        </ClientOnly>
      </div>

      <div class="relative z-10 w-full">

        <!-- ================= BÖLÜM 1: HERO ================= -->
        <section id="hero" class="scroll-section snap-start snap-always min-h-screen flex flex-col px-6 relative pt-14">
          <div class="sticky top-14 w-full flex flex-wrap justify-center gap-3 pt-6 pb-2 z-30">
            <div v-for="item in navItems" :key="item.id" class="relative group">
              <button @click="scrollTo(item.id)" class="px-5 py-2 text-sm font-medium rounded-full bg-white/60 dark:bg-neutral-800/60 backdrop-blur-md border border-neutral-200/50 dark:border-neutral-700/50 text-neutral-600 dark:text-neutral-300 hover:border-blue-400 hover:text-blue-600 hover:-translate-y-0.5 transition-all shadow-sm focus:outline-none">{{ item.name }}</button>
            </div>
          </div>
          <div class="flex-1 flex flex-col items-center justify-center pb-24 z-20 w-full max-w-4xl mx-auto text-center">
            <h1 data-parallax="0.14" class="text-5xl md:text-7xl font-bold bg-clip-text text-transparent gradient-text pb-2 tracking-tight mb-12">Akıllı Finans Asistanı</h1>
            <div class="w-full pointer-events-auto animate-float-soft"><ChatPrompt /></div>
          </div>
        </section>

        <!-- ================= BÖLÜM 2: PROJE ÖZETİ ================= -->
        <section id="ozet" class="scroll-section snap-start snap-always min-h-screen flex items-center justify-center px-6 py-20 bg-neutral-900/80 backdrop-blur-lg">
          <div class="max-w-5xl w-full">
            <h2 class="anim-heading text-3xl font-bold text-center mb-12 text-white">Proje Özeti</h2>
            <div class="stagger-group w-full bg-white/5 border border-white/10 rounded-2xl overflow-hidden shadow-2xl flex flex-col">

              <div class="stagger-item grid grid-cols-1 md:grid-cols-[1fr,3fr] border-b border-white/10">
                <div class="p-6 bg-white/5 font-bold text-cyan-300 flex items-center">Proje Adı</div>
                <div class="p-6 text-white font-medium text-lg">FinAgent</div>
              </div>

              <div class="stagger-item grid grid-cols-1 md:grid-cols-[1fr,3fr] border-b border-white/10">
                <div class="p-6 bg-white/5 font-bold text-cyan-300 flex items-center">Projenin Amacı</div>
                <div class="p-6 text-neutral-300">Katılım bankalarının web sitelerinde yayınlanan doğal dildeki kampanya metinlerinden kâr payı oranı, vade, ücret, ödül gibi finansal bilgileri otomatik çıkararak, bu bilgileri standartlaştırıp dashboard ve chatbot aracılığıyla kullanıcılara sunmak.</div>
              </div>

              <div class="stagger-item grid grid-cols-1 md:grid-cols-[1fr,3fr] border-b border-white/10">
                <div class="p-6 bg-white/5 font-bold text-cyan-300 flex items-center">Problemin Tanımı</div>
                <div class="p-6 text-neutral-300">Katılım bankacılığında kampanya metinleri farklı formatlarda, farklı terminolojilerle yazılmakta ve manuel karşılaştırma zorlaşmaktadır. Bu durum banka çalışanlarının ve müşterilerin en avantajlı ürünü seçmesini geciktirmektedir.</div>
              </div>

              <div class="stagger-item grid grid-cols-1 md:grid-cols-[1fr,3fr]">
                <div class="p-6 bg-white/5 font-bold text-cyan-300 flex items-center">Çözüm Yaklaşımı</div>
                <div class="p-6 text-neutral-300">Web scraping ile veri toplama, Türkçe NLP modelleri ile metin analizi ve bilgi çıkarımı, çıkarılan verileri standart formata dönüştürüp karşılaştırılabilir hale getirme, sonuçları interaktif dashboard ve soru-cevap chatbotu ile kullanıcıya sunma.</div>
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
              <h2 class="anim-heading text-3xl font-bold mb-12 text-white drop-shadow-sm">Sistem Mimarisi Katmanları</h2>

              <div class="stagger-group flex flex-col gap-5 w-full max-w-4xl mx-auto">
                <div class="stagger-item p-5 bg-white/10 backdrop-blur-md border border-white/20 rounded-2xl shadow-lg relative overflow-hidden hover:bg-white/15 hover:-translate-y-1 transition-all duration-300">
                  <div class="absolute top-0 left-0 w-1 bg-cyan-300 h-full"></div>
                  <h3 class="text-sm uppercase tracking-widest text-cyan-200 mb-4 font-bold flex items-center justify-center gap-2">
                    <span class="w-6 h-6 rounded-full bg-cyan-500/30 flex items-center justify-center text-xs">4</span>
                    Kullanıcı Arayüzü
                  </h3>
                  <div class="flex flex-col sm:flex-row justify-center gap-4">
                    <div class="px-6 py-3 bg-white/10 border border-white/10 rounded-xl text-sm font-medium text-white w-full sm:w-1/2">
                      <span class="block text-cyan-300 font-bold mb-1">Nuxt Dashboard</span>
                      <span class="text-xs text-white/70">Filtreleme ve Karşılaştırma</span>
                    </div>
                    <div class="px-6 py-3 bg-white/10 border border-white/10 rounded-xl text-sm font-medium text-white w-full sm:w-1/2 flex items-center justify-center">
                      <span class="text-cyan-300 font-bold">React Chatbot</span>
                    </div>
                  </div>
                </div>

                <div class="stagger-item p-5 bg-white/10 backdrop-blur-md border border-white/20 rounded-2xl shadow-lg relative overflow-hidden hover:bg-white/15 hover:-translate-y-1 transition-all duration-300">
                  <div class="absolute top-0 left-0 w-1 bg-blue-300 h-full"></div>
                  <h3 class="text-sm uppercase tracking-widest text-blue-200 mb-4 font-bold flex items-center justify-center gap-2">
                    <span class="w-6 h-6 rounded-full bg-blue-500/30 flex items-center justify-center text-xs">3</span>
                    FastAPI Backend
                  </h3>
                  <div class="flex flex-col sm:flex-row justify-center gap-4">
                    <div class="px-6 py-3 bg-white/10 border border-white/10 rounded-xl text-sm font-medium text-white w-full sm:w-1/2">
                      <span class="block text-blue-300 font-bold mb-1">LlamaIndex RAG Motoru</span>
                      <span class="text-xs text-white/70">Retrieve, Rerank, Generate</span>
                    </div>
                    <div class="px-6 py-3 bg-white/10 border border-white/10 rounded-xl text-sm font-medium text-white w-full sm:w-1/2 flex items-center justify-center">
                      <span class="text-xs font-mono text-white/80">/compare, /ask, /search, /dashboard</span>
                    </div>
                  </div>
                </div>

                <div class="stagger-item p-5 bg-white/10 backdrop-blur-md border border-white/20 rounded-2xl shadow-lg relative overflow-hidden hover:bg-white/15 hover:-translate-y-1 transition-all duration-300">
                  <div class="absolute top-0 left-0 w-1 bg-indigo-300 h-full"></div>
                  <h3 class="text-sm uppercase tracking-widest text-indigo-200 mb-4 font-bold flex items-center justify-center gap-2">
                    <span class="w-6 h-6 rounded-full bg-indigo-500/30 flex items-center justify-center text-xs">2</span>
                    AI Servis Katmanı
                  </h3>
                  <div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4">
                    <div class="p-3 bg-white/10 border border-white/10 rounded-xl flex flex-col items-center text-center">
                      <span class="text-indigo-300 text-[10px] font-bold mb-1 uppercase tracking-wider">LLM</span>
                      <span class="text-xs text-white font-medium">Qwen/Qwen3.5-9B-Base</span>
                    </div>
                    <div class="p-3 bg-white/10 border border-white/10 rounded-xl flex flex-col items-center text-center">
                      <span class="text-indigo-300 text-[10px] font-bold mb-1 uppercase tracking-wider">NER Servisi</span>
                      <span class="text-xs text-white font-medium">ModernBERT-TR</span>
                    </div>
                    <div class="p-3 bg-white/10 border border-white/10 rounded-xl flex flex-col items-center text-center">
                      <span class="text-indigo-300 text-[10px] font-bold mb-1 uppercase tracking-wider">Embedding</span>
                      <span class="text-xs text-white font-medium">Qwen3-Embedding-0.6B</span>
                    </div>
                    <div class="p-3 bg-white/10 border border-white/10 rounded-xl flex flex-col items-center text-center">
                      <span class="text-indigo-300 text-[10px] font-bold mb-1 uppercase tracking-wider">Reranker</span>
                      <span class="text-xs text-white font-medium">Qwen3-Reranker-0.6B</span>
                    </div>
                  </div>
                </div>

                <div class="stagger-item p-5 bg-white/10 backdrop-blur-md border border-white/20 rounded-2xl shadow-lg relative overflow-hidden hover:bg-white/15 hover:-translate-y-1 transition-all duration-300">
                  <div class="absolute top-0 left-0 w-1 bg-teal-300 h-full"></div>
                  <h3 class="text-sm uppercase tracking-widest text-teal-200 mb-4 font-bold flex items-center justify-center gap-2">
                    <span class="w-6 h-6 rounded-full bg-teal-500/30 flex items-center justify-center text-xs">1</span>
                    Veri Katmanı
                  </h3>
                  <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div class="p-2 bg-white/10 border border-white/10 rounded-xl flex flex-col items-center text-center">
                      <span class="text-teal-300 text-sm font-bold">PostgreSQL</span>
                      <span class="text-[10px] text-white/70">İlişkisel DB</span>
                    </div>
                    <div class="p-2 bg-white/10 border border-white/10 rounded-xl flex flex-col items-center text-center">
                      <span class="text-teal-300 text-sm font-bold">Qdrant</span>
                      <span class="text-[10px] text-white/70">Vektör DB</span>
                    </div>
                    <div class="p-2 bg-white/10 border border-white/10 rounded-xl flex flex-col items-center text-center">
                      <span class="text-teal-300 text-sm font-bold">Redis</span>
                      <span class="text-[10px] text-white/70">Önbellek</span>
                    </div>
                    <div class="p-2 bg-white/10 border border-white/10 rounded-xl flex flex-col items-center text-center">
                      <span class="text-teal-300 text-sm font-bold">Web Scraper</span>
                      <span class="text-[10px] text-white/70">BS4 + Selenium</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </section>

          <!-- ================= BÖLÜM 4: SİSTEM AKIŞI ================= -->
          <section id="akis" class="scroll-section snap-start snap-always min-h-screen flex items-center justify-center px-6 py-20 relative">
            <div class="max-w-6xl w-full text-center">
              <h2 class="anim-heading text-3xl font-bold mb-12 text-white drop-shadow-sm">Sistem Akış Diyagramı</h2>

              <div class="stagger-group grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-4">
                <div v-for="step in flowSteps" :key="step.id" class="stagger-item p-4 bg-white/5 backdrop-blur-sm border border-white/10 rounded-xl flex flex-col items-center text-center relative group hover:bg-white/15 hover:-translate-y-1 transition-all duration-300">
                  <div class="w-8 h-8 rounded-full bg-cyan-500/20 text-cyan-300 border border-cyan-400/30 flex items-center justify-center font-bold text-sm mb-3 group-hover:scale-110 transition-transform">
                    {{ step.id }}
                  </div>
                  <h4 class="text-xs font-bold text-white mb-1 h-8 flex items-center justify-center">{{ step.title }}</h4>
                  <p class="text-[10px] text-white/70 leading-tight">{{ step.desc }}</p>
                  <div v-if="step.id !== 7 && step.id !== 14" class="hidden lg:block absolute top-1/2 -right-3 w-4 h-0.5 bg-white/20 -translate-y-1/2"></div>
                </div>
              </div>
            </div>
          </section>

          <!-- ================= BÖLÜM 5: PROJE HEDEFLERİ ================= -->
          <section id="hedefler" class="scroll-section snap-start snap-always min-h-screen flex items-center justify-center px-6 py-20 relative">
            <div class="max-w-4xl w-full">
              <h2 class="anim-heading text-3xl font-bold text-center mb-12 text-white drop-shadow-sm">Proje Hedefleri</h2>
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
            <h2 class="anim-heading text-3xl font-bold text-center mb-12 text-white">SmartData Takımı</h2>

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
              <p class="mt-6 text-center text-sm font-medium text-neutral-400 animate-pulse">Sohbete başlamak için aşağı kaydırmaya devam edin veya arama yapın.</p>
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