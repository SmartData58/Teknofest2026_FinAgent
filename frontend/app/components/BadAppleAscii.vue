<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue'

const props = defineProps({
  show: Boolean
})
const emit = defineEmits(['close'])

const videoRef = ref(null)
const audioRef = ref(null)
const canvasRef = ref(null)
const asciiText = ref('')
let animationFrameId = null
const errorMsg = ref('')
const isLoading = ref(true)

// Koyu renkten açık renge doğru karakterler
const ASCII_CHARS = " .:-=+*#%@".split('')

const drawAscii = () => {
  if (!videoRef.value || !canvasRef.value) return
  if (videoRef.value.paused || videoRef.value.ended) return

  const ctx = canvasRef.value.getContext('2d', { willReadFrequently: true })
  const width = canvasRef.value.width
  const height = canvasRef.value.height

  ctx.drawImage(videoRef.value, 0, 0, width, height)
  const pixels = ctx.getImageData(0, 0, width, height).data

  let ascii = ''
  for (let y = 0; y < height; y++) {
    for (let x = 0; x < width; x++) {
      const offset = (y * width + x) * 4
      const r = pixels[offset]
      const g = pixels[offset + 1]
      const b = pixels[offset + 2]
      // Parlaklık (Luminance) formülü
      const brightness = (0.299 * r + 0.587 * g + 0.114 * b) / 255
      const charIndex = Math.floor(brightness * (ASCII_CHARS.length - 1))
      ascii += ASCII_CHARS[charIndex]
    }
    ascii += '\n'
  }
  asciiText.value = ascii

  animationFrameId = requestAnimationFrame(drawAscii)
}

const onPlay = () => {
  isLoading.value = false
  // Sesi videoyla senkronize başlat
  if (audioRef.value) {
    audioRef.value.currentTime = videoRef.value ? videoRef.value.currentTime : 0
    audioRef.value.play().catch(e => console.error("Ses çalınamadı:", e))
  }
  drawAscii()
}

const onEnded = () => {
  emit('close')
}

const onError = (e) => {
  console.error("Video/Audio Error:", e)
  isLoading.value = false
  errorMsg.value = "Medya yüklenemedi. Lütfen 'bad_apple_video.mp4' dosyasının var olduğundan emin olun."
}

const handleKeyDown = (e) => {
  if (e.key === 'Escape' && props.show) {
    emit('close')
  }
}

watch(() => props.show, (newVal) => {
  if (newVal) {
    isLoading.value = true
    errorMsg.value = ''
    asciiText.value = ''
    if (process.client) {
      window.addEventListener('keydown', handleKeyDown)
    }
    setTimeout(() => {
      if (videoRef.value) {
        videoRef.value.currentTime = 0
        videoRef.value.play().catch(err => console.warn("Video oynatılamadı:", err))
      }
    }, 100)
  } else {
    if (animationFrameId) cancelAnimationFrame(animationFrameId)
    if (videoRef.value) videoRef.value.pause()
    if (audioRef.value) audioRef.value.pause()
    if (process.client) {
      window.removeEventListener('keydown', handleKeyDown)
    }
  }
})

onUnmounted(() => {
  if (animationFrameId) cancelAnimationFrame(animationFrameId)
  if (audioRef.value) audioRef.value.pause()
  if (process.client) {
    window.removeEventListener('keydown', handleKeyDown)
  }
})

</script>

<template>
  <Transition
    enter-active-class="transition-opacity duration-1000"
    enter-from-class="opacity-0"
    enter-to-class="opacity-100"
    leave-active-class="transition-opacity duration-500"
    leave-from-class="opacity-100"
    leave-to-class="opacity-0"
  >
    <div v-if="show" class="fixed inset-0 z-[9999] bg-black flex flex-col items-center justify-center overflow-hidden">
      
      <!-- Gizli Video, Ses ve Canvas -->
      <video 
        ref="videoRef" 
        src="/bad_apple_video.mp4" 
        class="hidden" 
        crossorigin="anonymous"
        playsinline
        @play="onPlay"
        @ended="onEnded"
        @error="onError"
      ></video>
      <audio 
        ref="audioRef" 
        src="/bad_apple_audio.m4a" 
        class="hidden"
      ></audio>

      <!-- 160x60 çözünürlük 4:3 oranında metin görünümü verir (Font oranının 1:2 olması nedeniyle) -->
      <canvas ref="canvasRef" width="160" height="60" class="hidden"></canvas>
      
      <div v-if="isLoading && !errorMsg" class="text-white/50 font-mono animate-pulse mb-4 text-xl">
        🍎 Bad Apple!! Yükleniyor...
      </div>

      <!-- ASCII Çıktısı Tüm Ekranı Kaplayacak Şekilde Uyarlandı -->
      <pre 
        v-if="!isLoading"
        class="text-white font-mono leading-none tracking-widest whitespace-pre select-none text-center flex items-center justify-center w-full h-full m-0 p-0"
        style="font-size: min(1.2vw, 1.4vh); line-height: 0.8; letter-spacing: 0.1em; text-shadow: 0 0 8px rgba(255, 255, 255, 0.2);"
      >{{ errorMsg || asciiText }}</pre>

      <button 
        @click="emit('close')" 
        class="absolute top-6 right-6 text-white/40 hover:text-white transition-colors bg-white/10 hover:bg-white/20 backdrop-blur-md rounded-full p-2.5 z-[10000] border border-white/20"
        title="Kapat (ESC)"
      >
        <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg>
      </button>

      <!-- Easter Egg Label -->
      <div class="absolute bottom-6 left-6 text-white/40 font-mono text-xs tracking-wider">
        🎵 Alstroemeria Records - Bad Apple!! feat. nomico
      </div>

    </div>
  </Transition>
</template>
