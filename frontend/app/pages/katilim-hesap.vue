<template>
  <div class="p-6 md:p-8 space-y-8 w-full max-w-[1400px] mx-auto min-h-full transition-transform duration-500 ease-[cubic-bezier(0.2,0.8,0.2,1)]"
       :class="selectedAccount ? 'lg:-translate-x-28 xl:-translate-x-32' : 'translate-x-0'">

    <!-- ================= ORTALANMIŞ BAŞLIK ================= -->
    <div class="flex flex-col items-center text-center gap-3 max-w-2xl mx-auto">
      <h1 class="reveal-title text-4xl md:text-5xl font-bold bg-clip-text text-transparent gradient-text pb-1">
        {{ $t('katilim_hesap.title', 'Katılım Hesabı Karşılaştırmaları') }}
      </h1>
      <p class="text-sm md:text-base text-neutral-500 dark:text-neutral-400">
        {{ $t('katilim_hesap.subtitle', 'Katılım bankalarının güncel kâr payı dağıtım oranları, brüt/net getiri tutarları ve vade sonu birikimlerini karşılaştırın.') }}
      </p>
      <div class="h-1 w-24 rounded-full bg-gradient-to-r from-emerald-500 to-teal-400 mt-1 title-underline"></div>
    </div>

    <!-- 2. ÖZET İSTATİSTİK KARTLARI (KPIs) - DİNAMİK FİLTRE HESAPLAMALI -->
    <div class="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
      
      <!-- En Yüksek Net Kâr Oranı -->
      <div class="p-4 rounded-2xl bg-white dark:bg-neutral-800/80 border border-neutral-200/80 dark:border-neutral-700 shadow-sm relative overflow-hidden flex flex-col justify-between">
        <div class="flex items-center justify-between gap-2 mb-2">
          <span class="text-xs font-bold text-neutral-500 dark:text-neutral-400">{{ $t('katilim_hesap.stat_max_net_rate', 'En Yüksek Net Kâr Oranı') }}</span>
          <span class="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
        </div>
        <div class="flex items-baseline gap-2">
          <span class="text-2xl sm:text-3xl font-black text-emerald-600 dark:text-emerald-400">
            {{ stats.max_net_rate > 0 ? '%' + stats.max_net_rate.toFixed(2).replace('.', ',') : '-' }}
          </span>
        </div>
        <div class="text-[11px] font-semibold text-neutral-500 dark:text-neutral-400 mt-1 truncate">
          {{ stats.best_bank || '-' }}
        </div>
      </div>

      <!-- En Yüksek Net Getiri Tutarı -->
      <div class="p-4 rounded-2xl bg-white dark:bg-neutral-800/80 border border-neutral-200/80 dark:border-neutral-700 shadow-sm relative overflow-hidden flex flex-col justify-between">
        <div class="flex items-center justify-between gap-2 mb-2">
          <span class="text-xs font-bold text-neutral-500 dark:text-neutral-400">{{ $t('katilim_hesap.stat_max_net_profit', 'En Yüksek Net Getiri') }}</span>
          <span class="w-2 h-2 rounded-full bg-teal-500"></span>
        </div>
        <div class="flex items-baseline gap-1">
          <span class="text-2xl sm:text-3xl font-black text-neutral-900 dark:text-white">
            {{ formatCurrency(stats.max_net_profit) }}
          </span>
        </div>
        <div class="text-[11px] font-semibold text-neutral-500 dark:text-neutral-400 mt-1">
          {{ $t('katilim_hesap.filter_amount_note', 'Seçili filtrelerde net kazanç') }}
        </div>
      </div>

      <!-- En Yüksek Brüt Kâr Oranı -->
      <div class="p-4 rounded-2xl bg-white dark:bg-neutral-800/80 border border-neutral-200/80 dark:border-neutral-700 shadow-sm relative overflow-hidden flex flex-col justify-between">
        <div class="flex items-center justify-between gap-2 mb-2">
          <span class="text-xs font-bold text-neutral-500 dark:text-neutral-400">{{ $t('katilim_hesap.stat_max_gross_rate', 'En Yüksek Brüt Oran') }}</span>
          <span class="w-2 h-2 rounded-full bg-cyan-500"></span>
        </div>
        <div class="flex items-baseline gap-1">
          <span class="text-2xl sm:text-3xl font-black text-cyan-600 dark:text-cyan-400">
            {{ stats.max_gross_rate > 0 ? '%' + stats.max_gross_rate.toFixed(2).replace('.', ',') : '-' }}
          </span>
        </div>
        <div class="text-[11px] font-semibold text-neutral-500 dark:text-neutral-400 mt-1">
          {{ $t('katilim_hesap.before_tax', 'Stopaj öncesi brüt kâr') }}
        </div>
      </div>

      <!-- Ortalama Sektör Net Kâr Oranı -->
      <div class="p-4 rounded-2xl bg-white dark:bg-neutral-800/80 border border-neutral-200/80 dark:border-neutral-700 shadow-sm relative overflow-hidden flex flex-col justify-between">
        <div class="flex items-center justify-between gap-2 mb-2">
          <span class="text-xs font-bold text-neutral-500 dark:text-neutral-400">{{ $t('katilim_hesap.stat_avg_net_rate', 'Ortalama Net Oran') }}</span>
          <span class="w-2 h-2 rounded-full bg-amber-500"></span>
        </div>
        <div class="flex items-baseline gap-2">
          <span class="text-2xl sm:text-3xl font-black text-amber-600 dark:text-amber-400">
            {{ stats.avg_net_rate > 0 ? '%' + stats.avg_net_rate.toFixed(2).replace('.', ',') : '-' }}
          </span>
        </div>
        <div class="text-[11px] font-semibold text-neutral-500 dark:text-neutral-400 mt-1">
          {{ filteredAccounts.length }} {{ $t('katilim_hesap.total_accounts_found', 'hesap seçeneği ortalaması') }}
        </div>
      </div>

    </div>

    <!-- 3. FİLTRELEME & KONTROL MERKEZİ -->
    <div class="p-5 rounded-3xl bg-white/90 dark:bg-neutral-900/90 backdrop-blur-md border border-neutral-200 dark:border-neutral-800 shadow-sm space-y-4 relative z-30">
      
      <div v-if="isSortOpen" @click="isSortOpen = false" class="fixed inset-0 z-40"></div>

      <!-- A. Üst Araçlar: Arama, Dışa Aktarma & Görünüm Seçici -->
      <div class="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 pb-3 border-b border-neutral-100 dark:border-neutral-800">
        
        <!-- Arama Çubuğu -->
        <div class="relative w-full sm:w-72">
          <svg class="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-neutral-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          <input 
            v-model="searchQuery" 
            type="text" 
            :placeholder="$t('katilim_hesap.search_placeholder', 'Banka veya vade ara...')" 
            class="w-full pl-9 pr-3 py-1.5 text-xs bg-neutral-100/80 dark:bg-neutral-800/80 border border-neutral-200 dark:border-neutral-700 rounded-xl focus:outline-none focus:ring-2 focus:ring-emerald-500 transition-all placeholder:text-neutral-400 text-neutral-800 dark:text-neutral-200"
          />
        </div>

        <!-- Sağ Araçlar: Dışa Aktarma, Görünüm Modu & Temizle -->
        <div class="flex items-center gap-2 self-end sm:self-auto flex-wrap" data-png-gizle>
          
          <!-- Dışa Aktarma Butonları -->
          <div class="flex items-center gap-1.5 mr-1">
            <button 
              @click="exportData('excel')" 
              :title="$t('katilim_hesap.export_excel', 'Excel İndir')" 
              class="p-2 bg-green-50 dark:bg-green-950/40 hover:bg-green-100 dark:hover:bg-green-900/50 text-green-700 dark:text-green-400 border border-green-200 dark:border-green-800/60 rounded-xl transition-all shadow-sm active:scale-95 group"
            >
              <svg class="w-4 h-4 group-hover:-translate-y-0.5 transition-transform" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
            </button>
            <button 
              @click="exportData('pdf')" 
              :title="$t('katilim_hesap.export_pdf', 'PDF İndir')" 
              class="p-2 bg-red-50 dark:bg-red-950/40 hover:bg-red-100 dark:hover:bg-red-900/50 text-red-700 dark:text-red-400 border border-red-200 dark:border-red-800/60 rounded-xl transition-all shadow-sm active:scale-95 group"
            >
              <svg class="w-4 h-4 group-hover:-translate-y-0.5 transition-transform" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
              </svg>
            </button>
            <button 
              @click="exportData('png')" 
              :title="$t('katilim_hesap.export_png', 'PNG İndir')" 
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
            {{ $t('katilim_hesap.clear_filters', 'Temizle') }}
          </button>

          <!-- Görünüm Değiştirici -->
          <div class="flex p-1 rounded-xl border border-neutral-300/50 dark:border-neutral-700/50 bg-neutral-100/60 dark:bg-neutral-800/60 backdrop-blur-sm shadow-sm gap-1">
            <button 
              @click="viewMode = 'grid'" 
              :class="viewMode === 'grid' ? 'bg-white dark:bg-neutral-700 text-emerald-600 dark:text-emerald-400 shadow-sm font-bold' : 'text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-white font-medium'"
              class="p-1.5 rounded-lg transition-all"
              :title="$t('katilim_hesap.grid_view', 'Kart Görünümü')"
            >
              <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z" />
              </svg>
            </button>
            <button 
              @click="viewMode = 'table'" 
              :class="viewMode === 'table' ? 'bg-white dark:bg-neutral-700 text-emerald-600 dark:text-emerald-400 shadow-sm font-bold' : 'text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-white font-medium'"
              class="p-1.5 rounded-lg transition-all"
              :title="$t('katilim_hesap.table_view', 'Tablo Görünümü')"
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
        
        <!-- Banka -->
        <div class="space-y-1.5">
          <div class="text-[11px] font-bold text-neutral-500 dark:text-neutral-400 uppercase tracking-wider">
            {{ $t('katilim_hesap.filter_bank', 'Banka') }}
          </div>
          <div class="inline-flex flex-wrap items-center p-1 rounded-xl border border-neutral-300/50 dark:border-neutral-700/50 bg-neutral-100/60 dark:bg-neutral-800/60 backdrop-blur-sm shadow-sm gap-1">
            <button 
              v-for="b in availableBanks" 
              :key="b.code"
              @click="toggleBank(b.code)"
              :class="selectedBanks.includes(b.code) ? 'bg-white dark:bg-neutral-700 text-emerald-600 dark:text-emerald-400 shadow-sm font-bold' : 'text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-white font-medium'"
              class="px-3 py-1.5 text-xs rounded-lg transition-all flex items-center gap-2 group"
            >
              <div class="w-5 h-5 rounded-md bg-white p-0.5 flex items-center justify-center shrink-0 shadow-2xs border border-neutral-200/60 dark:border-white/20 overflow-hidden">
                <img :src="b.logo_url" :alt="b.name" class="w-full h-full max-w-full max-h-full object-contain group-hover:scale-110 transition-transform" />
              </div>
              <span>{{ b.name }}</span>
            </button>
          </div>
        </div>

        <!-- Tier -->
        <div v-if="availableTiers.length" class="space-y-1.5">
          <div class="text-[11px] font-bold text-neutral-500 dark:text-neutral-400 uppercase tracking-wider">
            {{ $t('katilim_hesap.filter_tier', 'Tier') }}
          </div>
          <div class="inline-flex flex-wrap items-center p-1 rounded-xl border border-neutral-300/50 dark:border-neutral-700/50 bg-neutral-100/60 dark:bg-neutral-800/60 backdrop-blur-sm shadow-sm gap-1">
            <button 
              v-for="tVal in availableTiers" 
              :key="tVal"
              @click="toggleTier(tVal)"
              :class="selectedTiers.includes(tVal) ? 'bg-white dark:bg-neutral-700 text-emerald-600 dark:text-emerald-400 shadow-sm font-bold' : 'text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-white font-medium'"
              class="px-3 py-1.5 text-xs rounded-lg transition-all flex items-center"
            >
              <span>{{ tVal }}</span>
            </button>
          </div>
        </div>

      </div>

      <!-- C. Tutar, Vade & Sıralama Kontrolleri -->
      <div class="grid grid-cols-1 lg:grid-cols-12 gap-4 pt-3 border-t border-neutral-100 dark:border-neutral-800 items-start">
        
        <!-- Yatırılan Tutar Seçici (6 Kolon) -->
        <div class="lg:col-span-6 space-y-1.5">
          <label class="text-[11px] font-bold text-neutral-500 dark:text-neutral-400 uppercase tracking-wider block">
            {{ $t('katilim_hesap.filter_amount', 'Yatırılan Tutar') }}
          </label>
          <div class="flex flex-nowrap items-center p-1 rounded-xl border border-neutral-300/50 dark:border-neutral-700/50 bg-neutral-100/60 dark:bg-neutral-800/60 backdrop-blur-sm shadow-sm gap-1 overflow-x-auto">
            <button 
              v-for="amt in availableAmounts" 
              :key="amt"
              @click="selectedAmount = selectedAmount === amt ? null : amt"
              :class="selectedAmount === amt ? 'bg-white dark:bg-neutral-700 text-emerald-600 dark:text-emerald-400 shadow-sm font-bold' : 'text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-white font-medium'"
              class="flex-1 min-w-0 whitespace-nowrap px-2 py-1.5 text-center text-xs rounded-lg transition-all"
            >
              {{ formatCompactNumber(amt) }} ₺
            </button>
          </div>
        </div>

        <!-- Vade Seçici (3 Kolon) -->
        <div class="lg:col-span-3 space-y-1.5">
          <label class="text-[11px] font-bold text-neutral-500 dark:text-neutral-400 uppercase tracking-wider block">
            {{ $t('katilim_hesap.filter_term', 'Vade') }}
          </label>
          <div class="flex flex-nowrap items-center p-1 rounded-xl border border-neutral-300/50 dark:border-neutral-700/50 bg-neutral-100/60 dark:bg-neutral-800/60 backdrop-blur-sm shadow-sm gap-1 overflow-x-auto no-scrollbar">
            <button 
              v-for="term in availableTerms" 
              :key="term"
              :title="term"
              @click="selectedTerm = selectedTerm === term ? null : term"
              :class="selectedTerm === term ? 'bg-white dark:bg-neutral-700 text-emerald-600 dark:text-emerald-400 shadow-sm font-bold' : 'text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-white font-medium'"
              class="flex-1 min-w-[50px] whitespace-nowrap px-2 py-1.5 text-center text-xs rounded-lg transition-all"
            >
              {{ formatTermLabel(term) }}
            </button>
          </div>
        </div>

        <!-- Sıralama Dropdown Menüsü (3 Kolon) -->
        <div class="lg:col-span-3 space-y-1.5 relative">
          <label class="text-[11px] font-bold text-neutral-500 dark:text-neutral-400 uppercase tracking-wider block">
            {{ $t('katilim_hesap.filter_sort', 'Sıralama') }}
          </label>
          <div class="relative">
            <button 
              @click="isSortOpen = !isSortOpen"
              class="w-full flex items-center justify-between px-3 py-2 text-xs bg-white dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 rounded-xl font-medium text-neutral-700 dark:text-neutral-200 shadow-sm hover:border-emerald-500/50 transition-all text-left"
            >
              <span class="truncate">{{ getSortLabel(sortBy) }}</span>
              <svg class="w-4 h-4 text-neutral-400 ml-1 transition-transform" :class="isSortOpen ? 'rotate-180' : ''" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
              </svg>
            </button>

            <!-- Dropdown Menü -->
            <transition enter-active-class="transition duration-100 ease-out" enter-from-class="transform scale-95 opacity-0" enter-to-class="transform scale-100 opacity-100" leave-active-class="transition duration-75 ease-in" leave-from-class="transform scale-100 opacity-100" leave-to-class="transform scale-95 opacity-0">
              <div 
                v-if="isSortOpen" 
                class="absolute right-0 top-full mt-1.5 w-56 bg-white dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 rounded-2xl shadow-xl z-50 p-1.5 space-y-0.5 max-h-60 overflow-y-auto"
              >
                <button
                  v-for="opt in sortOptions"
                  :key="opt.value"
                  @click="sortBy = opt.value; isSortOpen = false"
                  :class="sortBy === opt.value ? 'bg-emerald-50 dark:bg-emerald-950/40 text-emerald-600 dark:text-emerald-400 font-bold' : 'text-neutral-600 dark:text-neutral-300 hover:bg-neutral-100 dark:hover:bg-neutral-700/50 font-medium'"
                  class="w-full text-left px-3 py-2 text-xs rounded-xl transition-all flex items-center justify-between"
                >
                  <span>{{ opt.label }}</span>
                  <svg v-if="sortBy === opt.value" class="w-4 h-4 text-emerald-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
                  </svg>
                </button>
              </div>
            </transition>
          </div>
        </div>

      </div>

    </div>

    <!-- ================= 4. İÇERİK LİSTESİ ================= -->
    <div id="katilim-content-area" class="relative min-h-[400px]">
      
      <!-- Yükleniyor Durumu -->
      <div v-if="isLoading" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <div v-for="i in 6" :key="i" class="p-6 rounded-3xl bg-white dark:bg-neutral-800/60 border border-neutral-200/80 dark:border-neutral-700/60 animate-pulse space-y-4">
          <div class="flex items-center justify-between">
            <div class="w-10 h-10 bg-neutral-200 dark:bg-neutral-700 rounded-xl"></div>
            <div class="w-20 h-6 bg-neutral-200 dark:bg-neutral-700 rounded-full"></div>
          </div>
          <div class="h-6 w-3/4 bg-neutral-200 dark:bg-neutral-700 rounded-lg"></div>
          <div class="grid grid-cols-2 gap-3 pt-3 border-t border-neutral-100 dark:border-neutral-700/40">
            <div class="h-10 bg-neutral-200 dark:bg-neutral-700 rounded-xl"></div>
            <div class="h-10 bg-neutral-200 dark:bg-neutral-700 rounded-xl"></div>
          </div>
        </div>
      </div>

      <!-- Boş Sonuç Durumu -->
      <div v-else-if="filteredAccounts.length === 0" class="flex flex-col items-center justify-center p-12 text-center bg-white dark:bg-neutral-800/40 rounded-3xl border border-neutral-200 dark:border-neutral-800 space-y-3">
        <div class="p-3 rounded-2xl bg-neutral-100 dark:bg-neutral-800 text-neutral-400">
          <svg class="w-8 h-8" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        </div>
        <div class="text-base font-bold text-neutral-800 dark:text-white">
          {{ $t('katilim_hesap.no_results_title', 'Seçilen Filtrelerde Katılım Hesabı Bulunamadı') }}
        </div>
        <p class="text-xs text-neutral-500 dark:text-neutral-400 max-w-sm">
          {{ $t('katilim_hesap.no_results_desc', 'Filtre kriterlerinizi temizleyerek veya farklı bir tutar/vade seçerek tekrar deneyebilirsiniz.') }}
        </p>
        <button 
          @click="clearFilters" 
          class="mt-2 px-4 py-2 text-xs font-semibold bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl shadow-md transition-all active:scale-95"
        >
          {{ $t('katilim_hesap.clear_filters', 'Tüm Filtreleri Temizle') }}
        </button>
      </div>

      <!-- A. KART GÖRÜNÜMÜ (MÜŞTERİ: YATAY DİKDÖRTGEN, BANKA ÇALIŞANI: 3 KOLONLU GRID) -->
      <template v-else-if="viewMode === 'grid'">

        <!-- 1. MÜŞTERİ GÖRÜNÜMÜ: YATAY DİKDÖRTGEN KARTLAR -->
        <div v-if="!isBankaci" class="flex flex-col space-y-3.5">
          <div 
            v-for="account in filteredAccounts" 
            :key="account.id"
            @click="openAccountDetails(account)"
            class="p-4 sm:p-5 rounded-2xl sm:rounded-3xl transition-all flex flex-col lg:flex-row lg:items-center justify-between gap-4 sm:gap-6 group cursor-pointer active:scale-[0.998] relative overflow-hidden"
            :class="isHighlighted(account) 
              ? 'bg-gradient-to-r from-emerald-500/[0.07] via-white to-white dark:from-emerald-500/[0.08] dark:via-neutral-800/95 dark:to-neutral-800/95 border-2 border-emerald-500/60 dark:border-emerald-500/50 shadow-md shadow-emerald-500/10 hover:border-emerald-500' 
              : 'bg-white dark:bg-neutral-800/90 border border-neutral-200/80 dark:border-neutral-700/80 shadow-sm hover:shadow-md hover:border-emerald-300 dark:hover:border-emerald-700'"
          >
            <!-- Sol Alan: Banka Bilgisi, Logo & Vade -->
            <div class="flex items-center gap-3 sm:gap-4 lg:w-64 shrink-0">
              <div class="w-12 h-12 rounded-2xl bg-white border border-neutral-200/80 dark:border-white/20 flex items-center justify-center p-2 shrink-0 shadow-xs group-hover:scale-105 transition-transform">
                <img :src="account.logo_url" :alt="account.banka_adi" class="w-full h-full object-contain" />
              </div>
              <div class="min-w-0">
                <div class="flex items-center gap-1.5 flex-wrap">
                  <h3 class="text-sm sm:text-base font-extrabold text-neutral-900 dark:text-white leading-snug truncate">{{ account.banka_adi }}</h3>
                  <span class="text-[10px] font-bold px-1.5 py-0.5 rounded-md bg-emerald-50 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-300 border border-emerald-200/60 dark:border-emerald-800/40 uppercase shrink-0">
                    {{ account.vade }}
                  </span>
                </div>
                <div class="flex items-center gap-2 mt-1 text-[11px] text-neutral-400">
                  <span>{{ account.tier }}</span>
                  <span>•</span>
                  <span>{{ account.guncellenme_tarihi }}</span>
                </div>
                <!-- Vurgulu En Yüksek Rozetleri -->
                <div v-if="isHighlighted(account)" class="flex items-center gap-1.5 flex-wrap mt-1.5">
                  <span v-if="isMaxNetRate(account)" class="px-1.5 py-0.5 text-[9px] font-black rounded-md bg-emerald-100 text-emerald-800 dark:bg-emerald-950/90 dark:text-emerald-300 border border-emerald-300 dark:border-emerald-700/70 flex items-center gap-1 shadow-xs">
                    <span class="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></span>
                    {{ $t('katilim_hesap.badge_max_net_rate', 'En Yüksek Net Oran') }}
                  </span>
                  <span v-if="isMaxNetProfit(account)" class="px-1.5 py-0.5 text-[9px] font-black rounded-md bg-teal-100 text-teal-800 dark:bg-teal-950/90 dark:text-teal-300 border border-teal-300 dark:border-teal-700/70 flex items-center gap-1 shadow-xs">
                    <span class="w-1.5 h-1.5 rounded-full bg-teal-500"></span>
                    {{ $t('katilim_hesap.badge_max_net_profit', 'En Yüksek Getiri') }}
                  </span>
                  <span v-if="isMaxGrossRate(account)" class="px-1.5 py-0.5 text-[9px] font-black rounded-md bg-cyan-100 text-cyan-800 dark:bg-cyan-950/90 dark:text-cyan-300 border border-cyan-300 dark:border-cyan-700/70 flex items-center gap-1 shadow-xs">
                    <span class="w-1.5 h-1.5 rounded-full bg-cyan-500"></span>
                    {{ $t('katilim_hesap.badge_max_gross_rate', 'En Yüksek Brüt Oran') }}
                  </span>
                </div>
              </div>
            </div>

            <!-- Orta Alan: Getiri Metrikleri (Yatay Kolonlar) -->
            <div class="grid grid-cols-2 sm:grid-cols-4 gap-3 sm:gap-4 flex-1 py-3 lg:py-0 border-y lg:border-y-0 lg:border-x border-neutral-100 dark:border-neutral-700/60 lg:px-6">
              
              <!-- Net Kâr Oranı -->
              <div class="flex flex-col justify-center">
                <span class="text-[10px] font-bold text-neutral-400 uppercase tracking-wider">{{ $t('katilim_hesap.net_rate', 'Net Oran') }}</span>
                <span class="text-base sm:text-lg font-black text-emerald-600 dark:text-emerald-400 mt-0.5" :class="isMaxNetRate(account) ? 'underline decoration-emerald-400 decoration-2 underline-offset-2' : ''">
                  {{ account.net_oran_str }}
                </span>
                <span class="text-[10px] text-neutral-400">
                  {{ $t('katilim_hesap.gross_rate', 'Brüt') }}: {{ account.brut_oran_str }}
                </span>
              </div>

              <!-- Yatırılan Tutar -->
              <div class="flex flex-col justify-center">
                <span class="text-[10px] font-bold text-neutral-400 uppercase tracking-wider">{{ $t('katilim_hesap.deposit_amount', 'Yatırılan Tutar') }}</span>
                <span class="text-xs sm:text-sm font-extrabold text-neutral-800 dark:text-neutral-200 mt-0.5">
                  {{ account.yatirilan_tutar_str }}
                </span>
                <span class="text-[11px] font-semibold text-neutral-500 dark:text-neutral-400">
                  {{ account.vade }}
                </span>
              </div>

              <!-- Net Kâr Getirisi -->
              <div class="flex flex-col justify-center">
                <span class="text-[10px] font-bold text-neutral-400 uppercase tracking-wider">{{ $t('katilim_hesap.net_profit', 'Net Kâr Getirisi') }}</span>
                <span class="text-sm sm:text-base font-black text-emerald-600 dark:text-emerald-400 mt-0.5" :class="isMaxNetProfit(account) ? 'text-teal-600 dark:text-teal-400' : ''">
                  {{ account.net_kar_str }}
                </span>
                <span class="text-[10px] text-red-500/80">
                  {{ $t('katilim_hesap.col_tax', 'Stopaj') }}: {{ account.stopaj_kesintisi_str }}
                </span>
              </div>

              <!-- Vade Sonu Toplam Bakiye -->
              <div class="flex flex-col justify-center">
                <span class="text-[10px] font-bold text-neutral-400 uppercase tracking-wider">{{ $t('katilim_hesap.maturity_total', 'Vade Sonu Toplam') }}</span>
                <span class="text-sm sm:text-base font-black text-neutral-900 dark:text-white mt-0.5">
                  {{ account.toplam_str }}
                </span>
                <span class="text-[10px] text-neutral-400">
                  {{ $t('katilim_hesap.principal_plus_profit', 'Ana Para + Kâr Payı') }}
                </span>
              </div>

            </div>

            <!-- Sağ Alan: Parlayan FinAgent Logosu Butonu -->
            <div class="flex items-center justify-end shrink-0 pl-2">
              <button 
                @click.stop="askAiAboutAccount(account)"
                :title="$t('katilim_hesap.ai_ask_tooltip', 'FinAgent ile Kâr Payı Getirisini Analiz Et')"
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
            v-for="account in filteredAccounts" 
            :key="account.id"
            class="p-5 rounded-3xl transition-all flex flex-col justify-between group cursor-pointer active:scale-[0.99] relative overflow-hidden"
            @click="openAccountDetails(account)"
            :class="isHighlighted(account) 
              ? 'bg-gradient-to-br from-emerald-500/[0.07] via-white to-white dark:from-emerald-500/[0.08] dark:via-neutral-800/95 dark:to-neutral-800/95 border-2 border-emerald-500/60 dark:border-emerald-500/50 shadow-md shadow-emerald-500/10 hover:border-emerald-500' 
              : 'bg-white dark:bg-neutral-800/90 border border-neutral-200/80 dark:border-neutral-700/80 shadow-sm hover:shadow-md hover:border-emerald-300 dark:hover:border-emerald-700'"
          >
            <!-- Kart Başlığı -->
            <div>
              <div class="flex items-start justify-between gap-3 pb-3 border-b border-neutral-100 dark:border-neutral-700/60">
                <div class="flex items-center gap-2.5">
                  <div class="w-10 h-10 rounded-2xl bg-white border border-neutral-200/80 dark:border-white/20 flex items-center justify-center p-1.5 shrink-0 shadow-xs">
                    <img :src="account.logo_url" :alt="account.banka_adi" class="w-full h-full object-contain" />
                  </div>
                  <div>
                    <h3 class="text-sm font-extrabold text-neutral-900 dark:text-white leading-snug">{{ account.banka_adi }}</h3>
                    <div class="flex items-center gap-1.5 mt-0.5 flex-wrap">
                      <span class="text-[10px] font-bold px-2 py-0.5 rounded-md bg-emerald-50 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-300 border border-emerald-200/60 dark:border-emerald-800/40 uppercase">
                        {{ account.vade }}
                      </span>
                      <span class="text-[10px] font-semibold text-neutral-400">{{ account.tier }}</span>
                    </div>
                    <!-- Vurgulu En Yüksek Rozetleri -->
                    <div v-if="isHighlighted(account)" class="flex items-center gap-1 flex-wrap mt-1.5">
                      <span v-if="isMaxNetRate(account)" class="px-1.5 py-0.5 text-[9px] font-black rounded-md bg-emerald-100 text-emerald-800 dark:bg-emerald-950/90 dark:text-emerald-300 border border-emerald-300 dark:border-emerald-700/70 flex items-center gap-1">
                        <span class="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></span>
                        {{ $t('katilim_hesap.badge_max_net_rate', 'En Yüksek Net Oran') }}
                      </span>
                      <span v-if="isMaxNetProfit(account)" class="px-1.5 py-0.5 text-[9px] font-black rounded-md bg-teal-100 text-teal-800 dark:bg-teal-950/90 dark:text-teal-300 border border-teal-300 dark:border-teal-700/70 flex items-center gap-1">
                        <span class="w-1.5 h-1.5 rounded-full bg-teal-500"></span>
                        {{ $t('katilim_hesap.badge_max_net_profit', 'En Yüksek Getiri') }}
                      </span>
                      <span v-if="isMaxGrossRate(account)" class="px-1.5 py-0.5 text-[9px] font-black rounded-md bg-cyan-100 text-cyan-800 dark:bg-cyan-950/90 dark:text-cyan-300 border border-cyan-300 dark:border-cyan-700/70 flex items-center gap-1">
                        <span class="w-1.5 h-1.5 rounded-full bg-cyan-500"></span>
                        {{ $t('katilim_hesap.badge_max_gross_rate', 'En Yüksek Brüt Oran') }}
                      </span>
                    </div>
                  </div>
                </div>

                <!-- Vurgulu Net Kâr Oranı Rozeti -->
                <div class="text-right">
                  <div class="text-[10px] font-bold text-neutral-400 uppercase tracking-wider">{{ $t('katilim_hesap.net_rate', 'Net Oran') }}</div>
                  <div class="text-lg font-black text-emerald-600 dark:text-emerald-400">
                    {{ account.net_oran_str }}
                  </div>
                </div>
              </div>

              <!-- Tutar & Vade Özeti -->
              <div class="my-4 p-3 rounded-2xl bg-neutral-50 dark:bg-neutral-900/60 border border-neutral-100 dark:border-neutral-800 grid grid-cols-2 gap-2 text-center">
                <div>
                  <div class="text-[10px] font-bold text-neutral-400 uppercase">{{ $t('katilim_hesap.deposit_amount', 'Yatırılan Tutar') }}</div>
                  <div class="text-xs font-extrabold text-neutral-800 dark:text-neutral-200 mt-0.5">
                    {{ account.yatirilan_tutar_str }}
                  </div>
                </div>
                <div class="border-l border-neutral-200 dark:border-neutral-800">
                  <div class="text-[10px] font-bold text-neutral-400 uppercase">{{ $t('katilim_hesap.filter_term', 'Vade') }}</div>
                  <div class="text-xs font-extrabold text-neutral-800 dark:text-neutral-200 mt-0.5">
                    {{ account.vade }}
                  </div>
                </div>
              </div>

              <!-- Getiri & Stopaj Hesaplama Detayları -->
              <div class="space-y-2 text-xs">
                <div class="flex items-center justify-between py-1 border-b border-neutral-100 dark:border-neutral-800">
                  <span class="text-neutral-500 dark:text-neutral-400">{{ $t('katilim_hesap.gross_rate', 'Brüt Kâr Oranı') }}</span>
                  <span class="font-semibold text-neutral-700 dark:text-neutral-300">
                    {{ account.brut_oran_str }}
                  </span>
                </div>

                <div class="flex items-center justify-between py-1 border-b border-neutral-100 dark:border-neutral-800">
                  <span class="text-neutral-500 dark:text-neutral-400">{{ $t('katilim_hesap.gross_profit', 'Brüt Kâr Getirisi') }}</span>
                  <span class="font-semibold text-neutral-700 dark:text-neutral-300">
                    {{ account.brut_kar_str }}
                  </span>
                </div>

                <div class="flex items-center justify-between py-1 border-b border-neutral-100 dark:border-neutral-800">
                  <span class="text-neutral-500 dark:text-neutral-400">{{ $t('katilim_hesap.withholding_tax', 'Stopaj Kesintisi (%7,5)') }}</span>
                  <span class="font-semibold text-red-500">
                    -{{ account.stopaj_kesintisi_str }}
                  </span>
                </div>

                <div class="flex items-center justify-between py-1 border-b border-neutral-100 dark:border-neutral-800">
                  <span class="font-bold text-neutral-800 dark:text-neutral-200">{{ $t('katilim_hesap.net_profit', 'Net Kâr Getirisi') }}</span>
                  <span class="font-black text-emerald-600 dark:text-emerald-400 text-sm">
                    {{ account.net_kar_str }}
                  </span>
                </div>

                <div class="flex items-center justify-between py-1">
                  <span class="font-bold text-neutral-800 dark:text-neutral-200">{{ $t('katilim_hesap.maturity_total', 'Vade Sonu Toplam') }}</span>
                  <span class="font-black text-neutral-900 dark:text-white text-sm">
                    {{ account.toplam_str }}
                  </span>
                </div>
              </div>
            </div>

            <!-- Kart Altı (Tarih & Parlayan Logo Butonu) -->
            <div class="mt-4 pt-3 border-t border-neutral-100 dark:border-neutral-700/60 flex items-center justify-between gap-2">
              <span class="text-[10px] text-neutral-400">
                {{ account.guncellenme_tarihi }}
              </span>
              <button 
                @click.stop="askAiAboutAccount(account)"
                :title="$t('katilim_hesap.ai_ask_tooltip', 'FinAgent ile Analiz Et')"
                class="finagent-glow-btn p-2 rounded-xl transition-all duration-300 hover:scale-110 active:scale-95 flex items-center justify-center cursor-pointer shadow-sm group/btn"
              >
                <img src="/logo.svg" class="w-4 h-4 object-contain logo-glow" alt="FinAgent" />
              </button>
            </div>
          </div>
        </div>

      </template>

      <!-- B. TABLO GÖRÜNÜMÜ -->
      <div v-else class="overflow-x-auto rounded-3xl border border-neutral-200 dark:border-neutral-800 bg-white/90 dark:bg-neutral-900/90 backdrop-blur-md shadow-sm">
        <table class="w-full text-left border-collapse text-xs">
          <thead>
            <tr class="border-b border-neutral-200 dark:border-neutral-800 bg-neutral-50/70 dark:bg-neutral-800/50 text-neutral-500 dark:text-neutral-400 font-bold uppercase tracking-wider">
              <th class="py-3.5 px-4">{{ $t('katilim_hesap.col_bank', 'Banka') }}</th>
              <th class="py-3.5 px-4">{{ $t('katilim_hesap.col_tier', 'Tier') }}</th>
              <th class="py-3.5 px-4">{{ $t('katilim_hesap.col_term', 'Vade') }}</th>
              <th class="py-3.5 px-4 text-right">{{ $t('katilim_hesap.col_amount', 'Yatırılan Tutar') }}</th>
              <th class="py-3.5 px-4 text-right">{{ $t('katilim_hesap.col_gross_rate', 'Brüt Oran') }}</th>
              <th class="py-3.5 px-4 text-right text-emerald-600 dark:text-emerald-400">{{ $t('katilim_hesap.col_net_rate', 'Net Oran') }}</th>
              <th class="py-3.5 px-4 text-right">{{ $t('katilim_hesap.col_gross_profit', 'Brüt Kâr') }}</th>
              <th class="py-3.5 px-4 text-right text-red-500">{{ $t('katilim_hesap.col_tax', 'Stopaj') }}</th>
              <th class="py-3.5 px-4 text-right font-black text-emerald-600 dark:text-emerald-400">{{ $t('katilim_hesap.col_net_profit', 'Net Kâr') }}</th>
              <th class="py-3.5 px-4 text-right font-black">{{ $t('katilim_hesap.col_total', 'Vade Sonu Toplam') }}</th>
              <th class="py-3.5 px-4 text-center">{{ $t('katilim_hesap.col_actions', 'İşlem') }}</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-neutral-100 dark:divide-neutral-800">
            <tr 
              v-for="account in filteredAccounts" 
              :key="account.id"
              class="transition-colors group cursor-pointer"
              :class="isHighlighted(account) ? 'bg-emerald-50/40 dark:bg-emerald-950/20 hover:bg-emerald-100/50 dark:hover:bg-emerald-900/30' : 'hover:bg-neutral-50/80 dark:hover:bg-neutral-800/40'"
              @click="openAccountDetails(account)"
            >
              <td class="py-3.5 px-4 font-bold text-neutral-900 dark:text-white flex items-center gap-2.5">
                <div class="w-6 h-6 rounded-md bg-white p-0.5 flex items-center justify-center shrink-0 shadow-2xs border border-neutral-200/60 dark:border-white/20">
                  <img :src="account.logo_url" :alt="account.banka_adi" class="w-full h-full object-contain" />
                </div>
                <div class="flex items-center gap-1.5 flex-wrap">
                  <span>{{ account.banka_adi }}</span>
                  <span v-if="isMaxNetRate(account)" class="px-1.5 py-0.5 text-[9px] font-bold rounded bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300 border border-emerald-300 dark:border-emerald-700">
                    {{ $t('katilim_hesap.badge_max_net_rate', 'En Yüksek Net Oran') }}
                  </span>
                </div>
              </td>
              <td class="py-3.5 px-4">
                <span class="text-[10px] font-semibold px-2 py-0.5 rounded bg-neutral-100 dark:bg-neutral-800 text-neutral-600 dark:text-neutral-300">
                  {{ account.tier }}
                </span>
              </td>
              <td class="py-3.5 px-4 font-semibold text-neutral-700 dark:text-neutral-300">
                {{ account.vade }}
              </td>
              <td class="py-3.5 px-4 text-right font-bold text-neutral-800 dark:text-neutral-200">
                {{ account.yatirilan_tutar_str }}
              </td>
              <td class="py-3.5 px-4 text-right font-medium text-neutral-600 dark:text-neutral-400">
                {{ account.brut_oran_str }}
              </td>
              <td class="py-3.5 px-4 text-right font-black text-emerald-600 dark:text-emerald-400">
                {{ account.net_oran_str }}
              </td>
              <td class="py-3.5 px-4 text-right font-semibold text-neutral-700 dark:text-neutral-300">
                {{ account.brut_kar_str }}
              </td>
              <td class="py-3.5 px-4 text-right font-semibold text-red-500">
                {{ account.stopaj_kesintisi_str }}
              </td>
              <td class="py-3.5 px-4 text-right font-black text-emerald-600 dark:text-emerald-400 text-sm">
                {{ account.net_kar_str }}
              </td>
              <td class="py-3.5 px-4 text-right font-black text-neutral-900 dark:text-white text-sm">
                {{ account.toplam_str }}
              </td>
              <td class="py-3.5 px-4 text-center">
                <div class="inline-flex items-center gap-1.5">
                  <button 
                    @click.stop="openAccountDetails(account)"
                    class="p-1.5 bg-neutral-100 hover:bg-emerald-500 hover:text-white dark:bg-neutral-800 dark:hover:bg-emerald-600 rounded-lg text-neutral-600 dark:text-neutral-300 transition-all shadow-sm"
                    :title="$t('katilim_hesap.calc_and_details', 'Hesapla & Detay')"
                  >
                    <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                    </svg>
                  </button>
                  <button 
                    @click.stop="askAiAboutAccount(account)"
                    class="finagent-glow-btn p-1.5 rounded-lg transition-all shadow-sm"
                    :title="$t('katilim_hesap.ai_ask_tooltip', 'FinAgent ile Analiz Et')"
                  >
                    <img src="/logo.svg" alt="FinAgent" class="w-4 h-4 object-contain logo-glow" />
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

    </div>

    <!-- ================= 5. KATILIM HESABI DETAY PANELİ (DRAWER / MODAL - NO BLUR) ================= -->
    <Teleport to="body">
      <Transition
        enter-active-class="transform transition-all duration-300 ease-out" 
        enter-from-class="translate-x-[120%] opacity-0 scale-95" 
        enter-to-class="translate-x-0 opacity-100 scale-100" 
        leave-active-class="transform transition-all duration-300 ease-in" 
        leave-from-class="translate-x-0 opacity-100 scale-100" 
        leave-to-class="translate-x-[120%] opacity-0 scale-95"
      >
        <div v-if="selectedAccount" class="fixed right-4 top-4 bottom-4 w-[340px] sm:w-[420px] lg:w-[480px] bg-white dark:bg-[#121212] rounded-[24px] shadow-[0_12px_40px_rgba(0,0,0,0.15)] dark:shadow-[0_12px_40px_rgba(0,0,0,0.7)] border border-neutral-200 dark:border-neutral-700 flex flex-col z-[100] overflow-hidden">
          
          <!-- Drawer Header -->
          <div class="flex justify-between items-center p-4 border-b border-neutral-200 dark:border-neutral-700 bg-neutral-50 dark:bg-neutral-800">
            <h3 class="text-[14px] font-bold flex items-center gap-2 text-neutral-800 dark:text-white">
              <svg class="w-4 h-4 text-emerald-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
              {{ $t('katilim_hesap.calc_and_details', 'Katılım Hesabı Detayları') }}
            </h3>
            <button @click="selectedAccount = null" class="p-1 text-neutral-500 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/30 rounded-lg transition-colors active:scale-90 transform duration-200" :title="$t('financing.close', 'Kapat')">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg>
            </button>
          </div>

          <!-- Drawer Body -->
          <div class="flex-1 overflow-y-auto p-4 lg:p-6 custom-scrollbar space-y-4">
            
            <!-- Banka Bilgisi ve Hesap Başlığı -->
            <div class="flex items-center gap-3 p-3.5 rounded-2xl bg-neutral-50 dark:bg-neutral-800/60 border border-neutral-100 dark:border-neutral-800">
              <div class="w-12 h-12 rounded-2xl bg-white border border-neutral-200/80 dark:border-white/20 flex items-center justify-center p-2 shrink-0 shadow-sm">
                <img :src="selectedAccount.logo_url" :alt="selectedAccount.banka_adi" class="w-full h-full object-contain" />
              </div>
              <div class="min-w-0 flex-1">
                <div class="flex items-center gap-2 flex-wrap">
                  <h2 class="text-base font-black text-neutral-900 dark:text-white leading-snug">{{ selectedAccount.banka_adi }}</h2>
                  <span v-if="selectedAccount.tier" class="text-[10px] font-bold px-2 py-0.5 rounded-md bg-blue-50 dark:bg-blue-900/40 text-blue-700 dark:text-cyan-300 border border-blue-200/60 dark:border-blue-800/40 uppercase">
                    {{ selectedAccount.tier }}
                  </span>
                </div>
                <div class="text-xs text-neutral-500 dark:text-neutral-400 truncate mt-0.5">
                  {{ selectedAccount.resmi_ad || selectedAccount.banka_adi }}
                </div>
              </div>
            </div>

            <!-- Vurgulu Finansal Parametreler (Grid) -->
            <div class="grid grid-cols-2 gap-2.5">
              
              <!-- Net Kâr Oranı -->
              <div class="bg-neutral-50 dark:bg-neutral-800/50 p-3.5 rounded-xl border border-neutral-100 dark:border-neutral-800">
                <div class="text-[10px] font-bold text-neutral-400 uppercase tracking-wider mb-0.5">{{ $t('katilim_hesap.col_net_rate', 'Net Kâr Oranı') }}</div>
                <div class="text-lg font-black text-emerald-600 dark:text-emerald-400">{{ selectedAccount.net_oran_str }}</div>
              </div>

              <!-- Yatırılan Tutar -->
              <div class="bg-neutral-50 dark:bg-neutral-800/50 p-3.5 rounded-xl border border-neutral-100 dark:border-neutral-800">
                <div class="text-[10px] font-bold text-neutral-400 uppercase tracking-wider mb-0.5">{{ $t('katilim_hesap.col_amount', 'Yatırılan Tutar') }}</div>
                <div class="text-base font-extrabold text-neutral-900 dark:text-white">{{ selectedAccount.yatirilan_tutar_str || formatCurrency(selectedAccount.yatirilan_tutar) }}</div>
              </div>

              <!-- Vade Süresi -->
              <div class="bg-neutral-50 dark:bg-neutral-800/50 p-3.5 rounded-xl border border-neutral-100 dark:border-neutral-800">
                <div class="text-[10px] font-bold text-neutral-400 uppercase tracking-wider mb-0.5">{{ $t('katilim_hesap.col_term', 'Vade') }}</div>
                <div class="text-base font-extrabold text-neutral-900 dark:text-white">{{ selectedAccount.vade }}</div>
              </div>

              <!-- Brüt Kâr Oranı -->
              <div class="bg-neutral-50 dark:bg-neutral-800/50 p-3.5 rounded-xl border border-neutral-100 dark:border-neutral-800">
                <div class="text-[10px] font-bold text-neutral-400 uppercase tracking-wider mb-0.5">{{ $t('katilim_hesap.col_gross_rate', 'Brüt Kâr Oranı') }}</div>
                <div class="text-base font-black text-blue-600 dark:text-cyan-400">{{ selectedAccount.brut_oran_str }}</div>
              </div>

            </div>

            <!-- Toplam Bakiye & Net Kâr Kartı -->
            <div class="p-4 rounded-2xl bg-gradient-to-br from-indigo-50/80 to-blue-50/80 dark:from-indigo-950/40 dark:to-blue-950/40 border border-indigo-200/70 dark:border-indigo-800/60">
              <div class="flex items-center justify-between">
                <div>
                  <span class="text-[11px] font-bold text-indigo-700 dark:text-indigo-300 uppercase tracking-wider block">
                    {{ $t('katilim_hesap.col_total', 'Vade Sonu Toplam Bakiye') }}
                  </span>
                  <span class="text-xl font-black text-indigo-900 dark:text-indigo-200 mt-1 block">
                    {{ selectedAccount.toplam_str || formatCurrency(selectedAccount.toplam) }}
                  </span>
                </div>
                <div class="text-right text-xs text-indigo-600/80 dark:text-indigo-400">
                  <span class="text-[10px] block text-neutral-500 dark:text-neutral-400">{{ $t('katilim_hesap.col_net_profit', 'Net Kâr Getirisi') }}</span>
                  <span class="font-extrabold text-sm text-emerald-600 dark:text-emerald-400">
                    {{ selectedAccount.net_kar_str || formatCurrency(selectedAccount.net_kar) }}
                  </span>
                </div>
              </div>
            </div>

            <!-- Getiri & Kesinti Dökümü -->
            <div class="bg-neutral-50 dark:bg-neutral-800/50 p-4 rounded-2xl border border-neutral-100 dark:border-neutral-800 space-y-2.5">
              <div class="text-[11px] font-bold text-neutral-400 uppercase tracking-wider mb-1">{{ $t('katilim_hesap.profit_breakdown', 'Getiri & Kesinti Dökümü') }}</div>
              
              <div class="flex items-center justify-between text-xs py-1 border-b border-neutral-200/50 dark:border-neutral-700/50">
                <span class="text-neutral-600 dark:text-neutral-400">{{ $t('katilim_hesap.col_gross_profit', 'Hesaplanan Brüt Kâr') }}</span>
                <span class="font-bold text-neutral-800 dark:text-neutral-200">{{ selectedAccount.brut_kar_str || formatCurrency(selectedAccount.brut_kar) }}</span>
              </div>

              <div class="flex items-center justify-between text-xs py-1 border-b border-neutral-200/50 dark:border-neutral-700/50">
                <span class="text-neutral-600 dark:text-neutral-400">{{ $t('katilim_hesap.withholding_tax', 'Yasal Stopaj Kesintisi (%7,5)') }}</span>
                <span class="font-bold text-red-500">{{ selectedAccount.stopaj_kesintisi_str || ('-' + formatCurrency(selectedAccount.stopaj_kesintisi)) }}</span>
              </div>

              <div class="flex items-center justify-between text-xs py-1">
                <span class="text-neutral-600 dark:text-neutral-400 font-semibold">{{ $t('katilim_hesap.col_net_profit', 'Net Kâr Payı Getirisi') }}</span>
                <span class="font-extrabold text-emerald-600 dark:text-emerald-400">{{ selectedAccount.net_kar_str || formatCurrency(selectedAccount.net_kar) }}</span>
              </div>
            </div>

            <!-- Yasal Bilgilendirme ve Güvence -->
            <div class="bg-neutral-50 dark:bg-neutral-800/50 p-3.5 rounded-2xl border border-neutral-100 dark:border-neutral-800 space-y-2 text-xs text-neutral-600 dark:text-neutral-400">
              <div class="font-bold text-neutral-800 dark:text-neutral-200 flex items-center gap-1.5">
                <svg class="w-4 h-4 text-emerald-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                </svg>
                <span>{{ $t('katilim_hesap.tmsf_guarantee_title', 'TMSF ve Katılım Fonu Güvencesi') }}</span>
              </div>
              <p class="leading-relaxed text-[11px]">
                {{ $t('katilim_hesap.tmsf_guarantee_desc', 'Katılım bankalarındaki gerçek kişilere ait katılım fonları, Tasarruf Mevduatı Sigorta Fonu (TMSF) güvencesi altındadır.') }}
              </p>
              <p class="text-[10.5px] text-neutral-400 leading-relaxed">
                {{ $t('katilim_hesap.profit_share_disclaimer', 'Katılım hesapları kâr-zarar ortaklığı prensibiyle çalışır; oranlar geçmiş dönem getirilerine ve piyasa şartlarına göre değişkenlik gösterebilir.') }}
              </p>
            </div>

            <!-- FinAgent ile Analiz Yap -->
            <div class="pt-2">
              <button 
                @click="askAiAboutAccount(selectedAccount)"
                class="w-full flex items-center justify-center gap-2.5 px-4 py-3.5 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white rounded-2xl text-xs sm:text-sm font-extrabold shadow-md hover:shadow-lg transition-all active:scale-98"
              >
                <img src="/logo.svg" class="w-4 h-4 object-contain brightness-0 invert" alt="" />
                <span>{{ $t('katilim_hesap.ai_ask_full_btn', "FinAgent ile Bu Getiriyi Analiz Et") }}</span>
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
import Lenis from 'lenis'
import { gsap } from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'

