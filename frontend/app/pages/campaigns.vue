<template>
  <div class="p-4 sm:p-6 lg:p-8 space-y-6 lg:space-y-8 w-full max-w-[1600px] mx-auto min-h-full">

    <!-- ================= ORTALANMIŞ BAŞLIK ================= -->
    <div class="flex flex-col items-center text-center gap-3">
      <h1 class="reveal-title text-4xl md:text-5xl font-bold bg-clip-text text-transparent gradient-text pb-1">
        {{ $t('campaigns.title', 'Tüm Kampanyalar') }}
      </h1>
      <p class="text-sm md:text-base text-neutral-500 dark:text-neutral-400 max-w-2xl">
        {{ $t('campaigns.subtitle', 'Toplanan tüm kampanyalar, gelişmiş filtreler ve yapay zeka çıkarım kanıtları.') }}
      </p>
      <div class="h-1 w-24 rounded-full bg-gradient-to-r from-blue-500 to-cyan-400 mt-1 title-underline"></div>
    </div>

    <!-- ================= GELİŞMİŞ FİLTRELER ================= -->
    <div class="relative z-30 p-5 bg-white/80 dark:bg-neutral-800/60 backdrop-blur-md border border-neutral-200/50 dark:border-neutral-700/50 rounded-2xl shadow-sm">

      <div v-if="openDropdown" @click="openDropdown = null" class="fixed inset-0 z-20"></div>

      <template v-if="pending">
        <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div v-for="i in 3" :key="`skel-filter-${i}`" class="h-16 bg-neutral-200 dark:bg-neutral-700 rounded-lg shimmer"></div>
        </div>
      </template>

      <template v-else>
        <div class="grid grid-cols-1 lg:grid-cols-4 gap-4 relative z-30">

          <div class="flex flex-col gap-1.5">
            <label class="text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wide">{{ $t('campaigns.search_label', 'Ara') }}</label>
            <div class="relative">
              <svg class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/></svg>
              <input
                v-model="search"
                type="text"
                :placeholder="$t('campaigns.search_placeholder', 'Kampanya veya banka ara...')"
                class="w-full bg-white dark:bg-neutral-900 border border-neutral-200 dark:border-neutral-700 rounded-lg pl-9 pr-3 py-2.5 text-sm text-neutral-700 dark:text-neutral-200 focus:ring-2 focus:ring-cyan-500 outline-none transition-all"
              >
            </div>
          </div>

          <div v-for="def in filterDefs" :key="def.key" class="flex flex-col gap-1.5 relative">
            <label class="text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wide">{{ def.label }}</label>
            <div
              @click="focusFilter(def.key)"
              class="min-h-[42px] w-full bg-white dark:bg-neutral-900 border rounded-lg px-2 py-1.5 text-sm flex items-center gap-1.5 flex-wrap cursor-text transition-all"
              :class="openDropdown === def.key ? 'border-cyan-500 ring-2 ring-cyan-500/30' : 'border-neutral-200 dark:border-neutral-700 hover:border-neutral-300 dark:hover:border-neutral-600'"
            >
              <span
                v-for="val in filters[def.key]"
                :key="val"
                class="chip inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-xs font-medium bg-cyan-500 text-white shadow-sm"
              >
                {{ getFilterOptionLabel(def.key, val) }}
                <span @click.stop="toggleValue(def.key, val)" class="hover:text-cyan-100 cursor-pointer leading-none">✕</span>
              </span>
              <input
                :ref="(el) => setFilterInputRef(def.key, el)"
                v-model="filterQuery[def.key]"
                @focus="openDropdown = def.key"
                @keydown.backspace="onFilterBackspace(def.key)"
                :placeholder="filters[def.key].length ? $t('campaigns.add_placeholder', 'Ekle...') : $t('campaigns.all_placeholder', 'Tümü')"
                class="flex-1 min-w-[70px] bg-transparent outline-none text-sm text-neutral-700 dark:text-neutral-200 placeholder-neutral-400 py-0.5"
              >
              <svg class="w-4 h-4 text-neutral-400 flex-shrink-0 transition-transform pointer-events-none" :class="openDropdown === def.key ? 'rotate-180' : ''" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M19 9l-7 7-7-7"/></svg>
            </div>

            <Transition name="dropdown">
              <div v-if="openDropdown === def.key" class="absolute top-full left-0 right-0 mt-1 z-40 bg-white dark:bg-neutral-900 border border-neutral-200 dark:border-neutral-700 rounded-lg shadow-xl max-h-72 overflow-y-auto py-1 custom-scrollbar" data-lenis-prevent="true">
                <label
                  v-for="opt in filteredOptions(def)"
                  :key="opt"
                  class="flex items-center gap-2.5 px-3 py-2 text-sm cursor-pointer hover:bg-cyan-50 dark:hover:bg-cyan-900/20 transition-colors"
                >
                  <input
                    type="checkbox"
                    :checked="filters[def.key].includes(opt)"
                    @change="toggleValue(def.key, opt)"
                    class="w-4 h-4 rounded border-neutral-300 text-cyan-600 focus:ring-cyan-500 dark:border-neutral-600 dark:bg-neutral-800"
                  >
                  <div v-if="def.key === 'banka'" class="w-5 h-5 rounded-md bg-white p-0.5 flex items-center justify-center shrink-0 border border-neutral-200/60 dark:border-white/20 shadow-2xs">
                    <img :src="getBankaLogo(opt)" class="w-full h-full object-contain" @error="(e) => e.target.style.display = 'none'" />
                  </div>
                  <span class="text-neutral-700 dark:text-neutral-200">{{ getFilterOptionLabel(def.key, opt) }}</span>
                </label>
                <div v-if="filteredOptions(def).length === 0" class="px-3 py-2 text-xs text-neutral-400 italic">{{ $t('campaigns.no_search_results', 'Sonuç bulunamadı') }}</div>
              </div>
            </Transition>
          </div>
        </div>

        <div class="flex flex-wrap items-center justify-between gap-4 mt-4 pt-4 border-t border-neutral-200/60 dark:border-neutral-700/60 relative z-10">
          <label class="flex items-center gap-2 cursor-pointer group">
            <input type="checkbox" v-model="filters.sadeceOranli" class="w-4 h-4 rounded border-neutral-300 text-cyan-600 focus:ring-cyan-500 dark:border-neutral-600 dark:bg-neutral-900 dark:checked:bg-cyan-500 transition-all cursor-pointer">
            <span class="text-sm font-medium text-neutral-600 dark:text-neutral-300 group-hover:text-neutral-900 dark:group-hover:text-white transition-colors">
              {{ $t('campaigns.only_with_rates', 'Yalnızca kâr payı oranı olanlar') }}
            </span>
          </label>

          <div class="flex items-center gap-3">
            <span v-if="activeFilterCount" class="text-xs font-medium text-cyan-600 dark:text-cyan-400">{{ activeFilterCount }} {{ $t('campaigns.active_filters', 'aktif filtre') }}</span>
            <button
              v-if="activeFilterCount"
              @click="clearFilters"
              class="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg border border-neutral-200 dark:border-neutral-700 text-neutral-600 dark:text-neutral-300 hover:bg-rose-50 dark:hover:bg-rose-900/20 hover:text-rose-600 hover:border-rose-300 transition-all"
            >
              <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"/></svg>
              {{ $t('campaigns.clear_filters', 'Filtreleri temizle') }}
            </button>
          </div>
        </div>
      </template>
    </div>

    <!-- ================= KAMPANYALAR TABLOSU (KAYDIRILABİLİR YAPI) ================= -->
    <div class="relative z-0 bg-white/80 dark:bg-neutral-800/60 backdrop-blur-md border border-neutral-200/50 dark:border-neutral-700/50 rounded-2xl shadow-sm flex flex-col">
      
      <div class="p-4 border-b border-neutral-200/50 dark:border-neutral-700/50 flex justify-between items-center bg-neutral-50/50 dark:bg-neutral-800/50 rounded-t-2xl z-20">
        <span class="text-xs font-semibold text-neutral-500 dark:text-neutral-400">
          <span v-if="!pending">
            <span class="text-cyan-600 dark:text-cyan-400 font-bold">{{ displayedCampaigns.length }}</span>
            {{ $t('campaigns.showing_campaigns', { count: displayedCampaigns.length, total: totalCount }) }}
          </span>
          <span v-else>{{ $t('campaigns.loading_data', 'Veriler yükleniyor...') }}</span>
        </span>
      </div>

      <div class="overflow-y-auto max-h-[580px] custom-scrollbar rounded-b-2xl relative" data-lenis-prevent="true">
        <table class="w-full text-left border-collapse table-fixed">
          
          <thead class="sticky top-0 z-10 bg-neutral-100/95 dark:bg-neutral-900/95 backdrop-blur-md shadow-sm">
            <tr class="text-xs uppercase text-neutral-500 dark:text-neutral-400">
              <th v-for="col in columns" :key="col.key"
                  @click="col.sortable && setSort(col.key)"
                  class="px-2.5 py-3 font-semibold border-b border-neutral-200/50 dark:border-neutral-700/50 select-none"
                  :class="[
                    col.width || '',
                    col.sortable ? 'cursor-pointer hover:text-cyan-600 dark:hover:text-cyan-400 transition-colors' : '',
                    col.align === 'center' ? 'text-center' : 'text-left'
                  ]">
                <span class="inline-flex items-center gap-1" :class="col.align === 'center' ? 'justify-center' : ''">
                  <span class="truncate">{{ col.label }}</span>
                  <span v-if="col.sortable" class="text-[10px] shrink-0" :class="sortKey === col.key ? 'text-cyan-500' : 'text-neutral-300 dark:text-neutral-600'">
                    {{ sortKey === col.key ? (sortDir === 'asc' ? '▲' : '▼') : '↕' }}
                  </span>
                </span>
              </th>
            </tr>
          </thead>

          <tbody class="divide-y divide-neutral-200/50 dark:divide-neutral-700/50 text-sm">

            <template v-if="pending">
              <tr v-for="i in 10" :key="`skel-row-${i}`">
                <td v-for="col in columns" :key="`skel-col-${col.key}`" class="px-2.5 py-3">
                  <div class="h-4 bg-neutral-200 dark:bg-neutral-700 rounded shimmer" :class="col.key === 'baslik' ? 'w-48' : 'w-16'"></div>
                </td>
              </tr>
            </template>

            <template v-else>
              <tr v-if="displayedCampaigns.length === 0">
                <td :colspan="columns.length" class="p-10 text-center text-neutral-500">
                  <div class="flex flex-col items-center gap-2">
                    <svg class="w-10 h-10 text-neutral-300 dark:text-neutral-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
                    {{ $t('campaigns.no_campaigns_found', 'Kriterlere uygun kampanya bulunamadı.') }}
                  </div>
                </td>
              </tr>
              <tr v-for="(camp, i) in displayedCampaigns" :key="camp.id"
                  @click="selectCampaign(camp.id)"
                  :style="{ transitionDelay: `${Math.min(i, 15) * 30}ms` }"
                  :class="[
                    revealed ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-2',
                    selectedCampaignId === camp.id ? 'bg-cyan-50/80 dark:bg-cyan-900/30' : ''
                  ]"
                  class="row-anim hover:bg-cyan-50/50 dark:hover:bg-cyan-900/20 transition-all duration-300 cursor-pointer">
                
                <td v-if="isColumnVisible('banka')" class="px-2.5 py-2.5 font-medium text-neutral-800 dark:text-neutral-200">
                  <div class="flex items-center gap-1.5 min-w-0">
                    <div class="w-5 h-5 rounded-md bg-white p-0.5 flex items-center justify-center shrink-0 border border-neutral-200/60 dark:border-white/20 shadow-2xs">
                      <img :src="getBankaLogo(camp.banka)" :alt="getBankaAd(camp.banka)" class="w-full h-full object-contain" @error="(e) => e.target.style.display = 'none'" />
                    </div>
                    <span class="font-semibold text-xs truncate" :title="getBankaAd(camp.banka)">{{ getBankaAd(camp.banka) }}</span>
                  </div>
                </td>
                <td v-if="isColumnVisible('baslik')" class="px-2.5 py-2.5 text-xs text-neutral-700 dark:text-neutral-300">
                  <div class="truncate font-medium" :title="camp.baslik">{{ camp.baslik }}</div>
                </td>
                
                <td v-if="isColumnVisible('tur')" class="px-1.5 py-2.5 text-center">
                  <span class="px-1.5 py-0.5 rounded-md text-[10px] font-bold bg-blue-50 dark:bg-blue-900/30 text-blue-600 dark:text-blue-300 truncate inline-block max-w-full" :title="formatTur(camp.tur)">{{ formatTur(camp.tur) }}</span>
                </td>
                
                <td v-if="isColumnVisible('karPayi')" class="px-1.5 py-2.5 text-center text-xs text-neutral-600 dark:text-neutral-300" :class="{'text-neutral-300 dark:text-neutral-600 italic': !isValidVal(camp.karPayi)}">{{ formatVal(camp.karPayi) }}</td>
                <td v-if="isColumnVisible('vade')" class="px-1.5 py-2.5 text-center text-xs text-neutral-600 dark:text-neutral-300" :class="{'text-neutral-300 dark:text-neutral-600 italic': !isValidVal(camp.vade)}">{{ formatVal(camp.vade) }}</td>
                <td v-if="isColumnVisible('taksit')" class="px-1.5 py-2.5 text-center text-xs text-neutral-600 dark:text-neutral-300" :class="{'text-neutral-300 dark:text-neutral-600 italic': !isValidVal(camp.taksit)}">{{ formatVal(camp.taksit) }}</td>
                
                <td v-if="isColumnVisible('odul')" class="px-1.5 py-2.5 text-center text-xs font-bold" :class="isValidVal(camp.odul) ? 'text-emerald-600 dark:text-emerald-400' : 'text-neutral-300 dark:text-neutral-600 italic'">{{ isValidVal(camp.odul) ? Number(camp.odul).toLocaleString('tr-TR') : '-' }}</td>
                
                <td v-if="isColumnVisible('bitisTarihi')" class="px-1.5 py-2.5 text-center text-xs text-neutral-600 dark:text-neutral-300 font-mono">{{ formatTarih(camp.bitisTarihi) }}</td>
                <td v-if="isColumnVisible('hedefKitle')" class="px-2 py-2.5 text-xs text-neutral-600 dark:text-neutral-300">
                  <div class="truncate" :title="formatHedefKitle(camp.hedefKitle)">{{ formatHedefKitle(camp.hedefKitle) }}</div>
                </td>
              </tr>
            </template>
          </tbody>
        </table>
      </div>
    </div>

    <!-- ================= ÇIKARIM KANITLARI ================= -->
    <div class="space-y-4 pt-4 pb-12">
      <div class="flex flex-col gap-1">
        <h2 class="text-2xl font-bold text-neutral-800 dark:text-neutral-100">
          {{ $t('campaigns.evidence_title', 'Çıkarım Kanıtları') }}
        </h2>
        <p class="text-sm text-neutral-500 dark:text-neutral-400">
          {{ $t('campaigns.evidence_desc', 'Bir kampanya seçin: sistemin her değeri metindeki HANGİ ifadeden ve hangi yöntemle çıkardığını görün.') }}
        </p>
      </div>

      <!-- Kampanya Seçici Kartı -->
      <div class="bg-white/80 dark:bg-neutral-800/80 backdrop-blur-md p-4 rounded-xl border border-neutral-200/60 dark:border-neutral-700/60 shadow-sm relative z-30">
        <label class="block text-xs font-bold text-neutral-500 dark:text-neutral-400 uppercase tracking-wider mb-2">
          {{ $t('campaigns.select_campaign_label', 'İncelenecek Kampanyayı Seçin') }}
        </label>
        
        <!-- Özel Seçim Açılır Menüsü -->
        <div class="relative">
          <button
            type="button"
            @click="campaignSelectOpen = !campaignSelectOpen"
            class="w-full bg-neutral-50 dark:bg-neutral-900 border rounded-lg px-4 py-3 text-left text-sm flex items-center justify-between transition-all"
            :class="campaignSelectOpen ? 'border-cyan-500 ring-2 ring-cyan-500/30' : 'border-neutral-200 dark:border-neutral-700 hover:border-neutral-300 dark:hover:border-neutral-600'"
          >
            <span :class="selectedCampaignId ? 'text-neutral-800 dark:text-neutral-200' : 'text-neutral-400'">{{ selectedCampaignLabel }}</span>
            <svg class="w-4 h-4 text-neutral-400 flex-shrink-0 transition-transform" :class="campaignSelectOpen ? 'rotate-180' : ''" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M19 9l-7 7-7-7"/></svg>
          </button>

          <div v-if="campaignSelectOpen" @click="campaignSelectOpen = false" class="fixed inset-0 z-20"></div>

          <Transition name="dropdown">
            <div v-if="campaignSelectOpen" class="absolute top-full left-0 right-0 mt-1 z-40 bg-white dark:bg-neutral-900 border border-neutral-200 dark:border-neutral-700 rounded-lg shadow-xl max-h-72 overflow-y-auto py-1 custom-scrollbar" data-lenis-prevent="true">
              <button type="button" @click="selectCampaign(null)" class="w-full text-left px-4 py-2.5 text-sm text-neutral-500 hover:bg-cyan-50 dark:hover:bg-cyan-900/20 transition-colors">
                {{ $t('campaigns.select_from_table', 'Tablodan bir kampanya seçin...') }}
              </button>
              <button
                v-for="c in campaigns"
                :key="c.id"
                type="button"
                @click="selectCampaign(c.id)"
                class="w-full text-left px-4 py-2.5 text-sm transition-colors flex items-center gap-2.5"
                :class="selectedCampaignId === c.id ? 'bg-cyan-50 dark:bg-cyan-900/30 text-cyan-700 dark:text-cyan-300 font-medium' : 'text-neutral-700 dark:text-neutral-200 hover:bg-cyan-50 dark:hover:bg-cyan-900/20'"
              >
                <div class="w-5 h-5 rounded-md bg-white p-0.5 flex items-center justify-center shrink-0 border border-neutral-200/60 dark:border-white/20 shadow-2xs">
                  <img :src="getBankaLogo(c.banka)" class="w-full h-full object-contain" @error="(e) => e.target.style.display = 'none'" />
                </div>
                <span class="truncate">{{ getBankaAd(c.banka) }} — {{ c.baslik }}</span>
              </button>
            </div>
          </Transition>
        </div>

        <Transition name="ev-fade">
        <div v-if="selectedCampaignId && !pendingEvidences" class="overflow-x-auto border border-neutral-200/50 dark:border-neutral-700/50 rounded-xl custom-scrollbar" data-lenis-prevent="true">
          <table class="w-full text-left border-collapse whitespace-nowrap">
            <thead>
              <tr class="bg-neutral-100/50 dark:bg-neutral-900/50 text-xs uppercase text-neutral-500 dark:text-neutral-400">
                <th class="p-3 font-semibold border-b border-neutral-200/50 dark:border-neutral-700/50">{{ $t('campaigns.evidence_fields.field', 'Alan') }}</th>
                <th class="p-3 font-semibold border-b border-neutral-200/50 dark:border-neutral-700/50">{{ $t('campaigns.evidence_fields.text_phrase', 'Metindeki İfade') }}</th>
                <th class="p-3 font-semibold border-b border-neutral-200/50 dark:border-neutral-700/50">{{ $t('campaigns.evidence_fields.normalized', 'Normalize Değer') }}</th>
                <th class="p-3 font-semibold border-b border-neutral-200/50 dark:border-neutral-700/50">{{ $t('campaigns.evidence_fields.method', 'Yöntem') }}</th>
                <th class="p-3 font-semibold border-b border-neutral-200/50 dark:border-neutral-700/50 text-center">{{ $t('campaigns.evidence_fields.confidence', 'Güven') }}</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-neutral-200/50 dark:divide-neutral-700/50 text-sm">
              <tr v-if="activeEvidences.length === 0">
                <td colspan="5" class="p-6 text-center text-neutral-500">{{ $t('campaigns.no_evidence_found', 'Bu kampanya için çıkarım kanıtı bulunamadı.') }}</td>
              </tr>
              <tr v-for="(ev, idx) in activeEvidences" :key="idx"
                  :style="{ transitionDelay: `${idx * 60}ms` }"
                  :class="evidenceReady ? 'opacity-100 translate-x-0' : 'opacity-0 -translate-x-3'"
                  class="row-anim hover:bg-neutral-50/50 dark:hover:bg-neutral-800/30 transition-all duration-500">
                <td class="p-3 font-medium text-neutral-800 dark:text-neutral-200">{{ ev.alan }}</td>
                <td class="p-3 text-neutral-600 dark:text-neutral-300 italic">"{{ ev.ifade }}"</td>
                <td class="p-3 text-neutral-800 dark:text-neutral-200 font-mono text-xs">{{ ev.normalize }}</td>
                <td class="p-3">
                  <span class="px-2 py-1 rounded text-[10px] font-bold uppercase tracking-wider"
                        :class="ev.yontem === 'kural' ? 'bg-indigo-100 text-indigo-700 dark:bg-indigo-900/50 dark:text-indigo-300' : 'bg-cyan-100 text-cyan-700 dark:bg-cyan-900/50 dark:text-cyan-300'">
                    {{ ev.yontem }}
                  </span>
                </td>
                <td class="p-3 text-center">
                  <div class="inline-flex items-center gap-2">
                    <div class="w-16 h-1.5 rounded-full bg-neutral-200 dark:bg-neutral-700 overflow-hidden">
                      <div class="h-full rounded-full transition-all duration-700" :class="Number(ev.guven) > 0.8 ? 'bg-emerald-500' : 'bg-orange-400'" :style="{ width: evidenceReady ? (Number(ev.guven) * 100) + '%' : '0%' }"></div>
                    </div>
                    <span class="font-mono text-xs" :class="Number(ev.guven) > 0.8 ? 'text-emerald-600 dark:text-emerald-400' : 'text-orange-500'">{{ ev.guven }}</span>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        </Transition>

        <div v-if="selectedCampaignId && pendingEvidences" class="p-8 text-center text-neutral-500 animate-pulse bg-neutral-50/50 dark:bg-neutral-900/30 rounded-xl">
          {{ $t('campaigns.loading_evidences', 'Kanıtlar yükleniyor...') }}
        </div>

        <div v-if="selectedCampaignId" class="border border-neutral-200/50 dark:border-neutral-700/50 rounded-xl overflow-hidden">
          <button @click="isTextExpanded = !isTextExpanded" class="w-full p-4 flex justify-between items-center bg-neutral-50 dark:bg-neutral-900/50 hover:bg-neutral-100 dark:hover:bg-neutral-800 transition-colors">
            <span class="text-sm font-semibold text-neutral-700 dark:text-neutral-200">{{ $t('campaigns.processed_text', 'Kampanyanın işlenmiş metni') }}</span>
            <svg class="w-5 h-5 text-neutral-500 transform transition-transform duration-300" :class="{'rotate-180': isTextExpanded}" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
            </svg>
          </button>
          <div class="grid transition-all duration-500 ease-in-out" :class="isTextExpanded ? 'grid-rows-[1fr]' : 'grid-rows-[0fr]'">
            <div class="overflow-hidden">
              <div class="p-4 bg-white dark:bg-neutral-900 text-sm text-neutral-600 dark:text-neutral-400 leading-relaxed max-h-64 overflow-y-auto custom-scrollbar" data-lenis-prevent="true">
                {{ activeCampaignText }}
              </div>
            </div>
          </div>
        </div>

        <div v-if="selectedCampaignId" class="pt-2">
          <a :href="activeCampaignUrl" target="_blank" class="inline-flex items-center gap-2 px-4 py-2 bg-white dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 rounded-lg text-sm font-medium text-neutral-700 dark:text-neutral-200 hover:bg-neutral-50 dark:hover:bg-neutral-700 hover:border-cyan-300 hover:-translate-y-0.5 transition-all shadow-sm">
            {{ $t('campaigns.open_source_page', 'Kaynak sayfayı aç') }}
            <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" /></svg>
          </a>
        </div>

      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { useI18n } from 'vue-i18n'
