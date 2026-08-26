<template>
  <div class="p-6 md:p-8 space-y-8 w-full max-w-[1400px] mx-auto min-h-full transition-transform duration-500 ease-[cubic-bezier(0.2,0.8,0.2,1)]"
       :class="selectedProduct ? 'lg:-translate-x-28 xl:-translate-x-32' : 'translate-x-0'">

    <!-- ================= ORTALANMIŞ BAŞLIK ================= -->
    <div class="flex flex-col items-center text-center gap-3 max-w-2xl mx-auto">
      <h1 class="reveal-title text-4xl md:text-5xl font-bold bg-clip-text text-transparent gradient-text pb-1">
        {{ $t('financing.title', 'Katılım Finansman Oranları') }}
      </h1>
      <p class="text-sm md:text-base text-neutral-500 dark:text-neutral-400">
        {{ $t('financing.subtitle', 'Katılım bankalarının güncel kâr payı oranları, taksit tutarları ve toplam geri ödeme maliyetlerini karşılaştırın.') }}
      </p>
      <div class="h-1 w-24 rounded-full bg-gradient-to-r from-blue-500 to-cyan-400 mt-1 title-underline"></div>
    </div>

    <!-- 2. ÖZET İSTATİSTİK KARTLARI (KPIs) -->
    <div class="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
      
      <!-- En Düşük Kâr Oranı -->
      <div class="p-4 rounded-2xl bg-white dark:bg-neutral-800/80 border border-neutral-200/80 dark:border-neutral-700 shadow-sm relative overflow-hidden flex flex-col justify-between">
        <div class="flex items-center justify-between gap-2 mb-2">
          <span class="text-xs font-bold text-neutral-500 dark:text-neutral-400">{{ $t('financing.stat_min_rate', 'En Düşük Kâr Oranı') }}</span>
          <span class="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
        </div>
        <div class="flex items-baseline gap-2">
          <span class="text-2xl sm:text-3xl font-black text-emerald-600 dark:text-emerald-400">
            {{ stats.min_rate > 0 ? '%' + stats.min_rate.toFixed(2).replace('.', ',') : '-' }}
          </span>
        </div>
        <div class="text-[11px] font-semibold text-neutral-500 dark:text-neutral-400 mt-1 truncate">
          {{ stats.best_bank || '-' }}
        </div>
      </div>

      <!-- En Düşük Aylık Taksit -->
      <div class="p-4 rounded-2xl bg-white dark:bg-neutral-800/80 border border-neutral-200/80 dark:border-neutral-700 shadow-sm relative overflow-hidden flex flex-col justify-between">
        <div class="flex items-center justify-between gap-2 mb-2">
          <span class="text-xs font-bold text-neutral-500 dark:text-neutral-400">{{ $t('financing.stat_min_installment', 'En Düşük Aylık Taksit') }}</span>
          <span class="w-2 h-2 rounded-full bg-blue-500"></span>
        </div>
        <div class="flex items-baseline gap-1">
          <span class="text-2xl sm:text-3xl font-black text-neutral-900 dark:text-white">
            {{ formatCurrency(stats.min_installment) }}
          </span>
        </div>
        <div class="text-[11px] font-semibold text-neutral-500 dark:text-neutral-400 mt-1">
          {{ $t('financing.filter_amount', 'Seçili filtrelerde') }}
        </div>
      </div>

      <!-- En Düşük Toplam Geri Ödeme -->
      <div class="p-4 rounded-2xl bg-white dark:bg-neutral-800/80 border border-neutral-200/80 dark:border-neutral-700 shadow-sm relative overflow-hidden flex flex-col justify-between">
        <div class="flex items-center justify-between gap-2 mb-2">
          <span class="text-xs font-bold text-neutral-500 dark:text-neutral-400">{{ $t('financing.stat_min_total', 'En Düşük Toplam Ödeme') }}</span>
          <span class="w-2 h-2 rounded-full bg-indigo-500"></span>
        </div>
        <div class="flex items-baseline gap-1">
          <span class="text-2xl sm:text-3xl font-black text-indigo-600 dark:text-indigo-400">
            {{ formatCurrency(stats.min_total) }}
          </span>
        </div>
        <div class="text-[11px] font-semibold text-neutral-500 dark:text-neutral-400 mt-1">
          {{ $t('financing.total_fees', 'Tüm masraflar dahil') }}
        </div>
      </div>

      <!-- Ortalama Sektör Kâr Oranı -->
      <div class="p-4 rounded-2xl bg-white dark:bg-neutral-800/80 border border-neutral-200/80 dark:border-neutral-700 shadow-sm relative overflow-hidden flex flex-col justify-between">
        <div class="flex items-center justify-between gap-2 mb-2">
          <span class="text-xs font-bold text-neutral-500 dark:text-neutral-400">{{ $t('financing.stat_avg_rate', 'Ortalama Kâr Oranı') }}</span>
          <span class="w-2 h-2 rounded-full bg-amber-500"></span>
        </div>
        <div class="flex items-baseline gap-2">
          <span class="text-2xl sm:text-3xl font-black text-amber-600 dark:text-amber-400">
            {{ stats.avg_rate > 0 ? '%' + stats.avg_rate.toFixed(2).replace('.', ',') : '-' }}
          </span>
        </div>
        <div class="text-[11px] font-semibold text-neutral-500 dark:text-neutral-400 mt-1">
          {{ filteredProducts.length }} {{ $t('financing.total_products_found', 'ürün ortalaması') }}
        </div>
      </div>

    </div>

    <!-- 3. FİLTRELEME & KONTROL MERKEZİ -->
    <div class="p-5 rounded-3xl bg-white/90 dark:bg-neutral-900/90 backdrop-blur-md border border-neutral-200 dark:border-neutral-800 shadow-sm space-y-4 relative z-30">
      
      <div v-if="isSortOpen" @click="isSortOpen = false" class="fixed inset-0 z-40"></div>

      <!-- A. Kategori Sekmeleri (Tabs) & Görünüm Seçici -->
      <div class="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 pb-3 border-b border-neutral-100 dark:border-neutral-800">
        
        <!-- Kategori Sekmeleri -->
        <div class="inline-flex flex-wrap items-center p-1 rounded-xl border border-neutral-300/50 dark:border-neutral-700/50 bg-neutral-100/60 dark:bg-neutral-800/60 backdrop-blur-sm shadow-sm gap-1">
          <button 
            v-for="cat in availableCategories" 
            :key="cat"
            @click="selectedCategory = selectedCategory === cat ? '' : cat"
            :class="selectedCategory === cat ? 'bg-white dark:bg-neutral-700 text-blue-600 dark:text-cyan-400 shadow-sm font-bold' : 'text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-white font-medium'"
            class="px-3 py-1.5 text-xs rounded-lg transition-all capitalize"
          >
            {{ getCategoryLabel(cat) }} ({{ countByCategory(cat) }})
          </button>
        </div>

        <!-- Sağ Araçlar: Dışa Aktarma, Görünüm Modu & Temizle -->
        <div class="flex items-center gap-2 self-end sm:self-auto flex-wrap" data-png-gizle>
          
          <!-- Dışa Aktarma Butonları -->
          <div class="flex items-center gap-1.5 mr-1">
            <button 
              @click="exportData('excel')" 
              :title="$t('financing.export_excel', 'Excel İndir')" 
              class="p-2 bg-green-50 dark:bg-green-950/40 hover:bg-green-100 dark:hover:bg-green-900/50 text-green-700 dark:text-green-400 border border-green-200 dark:border-green-800/60 rounded-xl transition-all shadow-sm active:scale-95 group"
            >
              <svg class="w-4 h-4 group-hover:-translate-y-0.5 transition-transform" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
            </button>
            <button 
              @click="exportData('pdf')" 
              :title="$t('financing.export_pdf', 'PDF İndir')" 
              class="p-2 bg-red-50 dark:bg-red-950/40 hover:bg-red-100 dark:hover:bg-red-900/50 text-red-700 dark:text-red-400 border border-red-200 dark:border-red-800/60 rounded-xl transition-all shadow-sm active:scale-95 group"
            >
              <svg class="w-4 h-4 group-hover:-translate-y-0.5 transition-transform" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
              </svg>
            </button>
            <button 
              @click="exportData('png')" 
              :title="$t('financing.export_png', 'PNG İndir')" 
              class="p-2 bg-blue-50 dark:bg-blue-950/40 hover:bg-blue-100 dark:hover:bg-blue-900/50 text-blue-700 dark:text-blue-400 border border-blue-200 dark:border-blue-800/60 rounded-xl transition-all shadow-sm active:scale-95 group"
            >
              <svg class="w-4 h-4 group-hover:-translate-y-0.5 transition-transform" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
              </svg>
            </button>
          </div>

          <!-- Temizle -->
          <button 
            v-if="hasActiveFilters"
            @click="clearFilters"
            class="px-2.5 py-1.5 text-xs font-semibold text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-950/30 rounded-xl transition-all border border-red-200 dark:border-red-800/50"
          >
            {{ $t('financing.clear_filters', 'Temizle') }}
          </button>

          <!-- Görünüm Değiştirici -->
          <div class="flex p-1 rounded-xl border border-neutral-300/50 dark:border-neutral-700/50 bg-neutral-100/60 dark:bg-neutral-800/60 backdrop-blur-sm shadow-sm gap-1">
            <button 
              @click="viewMode = 'grid'" 
              :class="viewMode === 'grid' ? 'bg-white dark:bg-neutral-700 text-blue-600 dark:text-cyan-400 shadow-sm font-bold' : 'text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-white font-medium'"
              class="p-1.5 rounded-lg transition-all"
              :title="$t('financing.grid_view', 'Kart Görünümü')"
            >
              <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z" />
              </svg>
            </button>
            <button 
              @click="viewMode = 'table'" 
              :class="viewMode === 'table' ? 'bg-white dark:bg-neutral-700 text-blue-600 dark:text-cyan-400 shadow-sm font-bold' : 'text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-white font-medium'"
              class="p-1.5 rounded-lg transition-all"
              :title="$t('financing.table_view', 'Tablo Görünümü')"
            >
              <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 10h16M4 14h16M4 18h16" />
              </svg>
            </button>
          </div>
        </div>

      </div>

      <!-- B. Banka & Tier Filtreleri (Yan Yana - Çoklu Seçim) -->
      <div class="flex flex-col md:flex-row items-start md:items-center gap-4 flex-wrap">
        
        <!-- Banka Filtresi -->
        <div class="space-y-1.5">
          <div class="text-[11px] font-bold text-neutral-500 dark:text-neutral-400 uppercase tracking-wider">
            {{ $t('financing.filter_bank', 'Banka Filtresi') }}
          </div>
          <div class="inline-flex flex-wrap items-center p-1 rounded-xl border border-neutral-300/50 dark:border-neutral-700/50 bg-neutral-100/60 dark:bg-neutral-800/60 backdrop-blur-sm shadow-sm gap-1">
            <button 
              v-for="b in availableBanks" 
              :key="b.code"
              @click="toggleBank(b.code)"
              :class="selectedBanks.includes(b.code) ? 'bg-white dark:bg-neutral-700 text-blue-600 dark:text-cyan-400 shadow-sm font-bold' : 'text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-white font-medium'"
              class="px-3 py-1.5 text-xs rounded-lg transition-all flex items-center gap-2 group"
            >
              <img :src="b.logo_url" :alt="b.name" class="w-4 h-4 object-contain rounded group-hover:scale-110 transition-transform" />
              <span>{{ b.name }}</span>
            </button>
          </div>
        </div>

        <!-- Tier Filtresi -->
        <div v-if="availableTiers.length" class="space-y-1.5">
          <div class="text-[11px] font-bold text-neutral-500 dark:text-neutral-400 uppercase tracking-wider">
            {{ $t('financing.filter_tier', 'Tier Filtresi') }}
          </div>
          <div class="inline-flex flex-wrap items-center p-1 rounded-xl border border-neutral-300/50 dark:border-neutral-700/50 bg-neutral-100/60 dark:bg-neutral-800/60 backdrop-blur-sm shadow-sm gap-1">
            <button 
              v-for="tVal in availableTiers" 
              :key="tVal"
              @click="toggleTier(tVal)"
              :class="selectedTiers.includes(tVal) ? 'bg-white dark:bg-neutral-700 text-blue-600 dark:text-cyan-400 shadow-sm font-bold' : 'text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-white font-medium'"
              class="px-3 py-1.5 text-xs rounded-lg transition-all flex items-center"
            >
              <span>{{ tVal }}</span>
            </button>
          </div>
        </div>

      </div>

      <!-- C. Tutar, Vade & Sıralama Kontrolleri -->
      <div class="grid grid-cols-1 lg:grid-cols-12 gap-4 pt-3 border-t border-neutral-100 dark:border-neutral-800 items-start">
        
        <!-- Tutar Seçici (5 Kolon) -->
        <div class="lg:col-span-5 space-y-1.5">
          <label class="text-[11px] font-bold text-neutral-500 dark:text-neutral-400 uppercase tracking-wider block">
            {{ $t('financing.filter_amount', 'Finansman Tutarı') }}
          </label>
          <div class="flex flex-wrap items-center p-1 rounded-xl border border-neutral-300/50 dark:border-neutral-700/50 bg-neutral-100/60 dark:bg-neutral-800/60 backdrop-blur-sm shadow-sm gap-1">
            <button 
              v-for="amt in availableAmounts" 
              :key="amt"
              @click="selectedAmount = selectedAmount === amt ? null : amt"
              :class="selectedAmount === amt ? 'bg-white dark:bg-neutral-700 text-blue-600 dark:text-cyan-400 shadow-sm font-bold' : 'text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-white font-medium'"
              class="flex-1 min-w-[65px] px-2 py-1.5 text-center text-xs rounded-lg transition-all"
            >
              {{ formatCompactNumber(amt) }} ₺
            </button>
          </div>
        </div>

        <!-- Vade Seçici (4 Kolon) -->
        <div class="lg:col-span-4 space-y-1.5">
          <label class="text-[11px] font-bold text-neutral-500 dark:text-neutral-400 uppercase tracking-wider block">
            {{ $t('financing.filter_term', 'Vade Süresi') }}
          </label>
          <div class="flex flex-wrap items-center p-1 rounded-xl border border-neutral-300/50 dark:border-neutral-700/50 bg-neutral-100/60 dark:bg-neutral-800/60 backdrop-blur-sm shadow-sm gap-1">
            <button 
              v-for="term in availableTerms" 
              :key="term"
              @click="selectedTerm = selectedTerm === term ? null : term"
              :class="selectedTerm === term ? 'bg-white dark:bg-neutral-700 text-blue-600 dark:text-cyan-400 shadow-sm font-bold' : 'text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-white font-medium'"
              class="flex-1 min-w-[50px] px-2 py-1.5 text-center text-xs rounded-lg transition-all"
            >
              {{ term }} {{ $t('financing.term_months', 'Ay') }}
            </button>
          </div>
        </div>

        <!-- Sıralama Dropdown (Campaigns Stili - 3 Kolon) -->
        <div class="lg:col-span-3 space-y-1.5 relative">
          <label class="text-[11px] font-bold text-neutral-500 dark:text-neutral-400 uppercase tracking-wider block">
            {{ $t('financing.sort_by', 'Sıralama') }}
          </label>
          <div class="relative">
            <div
              @click="isSortOpen = !isSortOpen"
              class="h-[38px] w-full bg-neutral-100/60 dark:bg-neutral-800/60 border border-neutral-300/50 dark:border-neutral-700/50 rounded-xl px-3 text-xs flex items-center justify-between cursor-pointer transition-all select-none shadow-sm backdrop-blur-sm hover:border-neutral-400 dark:hover:border-neutral-600"
              :class="isSortOpen ? 'border-blue-500 ring-2 ring-blue-500/30 bg-white dark:bg-neutral-800' : ''"
            >
              <span class="font-bold text-neutral-800 dark:text-neutral-200 truncate">
                {{ getSortLabel(sortBy) }}
              </span>
              <svg 
                class="w-3.5 h-3.5 text-neutral-400 flex-shrink-0 transition-transform duration-200 pointer-events-none ml-2" 
                :class="isSortOpen ? 'rotate-180 text-blue-500' : ''" 
                fill="none" 
                viewBox="0 0 24 24" 
                stroke="currentColor" 
                stroke-width="2"
              >
                <path stroke-linecap="round" stroke-linejoin="round" d="M19 9l-7 7-7-7"/>
              </svg>
            </div>

            <!-- Dropdown Menü (Campaigns Stili) -->
            <Transition
              enter-active-class="transition duration-150 ease-out"
              enter-from-class="opacity-0 translate-y-1 scale-98"
              enter-to-class="opacity-100 translate-y-0 scale-100"
              leave-active-class="transition duration-100 ease-in"
              leave-from-class="opacity-100 translate-y-0 scale-100"
              leave-to-class="opacity-0 translate-y-1 scale-98"
            >
              <div 
                v-if="isSortOpen" 
                class="absolute top-full left-0 right-0 mt-1.5 z-50 bg-white dark:bg-neutral-900 border border-neutral-200 dark:border-neutral-700 rounded-xl shadow-xl py-1 overflow-hidden"
              >
                <div
                  v-for="opt in sortOptions"
                  :key="opt.value"
                  @click="sortBy = opt.value; isSortOpen = false"
                  class="flex items-center justify-between px-3 py-2 text-xs cursor-pointer hover:bg-blue-50 dark:hover:bg-blue-900/30 transition-colors"
                  :class="sortBy === opt.value ? 'bg-blue-50/80 dark:bg-blue-900/40 text-blue-600 dark:text-cyan-400 font-bold' : 'text-neutral-700 dark:text-neutral-200 font-medium'"
                >
                  <span>{{ opt.label }}</span>
                  <svg v-if="sortBy === opt.value" class="w-3.5 h-3.5 text-blue-600 dark:text-cyan-400 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5"><path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/></svg>
                </div>
              </div>
            </Transition>
          </div>
        </div>

      </div>

    </div>

    <!-- 4. LİSTELEME ALANI (ID: financing-content-area PNG export için) -->
    <div id="financing-content-area" class="space-y-6">

      <!-- Sonuç Sayacı -->
      <div class="flex items-center justify-between text-xs font-semibold text-neutral-500 dark:text-neutral-400 px-1">
        <span>{{ filteredProducts.length }} {{ $t('financing.total_products_found', 'Finansman Seçeneği Listelendi') }}</span>
      </div>

      <!-- Yükleniyor Durumu -->
      <div v-if="isLoading" class="flex flex-col items-center justify-center py-20 gap-3">
        <div class="w-10 h-10 border-4 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
        <span class="text-xs font-semibold text-neutral-500">{{ $t('financing.loading', 'Finansman verileri yükleniyor...') }}</span>
      </div>

      <!-- Sonuç Bulunamadı -->
      <div v-else-if="filteredProducts.length === 0" class="p-12 text-center rounded-3xl bg-neutral-50 dark:bg-neutral-800/40 border border-neutral-200 dark:border-neutral-700">
        <svg class="w-12 h-12 text-neutral-400 mx-auto mb-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        <div class="text-sm font-bold text-neutral-700 dark:text-neutral-300 mb-1">
          {{ $t('financing.no_results', 'Seçilen kriterlere uygun finansman seçeneği bulunamadı.') }}
        </div>
        <button @click="clearFilters" class="mt-3 px-4 py-2 bg-blue-600 text-white rounded-xl text-xs font-bold hover:bg-blue-700 transition-all">
          {{ $t('financing.clear_filters', 'Filtreleri Sıfırla') }}
        </button>
      </div>

      <!-- A. KART GÖRÜNÜMÜ (MÜŞTERİ: YATAY DİKDÖRTGEN, BANKA: 3 KOLONLU GRID) -->
      <template v-else-if="viewMode === 'grid'">

        <!-- 1. MÜŞTERİ GÖRÜNÜMÜ: YATAY DİKDÖRTGEN KARTLAR -->
        <div v-if="!isBankaci" class="flex flex-col space-y-3.5">
          <div 
            v-for="p in filteredProducts" 
            :key="p.id"
            @click="openProductDetails(p)"
            class="p-4 sm:p-5 rounded-2xl sm:rounded-3xl bg-white dark:bg-neutral-800/90 border border-neutral-200/80 dark:border-neutral-700/80 shadow-sm hover:shadow-md hover:border-blue-300 dark:hover:border-blue-700 transition-all flex flex-col lg:flex-row lg:items-center justify-between gap-4 sm:gap-6 group cursor-pointer active:scale-[0.998]"
          >
            <!-- Sol Alan: Banka Bilgisi, Logo & Kategori -->
            <div class="flex items-center gap-3 sm:gap-4 lg:w-60 shrink-0">
              <div class="w-12 h-12 rounded-2xl bg-neutral-50 dark:bg-neutral-700/60 border border-neutral-200 dark:border-neutral-600 flex items-center justify-center p-2 shrink-0 group-hover:scale-105 transition-transform">
                <img :src="p.logo_url" :alt="p.banka_adi" class="w-full h-full object-contain" />
              </div>
              <div class="min-w-0">
                <div class="flex items-center gap-1.5 flex-wrap">
                  <h3 class="text-sm sm:text-base font-extrabold text-neutral-900 dark:text-white leading-snug truncate">{{ p.banka_adi }}</h3>
                  <span class="text-[10px] font-bold px-1.5 py-0.5 rounded-md bg-blue-50 dark:bg-blue-900/40 text-blue-700 dark:text-cyan-300 border border-blue-200/60 dark:border-blue-800/40 uppercase shrink-0">
                    {{ getCategoryLabel(p.urun) }}
                  </span>
                </div>
                <div class="flex items-center gap-2 mt-1 text-[11px] text-neutral-400">
                  <span>{{ p.tier }}</span>
                  <span>•</span>
                  <span>{{ p.guncellenme_tarihi }}</span>
                </div>
              </div>
            </div>

            <!-- Orta Alan: Finansal Metrikler (Yatay Kolonlar) -->
            <div class="grid grid-cols-2 sm:grid-cols-4 gap-3 sm:gap-4 flex-1 py-3 lg:py-0 border-y lg:border-y-0 lg:border-x border-neutral-100 dark:border-neutral-700/60 lg:px-6">
              
              <!-- Kâr Oranı -->
              <div class="flex flex-col justify-center">
                <span class="text-[10px] font-bold text-neutral-400 uppercase tracking-wider">{{ $t('financing.rate', 'Kâr Oranı') }}</span>
                <span class="text-base sm:text-lg font-black text-emerald-600 dark:text-emerald-400 mt-0.5">
                  {{ p.kar_orani_str }}
                </span>
              </div>

              <!-- Tutar & Vade -->
              <div class="flex flex-col justify-center">
                <span class="text-[10px] font-bold text-neutral-400 uppercase tracking-wider">{{ $t('financing.amount', 'Tutar') }} & {{ $t('financing.term', 'Vade') }}</span>
                <span class="text-xs sm:text-sm font-extrabold text-neutral-800 dark:text-neutral-200 mt-0.5">
                  {{ formatCurrency(p.finansman_tutari) }}
                </span>
                <span class="text-[11px] font-semibold text-neutral-500 dark:text-neutral-400">
                  {{ p.vade }} {{ $t('financing.term_months', 'Ay') }}
                </span>
              </div>

              <!-- Aylık Taksit -->
              <div class="flex flex-col justify-center">
                <span class="text-[10px] font-bold text-neutral-400 uppercase tracking-wider">{{ $t('financing.installment', 'Aylık Taksit') }}</span>
                <span class="text-sm sm:text-base font-black text-neutral-900 dark:text-white mt-0.5">
                  {{ p.aylik_taksit_str }}
                </span>
              </div>

              <!-- Toplam Geri Ödeme -->
              <div class="flex flex-col justify-center">
                <span class="text-[10px] font-bold text-neutral-400 uppercase tracking-wider">{{ $t('financing.total_payment', 'Toplam Ödeme') }}</span>
                <span class="text-sm sm:text-base font-black text-indigo-600 dark:text-indigo-400 mt-0.5">
                  {{ p.geri_odenecek_toplam_str }}
                </span>
                <span class="text-[10px] text-neutral-400 truncate" :title="$t('financing.allocation_short', 'Tahsis') + ': ' + p.tahsis_ucreti_str">
                  {{ $t('financing.allocation_short', 'Tahsis') }}: {{ p.tahsis_ucreti_str }}
                </span>
              </div>

            </div>

            <!-- Sağ Alan: Parlayan FinAgent Logosu Butonu -->
            <div class="flex items-center justify-end shrink-0 pl-2">
              <button 
                @click.stop="askAiAboutProduct(p)"
                :title="$t('financing.ask_finagent', 'FinAgent ile Analiz Et')"
                class="finagent-glow-btn p-3 rounded-2xl transition-all duration-300 hover:scale-110 active:scale-95 flex items-center justify-center cursor-pointer shadow-sm group/btn"
              >
                <img src="/logo.svg" class="w-6 h-6 object-contain logo-glow" alt="FinAgent" />
              </button>
            </div>

          </div>
        </div>

        <!-- 2. BANKA ÇALIŞANI GÖRÜNÜMÜ: 3 KOLONLU DİKEY GRID KARTLAR -->
        <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          <div 
            v-for="p in filteredProducts" 
            :key="p.id"
            @click="openProductDetails(p)"
            class="p-5 rounded-3xl bg-white dark:bg-neutral-800/90 border border-neutral-200/80 dark:border-neutral-700/80 shadow-sm hover:shadow-md hover:border-blue-300 dark:hover:border-blue-700 transition-all flex flex-col justify-between group cursor-pointer active:scale-[0.995]"
          >
            <!-- Kart Başlığı -->
            <div>
              <div class="flex items-start justify-between gap-3 pb-3 border-b border-neutral-100 dark:border-neutral-700/60">
                <div class="flex items-center gap-2.5">
                  <div class="w-10 h-10 rounded-2xl bg-neutral-50 dark:bg-neutral-700/60 border border-neutral-200 dark:border-neutral-600 flex items-center justify-center p-1.5 shrink-0">
                    <img :src="p.logo_url" :alt="p.banka_adi" class="w-full h-full object-contain" />
                  </div>
                  <div>
                    <h3 class="text-sm font-extrabold text-neutral-900 dark:text-white leading-snug">{{ p.banka_adi }}</h3>
                    <div class="flex items-center gap-1.5 mt-0.5">
                      <span class="text-[10px] font-bold px-2 py-0.5 rounded-md bg-blue-50 dark:bg-blue-900/40 text-blue-700 dark:text-cyan-300 border border-blue-200/60 dark:border-blue-800/40 uppercase">
                        {{ getCategoryLabel(p.urun) }}
                      </span>
                      <span class="text-[10px] font-semibold text-neutral-400">{{ p.tier }}</span>
                    </div>
                  </div>
                </div>

                <!-- Vurgulu Kâr Oranı Rozeti -->
                <div class="text-right">
                  <div class="text-[10px] font-bold text-neutral-400 uppercase tracking-wider">{{ $t('financing.rate', 'Kâr Oranı') }}</div>
                  <div class="text-lg font-black text-emerald-600 dark:text-emerald-400">
                    {{ p.kar_orani_str }}
                  </div>
                </div>
              </div>

              <!-- Tutar & Vade Özeti -->
              <div class="my-4 p-3 rounded-2xl bg-neutral-50 dark:bg-neutral-900/60 border border-neutral-100 dark:border-neutral-800 grid grid-cols-2 gap-2 text-center">
                <div>
                  <div class="text-[10px] font-bold text-neutral-400 uppercase">{{ $t('financing.amount', 'Tutar') }}</div>
                  <div class="text-xs font-extrabold text-neutral-800 dark:text-neutral-200 mt-0.5">
                    {{ formatCurrency(p.finansman_tutari) }}
                  </div>
                </div>
                <div class="border-l border-neutral-200 dark:border-neutral-800">
                  <div class="text-[10px] font-bold text-neutral-400 uppercase">{{ $t('financing.term', 'Vade') }}</div>
                  <div class="text-xs font-extrabold text-neutral-800 dark:text-neutral-200 mt-0.5">
                    {{ p.vade }} {{ $t('financing.term_months', 'Ay') }}
                  </div>
                </div>
              </div>

              <!-- Finansal Hesaplama Detayları -->
              <div class="space-y-2 text-xs">
                <div class="flex items-center justify-between py-1 border-b border-neutral-100 dark:border-neutral-800">
                  <span class="text-neutral-500 dark:text-neutral-400">{{ $t('financing.installment', 'Aylık Taksit') }}</span>
                  <span class="font-extrabold text-neutral-900 dark:text-white text-sm">
                    {{ p.aylik_taksit_str }}
                  </span>
                </div>

                <div class="flex items-center justify-between py-1 border-b border-neutral-100 dark:border-neutral-800">
                  <span class="text-neutral-500 dark:text-neutral-400">{{ $t('financing.total_payment', 'Toplam Geri Ödeme') }}</span>
                  <span class="font-extrabold text-indigo-600 dark:text-indigo-400">
                    {{ p.geri_odenecek_toplam_str }}
                  </span>
                </div>

                <!-- Masraflar Dökümü -->
                <div class="pt-1 text-[11px] text-neutral-500 dark:text-neutral-400 space-y-1 bg-neutral-50/50 dark:bg-neutral-900/30 p-2 rounded-xl">
                  <div class="flex justify-between">
                    <span>{{ $t('financing.allocation_fee', 'Tahsis Ücreti') }}:</span>
                    <span class="font-semibold text-neutral-700 dark:text-neutral-300">{{ p.tahsis_ucreti_str }}</span>
                  </div>
                  <div v-if="p.ekspertiz_ucreti > 0" class="flex justify-between">
                    <span>{{ $t('financing.appraisal_fee', 'Ekspertiz') }}:</span>
                    <span class="font-semibold text-neutral-700 dark:text-neutral-300">{{ p.ekspertiz_ucreti_str }}</span>
                  </div>
                  <div v-if="p.ipotek_tesis_ucreti > 0" class="flex justify-between">
                    <span>{{ $t('financing.mortgage_fee', 'İpotek Tesis') }}:</span>
                    <span class="font-semibold text-neutral-700 dark:text-neutral-300">{{ p.ipotek_tesis_ucreti_str }}</span>
                  </div>
                </div>
              </div>
            </div>

            <!-- Kart Altı (Tarih & Parlayan Logo Butonu) -->
            <div class="mt-4 pt-3 border-t border-neutral-100 dark:border-neutral-700/60 flex items-center justify-between gap-2">
              <span class="text-[10px] text-neutral-400">
                {{ p.guncellenme_tarihi }}
              </span>
              <button 
                @click.stop="askAiAboutProduct(p)"
                :title="$t('financing.ask_finagent', 'FinAgent ile Analiz Et')"
                class="finagent-glow-btn p-2 rounded-xl transition-all duration-300 hover:scale-110 active:scale-95 flex items-center justify-center cursor-pointer shadow-sm group/btn"
              >
                <img src="/logo.svg" class="w-4 h-4 object-contain logo-glow" alt="FinAgent" />
              </button>
            </div>
          </div>
        </div>

      </template>

      <!-- B. TABLO GÖRÜNÜMÜ (TABLE) -->
      <div v-else class="overflow-x-auto rounded-3xl border border-neutral-200 dark:border-neutral-800 bg-white dark:bg-neutral-900 shadow-sm custom-scrollbar">
        <table class="w-full text-left border-collapse text-xs">
          <thead>
            <tr class="bg-neutral-50 dark:bg-neutral-800/80 border-b border-neutral-200 dark:border-neutral-700 text-neutral-600 dark:text-neutral-300">
              <th class="py-3.5 px-4 font-bold">{{ $t('financing.bank', 'Banka') }}</th>
              <th class="py-3.5 px-4 font-bold">{{ $t('financing.product', 'Kategori') }}</th>
              <th class="py-3.5 px-4 font-bold">{{ $t('financing.amount', 'Tutar') }}</th>
              <th class="py-3.5 px-4 font-bold">{{ $t('financing.term', 'Vade') }}</th>
              <th class="py-3.5 px-4 font-bold text-emerald-600 dark:text-emerald-400">{{ $t('financing.rate', 'Kâr Oranı') }}</th>
              <th class="py-3.5 px-4 font-bold">{{ $t('financing.installment', 'Aylık Taksit') }}</th>
              <th class="py-3.5 px-4 font-bold text-indigo-600 dark:text-indigo-400">{{ $t('financing.total_payment', 'Toplam Geri Ödeme') }}</th>
              <th class="py-3.5 px-4 font-bold">{{ $t('financing.allocation_fee', 'Tahsis Ücreti') }}</th>
              <th class="py-3.5 px-4 font-bold text-right" data-png-gizle>{{ $t('financing.actions', 'İşlem') }}</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-neutral-100 dark:divide-neutral-800">
            <tr 
              v-for="p in filteredProducts" 
              :key="p.id"
              @click="openProductDetails(p)"
              class="hover:bg-neutral-50/80 dark:hover:bg-neutral-800/40 transition-colors cursor-pointer"
            >
              <td class="py-3 px-4">
                <div class="flex items-center gap-2">
                  <img :src="p.logo_url" :alt="p.banka_adi" class="w-5 h-5 object-contain" />
                  <span class="font-bold text-neutral-900 dark:text-white">{{ p.banka_adi }}</span>
                </div>
              </td>
              <td class="py-3 px-4">
                <span class="font-semibold text-neutral-700 dark:text-neutral-300 capitalize">
                  {{ getCategoryLabel(p.urun) }}
                </span>
              </td>
              <td class="py-3 px-4 font-bold text-neutral-800 dark:text-neutral-200">
                {{ formatCurrency(p.finansman_tutari) }}
              </td>
              <td class="py-3 px-4 font-medium text-neutral-600 dark:text-neutral-400">
                {{ p.vade }} {{ $t('financing.term_months', 'Ay') }}
              </td>
              <td class="py-3 px-4 font-extrabold text-emerald-600 dark:text-emerald-400 text-sm">
                {{ p.kar_orani_str }}
              </td>
              <td class="py-3 px-4 font-extrabold text-neutral-900 dark:text-white">
                {{ p.aylik_taksit_str }}
              </td>
              <td class="py-3 px-4 font-extrabold text-indigo-600 dark:text-indigo-400">
                {{ p.geri_odenecek_toplam_str }}
              </td>
              <td class="py-3 px-4 text-neutral-500 dark:text-neutral-400">
                {{ p.tahsis_ucreti_str }}
              </td>
              <td class="py-3 px-4 text-right" data-png-gizle>
                <button 
                  @click.stop="askAiAboutProduct(p)"
                  :title="$t('financing.ask_finagent', 'FinAgent ile Analiz Et')"
                  class="finagent-glow-btn p-1.5 rounded-lg transition-all duration-300 hover:scale-110 active:scale-95 inline-flex items-center justify-center cursor-pointer shadow-sm group/btn"
                >
                  <img src="/logo.svg" class="w-4 h-4 object-contain logo-glow" alt="FinAgent" />
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

    </div>

    <!-- ================= FİNANSMAN DETAY PANELİ (DRAWER / MODAL - NO BLUR) ================= -->
    <Teleport to="body">
      <Transition
        enter-active-class="transform transition-all duration-300 ease-out" 
        enter-from-class="translate-x-[120%] opacity-0 scale-95" 
        enter-to-class="translate-x-0 opacity-100 scale-100" 
        leave-active-class="transform transition-all duration-300 ease-in" 
        leave-from-class="translate-x-0 opacity-100 scale-100" 
        leave-to-class="translate-x-[120%] opacity-0 scale-95"
      >
        <div v-if="selectedProduct" class="fixed right-4 top-4 bottom-4 w-[340px] sm:w-[420px] lg:w-[480px] bg-white dark:bg-[#121212] rounded-[24px] shadow-[0_12px_40px_rgba(0,0,0,0.15)] dark:shadow-[0_12px_40px_rgba(0,0,0,0.7)] border border-neutral-200 dark:border-neutral-700 flex flex-col z-[100] overflow-hidden">
          
          <!-- Drawer Header -->
          <div class="flex justify-between items-center p-4 border-b border-neutral-200 dark:border-neutral-700 bg-neutral-50 dark:bg-neutral-800">
            <h3 class="text-[14px] font-bold flex items-center gap-2 text-neutral-800 dark:text-white">
              <svg class="w-4 h-4 text-emerald-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
              {{ $t('financing.modal_title', 'Finansman Detayları') }}
            </h3>
            <button @click="selectedProduct = null" class="p-1 text-neutral-500 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/30 rounded-lg transition-colors active:scale-90 transform duration-200" :title="$t('financing.close', 'Kapat')">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg>
            </button>
          </div>

          <!-- Drawer Body -->
          <div class="flex-1 overflow-y-auto p-4 lg:p-6 custom-scrollbar space-y-4">
            
            <!-- Banka Bilgisi ve Kategori Başlığı -->
            <div class="flex items-center gap-3 p-3.5 rounded-2xl bg-neutral-50 dark:bg-neutral-800/60 border border-neutral-100 dark:border-neutral-800">
              <div class="w-12 h-12 rounded-2xl bg-white dark:bg-neutral-700/80 border border-neutral-200 dark:border-neutral-600 flex items-center justify-center p-2 shrink-0 shadow-sm">
                <img :src="selectedProduct.logo_url" :alt="selectedProduct.banka_adi" class="w-full h-full object-contain" />
              </div>
              <div class="min-w-0 flex-1">
                <div class="flex items-center gap-2 flex-wrap">
                  <h2 class="text-base font-black text-neutral-900 dark:text-white leading-snug">{{ selectedProduct.banka_adi }}</h2>
                  <span class="text-[10px] font-bold px-2 py-0.5 rounded-md bg-blue-50 dark:bg-blue-900/40 text-blue-700 dark:text-cyan-300 border border-blue-200/60 dark:border-blue-800/40 uppercase">
                    {{ getCategoryLabel(selectedProduct.urun) }}
                  </span>
                </div>
                <div class="flex items-center gap-2 mt-1 text-xs text-neutral-400">
                  <span class="font-semibold text-neutral-500 dark:text-neutral-300">{{ selectedProduct.tier }}</span>
                  <span>•</span>
                  <span>{{ selectedProduct.guncellenme_tarihi }}</span>
                </div>
              </div>
            </div>

            <!-- Vurgulu Finansal Parametreler (Grid) -->
            <div class="grid grid-cols-2 gap-2.5">
              
              <!-- Kâr Oranı -->
              <div class="bg-neutral-50 dark:bg-neutral-800/50 p-3.5 rounded-xl border border-neutral-100 dark:border-neutral-800">
                <div class="text-[10px] font-bold text-neutral-400 uppercase tracking-wider mb-0.5">{{ $t('financing.rate', 'Kâr Oranı') }}</div>
                <div class="text-lg font-black text-emerald-600 dark:text-emerald-400">{{ selectedProduct.kar_orani_str }}</div>
              </div>

              <!-- Finansman Tutarı -->
              <div class="bg-neutral-50 dark:bg-neutral-800/50 p-3.5 rounded-xl border border-neutral-100 dark:border-neutral-800">
                <div class="text-[10px] font-bold text-neutral-400 uppercase tracking-wider mb-0.5">{{ $t('financing.amount', 'Finansman Tutarı') }}</div>
                <div class="text-base font-extrabold text-neutral-900 dark:text-white">{{ formatCurrency(selectedProduct.finansman_tutari) }}</div>
              </div>

              <!-- Vade Süresi -->
              <div class="bg-neutral-50 dark:bg-neutral-800/50 p-3.5 rounded-xl border border-neutral-100 dark:border-neutral-800">
                <div class="text-[10px] font-bold text-neutral-400 uppercase tracking-wider mb-0.5">{{ $t('financing.term', 'Vade') }}</div>
                <div class="text-base font-extrabold text-neutral-900 dark:text-white">{{ selectedProduct.vade }} {{ $t('financing.term_months', 'Ay') }}</div>
              </div>

              <!-- Aylık Taksit -->
              <div class="bg-neutral-50 dark:bg-neutral-800/50 p-3.5 rounded-xl border border-neutral-100 dark:border-neutral-800">
                <div class="text-[10px] font-bold text-neutral-400 uppercase tracking-wider mb-0.5">{{ $t('financing.installment', 'Aylık Taksit') }}</div>
                <div class="text-base font-black text-blue-600 dark:text-cyan-400">{{ selectedProduct.aylik_taksit_str }}</div>
              </div>

            </div>

            <!-- Toplam Geri Ödeme Kartı -->
            <div class="p-4 rounded-2xl bg-gradient-to-br from-indigo-50/80 to-blue-50/80 dark:from-indigo-950/40 dark:to-blue-950/40 border border-indigo-200/70 dark:border-indigo-800/60">
              <div class="flex items-center justify-between">
                <div>
                  <span class="text-[11px] font-bold text-indigo-700 dark:text-indigo-300 uppercase tracking-wider block">
                    {{ $t('financing.total_payment', 'Toplam Geri Ödeme') }}
                  </span>
                  <span class="text-xl font-black text-indigo-900 dark:text-indigo-200 mt-1 block">
                    {{ selectedProduct.geri_odenecek_toplam_str }}
                  </span>
                </div>
                <div class="text-right text-xs text-indigo-600/80 dark:text-indigo-400">
                  <span class="text-[10px] block text-neutral-500 dark:text-neutral-400">{{ $t('financing.total_profit_share', 'Toplam Kâr Payı') }}</span>
                  <span class="font-extrabold text-sm">
                    {{ formatCurrency(Math.max(0, (selectedProduct.geri_odenecek_toplam_tutar || 0) - (selectedProduct.finansman_tutari || 0))) }}
                  </span>
                </div>
              </div>
            </div>

            <!-- Masraflar Dökümü -->
            <div class="bg-neutral-50 dark:bg-neutral-800/50 p-4 rounded-2xl border border-neutral-100 dark:border-neutral-800 space-y-2.5">
              <div class="text-[11px] font-bold text-neutral-400 uppercase tracking-wider mb-1">{{ $t('financing.fees_breakdown', 'Yasal Masraflar & Harçlar') }}</div>
              
              <div class="flex items-center justify-between text-xs py-1 border-b border-neutral-200/50 dark:border-neutral-700/50">
                <span class="text-neutral-600 dark:text-neutral-400">{{ $t('financing.allocation_fee', 'Tahsis Ücreti') }}</span>
                <span class="font-bold text-neutral-800 dark:text-neutral-200">{{ selectedProduct.tahsis_ucreti_str }}</span>
              </div>

              <div class="flex items-center justify-between text-xs py-1 border-b border-neutral-200/50 dark:border-neutral-700/50">
                <span class="text-neutral-600 dark:text-neutral-400">{{ $t('financing.appraisal_fee', 'Ekspertiz Ücreti') }}</span>
                <span class="font-bold text-neutral-800 dark:text-neutral-200">{{ selectedProduct.ekspertiz_ucreti_str }}</span>
              </div>

              <div class="flex items-center justify-between text-xs py-1">
                <span class="text-neutral-600 dark:text-neutral-400">{{ $t('financing.mortgage_fee', 'İpotek Tesis Ücreti') }}</span>
                <span class="font-bold text-neutral-800 dark:text-neutral-200">{{ selectedProduct.ipotek_tesis_ucreti_str }}</span>
              </div>
            </div>

            <!-- FinAgent ile Analiz Yap -->
            <div class="pt-2">
              <button 
                @click="askAiAboutProduct(selectedProduct)"
                class="w-full flex items-center justify-center gap-2.5 px-4 py-3.5 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white rounded-2xl text-xs sm:text-sm font-extrabold shadow-md hover:shadow-lg transition-all active:scale-98"
              >
                <img src="/logo.svg" class="w-4 h-4 object-contain brightness-0 invert" alt="" />
                <span>{{ $t('financing.ask_finagent', 'FinAgent ile Bu Finansmanı Analiz Et') }}</span>
              </button>
            </div>

          </div>
        </div>
      </Transition>
    </Teleport>

  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { gsap } from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'
