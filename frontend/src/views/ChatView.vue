<script setup lang="ts">
import { ref, onMounted, nextTick, computed } from 'vue'
import { Send, Loader2, FileText, Database, Plus, Bot, Sparkles, Trash2 } from 'lucide-vue-next'
import { marked } from 'marked'
import { api, type KnowledgeBase, type SourceReference } from '@/api/client'
import { useLanguageStore } from '@/stores/language'
import Card from '@/components/ui/Card.vue'
import Button from '@/components/ui/Button.vue'
import Select from '@/components/ui/Select.vue'

const languageStore = useLanguageStore()
const messagesContainer = ref<HTMLElement | null>(null)

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  sources?: SourceReference[]
  isComplete?: boolean
}

const messages = ref<Message[]>([])
const input = ref('')
const isLoading = ref(false)
const selectedKb = ref<string>('')
const knowledgeBases = ref<KnowledgeBase[]>([])
const pendingContent = ref('')
const inputRef = ref<HTMLTextAreaElement | null>(null)
const currentSessionId = ref<string>('')

function adjustTextareaHeight() {
  if (inputRef.value) {
    inputRef.value.style.height = 'auto'
    const newHeight = Math.min(inputRef.value.scrollHeight, 150)
    inputRef.value.style.height = newHeight + 'px'
  }
}

marked.setOptions({
  breaks: true,
  gfm: true
})

function renderMarkdown(content: string): string {
  try {
    return marked(content) as string
  } catch {
    return content
  }
}

function updateMessageContent(index: number, content: string) {
  messages.value[index].content = content
}

function resetInputHeight() {
  if (inputRef.value) {
    inputRef.value.style.height = 'auto'
  }
}

onMounted(async () => {
  await loadKnowledgeBases()
  await loadSessionHistory()
})

// Load session history from backend
async function loadSessionHistory() {
  const savedSessionId = localStorage.getItem('ragdocman_current_session')
  if (savedSessionId) {
    try {
      const res = await api.getSessionHistory(savedSessionId)
      if (res.success && res.data && res.data.messages) {
        // Convert backend history to messages
        for (const msg of res.data.messages) {
          messages.value.push({
            id: `${Date.now()}_${Math.random()}`,
            role: msg.role as 'user' | 'assistant',
            content: msg.content,
            isComplete: true
          })
        }
        // Update session_id for continuing the conversation
        currentSessionId.value = savedSessionId
      }
    } catch (error) {
      console.error('Failed to load session history:', error)
    }
  }
}

async function loadKnowledgeBases() {
  const res = await api.getKnowledgeBases()
  if (res.success && res.data) {
    knowledgeBases.value = res.data
    if (res.data.length > 0 && !selectedKb.value) {
      selectedKb.value = res.data[0].id
    }
  }
}

const kbOptions = computed(() => {
  return knowledgeBases.value.map(kb => ({
    value: kb.id,
    label: kb.name
  }))
})

function scrollToBottom() {
  nextTick(() => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
    }
  })
}

// Detect knowledge base management commands
function detectKbCommand(query: string): { action: string; name?: string; id?: string } | null {
  const q = query.trim()

  // Create knowledge base patterns
  if (/^(创建|创建一个|新建)(.*?)(知识库|知识库|kb)/i.test(q)) {
    const match = q.match(/(?:创建|创建一个|新建)(?:一个)?(?:名为|叫)?(.+?)(?:的)?(?:知识库|kb)/i)
    if (match && match[1]) {
      const name = match[1].trim()
      return { action: 'create', name }
    }
  }

  // Delete knowledge base patterns
  if (/^(删除|删除|移除)(.*?)(知识库|kb)/i.test(q)) {
    const kb = knowledgeBases.value.find(k =>
      q.toLowerCase().includes(k.name.toLowerCase())
    )
    const nameMatch = q.match(/(?:删除|删除|移除)(?:一个)?(?:名为|叫)?(.+?)(?:的)?(?:知识库|kb)?/i)
    if (kb) {
      return { action: 'delete', id: kb.id, name: kb.name }
    } else if (nameMatch && nameMatch[1]) {
      return { action: 'delete_by_name', name: nameMatch[1].trim() }
    }
  }

  // Rename knowledge base patterns
  if (/^(重命名|改名|修改)(.*?)(知识库|kb)/i.test(q)) {
    const parts = q.replace(/(?:重命名|改名|修改)/i, '').split(/给|叫|为/)
    if (parts.length >= 2) {
      const oldName = parts[0].trim()
      const newName = parts[1].trim().replace(/的(?:知识库|kb)/i, '')
      const kb = knowledgeBases.value.find(k => k.name.toLowerCase().includes(oldName.toLowerCase()))
      if (kb) {
        return { action: 'rename', id: kb.id, name: newName }
      }
    }
  }

  return null
}

