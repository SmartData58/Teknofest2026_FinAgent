<script setup>
import { ref, computed } from 'vue'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()

const isHovered = ref(false)
const isFocused = ref(false)
const inputText = ref('')
const inputRef = ref(null)

const chatStore = useChatStore()
const router = useRouter()

const isNavigating = ref(false)

// 🚀 TOKAT 1: Dosya State'leri Eklendi!
const fileInput = ref(null)
const selectedFiles = ref([])
const maxFiles = 3

// 🚀 TOKAT 2: Kutu kapanmasın diye selectedFiles.length koşulu eklendi!
const isActive = computed(() => isHovered.value || isFocused.value || inputText.value.length > 0 || isNavigating.value || selectedFiles.value.length > 0)

const focusInput = () => {
  if (inputRef.value) {
    inputRef.value.focus()
  }
}

// Dosya seçme diyaloğunu tetikler
const triggerFileInput = () => {
  if (fileInput.value) {
    fileInput.value.click()
  }
}

// Dosyalar seçildiğinde diziye ekler
const handleFileSelect = (event) => {
  const files = Array.from(event.target.files)
  if (selectedFiles.value.length + files.length > maxFiles) {
    alert(`En fazla ${maxFiles} dosya yükleyebilirsiniz.`)
    event.target.value = '' 
    return
  }
  selectedFiles.value.push(...files)
  event.target.value = '' 
}

// Seçilen dosyayı listeden çıkarır
const removeFile = (index) => {
  selectedFiles.value.splice(index, 1)
  if (selectedFiles.value.length === 0 && fileInput.value) fileInput.value.value = ''
}

const goToChat = () => {
  if (isNavigating.value || (!inputText.value.trim() && selectedFiles.value.length === 0)) return
  
  isNavigating.value = true

  // 🚀 TOKAT 1: Verileri Pinia deposuna teslim et!
  chatStore.setChatData(inputText.value.trim(), selectedFiles.value)

  setTimeout(() => {
    // 🚀 TOKAT 2: Hard reload (window.location) yok! Yumuşak geçiş var!
    router.push('/chat')
  }, 250)
}
</script>

