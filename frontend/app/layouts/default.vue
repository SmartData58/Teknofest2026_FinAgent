<script setup>
import { ref, watch, onMounted, onUnmounted, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute } from 'vue-router'

const { locale, setLocale, t } = useI18n()
const colorMode = useColorMode()
const route = useRoute()

// viewMode artık Nuxt'un paylaşımlı global state'i (useState) ile tutuluyor.
// dashboard.vue layout'u da AYNI 'globalViewMode' anahtarını kullanıyor,
// böylece hangi layout aktifse ordan yapılan değişiklik diğerine de yansıyor.
// (Önceden burada yerel bir ref() vardı; bu yüzden default layout'ta yapılan
// seçim, dashboard layout'una hiç ulaşmıyordu ve sayfa boş/senkronsuz kalıyordu.)
const viewMode = useState('globalViewMode', () => 'musteri')

const toggleTheme = () => {
  colorMode.preference = colorMode.value === 'dark' ? 'light' : 'dark'
}

const toggleLanguage = () => {
  const nextLang = locale.value === 'tr' ? 'en' : 'tr'
  setLocale(nextLang)
  try {
    if (process.client) localStorage.setItem('language', nextLang)
  } catch (e) {}
}

// Mobil cihazlar için menü açma kapama
const isMobileMenuOpen = ref(false)

const setViewMode = (mode) => {
  viewMode.value = mode
  try {
    if (process.client) localStorage.setItem('viewMode', mode)
  } catch (e) {}
}

// Üst barın görünürlük durumu
const isHeaderVisible = ref(true)
let scrollerElement = null
let lastScrollTop = 0

const handleScroll = () => {
  if (!scrollerElement) return
  const currentScrollTop = scrollerElement.scrollTop

  if (currentScrollTop < 60) {
    isHeaderVisible.value = true
  } else if (currentScrollTop > lastScrollTop) {
    isHeaderVisible.value = false
  } else {
    isHeaderVisible.value = true
  }
  lastScrollTop = currentScrollTop <= 0 ? 0 : currentScrollTop
}

onMounted(() => {
  try {
    if (process.client) {
      const savedMode = localStorage.getItem('viewMode')
      if (savedMode) viewMode.value = savedMode

      const savedLang = localStorage.getItem('language')
      if (savedLang) setLocale(savedLang)
    }
  } catch (e) {}

  scrollerElement = document.getElementById('main-scroller')
  if (scrollerElement) {
    scrollerElement.addEventListener('scroll', handleScroll, { passive: true })
  }
})

onUnmounted(() => {
  if (scrollerElement) {
    scrollerElement.removeEventListener('scroll', handleScroll)
  }
})

// Menü varsayılan olarak kapalı
const isSidebarOpen = ref(false)

// Sayfa yolu her değiştiğinde menüyü otomatik kapat ve header'ı sıfırla
watch(() => route.path, () => {
  isSidebarOpen.value = false
  isMobileMenuOpen.value = false
  isHeaderVisible.value = true
})

