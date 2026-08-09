<script setup>
import { ref, watch, onMounted, onUnmounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute } from 'vue-router'

const { locale, setLocale, t } = useI18n()
const colorMode = useColorMode()
const route = useRoute()

const toggleTheme = () => {
  colorMode.preference = colorMode.value === 'dark' ? 'light' : 'dark'
}
const toggleLanguage = () => {
  const nextLang = locale.value === 'tr' ? 'en' : 'tr'
  setLocale(nextLang)
}

// Menü varsayılan olarak kapalı
const isSidebarOpen = ref(false)

// Üst barın görünürlük durumu
const isHeaderVisible = ref(true)
let scrollerElement = null
let lastScrollTop = 0

// Akıllı Kaydırma (Smart Scroll) takibi
const handleScroll = () => {
  if (!scrollerElement) return
  const currentScrollTop = scrollerElement.scrollTop

  // Sayfanın en üstündeyken her zaman göster
  if (currentScrollTop < 60) {
    isHeaderVisible.value = true
  } 
  // Aşağı kaydırılıyorsa menüyü gizle
  else if (currentScrollTop > lastScrollTop) {
    isHeaderVisible.value = false
  } 
  // Yukarı kaydırılıyorsa menüyü zarifçe geri getir
  else {
    isHeaderVisible.value = true
  }

  // Son konumu güncelle (Safari/iOS'teki bounce efektine karşı 0'da tut)
  lastScrollTop = currentScrollTop <= 0 ? 0 : currentScrollTop
}

