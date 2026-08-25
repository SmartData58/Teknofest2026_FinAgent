<template>
  <div class="p-6 md:p-8 space-y-12 w-full max-w-[1400px] mx-auto min-h-full transition-transform duration-500 ease-[cubic-bezier(0.2,0.8,0.2,1)]"
       :class="selectedModalCampaign ? 'lg:-translate-x-28 xl:-translate-x-32' : 'translate-x-0'">

    <!-- BAŞLIK -->
    <div class="flex flex-col items-center text-center gap-3 max-w-2xl mx-auto">
      <h1 class="reveal-title text-4xl md:text-5xl font-bold bg-clip-text text-transparent gradient-text pb-1">
        {{ $t('comparison.title', 'Karşılaştırma') }}
      </h1>
      <p class="text-sm md:text-base text-neutral-500 dark:text-neutral-400">
        Şartnamedeki kriterlere göre kampanya kıyası. Bir alan 'Belirtilmemiş' ise o kampanya ilgili kritere dahil edilmez.
      </p>
      <div class="h-1 w-24 rounded-full bg-gradient-to-r from-blue-500 to-cyan-400 mt-1 title-underline"></div>
    </div>

    
    <!-- KİŞİSELLEŞTİRİLMİŞ KARŞILAŞTIRMA MATRİSİ -->
    <div class="reveal-on-scroll space-y-6 bg-white/80 dark:bg-neutral-800/50 backdrop-blur-md border border-neutral-200/50 dark:border-neutral-700/50 rounded-2xl p-6 shadow-sm">
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-neutral-200 dark:border-neutral-700 pb-3">
        <h2 class="text-xl font-bold text-neutral-800 dark:text-neutral-100 flex items-center gap-2">
          <span class="inline-block w-1.5 h-5 rounded-full bg-gradient-to-b from-indigo-500 to-purple-500"></span>
          {{ $t('comparison.custom_compare', 'Özel Karşılaştırma Matrisi') }}
        </h2>

        <!-- Dışa Aktarma Butonları (Sonuç Geldikten Sonra) -->
        <div v-if="matrixData.length > 0" class="flex items-center gap-1.5" data-png-gizle>
          <button @click="exportMatrix('excel')" title="Excel Olarak İndir" class="p-2 bg-green-50 dark:bg-green-900/20 text-green-600 dark:text-green-400 border border-green-200 dark:border-green-800/50 rounded-lg hover:bg-green-100 dark:hover:bg-green-900/40 transition-all shadow-sm hover:shadow active:scale-95 group">
            <svg class="w-4 h-4 group-hover:-translate-y-0.5 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 10h18M3 14h18m-9-4v8m-7 0h14a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"></path></svg>
          </button>
          <button @click="exportMatrix('pdf')" title="PDF Olarak İndir" class="p-2 bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 border border-red-200 dark:border-red-800/50 rounded-lg hover:bg-red-100 dark:hover:bg-red-900/40 transition-all shadow-sm hover:shadow active:scale-95 group">
            <svg class="w-4 h-4 group-hover:-translate-y-0.5 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path></svg>
          </button>
          <button @click="exportMatrix('png')" title="PNG Olarak Kaydet" class="p-2 bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400 border border-blue-200 dark:border-blue-800/50 rounded-lg hover:bg-blue-100 dark:hover:bg-blue-900/40 transition-all shadow-sm hover:shadow active:scale-95 group">
            <svg class="w-4 h-4 group-hover:-translate-y-0.5 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"></path></svg>
          </button>
        </div>
      </div>
      
      <!-- Arama ve Seçim Çubuğu -->
      <div class="relative z-30">
        <div class="flex flex-col md:flex-row gap-3 items-start md:items-center">
          <div class="relative w-full md:w-2/3">
            <input 
              v-model="searchQuery" 
              @focus="showDropdown = true"
              type="text" 
              :placeholder="$t('comparison.search_placeholder', 'Karşılaştırmak istediğiniz kampanyayı arayın...')"
              class="w-full bg-white dark:bg-neutral-900 border border-neutral-200 dark:border-neutral-700 rounded-xl px-4 py-3 text-sm focus:ring-2 focus:ring-indigo-500 outline-none transition-all"
            >
            <!-- Dropdown -->
            <div v-if="showDropdown && searchResults.length > 0" class="absolute top-full left-0 right-0 mt-2 bg-white dark:bg-neutral-900 border border-neutral-200 dark:border-neutral-700 rounded-xl shadow-xl max-h-60 overflow-y-auto z-50">
              <div 
                v-for="camp in searchResults" 
                :key="camp.id"
                @click="addToCompare(camp)"
                class="p-3 hover:bg-indigo-50 dark:hover:bg-indigo-900/30 cursor-pointer border-b border-neutral-100 dark:border-neutral-800 last:border-0 flex justify-between items-center transition-colors"
              >
                <div>
                  <div class="font-medium text-sm text-neutral-800 dark:text-neutral-200">{{ camp.baslik }}</div>
                  <div class="text-xs text-neutral-500 flex items-center gap-1.5 mt-0.5">
                    <img v-if="getBankaLogo(camp.banka)" :src="getBankaLogo(camp.banka)" class="w-3.5 h-3.5 object-contain" @error="(e) => e.target.style.display = 'none'" />
                    <span>{{ getBankaAd(camp.banka) }}</span>
                  </div>
                </div>
                <svg class="w-5 h-5 text-indigo-500 opacity-50" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/></svg>
              </div>
            </div>
          </div>
          <button 
            @click="fetchCompareMatrix" 
            :disabled="selectedForCompare.length < 2 || isComparing"
            class="w-full md:w-auto px-6 py-3 bg-gradient-to-r from-indigo-500 to-purple-500 hover:from-indigo-600 hover:to-purple-600 disabled:opacity-50 disabled:cursor-not-allowed text-white font-medium rounded-xl transition-all shadow-sm flex items-center justify-center gap-2"
          >
            <svg v-if="isComparing" class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>
            {{ $t('comparison.compare_btn', 'Karşılaştır') }}
          </button>
        </div>
        
        <!-- Seçilen Etiketler -->
        <div v-if="selectedForCompare.length > 0" class="flex flex-wrap gap-2 mt-4">
          <span v-for="camp in selectedForCompare" :key="camp.id" class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-indigo-100 dark:bg-indigo-900/40 text-indigo-700 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-800">
            <span class="truncate max-w-[180px]">{{ camp.baslik }}</span>
            <button @click="removeFromCompare(camp.id)" class="hover:text-indigo-900 dark:hover:text-indigo-100 hover:bg-indigo-200 dark:hover:bg-indigo-800 rounded-full p-0.5 transition-colors">
              <svg class="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>
            </button>
          </span>
        </div>
      </div>

      <!-- Karşılaştırma Matrisi Tablosu (Sadece Dolu Kısımlar Listelenir) -->
      <div id="comparison-matrix-table" v-if="matrixData.length > 0" class="mt-8 overflow-x-auto custom-scrollbar border border-neutral-200 dark:border-neutral-700 rounded-xl animate-fade-in shadow-md bg-white dark:bg-neutral-900 p-2" data-lenis-prevent="true">
        <table class="w-full text-left border-collapse min-w-max">
          <thead>
            <tr class="bg-neutral-50 dark:bg-neutral-800/50">
              <th class="p-4 border-b border-r border-neutral-200 dark:border-neutral-700 font-semibold text-neutral-500 w-44">{{ $t('comparison.feature', 'Özellik') }}</th>
              <th v-for="camp in matrixData" :key="camp.id" @click="openCampaignModal(camp.id)" class="p-4 border-b border-r last:border-r-0 border-neutral-200 dark:border-neutral-700 font-bold text-center w-64 text-indigo-600 dark:text-indigo-400 hover:bg-indigo-50/50 dark:hover:bg-indigo-900/20 cursor-pointer transition-colors group">
                <div class="text-xs text-neutral-500 mb-1 font-normal flex items-center justify-center gap-1">
                  <img v-if="getBankaLogo(camp.genel_bilgi?.banka_id)" :src="getBankaLogo(camp.genel_bilgi?.banka_id)" class="w-3.5 h-3.5 object-contain" @error="(e) => e.target.style.display = 'none'" />
                  <span>{{ getBankaAd(camp.genel_bilgi?.banka_id) }}</span>
                </div>
                <div class="whitespace-normal break-words group-hover:underline">{{ camp.genel_bilgi?.kampanya_adi }}</div>
                <div class="text-[10px] text-neutral-400 font-normal mt-1 flex items-center justify-center gap-0.5">
                  Detayı Gör <svg class="w-3 h-3 inline" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"/></svg>
                </div>
              </th>
            </tr>
          </thead>
          <tbody class="divide-y divide-neutral-200 dark:divide-neutral-700 text-sm">
            
            <!-- Kampanya Türü -->
            <tr v-if="hasAnyValidRow(c => c.genel_bilgi?.kampanya_turu)" class="hover:bg-neutral-50/50 dark:hover:bg-neutral-800/30 transition-colors">
              <td class="p-4 border-r border-neutral-200 dark:border-neutral-700 font-medium text-neutral-700 dark:text-neutral-300 bg-neutral-50/30 dark:bg-neutral-800/20">{{ $t('campaigns.columns.tur', 'Kampanya Türü') }}</td>
              <td v-for="camp in matrixData" :key="camp.id" class="p-4 border-r last:border-r-0 border-neutral-200 dark:border-neutral-700 text-center">
                {{ camp.genel_bilgi?.kampanya_turu || '-' }}
              </td>
            </tr>

            <!-- Kâr Payı -->
            <tr v-if="hasAnyValidRow(c => c.finansman_detay?.kar_payi_orani)" class="hover:bg-neutral-50/50 dark:hover:bg-neutral-800/30 transition-colors">
              <td class="p-4 border-r border-neutral-200 dark:border-neutral-700 font-medium text-neutral-700 dark:text-neutral-300 bg-neutral-50/30 dark:bg-neutral-800/20">{{ $t('campaigns.columns.karPayi', 'Kâr Payı (%)') }}</td>
              <td v-for="camp in matrixData" :key="camp.id" class="p-4 border-r last:border-r-0 border-neutral-200 dark:border-neutral-700 text-center">
                <span v-if="isValidVal(camp.finansman_detay?.kar_payi_orani)" class="font-semibold text-blue-600 dark:text-blue-400">%{{ camp.finansman_detay?.kar_payi_orani }}</span>
                <span v-else class="px-2 py-0.5 rounded text-xs bg-neutral-100 dark:bg-neutral-800 text-neutral-400">-</span>
              </td>
            </tr>

            <!-- Vade -->
            <tr v-if="hasAnyValidRow(c => c.finansman_detay?.vade_ay)" class="hover:bg-neutral-50/50 dark:hover:bg-neutral-800/30 transition-colors">
              <td class="p-4 border-r border-neutral-200 dark:border-neutral-700 font-medium text-neutral-700 dark:text-neutral-300 bg-neutral-50/30 dark:bg-neutral-800/20">{{ $t('campaigns.columns.vade', 'Vade (Ay)') }}</td>
              <td v-for="camp in matrixData" :key="camp.id" class="p-4 border-r last:border-r-0 border-neutral-200 dark:border-neutral-700 text-center">
                <span v-if="isValidVal(camp.finansman_detay?.vade_ay)">{{ camp.finansman_detay?.vade_ay }} Ay</span>
                <span v-else class="px-2 py-0.5 rounded text-xs bg-neutral-100 dark:bg-neutral-800 text-neutral-400">-</span>
              </td>
            </tr>

            <!-- Taksit -->
            <tr v-if="hasAnyValidRow(c => c.finansman_detay?.taksit)" class="hover:bg-neutral-50/50 dark:hover:bg-neutral-800/30 transition-colors">
              <td class="p-4 border-r border-neutral-200 dark:border-neutral-700 font-medium text-neutral-700 dark:text-neutral-300 bg-neutral-50/30 dark:bg-neutral-800/20">{{ $t('campaigns.columns.taksit', 'Taksit') }}</td>
              <td v-for="camp in matrixData" :key="camp.id" class="p-4 border-r last:border-r-0 border-neutral-200 dark:border-neutral-700 text-center">
                <span v-if="isValidVal(camp.finansman_detay?.taksit)">{{ camp.finansman_detay?.taksit }}</span>
                <span v-else class="px-2 py-0.5 rounded text-xs bg-neutral-100 dark:bg-neutral-800 text-neutral-400">-</span>
              </td>
            </tr>

            <!-- Tahsis Ücreti -->
            <tr v-if="hasAnyValidRow(c => c.finansman_detay?.tahsis_ucreti)" class="hover:bg-neutral-50/50 dark:hover:bg-neutral-800/30 transition-colors">
              <td class="p-4 border-r border-neutral-200 dark:border-neutral-700 font-medium text-neutral-700 dark:text-neutral-300 bg-neutral-50/30 dark:bg-neutral-800/20">Tahsis Ücreti (TL)</td>
              <td v-for="camp in matrixData" :key="camp.id" class="p-4 border-r last:border-r-0 border-neutral-200 dark:border-neutral-700 text-center">
                <span v-if="isValidVal(camp.finansman_detay?.tahsis_ucreti)" class="font-semibold text-orange-600 dark:text-orange-400">{{ Number(camp.finansman_detay?.tahsis_ucreti).toLocaleString('tr-TR') }} TL</span>
                <span v-else class="px-2 py-0.5 rounded text-xs bg-neutral-100 dark:bg-neutral-800 text-neutral-400">-</span>
              </td>
            </tr>

            <!-- Finansman Tutarı -->
            <tr v-if="hasAnyValidRow(c => c.finansman_detay?.finansman_tutari)" class="hover:bg-neutral-50/50 dark:hover:bg-neutral-800/30 transition-colors">
              <td class="p-4 border-r border-neutral-200 dark:border-neutral-700 font-medium text-neutral-700 dark:text-neutral-300 bg-neutral-50/30 dark:bg-neutral-800/20">Finansman Tutarı (TL)</td>
              <td v-for="camp in matrixData" :key="camp.id" class="p-4 border-r last:border-r-0 border-neutral-200 dark:border-neutral-700 text-center">
                <span v-if="isValidVal(camp.finansman_detay?.finansman_tutari)" class="font-semibold text-cyan-600 dark:text-cyan-400">{{ Number(camp.finansman_detay?.finansman_tutari).toLocaleString('tr-TR') }} TL</span>
                <span v-else class="px-2 py-0.5 rounded text-xs bg-neutral-100 dark:bg-neutral-800 text-neutral-400">-</span>
              </td>
            </tr>

            <!-- Ödül Miktarı -->
            <tr v-if="hasAnyValidRow(c => c.promosyon_detay?.odul_tutari)" class="hover:bg-neutral-50/50 dark:hover:bg-neutral-800/30 transition-colors">
              <td class="p-4 border-r border-neutral-200 dark:border-neutral-700 font-medium text-neutral-700 dark:text-neutral-300 bg-neutral-50/30 dark:bg-neutral-800/20">{{ $t('campaigns.columns.odul', 'Ödül Miktarı') }}</td>
              <td v-for="camp in matrixData" :key="camp.id" class="p-4 border-r last:border-r-0 border-neutral-200 dark:border-neutral-700 text-center">
                <span v-if="isValidVal(camp.promosyon_detay?.odul_tutari)" class="font-semibold text-emerald-600 dark:text-emerald-400">{{ Number(camp.promosyon_detay?.odul_tutari).toLocaleString('tr-TR') }} TL</span>
                <span v-else class="px-2 py-0.5 rounded text-xs bg-neutral-100 dark:bg-neutral-800 text-neutral-400">-</span>
              </td>
            </tr>

            <!-- MGM / Davet Et Kazan -->
            <tr v-if="hasAnyValidRow(c => c.mgm_detay?.kisi_basi_kazanc || c.mgm_detay?.davet_eden_odul || (c.mgm_detay?.is_mgm && c.promosyon_detay?.odul_tutari))" class="hover:bg-neutral-50/50 dark:hover:bg-neutral-800/30 transition-colors">
              <td class="p-4 border-r border-neutral-200 dark:border-neutral-700 font-medium text-neutral-700 dark:text-neutral-300 bg-neutral-50/30 dark:bg-neutral-800/20">MGM (Davet Et Kazan)</td>
              <td v-for="camp in matrixData" :key="camp.id" class="p-4 border-r last:border-r-0 border-neutral-200 dark:border-neutral-700 text-center">
                <span v-if="isValidVal(camp.mgm_detay?.kisi_basi_kazanc || camp.mgm_detay?.davet_eden_odul || (camp.mgm_detay?.is_mgm && camp.promosyon_detay?.odul_tutari))" class="font-bold text-amber-600 dark:text-amber-400">
                  {{ Number(camp.mgm_detay?.kisi_basi_kazanc || camp.mgm_detay?.davet_eden_odul || camp.promosyon_detay?.odul_tutari).toLocaleString('tr-TR') }} TL
                </span>
                <span v-else class="px-2 py-0.5 rounded text-xs bg-neutral-100 dark:bg-neutral-800 text-neutral-400">-</span>
              </td>
            </tr>

            <!-- Hedef Kitle -->
            <tr v-if="hasAnyValidRow(c => c.genel_bilgi?.hedef_kitle)" class="hover:bg-neutral-50/50 dark:hover:bg-neutral-800/30 transition-colors">
              <td class="p-4 border-r border-neutral-200 dark:border-neutral-700 font-medium text-neutral-700 dark:text-neutral-300 bg-neutral-50/30 dark:bg-neutral-800/20">{{ $t('campaigns.columns.hedefKitle', 'Hedef Kitle') }}</td>
              <td v-for="camp in matrixData" :key="camp.id" class="p-4 border-r last:border-r-0 border-neutral-200 dark:border-neutral-700 text-center">
                <span v-if="isValidVal(Array.isArray(camp.genel_bilgi?.hedef_kitle) ? camp.genel_bilgi.hedef_kitle.join(', ') : camp.genel_bilgi?.hedef_kitle)">{{ Array.isArray(camp.genel_bilgi?.hedef_kitle) ? camp.genel_bilgi.hedef_kitle.join(', ') : camp.genel_bilgi?.hedef_kitle }}</span>
                <span v-else class="px-2 py-0.5 rounded text-xs bg-neutral-100 dark:bg-neutral-800 text-neutral-400">-</span>
              </td>
            </tr>

          </tbody>
        </table>
      </div>
    </div>

    <!-- KRİTER SEKSİYONLARI -->
    <div v-for="(criterion, index) in criteriaConfig" :key="index" class="reveal-on-scroll space-y-4">

      <!-- Kriter Başlığı -->
      <h2 class="text-xl font-bold text-neutral-800 dark:text-neutral-100 border-b border-neutral-200 dark:border-neutral-700 pb-2 flex items-center gap-2">
        <span class="inline-block w-1.5 h-5 rounded-full" :class="criterion.id === 'highest_mgm' ? 'bg-gradient-to-b from-amber-500 to-yellow-400' : 'bg-gradient-to-b from-blue-500 to-cyan-400'"></span>
        {{ criterion.title }}
      </h2>

      <!-- Skeleton Yükleniyor Ekranı -->
      <div v-if="pending" class="bg-white/80 dark:bg-neutral-800/50 backdrop-blur-md border border-neutral-200/50 dark:border-neutral-700/50 rounded-xl overflow-hidden">
        <div class="p-4 border-b border-neutral-200/50 dark:border-neutral-700/50 flex gap-4">
          <div v-for="i in 4" :key="i" class="h-4 bg-neutral-200 dark:bg-neutral-700 rounded w-24 shimmer"></div>
        </div>
        <div class="p-4 space-y-4">
          <div v-for="i in 3" :key="`row-${i}`" class="h-6 bg-neutral-200 dark:bg-neutral-700 rounded w-full shimmer"></div>
        </div>
      </div>

      <!-- Gerçek Tablo ve Öne Çıkan -->
      <div v-else>
        <div v-if="getSortedData(criterion).length === 0" class="p-6 bg-neutral-50/50 dark:bg-neutral-900/30 border border-dashed border-neutral-300 dark:border-neutral-700 rounded-xl text-center text-sm text-neutral-500">
          Bu kriter için veritabanında uygun kampanya bulunamadı.
        </div>

        <div v-else class="space-y-4">
          <!-- Scroll Kutusu -->
          <div class="bg-white/80 dark:bg-neutral-800/50 backdrop-blur-md border border-neutral-200/50 dark:border-neutral-700/50 rounded-xl shadow-sm overflow-hidden relative">
            <div class="overflow-x-auto overflow-y-auto max-h-[320px] custom-scrollbar" data-lenis-prevent="true">
              <table class="w-full text-left border-collapse whitespace-nowrap min-w-max relative">
                <!-- Sticky Thead -->
                <thead class="sticky top-0 z-20 bg-neutral-100/95 dark:bg-neutral-900/95 backdrop-blur-md shadow-sm after:absolute after:inset-x-0 after:bottom-0 after:border-b after:border-neutral-200/50 dark:after:border-neutral-700/50">
                  <tr class="text-xs uppercase text-neutral-500 dark:text-neutral-400">
                    <th v-for="col in criterion.columns" :key="col.key" class="p-4 font-semibold">
                      {{ col.label }}
                    </th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-neutral-200/50 dark:divide-neutral-700/50 text-sm">
                  <!-- Tablo Verileri (Tıklanabilir ve Paneli Açar) -->
                  <tr v-for="(row, ri) in getSortedData(criterion)" :key="row.id"
                      @click="openCampaignModal(row.id)"
                      class="hover:bg-cyan-50/60 dark:hover:bg-cyan-900/20 transition-colors cursor-pointer group"
                      :class="ri === 0 ? 'bg-blue-50/40 dark:bg-cyan-900/10' : ''">
                    <td v-for="col in criterion.columns" :key="col.key" class="p-4 text-neutral-700 dark:text-neutral-300">
                      <span class="inline-flex items-center gap-2">
                        <span v-if="ri === 0 && col.key === 'banka'" class="text-[10px] font-bold px-1.5 py-0.5 rounded bg-gradient-to-r from-blue-500 to-cyan-400 text-white">1</span>
                        
                        <!-- Banka Kolonu (Logolu & Düzgün İsimli) -->
                        <span v-if="col.key === 'banka'" class="inline-flex items-center gap-2 font-semibold text-neutral-900 dark:text-neutral-100">
                          <img v-if="getBankaLogo(row.banka)" :src="getBankaLogo(row.banka)" class="w-4 h-4 object-contain" @error="(e) => e.target.style.display = 'none'" />
                          {{ getBankaAd(row.banka) }}
                        </span>

                        <!-- Kâr Payı Kolonu -->
                        <span v-else-if="col.key === 'karPayi'" class="font-bold text-blue-600 dark:text-blue-400">
                          {{ row.karPayi !== null && row.karPayi !== undefined ? '%' + row.karPayi : '-' }}
                        </span>

                        <!-- Ödül / MGM Kazanç Kolonları -->
                        <span v-else-if="col.key === 'odul' || col.key === 'mgmKazanc' || col.key === 'mgmLimit' || col.key === 'tahsisUcreti'" class="font-bold" :class="col.key === 'mgmKazanc' ? 'text-amber-600 dark:text-amber-400' : 'text-emerald-600 dark:text-emerald-400'">
                          {{ row[col.key] !== null && row[col.key] !== undefined ? Number(row[col.key]).toLocaleString('tr-TR') + ' TL' : '-' }}
                        </span>

                        <!-- Vade Kolonu -->
                        <span v-else-if="col.key === 'vade'">
                          {{ row.vade ? row.vade + ' Ay' : '-' }}
                        </span>

                        <!-- Genel Başlık Kolonu -->
                        <span v-else :class="{'font-medium text-neutral-900 dark:text-neutral-100 group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors': col.key === 'baslik'}">
                          {{ col.key === 'baslik' && row[col.key] && row[col.key].length > 60 ? row[col.key].substring(0, 60) + '...' : (row[col.key] ?? '-') }}
                        </span>
                      </span>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          <!-- Öne Çıkan (Şampiyon) Kutusu -->
          <div @click="openCampaignModal(getTopItem(criterion).id)" class="inline-flex items-center gap-2 px-4 py-3 bg-blue-50/50 dark:bg-cyan-900/20 border border-blue-200/50 dark:border-cyan-800/50 rounded-lg text-sm text-neutral-700 dark:text-neutral-300 hover:border-blue-400 cursor-pointer transition-all hover:shadow-sm group">
            <span class="font-bold text-blue-600 dark:text-cyan-400">En Avantajlı:</span>
            <span>
              <strong class="text-neutral-900 dark:text-white">{{ getBankaAd(getTopItem(criterion).banka) }}</strong> —
              <span class="group-hover:underline">{{ getTopItem(criterion).baslik }}</span>
              <span class="opacity-75 font-semibold text-blue-600 dark:text-blue-400 ml-1">
                ({{ getMetricLabel(criterion.sortKey) }}: {{ formatTopMetric(criterion.sortKey, getTopItem(criterion)[criterion.sortKey]) }})
              </span>
            </span>
          </div>
        </div>
      </div>
    </div>

    <!-- YASAL UYARI FOOTER -->
    <div class="reveal-on-scroll mt-8 p-5 border-l-4 border-neutral-300 dark:border-neutral-600 bg-neutral-100/50 dark:bg-neutral-800/30 text-xs sm:text-sm text-neutral-500 dark:text-neutral-400 italic rounded-r-lg">
      Bu bilgiler yatırım tavsiyesi değildir. Karşılaştırmalar yalnızca metinlerden otomatik çıkarılan alanlara dayanır; kampanya koşullarının tamamı için bankaların resmî sayfaları esastır.
    </div>

    <!-- ================= KAMPANYA DETAY PANELİ (DRAWER / MODAL) ================= -->
    <Teleport to="body">
      <Transition
        enter-active-class="transform transition-all duration-300 ease-out" 
        enter-from-class="translate-x-[120%] opacity-0 scale-95" 
        enter-to-class="translate-x-0 opacity-100 scale-100" 
        leave-active-class="transform transition-all duration-300 ease-in" 
        leave-from-class="translate-x-0 opacity-100 scale-100" 
        leave-to-class="translate-x-[120%] opacity-0 scale-95"
      >
        <div v-if="selectedModalCampaign" class="fixed right-4 top-4 bottom-4 w-[340px] sm:w-[420px] lg:w-[480px] bg-white dark:bg-[#121212] rounded-[24px] shadow-[0_12px_40px_rgba(0,0,0,0.15)] dark:shadow-[0_12px_40px_rgba(0,0,0,0.7)] border border-neutral-200 dark:border-neutral-700 flex flex-col z-[100] overflow-hidden">
          <!-- Drawer Header -->
          <div class="flex justify-between items-center p-4 border-b border-neutral-200 dark:border-neutral-700 bg-neutral-50 dark:bg-neutral-800">
            <h3 class="text-[14px] font-bold flex items-center gap-2 text-neutral-800 dark:text-white">
              <svg class="w-4 h-4 text-emerald-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4"></path></svg>
              Kampanya Detayları
            </h3>
            <button @click="selectedModalCampaign = null" class="p-1 text-neutral-500 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/30 rounded transition-colors active:scale-90 transform duration-200" title="Kapat">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg>
            </button>
          </div>

          <!-- Drawer Body -->
          <div class="flex-1 overflow-y-auto p-4 lg:p-6 custom-scrollbar space-y-4">
            
            <!-- Kaynak Link -->
            <a v-if="hasValue(selectedModalCampaign.genel_bilgi?.kaynak_url || selectedModalCampaign.url)" 
               :href="selectedModalCampaign.genel_bilgi?.kaynak_url || selectedModalCampaign.url" target="_blank" rel="noopener noreferrer"
               class="flex items-center gap-2 px-3 py-2.5 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800/50 rounded-xl text-sm font-semibold text-blue-600 dark:text-blue-400 hover:bg-blue-100 dark:hover:bg-blue-900/40 transition-colors w-fit">
              <svg class="w-4 h-4 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"></path></svg>
              Kaynak sayfaya git
            </a>

            <!-- Banka & Kampanya Adı -->
            <div class="border-b border-neutral-100 dark:border-neutral-800 pb-3">
              <div v-if="hasValue(selectedModalCampaign.genel_bilgi?.banka_id || selectedModalCampaign.banka)" class="text-xs font-bold text-indigo-500 dark:text-indigo-400 uppercase tracking-wider mb-1">
                {{ getBankaAd(selectedModalCampaign.genel_bilgi?.banka_id || selectedModalCampaign.banka) }}
              </div>
              <h2 class="text-lg font-black text-neutral-900 dark:text-white leading-snug">
                {{ selectedModalCampaign.genel_bilgi?.kampanya_adi || selectedModalCampaign.baslik }}
              </h2>
            </div>

            <!-- Parametre Grid'i -->
            <div class="grid grid-cols-2 gap-2.5">
              <!-- Tür -->
              <div v-if="hasValue(selectedModalCampaign.genel_bilgi?.kampanya_turu || selectedModalCampaign.tur)" class="bg-neutral-50 dark:bg-neutral-800/50 p-3 rounded-xl border border-neutral-100 dark:border-neutral-800">
                <div class="text-[10px] font-bold text-neutral-400 uppercase tracking-wider mb-0.5">Tür</div>
                <div class="text-xs font-semibold text-neutral-800 dark:text-neutral-200 truncate">{{ selectedModalCampaign.genel_bilgi?.kampanya_turu || selectedModalCampaign.tur }}</div>
              </div>

              <!-- Kategori -->
              <div v-if="hasValue(selectedModalCampaign.genel_bilgi?.kategori)" class="bg-neutral-50 dark:bg-neutral-800/50 p-3 rounded-xl border border-neutral-100 dark:border-neutral-800">
                <div class="text-[10px] font-bold text-neutral-400 uppercase tracking-wider mb-0.5">Kategori</div>
                <div class="text-xs font-semibold text-neutral-800 dark:text-neutral-200 truncate">{{ selectedModalCampaign.genel_bilgi?.kategori }}</div>
              </div>

              <!-- Kâr Payı -->
              <div v-if="hasValue(selectedModalCampaign.finansman_detay?.kar_payi_orani || selectedModalCampaign.karPayi)" class="bg-neutral-50 dark:bg-neutral-800/50 p-3 rounded-xl border border-neutral-100 dark:border-neutral-800">
                <div class="text-[10px] font-bold text-neutral-400 uppercase tracking-wider mb-0.5">Kâr Payı</div>
                <div class="text-xs font-bold text-blue-600 dark:text-blue-400">%{{ selectedModalCampaign.finansman_detay?.kar_payi_orani || selectedModalCampaign.karPayi }}</div>
              </div>

              <!-- Vade -->
              <div v-if="hasValue(selectedModalCampaign.finansman_detay?.vade_ay || selectedModalCampaign.vade)" class="bg-neutral-50 dark:bg-neutral-800/50 p-3 rounded-xl border border-neutral-100 dark:border-neutral-800">
                <div class="text-[10px] font-bold text-neutral-400 uppercase tracking-wider mb-0.5">Vade</div>
                <div class="text-xs font-bold text-indigo-600 dark:text-indigo-400">{{ selectedModalCampaign.finansman_detay?.vade_ay || selectedModalCampaign.vade }} Ay</div>
              </div>

              <!-- Taksit -->
              <div v-if="hasValue(selectedModalCampaign.finansman_detay?.taksit || selectedModalCampaign.taksit)" class="bg-neutral-50 dark:bg-neutral-800/50 p-3 rounded-xl border border-neutral-100 dark:border-neutral-800">
                <div class="text-[10px] font-bold text-neutral-400 uppercase tracking-wider mb-0.5">Taksit</div>
                <div class="text-xs font-semibold text-neutral-800 dark:text-neutral-200">{{ selectedModalCampaign.finansman_detay?.taksit || selectedModalCampaign.taksit }}</div>
              </div>

              <!-- Tahsis Ücreti -->
              <div v-if="hasValue(selectedModalCampaign.finansman_detay?.tahsis_ucreti || selectedModalCampaign.tahsisUcreti)" class="bg-neutral-50 dark:bg-neutral-800/50 p-3 rounded-xl border border-neutral-100 dark:border-neutral-800">
                <div class="text-[10px] font-bold text-neutral-400 uppercase tracking-wider mb-0.5">Tahsis Ücreti</div>
                <div class="text-xs font-bold text-orange-600 dark:text-orange-400">{{ Number(selectedModalCampaign.finansman_detay?.tahsis_ucreti || selectedModalCampaign.tahsisUcreti).toLocaleString('tr-TR') }} ₺</div>
              </div>

              <!-- Finansman Tutarı -->
              <div v-if="hasValue(selectedModalCampaign.finansman_detay?.finansman_tutari)" class="bg-neutral-50 dark:bg-neutral-800/50 p-3 rounded-xl border border-neutral-100 dark:border-neutral-800">
                <div class="text-[10px] font-bold text-neutral-400 uppercase tracking-wider mb-0.5">Finansman Tutarı</div>
                <div class="text-xs font-bold text-cyan-600 dark:text-cyan-400">{{ Number(selectedModalCampaign.finansman_detay?.finansman_tutari).toLocaleString('tr-TR') }} ₺</div>
              </div>

              <!-- Ödül -->
              <div v-if="hasValue(selectedModalCampaign.promosyon_detay?.odul_tutari || selectedModalCampaign.odul)" class="bg-neutral-50 dark:bg-neutral-800/50 p-3 rounded-xl border border-neutral-100 dark:border-neutral-800">
                <div class="text-[10px] font-bold text-neutral-400 uppercase tracking-wider mb-0.5">Ödül</div>
                <div class="text-xs font-bold text-emerald-600 dark:text-emerald-400">{{ Number(selectedModalCampaign.promosyon_detay?.odul_tutari || selectedModalCampaign.odul).toLocaleString('tr-TR') }} ₺</div>
              </div>

              <!-- MGM Kazanç -->
              <div v-if="hasValue(selectedModalCampaign.mgm_detay?.kisi_basi_kazanc || selectedModalCampaign.mgmKazanc)" class="bg-neutral-50 dark:bg-neutral-800/50 p-3 rounded-xl border border-neutral-100 dark:border-neutral-800">
                <div class="text-[10px] font-bold text-neutral-400 uppercase tracking-wider mb-0.5">MGM Kazanç</div>
                <div class="text-xs font-bold text-purple-600 dark:text-purple-400">{{ Number(selectedModalCampaign.mgm_detay?.kisi_basi_kazanc || selectedModalCampaign.mgmKazanc).toLocaleString('tr-TR') }} ₺</div>
              </div>

              <!-- Bitiş Tarihi -->
              <div v-if="hasValue(selectedModalCampaign.genel_bilgi?.bitis_tarihi || selectedModalCampaign.bitisTarihi)" class="bg-neutral-50 dark:bg-neutral-800/50 p-3 rounded-xl border border-neutral-100 dark:border-neutral-800">
                <div class="text-[10px] font-bold text-neutral-400 uppercase tracking-wider mb-0.5">Bitiş Tarihi</div>
                <div class="text-xs font-semibold text-neutral-800 dark:text-neutral-200">{{ formatTarih(selectedModalCampaign.genel_bilgi?.bitis_tarihi || selectedModalCampaign.bitisTarihi) }}</div>
              </div>
            </div>

            <!-- Hedef Kitle -->
            <div v-if="hasValue(selectedModalCampaign.genel_bilgi?.hedef_kitle || selectedModalCampaign.hedefKitle)" class="bg-neutral-50 dark:bg-neutral-800/50 p-3 rounded-xl border border-neutral-100 dark:border-neutral-800">
              <div class="text-[10px] font-bold text-neutral-400 uppercase tracking-wider mb-1">Hedef Kitle</div>
              <div class="text-xs font-medium text-neutral-700 dark:text-neutral-300">
                {{ Array.isArray(selectedModalCampaign.genel_bilgi?.hedef_kitle || selectedModalCampaign.hedefKitle) ? (selectedModalCampaign.genel_bilgi?.hedef_kitle || selectedModalCampaign.hedefKitle).join(', ') : (selectedModalCampaign.genel_bilgi?.hedef_kitle || selectedModalCampaign.hedefKitle) }}
              </div>
            </div>

            <!-- Masraf Bilgisi -->
            <div v-if="hasValue(selectedModalCampaign.finansman_detay?.masraf_bilgi)" class="bg-neutral-50 dark:bg-neutral-800/50 p-3 rounded-xl border border-neutral-100 dark:border-neutral-800">
              <div class="text-[10px] font-bold text-neutral-400 uppercase tracking-wider mb-1">Masraf Bilgisi</div>
              <div class="text-xs font-medium text-neutral-700 dark:text-neutral-300">{{ selectedModalCampaign.finansman_detay.masraf_bilgi }}</div>
            </div>

            <!-- Kampanya Metni -->
            <div v-if="hasValue(selectedModalCampaign.genel_bilgi?.metin || selectedModalCampaign.metin)" class="pt-3 border-t border-neutral-200 dark:border-neutral-800">
              <div class="text-[10px] font-bold text-neutral-400 uppercase tracking-wider mb-2">Kampanya Metni</div>
              <pre class="font-mono text-xs whitespace-pre-wrap leading-relaxed text-neutral-600 dark:text-neutral-300 break-words bg-neutral-50 dark:bg-neutral-900/80 p-3.5 rounded-xl border border-neutral-200/80 dark:border-neutral-800 max-h-72 overflow-y-auto custom-scrollbar">{{ selectedModalCampaign.genel_bilgi?.metin || selectedModalCampaign.metin }}</pre>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>

  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import Lenis from 'lenis'

