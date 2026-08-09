<template>
  <div class="w-full min-h-screen bg-neutral-50 dark:bg-neutral-900 flex flex-col px-6 animate-pulse">
    
    <!-- EN ÜST: 4 Navigasyon Butonunun İskeleti -->
    <div class="w-full flex flex-wrap justify-center gap-3 pt-8">
      <div v-for="i in 4" :key="i" class="w-28 h-9 rounded-full bg-neutral-200 dark:bg-neutral-800"></div>
    </div>

    <!-- MERKEZ: Ana Başlık ve Oval Kutu İskeleti -->
    <div class="flex-1 flex flex-col items-center justify-center pb-24 w-full max-w-4xl mx-auto text-center">
      
      <!-- Başlık Alanı İskeleti -->
      <div class="w-3/4 md:w-2/3 h-16 md:h-20 bg-neutral-200 dark:bg-neutral-800 rounded-2xl mb-12"></div>
      
      <!-- Oval Arama Çubuğu İskeleti (Kutu kapalı halini simüle eder) -->
      <div class="w-full max-w-[320px] h-14 bg-neutral-200 dark:bg-neutral-800 rounded-full"></div>
      
    </div>
  </div>
</template>