gsap.registerPlugin(ScrollTrigger)

const { t } = useI18n()
const router = useRouter()

let lenis = null
let lenisRafId = null

useHead({
  title: computed(() => t('page_titles.katilim_hesap', 'Katılım Hesabı Karşılaştırmaları'))
})

// Global Görünüm Modu (Müşteri vs Banka Çalışanı)
const globalViewMode = useState('globalViewMode', () => 'musteri')
const isBankaci = computed(() => globalViewMode.value === 'bankaci')

// Durumlar
const isLoading = ref(true)
const allAccounts = ref([])
const availableBanks = ref([])
const availableAmounts = ref([])
const availableTerms = ref([])

// Filtre Seçimleri
const searchQuery = ref('')
const selectedBanks = ref([])
const selectedTiers = ref([])
const selectedAmount = ref(null)
const selectedTerm = ref(null)
const sortBy = ref('net_rate_desc')
const viewMode = ref('grid')

// Sıralama Dropdown Menüsü
const isSortOpen = ref(false)
const sortOptions = computed(() => [
  { value: 'net_rate_desc', label: t('katilim_hesap.sort_net_rate_desc', 'Net Kâr Oranı (En Yüksek)') },
  { value: 'net_rate_asc', label: t('katilim_hesap.sort_net_rate_asc', 'Net Kâr Oranı (En Düşük)') },
  { value: 'gross_rate_desc', label: t('katilim_hesap.sort_gross_rate_desc', 'Brüt Kâr Oranı (En Yüksek)') },
  { value: 'net_profit_desc', label: t('katilim_hesap.sort_net_profit_desc', 'Net Getiri Tutarı (En Yüksek)') },
  { value: 'total_desc', label: t('katilim_hesap.sort_total_desc', 'Vade Sonu Toplam (En Yüksek)') },
  { value: 'amount_desc', label: t('katilim_hesap.sort_amount_desc', 'Tutar (Büyükten Küçüğe)') },
])

