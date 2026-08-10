<script setup>
import { ref, onMounted, nextTick } from 'vue'
import DotMatrix from "~/components/loaders/DotMatrix.vue"

const mounted = ref(false)
const chatHistory = ref([])
const userMessage = ref('')
const isLoading = ref(false)
const isStreaming = ref(false)

// --- Kaynaklar ve Dosyalar İçin Box Modal (Drawer) State'leri ---
const showSourceModal = ref(false)
const activeSource = ref(null)
const activeFile = ref(null) 
const activeModalType = ref('source') // 'source' veya 'file'

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

const downloadFile = (file, event) => {
  event.stopPropagation() // Tıklamada panelin açılmasını engelle
  const a = document.createElement('a')
  a.href = file.url
  a.download = file.name
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
}

const useThinking = ref(false)
const fileInput = ref(null)
const selectedFiles = ref([])
const maxFiles = 3
const isDragging = ref(false)
const loadingText = ref('İşlem başlatılıyor...')

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
    alert(`En fazla ${maxFiles} dosya yükleyebilirsiniz.`)
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
    alert(`En fazla ${maxFiles} dosya yükleyebilirsiniz.`)
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

// 🚀 TOKAT 1: Yapay zekanın saçmaladığı "<span>" sızıntılarını kökünden temizliyoruz!
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
      
      // br ve madde işaretlerini güzelleştirme
      rowContent = rowContent.replace(/&lt;br\s*\/?[&gt;]?/gi, '<br class="mt-2 mb-1">');
      rowContent = rowContent.replace(/(?:&amp;)?(?:&gt;|gt;)\s*[\*•-]?/gi, '<br class="mt-2 mb-1"><span class="text-blue-500 font-bold mr-1.5">•</span>');
      
      // 🚀 YENİ: Modelin ürettiği <span ...> ve </span> gibi ucube yazıları tamamen sil!
      rowContent = rowContent.replace(/&lt;\/?span[^&]*&gt;/gi, '');

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
    // Dosyanın türüne göre (resim mi pdf mi) özel kontrol yapmak için
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

  let activeTasks = [];
  if (selectedFiles.value.length > 0) activeTasks.push("Belgeler analiz ediliyor");
  if (historyToSend.length > 0) activeTasks.push("Sohbet geçmişi taranıyor");
  if (useThinking.value) activeTasks.push("Derin düşünme uygulanıyor");
  
  loadingText.value = activeTasks.length > 0 
    ? activeTasks.join(" ➔ ") + "..." 
    : "Yapay zeka yanıtı hazırlıyor...";

  userMessage.value = ''
  
  isLoading.value = true 
  isStreaming.value = true

  clearFiles()
  scrollToBottom()

  let buffer = '';
  let assistantBubbleCreated = false;
  let assistantIndex = -1;

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
          loadingText.value = match[1]; 
      }
      buffer = buffer.replace(/\[STATUS\][\s\S]*?\[\/STATUS\]/g, '');

      let sourceRegex = /\[SOURCES\]([\s\S]*?)\[\/SOURCES\]/g;
      let matchSource;
      while ((matchSource = sourceRegex.exec(buffer)) !== null) {
          try {
              const parsedSources = JSON.parse(matchSource[1]);
              if (!assistantBubbleCreated) {
                  chatHistory.value.push({ role: 'assistant', content: '', sources: parsedSources })
                  assistantIndex = chatHistory.value.length - 1
                  assistantBubbleCreated = true
                  isLoading.value = false
              } else {
                  chatHistory.value[assistantIndex].sources = parsedSources;
                  scrollToBottom()
              }
          } catch(e) { console.error("Kaynak parse hatası", e) }
      }
      buffer = buffer.replace(/\[SOURCES\][\s\S]*?\[\/SOURCES\]/g, '');

      let partialSourceIndex = buffer.lastIndexOf('[SOURCES');
      if (partialSourceIndex !== -1 && buffer.indexOf('[/SOURCES]', partialSourceIndex) === -1) {
          continue;
      }

      let partialIndex = buffer.lastIndexOf('[STATUS');
      if (partialIndex !== -1 && buffer.indexOf('[/STATUS]', partialIndex) === -1) {
          continue; 
      }
      
      const possibleTags = ["[", "[S", "[ST", "[STA", "[STAT", "[STATUS", "[STATUS]"];
      if (possibleTags.some(tag => buffer.endsWith(tag)) && !assistantBubbleCreated) {
          continue; 
      }

      if (buffer.trim().length > 0 && !assistantBubbleCreated) {
        chatHistory.value.push({ role: 'assistant', content: '' })
        assistantIndex = chatHistory.value.length - 1
        isLoading.value = false 
        assistantBubbleCreated = true
      }

      if (assistantBubbleCreated && buffer.length > 0) {
        chatHistory.value[assistantIndex].content += buffer
        buffer = ''
        scrollToBottom()
      }
    }

  } catch (error) {
    console.error('Akış sırasında hata:', error)
    if (!assistantBubbleCreated) {
       chatHistory.value.push({ role: 'assistant', content: '' })
       assistantIndex = chatHistory.value.length - 1
       isLoading.value = false
    }
    chatHistory.value[assistantIndex].content = 'Üzgünüm, sunucuyla iletişim kurulamadı.'
  } finally {
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
                            <!-- Dosya İkonu -->
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
                    
                    <div 
                      class="whitespace-pre-wrap leading-relaxed text-[15px]" 
                      v-html="formatMessage(msg.content)">
                    </div>
                    
                    <Transition
                      enter-active-class="transition-all duration-500 delay-100 ease-out"
                      enter-from-class="opacity-0 translate-y-2"
                      enter-to-class="opacity-100 translate-y-0"
                    >
                      <div v-if="msg.sources && msg.sources.length > 0" class="mt-4 pt-3 border-t border-neutral-200 dark:border-neutral-700/50">
                        <p class="text-[11px] font-bold tracking-wider uppercase text-neutral-400 mb-2">Veritabanı Kaynakları</p>
                        <div class="flex flex-wrap gap-2">
                          <button v-for="src in msg.sources" :key="src.index" @click="openSourceModal(src)" 
                                  class="text-xs bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-400 px-3 py-1.5 rounded-lg border border-blue-200 dark:border-blue-800/50 hover:bg-blue-100 dark:hover:bg-blue-900/40 transition-colors flex items-center gap-1.5 group shadow-sm">
                            <svg class="w-3.5 h-3.5 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"></path></svg>
                            Kaynak [{{ src.index }}] 
                            <span class="text-blue-400 dark:text-blue-500 opacity-0 group-hover:opacity-100 transition-opacity">Göster &rarr;</span>
                          </button>
                        </div>
                      </div>
                    </Transition>
                  </div>
                </div>
              </div>
            </TransitionGroup>
            
            <Transition
              enter-active-class="transition-all duration-300 ease-out"
              enter-from-class="opacity-0 translate-y-4"
              enter-to-class="opacity-100 translate-y-0"
              leave-active-class="transition-all duration-200 ease-in"
              leave-from-class="opacity-100"
              leave-to-class="opacity-0"
            >
              <div v-if="isLoading" class="flex gap-4 w-full py-4 items-center">
                <div class="flex-shrink-0 w-8 h-8 flex items-center justify-center rounded-full bg-neutral-200 dark:bg-neutral-800 animate-pulse">
                   <svg class="w-4 h-4 text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"></path></svg>
                </div>
                <div class="flex items-center gap-3 bg-white dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 px-5 py-3 rounded-2xl shadow-sm">
                  <DotMatrix :size="3" :dot-size="8" :gap="2" color="#00eaff" :speed="1.2" />
                  <span class="text-sm text-neutral-500 font-medium animate-pulse">{{ loadingText }}</span>
                </div>
              </div>
            </Transition>
            
            <div ref="scrollAnchor" class="h-4 w-full"></div>
          </div>
        </div>

        <div class="w-full max-w-4xl mx-auto px-4 pb-4 pointer-events-auto relative z-20">
          
          <Transition
            enter-active-class="transition-all duration-300 cubic-bezier(0.4, 0, 0.2, 1)"
            enter-from-class="opacity-0 translate-y-2 scale-95"
            enter-to-class="opacity-100 translate-y-0 scale-100"
            leave-active-class="transition-all duration-200 cubic-bezier(0.4, 0, 0.2, 1)"
            leave-from-class="opacity-100 translate-y-0 scale-100"
            leave-to-class="opacity-0 translate-y-2 scale-95"
          >
            <div v-if="selectedFiles.length > 0" class="absolute bottom-full left-4 mb-2 flex items-center gap-2 max-w-[90%] overflow-x-auto custom-scrollbar pb-1 z-30">
              <div v-for="(file, index) in selectedFiles" :key="index" class="flex items-center gap-1.5 bg-white dark:bg-neutral-800 px-3 py-1.5 rounded-xl border border-neutral-200 dark:border-neutral-700 shadow-sm whitespace-nowrap">
                <svg class="w-3.5 h-3.5 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path></svg>
                <span class="text-[12px] font-medium text-neutral-600 dark:text-neutral-300 truncate max-w-[120px]">{{ file.name }}</span>
                <button @click.prevent="removeFile(index)" type="button" class="ml-0.5 p-0.5 text-neutral-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/30 rounded transition-colors">
                  <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg>
                </button>
              </div>
            </div>
          </Transition>

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

      <!-- ORTAK KAYAN PANEL (DRAWER) -->
      <Transition
        enter-active-class="transform transition-all duration-500 ease-[cubic-bezier(0.2,0.8,0.2,1)]"
        enter-from-class="translate-x-[120%] opacity-0 scale-95"
        enter-to-class="translate-x-0 opacity-100 scale-100"
        leave-active-class="transform transition-all duration-300 ease-in"
        leave-from-class="translate-x-0 opacity-100 scale-100"
        leave-to-class="translate-x-[120%] opacity-0 scale-95"
      >
        <div v-if="showSourceModal" class="absolute right-4 top-4 bottom-4 w-[340px] lg:w-[480px] bg-white dark:bg-neutral-900 rounded-[24px] shadow-[0_8px_30px_rgb(0,0,0,0.12)] border border-neutral-200 dark:border-neutral-800 flex flex-col z-50 overflow-hidden">
          
          <div class="flex justify-between items-center p-5 border-b border-neutral-100 dark:border-neutral-800 bg-neutral-50/50 dark:bg-neutral-900/50">
            <h3 class="text-[15px] font-bold flex items-center gap-2 text-neutral-800 dark:text-white">
              <svg v-if="activeModalType === 'source'" class="w-5 h-5 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4"></path></svg>
              <svg v-else class="w-5 h-5 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13"></path></svg>
              {{ activeModalType === 'source' ? 'Veritabanı Kaydı' : 'Dosya Önizleme' }}
            </h3>
            <div class="flex items-center gap-2">
              <span v-if="activeModalType === 'source'" class="text-[11px] font-bold tracking-wider text-blue-700 bg-blue-100 dark:bg-blue-900/50 dark:text-blue-300 px-2 py-1 rounded border border-blue-200 dark:border-blue-800/50">ID: {{ activeSource?.kampanya_id }}</span>
              <button @click="showSourceModal = false" class="p-1.5 text-neutral-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/30 rounded-lg transition-colors">
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg>
              </button>
            </div>
          </div>
          
          <!-- 🚀 TOKAT 2: Dosya önizleme kısmını tamamen kutuya hapsediyoruz! -->
          <div class="flex-1 overflow-hidden bg-neutral-50 dark:bg-[#121212] flex items-center justify-center">
            <template v-if="activeModalType === 'source'">
                <div class="w-full h-full overflow-y-auto p-5 custom-scrollbar">
                    <pre class="whitespace-pre-wrap text-[12.5px] font-mono leading-relaxed text-neutral-600 dark:text-neutral-300 p-4 rounded-xl border border-neutral-200 dark:border-neutral-800/80 bg-white dark:bg-neutral-900/50">{{ activeSource?.icerik }}</pre>
                </div>
            </template>
            <template v-else>
                <!-- Resimse resim etiketi, PDF ise iframe ile tam sığacak şekilde ayarladık -->
                <img v-if="activeFile?.isImage" :src="activeFile?.url" class="w-full h-full object-contain p-4" />
                <iframe v-else :src="activeFile?.url" class="w-full h-full border-none bg-white"></iframe>
            </template>
          </div>
          
          <div v-if="activeModalType === 'file'" class="p-4 border-t border-neutral-100 dark:border-neutral-800 bg-white dark:bg-neutral-900 flex justify-between items-center">
              <span class="text-xs font-medium text-neutral-500 truncate max-w-[200px]">{{ activeFile?.name }}</span>
              <button @click="downloadFile(activeFile, $event)" class="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-lg flex items-center gap-2 transition-colors">
                  <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"></path></svg>
                  İndir
              </button>
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
</style>