import Lenis from 'lenis'

gsap.registerPlugin(ScrollTrigger)

let lenis = null
let lenisRafId = null

const router = useRouter()
const { t } = useI18n()

useHead({
  title: computed(() => t('page_titles.financing', 'Katılım Finansman Kâr Oranları'))
})

// Global Görünüm Modu (Müşteri vs Banka Çalışanı)
const globalViewMode = useState('globalViewMode', () => 'musteri')
const isBankaci = computed(() => globalViewMode.value === 'bankaci')

// Durumlar
const isLoading = ref(true)
const allProducts = ref([])
const availableBanks = ref([])
const availableCategories = ref([])
const availableAmounts = ref([])
const availableTerms = ref([])
const stats = ref({
  min_rate: 0,
  avg_rate: 0,
  min_installment: 0,
  min_total: 0,
  best_bank: '-'
})

// Filtre Seçimleri
const selectedCategory = ref('')
const selectedBanks = ref([])
const selectedTiers = ref([])
const selectedAmount = ref(null)
const selectedTerm = ref(null)
const sortBy = ref('rate_asc')
const viewMode = ref('grid')

const toggleBank = (code) => {
  const idx = selectedBanks.value.indexOf(code)
  if (idx > -1) {
    selectedBanks.value.splice(idx, 1)
  } else {
    selectedBanks.value.push(code)
  }
}