const menuItems = computed(() => [
  {
    name: t('menu.home', 'Ana Sayfa'),
    path: '/',
    icon: '<svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="m2.25 12 8.954-8.955c.44-.439 1.152-.439 1.591 0L21.75 12M4.5 9.75v10.125c0 .621.504 1.125 1.125 1.125H9.75v-4.875c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125V21h4.125c.621 0 1.125-.504 1.125-1.125V9.75M8.25 21h8.25" /></svg>'
  },
  {
    name: t('menu.dashboard', 'Pazar Analizi'),
    path: '/dashboard',
    icon: '<svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M11 3.055A9.001 9.001 0 1020.945 13H11V3.055z" /><path stroke-linecap="round" stroke-linejoin="round" d="M20.488 9H15V3.512A9.025 9.025 0 0120.488 9z" /></svg>'
  },
  {
    name: t('menu.comparison', 'Karşılaştırma'),
    path: '/comparison',
    icon: '<svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M7.5 21 3 16.5m0 0L7.5 12M3 16.5h13.5m0-13.5L21 7.5m0 0L16.5 12M21 7.5H7.5" /></svg>'
  },
  {
    name: t('menu.financing', 'Finansman Karşılaştırmaları'),
    path: '/finansman',
    icon: '<svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M12 6v12m-3-2.818.879.659c1.171.879 3.07.879 4.242 0 1.172-.879 1.172-2.303 0-3.182C13.536 12.219 12.768 12 12 12c-.725 0-1.45-.22-2.003-.659-1.106-.879-1.106-2.303 0-3.182s2.9-.879 4.006 0l.415.33M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" /></svg>'
  },
  {
    name: t('menu.katilim_hesap', 'Katılım Hesabı Karşılaştırmaları'),
    path: '/katilim-hesap',
    icon: '<svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M2.25 18.75a60.07 60.07 0 0 1 15.797 2.101c.727.198 1.453-.342 1.453-1.096V18.75M3.75 4.5v.75A.75.75 0 0 1 3 6H2.25m0 0v8.25m0-8.25A2.25 2.25 0 0 1 4.5 3h15A2.25 2.25 0 0 1 21.75 5.25m0 0V18a2.25 2.25 0 0 1-2.25 2.25m0 0H3.75m18-15A2.25 2.25 0 0 0 19.5 3m0 0h-15m15 0a2.25 2.25 0 0 1 2.25 2.25v12.75M9 9.75h6m-6 3h6m-3-6v9" /></svg>'
  },
  {
    name: t('menu.campaigns', 'Tüm Kampanyalar'),
    path: '/campaigns',
    icon: '<svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M9 12.75 11.25 15 15 9.75M21 12c0 1.268-.63 2.39-1.593 3.068a3.745 3.745 0 0 1-1.043 3.296 3.745 3.745 0 0 1-3.296 1.043A3.745 3.745 0 0 1 12 21c-1.268 0-2.39-.63-3.068-1.593a3.746 3.746 0 0 1-3.296-1.043 3.745 3.745 0 0 1-1.043-3.296A3.745 3.745 0 0 1 3 12c0-1.268.63-2.39 1.593-3.068a3.745 3.745 0 0 1 1.043-3.296 3.746 3.746 0 0 1 3.296-1.043A3.746 3.746 0 0 1 12 3c1.268 0 2.39.63 3.068 1.593a3.746 3.746 0 0 1 3.296 1.043 3.746 3.746 0 0 1 1.043 3.296A3.745 3.745 0 0 1 21 12Z" /></svg>'
  },
  {
    name: t('menu.chat', 'AI Asistan'),
    path: '/chat',
    icon: '<svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 0 1-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" /></svg>'
  }
])
</script>

