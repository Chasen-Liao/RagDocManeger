<script setup lang="ts">
import { ref, onMounted, nextTick, computed } from 'vue'
import { Send, Loader2, FileText, Database, Plus } from 'lucide-vue-next'
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
  loadSessions()
})

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

function loadSessions() {
  const saved = localStorage.getItem('ragdocman_sessions')
  if (saved) {
    try {
      const sessions = JSON.parse(saved)
      if (sessions.length > 0) {
        messages.value = sessions[0].messages || []
        selectedKb.value = sessions[0].kbId || ''
      }
    } catch {
      // Ignore
    }
  }
}

function saveSession() {
  const sessions = localStorage.getItem('ragdocman_sessions')
  let sessionList = sessions ? JSON.parse(sessions) : []

  if (sessionList.length === 0 || sessionList[0].messages.length === 0) {
    sessionList.unshift({
      id: Date.now().toString(),
      kbId: selectedKb.value,
      messages: messages.value,
      createdAt: new Date().toISOString()
    })
  } else {
    sessionList[0] = {
      ...sessionList[0],
      kbId: selectedKb.value,
      messages: messages.value,
      createdAt: new Date().toISOString()
    }
  }

  localStorage.setItem('ragdocman_sessions', JSON.stringify(sessionList))
}

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

  try {
    await api.streamRagAnswer(
      {
        kb_id: selectedKb.value,
        query,
        top_k: 5,
        include_sources: true
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
          saveSession()
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
  if (messages.value.length > 0) {
    const sessions = localStorage.getItem('ragdocman_sessions')
    let sessionList = sessions ? JSON.parse(sessions) : []
    sessionList.unshift({
      id: Date.now().toString(),
      kbId: selectedKb.value,
      messages: messages.value,
      createdAt: new Date().toISOString()
    })
    localStorage.setItem('ragdocman_sessions', JSON.stringify(sessionList))
  }
  messages.value = []
}

function handleKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    sendMessage()
  }
}
</script>

<template>
  <div class="min-h-[calc(100vh-4rem)] flex flex-col max-w-4xl mx-auto px-4 py-8">
    <!-- Header -->
    <div class="flex items-center justify-between mb-6">
      <h1 class="font-title text-2xl font-bold text-light-text dark:text-dark-text">{{ languageStore.t.chat.title }}</h1>
      <div class="flex items-center gap-3">
        <Select
          v-model="selectedKb"
          :options="kbOptions"
        />
        <Button variant="ghost" size="sm" @click="newChat">
          <Plus class="w-4 h-4" />
          {{ languageStore.t.chat.newChat }}
        </Button>
      </div>
    </div>

    <!-- Messages -->
    <div ref="messagesContainer" class="flex-1 space-y-4 overflow-y-auto mb-4 max-h-[calc(100vh-16rem)]">
      <div v-if="messages.length === 0" class="flex flex-col items-center justify-center h-64 text-center">
        <div class="w-16 h-16 rounded-2xl bg-gradient-to-br from-blue-500/20 to-purple-600/20 flex items-center justify-center mb-4">
          <Database class="w-8 h-8 text-light-cta dark:text-dark-cta" />
        </div>
        <h2 class="text-xl font-title font-semibold text-light-text dark:text-dark-text mb-2">
          {{ languageStore.t.chat.welcome }}
        </h2>
        <p class="text-light-text/60 dark:text-dark-text/60 max-w-md">
          {{ languageStore.t.chat.welcomeDesc }}
        </p>
      </div>

      <div
        v-for="(msg, index) in messages"
        :key="msg.id"
        class="animate-slide-up"
      >
        <!-- User message -->
        <div v-if="msg.role === 'user'" class="flex justify-end">
          <div class="max-w-[80%] rounded-2xl px-4 py-3 bg-light-cta dark:bg-dark-cta text-white">
            {{ msg.content }}
          </div>
        </div>

        <!-- Assistant message -->
        <div v-else class="flex justify-start">
          <Card class="max-w-[85%] p-4">
            <div class="prose prose-sm dark:prose-invert max-w-none">
              <div v-if="msg.content" class="markdown-content" v-html="renderMarkdown(msg.content)"></div>
              <div v-else class="flex items-center gap-2 text-light-text/50">
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
                    class="text-xs p-2 rounded-lg bg-light-bg dark:bg-dark-bg"
                  >
                    <div class="font-medium text-light-cta dark:text-dark-cta">{{ source.doc_name }}</div>
                    <div class="text-light-text/60 dark:text-dark-text/60 truncate">{{ source.content }}</div>
                  </div>
                </div>
              </div>
            </Transition>
          </Card>
        </div>
      </div>
    </div>

    <!-- Input -->
    <div class="sticky bottom-0 pt-4 bg-gradient-to-t from-light-bg dark:from-dark-bg via-light-bg/95 dark:via-dark-bg/95 to-transparent">
      <div class="flex items-end gap-3 p-4 rounded-2xl border border-light-border dark:border-dark-border bg-light-card dark:bg-dark-card shadow-glass">
        <div class="flex-1 overflow-y-auto" style="max-height: 150px;">
          <textarea
            ref="inputRef"
            v-model="input"
            :placeholder="languageStore.t.chat.placeholder"
            rows="1"
            class="w-full resize-none bg-transparent border-none outline-none text-light-text dark:text-dark-text placeholder:text-gray-400"
            style="max-height: 150px;"
            @input="adjustTextareaHeight"
            @keydown="handleKeydown"
          ></textarea>
        </div>
        <Button
          :disabled="!input.trim() || !selectedKb"
          :loading="isLoading"
          @click="sendMessage"
        >
          <Send class="w-4 h-4" />
        </Button>
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