const toggleTier = (tVal) => {
  const idx = selectedTiers.value.indexOf(tVal)
  if (idx > -1) {
    selectedTiers.value.splice(idx, 1)
  } else {
    selectedTiers.value.push(tVal)
  }
}

const availableTiers = computed(() => {
  const set = new Set(allProducts.value.map(p => p.tier).filter(Boolean))
  return Array.from(set).sort()
})

// Sıralama Dropdown Menüsü (Campaigns Stili)
const isSortOpen = ref(false)
const sortOptions = computed(() => [
  { value: 'rate_asc', label: t('financing.sort_rate_asc', 'Kâr Oranı (En Düşük)') },
  { value: 'rate_desc', label: t('financing.sort_rate_desc', 'Kâr Oranı (En Yüksek)') },
  { value: 'installment_asc', label: t('financing.sort_installment_asc', 'Aylık Taksit (En Düşük)') },
  { value: 'total_asc', label: t('financing.sort_total_asc', 'Toplam Geri Ödeme (En Düşük)') },
  { value: 'term_asc', label: t('financing.sort_term_asc', 'Vade (Kısadan Uzuna)') },
  { value: 'term_desc', label: t('financing.sort_term_desc', 'Vade (Uzundan Kısaya)') },
])

const getSortLabel = (val) => {
  const match = sortOptions.value.find(s => s.value === val)
  return match ? match.label : val
}

