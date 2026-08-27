<script setup>
import { computed } from 'vue'

/**
 * Kâr oranının kendi kategori ortalamasına göre konumunu gösteren ok.
 *
 *   'dusuk'  -> aşağı bakan YEŞİL ok  (ortalamanın altında; müşteri lehine)
 *   'yuksek' -> yukarı bakan KIRMIZI ok (ortalamanın üstünde)
 *   null     -> hiçbir şey çizilmez
 *
 * Yön/renk eşlemesi bilinçli: kâr oranında DÜŞÜK olmak iyidir, o yüzden aşağı
 * ok yeşil. Bu, borsa grafiklerindeki "yukarı=yeşil" alışkanlığının tersi;
 * karışmasın diye ipucu metni durumu açıkça yazıyor.
 *
 * Yalnızca banka çalışanı görünümünde çağrılıyor (bkz. ortalamayaGoreKonum).
 */
const props = defineProps({
  konum: { type: String, default: null },   // 'dusuk' | 'yuksek' | null
  ipucu: { type: String, default: '' },
  // `ters=false` (finansman): DÜŞÜK iyidir  -> aşağı yeşil / yukarı kırmızı
  // `ters=true`  (katılım)  : YÜKSEK iyidir -> yukarı yeşil / aşağı kırmızı
  // Yön ve renk aynı proptan türetiliyor ki iki sayfa arasında tutarsız bir
  // eşleme (ör. yeşil aşağı ok ama "iyi değil" anlamı) oluşamasın.
  ters: { type: Boolean, default: false }
})

// Okun YÖNÜ her zaman değerin ortalamaya göre konumunu gösterir.
const yukariBakiyor = computed(() => props.konum === 'yuksek')
// RENK ise o konumun İYİ olup olmadığını gösterir.
const iyi = computed(() =>
  props.ters ? props.konum === 'yuksek' : props.konum === 'dusuk'
)
</script>

<template>
  <span
    v-if="konum"
    class="ortalama-ok"
    :class="iyi ? 'ok-iyi' : 'ok-kotu'"
    :title="ipucu"
    :aria-label="ipucu"
    role="img"
    tabindex="0"
  >
    <!-- Yukarı ok: değer ortalamanın ÜSTÜNDE -->
    <svg v-if="yukariBakiyor" viewBox="0 0 24 24" fill="none" stroke="currentColor"
         stroke-width="3" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
      <path d="M12 19V5M6 11l6-6 6 6" />
    </svg>
    <!-- Aşağı ok: değer ortalamanın ALTINDA -->
    <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor"
         stroke-width="3" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
      <path d="M12 5v14M6 13l6 6 6-6" />
    </svg>
  </span>
</template>

<style scoped>
.ortalama-ok{
  display:inline-flex; align-items:center; justify-content:center;
  width:1.05rem; height:1.05rem; flex:none; cursor:help; border-radius:50%;
  transition:transform .18s ease, filter .18s ease;
}
.ortalama-ok svg{width:100%; height:100%}

/* Glow: renk değişkeni üzerinden, iki tema için de aynı kural. */
.ok-iyi{ color:#10b981; filter:drop-shadow(0 0 3px rgba(16,185,129,.55)); }
.ok-kotu{ color:#ef4444; filter:drop-shadow(0 0 3px rgba(239,68,68,.55)); }

.ortalama-ok:hover,
.ortalama-ok:focus-visible{ transform:scale(1.22); }
.ok-iyi:hover, .ok-iyi:focus-visible{ filter:drop-shadow(0 0 7px rgba(16,185,129,.95)); }
.ok-kotu:hover, .ok-kotu:focus-visible{ filter:drop-shadow(0 0 7px rgba(239,68,68,.95)); }

.ortalama-ok:focus-visible{ outline:2px solid currentColor; outline-offset:2px; }

/* Koyu temada glow biraz daha belirgin olmalı, aksi hâlde zeminde kayboluyor. */
@media (prefers-color-scheme: dark){
  :root:not([data-theme="light"]) .ok-iyi{ filter:drop-shadow(0 0 4px rgba(52,211,153,.7)); }
  :root:not([data-theme="light"]) .ok-kotu{ filter:drop-shadow(0 0 4px rgba(248,113,113,.7)); }
}
:root[data-theme="dark"] .ok-iyi{ filter:drop-shadow(0 0 4px rgba(52,211,153,.7)); }
:root[data-theme="dark"] .ok-kotu{ filter:drop-shadow(0 0 4px rgba(248,113,113,.7)); }

@media (prefers-reduced-motion: reduce){
  .ortalama-ok{ transition:none }
  .ortalama-ok:hover, .ortalama-ok:focus-visible{ transform:none }
}
</style>