const getSortLabel = (val) => {
  const match = sortOptions.value.find(s => s.value === val)
  return match ? match.label : val
}

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
  const set = new Set(allAccounts.value.map(a => a.tier).filter(Boolean))
  return Array.from(set).sort()
})

// Filtrelenmiş ve Sıralanmış Hesaplar
const filteredAccounts = computed(() => {
  let list = [...allAccounts.value]

  if (searchQuery.value.trim()) {
    const q = searchQuery.value.trim().toLowerCase()
    list = list.filter(a => 
      a.banka_adi.toLowerCase().includes(q) ||
      a.vade.toLowerCase().includes(q) ||
      a.tier.toLowerCase().includes(q)
    )
  }

  if (selectedBanks.value.length > 0) {
    list = list.filter(a => selectedBanks.value.includes(a.banka_kodu) || selectedBanks.value.includes(a.banka_id))
  }

  if (selectedTiers.value.length > 0) {
    list = list.filter(a => selectedTiers.value.includes(a.tier))
  }

  if (selectedAmount.value !== null) {
    list = list.filter(a => Math.abs(a.yatirilan_tutar - selectedAmount.value) < 1)
  }

  if (selectedTerm.value !== null) {
    list = list.filter(a => a.vade === selectedTerm.value)
  }

  // Sıralama
  switch (sortBy.value) {
    case 'net_rate_desc':
      list.sort((a, b) => b.net_oran - a.net_oran)
      break
    case 'net_rate_asc':
      list.sort((a, b) => a.net_oran - b.net_oran)
      break
    case 'gross_rate_desc':
      list.sort((a, b) => b.brut_oran - a.brut_oran)
      break
    case 'net_profit_desc':
      list.sort((a, b) => b.net_kar - a.net_kar)
      break
    case 'total_desc':
      list.sort((a, b) => b.toplam - a.toplam)
      break
    case 'amount_desc':
      list.sort((a, b) => b.yatirilan_tutar - a.yatirilan_tutar)
      break
  }

  return list
})