// Seçili Finansman Detay Modalı (Sağ Açılır Panel)
const selectedProduct = ref(null)
const openProductDetails = (product) => {
  selectedProduct.value = product
}

// API'den Veri Çekme
const fetchFinancingData = async () => {
  isLoading.value = true
  try {
    const res = await fetch('http://localhost:8003/finansman')
    if (res.ok) {
      const data = await res.json()
      allProducts.value = data.products || []
      availableBanks.value = data.filters?.banks || []
      availableCategories.value = data.filters?.products || []
      availableAmounts.value = data.filters?.amounts || []
      availableTerms.value = data.filters?.terms || []
      stats.value = data.stats || {}
    }
  } catch (err) {
    console.error('Finansman verileri çekilemedi:', err)
  } finally {
    isLoading.value = false
  }
}

onMounted(() => {
  fetchFinancingData()
  if (process.client) {
    nextTick(() => {
      const scrollerEl = document.getElementById('main-scroller')
      if (scrollerEl) {
        const content = scrollerEl.querySelector('main') || scrollerEl.firstElementChild
        lenis = new Lenis({
          wrapper: scrollerEl,
          content: content,
          duration: 1.15,
          easing: (t) => Math.min(1, 1.001 - Math.pow(2, -10 * t)),
          smoothWheel: true,
          gestureOrientation: 'vertical',
          touchMultiplier: 1.6
        })
        lenis.on('scroll', ScrollTrigger.update)
        const raf = (time) => {
          lenis?.raf(time)
          lenisRafId = requestAnimationFrame(raf)
        }
        lenisRafId = requestAnimationFrame(raf)
      }
    })
  }
})