import Lenis from 'lenis'
import { useTaxonomy } from '~/composables/useTaxonomy'

const { t } = useI18n()
const { formatTur, formatHedefKitle, formatKategori } = useTaxonomy()

useHead({
  title: computed(() => t('page_titles.campaigns', 'Tüm Kampanyalar'))
})

// --- REAKTİF DURUMLAR (STATE) ---
const pending = ref(true)
const pendingEvidences = ref(false)
const isTextExpanded = ref(false)
const selectedCampaignId = ref(null)
const revealed = ref(false)
const evidenceReady = ref(false)
const openDropdown = ref(null)
const campaignSelectOpen = ref(false)

const campaigns = ref([])
const banks = ref([])
const activeEvidences = ref([])
const totalCount = ref(0)

const search = ref('')
const sortKey = ref('')
const sortDir = ref('asc')

const filters = ref({
  banka: [],
  tur: [],
  kitle: [],
  sadeceOranli: false
})

const filterQuery = ref({ banka: '', tur: '', kitle: '' })
const filterOptions = ref({
  bankalar: [],
  turler: [],
  kitleler: []
})
const filterInputs = {}

// --- YARDIMCI DOĞRULAMA VE FORMATLAMA ---
const isValidVal = (val) => val !== null && val !== undefined && val !== '' && String(val).trim().toLowerCase() !== 'none' && String(val).trim().toLowerCase() !== 'null' && String(val).trim() !== '-'
const formatVal = (val) => isValidVal(val) ? val : '-'
const formatTarih = (val) => {
  if (!isValidVal(val)) return '-'
  try {
    const d = new Date(val)
    if (isNaN(d.getTime())) return String(val).replace(/T.*$/, '')
    const day = String(d.getDate()).padStart(2, '0')
    const month = String(d.getMonth() + 1).padStart(2, '0')
    const year = d.getFullYear()
    return `${day}.${month}.${year}`
  } catch {
    return String(val).replace(/T.*$/, '')
  }
}