// DİNAMİK KPI METRİKLERİ (KULLANICININ SEÇTİĞİ FİLTRELERE GÖRE ANINDA YENİDEN HESAPLANIR)
const stats = computed(() => {
  const list = filteredAccounts.value
  if (!list || !list.length) {
    return {
      max_net_rate: 0,
      avg_net_rate: 0,
      max_net_profit: 0,
      max_gross_rate: 0,
      best_bank: '-'
    }
  }

  const validNetRates = list.map(a => a.net_oran).filter(r => r > 0)
  const max_net_rate = validNetRates.length ? Math.max(...validNetRates) : 0
  const avg_net_rate = validNetRates.length ? validNetRates.reduce((a, b) => a + b, 0) / validNetRates.length : 0

  const validGrossRates = list.map(a => a.brut_oran).filter(r => r > 0)
  const max_gross_rate = validGrossRates.length ? Math.max(...validGrossRates) : 0

  const validNetProfits = list.map(a => a.net_kar).filter(p => p > 0)
  const max_net_profit = validNetProfits.length ? Math.max(...validNetProfits) : 0

  const bestAccount = list.find(a => a.net_oran === max_net_rate)
  const best_bank = bestAccount ? (bestAccount.banka_adi || bestAccount.banka_kodu) : '-'

  return {
    max_net_rate,
    avg_net_rate: Number(avg_net_rate.toFixed(2)),
    max_net_profit,
    max_gross_rate,
    best_bank
  }
})

