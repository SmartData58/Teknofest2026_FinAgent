<script setup>
import { ref, onMounted, onUnmounted } from 'vue'

const canvasRef = ref(null)

const logos = [
  '/adilkatilim_logo.svg',
  '/albaraka_logo.svg',
  '/dunyakatilim_logo.svg',
  '/emlakkatilim_logo.svg',
  '/hayatfinans_logo.svg',
  '/kuveytturk_logo.svg',
  '/tombank_logo.svg',
  '/turkiyefinans_logo.svg',
  '/vakıfkatilim_logo.svg',
  '/ziraatkatilim_logo.svg'
]

let animationId = null
const particles = []
const images = []

const initParticles = () => {
  const canvas = canvasRef.value
  if (!canvas) return
  const ctx = canvas.getContext('2d', { alpha: true })
  
  const resize = () => {
    if (!canvas.parentElement) return
    canvas.width = canvas.parentElement.offsetWidth
    canvas.height = canvas.parentElement.offsetHeight
  }
  window.addEventListener('resize', resize)
  resize()

  logos.forEach(src => {
    const img = new Image()
    img.src = src
    images.push(img)
  })

  // Partikül sayıları (performans için abartılmadı)
  const numBasic = 60
  const numLogos = 15

  for (let i = 0; i < numBasic + numLogos; i++) {
    const isLogo = i >= numBasic
    particles.push({
      x: Math.random() * canvas.width,
      y: Math.random() * canvas.height,
      vx: (Math.random() - 0.5) * 0.4,
      vy: (Math.random() - 0.5) * 0.4 - 0.1, // Hafif yukarı eğilim
      size: isLogo ? Math.random() * 40 + 40 : Math.random() * 2.5 + 1, // Logolar biraz daha büyük olsun
      opacity: isLogo ? Math.random() * 0.1 + 0.05 : Math.random() * 0.4 + 0.1, 
      isLogo: isLogo,
      imgIndex: isLogo ? Math.floor(Math.random() * logos.length) : null,
      rotation: isLogo ? 0 : Math.random() * Math.PI * 2,
      vRotation: isLogo ? 0 : (Math.random() - 0.5) * 0.015
    })
  }

  const draw = () => {
    ctx.clearRect(0, 0, canvas.width, canvas.height)
    
    const isDark = document.documentElement.classList.contains('dark')
    // Noktaların rengi (Hero kısmı hep aydınlık gibiyse de dark mode destekliyoruz)
    const particleColor = isDark ? '255, 255, 255' : '100, 116, 139' 

    particles.forEach(p => {
      p.x += p.vx
      p.y += p.vy
      
      // Sadece noktalar dönsün, logolar her zaman düz kalsın
      if (!p.isLogo) {
        p.rotation += p.vRotation
      }

      // Ekrandan çıkınca diğer taraftan başlat
      if (p.x < -100) p.x = canvas.width + 100
      if (p.x > canvas.width + 100) p.x = -100
      if (p.y < -100) p.y = canvas.height + 100
      if (p.y > canvas.height + 100) p.y = -100

      ctx.save()
      ctx.translate(p.x, p.y)
      if (!p.isLogo) {
        ctx.rotate(p.rotation)
      }
      ctx.globalAlpha = p.opacity

      if (p.isLogo) {
        const img = images[p.imgIndex]
        if (img && img.complete && img.width > 0) {
          // Logoları renksiz (grayscale) yapıyoruz
          if (isDark) {
            ctx.filter = 'grayscale(100%) brightness(200%)'
          } else {
            ctx.filter = 'grayscale(100%) opacity(60%)'
          }
          
          // Orijinal en-boy oranını (aspect ratio) koruyarak çiz
          let drawW = p.size
          let drawH = p.size
          if (img.width > img.height) {
            drawH = p.size * (img.height / img.width)
          } else {
            drawW = p.size * (img.width / img.height)
          }
          
          ctx.drawImage(img, -drawW / 2, -drawH / 2, drawW, drawH)
        }
      } else {
        ctx.fillStyle = `rgba(${particleColor}, 1)`
        ctx.beginPath()
        ctx.arc(0, 0, p.size, 0, Math.PI * 2)
        ctx.fill()
      }
      ctx.restore()
    })

    animationId = requestAnimationFrame(draw)
  }
  
  draw()

  onUnmounted(() => {
    window.removeEventListener('resize', resize)
    if (animationId) cancelAnimationFrame(animationId)
  })
}

onMounted(() => {
  // Parent div'in boyutunu alabilmesi için çok kısa bir süre bekle
  setTimeout(initParticles, 150)
})

</script>

<template>
  <canvas 
    ref="canvasRef" 
    class="absolute inset-0 w-full h-full pointer-events-none z-0"
  ></canvas>
</template>
