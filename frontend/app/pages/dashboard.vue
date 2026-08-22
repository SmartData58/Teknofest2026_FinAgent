<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()

// Bu sayfa 'default' layout'unu kullanır (layouts/default.vue).
// Farklı bir layout istersen: definePageMeta({ layout: 'dashboard' })
definePageMeta({
  layout: 'default'
})

// ⭐ ASIL DÜZELTME: viewMode bilgisini layout ile AYNI global state'ten okuyoruz.
// Anahtar birebir 'globalViewMode' olmalı — layout'taki useState ile aynı.
// Header'daki Müşteri / Banka Çalışanı butonuna basıldığında bu sayfa
// otomatik olarak yeniden render olur.
const viewMode = useState('globalViewMode', () => 'musteri')

const isBankaci = computed(() => viewMode.value === 'bankaci')

// ---------------------------------------------------------------------------
// 🔻 BURADAN İTİBAREN ÖRNEK VERİ — kendi API/composable'ınla değiştir.
//    Örn: const { data: banks } = await useFetch('/api/banks')
// ---------------------------------------------------------------------------
const allBanks = [
  { id: 1, name: 'Ziraat Katılım', rate: 42.5, campaigns: 8, gizli: 2, durum: 'aktif' },
  { id: 2, name: 'Vakıf Katılım', rate: 41.8, campaigns: 6, gizli: 1, durum: 'aktif' },
  { id: 3, name: 'Türkiye Emlak Katılım', rate: 40.9, campaigns: 5, gizli: 3, durum: 'aktif' },
  { id: 4, name: 'Kuveyt Türk', rate: 39.75, campaigns: 11, gizli: 4, durum: 'aktif' },
  { id: 5, name: 'Albaraka Türk', rate: 38.6, campaigns: 7, gizli: 2, durum: 'inceleme' },
  { id: 6, name: 'Türkiye Finans', rate: 37.4, campaigns: 4, gizli: 1, durum: 'aktif' }
]

// viewMode'a göre türetilen veri: bankacı gizli kampanyaları da görür.
const banks = computed(() =>
  allBanks.map((b) => ({
    ...b,
    visibleCampaigns: isBankaci.value ? b.campaigns + b.gizli : b.campaigns
  }))
)

const maxRate = computed(() => Math.max(...banks.value.map((b) => b.rate)))

const totalCampaigns = computed(() =>
  banks.value.reduce((sum, b) => sum + b.visibleCampaigns, 0)
)

const avgRate = computed(() => {
  if (!banks.value.length) return 0
  return banks.value.reduce((sum, b) => sum + b.rate, 0) / banks.value.length
})

const topBank = computed(() =>
  banks.value.reduce((best, b) => (b.rate > best.rate ? b : best), banks.value[0])
)

const hiddenCount = computed(() =>
  allBanks.reduce((sum, b) => sum + b.gizli, 0)
)

const nf = new Intl.NumberFormat('tr-TR', { maximumFractionDigits: 2 })
const fmt = (n) => nf.format(n)
</script>

