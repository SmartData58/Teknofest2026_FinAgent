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
  height: 100vh;
  overflow: hidden; /* Tarayıcının ana kaydırma çubuğunu gizler */
}
</style>