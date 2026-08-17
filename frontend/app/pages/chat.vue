<script setup>
import { ref, onMounted, nextTick } from 'vue'
import DotMatrix from "~/components/loaders/DotMatrix.vue"
import { useChatStore } from '~/stores/chatStore'

const mounted = ref(false)
const chatHistory = ref([])
const userMessage = ref('')
const isLoading = ref(false)
const isStreaming = ref(false)

const chatStore = useChatStore()

// --- Kaynaklar ve Dosyalar İçin Box Modal (Drawer) State'leri ---
const showSourceModal = ref(false)
const activeSource = ref(null)
const activeFile = ref(null) 
const activeModalType = ref('source') 

const toastMessage = ref('')
const showToast = (msg) => {
  toastMessage.value = msg
  setTimeout(() => {
    toastMessage.value = ''
  }, 3000)
}

const openSourceModal = (source) => {
  activeSource.value = source
  activeModalType.value = 'source'
  showSourceModal.value = true
}

const openFileModal = (file) => {
  activeFile.value = file
  activeModalType.value = 'file'
  showSourceModal.value = true
}

const openSourceFromChart = (sourceIndex, sources) => {
    if (!sourceIndex || !sources) return;
    const source = sources.find(s => s.index === sourceIndex);
    if (source) {
        openSourceModal(source);
    } else {
        showToast("Kaynak bulunamadı.");
    }
}

const downloadFile = (file, event) => {
  event.stopPropagation() 
  
  if (file.isReport) {
    const iframe = document.getElementById('report-iframe')
    if (iframe && iframe.contentWindow) {
      iframe.contentWindow.print()
    }
  } else {
    const a = document.createElement('a')
    a.href = file.url
    a.download = file.name
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
  }
}

const isExporting = ref({})
const isExportingExcel = ref({})

const exportToExcel = async (index) => {
  const originalElement = document.getElementById('message-content-' + index)
  let tablesArray = originalElement ? Array.from(originalElement.querySelectorAll('table')) : []
  
  if (chatHistory.value[index].chart) {
    const chart = chatHistory.value[index].chart
    const chartTable = document.createElement('table')
    let chartHtml = `<tr><th>Banka / Kurum</th><th>Kampanya Detayı</th><th>Değer</th></tr>`
    
    chart.labels.forEach((label, i) => {
      const camp = chart.sub_labels ? chart.sub_labels[i] : '-'
      const prefix = chart.prefix || '%'
      const suffix = chart.suffix || ''
      chartHtml += `<tr><td>${label}</td><td>${camp}</td><td>${prefix}${chart.values[i]}${suffix}</td></tr>`
    })
    
    if (chart.stats) {
      const prefix = chart.prefix || '%'
      const suffix = chart.suffix || ''
      chartHtml += `<tr><td>--</td><td>--</td><td>--</td></tr>`
      chartHtml += `<tr><td>Ortalama Değer</td><td>-</td><td>${prefix}${chart.stats.avg}${suffix}</td></tr>`
      chartHtml += `<tr><td>En Düşük Değer</td><td>-</td><td>${prefix}${chart.stats.min}${suffix}</td></tr>`
      chartHtml += `<tr><td>En Yüksek Değer</td><td>-</td><td>${prefix}${chart.stats.max}${suffix}</td></tr>`
    }
    
    chartTable.innerHTML = chartHtml
    tablesArray.push(chartTable)
  }

  if (tablesArray.length === 0) {
    showToast("Bu mesajda dışa aktarılacak veri veya tablo bulunamadı.")
    return
  }

  if (isExportingExcel.value[index]) return;
  isExportingExcel.value[index] = true;
  
  try {
      if (!window.XLSX) {
        const script = document.createElement('script')
        script.src = 'https://cdn.jsdelivr.net/npm/xlsx-js-style@1.2.0/dist/xlsx.bundle.js'
        document.head.appendChild(script)
        await new Promise(resolve => script.onload = resolve)
      }

      const wb = window.XLSX.utils.book_new()
      
      tablesArray.forEach((table, i) => {
        const clonedTable = table.cloneNode(true)
        
        let tableHtml = clonedTable.innerHTML;
        tableHtml = tableHtml.replace(/<\/?ins[^>]*>/gi, '');
        tableHtml = tableHtml.replace(/<\/?small[^>]*>/gi, '');
        tableHtml = tableHtml.replace(/<\/?span[^>]*>/gi, '');
        tableHtml = tableHtml.replace(/•\*/g, '•'); 
        clonedTable.innerHTML = tableHtml;

        let maxCols = 0;
        clonedTable.querySelectorAll('tr').forEach(tr => {
            if (tr.children.length > maxCols) maxCols = tr.children.length;
        });

        const emptyRow = document.createElement('tr');
        const emptyCell = document.createElement('td');
        emptyCell.colSpan = maxCols;
        emptyCell.innerText = "";
        emptyRow.appendChild(emptyCell);

        const footerRow = document.createElement('tr');
        const footerCell = document.createElement('td');
        footerCell.colSpan = maxCols;
        footerCell.innerText = "Bu rapor, SmartData takımı tarafından geliştirilen FinAgent Yapay Zeka asistanı tarafından otomatik olarak oluşturulmuştur.";
        footerRow.appendChild(footerCell);
        
        clonedTable.appendChild(emptyRow);
        clonedTable.appendChild(footerRow);

        const ws = window.XLSX.utils.table_to_sheet(clonedTable)

        const range = window.XLSX.utils.decode_range(ws['!ref'] || "A1:A1");
        let rowCount = range.e.r + 1;

        const json = window.XLSX.utils.sheet_to_json(ws, { header: 1 })
        const colWidths = []
        
        for (let r = 0; r < json.length; r++) {
          const row = json[r] || []
          for (let c = 0; c < maxCols; c++) {
            const cellValue = row[c] ? row[c].toString() : ""
            const lines = cellValue.split('\n')
            let maxLineLen = 10; 
            lines.forEach(l => { 
                if (l.length > maxLineLen) maxLineLen = l.length 
            })
            
            if (!colWidths[c]) colWidths[c] = 10;
            if (maxLineLen > colWidths[c]) {
               colWidths[c] = Math.min(maxLineLen + 2, 80); 
            }
          }
        }
        ws['!cols'] = colWidths.map(w => ({ wch: w }))

        if (!ws['!merges']) ws['!merges'] = [];
        ws['!merges'].push({
            s: { r: rowCount - 1, c: 0 }, 
            e: { r: rowCount - 1, c: maxCols - 1 } 
        });

        for (let R = 0; R < rowCount; R++) {
            for (let C = 0; C < maxCols; C++) {
                const cellRef = window.XLSX.utils.encode_cell({ c: C, r: R });
                if (!ws[cellRef]) ws[cellRef] = { t: 's', v: '' }; 
                
                const cell = ws[cellRef];
                cell.s = {
                    alignment: { wrapText: true, vertical: 'top' },
                    border: {
                        top: { style: 'thin', color: { rgb: "CBD5E1" } },
                        bottom: { style: 'thin', color: { rgb: "CBD5E1" } },
                        left: { style: 'thin', color: { rgb: "CBD5E1" } },
                        right: { style: 'thin', color: { rgb: "CBD5E1" } }
                    }
                };

                if (R === 0) {
                    cell.s.font = { bold: true, color: { rgb: "FFFFFF" } };
                    cell.s.fill = { fgColor: { rgb: "2563EB" } };
                    cell.s.alignment = { vertical: 'center', horizontal: 'center', wrapText: true };
                }
                
                if (R === rowCount - 2) cell.s = {}; 
                if (R === rowCount - 1) {
                    cell.s = { font: { italic: true, color: { rgb: "6B7280" } }, alignment: { vertical: 'center', horizontal: 'center' } };
                }
            }
        }

        window.XLSX.utils.book_append_sheet(wb, ws, "Tablo " + (i + 1))
      })

      const fileName = `FinAgent_Rapor_${new Date().getTime()}.xlsx`
      window.XLSX.writeFile(wb, fileName)

  } catch (err) {
      console.error("Excel oluşturulurken hata:", err)
      showToast("Excel oluşturulurken bir hata meydana geldi.")
  } finally {
      isExportingExcel.value[index] = false;
  }
}