// En Yüksek 3 Metriği Yansıtan Hesapları Vurgulama Fonksiyonları
const isMaxNetRate = (a) => stats.value.max_net_rate > 0 && a.net_oran === stats.value.max_net_rate
const isMaxNetProfit = (a) => stats.value.max_net_profit > 0 && a.net_kar === stats.value.max_net_profit
const isMaxGrossRate = (a) => stats.value.max_gross_rate > 0 && a.brut_oran === stats.value.max_gross_rate
const isHighlighted = (a) => isMaxNetRate(a) || isMaxNetProfit(a) || isMaxGrossRate(a)

const hasActiveFilters = computed(() => {
  return searchQuery.value.trim() !== '' || selectedBanks.value.length > 0 || selectedTiers.value.length > 0 || selectedAmount.value !== null || selectedTerm.value !== null
})

const clearFilters = () => {
  searchQuery.value = ''
  selectedBanks.value = []
  selectedTiers.value = []
  selectedAmount.value = null
  selectedTerm.value = null
  sortBy.value = 'net_rate_desc'
}

// Seçili Hesap Detay & Simülasyon Paneli
const selectedAccount = ref(null)
const simAmount = ref(100000)

const openAccountDetails = (account) => {
  selectedAccount.value = account
  simAmount.value = account.yatirilan_tutar > 0 ? account.yatirilan_tutar : 100000
}

// Simülatör Hesaplama
const simCalculated = computed(() => {
  if (!selectedAccount.value) return { gross: 0, tax: 0, net: 0, total: 0 }
  
  const amt = Number(simAmount.value) || 0
  const bRate = selectedAccount.value.brut_oran || 30.0
  const nRate = selectedAccount.value.net_oran || 25.0
  
  // Vade gününü çıkar (32 gün, 92 gün, 184 gün, 365 gün)
  let days = 32
  const vStr = selectedAccount.value.vade || ''
  if (vStr.includes('92') || vStr.includes('3 Ay')) days = 92
  else if (vStr.includes('184') || vStr.includes('6 Ay')) days = 184
  else if (vStr.includes('365') || vStr.includes('1 Yıl') || vStr.includes('12 Ay')) days = 365
  
  const gross = amt * (bRate / 100.0) * (days / 365.0)
  const net = amt * (nRate / 100.0) * (days / 365.0)
  const tax = Math.max(0, gross - net)
  const total = amt + net

  return {
    gross: Math.round(gross * 100) / 100,
    tax: Math.round(tax * 100) / 100,
    net: Math.round(net * 100) / 100,
    total: Math.round(total * 100) / 100
  }
})