<template>
  <div class="w-full flex justify-center items-center min-h-[5rem] relative">
    
    <!-- 🚀 TOKAT 3: Kutunun Üstünde Beliren Seçili Dosyalar Listesi (Animasyonlu) -->
    <Transition
      enter-active-class="transition-all duration-300 cubic-bezier(0.4, 0, 0.2, 1)"
      enter-from-class="opacity-0 translate-y-2 scale-95"
      enter-to-class="opacity-100 translate-y-0 scale-100"
      leave-active-class="transition-all duration-200 cubic-bezier(0.4, 0, 0.2, 1)"
      leave-from-class="opacity-100 translate-y-0 scale-100"
      leave-to-class="opacity-0 translate-y-2 scale-95"
    >
      <div v-if="selectedFiles.length > 0" class="absolute bottom-full mb-3 flex items-center p-2 bg-white dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 rounded-xl shadow-lg overflow-x-auto gap-2 max-w-full z-30">
        <div v-for="(file, index) in selectedFiles" :key="index" class="flex items-center gap-2 bg-neutral-100 dark:bg-neutral-700 p-2 rounded-lg border border-neutral-200 dark:border-neutral-600 whitespace-nowrap">
          <svg class="w-4 h-4 text-blue-600 dark:text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path></svg>
          <span class="text-sm font-medium text-neutral-700 dark:text-neutral-200 truncate max-w-[120px]">{{ file.name }}</span>
          <button @click.prevent="removeFile(index)" type="button" class="ml-1 p-1 text-neutral-400 hover:text-red-500 hover:bg-red-100 dark:hover:bg-red-900/30 rounded-md transition-colors">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg>
          </button>
        </div>
      </div>
    </Transition>

    <form 
      @submit.prevent="goToChat"
      class="relative flex items-center bg-white dark:bg-[#1e1f22] border border-neutral-300 dark:border-neutral-700 rounded-full px-2 py-2 shadow-sm focus-within:ring-1 focus-within:ring-neutral-400 dark:focus-within:ring-neutral-500 transition-all duration-500 ease-out w-full cursor-text z-20"
      :class="isActive ? 'max-w-3xl' : 'max-w-[320px]'"
      @mouseenter="isHovered = true"
      @mouseleave="isHovered = false"
      @click="focusInput"
    >
      
      <!-- 🚀 TOKAT 4: Sol Taraftaki Gizli Dosya Inputu ve Ataş İkonu -->
      <input type="file" multiple ref="fileInput" class="hidden" @change="handleFileSelect" accept=".pdf, image/*, .xls, .xlsx, .doc, .docx, .ppt, .pptx" />
      
      <!-- Sadece kutu açıldığında solda beliren buton -->
      <div class="relative group flex items-center z-20 transition-all duration-500 ml-1" :class="isActive ? 'opacity-100 scale-100 mr-2' : 'opacity-0 scale-50 w-0 overflow-hidden pointer-events-none'">
         <button type="button" @click.stop="triggerFileInput" :disabled="isNavigating" class="p-2 text-neutral-400 hover:text-blue-500 transition-all rounded-full hover:bg-neutral-100 dark:hover:bg-neutral-700 active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed">
           <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13"></path></svg>
         </button>
      </div>

      <!-- 1. ORTADAKİ MAVİ YAZI -->
      <div 
        class="absolute inset-0 flex items-center justify-center pointer-events-none transition-all duration-500"
        :class="isActive ? 'opacity-0 scale-90' : 'opacity-100 scale-100'"
      >
        <span class="text-blue-600 dark:text-blue-400 font-medium text-lg tracking-wide">
          {{ t('focusQuestion') }}
        </span>
      </div>

      <!-- 2. ANİMASYONLU YER TUTUCU -->
      <!-- Ataş butonu geldiği için left-6 yerine left-14 yapıyoruz ki üst üste binmesin -->
      <div 
        class="absolute left-14 pointer-events-none transition-all duration-500 delay-75"
        :class="(isActive && !inputText && selectedFiles.length === 0) ? 'opacity-100 translate-x-0' : 'opacity-0 translate-x-4'"
      >
        <span class="text-neutral-500 text-base">{{ t('askGemini') }}</span>
      </div>

      <!-- 3. GERÇEK GİRDİ ALANI (Input) -->
      <input 
        ref="inputRef"
        type="text" 
        v-model="inputText"
        :disabled="isNavigating"
        @focus="isFocused = true"
        @blur="isFocused = false"
        class="flex-1 bg-transparent border-none outline-none text-neutral-800 dark:text-neutral-100 px-2 py-2 text-base z-10 transition-opacity duration-300 disabled:opacity-50"
        :class="isActive ? 'opacity-100' : 'opacity-0 pointer-events-none'"
      >

      <!-- 4. GÖNDER BUTONU & Tooltip -->
      <div 
        class="relative group flex items-center pl-2 pr-1 z-20 transition-all duration-500"
        :class="isActive ? 'opacity-100 scale-100' : 'opacity-0 scale-50 pointer-events-none'"
      >
        <!-- Butonu submit tipi yapıp, dosya varsa da aktif olacak şekilde ayarladık -->
        <button 
          type="submit"
          :disabled="isNavigating || (!inputText.trim() && selectedFiles.length === 0)"
          class="p-2.5 bg-neutral-100 hover:bg-blue-600 text-neutral-500 hover:text-white dark:bg-[#2b2d31] dark:text-neutral-400 dark:hover:bg-blue-600 dark:hover:text-white rounded-full transition-colors flex items-center justify-center focus:outline-none disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <!-- Normal İkon (Gönderme Oku) -->
          <svg v-if="!isNavigating" xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 -translate-y-[1px] translate-x-[1px]" viewBox="0 0 20 20" fill="currentColor">
            <path d="M10.894 2.553a1 1 0 00-1.788 0l-7 14a1 1 0 001.169 1.409l5-1.429A1 1 0 009 15.571V11a1 1 0 112 0v4.571a1 1 0 00.725.962l5 1.428a1 1 0 001.17-1.408l-7-14z" />
          </svg>

          <!-- Yükleniyor (Spinner) İkonu -->
          <svg v-else class="animate-spin w-5 h-5 text-current" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
        </button>

        <div class="absolute bottom-full mb-3 right-0 px-2 py-1 text-xs font-medium bg-neutral-800 text-white dark:bg-neutral-100 dark:text-neutral-900 rounded opacity-0 group-hover:opacity-100 transition-all pointer-events-none whitespace-nowrap shadow-lg">
          {{ t('send', 'Gönder') }}
        </div>
      </div>

    </form>
  </div>
</template>