onUnmounted(() => {
  if (lenisRafId) {
    cancelAnimationFrame(lenisRafId)
    lenisRafId = null
  }
  if (lenis) {
    lenis.destroy()
    lenis = null
  }
  ScrollTrigger.getAll().forEach(t => t.kill())
})

// Filtrelenmiş ve Sıralanmış Ürünler
const filteredProducts = computed(() => {
  let list = [...allProducts.value]

  if (selectedCategory.value) {
    list = list.filter(p => p.urun === selectedCategory.value)
  }

  if (selectedBanks.value.length > 0) {
    list = list.filter(p => selectedBanks.value.includes(p.banka_kodu) || selectedBanks.value.includes(p.banka_id))
  }

  if (selectedTiers.value.length > 0) {
    list = list.filter(p => selectedTiers.value.includes(p.tier))
  }

  if (selectedAmount.value !== null) {
    list = list.filter(p => p.finansman_tutari === selectedAmount.value)
  }

  if (selectedTerm.value !== null) {
    list = list.filter(p => p.vade === selectedTerm.value)
  }

  // Sıralama
  switch (sortBy.value) {
    case 'rate_asc':
      list.sort((a, b) => (a.kar_orani <= 0 ? 1 : 0) - (b.kar_orani <= 0 ? 1 : 0) || a.kar_orani - b.kar_orani)
      break
    case 'rate_desc':
      list.sort((a, b) => b.kar_orani - a.kar_orani)
      break
    case 'installment_asc':
      list.sort((a, b) => a.aylik_taksit_tutari - b.aylik_taksit_tutari)
      break
    case 'total_asc':
      list.sort((a, b) => a.geri_odenecek_toplam_tutar - b.geri_odenecek_toplam_tutar)
      break
    case 'term_asc':
      list.sort((a, b) => a.vade - b.vade)
      break
    case 'term_desc':
      list.sort((a, b) => b.vade - a.vade)
      break
  }

  return list
})