async function sendMessage() {
  if (!input.value.trim() || isLoading.value) return

  // Check if it's a knowledge base management command
  const kbCommand = detectKbCommand(input.value)

  // If no knowledge base selected and it's not a create command, ask to select one
  if (!selectedKb.value && (!kbCommand || kbCommand.action !== 'create')) {
    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: input.value.trim()
    }
    messages.value.push(userMessage)

    const assistantMessage: Message = {
      id: (Date.now() + 1).toString(),
      role: 'assistant',
      content: languageStore.current === 'zh'
        ? '请先选择一个知识库，或者直接说"创建一个名为[名字]的知识库"来新建。'
        : 'Please select a knowledge base first, or say "create a knowledge base named [name]" to create a new one.',
      isComplete: true
    }
    messages.value.push(assistantMessage)
    input.value = ''
    resetInputHeight()
    scrollToBottom()
    return
  }

  // Handle KB management commands without needing RAG
  if (kbCommand) {
    await handleKbCommand(kbCommand)
    return
  }

  if (!selectedKb.value) return

  const userMessage: Message = {
    id: Date.now().toString(),
    role: 'user',
    content: input.value.trim()
  }

  messages.value.push(userMessage)
  const query = input.value.trim()
  input.value = ''
  resetInputHeight()
  isLoading.value = true
  pendingContent.value = ''

  const messageId = (Date.now() + 1).toString()
  const assistantIndex = messages.value.push({
    id: messageId,
    role: 'assistant',
    content: '',
    sources: [],
    isComplete: false
  }) - 1

  scrollToBottom()

  // Get or create session ID
  if (!currentSessionId.value) {
    currentSessionId.value = localStorage.getItem('ragdocman_current_session') || `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
    localStorage.setItem('ragdocman_current_session', currentSessionId.value)
  }

  try {
    await api.streamRagAnswer(
      {
        kb_id: selectedKb.value,
        query,
        top_k: 5,
        include_sources: true,
        session_id: currentSessionId.value
      },
      {
        onSources: (sources) => {
          messages.value[assistantIndex].sources = sources
        },
        onContent: (content) => {
          pendingContent.value += content
          updateMessageContent(assistantIndex, pendingContent.value)
          scrollToBottom()
        },
        onDone: () => {
          messages.value[assistantIndex].isComplete = true
        },
        onError: (error) => {
          pendingContent.value = languageStore.current === 'zh'
            ? `抱歉，发生了一些错误：${error}`
            : `Sorry, an error occurred: ${error}`
          updateMessageContent(assistantIndex, pendingContent.value)
        }
      }
    )
  } catch (error) {
    updateMessageContent(assistantIndex, languageStore.current === 'zh'
      ? '抱歉，发生了一些错误，请稍后重试。'
      : 'Sorry, an error occurred. Please try again later.')
  } finally {
    isLoading.value = false
    pendingContent.value = ''
  }
}

async function handleKbCommand(cmd: { action: string; name?: string; id?: string }) {
  const userMessage: Message = {
    id: Date.now().toString(),
    role: 'user',
    content: input.value.trim()
  }
  messages.value.push(userMessage)
  const query = input.value.trim()
  input.value = ''
  resetInputHeight()
  isLoading.value = true

  const assistantIndex = messages.value.push({
    id: (Date.now() + 1).toString(),
    role: 'assistant',
    content: '',
    isComplete: false
  }) - 1

  scrollToBottom()

  try {
    let response = ''

    switch (cmd.action) {
      case 'create': {
        const res = await api.createKnowledgeBase({
          name: cmd.name || query.replace(/(?:创建|创建一个|新建)/, '').trim(),
          description: ''
        })
        if (res.success && res.data) {
          knowledgeBases.value.unshift(res.data)
          selectedKb.value = res.data.id
          response = languageStore.current === 'zh'
            ? `已成功创建知识库 "${res.data.name}"`
            : `Knowledge base "${res.data.name}" created successfully`
        } else {
          response = languageStore.current === 'zh'
            ? `创建知识库失败：${res.error?.message || '未知错误'}`
            : `Failed to create knowledge base: ${res.error?.message || 'Unknown error'}`
        }
        break
      }

      case 'delete':
      case 'delete_by_name': {
        let targetId = cmd.id
        if (cmd.action === 'delete_by_name' && cmd.name) {
          const kb = knowledgeBases.value.find(k =>
            k.name.toLowerCase().includes(cmd.name!.toLowerCase())
          )
          targetId = kb?.id
        }
        if (!targetId) {
          response = languageStore.current === 'zh'
            ? `未找到要删除的知识库`
            : `Knowledge base not found`
        } else {
          const res = await api.deleteKnowledgeBase(targetId)
          if (res.success) {
            knowledgeBases.value = knowledgeBases.value.filter(k => k.id !== targetId)
            if (selectedKb.value === targetId) {
              selectedKb.value = knowledgeBases.value[0]?.id || ''
            }
            response = languageStore.current === 'zh'
              ? `已删除知识库 "${cmd.name || cmd.id}"`
              : `Knowledge base "${cmd.name || cmd.id}" deleted`
          } else {
            response = languageStore.current === 'zh'
              ? `删除知识库失败：${res.error?.message || '未知错误'}`
              : `Failed to delete knowledge base: ${res.error?.message || 'Unknown error'}`
          }
        }
        break
      }

      case 'rename': {
        const res = await api.updateKnowledgeBase(cmd.id!, { name: cmd.name })
        if (res.success && res.data) {
          const index = knowledgeBases.value.findIndex(k => k.id === cmd.id)
          if (index >= 0) {
            knowledgeBases.value[index] = res.data
          }
          selectedKb.value = cmd.id!
          response = languageStore.current === 'zh'
            ? `已将知识库重命名为 "${cmd.name}"`
            : `Knowledge base renamed to "${cmd.name}"`
        } else {
          response = languageStore.current === 'zh'
            ? `重命名失败：${res.error?.message || '未知错误'}`
            : `Failed to rename: ${res.error?.message || 'Unknown error'}`
        }
        break
      }
    }

    messages.value[assistantIndex].content = response
    messages.value[assistantIndex].isComplete = true
    scrollToBottom()
  } catch (error) {
    messages.value[assistantIndex].content = languageStore.current === 'zh'
      ? `操作失败：${error}`
      : `Operation failed: ${error}`
    messages.value[assistantIndex].isComplete = true
  } finally {
    isLoading.value = false
  }
}

function newChat() {
  // Clear current session on UI
  messages.value = []
  localStorage.removeItem('ragdocman_current_session')
  currentSessionId.value = ''
}

function handleKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    sendMessage()
  }
}
</script>

<template>
  <div class="min-h-[calc(100vh-4rem)] flex flex-col">
    <!-- Header -->
    <div class="sticky top-0 z-20 bg-gradient-to-b from-light-bg dark:from-dark-bg to-transparent pt-4 pb-2 px-4">
      <div class="flex items-center justify-between max-w-4xl mx-auto">
        <div class="flex items-center gap-3">
          <div class="relative">
            <div class="w-10 h-10 rounded-xl bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center shadow-lg shadow-cyan-500/20">
              <Bot class="w-5 h-5 text-white" />
            </div>
            <div class="absolute -bottom-0.5 -right-0.5 w-3 h-3 bg-green-500 rounded-full border-2 border-light-bg dark:border-dark-bg"></div>
          </div>
          <div>
            <h1 class="font-title text-xl font-bold text-light-text dark:text-dark-text">
              {{ languageStore.t.chat.title }}
            </h1>
            <p class="text-xs text-cyan-500 dark:text-cyan-400 font-medium">
              RAG Assistant
            </p>
          </div>
        </div>

        <div class="flex items-center gap-3">
          <Select
            v-model="selectedKb"
            :options="kbOptions"
            class="min-w-[180px]"
          />
          <Button variant="ghost" size="sm" @click="newChat" :title="languageStore.t.chat.newChat">
            <Plus class="w-4 h-4" />
          </Button>
        </div>
      </div>
    </div>

    <!-- Messages -->
    <div ref="messagesContainer" class="flex-1 overflow-y-auto px-4 py-4 max-w-4xl mx-auto w-full">
      <!-- Welcome State -->
      <div v-if="messages.length === 0" class="flex flex-col items-center justify-center h-[60vh] text-center px-4">
        <div class="relative mb-6">
          <div class="w-24 h-24 rounded-3xl bg-gradient-to-br from-cyan-500/20 via-blue-500/20 to-purple-600/20 flex items-center justify-center animate-pulse">
            <div class="w-16 h-16 rounded-2xl bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center shadow-xl shadow-cyan-500/30">
              <Sparkles class="w-8 h-8 text-white" />
            </div>
          </div>
        </div>

        <h2 class="text-2xl font-title font-bold text-light-text dark:text-dark-text mb-3 bg-gradient-to-r from-cyan-500 to-blue-600 bg-clip-text text-transparent">
          {{ languageStore.t.chat.welcome }}
        </h2>
        <p class="text-light-text/60 dark:text-dark-text/60 max-w-md mb-8">
          {{ languageStore.t.chat.welcomeDesc }}
        </p>

        <!-- Quick action cards -->
        <div class="grid grid-cols-2 md:grid-cols-3 gap-3 max-w-lg">
          <button
            v-for="action in [
              { icon: FileText, label: '搜索文档', labelEn: 'Search Docs', action: '搜索' },
              { icon: Plus, label: '创建知识库', labelEn: 'Create KB', action: '创建一个' },
              { icon: Database, label: '查看知识库', labelEn: 'View KBs', action: '列出知识库' }
            ]"
            :key="action.label"
            @click="input = action.action"
            class="flex items-center gap-2 px-4 py-3 rounded-xl border border-light-border dark:border-dark-border hover:border-cyan-500/50 hover:bg-cyan-500/5 transition-all duration-200 group"
          >
            <component :is="action.icon" class="w-4 h-4 text-cyan-500 group-hover:text-cyan-400" />
            <span class="text-sm text-light-text/80 dark:text-dark-text/80">{{ languageStore.current === 'zh' ? action.label : action.labelEn }}</span>
          </button>
        </div>
      </div>

      <!-- Message List -->
      <div v-else class="space-y-4 pb-4">
        <div
          v-for="msg in messages"
          :key="msg.id"
          class="animate-fade-in"
        >
          <!-- User message -->
          <div v-if="msg.role === 'user'" class="flex justify-end">
            <div class="max-w-[80%] rounded-2xl px-4 py-3 bg-gradient-to-r from-cyan-500 to-blue-600 text-white shadow-lg shadow-cyan-500/20">
              <p class="whitespace-pre-wrap">{{ msg.content }}</p>
            </div>
          </div>

          <!-- Assistant message -->
          <div v-else class="flex justify-start">
            <Card class="max-w-[95%] w-full p-0 overflow-hidden">
              <!-- Status bar -->
              <div class="flex items-center justify-between px-4 py-2 bg-gradient-to-r from-gray-50/50 to-gray-100/50 dark:from-gray-800/50 dark:to-gray-700/50 border-b border-light-border dark:border-dark-border">
                <div class="flex items-center gap-2">
                  <Bot class="w-4 h-4 text-cyan-500" />
                  <span class="text-sm font-medium text-light-text/70 dark:text-dark-text/70">
                    AI
                  </span>
                  <span v-if="!msg.isComplete" class="flex items-center gap-1 text-xs text-cyan-500">
                    <Loader2 class="w-3 h-3 animate-spin" />
                    {{ languageStore.t.chat.thinking }}
                  </span>
                  <span v-else class="text-xs text-green-500">
                    {{ languageStore.current === 'zh' ? '完成' : 'Done' }}
                  </span>
                </div>
              </div>

              <!-- Content -->
              <div class="p-4">
                <div class="prose prose-sm dark:prose-invert max-w-none">
                  <div v-if="msg.content" class="markdown-content" v-html="renderMarkdown(msg.content)"></div>
                  <div v-else-if="!msg.isComplete" class="flex items-center gap-2 text-light-text/50">
                    <Loader2 class="w-4 h-4 animate-spin" />
                    <span>{{ languageStore.t.chat.thinking }}</span>
                  </div>
                </div>

                <!-- Sources -->
                <Transition name="fade-slide">
                  <div v-if="msg.isComplete && msg.sources && msg.sources.length > 0" class="mt-4 pt-4 border-t border-light-border dark:border-dark-border">
                    <h4 class="text-sm font-medium text-light-text/70 dark:text-dark-text/70 mb-2 flex items-center gap-1">
                      <FileText class="w-4 h-4" />
                      {{ languageStore.t.chat.sources }}
                    </h4>
                    <div class="space-y-2">
                      <div
                        v-for="source in msg.sources"
                        :key="source.chunk_id"
                        class="text-xs p-2 rounded-lg bg-light-bg dark:bg-dark-bg border border-light-border dark:border-dark-border"
                      >
                        <div class="font-medium text-cyan-600 dark:text-cyan-400 flex items-center justify-between">
                          <span>{{ source.doc_name }}</span>
                          <span class="text-green-500">{{ (source.score * 100).toFixed(0) }}%</span>
                        </div>
                        <div class="text-light-text/60 dark:text-dark-text/60 truncate mt-1">{{ source.content }}</div>
                      </div>
                    </div>
                  </div>
                </Transition>
              </div>
            </Card>
          </div>
        </div>
      </div>
    </div>

    <!-- Input -->
    <div class="sticky bottom-0 pt-4 pb-4 px-4 bg-gradient-to-t from-light-bg dark:from-dark-bg via-light-bg/95 dark:via-dark-bg/95 to-transparent">
      <div class="max-w-4xl mx-auto">
        <div class="relative flex items-end gap-3 p-3 rounded-2xl border border-cyan-500/30 dark:border-cyan-400/30 bg-light-card/80 dark:bg-dark-card/80 backdrop-blur-xl shadow-lg shadow-cyan-500/10">
          <!-- Glow effect -->
          <div class="absolute inset-0 rounded-2xl bg-gradient-to-r from-cyan-500/5 to-blue-500/5 pointer-events-none"></div>

          <div class="flex-1 overflow-y-auto" style="max-height: 150px;">
            <textarea
              ref="inputRef"
              v-model="input"
              :placeholder="languageStore.t.chat.placeholder"
              rows="1"
              class="w-full resize-none bg-transparent border-none outline-none text-light-text dark:text-dark-text placeholder:text-gray-400 z-10 relative"
              style="max-height: 150px;"
              @input="adjustTextareaHeight"
              @keydown="handleKeydown"
            ></textarea>
          </div>

          <Button
            :disabled="!input.trim() || !selectedKb || isLoading"
            :loading="isLoading"
            @click="sendMessage"
            class="relative z-10 bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 border-0"
          >
            <Send class="w-4 h-4" />
          </Button>
        </div>
      </div>
    </div>
  </div>
</template>

<style>
/* Transition forSources */
.fade-slide-enter-active {
  transition: all 0.3s ease-out;
}

.fade-slide-enter-from {
  opacity: 0;
  transform: translateY(10px);
}

.fade-slide-enter-to {
  opacity: 1;
  transform: translateY(0);
}

.markdown-content {
  color: var(--color-text);
  line-height: 1.6;
}

.markdown-content h1,
.markdown-content h2,
.markdown-content h3,
.markdown-content h4 {
  margin-top: 1em;
  margin-bottom: 0.5em;
  font-weight: 600;
}

.markdown-content h1 { font-size: 1.5em; }
.markdown-content h2 { font-size: 1.3em; }
.markdown-content h3 { font-size: 1.1em; }

.markdown-content p { margin-bottom: 0.75em; }

.markdown-content ul,
.markdown-content ol {
  padding-left: 1.5em;
  margin-bottom: 0.75em;
}

.markdown-content li { margin-bottom: 0.25em; }

.markdown-content code {
  background: rgba(0, 0, 0, 0.1);
  padding: 0.15em 0.4em;
  border-radius: 4px;
  font-family: monospace;
  font-size: 0.9em;
}

:global(.dark) .markdown-content code {
  background: rgba(255, 255, 255, 0.1);
}

.markdown-content pre {
  background: rgba(0, 0, 0, 0.05);
  padding: 1em;
  border-radius: 8px;
  overflow-x: auto;
  margin-bottom: 0.75em;
}

:global(.dark) .markdown-content pre {
  background: rgba(255, 255, 255, 0.05);
}

.markdown-content pre code {
  background: transparent;
  padding: 0;
}

.markdown-content blockquote {
  border-left: 3px solid var(--color-cta);
  padding-left: 1em;
  margin-left: 0;
  color: rgba(0, 0, 0, 0.6);
}

:global(.dark) .markdown-content blockquote {
  color: rgba(255, 255, 255, 0.6);
}

.markdown-content a {
  color: var(--color-cta);
  text-decoration: underline;
}
</style>