<template>
  <div class="flex h-screen w-full bg-neutral-50 dark:bg-neutral-900 text-neutral-800 dark:text-neutral-100 font-sans overflow-hidden">

    <Transition name="backdrop">
      <div
        v-if="isSidebarOpen"
        @click="isSidebarOpen = false"
        class="fixed inset-0 bg-neutral-900/40 backdrop-blur-sm z-40"
      ></div>
    </Transition>

    <aside :class="isSidebarOpen ? 'w-64 border-r' : 'w-0 border-none'" class="h-full transition-all duration-300 ease-in-out shrink-0 overflow-hidden bg-white dark:bg-neutral-800 border-neutral-200 dark:border-neutral-700 z-50 shadow-xl flex flex-col">
      <div class="flex-1 flex flex-col min-h-0">
        <div class="h-14 flex items-center px-5 border-b border-neutral-200 dark:border-neutral-700 shrink-0 gap-2.5">
          <img src="/logo.svg" alt="FinAgent Logo" class="w-6 h-6 object-contain" />
          <span class="text-xl font-bold tracking-wider brand-text">{{ t('brand', 'FinAgent') }}</span>
        </div>

        <nav class="p-4 space-y-2 overflow-y-auto custom-scrollbar flex-1">
          <NuxtLink
            v-for="(item, index) in menuItems"
            :key="item.path"
            :to="item.path"
            :style="{ transitionDelay: isSidebarOpen ? `${120 + index * 40}ms` : '0ms' }"
            :class="isSidebarOpen ? 'opacity-100 translate-x-0' : 'opacity-0 -translate-x-4'"
            class="menu-link group flex items-center space-x-3 px-4 py-2.5 rounded-lg transition-all duration-300 relative overflow-hidden hover:bg-neutral-100 dark:hover:bg-neutral-700/50"
            active-class="bg-blue-50 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 font-medium"
          >
            <span class="absolute left-0 top-1/2 -translate-y-1/2 h-0 w-1 rounded-r bg-blue-500 transition-all duration-300 group-hover:h-6 indicator"></span>
            <div v-html="item.icon" class="flex-shrink-0 text-current transition-transform duration-300 group-hover:scale-110 group-hover:rotate-3"></div>
            <span class="text-sm font-medium transition-transform duration-300 group-hover:translate-x-0.5">{{ item.name }}</span>
          </NuxtLink>
        </nav>
      </div>
    </aside>

    <div id="main-scroller" class="flex-1 h-full overflow-y-auto relative">

      <header
        :class="isHeaderVisible ? 'translate-y-0 opacity-100' : '-translate-y-[120%] opacity-0 pointer-events-none'"
        class="sticky top-0 w-full h-14 bg-transparent flex items-center justify-between px-3 sm:px-6 z-40 transition-all duration-500 ease-in-out -mb-14"
      >
        <div class="flex items-center space-x-2 sm:space-x-5 pointer-events-auto shrink-0">
          <div class="relative group flex items-center">
            <button @click="isSidebarOpen = !isSidebarOpen" :class="{ 'is-open': isSidebarOpen }" class="menu-btn p-2 -ml-1 sm:-ml-2 rounded-lg hover:bg-neutral-200/80 dark:hover:bg-neutral-700/80 bg-white/40 dark:bg-neutral-800/40 backdrop-blur-md transition-colors focus:outline-none text-neutral-600 dark:text-neutral-300 shadow-sm border border-neutral-200/50 dark:border-neutral-700/50">
              <span class="burger">
                <span class="burger-line"></span>
                <span class="burger-line"></span>
                <span class="burger-line"></span>
              </span>
            </button>
            <div class="absolute top-full mt-2 left-0 px-2 py-1 text-xs font-medium bg-neutral-800 text-white dark:bg-neutral-100 dark:text-neutral-900 rounded opacity-0 group-hover:opacity-100 transition-all pointer-events-none whitespace-nowrap shadow-lg">
              {{ t('header.menu', 'Menü') }}
            </div>
          </div>

          <div class="relative group flex items-center">
            <img src="/teknofest.svg" alt="Teknofest" class="h-5 sm:h-6 w-auto object-contain opacity-90 hover:opacity-100 hover:scale-110 transition-all duration-300 cursor-pointer" />
            <div class="absolute top-full mt-2 left-1/2 -translate-x-1/2 px-2 py-1 text-xs font-medium bg-neutral-800 text-white dark:bg-neutral-100 dark:text-neutral-900 rounded opacity-0 group-hover:opacity-100 transition-all pointer-events-none whitespace-nowrap shadow-lg">Teknofest</div>
          </div>

          <div class="relative group flex items-center">
            <div class="opacity-90 hover:opacity-100 hover:scale-110 transition-all duration-300 cursor-pointer">
              <img src="/biquery.svg" alt="BiQuery" class="h-3.5 sm:h-4 w-auto object-contain block dark:hidden" />
              <img src="/biqueryblack.svg" alt="BiQuery" class="h-3.5 sm:h-4 w-auto object-contain hidden dark:block" />
            </div>
            <div class="absolute top-full mt-2 left-1/2 -translate-x-1/2 px-2 py-1 text-xs font-medium bg-neutral-800 text-white dark:bg-neutral-100 dark:text-neutral-900 rounded opacity-0 group-hover:opacity-100 transition-all pointer-events-none whitespace-nowrap shadow-lg">BiQuery</div>
          </div>
        </div>

        <div class="flex items-center space-x-1.5 sm:space-x-4 pointer-events-auto">

          <!-- Görünüm Modu Toggle (Müşteri / Banka Çalışanı) - Mobil ve Masaüstü Uyumlu -->
          <div class="flex p-0.5 sm:p-1 rounded-lg border border-neutral-300/50 dark:border-neutral-600/50 bg-white/40 dark:bg-neutral-800/40 backdrop-blur-md shadow-sm">
            <div class="relative group flex items-center">
              <button @click="setViewMode('musteri')" :class="viewMode === 'musteri' ? 'bg-white dark:bg-neutral-700 shadow-sm text-blue-600 dark:text-cyan-400' : 'text-neutral-600 dark:text-neutral-300 hover:text-neutral-900 dark:hover:text-white'" class="px-2 sm:px-3 py-1 sm:py-1.5 text-[11px] sm:text-xs font-bold rounded-md transition-all flex items-center gap-1 sm:gap-1.5 whitespace-nowrap">
                <svg class="w-3.5 h-3.5 opacity-70 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"/></svg>
                <span>{{ t('header.customer', 'Müşteri') }}</span>
              </button>
              <div class="absolute top-full mt-2 left-1/2 -translate-x-1/2 px-2 py-1 text-xs font-medium bg-neutral-800 text-white dark:bg-neutral-100 dark:text-neutral-900 rounded opacity-0 group-hover:opacity-100 transition-all pointer-events-none whitespace-nowrap shadow-lg z-50">
                {{ t('header.customer_info', 'Yalnızca genel kampanyaları gösterir') }}
              </div>
            </div>

            <div class="relative group flex items-center">
              <button @click="setViewMode('bankaci')" :class="viewMode === 'bankaci' ? 'bg-white dark:bg-neutral-700 shadow-sm text-blue-600 dark:text-cyan-400' : 'text-neutral-600 dark:text-neutral-300 hover:text-neutral-900 dark:hover:text-white'" class="px-2 sm:px-3 py-1 sm:py-1.5 text-[11px] sm:text-xs font-bold rounded-md transition-all flex items-center gap-1 sm:gap-1.5 whitespace-nowrap">
                <svg class="w-3.5 h-3.5 opacity-70 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 13.255A23.931 23.931 0 0112 15c-3.183 0-6.22-.62-9-1.745M16 6V4a2 2 0 00-2-2h-4a2 2 0 00-2 2v2m4 6h.01M5 20h14a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"/></svg>
                <span class="hidden sm:inline">{{ t('header.bank_employee', 'Banka Çalışanı') }}</span>
                <span class="sm:hidden">{{ t('header.bank_short', 'Banka') }}</span>
              </button>
              <div class="absolute top-full mt-2 left-1/2 -translate-x-1/2 px-2 py-1 text-xs font-medium bg-neutral-800 text-white dark:bg-neutral-100 dark:text-neutral-900 rounded opacity-0 group-hover:opacity-100 transition-all pointer-events-none whitespace-nowrap shadow-lg z-50">
                {{ t('header.bank_employee_info', 'Kurum içi ve gizli kampanyaları da içerir') }}
              </div>
            </div>
          </div>

          <div class="flex items-center space-x-1.5 sm:space-x-2 border-l border-neutral-300/50 dark:border-neutral-600/50 pl-2 sm:pl-4">
            <div class="relative group flex items-center">
              <button @click="toggleLanguage" class="px-2 sm:px-2.5 py-1 rounded-md border border-neutral-300/50 dark:border-neutral-600/50 text-[11px] sm:text-xs font-bold text-neutral-600 dark:text-neutral-300 hover:bg-neutral-200/80 dark:hover:bg-neutral-700/80 hover:-translate-y-0.5 bg-white/40 dark:bg-neutral-800/40 backdrop-blur-md transition-all duration-300 shadow-sm active:scale-95">
                <Transition name="lang" mode="out-in">
                  <span :key="locale">{{ locale.toUpperCase() }}</span>
                </Transition>
              </button>
              <div class="absolute top-full mt-2 left-1/2 -translate-x-1/2 px-2 py-1 text-xs font-medium bg-neutral-800 text-white dark:bg-neutral-100 dark:text-neutral-900 rounded opacity-0 group-hover:opacity-100 transition-all pointer-events-none whitespace-nowrap shadow-lg z-50">
                {{ t('header.change_language', 'Dil Değiştir') }}
              </div>
            </div>

            <div class="relative group flex items-center">
              <button @click="toggleTheme" class="p-1 sm:p-1.5 rounded-lg border border-neutral-300/50 dark:border-neutral-600/50 hover:bg-neutral-200/80 dark:hover:bg-neutral-700/80 hover:-translate-y-0.5 text-neutral-600 dark:text-neutral-300 bg-white/40 dark:bg-neutral-800/40 backdrop-blur-md transition-all duration-300 shadow-sm active:scale-95 overflow-hidden">
                <Transition name="theme" mode="out-in">
                  <svg v-if="colorMode.value === 'dark'" key="sun" xmlns="http://www.w3.org/2000/svg" class="h-3.5 sm:h-4 w-3.5 sm:w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" /></svg>
                  <svg v-else key="moon" xmlns="http://www.w3.org/2000/svg" class="h-3.5 sm:h-4 w-3.5 sm:w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" /></svg>
                </Transition>
              </button>
              <div class="absolute top-full mt-2 right-0 px-2 py-1 text-xs font-medium bg-neutral-800 text-white dark:bg-neutral-100 dark:text-neutral-900 rounded opacity-0 group-hover:opacity-100 transition-all pointer-events-none whitespace-nowrap shadow-lg z-50">
                {{ t('header.change_theme', 'Tema Değiştir') }}
              </div>
            </div>
          </div>
        </div>
      </header>

      <main class="w-full min-h-full">
        <slot />
      </main>

    </div>
  </div>
