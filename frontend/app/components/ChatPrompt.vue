<script setup>
import { ref, computed } from 'vue'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()

const isHovered = ref(false)
const isFocused = ref(false)
const inputText = ref('')
const inputRef = ref(null)

// Kutu aktif mi?
const isActive = computed(() => isHovered.value || isFocused.value || inputText.value.length > 0)

// Kullanıcı kapalı kutuya tıkladığında input'a odaklansın
const focusInput = () => {
  if (inputRef.value) {
    inputRef.value.focus()
  }
}
</script>

<template>
  <!-- Kutu büyüyüp küçülürken etrafındaki elementleri itmemesi için sabit yükseklikli bir kapsayıcı -->
  <div class="w-full flex justify-center items-center h-20">
    
    <!-- Ana Oval Kutu: max-w-[280px]'den max-w-3xl'e yumuşak geçiş yapar -->
    <div 
      class="relative flex items-center bg-white dark:bg-[#1e1f22] border border-neutral-300 dark:border-neutral-700 rounded-full px-2 py-2 shadow-sm focus-within:ring-1 focus-within:ring-neutral-400 dark:focus-within:ring-neutral-500 transition-all duration-500 ease-out w-full cursor-text"
      :class="isActive ? 'max-w-3xl' : 'max-w-[320px]'"
      @mouseenter="isHovered = true"
      @mouseleave="isHovered = false"
      @click="focusInput"
    >
      
      <!-- 1. ORTADAKİ MAVİ YAZI ("Neye odaklanalım?") -->
      <!-- Sadece kutu kapalıyken görünür, açılırken küçülerek kaybolur -->
      <div 
        class="absolute inset-0 flex items-center justify-center pointer-events-none transition-all duration-500"
        :class="isActive ? 'opacity-0 scale-90' : 'opacity-100 scale-100'"
      >
        <span class="text-blue-600 dark:text-blue-400 font-medium text-lg tracking-wide">
          {{ t('focusQuestion') }}
        </span>
      </div>

      <!-- 2. ANİMASYONLU YER TUTUCU ("FinAgent'a sorun") -->
      <!-- Kutu açıldığında sağdan sola doğru kayarak (translate) ve belirek gelir -->
      <div 
        class="absolute left-6 pointer-events-none transition-all duration-500 delay-75"
        :class="(isActive && !inputText) ? 'opacity-100 translate-x-0' : 'opacity-0 translate-x-4'"
      >
        <span class="text-neutral-500 text-base">{{ t('askGemini') }}</span>
      </div>

      <!-- 3. GERÇEK GİRDİ ALANI (Input) -->
      <input 
        ref="inputRef"
        type="text" 
        v-model="inputText"
        @focus="isFocused = true"
        @blur="isFocused = false"
        class="flex-1 bg-transparent border-none outline-none text-neutral-800 dark:text-neutral-100 px-4 py-2 text-base z-10 transition-opacity duration-300"
        :class="isActive ? 'opacity-100' : 'opacity-0 pointer-events-none'"
      >


      <!-- 4. GÖNDER BUTONU & Tooltip -->
      <!-- Kutu kapalıyken gizlidir, açıldığında görünür -->
      <div 
        class="relative group flex items-center pl-2 pr-1 z-20 transition-all duration-500"
        :class="isActive ? 'opacity-100 scale-100' : 'opacity-0 scale-50 pointer-events-none'"
      >
        <button class="p-2.5 bg-neutral-100 hover:bg-blue-600 text-neutral-500 hover:text-white dark:bg-[#2b2d31] dark:text-neutral-400 dark:hover:bg-blue-600 dark:hover:text-white rounded-full transition-colors flex items-center justify-center focus:outline-none">
          <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 -translate-y-[1px] translate-x-[1px]" viewBox="0 0 20 20" fill="currentColor">
            <path d="M10.894 2.553a1 1 0 00-1.788 0l-7 14a1 1 0 001.169 1.409l5-1.429A1 1 0 009 15.571V11a1 1 0 112 0v4.571a1 1 0 00.725.962l5 1.428a1 1 0 001.17-1.408l-7-14z" />
          </svg>
        </button>
        <!-- Gönder Tooltip -->
        <div class="absolute bottom-full mb-3 right-0 px-2 py-1 text-xs font-medium bg-neutral-800 text-white dark:bg-neutral-100 dark:text-neutral-900 rounded opacity-0 group-hover:opacity-100 transition-all pointer-events-none whitespace-nowrap shadow-lg">
          {{ t('send', 'Gönder') }}
        </div>
      </div>

    </div>
  </div>
</template>