const hasActiveFilters = computed(() => {
  return selectedCategory.value !== '' || selectedBanks.value.length > 0 || selectedTiers.value.length > 0 || selectedAmount.value !== null || selectedTerm.value !== null
})

const clearFilters = () => {
  selectedCategory.value = ''
  selectedBanks.value = []
  selectedTiers.value = []
  selectedAmount.value = null
  selectedTerm.value = null
  sortBy.value = 'rate_asc'
}

const countByCategory = (cat) => {
  return allProducts.value.filter(p => p.urun === cat).length
}

const getCategoryLabel = (cat) => {
  const map = {
    'ihtiyac': t('financing.ihtiyac', 'İhtiyaç'),
    'konut': t('financing.konut', 'Konut'),
    'tasit': t('financing.tasit', 'Taşıt')
  }
  return map[cat] || cat
}

const formatCurrency = (val) => {
  if (val === null || val === undefined || isNaN(val)) return '-'
  return new Intl.NumberFormat('tr-TR', { maximumFractionDigits: 2 }).format(val) + ' ₺'
}

const formatCompactNumber = (val) => {
  if (!val) return '0'
  return new Intl.NumberFormat('tr-TR').format(val)
}

// FinAgent Sohbetine Yönlendirme
const askAiAboutProduct = (product) => {
  const prompt = `${product.banka_adi} bankasının ${product.finansman_tutari.toLocaleString('tr-TR')} TL tutarındaki ${product.vade} ay vadeli ${getCategoryLabel(product.urun)} Finansmanı kâr oranını (%${product.kar_orani.toFixed(2).replace('.', ',')}) ve aylık ${product.aylik_taksit_str} taksit seçeneğini sektördeki diğer katılım bankalarıyla karşılaştırarak detaylı analiz et.`
  
  if (process.client) {
    sessionStorage.setItem('finagent_direct_prompt', prompt)
    sessionStorage.setItem('finagent_auto_send', 'true')
  }
  router.push('/chat')
}

const escapeHtml = (unsafe) => {
  if (!unsafe) return ''
  return String(unsafe)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;')
}