const getBankaLogo = (banka_id) => {
  if (!banka_id) return null
  const b = banks.value.find(x => x._id === banka_id || x.id === banka_id || x.kisa_ad?.toLowerCase().replace(/ /g, '') === banka_id)
  if (b?.logo_url) return b.logo_url
  const cleanId = String(banka_id).toLowerCase().replace(/_/g, '').replace(/ /g, '')
  return `/${cleanId}_logo.svg`
}

const getBankaAd = (banka_id) => {
  if (!banka_id) return '-'
  const b = banks.value.find(x => x._id === banka_id || x.id === banka_id || x.kisa_ad?.toLowerCase().replace(/ /g, '') === banka_id)
  return b ? (b.kisa_ad || b.resmi_ad) : banka_id
}

const getFilterOptionLabel = (key, opt) => {
  if (!opt) return '-'
  if (key === 'banka') return getBankaAd(opt)
  if (key === 'tur') return formatTur(opt)
  if (key === 'kitle') return formatHedefKitle(opt)
  return opt
}

// --- FİLTRELENMİŞ VE HESAPLANMIŞ ALANLAR ---
const filterDefs = computed(() => [
  { key: 'banka', label: t('campaigns.columns.banka', 'Banka'), options: filterOptions.value.bankalar },
  { key: 'tur', label: t('campaigns.columns.tur', 'Tür'), options: filterOptions.value.turler },
  { key: 'kitle', label: t('campaigns.columns.hedefKitle', 'Hedef Kitle'), options: filterOptions.value.kitleler }
])