const pending = ref(true)
const campaigns = ref([])
const banks = ref([])

const searchQuery = ref('')
const showDropdown = ref(false)
const selectedForCompare = ref([])
const matrixData = ref([])
const isComparing = ref(false)
const selectedModalCampaign = ref(null)

const isValidVal = (val) => {
  return val !== null && val !== undefined && val !== '' && String(val).trim().toLowerCase() !== 'none' && String(val).trim().toLowerCase() !== 'null'
}

const hasValue = (val) => {
  if (val === null || val === undefined) return false
  if (typeof val === 'string' && (val.trim() === '' || val.trim().toLowerCase() === 'none' || val.trim().toLowerCase() === 'null')) return false
  if (Array.isArray(val) && val.length === 0) return false
  return true
}

const formatTarih = (val) => {
  if (!val || val === '-') return '-'
  try {
    let d = new Date(val)
    if (isNaN(d.getTime())) {
      const p = String(val).split('.')
      if (p.length === 3) d = new Date(`${p[2]}-${p[1]}-${p[0]}`)
    }
    if (isNaN(d.getTime())) return val
    return d.toLocaleDateString('tr-TR', { day: 'numeric', month: 'long', year: 'numeric' })
  } catch (e) {
    return val
  }
}

// 🎯 SEÇİLEN KAMPANYALARIN HİÇBİRİNDE DOLU DEĞİLSE SATIRI GİZLEYEN YARDIMCI
const hasAnyValidRow = (getterFn) => {
  if (!matrixData.value || matrixData.value.length === 0) return false
  return matrixData.value.some(camp => isValidVal(getterFn(camp)))
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

const searchResults = computed(() => {
  const q = searchQuery.value.trim().toLocaleLowerCase('tr')
  if (!q) return []
  return campaigns.value.filter(c => 
    !selectedForCompare.value.find(s => s.id === c.id) &&
    ((c.baslik && c.baslik.toLocaleLowerCase('tr').includes(q)) || 
     (c.banka && c.banka.toLocaleLowerCase('tr').includes(q)) ||
     (getBankaAd(c.banka).toLocaleLowerCase('tr').includes(q)))
  ).slice(0, 8)
})

const addToCompare = (camp) => {
  if (selectedForCompare.value.length >= 4) {
    alert("En fazla 4 kampanya karşılaştırabilirsiniz.")
    return
  }
  selectedForCompare.value.push(camp)
  searchQuery.value = ''
  showDropdown.value = false
}

const removeFromCompare = (id) => {
  selectedForCompare.value = selectedForCompare.value.filter(c => c.id !== id)
  if (selectedForCompare.value.length === 0) {
    matrixData.value = []
  }
}

const fetchCompareMatrix = async () => {
  if (selectedForCompare.value.length < 2) return
  
  isComparing.value = true
  try {
    const ids = selectedForCompare.value.map(c => c.id).join(',')
    const res = await fetch(`http://localhost:8003/campaigns/compare?ids=${encodeURIComponent(ids)}`)
    if (res.ok) {
      matrixData.value = await res.json()
      await nextTick()
      document.getElementById('comparison-matrix-table')?.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
    } else {
      console.error("API Hatası:", res.status, await res.text())
    }
  } catch (err) {
    console.error("Karşılaştırma matrisi çekilemedi", err)
  } finally {
    isComparing.value = false
  }
}

// 🎯 KAMPANYA DETAY PANELİNİ AÇMA
const openCampaignModal = async (id) => {
  if (!id) return
  
  let camp = campaigns.value.find(c => {
    const cid = c.id || c._id
    return cid === id || String(cid) === String(id)
  })
  
  if (camp) {
    selectedModalCampaign.value = camp
  }
  
  try {
    const res = await fetch(`http://localhost:8003/campaigns/${id}`)
    if (res.ok) {
      const data = await res.json()
      selectedModalCampaign.value = data
      if (camp) {
        Object.assign(camp, data)
      }
    }
  } catch (err) {
    console.error('Kampanya detayı çekilemedi:', err)
  }
}

// ===================== EXCEL, PDF VE PNG DIŞA AKTARMA =====================
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

const escapeHtml = (str) => {
  if (str === null || str === undefined) return ''
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;')
}

const exportMatrix = async (format) => {
  if (matrixData.value.length === 0) return

  const today = new Date().toLocaleDateString('tr-TR', { year: 'numeric', month: 'long', day: 'numeric' })

  if (format === 'excel') {
    try {
      await betigiYukle('https://cdn.jsdelivr.net/npm/xlsx-js-style@1.2.0/dist/xlsx.bundle.js', 'XLSX')
      const XLSX = window.XLSX
      const wb = XLSX.utils.book_new()

      const headers = ['Özellik', ...matrixData.value.map(c => `${getBankaAd(c.genel_bilgi?.banka_id)} - ${c.genel_bilgi?.kampanya_adi || c.baslik}`)]
      const rows = [
        ['FINAGENT - KAMPANYA KARŞILAŞTIRMA MATRİSİ'],
        [`Tarih: ${today}`, `Karşılaştırılan Kampanya Sayısı: ${matrixData.value.length}`],
        [],
        headers
      ]

      if (hasAnyValidRow(c => c.genel_bilgi?.kampanya_turu)) {
        rows.push(['Kampanya Türü', ...matrixData.value.map(c => c.genel_bilgi?.kampanya_turu || '-')])
      }
      if (hasAnyValidRow(c => c.finansman_detay?.kar_payi_orani)) {
        rows.push(['Kâr Payı (%)', ...matrixData.value.map(c => c.finansman_detay?.kar_payi_orani ? `%${c.finansman_detay.kar_payi_orani}` : '-')])
      }
      if (hasAnyValidRow(c => c.finansman_detay?.vade_ay)) {
        rows.push(['Vade (Ay)', ...matrixData.value.map(c => c.finansman_detay?.vade_ay ? `${c.finansman_detay.vade_ay} Ay` : '-')])
      }
      if (hasAnyValidRow(c => c.finansman_detay?.taksit)) {
        rows.push(['Taksit', ...matrixData.value.map(c => c.finansman_detay?.taksit || '-')])
      }
      if (hasAnyValidRow(c => c.finansman_detay?.tahsis_ucreti)) {
        rows.push(['Tahsis Ücreti (TL)', ...matrixData.value.map(c => c.finansman_detay?.tahsis_ucreti ? `${Number(c.finansman_detay.tahsis_ucreti).toLocaleString('tr-TR')} TL` : '-')])
      }
      if (hasAnyValidRow(c => c.promosyon_detay?.odul_tutari)) {
        rows.push(['Ödül (TL)', ...matrixData.value.map(c => c.promosyon_detay?.odul_tutari ? `${Number(c.promosyon_detay.odul_tutari).toLocaleString('tr-TR')} TL` : '-')])
      }
      if (hasAnyValidRow(c => c.mgm_detay?.kisi_basi_kazanc || c.mgm_detay?.davet_eden_odul)) {
        rows.push(['MGM / Davet Ödülü', ...matrixData.value.map(c => c.mgm_detay?.kisi_basi_kazanc || c.mgm_detay?.davet_eden_odul ? `${Number(c.mgm_detay.kisi_basi_kazanc || c.mgm_detay.davet_eden_odul).toLocaleString('tr-TR')} TL` : '-')])
      }
      if (hasAnyValidRow(c => c.genel_bilgi?.hedef_kitle)) {
        rows.push(['Hedef Kitle', ...matrixData.value.map(c => Array.isArray(c.genel_bilgi?.hedef_kitle) ? c.genel_bilgi.hedef_kitle.join(', ') : (c.genel_bilgi?.hedef_kitle || '-'))])
      }

      const ws = XLSX.utils.aoa_to_sheet(rows)
      ws['!cols'] = [{ wch: 25 }, ...matrixData.value.map(() => ({ wch: 40 }))]
      XLSX.utils.book_append_sheet(wb, ws, 'Karsilastirma_Matrisi')
      XLSX.writeFile(wb, `FinAgent_Karsilastirma_Matrisi_${Date.now()}.xlsx`)
    } catch (e) {
      console.error('Excel export hatası:', e)
    }
  } else if (format === 'pdf') {
    try {
      await betigiYukle('https://cdnjs.cloudflare.com/ajax/libs/html2pdf.js/0.10.1/html2pdf.bundle.min.js', 'html2pdf')

      let html = `
        <div style="font-family: 'Segoe UI', Arial, sans-serif; color: #171717; background-color: #ffffff; padding: 25px; max-width: 850px; margin: 0 auto;">
            <!-- ÜST BAŞLIK -->
            <div style="border-bottom: 2px solid #2563eb; padding-bottom: 12px; margin-bottom: 20px;">
                <h1 style="color: #2563eb; margin: 0; font-size: 24px; font-weight: bold;">FinAgent Kampanya Karşılaştırma Matrisi</h1>
                <p style="color: #6b7280; font-size: 12px; margin: 5px 0 0 0;">Oluşturulma Tarihi: ${escapeHtml(today)}</p>
            </div>

            <table style="width: 100%; border-collapse: collapse; font-size: 11px; margin-top: 15px;">
                <thead>
                    <tr style="background-color: #f3f4f6;">
                        <th style="padding: 8px 10px; border: 1px solid #d1d5db; text-align: left; color: #1f2937; width: 140px;">Özellik</th>
                        ${matrixData.value.map(c => `
                          <th style="padding: 8px 10px; border: 1px solid #d1d5db; text-align: center; color: #1e40af;">
                              <div style="font-size: 9.5px; color: #6b7280;">${escapeHtml(getBankaAd(c.genel_bilgi?.banka_id))}</div>
                              <div style="font-weight: bold;">${escapeHtml(c.genel_bilgi?.kampanya_adi || c.baslik)}</div>
                          </th>
                        `).join('')}
                    </tr>
                </thead>
                <tbody>`

      if (hasAnyValidRow(c => c.genel_bilgi?.kampanya_turu)) {
        html += `<tr><td style="padding: 7px 10px; border: 1px solid #d1d5db; font-weight: bold; background: #f9fafb;">Kampanya Türü</td>${matrixData.value.map(c => `<td style="padding: 7px 10px; border: 1px solid #d1d5db; text-align: center;">${escapeHtml(c.genel_bilgi?.kampanya_turu || '-')}</td>`).join('')}</tr>`
      }
      if (hasAnyValidRow(c => c.finansman_detay?.kar_payi_orani)) {
        html += `<tr><td style="padding: 7px 10px; border: 1px solid #d1d5db; font-weight: bold; background: #f9fafb;">Kâr Payı</td>${matrixData.value.map(c => `<td style="padding: 7px 10px; border: 1px solid #d1d5db; text-align: center; font-weight: bold; color: #2563eb;">${c.finansman_detay?.kar_payi_orani ? `%${c.finansman_detay.kar_payi_orani}` : '-'}</td>`).join('')}</tr>`
      }
      if (hasAnyValidRow(c => c.finansman_detay?.vade_ay)) {
        html += `<tr><td style="padding: 7px 10px; border: 1px solid #d1d5db; font-weight: bold; background: #f9fafb;">Vade</td>${matrixData.value.map(c => `<td style="padding: 7px 10px; border: 1px solid #d1d5db; text-align: center;">${c.finansman_detay?.vade_ay ? `${c.finansman_detay.vade_ay} Ay` : '-'}</td>`).join('')}</tr>`
      }
      if (hasAnyValidRow(c => c.finansman_detay?.taksit)) {
        html += `<tr><td style="padding: 7px 10px; border: 1px solid #d1d5db; font-weight: bold; background: #f9fafb;">Taksit</td>${matrixData.value.map(c => `<td style="padding: 7px 10px; border: 1px solid #d1d5db; text-align: center;">${escapeHtml(c.finansman_detay?.taksit || '-')}</td>`).join('')}</tr>`
      }
      if (hasAnyValidRow(c => c.finansman_detay?.tahsis_ucreti)) {
        html += `<tr><td style="padding: 7px 10px; border: 1px solid #d1d5db; font-weight: bold; background: #f9fafb;">Tahsis Ücreti</td>${matrixData.value.map(c => `<td style="padding: 7px 10px; border: 1px solid #d1d5db; text-align: center; color: #ea580c; font-weight: bold;">${c.finansman_detay?.tahsis_ucreti ? `${Number(c.finansman_detay.tahsis_ucreti).toLocaleString('tr-TR')} TL` : '-'}</td>`).join('')}</tr>`
      }
      if (hasAnyValidRow(c => c.promosyon_detay?.odul_tutari)) {
        html += `<tr><td style="padding: 7px 10px; border: 1px solid #d1d5db; font-weight: bold; background: #f9fafb;">Ödül</td>${matrixData.value.map(c => `<td style="padding: 7px 10px; border: 1px solid #d1d5db; text-align: center; color: #059669; font-weight: bold;">${c.promosyon_detay?.odul_tutari ? `${Number(c.promosyon_detay.odul_tutari).toLocaleString('tr-TR')} TL` : '-'}</td>`).join('')}</tr>`
      }
      if (hasAnyValidRow(c => c.mgm_detay?.kisi_basi_kazanc || c.mgm_detay?.davet_eden_odul)) {
        html += `<tr><td style="padding: 7px 10px; border: 1px solid #d1d5db; font-weight: bold; background: #f9fafb;">MGM / Davet</td>${matrixData.value.map(c => `<td style="padding: 7px 10px; border: 1px solid #d1d5db; text-align: center; color: #d97706; font-weight: bold;">${c.mgm_detay?.kisi_basi_kazanc || c.mgm_detay?.davet_eden_odul ? `${Number(c.mgm_detay.kisi_basi_kazanc || c.mgm_detay.davet_eden_odul).toLocaleString('tr-TR')} TL` : '-'}</td>`).join('')}</tr>`
      }
      if (hasAnyValidRow(c => c.genel_bilgi?.hedef_kitle)) {
        html += `<tr><td style="padding: 7px 10px; border: 1px solid #d1d5db; font-weight: bold; background: #f9fafb;">Hedef Kitle</td>${matrixData.value.map(c => `<td style="padding: 7px 10px; border: 1px solid #d1d5db; text-align: center;">${escapeHtml(Array.isArray(c.genel_bilgi?.hedef_kitle) ? c.genel_bilgi.hedef_kitle.join(', ') : (c.genel_bilgi?.hedef_kitle || '-'))}</td>`).join('')}</tr>`
      }

      html += `</tbody></table>
            <div style="margin-top: 30px; padding-top: 10px; border-top: 1px solid #e5e7eb; text-align: center; font-size: 11px; color: #9ca3af;">
                Bu rapor, FinAgent Yapay Zeka platformu tarafından otomatik olarak oluşturulmuştur.
            </div>
        </div>`

      const tempDiv = document.createElement('div')
      tempDiv.innerHTML = html

      await window.html2pdf().set({
          margin:       0.4,
          filename:     `FinAgent_Karsilastirma_Matrisi_${Date.now()}.pdf`,
          image:        { type: 'jpeg', quality: 0.98 },
          html2canvas:  { scale: 2, backgroundColor: '#ffffff', useCORS: true },
          jsPDF:        { unit: 'in', format: 'a4', orientation: 'portrait' },
          pagebreak:    { mode: ['avoid-all', 'css', 'legacy'] },
      }).from(tempDiv).save()
    } catch (e) {
      console.error('PDF export hatası:', e)
    }
  } else if (format === 'png') {
    try {
      await betigiYukle('https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js', 'html2canvas')
      const el = document.getElementById('comparison-matrix-table')
      if (!el) return

      const canvas = await window.html2canvas(el, {
        scale: 2.5,
        backgroundColor: '#ffffff',
        useCORS: true,
        logging: false
      })

      const dataUrl = canvas.toDataURL('image/png', 1.0)
      const link = document.createElement('a')
      link.download = `FinAgent_Karsilastirma_Matrisi_${Date.now()}.png`
      link.href = dataUrl
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
    } catch (e) {
      console.error('PNG export hatası:', e)
    }
  }
}

// Click outside to close dropdown
if (process.client) {
  document.addEventListener('click', (e) => {
    const isInput = e.target.closest('input[type="text"]')
    const isDropdown = e.target.closest('.absolute.top-full')
    if (!isInput && !isDropdown) {
      showDropdown.value = false
    }
  })
}

let lenis = null
let lenisRafId = null
let observer = null

// --- DİNAMİK KRİTER YAPILANDIRMASI ---
const criteriaConfig = [
  {
    id: 'lowest_profit',
    title: 'En Düşük Kâr Payı Oranı',
    sortKey: 'karPayi',
    sortAsc: true,
    columns: [
      { key: 'banka', label: 'Banka' },
      { key: 'baslik', label: 'Kampanya' },
      { key: 'karPayi', label: 'Kâr Payı (%)' },
      { key: 'vade', label: 'Vade (ay)' },
      { key: 'hedefKitle', label: 'Hedef Kitle' }
    ]
  },
  {
    id: 'highest_reward',
    title: 'En Yüksek Ödül Miktarı',
    sortKey: 'odul',
    sortAsc: false,
    columns: [
      { key: 'banka', label: 'Banka' },
      { key: 'baslik', label: 'Kampanya' },
      { key: 'odul', label: 'Ödül (TL)' },
      { key: 'bitisTarihi', label: 'Bitiş Tarihi' },
      { key: 'hedefKitle', label: 'Hedef Kitle' }
    ]
  },
  {
    id: 'highest_mgm',
    title: 'En Yüksek MGM (Davet Et Kazan) Ödülü',
    sortKey: 'mgmKazanc',
    sortAsc: false,
    columns: [
      { key: 'banka', label: 'Banka' },
      { key: 'baslik', label: 'Kampanya' },
      { key: 'mgmKazanc', label: 'Kişi Başı / Davet Ödülü' },
      { key: 'mgmLimit', label: 'Toplam Kazanç Limiti' },
      { key: 'bitisTarihi', label: 'Bitiş Tarihi' },
      { key: 'hedefKitle', label: 'Hedef Kitle' }
    ]
  },
  {
    id: 'longest_term',
    title: 'En Uzun Vade',
    sortKey: 'vade',
    sortAsc: false,
    columns: [
      { key: 'banka', label: 'Banka' },
      { key: 'baslik', label: 'Kampanya' },
      { key: 'vade', label: 'Vade (ay)' },
      { key: 'karPayi', label: 'Kâr Payı (%)' },
      { key: 'hedefKitle', label: 'Hedef Kitle' }
    ]
  },
  {
    id: 'lowest_fee',
    title: 'En Düşük Tahsis Ücreti',
    sortKey: 'tahsisUcreti',
    sortAsc: true,
    columns: [
      { key: 'banka', label: 'Banka' },
      { key: 'baslik', label: 'Kampanya' },
      { key: 'tahsisUcreti', label: 'Tahsis Ücreti (TL)' },
      { key: 'karPayi', label: 'Kâr Payı (%)' },
      { key: 'vade', label: 'Vade (ay)' }
    ]
  }
]

const getMetricLabel = (key) => {
  const labels = {
    'karPayi': 'Kâr Payı (%)',
    'odul': 'Ödül (TL)',
    'vade': 'Vade (ay)',
    'tahsisUcreti': 'Tahsis Ücreti (TL)',
    'mgmKazanc': 'MGM Davet Ödülü',
    'mgmLimit': 'Toplam Kazanç Limiti'
  }
  return labels[key] || key
}

const formatTopMetric = (key, val) => {
  if (val === null || val === undefined) return '-'
  if (key === 'karPayi') return '%' + val
  if (key === 'vade') return val + ' Ay'
  if (key === 'odul' || key === 'mgmKazanc' || key === 'mgmLimit' || key === 'tahsisUcreti') {
    return Number(val).toLocaleString('tr-TR') + ' TL'
  }
  return val
}

const getSortedData = (criterion) => {
  const validData = campaigns.value.filter(c => {
    let val = c[criterion.sortKey]
    
    if (val === null || val === undefined || val === '' || String(val).trim().toLowerCase() === 'none') {
      return false
    }

    if (typeof val === 'string') {
        val = val.replace(',', '.')
    }

    const floatVal = parseFloat(val)
    if (isNaN(floatVal)) return false
    
    if ((criterion.sortKey === 'vade' || criterion.sortKey === 'odul' || criterion.sortKey === 'mgmKazanc' || criterion.sortKey === 'mgmLimit') && floatVal <= 0) {
      return false
    }

    if ((criterion.sortKey === 'karPayi' || criterion.sortKey === 'tahsisUcreti') && floatVal < 0) {
      return false
    }

    return true
  })
  
  const sorted = validData.sort((a, b) => {
    let valA = parseFloat(String(a[criterion.sortKey]).replace(',', '.')) || 0
    let valB = parseFloat(String(b[criterion.sortKey]).replace(',', '.')) || 0
    return criterion.sortAsc ? (valA - valB) : (valB - valA)
  })
  
  return sorted
}

const getTopItem = (criterion) => {
  const sorted = getSortedData(criterion)
  return sorted.length > 0 ? sorted[0] : {}
}

const setupObserver = (scrollerEl) => {
  observer = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        entry.target.classList.add('is-visible')
        observer.unobserve(entry.target)
      }
    })
  }, { root: scrollerEl || null, threshold: 0.12, rootMargin: '0px 0px -8% 0px' })

  document.querySelectorAll('.reveal-on-scroll').forEach(el => observer.observe(el))
}