const exportToPDF = async (index) => {
  if (isExporting.value[index]) return;
  isExporting.value[index] = true;
  
  try {
      const originalElement = document.getElementById('message-content-' + index)
      
      let rawHtml = originalElement ? originalElement.innerHTML.replace(/class="[^"]*"/g, '') : ''
      rawHtml = rawHtml.replace(/&lt;\/?span[^&]*&gt;/gi, '');
      rawHtml = rawHtml.replace(/&lt;\/?small[^&]*&gt;/gi, '');

      if (chatHistory.value[index].chart) {
          const chart = chatHistory.value[index].chart
          const maxVal = chart.stats ? chart.stats.max : Math.max(...chart.values)
          const prefix = chart.prefix || '%'
          const suffix = chart.suffix || ''

          let chartHtml = `
          <div style="margin-top: 25px; border: 1px solid #e5e7eb; border-radius: 12px; padding: 20px; background-color: #f8fafc; page-break-inside: avoid;">
              <h3 style="margin-top: 0; margin-bottom: 5px; color: #1e40af; font-size: 16px;">${chart.title || 'Pazar Analizi'}</h3>
              <p style="margin-top: 0; margin-bottom: 20px; color: #6b7280; font-size: 11px;">${chart.subtitle || 'Bankalar Arası Veri Kıyaslaması'}</p>
          `

          if (chart.stats) {
              chartHtml += `
              <div style="display: flex; gap: 15px; margin-bottom: 25px;">
                  <div style="flex: 1; padding: 12px; border: 1px solid #bfdbfe; border-radius: 8px; background-color: #fff; text-align: center;">
                      <span style="display: block; font-size: 10px; color: #3b82f6; font-weight: 700; margin-bottom: 4px;">ORTALAMA</span>
                      <span style="font-size: 16px; font-weight: 900; color: #1e3a8a;">${prefix}${chart.stats.avg}${suffix}</span>
                  </div>
                  <div style="flex: 1; padding: 12px; border: 1px solid #bbf7d0; border-radius: 8px; background-color: #fff; text-align: center;">
                      <span style="display: block; font-size: 10px; color: #22c55e; font-weight: 700; margin-bottom: 4px;">EN DÜŞÜK</span>
                      <span style="font-size: 16px; font-weight: 900; color: #14532d;">${prefix}${chart.stats.min}${suffix}</span>
                  </div>
                  <div style="flex: 1; padding: 12px; border: 1px solid #fecaca; border-radius: 8px; background-color: #fff; text-align: center;">
                      <span style="display: block; font-size: 10px; color: #ef4444; font-weight: 700; margin-bottom: 4px;">EN YÜKSEK</span>
                      <span style="font-size: 16px; font-weight: 900; color: #7f1d1d;">${prefix}${chart.stats.max}${suffix}</span>
                  </div>
              </div>
              `
          }

          chart.labels.forEach((label, i) => {
              const val = chart.values[i]
              const widthPct = (val / maxVal) * 100
              const barColor = (chart.stats && val === chart.stats.min) ? '#22c55e' : '#3b82f6'
              const subLabel = chart.sub_labels ? chart.sub_labels[i] : ''

              chartHtml += `
              <div style="margin-bottom: 15px;">
                  <div style="display: flex; justify-content: space-between; margin-bottom: 6px;">
                      <strong style="font-size: 12px; color: #374151;">${label} <span style="font-size: 10px; color: #9ca3af; font-weight: normal; margin-left: 6px;">${subLabel}</span></strong>
                      <strong style="font-size: 12px; color: ${barColor};">${prefix}${val}${suffix}</strong>
                  </div>
                  <div style="width: 100%; height: 14px; background-color: #e5e7eb; border-radius: 7px; overflow: hidden;">
                      <div style="width: ${widthPct}%; height: 100%; background-color: ${barColor}; border-radius: 7px;"></div>
                  </div>
              </div>
              `
          })

          chartHtml += `</div>`
          rawHtml += chartHtml
      }

      if (!rawHtml.trim()) {
          showToast("Raporlanacak içerik bulunamadı.");
          return;
      }

      const currentDate = new Date().toLocaleDateString('tr-TR', { year: 'numeric', month: 'long', day: 'numeric' });

      const fullHtmlString = `
        <!DOCTYPE html>
        <html>
        <head>
          <title>FinAgent_Rapor</title>
          <style>
            @page { size: A4 portrait; margin: 0; }
            * { box-sizing: border-box; }
            body { 
              font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; 
              color: #1f2937; padding: 15mm; margin: 0; line-height: 1.5; font-size: 11px; background-color: #fff; 
              -webkit-print-color-adjust: exact; 
              print-color-adjust: exact; 
            }
            .report-header {
              display: flex;
              justify-content: space-between;
              align-items: flex-end;
              border-bottom: 2px solid #2563eb;
              padding-bottom: 10px;
              margin-bottom: 15px;
            }
            .report-header .brand { font-size: 22px; font-weight: 800; color: #2563eb; letter-spacing: -0.5px; margin: 0; }
            .report-header .brand span { color: #6b7280; font-weight: 400; font-size: 16px; }
            .report-header .meta { text-align: right; font-size: 10px; color: #6b7280; }
            .report-header .meta strong { display: block; color: #111827; font-size: 11px; margin-top: 2px; }
            h1, h2, h3 { color: #111827; margin-top: 15px; margin-bottom: 8px; }
            h1 { font-size: 16px; }
            h2 { font-size: 14px; border-bottom: 1px solid #e5e7eb; padding-bottom: 4px; }
            h3 { font-size: 12px; color: #2563eb; }
            table { width: 100%; border-collapse: collapse; margin-bottom: 15px; table-layout: fixed; }
            tr { page-break-inside: avoid; }
            th, td { border: 1px solid #e5e7eb; padding: 6px 8px; text-align: left; vertical-align: top; word-wrap: break-word; font-size: 10px; }
            th { background-color: #f8fafc; font-weight: 600; color: #111827; }
            tbody tr:nth-child(even) { background-color: #f9fafb; }
            p, li { margin-bottom: 5px; font-size: 11px; }
            ul { margin-left: 15px; margin-bottom: 12px; }
            pre { background-color: #f1f5f9; padding: 10px; border-radius: 6px; font-size: 9px; white-space: pre-wrap; word-wrap: break-word; border: 1px solid #e2e8f0; }
            strong { font-weight: 600; color: #000; }
            .report-footer {
              position: fixed;
              bottom: 10mm;
              left: 15mm;
              right: 15mm;
              border-top: 1px solid #e5e7eb;
              padding-top: 8px;
              font-size: 9px;
              color: #9ca3af;
              text-align: center;
              background-color: #fff;
              z-index: 10;
            }
            .report-content { padding-bottom: 15mm; }
          </style>
        </head>
        <body>
          <div class="report-footer">
            Bu rapor, SmartData takımı tarafından geliştirilen FinAgent Yapay Zeka asistanı tarafından otomatik olarak oluşturulmuştur.
          </div>
          <div class="report-header">
            <div class="brand">FinAgent <span>Raporu</span></div>
            <div class="meta">
              <div>Oluşturulma Tarihi</div>
              <strong>${currentDate}</strong>
            </div>
          </div>
          <div class="report-content">
            ${rawHtml}
          </div>
        </body>
        </html>
      `;

      const fileName = `FinAgent_Rapor_${new Date().getTime()}.pdf`

      activeFile.value = {
        name: fileName,
        isReport: true, 
        htmlContent: fullHtmlString
      }
      activeModalType.value = 'file'
      showSourceModal.value = true

  } catch (err) {
      console.error("Rapor oluşturulurken hata:", err)
      showToast("Rapor oluşturulurken bir hata meydana geldi.")
  } finally {
      isExporting.value[index] = false;
  }
}

