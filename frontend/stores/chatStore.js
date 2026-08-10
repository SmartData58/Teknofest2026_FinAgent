// stores/chatStore.js
import { defineStore } from 'pinia'

export const useChatStore = defineStore('chat', {
  state: () => ({
    initialPrompt: '',
    initialFiles: []
  }),
  actions: {
    setChatData(prompt, files) {
      this.initialPrompt = prompt
      this.initialFiles = files
    },
    clearChatData() {
      this.initialPrompt = ''
      this.initialFiles = []
    }
  }
})