onMounted(() => {
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

// Sayfa yolu (URL) her değiştiğinde menüyü otomatik kapat ve header'ı sıfırla
watch(() => route.path, () => {
  isSidebarOpen.value = false
  isHeaderVisible.value = true
})

const menuItems = [
  { 
    name: 'menu.app', 
    path: '/', 
    icon: '<svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z" /></svg>' 
  },
  { 
    name: 'menu.overview', 
    path: '/dashboard', 
    icon: '<svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M11 3.055A9.001 9.001 0 1020.945 13H11V3.055z" /><path stroke-linecap="round" stroke-linejoin="round" d="M20.488 9H15V3.512A9.025 9.025 0 0120.488 9z" /></svg>' 
  },
  { 
    name: 'menu.campaigns', 
    path: '/campaigns', 
    icon: '<svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 002-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" /></svg>' 
  },
  { 
    name: 'menu.comparison', 
    path: '/comparison', 
    icon: '<svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" /></svg>' 
  },
  { 
    name: 'menu.chatbot', 
    path: '/chat', 
    icon: '<svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" /></svg>' 
  }
]
</script>

<template>
  <div class="flex h-screen w-full bg-neutral-50 dark:bg-neutral-900 text-neutral-800 dark:text-neutral-100 font-sans overflow-hidden">

    <!-- ARKA PLAN KARARTMASI -->
    <Transition name="backdrop">
      <div
        v-if="isSidebarOpen"
        @click="isSidebarOpen = false"
        class="fixed inset-0 bg-neutral-900/40 backdrop-blur-sm z-40"
      ></div>
    </Transition>

    <!-- SİDEBAR -->
    <aside :class="isSidebarOpen ? 'w-64 border-r' : 'w-0 border-none'" class="h-full transition-all duration-300 ease-in-out shrink-0 overflow-hidden bg-white dark:bg-neutral-800 border-neutral-200 dark:border-neutral-700 z-50 shadow-xl">
      <div class="w-64 h-full flex flex-col justify-between">
        <div>
          <div class="h-14 flex items-center px-6 border-b border-neutral-200 dark:border-neutral-700">
            <span class="text-xl font-bold tracking-wider brand-text">{{ t('brand') }}</span>
          </div>
          <nav class="p-4 space-y-2">
            <NuxtLink
              v-for="(item, index) in menuItems"
              :key="item.path"
              :to="item.path"
              :style="{ transitionDelay: isSidebarOpen ? `${120 + index * 70}ms` : '0ms' }"
              :class="isSidebarOpen ? 'opacity-100 translate-x-0' : 'opacity-0 -translate-x-4'"
              class="menu-link group flex items-center space-x-3 px-4 py-2.5 rounded-lg transition-all duration-300 relative overflow-hidden hover:bg-neutral-100 dark:hover:bg-neutral-700/50"
              active-class="bg-blue-50 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 font-medium"
            >
              <span class="absolute left-0 top-1/2 -translate-y-1/2 h-0 w-1 rounded-r bg-blue-500 transition-all duration-300 group-hover:h-6 indicator"></span>
              <div v-html="item.icon" class="flex-shrink-0 text-current transition-transform duration-300 group-hover:scale-110 group-hover:rotate-3"></div>
              <span class="text-sm font-medium transition-transform duration-300 group-hover:translate-x-0.5">{{ t(item.name) }}</span>
            </NuxtLink>
          </nav>
        </div>

        <div class="p-4 border-t border-neutral-200 dark:border-neutral-700 bg-neutral-50 dark:bg-neutral-850">
          <div class="text-xs text-center text-neutral-500 dark:text-neutral-400 font-medium">
            {{ t('team') }}
          </div>
        </div>
      </div>
    </aside>

    <!-- ANA İÇERİK ALANI -->
    <div id="main-scroller" class="flex-1 h-full overflow-y-auto relative">

      <!-- Üst Menü Barı (Header) - SÜRESİ UZATILDI VE YUMUŞATILDI -->
      <header 
        :class="isHeaderVisible ? 'translate-y-0 opacity-100' : '-translate-y-[120%] opacity-0 pointer-events-none'"
        class="sticky top-0 w-full h-14 bg-transparent flex items-center justify-between px-6 z-40 transition-all duration-500 ease-in-out -mb-14"
      >
        <!-- Sol: Menü Butonu ve Logolar -->
        <div class="flex items-center space-x-5 pointer-events-auto">
          <!-- Menü Butonu -->
          <div class="relative group flex items-center">
            <button @click="isSidebarOpen = !isSidebarOpen" :class="{ 'is-open': isSidebarOpen }" class="menu-btn p-2 -ml-2 rounded-lg hover:bg-neutral-200/80 dark:hover:bg-neutral-700/80 bg-white/40 dark:bg-neutral-800/40 backdrop-blur-md transition-colors focus:outline-none text-neutral-600 dark:text-neutral-300 shadow-sm border border-neutral-200/50 dark:border-neutral-700/50">
              <span class="burger">
                <span class="burger-line"></span>
                <span class="burger-line"></span>
                <span class="burger-line"></span>
              </span>
            </button>
            <div class="absolute top-full mt-2 left-0 px-2 py-1 text-xs font-medium bg-neutral-800 text-white dark:bg-neutral-100 dark:text-neutral-900 rounded opacity-0 group-hover:opacity-100 transition-all pointer-events-none whitespace-nowrap shadow-lg">Menü</div>
          </div>

          <!-- Teknofest Logosu -->
          <div class="relative group flex items-center">
            <img src="/teknofest.svg" alt="Teknofest" class="h-6 w-auto object-contain opacity-90 hover:opacity-100 hover:scale-110 transition-all duration-300 cursor-pointer" />
            <div class="absolute top-full mt-2 left-1/2 -translate-x-1/2 px-2 py-1 text-xs font-medium bg-neutral-800 text-white dark:bg-neutral-100 dark:text-neutral-900 rounded opacity-0 group-hover:opacity-100 transition-all pointer-events-none whitespace-nowrap shadow-lg">Teknofest</div>
          </div>

          <!-- BiQuery Logosu -->
          <div class="relative group flex items-center">
            <div class="opacity-90 hover:opacity-100 hover:scale-110 transition-all duration-300 cursor-pointer">
              <img src="/biquery.svg" alt="BiQuery" class="h-4 w-auto object-contain block dark:hidden" />
              <img src="/biqueryblack.svg" alt="BiQuery" class="h-4 w-auto object-contain hidden dark:block" />
            </div>
            <div class="absolute top-full mt-2 left-1/2 -translate-x-1/2 px-2 py-1 text-xs font-medium bg-neutral-800 text-white dark:bg-neutral-100 dark:text-neutral-900 rounded opacity-0 group-hover:opacity-100 transition-all pointer-events-none whitespace-nowrap shadow-lg">BiQuery</div>
          </div>
        </div>

        <!-- Sağ: Dil/Tema Butonları -->
        <div class="flex items-center space-x-4 pointer-events-auto">
          <!-- Dil Değiştir -->
          <div class="relative group flex items-center">
            <button @click="toggleLanguage" class="px-2.5 py-1 rounded-md border border-neutral-300/50 dark:border-neutral-600/50 text-xs font-bold text-neutral-600 dark:text-neutral-300 hover:bg-neutral-200/80 dark:hover:bg-neutral-700/80 hover:-translate-y-0.5 bg-white/40 dark:bg-neutral-800/40 backdrop-blur-md transition-all duration-300 shadow-sm active:scale-95">
              <Transition name="lang" mode="out-in">
                <span :key="locale">{{ locale.toUpperCase() }}</span>
              </Transition>
            </button>
            <div class="absolute top-full mt-2 left-1/2 -translate-x-1/2 px-2 py-1 text-xs font-medium bg-neutral-800 text-white dark:bg-neutral-100 dark:text-neutral-900 rounded opacity-0 group-hover:opacity-100 transition-all pointer-events-none whitespace-nowrap shadow-lg">Dil Değiştir</div>
          </div>

          <!-- Tema Değiştir -->
          <div class="relative group flex items-center">
            <button @click="toggleTheme" class="p-1.5 rounded-lg border border-neutral-300/50 dark:border-neutral-600/50 hover:bg-neutral-200/80 dark:hover:bg-neutral-700/80 hover:-translate-y-0.5 text-neutral-600 dark:text-neutral-300 bg-white/40 dark:bg-neutral-800/40 backdrop-blur-md transition-all duration-300 shadow-sm active:scale-95 overflow-hidden">
              <Transition name="theme" mode="out-in">
                <svg v-if="colorMode.value === 'dark'" key="sun" xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" /></svg>
                <svg v-else key="moon" xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" /></svg>
              </Transition>
            </button>
            <div class="absolute top-full mt-2 right-0 px-2 py-1 text-xs font-medium bg-neutral-800 text-white dark:bg-neutral-100 dark:text-neutral-900 rounded opacity-0 group-hover:opacity-100 transition-all pointer-events-none whitespace-nowrap shadow-lg">Tema Değiştir</div>
          </div>
        </div>
      </header>

      <!-- İÇERİK -->
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
</style>