const generateConicGradient = (chart) => {
    if (!chart || !chart.values) return '';
    const total = chart.values.reduce((a, b) => a + b, 0);
    const colors = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#06b6d4'];
    let gradientParts = [];
    let currentDegree = 0;
    
    chart.values.forEach((val, index) => {
        const degree = (val / total) * 360;
        const color = colors[index % colors.length];
        gradientParts.push(`${color} ${currentDegree}deg ${currentDegree + degree}deg`);
        currentDegree += degree;
    });
    
    return `conic-gradient(${gradientParts.join(', ')})`;
}

const getChartColor = (index) => {
    const colors = ['bg-blue-500', 'bg-green-500', 'bg-amber-500', 'bg-red-500', 'bg-purple-500', 'bg-pink-500', 'bg-cyan-500'];
    return colors[index % colors.length];
}

const fileInput = ref(null)
const selectedFiles = ref([])
const maxFiles = 3
const isDragging = ref(false)
const useThinking = ref(false)

const chatContainer = ref(null)
const scrollAnchor = ref(null) 

onMounted(() => {
  requestAnimationFrame(() => { mounted.value = true })

  const sharedPrompt = useState('sharedPrompt', () => '')
  const sharedFiles = useState('sharedFiles', () => [])

  if (sharedPrompt.value || sharedFiles.value.length > 0) {
    userMessage.value = sharedPrompt.value
    selectedFiles.value = [...sharedFiles.value]

    sharedPrompt.value = ''
    sharedFiles.value = []

    setTimeout(() => {
      sendMessage()
    }, 500)
  }
})

const goHome = () => navigateTo('/')
const triggerFileInput = () => fileInput.value.click()

const handleFileSelect = (event) => {
  const files = Array.from(event.target.files)
  if (selectedFiles.value.length + files.length > maxFiles) {
    showToast(`En fazla ${maxFiles} dosya yükleyebilirsiniz.`)
    event.target.value = '' 
    return
  }
  selectedFiles.value.push(...files)
  event.target.value = '' 
}

const handleDrop = (event) => {
  isDragging.value = false
  const files = Array.from(event.dataTransfer.files)
  if (selectedFiles.value.length + files.length > maxFiles) {
    showToast(`En fazla ${maxFiles} dosya yükleyebilirsiniz.`)
    return
  }
  selectedFiles.value.push(...files)
}

const removeFile = (index) => {
  selectedFiles.value.splice(index, 1)
  if (selectedFiles.value.length === 0 && fileInput.value) fileInput.value.value = ''
}

const clearFiles = () => {
  selectedFiles.value = []
  if (fileInput.value) fileInput.value.value = ''
}

const scrollToBottom = () => {
  nextTick(() => {
    if (scrollAnchor.value) {
      scrollAnchor.value.scrollIntoView({ behavior: 'auto', block: 'end' })
    }
  })
}

// 🚀 TOKAT: Gelen kelimeye göre animasyonu/ikonu otomatik seçen asistan
const determineIcon = (text) => {
    if (!text) return 'robot';
    const lower = text.toLowerCase();
    if (lower.includes('mongo') || lower.includes('veritabanı') || lower.includes('redis') || lower.includes('cache')) return 'database';
    if (lower.includes('qdrant') || lower.includes('vektör') || lower.includes('taranıyor')) return 'search';
    if (lower.includes('rerank') || lower.includes('optimize')) return 'sort';
    if (lower.includes('dosya') || lower.includes('belge') || lower.includes('işlem')) return 'file';
    if (lower.includes('düşünme')) return 'brain';
    return 'robot';
}