const filteredCampaigns = computed(() => {
  const q = search.value.trim().toLocaleLowerCase('tr')
  const f = filters.value || { banka: [], tur: [], kitle: [], sadeceOranli: false }
  return campaigns.value.filter(camp => {
    const matchBanka = !f.banka?.length || f.banka.includes(camp.banka)
    const matchTur = !f.tur?.length || f.tur.includes(camp.tur)
    const matchKitle = !f.kitle?.length || f.kitle.some(k => {
      const campKitle = String(camp.hedefKitle || '').toLowerCase()
      return campKitle.includes(String(k).toLowerCase())
    })
    
    const matchOran = !f.sadeceOranli || (isValidVal(camp.karPayi) && parseFloat(camp.karPayi) > 0)
    
    const matchSearch = !q ||
      (camp.baslik && camp.baslik.toLocaleLowerCase('tr').includes(q)) ||
      (camp.banka && camp.banka.toLocaleLowerCase('tr').includes(q))
    return matchBanka && matchTur && matchKitle && matchOran && matchSearch
  })
})

const displayedCampaigns = computed(() => {
  const list = [...filteredCampaigns.value]
  if (!sortKey.value) return list
  const numericKeys = ['karPayi', 'vade', 'taksit', 'odul']
  const dir = sortDir.value === 'asc' ? 1 : -1
  return list.sort((a, b) => {
    let va = a[sortKey.value]
    let vb = b[sortKey.value]
    if (va === null || va === undefined || va === '' || va === 'None') return 1
    if (vb === null || vb === undefined || vb === '' || vb === 'None') return -1
    if (numericKeys.includes(sortKey.value)) {
      return (parseFloat(va) - parseFloat(vb)) * dir
    }
    return String(va).localeCompare(String(vb), 'tr') * dir
  })
})