</template>

<style scoped>
.router-link-active { transition: all 0.2s ease-in-out; }

.brand-text {
  background-image: linear-gradient(90deg, #2563eb, #06b6d4, #6366f1, #2563eb);
  background-size: 300% 100%;
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
  animation: brandShift 6s ease infinite;
}
@keyframes brandShift {
  0% { background-position: 0% 50%; }
  50% { background-position: 100% 50%; }
  100% { background-position: 0% 50%; }
}

.menu-link.router-link-active .indicator { height: 1.5rem; }

.backdrop-enter-active, .backdrop-leave-active { transition: opacity 0.3s ease; }
.backdrop-enter-from, .backdrop-leave-to { opacity: 0; }

.burger {
  position: relative;
  display: block;
  width: 20px;
  height: 14px;
}
.burger-line {
  position: absolute;
  left: 0;
  width: 100%;
  height: 2px;
  border-radius: 2px;
  background: currentColor;
  transition: transform 0.3s ease, opacity 0.25s ease, top 0.3s ease;
}
.burger-line:nth-child(1) { top: 0; }
.burger-line:nth-child(2) { top: 6px; }
.burger-line:nth-child(3) { top: 12px; }
.menu-btn.is-open .burger-line:nth-child(1) { top: 6px; transform: rotate(45deg); }
.menu-btn.is-open .burger-line:nth-child(2) { opacity: 0; transform: scaleX(0); }
.menu-btn.is-open .burger-line:nth-child(3) { top: 6px; transform: rotate(-45deg); }

.theme-enter-active, .theme-leave-active { transition: transform 0.35s ease, opacity 0.35s ease; }
.theme-enter-from { opacity: 0; transform: rotate(-90deg) scale(0.5); }
.theme-leave-to { opacity: 0; transform: rotate(90deg) scale(0.5); }

.lang-enter-active, .lang-leave-active { transition: transform 0.25s ease, opacity 0.25s ease; }
.lang-enter-from { opacity: 0; transform: translateY(6px); }
.lang-leave-to { opacity: 0; transform: translateY(-6px); }

.custom-scrollbar::-webkit-scrollbar { width: 4px; height: 4px; }
.custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
.custom-scrollbar::-webkit-scrollbar-thumb { background: #cbd5e1; border-radius: 10px; }
:global(.dark) .custom-scrollbar::-webkit-scrollbar-thumb { background: #475569; }
.custom-scrollbar::-webkit-scrollbar-thumb:hover { background: #94a3b8; }
</style>