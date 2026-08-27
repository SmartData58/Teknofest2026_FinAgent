<script setup>
useHead({
  titleTemplate: (titleChunk) => {
    return titleChunk ? `${titleChunk} · FinAgent` : 'FinAgent | Katılım Bankacılığı Analiz Asistanı'
  },
  link: [
    { rel: 'icon', type: 'image/svg+xml', href: '/logo.svg' },
    { rel: 'shortcut icon', href: '/logo.svg' },
    { rel: 'apple-touch-icon', href: '/logo.svg' }
  ]
})
</script>

<template>
  <NuxtLayout>
    <NuxtPage />
  </NuxtLayout>
</template>

<style>
html, body, #__nuxt {

  margin: 0;
  padding: 0;
  /* 100vh mobilde adres çubuğu GİZLİYKENki en büyük yüksekliktir. Çubuk
     görünürken uygulamanın alt kısmı ekranın dışına taşıyor, `overflow:hidden`
     yüzünden oraya kaydırılamıyor ve sohbetin yazma kutusu erişilemez hâle
     geliyordu. 100dvh görünür alanı takip eder; desteklemeyen tarayıcı ilk
     kuralda kalır. */
  height: 100vh;
  height: 100dvh;
  overflow: hidden; /* Tarayıcının ana kaydırma çubuğunu gizler */
}

/* Tailwind'in `h-screen` sınıfı da 100vh üretiyor ve aynı tuzağa düşüyor.
   `h-dvh` tek başına kullanılsa dvh desteklemeyen tarayıcıda yükseklik hiç
   uygulanmazdı; bu yüzden iki katmanlı kendi yardımcımızı kullanıyoruz. */
.ekran-yuksekligi {
  height: 100vh;
  height: 100dvh;
}
</style>