const hasAnyValidRow = (getterFn) => {
  if (!filteredCampaigns.value || filteredCampaigns.value.length === 0) return true
  return filteredCampaigns.value.some(camp => {
    const val = getterFn(camp)
    if (val === null || val === undefined) return false
    const s = String(val).trim().toLowerCase()
    return s !== '' && s !== 'none' && s !== 'null' && s !== '-' && s !== 'bilinmiyor'
  })
}

const columns = computed(() => {
  const cols = [
    { key: 'banka', label: t('campaigns.columns.banka', 'Banka'), sortable: true, align: 'left', width: 'w-[15%] min-w-[130px]' },
    { key: 'baslik', label: t('campaigns.columns.kampanya', 'Kampanya'), sortable: true, align: 'left', width: 'min-w-[200px]' }
  ]
  
  if (hasAnyValidRow(c => c.tur)) {
    cols.push({ key: 'tur', label: t('campaigns.columns.tur', 'Tür'), sortable: true, align: 'center', width: 'w-[9%] min-w-[80px]' })
  }
  
  if (hasAnyValidRow(c => (isValidVal(c.karPayi) && parseFloat(c.karPayi) > 0) ? c.karPayi : null)) {
    cols.push({ key: 'karPayi', label: t('campaigns.columns.karPayi', 'Kâr Payı (%)'), sortable: true, align: 'center', width: 'w-[9%] min-w-[85px]' })
  }
  
  if (hasAnyValidRow(c => (isValidVal(c.vade) && parseInt(c.vade) > 0) ? c.vade : null)) {
    cols.push({ key: 'vade', label: t('campaigns.columns.vade', 'Vade (ay)'), sortable: true, align: 'center', width: 'w-[7%] min-w-[70px]' })
  }
  
  if (hasAnyValidRow(c => (isValidVal(c.taksit) && c.taksit !== '-') ? c.taksit : null)) {
    cols.push({ key: 'taksit', label: t('campaigns.columns.taksit', 'Taksit'), sortable: true, align: 'center', width: 'w-[7%] min-w-[70px]' })
  }
  
  if (hasAnyValidRow(c => (isValidVal(c.odul) && Number(c.odul) > 0) ? c.odul : null)) {
    cols.push({ key: 'odul', label: t('campaigns.columns.odul', 'Ödül (TL)'), sortable: true, align: 'center', width: 'w-[8%] min-w-[80px]' })
  }
  
  if (hasAnyValidRow(c => (isValidVal(c.bitisTarihi) && c.bitisTarihi !== '-') ? c.bitisTarihi : null)) {
    cols.push({ key: 'bitisTarihi', label: t('campaigns.columns.bitisTarihi', 'Bitiş'), sortable: true, align: 'center', width: 'w-[9%] min-w-[85px]' })
  }
  
  if (hasAnyValidRow(c => {
    const k = c.hedefKitle
    if (!k || k === '-') return null
    return (Array.isArray(k) ? k.length > 0 : String(k).trim().length > 0) ? k : null
  })) {
    cols.push({ key: 'hedefKitle', label: t('campaigns.columns.hedefKitle', 'Hedef Kitle'), sortable: true, align: 'left', width: 'w-[11%] min-w-[100px]' })
  }
  
  return cols
})