// API'den Veri Çekme
const fetchAccountsData = async () => {
  isLoading.value = true
  try {
    const res = await fetch('http://localhost:8003/katilim-hesap')
    if (res.ok) {
      const data = await res.json()
      allAccounts.value = data.accounts || []
      availableBanks.value = data.filters?.banks || []
      availableAmounts.value = data.filters?.amounts || []
      
      const rawTerms = data.filters?.terms || []
      const parseTermDays = (term) => {
        if (!term) return 0
        const match = term.match(/(\d+)\s*G[üu]n/i)
        if (match) return parseInt(match[1], 10)
        const monthMatch = term.match(/(\d+)\s*Ay/i)
        if (monthMatch) return parseInt(monthMatch[1], 10) * 30
        const yearMatch = term.match(/(\d+)\s*Y[ıi]l/i)
        if (yearMatch) return parseInt(yearMatch[1], 10) * 365
        return 999
      }
      availableTerms.value = [...rawTerms].sort((a, b) => parseTermDays(a) - parseTermDays(b))
    }
  } catch (err) {
    console.error('Katılım hesapları verileri çekilemedi:', err)
  } finally {
    isLoading.value = false
  }
}

// FinAgent AI Analiz Köprüsü
const askAiAboutAccount = async (account) => {
  try {
    const res = await fetch('http://localhost:8003/api/analiz-koprusu', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        kaynak: 'katilim_hesap',
        katilim_hesap: {
          banka: account.banka_id || account.banka_kodu,
          tutar: account.yatirilan_tutar,
          vade: account.vade,
          net_oran: account.net_oran,
          brut_oran: account.brut_oran,
          net_kar: account.net_kar_str
        }
      })
    })

    if (res.ok) {
      const data = await res.json()
      if (data.prompt) {
        sessionStorage.setItem('finagent_direct_prompt', data.prompt)
        sessionStorage.setItem('finagent_auto_send', '1')
        router.push('/chat')
        return
      }
    }
  } catch (err) {
    console.error('Analiz köprüsü çağrısı başarısız:', err)
  }

  // Yedek doğrudan yönlendirme
  const fallbackPrompt = `${account.banka_adi} katılım bankasının ${account.yatirilan_tutar_str} tutarındaki ${account.vade} vadeli katılım hesabı teklifini (${account.net_oran_str} net kâr payı oranı) sektör ortalamasıyla karşılaştırarak analiz et.`
  sessionStorage.setItem('finagent_direct_prompt', fallbackPrompt)
  sessionStorage.setItem('finagent_auto_send', '1')
  router.push('/chat')
}

// Yardımcı Formatlayıcılar
const formatTermLabel = (term) => {
  if (!term) return ''
  if (term.includes('/')) {
    const parts = term.split('/')
    return parts[1]?.trim() || term
  }
  return term.replace(/\s*Vadeli/i, '').trim()
}

const formatCurrency = (val) => {
  if (val === undefined || val === null || isNaN(val) || val <= 0) return '-'
  return new Intl.NumberFormat('tr-TR', { style: 'currency', currency: 'TRY', maximumFractionDigits: 2 }).format(val)
}

const formatCompactNumber = (val) => {
  if (!val) return '0'
  if (val >= 1000000) return (val / 1000000).toFixed(0) + ' Milyon'
  if (val >= 1000) return (val / 1000).toFixed(0) + ' Bin'
  return val.toString()
}

const betigiYukle = (src, globalName) => {
  return new Promise((resolve, reject) => {
    if (typeof window !== 'undefined' && window[globalName]) {
      return resolve(window[globalName])
    }
    const existing = document.querySelector(`script[src="${src}"]`)
    if (existing) {
      if (window[globalName]) return resolve(window[globalName])
      existing.addEventListener('load', () => resolve(window[globalName]))
      existing.addEventListener('error', (err) => reject(err))
      setTimeout(() => {
        if (window[globalName]) resolve(window[globalName])
        else resolve(window[globalName])
      }, 1500)
      return
    }
    const s = document.createElement('script')
    s.src = src
    s.async = true
    s.onload = () => resolve(window[globalName])
    s.onerror = (err) => reject(err)
    document.head.appendChild(s)
  })
}

const escapeHtml = (str) => {
  if (str === null || str === undefined) return ''
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;')
}

