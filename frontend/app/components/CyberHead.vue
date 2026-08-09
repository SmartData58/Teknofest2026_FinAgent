<script setup>
import { shallowRef, onMounted, onUnmounted } from 'vue'
import { Vector3 } from 'three'

const headRef = shallowRef(null)
const target = new Vector3()
let animationFrameId = null

const onPointerMove = (e) => {
  if (typeof window === 'undefined') return
  // Farenin konumunu normalize et (-1 ile 1 arası)
  const x = (e.clientX / window.innerWidth) * 2 - 1
  const y = -(e.clientY / window.innerHeight) * 2 + 1
  
  // Hedef vektörü güncelle
  target.set(x * 5, y * 5, 5)
}

// Yerel Animasyon Döngüsü (Native Render Loop)
const animate = () => {
  if (headRef.value) {
    // Kafa objesinin hedefe doğru yumuşak (lerp) dönüşü
    const currentQuaternion = headRef.value.quaternion.clone()
    headRef.value.lookAt(target)
    const targetQuaternion = headRef.value.quaternion.clone()
    
    headRef.value.quaternion.copy(currentQuaternion)
    headRef.value.quaternion.slerp(targetQuaternion, 0.05) // 0.05 hız değeri
  }
  
  // Döngüyü tekrar çağır
  animationFrameId = requestAnimationFrame(animate)
}

onMounted(() => {
  animate() // Bileşen yüklendiğinde döngüyü başlat
})

onUnmounted(() => {
  // Bileşen ekrandan kalktığında bellek sızıntısını önlemek için döngüyü durdur
  if (animationFrameId) {
    cancelAnimationFrame(animationFrameId)
  }
})
</script>

<template>
  <!-- window-size KALDIRILDI, class="w-full h-full" EKLENDİ -->
  <TresCanvas alpha class="w-full h-full" @pointer-move="onPointerMove" clear-color="transparent">
    <TresPerspectiveCamera :position="[0, 0, 8]" :fov="45" />
    <TresAmbientLight :intensity="0.5" />
    <TresDirectionalLight :position="[5, 5, 5]" :intensity="1" />
    
    <TresGroup ref="headRef">
      <!-- Ana Kafa İskeleti (Tel Kafes) -->
      <TresMesh>
        <TresBoxGeometry :args="[2, 2.5, 2]" />
        <TresMeshStandardMaterial color="#3b82f6" :wireframe="true" />
      </TresMesh>
      
      <!-- Göz / Vizör (Parlayan Kısım) -->
      <TresMesh :position="[0, 0.4, 1.01]">
        <TresBoxGeometry :args="[1.4, 0.3, 0.1]" />
        <TresMeshStandardMaterial color="#60a5fa" emissive="#3b82f6" :emissiveIntensity="1.5" />
      </TresMesh>

      <!-- Kulaklık / Anten Detayları -->
      <TresMesh :position="[1.1, 0, 0]">
        <TresBoxGeometry :args="[0.2, 0.8, 0.8]" />
        <TresMeshStandardMaterial color="#1e3a8a" :wireframe="true" />
      </TresMesh>
      <TresMesh :position="[-1.1, 0, 0]">
        <TresBoxGeometry :args="[0.2, 0.8, 0.8]" />
        <TresMeshStandardMaterial color="#1e3a8a" :wireframe="true" />
      </TresMesh>
    </TresGroup>
  </TresCanvas>
</template>