const isColumnVisible = (key) => {
  return columns.value.some(c => c.key === key)
}

const activeFilterCount = computed(() =>
  filters.value.banka.length +
  filters.value.tur.length +
  filters.value.kitle.length +
  (filters.value.sadeceOranli ? 1 : 0) +
  (search.value.trim() ? 1 : 0)
)

const selectedCampaignLabel = computed(() => {
  const c = campaigns.value.find(x => x.id === selectedCampaignId.value)
  return c ? `${c.banka} — ${c.baslik}` : t('campaigns.select_from_table', 'Tablodan bir kampanya seçin...')
})

const activeCampaignText = computed(() => {
  const camp = campaigns.value.find(c => c.id === selectedCampaignId.value)
  return camp ? camp.metin : ''
})

const activeCampaignUrl = computed(() => {
  const camp = campaigns.value.find(c => c.id === selectedCampaignId.value)
  return camp ? camp.url : '#'
})

// --- EYLEMLER VE İŞLEVLER ---
const setFilterInputRef = (key, el) => { if (el) filterInputs[key] = el }

const focusFilter = (key) => {
  if (openDropdown.value === key) {
    openDropdown.value = null
    return
  }
  openDropdown.value = key
  nextTick(() => filterInputs[key] && filterInputs[key].focus())
}