const formatProfitRate = (p) => {
  if (p.kar_orani !== null && p.kar_orani !== undefined && !isNaN(p.kar_orani) && Number(p.kar_orani) > 0) {
    return `%${Number(p.kar_orani).toFixed(2).replace('.', ',')}`
  }
  if (p.kar_orani_str) {
    let s = String(p.kar_orani_str).trim()
    if (!s.startsWith('%')) s = '%' + s
    return s
  }
  return '-'
}

const formatFee = (val) => {
  if (!val || val === '0' || val === 0) return '0 ₺'
  const num = typeof val === 'number' ? val : parseFloat(String(val).replace(/[^0-9.,]/g, '').replace(',', '.'))
  if (isNaN(num) || num === 0) return '0 ₺'
  return new Intl.NumberFormat('tr-TR', { maximumFractionDigits: 0 }).format(num) + ' ₺'
}

// Dışa Aktarma
const betigiYukle = (src, globalName) => {
  return new Promise((resolve, reject) => {
    if (window[globalName]) return resolve()
    const s = document.createElement('script')
    s.src = src
    s.onload = resolve
    s.onerror = reject
    document.head.appendChild(s)
  })
}

const exportData = async (type) => {
  if (filteredProducts.value.length === 0) return

  if (type === 'excel') {
    let csv = '\uFEFFBanka;Kategori;Tier;Finansman Tutari (TL);Vade (Ay);Kar Orani;Aylik Taksit (TL);Toplam Geri Odeme (TL);Tahsis Ucreti;Guncellenme Tarihi\n'
    filteredProducts.value.forEach(p => {
      csv += `"${p.banka_adi}";"${getCategoryLabel(p.urun)}";"${p.tier || ''}";"${p.finansman_tutari}";"${p.vade}";"${formatProfitRate(p)}";"${p.aylik_taksit_str}";"${p.geri_odenecek_toplam_str}";"${p.tahsis_ucreti_str}";"${p.guncellenme_tarihi}"\n`
    })
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
    const link = document.createElement('a')
    link.href = URL.createObjectURL(blob)
    link.download = `katilim_finansman_oranlari_${new Date().toISOString().slice(0, 10)}.csv`
    link.click()
  } else if (type === 'pdf') {
    try {
      await betigiYukle('https://cdnjs.cloudflare.com/ajax/libs/html2pdf.js/0.10.1/html2pdf.bundle.min.js', 'html2pdf')

      const today = new Date().toLocaleDateString('tr-TR', { day: '2-digit', month: 'long', year: 'numeric', hour: '2-digit', minute: '2-digit' })
      const activeFilterSummary = []
      if (selectedCategory.value) activeFilterSummary.push(`Kategori: ${getCategoryLabel(selectedCategory.value)}`)
      if (selectedBanks.value.length > 0) {
        const bNames = selectedBanks.value.map(code => {
          const bObj = availableBanks.value.find(b => b.code === code)
          return bObj ? bObj.name : code
        })
        activeFilterSummary.push(`Banka: ${bNames.join(', ')}`)
      }
      if (selectedTiers.value.length > 0) activeFilterSummary.push(`Tier: ${selectedTiers.value.join(', ')}`)
      if (selectedAmount.value !== null) activeFilterSummary.push(`Tutar: ${formatCurrency(selectedAmount.value)}`)
      if (selectedTerm.value !== null) activeFilterSummary.push(`Vade: ${selectedTerm.value} Ay`)

      // Sayfa Bölümleme (Sayfalara maksimum sayıda ürün sığdırma)
      const PAGE1_CHUNK_SIZE = 40
      const NEXT_PAGES_CHUNK_SIZE = 52

      const pages = []
      const remaining = [...filteredProducts.value]

      // 1. Sayfa
      pages.push({
        isFirst: true,
        items: remaining.splice(0, PAGE1_CHUNK_SIZE)
      })

      // Sonraki Sayfalar
      while (remaining.length > 0) {
        pages.push({
          isFirst: false,
          items: remaining.splice(0, NEXT_PAGES_CHUNK_SIZE)
        })
      }

      const totalPages = pages.length

      let html = `
        <div style="font-family: 'Segoe UI', Arial, sans-serif; color: #171717; background-color: #ffffff; width: 720px; margin: 0 auto; box-sizing: border-box;">`

      pages.forEach((page, pageIdx) => {
        const isLastPage = pageIdx === totalPages - 1
        const pageNumber = pageIdx + 1

        html += `
          <div style="box-sizing: border-box; width: 720px; min-height: 1020px; display: flex; flex-direction: column; justify-content: space-between; padding: 10px 5px 10px 5px; ${!isLastPage ? 'page-break-after: always;' : ''}">
            
            <!-- ÜST İÇERİK ALANI -->
            <div style="width: 100%;">
              ${page.isFirst ? `
                <!-- 1. SAYFA ANA BAŞLIK & MARKA -->
                <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #2563eb; padding-bottom: 8px; margin-bottom: 10px;">
                    <div>
                        <h1 style="color: #2563eb; margin: 0; font-size: 19px; font-weight: 800; letter-spacing: -0.5px;">
                            FinAgent · Katılım Finansman Oranları Raporu
                        </h1>
                        <p style="color: #6b7280; font-size: 10px; margin: 2px 0 0 0;">
                            Rapor Tarihi: ${escapeHtml(today)} ${activeFilterSummary.length ? `| Filtreler: ${escapeHtml(activeFilterSummary.join(', '))}` : ''}
                        </p>
                    </div>
                    <div style="text-align: right;">
                        <span style="font-size: 10.5px; font-weight: 700; color: #1e40af; background: #eff6ff; border: 1px solid #bfdbfe; padding: 2px 7px; border-radius: 5px;">
                            ${filteredProducts.value.length} Ürün Listelendi
                        </span>
                    </div>
                </div>

                <!-- ÖZET İSTATİSTİK KUTULARI (KPIs) -->
                <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 6px; margin-bottom: 10px;">
                    <div style="background-color: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 6px; padding: 6px 4px; text-align: center;">
                        <div style="font-size: 8.5px; font-weight: 700; color: #166534; text-transform: uppercase;">En Düşük Kâr Oranı</div>
                        <div style="font-size: 14px; font-weight: 900; color: #059669; margin-top: 1px;">${stats.value.min_rate > 0 ? '%' + stats.value.min_rate.toFixed(2).replace('.', ',') : '-'}</div>
                        <div style="font-size: 7.5px; color: #15803d; font-weight: 600;">${escapeHtml(stats.value.best_bank || '-')}</div>
                    </div>
                    <div style="background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px; padding: 6px 4px; text-align: center;">
                        <div style="font-size: 8.5px; font-weight: 700; color: #475569; text-transform: uppercase;">En Düşük Taksit</div>
                        <div style="font-size: 13.5px; font-weight: 900; color: #0f172a; margin-top: 1px;">${formatCurrency(stats.value.min_installment)}</div>
                        <div style="font-size: 7.5px; color: #64748b;">Seçili filtrelerde</div>
                    </div>
                    <div style="background-color: #eef2ff; border: 1px solid #c7d2fe; border-radius: 6px; padding: 6px 4px; text-align: center;">
                        <div style="font-size: 8.5px; font-weight: 700; color: #3730a3; text-transform: uppercase;">En Düşük Toplam Ödeme</div>
                        <div style="font-size: 13.5px; font-weight: 900; color: #4f46e5; margin-top: 1px;">${formatCurrency(stats.value.min_total)}</div>
                        <div style="font-size: 7.5px; color: #4338ca;">Tüm masraflar dahil</div>
                    </div>
                    <div style="background-color: #fffbeb; border: 1px solid #fde68a; border-radius: 6px; padding: 6px 4px; text-align: center;">
                        <div style="font-size: 8.5px; font-weight: 700; color: #92400e; text-transform: uppercase;">Sektör Ortalaması</div>
                        <div style="font-size: 14px; font-weight: 900; color: #d97706; margin-top: 1px;">${stats.value.avg_rate > 0 ? '%' + stats.value.avg_rate.toFixed(2).replace('.', ',') : '-'}</div>
                        <div style="font-size: 7.5px; color: #b45309;">${filteredProducts.value.length} ürün ortalaması</div>
                    </div>
                </div>
              ` : `
                <!-- DEVAM SAYFALARI ÜST BAŞLIĞI -->
                <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1.5px solid #e2e8f0; padding-bottom: 5px; margin-bottom: 8px;">
                    <div style="font-size: 11.5px; font-weight: 800; color: #2563eb;">
                        FinAgent · Katılım Finansman Oranları Raporu
                    </div>
                    <div style="font-size: 9px; color: #64748b;">
                        Rapor Tarihi: ${escapeHtml(today)}
                    </div>
                </div>
              `}

              <!-- FİNANSMAN DETAY TABLOSU -->
              <table style="width: 100%; border-collapse: collapse; font-size: 7.8px; table-layout: fixed; line-height: 1.15;">
                  <thead>
                      <tr style="background-color: #f1f5f9;">
                          <th style="width: 17%; padding: 4px 4px; border: 1px solid #cbd5e1; text-align: left; color: #1e293b; font-weight: 700;">Banka</th>
                          <th style="width: 15%; padding: 4px 4px; border: 1px solid #cbd5e1; text-align: left; color: #1e293b; font-weight: 700;">Kategori</th>
                          <th style="width: 14%; padding: 4px 4px; border: 1px solid #cbd5e1; text-align: right; color: #1e293b; font-weight: 700;">Tutar</th>
                          <th style="width: 8%; padding: 4px 3px; border: 1px solid #cbd5e1; text-align: center; color: #1e293b; font-weight: 700;">Vade</th>
                          <th style="width: 10%; padding: 4px 3px; border: 1px solid #cbd5e1; text-align: center; color: #059669; font-weight: 800;">Kâr Oranı</th>
                          <th style="width: 14%; padding: 4px 4px; border: 1px solid #cbd5e1; text-align: right; color: #1e293b; font-weight: 700;">Aylık Taksit</th>
                          <th style="width: 13%; padding: 4px 4px; border: 1px solid #cbd5e1; text-align: right; color: #4338ca; font-weight: 800;">Toplam Ödeme</th>
                          <th style="width: 9%; padding: 4px 3px; border: 1px solid #cbd5e1; text-align: right; color: #1e293b; font-weight: 700;">Tahsis</th>
                      </tr>
                  </thead>
                  <tbody>
                    ${page.items.map((p, idx) => `
                      <tr style="${idx % 2 === 1 ? 'background-color: #f8fafc;' : ''}">
                        <td style="padding: 2.8px 4px; border: 1px solid #e2e8f0; font-weight: 700; color: #1e40af; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${escapeHtml(p.banka_adi)}</td>
                        <td style="padding: 2.8px 4px; border: 1px solid #e2e8f0; font-weight: 500; text-transform: capitalize; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${escapeHtml(getCategoryLabel(p.urun))}</td>
                        <td style="padding: 2.8px 4px; border: 1px solid #e2e8f0; text-align: right; font-weight: 600; white-space: nowrap;">${formatCurrency(p.finansman_tutari)}</td>
                        <td style="padding: 2.8px 3px; border: 1px solid #e2e8f0; text-align: center; white-space: nowrap;">${p.vade} Ay</td>
                        <td style="padding: 2.8px 3px; border: 1px solid #e2e8f0; text-align: center; font-weight: 800; color: #059669; white-space: nowrap;">${formatProfitRate(p)}</td>
                        <td style="padding: 2.8px 4px; border: 1px solid #e2e8f0; text-align: right; font-weight: 700; color: #0f172a; white-space: nowrap;">${p.aylik_taksit_str}</td>
                        <td style="padding: 2.8px 4px; border: 1px solid #e2e8f0; text-align: right; font-weight: 800; color: #4338ca; white-space: nowrap;">${p.geri_odenecek_toplam_str}</td>
                        <td style="padding: 2.8px 3px; border: 1px solid #e2e8f0; text-align: right; color: #64748b; white-space: nowrap;">${formatFee(p.tahsis_ucreti)}</td>
                      </tr>
                    `).join('')}
                  </tbody>
              </table>
            </div>

            <!-- HER SAYFANIN ALTINDAKİ YASAL UYARI & ALTBİLGİ ALANI -->
            <div style="width: 100%; margin-top: auto; padding-top: 10px;">
              <div style="padding: 6px 10px; background-color: #f8fafc; border-left: 3px solid #94a3b8; border-radius: 4px; font-size: 8px; color: #64748b; font-style: italic; line-height: 1.35;">
                  Bu raporda yer alan veriler katılım bankalarının kamuya açık kâr payı tablolarından derlenmiştir. Yatırım tavsiyesi niteliğinde olmayıp, kesin finansman koşulları ve onay süreçleri ilgili bankaların yetkisindedir.
              </div>

              <div style="margin-top: 8px; padding-top: 6px; border-top: 1px solid #e5e7eb; display: flex; justify-content: space-between; align-items: center; font-size: 8.5px; color: #9ca3af;">
                  <span>Katılım Finansman Oranları · Bu rapor, FinAgent Yapay Zekâ platformu tarafından otomatik olarak oluşturulmuştur.</span>
                  <span style="font-weight: 700; color: #6b7280;">Sayfa ${pageNumber} / ${totalPages}</span>
              </div>
            </div>

          </div>
        `
      })

      html += `</div>`

      const tempDiv = document.createElement('div')
      tempDiv.innerHTML = html

      await window.html2pdf().set({
        margin:       [0.3, 0.3, 0.3, 0.3],
        filename:     `FinAgent_Finansman_Raporu_${Date.now()}.pdf`,
        image:        { type: 'jpeg', quality: 0.98 },
        html2canvas:  { scale: 2, backgroundColor: '#ffffff', useCORS: true },
        jsPDF:        { unit: 'in', format: 'a4', orientation: 'portrait' },
        pagebreak:    { mode: ['css', 'legacy'] },
      }).from(tempDiv).save()

    } catch (e) {
      console.error('PDF export hatası:', e)
    }
  } else if (type === 'png') {
    try {
      await betigiYukle('https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js', 'html2canvas')
      const target = document.getElementById('financing-content-area')
      if (!target) return

      const gizlenecekler = target.querySelectorAll('[data-png-gizle]')
      gizlenecekler.forEach(el => el.style.display = 'none')

      const canvas = await window.html2canvas(target, {
        scale: 2,
        useCORS: true,
        backgroundColor: document.documentElement.classList.contains('dark') ? '#171717' : '#ffffff'
      })

      gizlenecekler.forEach(el => el.style.display = '')

      const link = document.createElement('a')
      link.download = `finansman_oranlari_${Date.now()}.png`
      link.href = canvas.toDataURL('image/png')
      link.click()
    } catch (e) {
      console.error('PNG kaydetme hatası:', e)
    }
  }
}
</script>