// Dışa Aktarma (Excel XLSX, Vektörel PDF, Ultra-HD PNG)
const exportData = async (type) => {
  if (filteredAccounts.value.length === 0) return

  if (type === 'excel') {
    try {
      await betigiYukle('https://cdn.jsdelivr.net/npm/xlsx-js-style@1.2.0/dist/xlsx.bundle.js', 'XLSX')
      const XLSX = window.XLSX
      const wb = XLSX.utils.book_new()

      const today = new Date().toLocaleDateString('tr-TR', { day: '2-digit', month: 'long', year: 'numeric' })
      const activeFilterSummary = []
      if (selectedBanks.value.length > 0) {
        const bNames = selectedBanks.value.map(code => {
          const bObj = availableBanks.value.find(b => b.code === code)
          return bObj ? bObj.name : code
        })
        activeFilterSummary.push(`Banka: ${bNames.join(', ')}`)
      }
      if (selectedTiers.value.length > 0) activeFilterSummary.push(`Tier: ${selectedTiers.value.join(', ')}`)
      if (selectedAmount.value !== null) activeFilterSummary.push(`Tutar: ${formatCurrency(selectedAmount.value)}`)
      if (selectedTerm.value !== null) activeFilterSummary.push(`Vade: ${selectedTerm.value}`)

      const dataRows = []
      
      // 1. Rapor Ana Başlığı
      dataRows.push([
        { v: 'FINAGENT · KATILIM HESABI KÂR PAYI GETİRİLERİ RAPORU', s: { font: { bold: true, sz: 14, color: { rgb: '1E40AF' } }, alignment: { horizontal: 'left' } } }
      ])
      
      // 2. Meta & Filtre Bilgileri
      dataRows.push([
        { v: `Rapor Tarihi: ${today} | Toplam Hesap Seçeneği: ${filteredAccounts.value.length}${activeFilterSummary.length ? ' | Filtreler: ' + activeFilterSummary.join(', ') : ''}`, s: { font: { italic: true, sz: 9, color: { rgb: '6B7280' } } } }
      ])
      dataRows.push([]) // Boş satır

      // 3. Tablo Başlıkları
      const headers = [
        'Banka',
        'Tier',
        'Vade',
        'Yatırılan Tutar (TL)',
        'Brüt Kâr Oranı (%)',
        'Net Kâr Oranı (%)',
        'Brüt Kâr Getirisi (TL)',
        'Stopaj Kesintisi (%7,5) (TL)',
        'Net Kâr Payı Getirisi (TL)',
        'Vade Sonu Toplam Bakiye (TL)'
      ]

      const headerCells = headers.map(h => ({
        v: h,
        s: {
          fill: { fgColor: { rgb: '2563EB' } },
          font: { bold: true, color: { rgb: 'FFFFFF' }, sz: 10 },
          alignment: { horizontal: 'center', vertical: 'center', wrapText: true },
          border: {
            top: { style: 'thin', color: { rgb: '93C5FD' } },
            bottom: { style: 'thin', color: { rgb: '93C5FD' } },
            left: { style: 'thin', color: { rgb: '93C5FD' } },
            right: { style: 'thin', color: { rgb: '93C5FD' } }
          }
        }
      }))
      dataRows.push(headerCells)

      // 4. Veri Satırları
      filteredAccounts.value.forEach((a, idx) => {
        const isEven = idx % 2 === 0
        const rowBg = isEven ? 'FFFFFF' : 'F8FAFC'
        const borderStyle = {
          top: { style: 'thin', color: { rgb: 'E2E8F0' } },
          bottom: { style: 'thin', color: { rgb: 'E2E8F0' } },
          left: { style: 'thin', color: { rgb: 'E2E8F0' } },
          right: { style: 'thin', color: { rgb: 'E2E8F0' } }
        }

        const brutRateVal = a.brut_oran ? a.brut_oran / 100 : (a.brut_oran_str ? parseFloat(a.brut_oran_str.replace('%', '').replace(',', '.')) / 100 : 0)
        const netRateVal = a.net_oran ? a.net_oran / 100 : (a.net_oran_str ? parseFloat(a.net_oran_str.replace('%', '').replace(',', '.')) / 100 : 0)

        const row = [
          { v: a.banka_adi || '', s: { fill: { fgColor: { rgb: rowBg } }, font: { bold: true, color: { rgb: '1E40AF' }, sz: 9 }, border: borderStyle, alignment: { horizontal: 'left' } } },
          { v: a.tier || '-', s: { fill: { fgColor: { rgb: rowBg } }, font: { sz: 9 }, border: borderStyle, alignment: { horizontal: 'center' } } },
          { v: a.vade || '', s: { fill: { fgColor: { rgb: rowBg } }, font: { sz: 9 }, border: borderStyle, alignment: { horizontal: 'center' } } },
          { v: a.yatirilan_tutar || 0, t: 'n', z: '#,##0.00 "₺"', s: { fill: { fgColor: { rgb: rowBg } }, font: { bold: true, sz: 9 }, border: borderStyle, alignment: { horizontal: 'right' } } },
          { v: brutRateVal, t: 'n', z: '0.00%', s: { fill: { fgColor: { rgb: rowBg } }, font: { sz: 9 }, border: borderStyle, alignment: { horizontal: 'center' } } },
          { v: netRateVal, t: 'n', z: '0.00%', s: { fill: { fgColor: { rgb: rowBg } }, font: { bold: true, color: { rgb: '059669' }, sz: 9 }, border: borderStyle, alignment: { horizontal: 'center' } } },
          { v: a.brut_kar || (a.brut_kar_str ? parseFloat(a.brut_kar_str.replace(/[^\d.,]/g, '').replace('.', '').replace(',', '.')) : 0), t: 'n', z: '#,##0.00 "₺"', s: { fill: { fgColor: { rgb: rowBg } }, font: { sz: 9 }, border: borderStyle, alignment: { horizontal: 'right' } } },
          { v: a.stopaj_kesintisi || (a.stopaj_kesintisi_str ? parseFloat(a.stopaj_kesintisi_str.replace(/[^\d.,]/g, '').replace('.', '').replace(',', '.')) : 0), t: 'n', z: '#,##0.00 "₺"', s: { fill: { fgColor: { rgb: rowBg } }, font: { sz: 9, color: { rgb: 'DC2626' } }, border: borderStyle, alignment: { horizontal: 'right' } } },
          { v: a.net_kar || (a.net_kar_str ? parseFloat(a.net_kar_str.replace(/[^\d.,]/g, '').replace('.', '').replace(',', '.')) : 0), t: 'n', z: '#,##0.00 "₺"', s: { fill: { fgColor: { rgb: rowBg } }, font: { bold: true, color: { rgb: '059669' }, sz: 9 }, border: borderStyle, alignment: { horizontal: 'right' } } },
          { v: a.toplam || (a.toplam_str ? parseFloat(a.toplam_str.replace(/[^\d.,]/g, '').replace('.', '').replace(',', '.')) : 0), t: 'n', z: '#,##0.00 "₺"', s: { fill: { fgColor: { rgb: rowBg } }, font: { bold: true, color: { rgb: '4338CA' }, sz: 9 }, border: borderStyle, alignment: { horizontal: 'right' } } }
        ]
        dataRows.push(row)
      })

      const ws = XLSX.utils.aoa_to_sheet(dataRows)
      ws['!cols'] = [
        { wch: 22 }, // Banka
        { wch: 10 }, // Tier
        { wch: 14 }, // Vade
        { wch: 22 }, // Yatırılan Tutar
        { wch: 18 }, // Brüt Oran
        { wch: 18 }, // Net Oran
        { wch: 20 }, // Brüt Kâr
        { wch: 22 }, // Stopaj Kesintisi
        { wch: 22 }, // Net Kâr
        { wch: 24 }  // Vade Sonu Toplam
      ]

      XLSX.utils.book_append_sheet(wb, ws, 'Katılım Hesapları')
      XLSX.writeFile(wb, `FinAgent_Katilim_Hesaplari_${new Date().toISOString().slice(0, 10)}.xlsx`)
    } catch (e) {
      console.error('Excel export hatası:', e)
    }
  } else if (type === 'pdf') {
    try {
      await betigiYukle('https://cdnjs.cloudflare.com/ajax/libs/html2pdf.js/0.10.1/html2pdf.bundle.min.js', 'html2pdf')

      const today = new Date().toLocaleDateString('tr-TR', { day: '2-digit', month: 'long', year: 'numeric', hour: '2-digit', minute: '2-digit' })
      const activeFilterSummary = []
      if (selectedBanks.value.length > 0) {
        const bNames = selectedBanks.value.map(code => {
          const bObj = availableBanks.value.find(b => b.code === code)
          return bObj ? bObj.name : code
        })
        activeFilterSummary.push(`Banka: ${bNames.join(', ')}`)
      }
      if (selectedTiers.value.length > 0) activeFilterSummary.push(`Tier: ${selectedTiers.value.join(', ')}`)
      if (selectedAmount.value !== null) activeFilterSummary.push(`Tutar: ${formatCurrency(selectedAmount.value)}`)
      if (selectedTerm.value !== null) activeFilterSummary.push(`Vade: ${selectedTerm.value}`)

      // Sayfalara bölme
      const PAGE1_CHUNK_SIZE = 40
      const NEXT_PAGES_CHUNK_SIZE = 52

      const pages = []
      const remaining = [...filteredAccounts.value]

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
                            FinAgent · Katılım Hesabı Kâr Payı Oranları Raporu
                        </h1>
                        <p style="color: #6b7280; font-size: 10px; margin: 2px 0 0 0;">
                            Rapor Tarihi: ${escapeHtml(today)} ${activeFilterSummary.length ? `| Filtreler: ${escapeHtml(activeFilterSummary.join(', '))}` : ''}
                        </p>
                    </div>
                    <div style="text-align: right;">
                        <span style="font-size: 10.5px; font-weight: 700; color: #1e40af; background: #eff6ff; border: 1px solid #bfdbfe; padding: 2px 7px; border-radius: 5px;">
                            ${filteredAccounts.value.length} Hesap Seçeneği
                        </span>
                    </div>
                </div>

                <!-- ÖZET İSTATİSTİK KUTULARI (KPIs) -->
                <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 6px; margin-bottom: 10px;">
                    <div style="background-color: #eff6ff; border: 1px solid #bfdbfe; border-radius: 6px; padding: 6px 4px; text-align: center;">
                        <div style="font-size: 8.5px; font-weight: 700; color: #1e40af; text-transform: uppercase;">En Yüksek Net Oran</div>
                        <div style="font-size: 14px; font-weight: 900; color: #2563eb; margin-top: 1px;">${stats.value.max_net_rate > 0 ? '%' + stats.value.max_net_rate.toFixed(2).replace('.', ',') : '-'}</div>
                        <div style="font-size: 7.5px; color: #1d4ed8; font-weight: 600;">${escapeHtml(stats.value.best_bank || '-')}</div>
                    </div>
                    <div style="background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px; padding: 6px 4px; text-align: center;">
                        <div style="font-size: 8.5px; font-weight: 700; color: #475569; text-transform: uppercase;">En Yüksek Net Getiri</div>
                        <div style="font-size: 13.5px; font-weight: 900; color: #0f172a; margin-top: 1px;">${formatCurrency(stats.value.max_net_profit)}</div>
                        <div style="font-size: 7.5px; color: #64748b;">Seçili tutar/vadede</div>
                    </div>
                    <div style="background-color: #eef2ff; border: 1px solid #c7d2fe; border-radius: 6px; padding: 6px 4px; text-align: center;">
                        <div style="font-size: 8.5px; font-weight: 700; color: #3730a3; text-transform: uppercase;">En Yüksek Brüt Oran</div>
                        <div style="font-size: 13.5px; font-weight: 900; color: #4f46e5; margin-top: 1px;">${stats.value.max_gross_rate > 0 ? '%' + stats.value.max_gross_rate.toFixed(2).replace('.', ',') : '-'}</div>
                        <div style="font-size: 7.5px; color: #4338ca;">Brüt kâr oranı</div>
                    </div>
                    <div style="background-color: #fffbeb; border: 1px solid #fde68a; border-radius: 6px; padding: 6px 4px; text-align: center;">
                        <div style="font-size: 8.5px; font-weight: 700; color: #92400e; text-transform: uppercase;">Sektör Ortalaması</div>
                        <div style="font-size: 14px; font-weight: 900; color: #d97706; margin-top: 1px;">${stats.value.avg_net_rate > 0 ? '%' + stats.value.avg_net_rate.toFixed(2).replace('.', ',') : '-'}</div>
                        <div style="font-size: 7.5px; color: #b45309;">${filteredAccounts.value.length} hesap ortalaması</div>
                    </div>
                </div>
              ` : `
                <!-- DEVAM SAYFALARI ÜST BAŞLIĞI -->
                <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1.5px solid #e2e8f0; padding-bottom: 5px; margin-bottom: 8px;">
                    <div style="font-size: 11.5px; font-weight: 800; color: #2563eb;">
                        FinAgent · Katılım Hesabı Kâr Payı Oranları Raporu
                    </div>
                    <div style="font-size: 9px; color: #64748b;">
                        Rapor Tarihi: ${escapeHtml(today)}
                    </div>
                </div>
              `}

              <!-- KATILIM HESAPLARI TABLOSU -->
              <table style="width: 100%; border-collapse: collapse; font-size: 7.8px; table-layout: fixed; line-height: 1.15;">
                  <thead>
                      <tr style="background-color: #f1f5f9;">
                          <th style="width: 18%; padding: 4px 4px; border: 1px solid #cbd5e1; text-align: left; color: #1e293b; font-weight: 700;">Banka</th>
                          <th style="width: 8%; padding: 4px 3px; border: 1px solid #cbd5e1; text-align: center; color: #1e293b; font-weight: 700;">Tier</th>
                          <th style="width: 10%; padding: 4px 3px; border: 1px solid #cbd5e1; text-align: center; color: #1e293b; font-weight: 700;">Vade</th>
                          <th style="width: 14%; padding: 4px 4px; border: 1px solid #cbd5e1; text-align: right; color: #1e293b; font-weight: 700;">Tutar</th>
                          <th style="width: 10%; padding: 4px 3px; border: 1px solid #cbd5e1; text-align: center; color: #1e293b; font-weight: 700;">Brüt Oran</th>
                          <th style="width: 10%; padding: 4px 3px; border: 1px solid #cbd5e1; text-align: center; color: #059669; font-weight: 800;">Net Oran</th>
                          <th style="width: 13%; padding: 4px 4px; border: 1px solid #cbd5e1; text-align: right; color: #1e293b; font-weight: 700;">Brüt Kâr</th>
                          <th style="width: 13%; padding: 4px 4px; border: 1px solid #cbd5e1; text-align: right; color: #059669; font-weight: 800;">Net Kâr</th>
                          <th style="width: 14%; padding: 4px 4px; border: 1px solid #cbd5e1; text-align: right; color: #4338ca; font-weight: 800;">Toplam Bakiye</th>
                      </tr>
                  </thead>
                  <tbody>
                    ${page.items.map((a, idx) => `
                      <tr style="${idx % 2 === 1 ? 'background-color: #f8fafc;' : ''}">
                        <td style="padding: 2.8px 4px; border: 1px solid #e2e8f0; font-weight: 700; color: #1e40af; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${escapeHtml(a.banka_adi)}</td>
                        <td style="padding: 2.8px 3px; border: 1px solid #e2e8f0; text-align: center; color: #64748b; white-space: nowrap;">${escapeHtml(a.tier || '-')}</td>
                        <td style="padding: 2.8px 3px; border: 1px solid #e2e8f0; text-align: center; white-space: nowrap;">${escapeHtml(a.vade)}</td>
                        <td style="padding: 2.8px 4px; border: 1px solid #e2e8f0; text-align: right; font-weight: 600; white-space: nowrap;">${a.yatirilan_tutar_str || formatCurrency(a.yatirilan_tutar)}</td>
                        <td style="padding: 2.8px 3px; border: 1px solid #e2e8f0; text-align: center; white-space: nowrap;">${a.brut_oran_str}</td>
                        <td style="padding: 2.8px 3px; border: 1px solid #e2e8f0; text-align: center; font-weight: 800; color: #059669; white-space: nowrap;">${a.net_oran_str}</td>
                        <td style="padding: 2.8px 4px; border: 1px solid #e2e8f0; text-align: right; color: #475569; white-space: nowrap;">${a.brut_kar_str}</td>
                        <td style="padding: 2.8px 4px; border: 1px solid #e2e8f0; text-align: right; font-weight: 800; color: #059669; white-space: nowrap;">${a.net_kar_str}</td>
                        <td style="padding: 2.8px 4px; border: 1px solid #e2e8f0; text-align: right; font-weight: 800; color: #4338ca; white-space: nowrap;">${a.toplam_str}</td>
                      </tr>
                    `).join('')}
                  </tbody>
              </table>
            </div>

            <!-- HER SAYFANIN ALTINDAKİ YASAL UYARI & ALTBİLGİ ALANI -->
            <div style="width: 100%; margin-top: auto; padding-top: 10px;">
              <div style="padding: 6px 10px; background-color: #f8fafc; border-left: 3px solid #2563eb; border-radius: 4px; font-size: 8px; color: #475569; font-style: italic; line-height: 1.35;">
                  Bu raporda yer alan veriler katılım bankalarının kamuya açık katılım fonu kâr payı dağıtım tablolarından derlenmiştir. Gerçek kişilere ait katılım fonları TMSF güvencesi altındadır. Kâr payı oranları geçmiş dönem getirilerini yansıtır.
              </div>

              <div style="margin-top: 8px; padding-top: 6px; border-top: 1px solid #e5e7eb; display: flex; justify-content: space-between; align-items: center; font-size: 8.5px; color: #9ca3af;">
                  <span>Katılım Hesapları Kâr Payı Oranları · Bu rapor, FinAgent Yapay Zekâ platformu tarafından otomatik olarak oluşturulmuştur.</span>
                  <span style="font-weight: 700; color: #2563eb;">Sayfa ${pageNumber} / ${totalPages}</span>
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
        filename:     `FinAgent_Katilim_Hesaplari_Raporu_${Date.now()}.pdf`,
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

      const today = new Date().toLocaleDateString('tr-TR', { day: '2-digit', month: 'long', year: 'numeric', hour: '2-digit', minute: '2-digit' })
      const activeFilterSummary = []
      if (selectedBanks.value.length > 0) {
        const bNames = selectedBanks.value.map(code => {
          const bObj = availableBanks.value.find(b => b.code === code)
          return bObj ? bObj.name : code
        })
        activeFilterSummary.push(`Banka: ${bNames.join(', ')}`)
      }
      if (selectedTiers.value.length > 0) activeFilterSummary.push(`Tier: ${selectedTiers.value.join(', ')}`)
      if (selectedAmount.value !== null) activeFilterSummary.push(`Tutar: ${formatCurrency(selectedAmount.value)}`)
      if (selectedTerm.value !== null) activeFilterSummary.push(`Vade: ${selectedTerm.value}`)

      let html = `
        <div style="font-family: 'Segoe UI', Arial, sans-serif; color: #171717; background-color: #ffffff; width: 1000px; padding: 24px; box-sizing: border-box;">
          
          <!-- ÜST BAŞLIK -->
          <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #2563eb; padding-bottom: 12px; margin-bottom: 16px;">
              <div>
                  <h1 style="color: #2563eb; margin: 0; font-size: 22px; font-weight: 800; letter-spacing: -0.5px;">
                      FinAgent · Katılım Hesabı Kâr Payı Oranları Raporu
                  </h1>
                  <p style="color: #6b7280; font-size: 11px; margin: 4px 0 0 0;">
                      Rapor Tarihi: ${escapeHtml(today)} ${activeFilterSummary.length ? `| Filtreler: ${escapeHtml(activeFilterSummary.join(', '))}` : ''}
                  </p>
              </div>
              <div style="text-align: right;">
                  <span style="font-size: 12px; font-weight: 700; color: #1e40af; background: #eff6ff; border: 1px solid #bfdbfe; padding: 4px 10px; border-radius: 8px;">
                      ${filteredAccounts.value.length} Hesap Seçeneği
                  </span>
              </div>
          </div>

          <!-- ÖZET İSTATİSTİK KUTULARI (KPIs) -->
          <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin-bottom: 18px;">
              <div style="background-color: #eff6ff; border: 1px solid #bfdbfe; border-radius: 8px; padding: 10px 8px; text-align: center;">
                  <div style="font-size: 10px; font-weight: 700; color: #1e40af; text-transform: uppercase;">En Yüksek Net Oran</div>
                  <div style="font-size: 18px; font-weight: 900; color: #2563eb; margin-top: 2px;">${stats.value.max_net_rate > 0 ? '%' + stats.value.max_net_rate.toFixed(2).replace('.', ',') : '-'}</div>
                  <div style="font-size: 9px; color: #1d4ed8; font-weight: 600;">${escapeHtml(stats.value.best_bank || '-')}</div>
              </div>
              <div style="background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 10px 8px; text-align: center;">
                  <div style="font-size: 10px; font-weight: 700; color: #475569; text-transform: uppercase;">En Yüksek Net Getiri</div>
                  <div style="font-size: 17px; font-weight: 900; color: #0f172a; margin-top: 2px;">${formatCurrency(stats.value.max_net_profit)}</div>
                  <div style="font-size: 9px; color: #64748b;">Seçili tutar/vadede</div>
              </div>
              <div style="background-color: #eef2ff; border: 1px solid #c7d2fe; border-radius: 8px; padding: 10px 8px; text-align: center;">
                  <div style="font-size: 10px; font-weight: 700; color: #3730a3; text-transform: uppercase;">En Yüksek Brüt Oran</div>
                  <div style="font-size: 17px; font-weight: 900; color: #4f46e5; margin-top: 2px;">${stats.value.max_gross_rate > 0 ? '%' + stats.value.max_gross_rate.toFixed(2).replace('.', ',') : '-'}</div>
                  <div style="font-size: 9px; color: #4338ca;">Brüt kâr oranı</div>
              </div>
              <div style="background-color: #fffbeb; border: 1px solid #fde68a; border-radius: 8px; padding: 10px 8px; text-align: center;">
                  <div style="font-size: 10px; font-weight: 700; color: #92400e; text-transform: uppercase;">Sektör Ortalaması</div>
                  <div style="font-size: 18px; font-weight: 900; color: #d97706; margin-top: 2px;">${stats.value.avg_net_rate > 0 ? '%' + stats.value.avg_net_rate.toFixed(2).replace('.', ',') : '-'}</div>
                  <div style="font-size: 9px; color: #b45309;">${filteredAccounts.value.length} hesap ortalaması</div>
              </div>
          </div>

          <!-- TABLO -->
          <table style="width: 100%; border-collapse: collapse; font-size: 10px; table-layout: fixed; line-height: 1.3;">
              <thead>
                  <tr style="background-color: #2563eb; color: #ffffff;">
                      <th style="width: 18%; padding: 7px 6px; border: 1px solid #93c5fd; text-align: left; font-weight: 700;">Banka</th>
                      <th style="width: 8%; padding: 7px 4px; border: 1px solid #93c5fd; text-align: center; font-weight: 700;">Tier</th>
                      <th style="width: 10%; padding: 7px 4px; border: 1px solid #93c5fd; text-align: center; font-weight: 700;">Vade</th>
                      <th style="width: 14%; padding: 7px 6px; border: 1px solid #93c5fd; text-align: right; font-weight: 700;">Yatırılan Tutar</th>
                      <th style="width: 10%; padding: 7px 4px; border: 1px solid #93c5fd; text-align: center; font-weight: 700;">Brüt Oran</th>
                      <th style="width: 10%; padding: 7px 4px; border: 1px solid #93c5fd; text-align: center; font-weight: 800;">Net Oran</th>
                      <th style="width: 13%; padding: 7px 6px; border: 1px solid #93c5fd; text-align: right; font-weight: 700;">Brüt Kâr</th>
                      <th style="width: 13%; padding: 7px 6px; border: 1px solid #93c5fd; text-align: right; font-weight: 800;">Net Kâr</th>
                      <th style="width: 14%; padding: 7px 6px; border: 1px solid #93c5fd; text-align: right; font-weight: 800;">Toplam Bakiye</th>
                  </tr>
              </thead>
              <tbody>
                ${filteredAccounts.value.map((a, idx) => `
                  <tr style="${idx % 2 === 1 ? 'background-color: #f8fafc;' : 'background-color: #ffffff;'}">
                    <td style="padding: 5px 6px; border: 1px solid #e2e8f0; font-weight: 700; color: #1e40af; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${escapeHtml(a.banka_adi)}</td>
                    <td style="padding: 5px 4px; border: 1px solid #e2e8f0; text-align: center; color: #64748b; white-space: nowrap;">${escapeHtml(a.tier || '-')}</td>
                    <td style="padding: 5px 4px; border: 1px solid #e2e8f0; text-align: center; white-space: nowrap;">${escapeHtml(a.vade)}</td>
                    <td style="padding: 5px 6px; border: 1px solid #e2e8f0; text-align: right; font-weight: 600; white-space: nowrap;">${a.yatirilan_tutar_str || formatCurrency(a.yatirilan_tutar)}</td>
                    <td style="padding: 5px 4px; border: 1px solid #e2e8f0; text-align: center; white-space: nowrap;">${a.brut_oran_str}</td>
                    <td style="padding: 5px 4px; border: 1px solid #e2e8f0; text-align: center; font-weight: 800; color: #059669; white-space: nowrap;">${a.net_oran_str}</td>
                    <td style="padding: 5px 6px; border: 1px solid #e2e8f0; text-align: right; color: #475569; white-space: nowrap;">${a.brut_kar_str}</td>
                    <td style="padding: 5px 6px; border: 1px solid #e2e8f0; text-align: right; font-weight: 800; color: #059669; white-space: nowrap;">${a.net_kar_str}</td>
                    <td style="padding: 5px 6px; border: 1px solid #e2e8f0; text-align: right; font-weight: 800; color: #4338ca; white-space: nowrap;">${a.toplam_str}</td>
                  </tr>
                `).join('')}
              </tbody>
          </table>

          <!-- ALTBİLGİ -->
          <div style="margin-top: 16px; padding: 8px 12px; background-color: #f8fafc; border-left: 3px solid #2563eb; border-radius: 4px; font-size: 9px; color: #64748b; font-style: italic; display: flex; justify-content: space-between; align-items: center;">
              <span>Bu raporda yer alan veriler katılım bankalarının kamuya açık katılım fonu kâr payı dağıtım tablolarından derlenmiştir. Gerçek kişilere ait katılım fonları TMSF güvencesi altındadır.</span>
              <span style="font-weight: 700; color: #2563eb; margin-left: 12px; white-space: nowrap;">FinAgent AI</span>
          </div>

        </div>
      `

      const tempDiv = document.createElement('div')
      tempDiv.style.position = 'fixed'
      tempDiv.style.left = '0px'
      tempDiv.style.top = '0px'
      tempDiv.style.zIndex = '-99999'
      tempDiv.style.width = '1000px'
      tempDiv.style.background = '#ffffff'
      tempDiv.style.pointerEvents = 'none'
      tempDiv.innerHTML = html
      document.body.appendChild(tempDiv)

      const targetEl = tempDiv.firstElementChild || tempDiv

      const canvas = await window.html2canvas(targetEl, {
        scale: 2,
        backgroundColor: '#ffffff',
        useCORS: true,
        logging: false,
        windowWidth: 1050,
        scrollX: 0,
        scrollY: 0,
        x: 0,
        y: 0
      })

      document.body.removeChild(tempDiv)

      const link = document.createElement('a')
      link.download = `FinAgent_Katilim_Hesaplari_${new Date().toISOString().slice(0, 10)}.png`
      link.href = canvas.toDataURL('image/png')
      link.click()
    } catch (e) {
      console.error('PNG kaydetme hatası:', e)
    }
  }
}

const handleKeyDown = (e) => {
  if (e.key === 'Escape' && selectedAccount.value) {
    selectedAccount.value = null
  }
}

onMounted(() => {
  fetchAccountsData()
  if (process.client) {
    window.addEventListener('keydown', handleKeyDown)
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
  if (process.client) {
    window.removeEventListener('keydown', handleKeyDown)
  }
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
</script>

<style scoped>
.gradient-text {
  background-image: linear-gradient(135deg, #10b981 0%, #06b6d4 100%);
}

.finagent-glow-btn {
  background: linear-gradient(135deg, rgba(16, 185, 129, 0.08), rgba(6, 182, 212, 0.08), rgba(20, 184, 166, 0.08));
  border: 1.5px solid rgba(16, 185, 129, 0.25);
  box-shadow: 0 0 15px -3px rgba(16, 185, 129, 0.15), 0 0 6px -2px rgba(6, 182, 212, 0.2);
}

:global(.dark) .finagent-glow-btn {
  background: linear-gradient(135deg, rgba(16, 185, 129, 0.15), rgba(6, 182, 212, 0.15), rgba(20, 184, 166, 0.15));
  border: 1.5px solid rgba(6, 182, 212, 0.35);
  box-shadow: 0 0 15px -3px rgba(16, 185, 129, 0.25), 0 0 6px -2px rgba(6, 182, 212, 0.3);
}

.finagent-glow-btn:hover {
  border-color: rgba(16, 185, 129, 0.6);
  box-shadow: 0 0 20px 2px rgba(16, 185, 129, 0.35), 0 0 10px 0px rgba(6, 182, 212, 0.4);
}

.logo-glow {
  filter: drop-shadow(0 0 5px rgba(16, 185, 129, 0.55)) drop-shadow(0 0 10px rgba(6, 182, 212, 0.35));
  animation: logoGlowShift 4s ease-in-out infinite alternate;
}

@keyframes logoGlowShift {
  0% {
    filter: drop-shadow(0 0 4px rgba(16, 185, 129, 0.5)) drop-shadow(0 0 8px rgba(6, 182, 212, 0.35));
  }
  50% {
    filter: drop-shadow(0 0 7px rgba(6, 182, 212, 0.75)) drop-shadow(0 0 14px rgba(20, 184, 166, 0.55));
  }
  100% {
    filter: drop-shadow(0 0 4px rgba(16, 185, 129, 0.5)) drop-shadow(0 0 8px rgba(6, 182, 212, 0.35));
  }
}

.no-scrollbar::-webkit-scrollbar {
  display: none;
}
.no-scrollbar {
  -ms-overflow-style: none;
  scrollbar-width: none;
}

.custom-scrollbar::-webkit-scrollbar {
  width: 6px;
}
.custom-scrollbar::-webkit-scrollbar-track {
  background: transparent;
}
.custom-scrollbar::-webkit-scrollbar-thumb {
  background-color: #cbd5e1;
  border-radius: 9999px;
}
:global(.dark) .custom-scrollbar::-webkit-scrollbar-thumb {
  background-color: #334155;
}
</style>