const fetchBanks = async () => {
  try {
    const res = await fetch('http://localhost:8003/banks')
    if (res.ok) {
      banks.value = await res.json()
    }
  } catch (e) {
    console.warn('Bankalar yüklenemedi:', e)
  }
}

const fetchCampaigns = async () => {
  try {
    const response = await fetch('http://localhost:8003/campaigns?limit=500&sadece_gecerli=false')
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }
    
    const data = await response.json()
    
    campaigns.value = data.map(c => {
      const gb = c.genel_bilgi || {}
      const fd = c.finansman_detay || {}
      const pd = c.promosyon_detay || {}
      const mgm = c.mgm_detay || {}

      let mgmKazanc = null
      if (mgm.kisi_basi_kazanc) {
        mgmKazanc = mgm.kisi_basi_kazanc
      } else if (mgm.davet_eden_odul) {
        mgmKazanc = mgm.davet_eden_odul
      } else if (mgm.toplam_kazanc_limiti) {
        mgmKazanc = mgm.toplam_kazanc_limiti
      } else {
        const tur = (gb.kampanya_turu || '').toLowerCase()
        const adi = (gb.kampanya_adi || '').toLowerCase()
        if (tur.includes('mgm') || adi.includes('davet') || adi.includes('arkadaş') || adi.includes('getir') || mgm.is_mgm) {
          mgmKazanc = pd.odul_tutari || null
        }
      }

      let mgmLimit = mgm.toplam_kazanc_limiti || mgm.mgm_limit_tl || (mgmKazanc && pd.odul_tutari ? pd.odul_tutari : null)

      return {
        id: c._id || c.id,
        _id: c._id || c.id,
        banka: gb.banka_id || c.banka,
        baslik: gb.kampanya_adi || c.baslik,
        tur: gb.kampanya_turu || c.tur,
        karPayi: fd.kar_payi_orani || c.kar_payi_orani,
        vade: fd.vade_ay || c.vade_ay,
        taksit: fd.taksit || c.taksit,
        tahsisUcreti: fd.tahsis_ucreti || c.tahsis_ucreti,
        odul: pd.odul_tutari || c.odul_miktari,
        mgmKazanc: mgmKazanc,
        mgmLimit: mgmLimit,
        bitisTarihi: gb.bitis_tarihi || c.bitis_tarihi || '-',
        hedefKitle: Array.isArray(gb.hedef_kitle) ? gb.hedef_kitle.join(', ') : (gb.hedef_kitle || c.hedef_kitle),
        url: gb.kaynak_url || c.url,
        metin: gb.metin || c.metin || ''
      }
    })

  } catch (error) {
    console.error('Kampanya verileri çekilirken hata oluştu:', error)
    campaigns.value = []
  } finally {
    pending.value = false
    nextTick(() => {
      setupObserver(document.getElementById('main-scroller'))
    })
  }
}

onMounted(async () => {
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
})

onUnmounted(() => {
  if (lenisRafId) cancelAnimationFrame(lenisRafId)
  if (lenis) { lenis.destroy(); lenis = null }
  if (observer) { observer.disconnect(); observer = null }
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
@keyframes titleIn { from { opacity: 0; transform: translateY(16px); letter-spacing: 0.08em; } to { opacity: 1; transform: translateY(0); letter-spacing: 0; } }
.title-underline { animation: underlineGrow 0.9s ease 0.3s both; transform-origin: center; }
@keyframes underlineGrow { from { transform: scaleX(0); opacity: 1; } to { transform: scaleX(1); opacity: 1; } }

.reveal-on-scroll {
  opacity: 0;
  transform: translateY(28px);
  transition: opacity 0.6s cubic-bezier(0.22,1,0.36,1), transform 0.6s cubic-bezier(0.22,1,0.36,1);
}
.reveal-on-scroll.is-visible { opacity: 1; transform: none; }

.row-reveal {
  opacity: 0;
  transform: translateY(12px);
  transition: opacity 0.5s ease, transform 0.5s ease;
}
.reveal-on-scroll.is-visible .row-reveal { opacity: 1; transform: none; }

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