const filteredOptions = (def) => {
  const q = (filterQuery.value[def.key] || '').trim().toLocaleLowerCase('tr')
  if (!q) return def.options
  return def.options.filter(o => {
    const rawMatch = String(o).toLocaleLowerCase('tr').includes(q)
    const labelMatch = String(getFilterOptionLabel(def.key, o)).toLocaleLowerCase('tr').includes(q)
    return rawMatch || labelMatch
  })
}

const onFilterBackspace = (key) => {
  if (!filterQuery.value[key] && filters.value[key].length) {
    filters.value[key].pop()
  }
}

const toggleValue = (key, val) => {
  const arr = filters.value[key]
  const idx = arr.indexOf(val)
  if (idx === -1) arr.push(val)
  else arr.splice(idx, 1)
  filterQuery.value[key] = ''
  nextTick(() => filterInputs[key] && filterInputs[key].focus())
}

const clearFilters = () => {
  filters.value.banka = []
  filters.value.tur = []
  filters.value.kitle = []
  filters.value.sadeceOranli = false
  filterQuery.value = { banka: '', tur: '', kitle: '' }
  search.value = ''
  openDropdown.value = null
}

const setSort = (key) => {
  if (sortKey.value === key) {
    sortDir.value = sortDir.value === 'asc' ? 'desc' : 'asc'
  } else {
    sortKey.value = key
    sortDir.value = 'asc'
  }
}

const selectCampaign = (id) => {
  selectedCampaignId.value = id
  campaignSelectOpen.value = false
  
  if (id) {
    setTimeout(() => {
      window.scrollBy({ top: 300, behavior: 'smooth' })
    }, 100)
  }
}

const fetchBanks = async () => {
  try {
    const res = await fetch('http://localhost:8003/banks')
    if (res.ok) {
      banks.value = await res.json()
    }
  } catch (e) {
    console.error('Bankalar alinamadi:', e)
  }
}

const fetchCampaigns = async () => {
  try {
    const res = await fetch('http://localhost:8003/campaigns?limit=1000&sadece_gecerli=false')
    if (!res.ok) throw new Error('API Hatası')
    const data = await res.json()
    
    campaigns.value = data.map(c => {
      const gb = c.genel_bilgi || {}
      const fd = c.finansman_detay || {}
      const pd = c.promosyon_detay || {}
      return {
        id: c._id || c.id,
        banka: gb.banka_id || c.banka,
        baslik: gb.kampanya_adi || c.baslik,
        tur: gb.kampanya_turu || c.kampanya_turu,
        karPayi: fd.kar_payi_orani || c.kar_payi_orani,
        vade: fd.vade_ay || c.vade_ay,
        taksit: fd.taksit || c.taksit_sayisi,
        odul: pd.odul_tutari || c.odul_miktari,
        bitisTarihi: gb.bitis_tarihi || c.bitis_tarihi,
        hedefKitle: Array.isArray(gb.hedef_kitle) ? gb.hedef_kitle.join(', ') : (gb.hedef_kitle || c.hedef_kitle),
        url: gb.kaynak_url || c.url,
        metin: gb.metin || ''
      }
    })
    totalCount.value = campaigns.value.length

    filterOptions.value.bankalar = [...new Set(campaigns.value.map(c => c.banka).filter(isValidVal))]
    filterOptions.value.turler = [...new Set(campaigns.value.map(c => c.tur).filter(isValidVal))]
    
    const allKitleTokens = campaigns.value.flatMap(c => {
      const raw = c.hedefKitle
      if (!raw) return []
      if (Array.isArray(raw)) return raw
      return String(raw).split(',').map(s => s.trim())
    }).filter(k => k && k !== '-' && k.toLowerCase() !== 'segment' && k.toLowerCase() !== 'segment_esnaf' && isValidVal(k))

    filterOptions.value.kitleler = [...new Set(allKitleTokens)]

  } catch (err) {
    console.error("Kampanyalar API'den çekilemedi:", err)
    campaigns.value = []
  }
}