<style scoped>
.gradient-text {
  background-image: linear-gradient(90deg, #2563eb, #06b6d4, #6366f1, #2563eb);
  background-size: 300% 100%;
  animation: gradShift 7s ease infinite;
}

@keyframes gradShift {
  0%, 100% { background-position: 0% 50%; }
  50% { background-position: 100% 50%; }
}

.reveal-title {
  opacity: 1;
  transform: none;
}

.title-underline {
  box-shadow: 0 0 12px rgba(6, 182, 212, 0.4);
}

.finagent-glow-btn {
  background: linear-gradient(135deg, rgba(37, 99, 235, 0.08), rgba(6, 182, 212, 0.08), rgba(99, 102, 241, 0.08));
  border: 1.5px solid rgba(37, 99, 235, 0.2);
  box-shadow: 0 0 15px -3px rgba(37, 99, 235, 0.15), 0 0 6px -2px rgba(6, 182, 212, 0.2);
}

:global(.dark) .finagent-glow-btn {
  background: linear-gradient(135deg, rgba(37, 99, 235, 0.15), rgba(6, 182, 212, 0.15), rgba(99, 102, 241, 0.15));
  border: 1.5px solid rgba(6, 182, 212, 0.35);
  box-shadow: 0 0 15px -3px rgba(6, 182, 212, 0.25), 0 0 6px -2px rgba(99, 102, 241, 0.3);
}

.finagent-glow-btn:hover {
  border-color: rgba(6, 182, 212, 0.6);
  box-shadow: 0 0 20px 2px rgba(6, 182, 212, 0.35), 0 0 10px 0px rgba(37, 99, 235, 0.4);
}

.logo-glow {
  filter: drop-shadow(0 0 5px rgba(6, 182, 212, 0.55)) drop-shadow(0 0 10px rgba(37, 99, 235, 0.35));
  animation: logoGlowShift 4s ease-in-out infinite alternate;
}

@keyframes logoGlowShift {
  0% {
    filter: drop-shadow(0 0 4px rgba(37, 99, 235, 0.5)) drop-shadow(0 0 8px rgba(6, 182, 212, 0.35));
  }
  50% {
    filter: drop-shadow(0 0 7px rgba(6, 182, 212, 0.75)) drop-shadow(0 0 14px rgba(99, 102, 241, 0.55));
  }
  100% {
    filter: drop-shadow(0 0 4px rgba(37, 99, 235, 0.5)) drop-shadow(0 0 8px rgba(6, 182, 212, 0.35));
  }
}

.custom-scrollbar::-webkit-scrollbar {
  height: 6px;
  width: 6px;
}
.custom-scrollbar::-webkit-scrollbar-thumb {
  background: rgba(150, 150, 150, 0.3);
  border-radius: 4px;
}
:global(.dark) .custom-scrollbar::-webkit-scrollbar-thumb {
  background: #475569;
}
</style>