<template>
  <!-- pt-20: layout'un header'ı -mb-14 ile içeriğin ÜSTÜNE biniyor, o yüzden
       sayfanın kendi üst boşluğunu vermesi gerekiyor. -->
  <div class="px-6 pt-20 pb-12 max-w-7xl mx-auto">

    <!-- Sayfa başlığı -->
    <div class="flex flex-wrap items-end justify-between gap-4 mb-8">
      <div>
        <h1 class="text-2xl font-bold tracking-tight text-neutral-900 dark:text-neutral-50">
          {{ t('dashboard.title', 'Bankalar & Pazarlar') }}
        </h1>
        <p class="mt-1 text-sm text-neutral-500 dark:text-neutral-400">
          {{ t('dashboard.subtitle', 'Katılım bankalarının güncel kâr payı oranları ve kampanya dağılımı') }}
        </p>
      </div>

      <!-- Aktif görünüm rozeti: state'in gerçekten bağlı olduğunu gösterir -->
      <div class="flex items-center gap-2 px-3 py-1.5 rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-800 shadow-sm">
        <span class="w-2 h-2 rounded-full" :class="isBankaci ? 'bg-cyan-500' : 'bg-blue-500'"></span>
        <span class="text-xs font-semibold text-neutral-600 dark:text-neutral-300">
          {{ isBankaci ? t('header.bank_employee', 'Banka Çalışanı') : t('header.customer', 'Müşteri') }}
        </span>
      </div>
    </div>

    <!-- KPI satırı -->
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
      <div class="p-5 rounded-xl border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-800 shadow-sm">
        <p class="text-xs font-medium text-neutral-500 dark:text-neutral-400">
          {{ t('dashboard.kpi_banks', 'Takip edilen banka') }}
        </p>
        <p class="mt-2 text-3xl font-semibold text-neutral-900 dark:text-neutral-50">{{ banks.length }}</p>
      </div>

      <div class="p-5 rounded-xl border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-800 shadow-sm">
        <p class="text-xs font-medium text-neutral-500 dark:text-neutral-400">
          {{ t('dashboard.kpi_campaigns', 'Görünür kampanya') }}
        </p>
        <p class="mt-2 text-3xl font-semibold text-neutral-900 dark:text-neutral-50">{{ totalCampaigns }}</p>
        <p v-if="isBankaci" class="mt-1 text-xs font-medium text-cyan-600 dark:text-cyan-400">
          +{{ hiddenCount }} {{ t('dashboard.kpi_internal', 'kurum içi') }}
        </p>
      </div>

      <div class="p-5 rounded-xl border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-800 shadow-sm">
        <p class="text-xs font-medium text-neutral-500 dark:text-neutral-400">
          {{ t('dashboard.kpi_avg', 'Ortalama kâr payı') }}
        </p>
        <p class="mt-2 text-3xl font-semibold text-neutral-900 dark:text-neutral-50">%{{ fmt(avgRate) }}</p>
      </div>

      <div class="p-5 rounded-xl border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-800 shadow-sm">
        <p class="text-xs font-medium text-neutral-500 dark:text-neutral-400">
          {{ t('dashboard.kpi_top', 'En yüksek oran') }}
        </p>
        <p class="mt-2 text-3xl font-semibold text-neutral-900 dark:text-neutral-50">%{{ fmt(topBank.rate) }}</p>
        <p class="mt-1 text-xs text-neutral-500 dark:text-neutral-400 truncate">{{ topBank.name }}</p>
      </div>
    </div>

    <!-- Banka tablosu -->
    <div class="rounded-xl border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-800 shadow-sm overflow-hidden">
      <div class="px-5 py-4 border-b border-neutral-200 dark:border-neutral-700">
        <h2 class="text-sm font-semibold text-neutral-900 dark:text-neutral-100">
          {{ t('dashboard.table_title', 'Kâr payı oranları') }}
        </h2>
      </div>

      <div class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead>
            <tr class="text-left text-xs font-medium text-neutral-500 dark:text-neutral-400 border-b border-neutral-200 dark:border-neutral-700">
              <th class="px-5 py-3 font-medium">{{ t('dashboard.col_bank', 'Banka') }}</th>
              <th class="px-5 py-3 font-medium w-1/3">{{ t('dashboard.col_rate', 'Kâr payı oranı') }}</th>
              <th class="px-5 py-3 font-medium text-right">{{ t('dashboard.col_campaigns', 'Kampanya') }}</th>
              <th class="px-5 py-3 font-medium text-right">{{ t('dashboard.col_status', 'Durum') }}</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-neutral-100 dark:divide-neutral-700/60">
            <tr v-for="bank in banks" :key="bank.id" class="hover:bg-neutral-50 dark:hover:bg-neutral-700/30 transition-colors">
              <td class="px-5 py-3.5 font-medium text-neutral-800 dark:text-neutral-100 whitespace-nowrap">
                {{ bank.name }}
              </td>
              <td class="px-5 py-3.5">
                <div class="flex items-center gap-3">
                  <div class="flex-1 h-2 rounded-full bg-blue-100 dark:bg-blue-950 overflow-hidden">
                    <div
                      class="h-full rounded-full bg-blue-600 dark:bg-blue-500"
                      :style="{ width: `${(bank.rate / maxRate) * 100}%` }"
                    ></div>
                  </div>
                  <span class="tabular-nums text-neutral-700 dark:text-neutral-200 w-14 text-right">
                    %{{ fmt(bank.rate) }}
                  </span>
                </div>
              </td>
              <td class="px-5 py-3.5 text-right tabular-nums text-neutral-700 dark:text-neutral-200">
                {{ bank.visibleCampaigns }}
              </td>
              <td class="px-5 py-3.5 text-right">
                <span
                  class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium"
                  :class="bank.durum === 'aktif'
                    ? 'bg-emerald-50 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400'
                    : 'bg-amber-50 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400'"
                >
                  <span class="w-1.5 h-1.5 rounded-full" :class="bank.durum === 'aktif' ? 'bg-emerald-500' : 'bg-amber-500'"></span>
                  {{ bank.durum === 'aktif' ? t('dashboard.status_active', 'Aktif') : t('dashboard.status_review', 'İncelemede') }}
                </span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Boş durum: bir daha sessizce blank kalmasın -->
      <div v-if="!banks.length" class="px-5 py-12 text-center">
        <p class="text-sm text-neutral-500 dark:text-neutral-400">
          {{ t('dashboard.empty', 'Gösterilecek banka verisi bulunamadı.') }}
        </p>
      </div>
    </div>

    <!-- Yalnızca banka çalışanına açık bölüm -->
    <div v-if="isBankaci" class="mt-6 p-5 rounded-xl border border-cyan-200 dark:border-cyan-900/50 bg-cyan-50/50 dark:bg-cyan-950/20">
      <div class="flex items-start gap-3">
        <svg class="w-5 h-5 shrink-0 mt-0.5 text-cyan-600 dark:text-cyan-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
        </svg>
        <div>
          <h3 class="text-sm font-semibold text-neutral-900 dark:text-neutral-100">
            {{ t('dashboard.internal_title', 'Kurum içi kampanyalar') }}
          </h3>
          <p class="mt-1 text-sm text-neutral-600 dark:text-neutral-300">
            {{ t('dashboard.internal_desc', 'Bu bölüm yalnızca Banka Çalışanı görünümünde listelenir.') }}
            <span class="font-medium tabular-nums">{{ hiddenCount }}</span>
            {{ t('dashboard.internal_count', 'gizli kampanya mevcut.') }}
          </p>
        </div>
      </div>
    </div>

  </div>
</template>