const fetchCampaignDetail = async (id) => {
  try {
    const res = await fetch(`http://localhost:8003/campaigns/${id}`)
    
    if (!res.ok) {
      console.error("Backend'den kampanya detayı alınırken hata döndü. HTTP Kodu:", res.status)
      throw new Error('Detay API Hatası')
    }
    
    const data = await res.json()
    
    activeEvidences.value = (data.kanitlar || []).map(k => ({
      alan: k.alan_adi || k.alan || 'Bilinmeyen Alan',
      ifade: k.ham_deger || k.ifade || 'Değer çıkarılamadı',
      normalize: k.normalize_deger || k.normalize || '-',
      yontem: k.yontem || 'Bilinmiyor',
      guven: k.guven_skoru || k.guven || 0
    }))
    
    const gb = data.genel_bilgi || {}
    const metinContent = gb.metin || data.metin || data.ham_metin || ''
    const urlContent = gb.kaynak_url || data.url || '#'
    
    const campIndex = campaigns.value.findIndex(c => c.id === id)
    if (campIndex !== -1) {
      if (metinContent) campaigns.value[campIndex].metin = metinContent
      if (urlContent && urlContent !== '#') campaigns.value[campIndex].url = urlContent
    }
  } catch (err) {
    console.error("Kampanya detayı çekilemedi:", err)
    activeEvidences.value = []
  }
}

const handleKeyDown = (e) => {
  if (e.key === 'Escape') {
    if (openDropdown.value) openDropdown.value = null
    if (campaignSelectOpen.value) campaignSelectOpen.value = false
    if (selectedCampaignId.value) selectedCampaignId.value = null
  }
}

// --- İZLEYİCİLER (WATCHERS) ---
watch(columns, (newCols) => {
  if (sortKey.value && !newCols.some(c => c.key === sortKey.value)) {
    sortKey.value = ''
  }
})

watch([filteredCampaigns, sortKey, sortDir], () => {
  revealed.value = false
  nextTick(() => { setTimeout(() => { revealed.value = true }, 30) })
})

watch(selectedCampaignId, async (newId) => {
  if (newId) {
    pendingEvidences.value = true
    evidenceReady.value = false
    isTextExpanded.value = false
    
    await fetchCampaignDetail(newId)
    
    pendingEvidences.value = false
    nextTick(() => { setTimeout(() => { evidenceReady.value = true }, 50) })
  } else {
    activeEvidences.value = []
    evidenceReady.value = false
  }
})

// --- YAŞAM DÖNGÜSÜ ---
let lenis = null
let lenisRafId = null

onMounted(async () => {
  if (process.client) {
    window.addEventListener('keydown', handleKeyDown)
  }
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
    const raf = (time) => { lenis.raf(time); lenisRafId = requestAnimationFrame(raf) }
    lenisRafId = requestAnimationFrame(raf)
  }

  await fetchBanks()
  await fetchCampaigns()
  pending.value = false
  nextTick(() => { setTimeout(() => { revealed.value = true }, 30) })
})

onUnmounted(() => {
  if (process.client) {
    window.removeEventListener('keydown', handleKeyDown)
  }
  if (lenisRafId) cancelAnimationFrame(lenisRafId)
  if (lenis) { lenis.destroy(); lenis = null }
})
</script>

<style scoped>
.gradient-text {
  background-image: linear-gradient(90deg, #2563eb, #06b6d4, #6366f1, #2563eb);
  background-size: 300% 100%;
  animation: gradShift 7s ease infinite;
}
@keyframes gradShift { 0% { background-position: 0% 50%; } 50% { background-position: 100% 50%; } 100% { background-position: 0% 50%; } }

.reveal-title { animation: titleIn 0.8s cubic-bezier(0.22,1,0.36,1) both; }
@keyframes titleIn { from { opacity: 0; transform: translateY(16px); } to { opacity: 1; transform: translateY(0); } }
.title-underline { animation: underlineGrow 0.9s ease 0.3s both; transform-origin: center; }
@keyframes underlineGrow { from { transform: scaleX(0); opacity: 0; } to { transform: scaleX(1); opacity: 1; } }

.dropdown-enter-active, .dropdown-leave-active { transition: opacity 0.2s ease, transform 0.2s ease; transform-origin: top; }
.dropdown-enter-from, .dropdown-leave-to { opacity: 0; transform: translateY(-6px) scaleY(0.96); }

.ev-fade-enter-active { transition: opacity 0.45s ease, transform 0.45s cubic-bezier(0.22,1,0.36,1); }
.ev-fade-leave-active { transition: opacity 0.2s ease; }
.ev-fade-enter-from { opacity: 0; transform: translateY(14px); }
.ev-fade-leave-to { opacity: 0; }

.chip { animation: chipPop 0.2s ease; }
@keyframes chipPop { from { transform: scale(0.8); opacity: 0; } to { transform: scale(1); opacity: 1; } }

.row-anim { will-change: opacity, transform; }

.shimmer { position: relative; overflow: hidden; }
.shimmer::after {
  content: ''; position: absolute; inset: 0; transform: translateX(-100%);
  background: linear-gradient(90deg, transparent, rgba(255,255,255,0.25), transparent);
  animation: shimmer 1.4s infinite;
}
@keyframes shimmer { 100% { transform: translateX(100%); } }

.custom-scrollbar::-webkit-scrollbar { width: 6px; height: 6px; }
.custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
.custom-scrollbar::-webkit-scrollbar-thumb { background: #cbd5e1; border-radius: 10px; }
:global(.dark) .custom-scrollbar::-webkit-scrollbar-thumb { background: #475569; }
.custom-scrollbar::-webkit-scrollbar-thumb:hover { background: #94a3b8; }
</style>