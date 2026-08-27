// https://nuxt.com/docs/api/configuration/nuxt-config
export default defineNuxtConfig({
  compatibilityDate: '2025-07-15',
  devtools: { enabled: true },
  devServer: {
    host: '0.0.0.0',
    port: 3000
  },

  // Frontend'i de tünelden yayınlarken gerekli.
  // Vite, gelen isteğin Host başlığı bilinmiyorsa "Blocked request" diyerek
  // reddeder (DNS rebinding koruması). Tünel alan adları beyaz listeye alındı.
  //
  // ⚠️ HMR'a ELLE DOKUNULMUYOR. Sabit `host`/`protocol: wss` verildiğinde
  // Vite bunu HER istemciye dayatıyor ve localhost'tan açıldığında tarayıcı
  // `wss://localhost/_nuxt/` adresine bağlanmaya çalışıp başarısız oluyordu
  // ("WebSocket closed without opened"). Varsayılan davranışta Vite istemciye
  // sayfanın KENDİ host'unu kullandırır; hem localhost hem tünel çalışır.
  vite: {
    server: {
      allowedHosts: [
        '.devtunnels.ms',        // VS Code dev tunnels
        '.trycloudflare.com',    // cloudflared
        '.ngrok-free.app',
        '.ngrok.io',
        '.loca.lt',
      ],
    },
  },

  // Backend API adresi TEK YERDEN yönetiliyor.
  // Daha önce 17 ayrı fetch çağrısında "http://localhost:8003" sabit
  // yazılıydı; tünel (cloudflared/ngrok) ya da sunucu dağıtımı için hepsini
  // tek tek değiştirmek gerekiyordu. Artık yalnızca .env değişiyor:
  //
  //   yerel   : NUXT_PUBLIC_API_URL=http://localhost:8003
  //   tünel   : NUXT_PUBLIC_API_URL=https://<ad>.trycloudflare.com
  //   aynı ana bilgisayarda ters vekil : NUXT_PUBLIC_API_URL=/api
  //
  // NUXT_PUBLIC_ önekli ortam değişkenleri `public` altındaki aynı adlı
  // anahtarı ÇALIŞMA ZAMANINDA ezer (apiUrl -> NUXT_PUBLIC_API_URL), yani
  // yeniden derleme gerekmez.
  runtimeConfig: {
    public: {
      apiUrl: process.env.NUXT_PUBLIC_API_URL || 'http://localhost:8003'
    }
  },
  
  app: {
    head: {
      title: 'FinAgent',
      titleTemplate: '%s · FinAgent',
      meta: [
        { charset: 'utf-8' },
        { name: 'viewport', content: 'width=device-width, initial-scale=1' },
        { name: 'description', content: 'Katılım Bankacılığı Kampanya ve Finansman Analiz Asistanı' }
      ],
      link: [
        { rel: 'icon', type: 'image/svg+xml', href: '/logo.svg' },
        { rel: 'alternate icon', href: '/logo.svg' }
      ]
    }
  },
  
  modules: [
    '@nuxtjs/tailwindcss',
    '@nuxtjs/color-mode',
    '@nuxtjs/i18n',
    '@tresjs/nuxt',
    '@pinia/nuxt'
  ],

  colorMode: {
    classSuffix: '',
    preference: 'system',
    fallback: 'light',
  },

  i18n: {
    locales: [
      { code: 'tr', name: 'Türkçe', file: 'tr.json' },
      { code: 'en', name: 'English', file: 'en.json' }
    ],
    defaultLocale: 'tr',
    langDir: 'locales/',
    strategy: 'no_prefix',
  },

  build: {
    transpile: ['three', 'gsap', 'chart.js', 'vue-chartjs', 'chartjs-plugin-zoom', 'hammerjs'],
  }
})