const formatMessage = (text) => {
  if (!text) return '';
  let html = text.trim().replace(/</g, '&lt;').replace(/>/g, '&gt;');
  html = html.replace(/\n{3,}/g, '\n\n');
  
  html = html.replace(/(?:^[ \t]*\|.*(?:\n|$))+/gm, (match) => {
    const lines = match.trim().split('\n');
    if (lines.length === 0) return match; 
    
    let tableHtml = '<div class="overflow-x-auto my-6 shadow-sm rounded-xl border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-800/80 transition-all duration-300"><table class="w-full text-sm text-left border-collapse">';
    let isBody = false;
    
    lines.forEach((line, index) => {
      if (line.match(/^[ \t]*\|[\s\-\.:]+\|/)) {
        isBody = true;
        return;
      }
      
      let rowContent = line.replace(/^[ \t]*\||\|[ \t]*$/g, ''); 
      rowContent = rowContent.replace(/&lt;br\s*\/?[&gt;]?/gi, '<br class="mt-2 mb-1">');
      rowContent = rowContent.replace(/(?:&amp;)?(?:&gt;|gt;)\s*[\*•-]?/gi, '<br class="mt-2 mb-1"><span class="text-blue-500 font-bold mr-1.5">•</span>');
      rowContent = rowContent.replace(/&lt;\/?span[^&]*&gt;/gi, '');
      rowContent = rowContent.replace(/&lt;\/?small[^&]*&gt;/gi, '');
      rowContent = rowContent.replace(/&lt;\/?ins[^&]*&gt;/gi, '');

      const cells = rowContent.split('|');
      tableHtml += '<tr class="border-b border-neutral-200 dark:border-neutral-700 hover:bg-neutral-50 dark:hover:bg-neutral-800/40 transition-colors">';
      
      cells.forEach(cell => {
        if (!isBody && index === 0) { 
          tableHtml += `<th class="px-5 py-4 bg-neutral-100/80 dark:bg-neutral-800/90 font-bold text-neutral-800 dark:text-neutral-200 border-r border-neutral-200 dark:border-neutral-700 last:border-0 align-top">${cell.trim()}</th>`;
        } else { 
          tableHtml += `<td class="px-5 py-4 text-neutral-600 dark:text-neutral-300 border-r border-neutral-200 dark:border-neutral-700 last:border-0 align-top leading-relaxed">${cell.trim()}</td>`;
        }
      });
      tableHtml += '</tr>';
    });
    
    tableHtml += '</table></div>\n';
    return tableHtml;
  });
  
  html = html
    .replace(/```[a-zA-Z]*\n?([\s\S]*?)```/g, '<pre class="bg-neutral-800 text-neutral-100 p-4 rounded-xl my-3 overflow-x-auto text-sm font-mono shadow-inner border border-neutral-700"><code>$1</code></pre>')
    .replace(/`([^`\n]+)`/g, '<code class="bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 px-1 py-0.5 rounded text-sm font-mono">$1</code>')
    .replace(/^#### (.*$)/gm, '<h4 class="text-base font-bold mt-4 mb-1 text-neutral-800 dark:text-neutral-200">$1</h4>')
    .replace(/^### (.*$)/gm, '<h3 class="text-lg font-bold mt-4 mb-1.5 text-blue-600 dark:text-blue-400">$1</h3>')
    .replace(/^## (.*$)/gm, '<h2 class="text-xl font-bold mt-5 mb-2 text-neutral-900 dark:text-white border-b border-neutral-200 dark:border-neutral-700 pb-1">$1</h2>')
    .replace(/^# (.*$)/gm, '<h1 class="text-2xl font-bold mt-5 mb-2 text-blue-600 dark:text-blue-400">$1</h1>')
    .replace(/\*\*(.*?)\*\*/g, '<strong class="font-bold text-neutral-900 dark:text-white">$1</strong>')
    .replace(/\b_(.*?)_\b/g, '<em class="italic text-neutral-700 dark:text-neutral-300">$1</em>')
    .replace(/^\s*[\-\*]\s+(.*$)/gm, '<li class="ml-5 list-disc marker:text-blue-500 mb-0.5">$1</li>')
    .replace(/^>\s+(.*$)/gm, '<blockquote class="border-l-4 border-blue-500 pl-4 my-2 text-neutral-600 dark:text-neutral-400 italic bg-blue-50 dark:bg-blue-900/10 py-2 rounded-r-lg">$1</blockquote>');
    
  html = html.replace(/(<\/h[1-4]>|<\/li>|<\/blockquote>|<\/pre>|<\/div>)\n+/g, '$1\n');
  html = html.replace(/\n+(<h[1-4]|<li|<blockquote|<pre|<div class="overflow-x-auto)/g, '\n$1');
  
  html = html.replace(/&lt;br\s*\/?[&gt;]/gi, '<br>');
  
  return html;
}

const sendMessage = async () => {
  if (!userMessage.value.trim() && selectedFiles.value.length === 0) return

  const text = userMessage.value || `${selectedFiles.value.length} dosya gönderildi.`
  const attachedFiles = selectedFiles.value.map(f => ({
    name: f.name,
    type: f.type,
    isImage: f.type.startsWith('image/'),
    url: URL.createObjectURL(f) 
  }))
  
  chatHistory.value.push({ role: 'user', content: text, files: attachedFiles })
  
  const historyToSend = chatHistory.value.slice(0, -1).map(msg => ({
    role: msg.role,
    content: msg.content
  }))

  const formData = new FormData()
  formData.append('prompt', text)
  formData.append('model', 'qwen3.5:4b') 
  formData.append('thinking', useThinking.value)
  formData.append('history', JSON.stringify(historyToSend))
  selectedFiles.value.forEach(file => formData.append('files', file))

  // 🚀 TOKAT: Asistan balonunu SIFIRDAN ve anında oluşturup State objelerini atıyoruz
  chatHistory.value.push({
    role: 'assistant',
    content: '',
    sources: null,
    chart: null,
    statuses: [], 
    currentStatus: null,
    activeTimer: '0.0',
    isStatusExpanded: false,
    isFinished: false
  });
  const aIdx = chatHistory.value.length - 1;

  let activeTasks = [];
  if (selectedFiles.value.length > 0) activeTasks.push("Belgeler analiz ediliyor");
  if (historyToSend.length > 0) activeTasks.push("Sohbet geçmişi taranıyor");
  if (useThinking.value) activeTasks.push("Derin düşünme uygulanıyor");

  userMessage.value = ''
  isLoading.value = true 
  isStreaming.value = true
  clearFiles()
  scrollToBottom()

  // Saniye Sayacı (Real-time timer)
  let statusInterval = null;
  const startTimer = () => {
      clearInterval(statusInterval);
      chatHistory.value[aIdx].activeTimer = '0.0';
      statusInterval = setInterval(() => {
          const cur = chatHistory.value[aIdx].currentStatus;
          if (cur) {
              chatHistory.value[aIdx].activeTimer = ((performance.now() - cur.startTime) / 1000).toFixed(1);
          }
      }, 100);
  };

  const updateStatus = (statusText) => {
      const now = performance.now();
      const cur = chatHistory.value[aIdx].currentStatus;
      if (cur) { // Önceki durumu kapat ve listeye ekle
          cur.endTime = now;
          cur.duration = ((now - cur.startTime) / 1000).toFixed(1);
          chatHistory.value[aIdx].statuses.push({...cur});
      }
      // Yeni durumu başlat
      chatHistory.value[aIdx].currentStatus = {
          text: statusText,
          startTime: now,
          endTime: null,
          duration: '0.0',
          icon: determineIcon(statusText)
      };
      startTimer();
  };

  const finishStatus = () => {
      const now = performance.now();
      const cur = chatHistory.value[aIdx].currentStatus;
      if (cur) {
          cur.endTime = now;
          cur.duration = ((now - cur.startTime) / 1000).toFixed(1);
          chatHistory.value[aIdx].statuses.push({...cur});
          chatHistory.value[aIdx].currentStatus = null;
      }
      chatHistory.value[aIdx].isFinished = true;
      clearInterval(statusInterval);
  };

  // İlk tetiklemeyi yapıyoruz
  if (activeTasks.length > 0) {
      updateStatus(activeTasks.join(" ➔ ") + " başlatılıyor...");
  } else {
      updateStatus("İşlem başlatılıyor...");
  }

  let buffer = '';

  try {
    const response = await fetch('http://localhost:8003/api/chat', {
      method: 'POST',
      body: formData
    })

    if (!response.body) throw new Error('Akış başlatılamadı.')

    const reader = response.body.getReader()
    const decoder = new TextDecoder()

    while (true) {
      const { value, done } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })

      let statusRegex = /\[STATUS\]([\s\S]*?)\[\/STATUS\]/g;
      let match;
      while ((match = statusRegex.exec(buffer)) !== null) {
          updateStatus(match[1]); // Her yeni status için güncelle
      }
      buffer = buffer.replace(/\[STATUS\][\s\S]*?\[\/STATUS\]/g, '');

      let sourceRegex = /\[SOURCES\]([\s\S]*?)\[\/SOURCES\]/g;
      let matchSource;
      while ((matchSource = sourceRegex.exec(buffer)) !== null) {
          try {
              chatHistory.value[aIdx].sources = JSON.parse(matchSource[1]);
              scrollToBottom()
          } catch(e) { console.error("Kaynak parse hatası", e) }
      }
      buffer = buffer.replace(/\[SOURCES\][\s\S]*?\[\/SOURCES\]/g, '');

      let chartRegex = /\[CHART\]([\s\S]*?)\[\/CHART\]/g;
      let matchChart;
      while ((matchChart = chartRegex.exec(buffer)) !== null) {
          try {
              chatHistory.value[aIdx].chart = JSON.parse(matchChart[1]);
              scrollToBottom()
          } catch(e) { console.error("Grafik Parse Hatası", e) }
      }
      buffer = buffer.replace(/\[CHART\][\s\S]*?\[\/CHART\]/g, '');

      let partialSourceIndex = buffer.lastIndexOf('[SOURCES');
      if (partialSourceIndex !== -1 && buffer.indexOf('[/SOURCES]', partialSourceIndex) === -1) {
          continue;
      }
      
      let partialChartIndex = buffer.lastIndexOf('[CHART');
      if (partialChartIndex !== -1 && buffer.indexOf('[/CHART]', partialChartIndex) === -1) {
          continue;
      }

      let partialIndex = buffer.lastIndexOf('[STATUS');
      if (partialIndex !== -1 && buffer.indexOf('[/STATUS]', partialIndex) === -1) {
          continue; 
      }
      
      const possibleTags = ["[", "[S", "[ST", "[STA", "[STAT", "[STATUS", "[STATUS]", "[C", "[CH", "[CHA", "[CHAR", "[CHART", "[CHART]"];
      if (possibleTags.some(tag => buffer.endsWith(tag))) {
          continue; 
      }

      if (buffer.length > 0) {
        // İçerik akmaya başladığı an, loading akordeonunu yeşil tike geçirip sayacı bitir
        if (!chatHistory.value[aIdx].isFinished) {
            finishStatus();
        }
        chatHistory.value[aIdx].content += buffer
        buffer = ''
        scrollToBottom()
      }
    }

  } catch (error) {
    console.error('Akış sırasında hata:', error)
    chatHistory.value[aIdx].content = 'Üzgünüm, sunucuyla iletişim kurulamadı.'
  } finally {
    finishStatus(); // Hata olsa bile kapat
    isLoading.value = false
    isStreaming.value = false 
    scrollToBottom()
  }
}
</script>

<template>
  <div 
    class="relative w-full h-screen flex flex-col transition-colors duration-500 ease-in-out bg-neutral-50 dark:bg-neutral-900 overflow-hidden"
    @dragover.prevent="isDragging = true"
    @dragleave.prevent="isDragging = false"
    @drop.prevent="handleDrop"
  >

    <Transition
      enter-active-class="transition duration-300 ease-out"
      enter-from-class="opacity-0 -translate-y-4"
      enter-to-class="opacity-100 translate-y-0"
      leave-active-class="transition duration-200 ease-in"
      leave-from-class="opacity-100 translate-y-0"
      leave-to-class="opacity-0 -translate-y-4"
    >
      <div v-if="toastMessage" class="fixed top-10 left-1/2 -translate-x-1/2 z-[200] bg-neutral-800 text-white px-6 py-3 rounded-full shadow-2xl flex items-center gap-3">
        <svg class="w-5 h-5 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
        <span class="text-sm font-medium">{{ toastMessage }}</span>
      </div>
    </Transition>

    <Transition
      enter-active-class="transition duration-300 ease-out"
      enter-from-class="opacity-0 scale-95"
      enter-to-class="opacity-100 scale-100"
      leave-active-class="transition duration-200 ease-in"
      leave-from-class="opacity-100 scale-100"
      leave-to-class="opacity-0 scale-95"
    >
      <div v-if="isDragging" class="absolute inset-0 z-[100] flex items-center justify-center border-4 border-dashed border-blue-500/50 m-4 rounded-3xl pointer-events-none bg-white/40 dark:bg-black/40 backdrop-blur-sm">
        <div class="bg-white dark:bg-neutral-800 px-10 py-6 rounded-2xl shadow-2xl flex flex-col items-center gap-4 animate-bounce">
          <svg class="w-12 h-12 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12"></path></svg>
          <span class="text-xl font-bold text-neutral-800 dark:text-neutral-100">Dosyaları buraya bırakın</span>
        </div>
      </div>
    </Transition>

    <div class="flex-1 w-full relative flex overflow-hidden">
      
      <div 
        class="flex-1 h-full flex flex-col transition-all duration-500 ease-[cubic-bezier(0.4,0,0.2,1)]"
        :class="showSourceModal ? 'lg:pr-[380px] lg:mr-[10px]' : 'pr-0'"
      >
        <div 
          ref="chatContainer"
          class="flex-1 overflow-y-auto px-4 py-6 custom-scrollbar"
        >
          <div class="max-w-4xl mx-auto w-full flex flex-col space-y-6 pb-4" :class="mounted ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-10'">
            
            <Transition
              enter-active-class="transition duration-700 ease-out"
              enter-from-class="opacity-0 scale-95"
              enter-to-class="opacity-100 scale-100"
              leave-active-class="transition duration-300 ease-in absolute w-full"
              leave-from-class="opacity-100"
              leave-to-class="opacity-0"
            >
              <div v-if="chatHistory.length === 0" class="flex items-center justify-center text-center h-[50vh]">
                <h2 class="text-3xl md:text-4xl font-bold text-neutral-800 dark:text-neutral-100 tracking-tight">
                  Neye odaklanalım?
                </h2>
              </div>
            </Transition>
            
            <TransitionGroup 
              enter-active-class="transition-all duration-500 ease-out-back"
              enter-from-class="opacity-0 translate-y-8 scale-95"
              enter-to-class="opacity-100 translate-y-0 scale-100"
            >
              <div v-for="(msg, index) in chatHistory" :key="index" class="w-full">
                
                <div v-if="msg.role === 'user'" class="flex justify-end w-full">
                  <div class="bg-blue-600 text-white rounded-t-2xl rounded-bl-2xl rounded-br-sm px-5 py-3.5 max-w-[85%] shadow-sm text-left leading-relaxed flex flex-col group">
                    
                    <div v-if="msg.files && msg.files.length > 0" class="flex flex-wrap gap-2 mb-3">
                      <div v-for="(file, fIndex) in msg.files" :key="fIndex" 
                           @click="openFileModal(file)"
                           class="flex items-center justify-between gap-3 p-1.5 pl-3 pr-2 bg-black/20 hover:bg-black/30 rounded-lg text-sm font-medium cursor-pointer transition-colors w-full sm:w-auto"
                           title="Dosyayı önizle">
                        <div class="flex items-center gap-1.5 overflow-hidden">
                            <svg class="w-4 h-4 text-white flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13"></path></svg>
                            <span class="truncate max-w-[150px] md:max-w-[200px]">{{ file.name }}</span>
                        </div>
                        
                        <button @click="downloadFile(file, $event)" class="p-1.5 rounded bg-white/10 hover:bg-white/30 transition-colors flex-shrink-0" title="İndir">
                           <svg class="w-3.5 h-3.5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"></path></svg>
                        </button>
                      </div>
                    </div>

                    <span class="whitespace-pre-wrap">{{ msg.content }}</span>
                  </div>
                </div>

                <div v-else class="flex gap-4 w-full text-neutral-800 dark:text-neutral-100 py-4">
                  <div class="mt-1 flex-shrink-0 w-8 h-8 flex items-center justify-center rounded-full bg-gradient-to-br from-blue-500 to-cyan-500 text-white shadow-md">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"></path></svg>
                  </div>
                  
                  <div class="flex-1 overflow-x-auto max-w-full">

                    <!-- 🚀 YENİ SİSTEM: DİNAMİK MİNİ ANİMASYONLU AŞAMA (HISTORY) AKORDEONU -->
                    <div v-if="msg.statuses?.length > 0 || msg.currentStatus" class="mb-4 max-w-lg">
                        <div class="bg-white dark:bg-neutral-800/80 border border-neutral-200 dark:border-neutral-700/60 rounded-2xl shadow-sm w-full overflow-hidden transition-all duration-300">
                            
                            <!-- Geçmiş Aşamalar -->
                            <div v-show="msg.isStatusExpanded && msg.statuses?.length > 0" class="flex flex-col border-b border-neutral-100 dark:border-neutral-700/50 bg-neutral-50/50 dark:bg-neutral-900/30 max-h-48 overflow-y-auto custom-scrollbar">
                                <div v-for="(stat, idx) in msg.statuses" :key="idx" class="flex items-center justify-between px-4 py-2 border-b border-neutral-100 dark:border-neutral-700/50 last:border-0">
                                    <div class="flex items-center gap-3 text-neutral-500 dark:text-neutral-400">
                                        <svg class="w-3.5 h-3.5 text-emerald-500" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path></svg>
                                        <span class="text-[13px]">{{ stat.text }}</span>
                                    </div>
                                    <span class="text-[11px] font-mono text-neutral-400">{{ stat.duration }}s</span>
                                </div>
                            </div>

                            <!-- Başlık / Şu Anki Durum -->
                            <div class="flex items-center justify-between px-4 py-2.5 cursor-pointer hover:bg-neutral-50 dark:hover:bg-neutral-700/40 transition-colors" @click="msg.isStatusExpanded = !msg.isStatusExpanded">
                                
                                <!-- Eğer işlem devam ediyorsa, tipine göre küçük animasyon göster -->
                                <div class="flex items-center gap-3 flex-1" v-if="msg.currentStatus">
                                    <div class="w-5 h-5 flex items-center justify-center shrink-0">
                                        <svg v-if="msg.currentStatus.icon === 'database'" class="w-4 h-4 text-blue-500 animate-pulse" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4"></path></svg>
                                        <svg v-else-if="msg.currentStatus.icon === 'search'" class="w-4 h-4 text-purple-500 animate-[spin_3s_linear_infinite]" fill="none" viewBox="0 0 24 24" stroke="currentColor"><circle cx="11" cy="11" r="8" stroke-width="2"></circle><line x1="21" y1="21" x2="16.65" y2="16.65" stroke-width="2"></line></svg>
                                        <svg v-else-if="msg.currentStatus.icon === 'sort'" class="w-4 h-4 text-amber-500 animate-pulse" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h7"></path></svg>
                                        <svg v-else-if="msg.currentStatus.icon === 'file'" class="w-4 h-4 text-emerald-500 animate-pulse" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z"></path></svg>
                                        <svg v-else-if="msg.currentStatus.icon === 'brain'" class="w-4 h-4 text-pink-500 animate-pulse" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"></path></svg>
                                        <DotMatrix v-else :size="2" :dot-size="4" :gap="2" color="#3b82f6" :speed="1.2" />
                                    </div>
                                    <span class="text-[13px] font-medium text-neutral-800 dark:text-neutral-200 truncate">{{ msg.currentStatus.text }}</span>
                                </div>
                                
                                <!-- Eğer işlem tamamen bittiyse (Yazı gelmeye başladıysa) -->
                                <div class="flex items-center gap-3 flex-1" v-else-if="msg.isFinished && msg.statuses?.length > 0">
                                    <svg class="w-4 h-4 text-emerald-500" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
                                    <span class="text-[13px] font-medium text-neutral-800 dark:text-neutral-200">İşlem tamamlandı ({{ (msg.statuses.reduce((acc, s) => acc + parseFloat(s.duration), 0)).toFixed(1) }}s)</span>
                                </div>

                                <!-- Sağ taraf (Süre ve Akordeon Açma Tuşu) -->
                                <div class="flex items-center gap-2 pl-3">
                                    <span v-if="msg.currentStatus" class="text-[11px] font-mono text-neutral-400 w-6 text-right">{{ msg.activeTimer }}s</span>
                                    
                                    <!-- İstediğin özel dizayn: Koyu/Açık Tema hap tuş ve içindeki 'ok' tasarımı -->
                                    <div class="bg-neutral-200 dark:bg-[#1e1e1e] border border-neutral-300 dark:border-[#2a2a2a] w-8 h-5 rounded-[10px] flex items-center justify-center transition-transform duration-300" :class="{'rotate-180': msg.isStatusExpanded}">
                                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" class="text-neutral-500 dark:text-[#a3a3a3]" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"></polyline></svg>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <div 
                      :id="'message-content-' + index"
                      class="whitespace-pre-wrap leading-relaxed text-[15px]" 
                      v-html="formatMessage(msg.content)">
                    </div>

                    <Transition enter-active-class="transition-all duration-700 ease-out" enter-from-class="opacity-0 scale-95 translate-y-4" enter-to-class="opacity-100 scale-100 translate-y-0">
                        <div v-if="msg.chart" class="mt-6 bg-white dark:bg-neutral-800/90 rounded-2xl border border-neutral-200 dark:border-neutral-700 shadow-md overflow-hidden">
                            <div class="p-5 sm:p-6 border-b border-neutral-100 dark:border-neutral-700/50 flex flex-col sm:flex-row justify-between gap-4 items-start sm:items-center bg-neutral-50/50 dark:bg-neutral-800/50">
                                <div class="flex items-center gap-3">
                                    <div class="flex items-center justify-center w-10 h-10 rounded-xl bg-blue-600 text-white shadow-sm">
                                        <svg v-if="msg.chart.type === 'doughnut'" class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 3.055A9.001 9.001 0 1020.945 13H11V3.055z"></path><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20.488 9H15V3.512A9.025 9.025 0 0120.488 9z"></path></svg>
                                        <svg v-else class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"></path></svg>
                                    </div>
                                    <div>
                                        <h4 class="text-base sm:text-lg font-bold text-neutral-800 dark:text-neutral-100">{{ msg.chart.title || 'Pazar Analizi' }}</h4>
                                        <p class="text-xs text-neutral-500 mt-0.5">{{ msg.chart.subtitle || 'Bankalar Arası Veri Kıyaslaması' }}</p>
                                    </div>
                                </div>
                                
                                <div v-if="msg.chart.stats" class="flex flex-wrap items-center gap-2 sm:gap-3 w-full sm:w-auto">
                                    <div class="flex-1 sm:flex-none bg-white dark:bg-neutral-800 px-4 py-2.5 rounded-xl border border-blue-100 dark:border-blue-900/50 shadow-sm text-center">
                                        <span class="block text-[9px] text-blue-500 font-bold uppercase tracking-wider mb-0.5">Ortalama Değer</span>
                                        <span class="text-sm sm:text-lg font-black text-neutral-800 dark:text-neutral-100">{{ msg.chart.prefix || '' }}{{ msg.chart.stats.avg }}{{ msg.chart.suffix || '' }}</span>
                                    </div>
                                    <div class="flex-1 sm:flex-none bg-white dark:bg-neutral-800 px-4 py-2.5 rounded-xl border border-green-100 dark:border-green-900/50 shadow-sm text-center relative overflow-hidden">
                                        <div class="absolute top-0 right-0 w-8 h-8 bg-green-500/10 rounded-bl-full"></div>
                                        <span class="block text-[9px] text-green-500 font-bold uppercase tracking-wider mb-0.5">En Düşük</span>
                                        <span class="text-sm sm:text-lg font-black text-green-600 dark:text-green-400">{{ msg.chart.prefix || '' }}{{ msg.chart.stats.min }}{{ msg.chart.suffix || '' }}</span>
                                    </div>
                                    <div class="flex-1 sm:flex-none bg-white dark:bg-neutral-800 px-4 py-2.5 rounded-xl border border-red-100 dark:border-red-900/50 shadow-sm text-center relative overflow-hidden">
                                        <div class="absolute top-0 right-0 w-8 h-8 bg-red-500/10 rounded-bl-full"></div>
                                        <span class="block text-[9px] text-red-500 font-bold uppercase tracking-wider mb-0.5">En Yüksek</span>
                                        <span class="text-sm sm:text-lg font-black text-red-600 dark:text-red-400">{{ msg.chart.prefix || '' }}{{ msg.chart.stats.max }}{{ msg.chart.suffix || '' }}</span>
                                    </div>
                                </div>
                            </div>
                            
                            <div class="p-5 sm:p-6 space-y-8">
                                <div class="flex flex-col sm:flex-row items-center justify-center gap-8 pb-8 border-b border-neutral-100 dark:border-neutral-700/50">
                                    <div class="relative w-48 h-48 sm:w-56 sm:h-56 shrink-0 flex items-center justify-center">
                                        <div class="absolute inset-0 rounded-full shadow-lg transition-transform duration-1000" :style="{ background: generateConicGradient(msg.chart) }"></div>
                                        <div class="absolute inset-4 bg-white dark:bg-neutral-800 rounded-full flex items-center justify-center shadow-inner">
                                            <div class="text-center">
                                                <span class="block text-xs font-bold text-neutral-400">Ortalama</span>
                                                <span class="text-xl font-black text-neutral-800 dark:text-white">{{ msg.chart.prefix || '' }}{{ msg.chart.stats?.avg }}{{ msg.chart.suffix || '' }}</span>
                                            </div>
                                        </div>
                                    </div>
                                    <div class="flex flex-col gap-2.5 w-full sm:w-auto max-h-56 overflow-y-auto custom-scrollbar pr-3">
                                        <div v-for="(label, i) in msg.chart.labels" :key="'pie-'+i" class="flex items-center gap-3">
                                            <div class="w-3 h-3 rounded-full shrink-0" :class="getChartColor(i)"></div>
                                            <div class="flex flex-col flex-1">
                                                <div class="flex justify-between items-center gap-4">
                                                    <span class="text-[13px] font-bold text-neutral-700 dark:text-neutral-200 truncate max-w-[130px]">{{ label }}</span>
                                                    <span class="text-[13px] font-black text-neutral-900 dark:text-white">{{ msg.chart.prefix || '' }}{{ msg.chart.values[i] }}{{ msg.chart.suffix || '' }}</span>
                                                </div>
                                                <span class="text-[9px] text-neutral-400 truncate max-w-[150px]">{{ msg.chart.sub_labels ? msg.chart.sub_labels[i] : '' }}</span>
                                            </div>
                                        </div>
                                    </div>
                                </div>

                                <div class="space-y-5 pt-2">
                                    <h4 class="text-sm font-bold text-neutral-800 dark:text-neutral-200 mb-4 flex items-center gap-2">
                                        <svg class="w-4 h-4 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 10h16M4 14h16M4 18h16"></path></svg>
                                        Detaylı Kampanya Kıyaslaması
                                    </h4>
                                    <div v-for="(label, i) in msg.chart.labels" :key="'bar-'+i" class="relative group">
                                        <div class="flex justify-between items-end mb-2.5">
                                            <div class="flex flex-col">
                                                <button 
                                                    v-if="msg.chart.source_indices && msg.chart.source_indices[i]"
                                                    @click="openSourceFromChart(msg.chart.source_indices[i], msg.sources)"
                                                    class="text-sm font-bold text-neutral-700 dark:text-neutral-300 flex items-center gap-1.5 hover:text-blue-600 dark:hover:text-blue-400 transition-colors group-hover:underline decoration-blue-400 decoration-2 underline-offset-4"
                                                    title="Veri kaynağını görüntüle">
                                                    {{ label }}
                                                    <svg class="w-3.5 h-3.5 text-blue-500 opacity-0 group-hover:opacity-100 transition-opacity" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"></path></svg>
                                                </button>
                                                <span v-else class="text-sm font-bold text-neutral-700 dark:text-neutral-300">{{ label }}</span>
                                                
                                                <span class="text-[11px] text-neutral-400 font-medium truncate max-w-[200px] sm:max-w-[300px]">{{ msg.chart.sub_labels ? msg.chart.sub_labels[i] : '' }}</span>
                                            </div>
                                            
                                            <span class="text-xs font-black text-blue-700 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/30 border border-blue-100 dark:border-blue-800/50 px-2.5 py-1 rounded-md shadow-sm transition-transform group-hover:scale-105">{{ msg.chart.prefix || '' }}{{ msg.chart.values[i] }}{{ msg.chart.suffix || '' }}</span>
                                        </div>
                                        <div class="h-3.5 sm:h-4 bg-neutral-100 dark:bg-neutral-900/60 rounded-full overflow-hidden shadow-inner relative">
                                            <div class="h-full transition-all duration-1000 ease-out relative rounded-full"
                                                    :class="msg.chart.stats && msg.chart.values[i] === msg.chart.stats.min ? 'bg-gradient-to-r from-green-500 via-green-400 to-emerald-400' : 'bg-gradient-to-r from-blue-600 via-blue-500 to-cyan-400'"
                                                    :style="{ width: (msg.chart.values[i] / (msg.chart.stats ? msg.chart.stats.max : Math.max(...msg.chart.values)) * 100) + '%' }">
                                                    <div class="absolute inset-0 bg-white/20 transform -translate-x-full group-hover:animate-[sheen_1.5s_ease-in-out_infinite]"></div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </Transition>
                    
                    <div class="mt-4 pt-4 border-t border-neutral-200 dark:border-neutral-700/50 flex flex-col gap-4">
                      <div class="flex items-center justify-end gap-2">
                        <button 
                          v-if="msg.content.trim() !== '' || msg.chart"
                          :disabled="isExportingExcel[index] || (isStreaming && index === chatHistory.length - 1)"
                          @click="exportToExcel(index)" 
                          class="text-xs flex items-center gap-1.5 text-green-700 dark:text-green-400 hover:text-green-800 dark:hover:text-green-300 transition-colors px-3 py-1.5 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800/50 rounded-lg shadow-sm hover:bg-green-100 dark:hover:bg-green-900/40 active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                          <template v-if="!isExportingExcel[index]">
                            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 10h18M3 14h18m-9-4v8m-7 0h14a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"></path></svg>
                            Excel İndir
                          </template>
                          <template v-else>
                            <svg class="animate-spin w-4 h-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>
                            Oluşturuluyor...
                          </template>
                        </button>

                        <button 
                          v-if="msg.content.trim() !== '' || msg.chart"
                          :disabled="isExporting[index] || (isStreaming && index === chatHistory.length - 1)"
                          @click="exportToPDF(index)" 
                          class="text-xs flex items-center gap-1.5 text-neutral-600 dark:text-neutral-300 hover:text-blue-600 dark:hover:text-blue-400 transition-colors px-3 py-1.5 bg-white dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 rounded-lg shadow-sm hover:shadow active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                          <template v-if="!isExporting[index]">
                            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path></svg>
                            Raporu Görüntüle
                          </template>
                          <template v-else>
                            <svg class="animate-spin w-4 h-4 text-blue-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>
                            Oluşturuluyor...
                          </template>
                        </button>
                      </div>

                      <div class="flex-1 w-full">
                        <Transition
                          enter-active-class="transition-all duration-500 delay-100 ease-out"
                          enter-from-class="opacity-0 translate-y-2"
                          enter-to-class="opacity-100 translate-y-0"
                        >
                          <div v-if="msg.sources && msg.sources.length > 0" class="w-full">
                              <details class="group bg-neutral-50 dark:bg-neutral-800/50 rounded-xl border border-neutral-200 dark:border-neutral-700/80 overflow-hidden shadow-sm w-full">
                                  <summary class="flex justify-between items-center font-medium cursor-pointer list-none px-4 py-3 text-sm text-neutral-700 dark:text-neutral-200 hover:bg-neutral-100 dark:hover:bg-neutral-800 transition-colors">
                                      <div class="flex items-center gap-2.5">
                                          <svg class="w-4 h-4 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"></path></svg>
                                          <span class="font-bold tracking-wide">SQL Veritabanı ile Güçlendirildi (Tıklayın)</span>
                                      </div>
                                      <span class="transition-transform duration-300 group-open:rotate-180 bg-white dark:bg-neutral-700 rounded-full p-1 shadow-sm border border-neutral-200 dark:border-neutral-600">
                                          <svg class="w-4 h-4 text-neutral-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"></path></svg>
                                      </span>
                                  </summary>
                                  <div class="p-4 bg-white dark:bg-neutral-900 border-t border-neutral-200 dark:border-neutral-700/80">
                                      <div class="text-xs text-neutral-500 dark:text-neutral-400 mb-2">Bu veriler yapılandırılmış SQL veritabanından hatasız olarak çekilmiştir.</div>
                                  </div>
                              </details>
                          </div>
                        </Transition>
                      </div>

                    </div>
                  </div>
                </div>
              </div>
            </TransitionGroup>
            
            <div ref="scrollAnchor" class="h-4 w-full"></div>
          </div>
        </div>

        <div class="w-full max-w-4xl mx-auto px-4 pb-4 pointer-events-auto relative z-20">
          <form @submit.prevent="sendMessage" class="flex flex-col w-full bg-white dark:bg-neutral-800 p-2 rounded-2xl border border-neutral-200 dark:border-neutral-700 shadow-sm transition-shadow focus-within:shadow-md focus-within:border-blue-300 dark:focus-within:border-blue-700">
            <div class="flex items-center justify-end px-3 py-1 border-b border-neutral-100 dark:border-neutral-700/50 mb-1">
               <label class="flex items-center cursor-pointer gap-2 group">
                 <span class="text-[11px] font-bold tracking-wider uppercase text-neutral-400 group-hover:text-blue-500 transition-colors">DÜŞÜNME</span>
                 <div class="relative">
                   <input type="checkbox" v-model="useThinking" class="sr-only" :disabled="isStreaming">
                   <div class="block w-8 h-5 rounded-full transition-colors" :class="useThinking ? 'bg-blue-500' : 'bg-neutral-300 dark:bg-neutral-600'"></div>
                   <div class="dot absolute left-1 top-1 bg-white w-3 h-3 rounded-full transition-transform" :class="useThinking ? 'transform translate-x-3' : ''"></div>
                 </div>
               </label>
            </div>

            <div class="flex gap-2 items-center">
              <input type="file" multiple ref="fileInput" class="hidden" @change="handleFileSelect" accept=".pdf, image/*, .xls, .xlsx, .doc, .docx, .ppt, .pptx" />
              <button type="button" @click="triggerFileInput" :disabled="isStreaming" class="p-3 text-neutral-400 hover:text-blue-500 transition-all rounded-xl hover:bg-neutral-100 dark:hover:bg-neutral-700 active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed">
                <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13"></path></svg>
              </button>
              <input v-model="userMessage" type="text" placeholder="Bir şeyler sorun veya dosya bırakın..." class="flex-1 bg-transparent px-2 py-3 text-neutral-900 dark:text-white outline-none placeholder:text-neutral-400 transition-all text-sm sm:text-base disabled:opacity-50" :disabled="isStreaming" />
              <button type="submit" :disabled="isStreaming || (!userMessage.trim() && selectedFiles.length === 0)" class="px-5 py-3 bg-blue-600 text-white rounded-xl hover:bg-blue-700 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center group active:scale-95">
                <svg class="w-5 h-5 transform group-hover:translate-x-1 group-hover:-translate-y-1 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"></path></svg>
              </button>
            </div>
          </form>
        </div>
      </div>

      <Transition enter-active-class="transform transition-all duration-500 ease-[cubic-bezier(0.2,0.8,0.2,1)]" enter-from-class="translate-x-[120%] opacity-0 scale-95" enter-to-class="translate-x-0 opacity-100 scale-100" leave-active-class="transform transition-all duration-300 ease-in" leave-from-class="translate-x-0 opacity-100 scale-100" leave-to-class="translate-x-[120%] opacity-0 scale-95">
        <div v-if="showSourceModal" class="absolute right-4 top-4 bottom-4 w-[340px] lg:w-[480px] bg-white dark:bg-neutral-900 rounded-[24px] shadow-[0_8px_30px_rgb(0,0,0,0.12)] border border-neutral-200 dark:border-neutral-800 flex flex-col z-50 overflow-hidden">
          
          <div class="flex justify-between items-center p-5 border-b border-neutral-100 dark:border-neutral-800 bg-neutral-50/50 dark:bg-neutral-900/50">
            <h3 class="text-[15px] font-bold flex items-center gap-2 text-neutral-800 dark:text-white">
              <svg class="w-5 h-5 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4"></path></svg>
              Veritabanı Kaydı
            </h3>
            <div class="flex items-center gap-2">
              <button @click="showSourceModal = false" class="p-1.5 text-neutral-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/30 rounded-lg transition-colors">
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg>
              </button>
            </div>
          </div>
          
          <div class="flex-1 overflow-hidden bg-neutral-50 dark:bg-[#121212] flex items-center justify-center relative">
                <div class="w-full h-full overflow-y-auto p-5 custom-scrollbar">
                    <pre class="whitespace-pre-wrap text-[12.5px] font-mono leading-relaxed text-neutral-600 dark:text-neutral-300 p-4 rounded-xl border border-neutral-200 dark:border-neutral-800/80 bg-white dark:bg-neutral-900/50">SQL Veritabanı (finagent.sqlite) bağlantısı sağlandı. Kampanya verileri doğrudan tablo üzerinden işlenmektedir.</pre>
                </div>
          </div>
        </div>
      </Transition>

    </div>
  </div>
</template>

<style scoped>
.ease-out-back {
  transition-timing-function: cubic-bezier(0.34, 1.56, 0.64, 1);
}

.custom-scrollbar::-webkit-scrollbar {
  width: 6px;
}
.custom-scrollbar::-webkit-scrollbar-track {
  background: transparent;
}
.custom-scrollbar::-webkit-scrollbar-thumb {
  background-color: #cbd5e1;
  border-radius: 20px;
}
.dark .custom-scrollbar::-webkit-scrollbar-thumb {
  background-color: #404040;
}

@keyframes sheen { 0% { transform: translateX(-100%); } 100% { transform: translateX(100%); } }
</style>