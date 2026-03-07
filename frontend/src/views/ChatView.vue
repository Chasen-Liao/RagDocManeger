<script setup lang="ts">
import { ref, onMounted, nextTick, computed } from 'vue'
import { Send, Loader2, FileText, Database, Plus, Bot, Activity, CheckCircle2, XCircle, Terminal, ChevronDown, ChevronRight, Zap, GitBranch } from 'lucide-vue-next'
import { marked } from 'marked'
import { api, type KnowledgeBase } from '@/api/client'
import { useLanguageStore } from '@/stores/language'
import Card from '@/components/ui/Card.vue'
import Button from '@/components/ui/Button.vue'
import Select from '@/components/ui/Select.vue'

const languageStore = useLanguageStore()
const messagesContainer = ref<HTMLElement | null>(null)

// Types
interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  thinking?: string
  toolCalls?: ToolCallDisplay[]
  isComplete?: boolean
  isError?: boolean
}

interface ToolCallDisplay {
  id: string
  name: string
  input: string
  output: string
  status: 'pending' | 'running' | 'success' | 'error'
  executionTime?: number
  expanded?: boolean
}

// State
const messages = ref<Message[]>([])
const input = ref('')
const isLoading = ref(false)
const selectedKb = ref<string>('')
const knowledgeBases = ref<KnowledgeBase[]>([])
const pendingContent = ref('')
const pendingThinking = ref('')
const inputRef = ref<HTMLTextAreaElement | null>(null)
const currentSessionId = ref<string>('')
const showToolsPanel = ref(true)

// Agent workflow state
const isAgentRunning = ref(false)
const currentToolCalls = ref<ToolCallDisplay[]>([])
const workflowLog = ref<Array<{ time: string; type: string; message: string }>>([])
const toolCallsExpanded = ref(true)

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

function resetInputHeight() {
  if (inputRef.value) {
    inputRef.value.style.height = 'auto'
  }
}

function addWorkflowLog(type: string, message: string) {
  const time = new Date().toLocaleTimeString('zh-CN', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' })
  workflowLog.value.push({ time, type, message })
  if (workflowLog.value.length > 50) {
    workflowLog.value = workflowLog.value.slice(-50)
  }
}

onMounted(async () => {
  await loadKnowledgeBases()
  await loadSessionHistory()
})

async function loadSessionHistory() {
  const savedSessionId = localStorage.getItem('ragdocman_current_session')
  if (savedSessionId) {
    try {
      const res = await api.getSessionHistory(savedSessionId)
      if (res.success && res.data && res.data.messages) {
        for (const msg of res.data.messages) {
          messages.value.push({
            id: `${Date.now()}_${Math.random()}`,
            role: msg.role as 'user' | 'assistant',
            content: msg.content,
            isComplete: true
          })
        }
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

function newChat() {
  messages.value = []
  localStorage.removeItem('ragdocman_current_session')
  currentSessionId.value = ''
  workflowLog.value = []
  currentToolCalls.value = []
}

function handleKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    sendMessage()
  }
}

async function sendMessage() {
  if (!input.value.trim() || isLoading.value) return

  if (!currentSessionId.value) {
    currentSessionId.value = `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
    localStorage.setItem('ragdocman_current_session', currentSessionId.value)
  }

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
  isAgentRunning.value = true
  pendingContent.value = ''
  pendingThinking.value = ''
  currentToolCalls.value = []
  workflowLog.value = []

  addWorkflowLog('start', 'Starting request...')

  const messageId = (Date.now() + 1).toString()
  const assistantIndex = messages.value.push({
    id: messageId,
    role: 'assistant',
    content: '',
    toolCalls: [],
    isComplete: false
  }) - 1

  scrollToBottom()

  try {
    await api.streamAgentMessage(
      query,
      currentSessionId.value,
      {
        onToolCall: (data: any) => {
          const toolName = data?.data?.tool_name || data?.tool_name || 'unknown'
          const toolInput = data?.data?.tool_input || data?.tool_input || {}
          const toolOutput = data?.data?.tool_output || data?.tool_output || ''

          let inputDisplay = ''
          if (toolInput && typeof toolInput === 'object') {
            inputDisplay = JSON.stringify(toolInput, null, 2)
          } else {
            inputDisplay = String(toolInput)
          }

          if (selectedKb.value && toolInput && typeof toolInput === 'object' && !toolInput.kb_id) {
            toolInput.kb_id = selectedKb.value
            inputDisplay = JSON.stringify(toolInput, null, 2)
          }

          addWorkflowLog('tool', `Tool: ${toolName}`)

          const newToolCall: ToolCallDisplay = {
            id: `${Date.now()}_${Math.random()}`,
            name: toolName,
            input: inputDisplay,
            output: '',
            status: 'running'
          }
          currentToolCalls.value.push(newToolCall)
          messages.value[assistantIndex].toolCalls = [...currentToolCalls.value]
          scrollToBottom()

          if (toolOutput && Object.keys(toolOutput).length > 0) {
            const lastTool = currentToolCalls.value[currentToolCalls.value.length - 1]
            if (lastTool) {
              lastTool.output = typeof toolOutput === 'string' ? toolOutput : JSON.stringify(toolOutput, null, 2)
              lastTool.status = 'success'
              addWorkflowLog('success', `${toolName} completed`)
            }
          }
        },
        onContent: (content, type) => {
          if (type === 'tool_result') {
            const lastTool = currentToolCalls.value[currentToolCalls.value.length - 1]
            if (lastTool && lastTool.status === 'running') {
              lastTool.output = content
              lastTool.status = 'success'
              addWorkflowLog('success', `Tool executed: ${lastTool.name}`)
            }
          } else if (type === 'thinking') {
            pendingThinking.value += content
            messages.value[assistantIndex].thinking = pendingThinking.value
          } else {
            pendingContent.value += content
            messages.value[assistantIndex].content = pendingContent.value
          }
          scrollToBottom()
        },
        onDone: () => {
          messages.value[assistantIndex].isComplete = true
          messages.value[assistantIndex].thinking = pendingThinking.value
          pendingThinking.value = ''
          isAgentRunning.value = false
          isLoading.value = false
          addWorkflowLog('done', 'Request complete')
          scrollToBottom()
        },
        onError: (error) => {
          addWorkflowLog('error', `Error: ${error}`)
          messages.value[assistantIndex].isError = true
          messages.value[assistantIndex].content = error
          messages.value[assistantIndex].isComplete = true
          isAgentRunning.value = false
          isLoading.value = false
          scrollToBottom()
        }
      }
    )
  } catch (error) {
    messages.value[assistantIndex].content = languageStore.current === 'zh'
      ? `Error: ${error}`
      : `Error: ${error}`
    messages.value[assistantIndex].isError = true
    messages.value[assistantIndex].isComplete = true
    isAgentRunning.value = false
    isLoading.value = false
  } finally {
    pendingContent.value = ''
    pendingThinking.value = ''
  }
}
</script>

<template>
  <div class="min-h-[calc(100vh-3.5rem)] flex flex-col lg:flex-row">
    <!-- Main Chat Area -->
    <div class="flex-1 flex flex-col min-w-0">
      <!-- Header -->
      <div class="sticky top-14 z-20 backdrop-header border-b border-gray-200 dark:border-gray-800">
        <div class="max-w-3xl mx-auto px-4 py-2.5">
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-2.5">
              <div class="w-7 h-7 rounded-md bg-gray-900 dark:bg-gray-100 flex items-center justify-center">
                <Bot class="w-3.5 h-3.5 text-white dark:text-gray-900" />
              </div>
              <div>
                <h1 class="font-medium text-gray-900 dark:text-gray-100 text-[14px]">
                  {{ languageStore.t.chat.title }}
                </h1>
                <p class="text-[11px] text-gray-500 dark:text-gray-400">
                  Agent Mode
                </p>
              </div>
            </div>

            <div class="flex items-center gap-1.5">
              <Select
                v-model="selectedKb"
                :options="kbOptions"
                class="w-36"
              />
              <Button variant="ghost" size="sm" @click="newChat">
                <Plus class="w-3.5 h-3.5" />
              </Button>
            </div>
          </div>
        </div>
      </div>

      <!-- Messages -->
      <div ref="messagesContainer" class="flex-1 overflow-y-auto w-full">
        <!-- Welcome State (Anthropic style) -->
        <div v-if="messages.length === 0" class="flex flex-col items-center justify-center min-h-[70vh] text-center px-4">
          <div class="w-16 h-16 rounded-2xl bg-[#0A35CC] dark:bg-[#7096FF] flex items-center justify-center mb-5">
            <Bot class="w-7 h-7 text-white dark:text-[#0D0D0C]" />
          </div>

          <h2 class="text-2xl font-medium text-[#31312D] dark:text-[#EAEAE8] mb-2">
            {{ languageStore.t.chat.welcome }}
          </h2>
          <p class="text-[15px] text-[#6B6B65] dark:text-[#989894] max-w-md mb-8">
            {{ languageStore.t.chat.welcomeDesc }}
          </p>

          <!-- Quick action buttons (Anthropic pill style) -->
          <div class="flex flex-wrap justify-center gap-2">
            <button
              v-for="action in [
                { label: '搜索文档', action: '搜索' },
                { label: '创建知识库', action: '创建一个' },
                { label: '查看知识库', action: '列出知识库' }
              ]"
              :key="action.label"
              @click="input = action.action"
              class="px-4 py-2.5 rounded-full border border-[#E8E8E6] dark:border-[#3A3A38] text-[14px] text-[#6B6B65] dark:text-[#989894] hover:bg-[#F7F7F5] dark:hover:bg-[#1A1A19] hover:border-[#0A35CC] dark:hover:border-[#7096FF] transition-all cursor-pointer"
            >
              {{ action.label }}
            </button>
          </div>
        </div>

        <!-- Message List -->
        <div v-else class="pb-24">
          <div
            v-for="msg in messages"
            :key="msg.id"
          >
            <!-- User message -->
            <div v-if="msg.role === 'user'" class="flex justify-end px-4 py-2">
              <div class="max-w-[80%] rounded-2xl px-4 py-3 bg-[#0F0F0F] dark:bg-[#F7F7F5] text-white dark:text-[#0F0F0F]">
                <p class="whitespace-pre-wrap text-[15px] leading-relaxed">{{ msg.content }}</p>
              </div>
            </div>

            <!-- Assistant message -->
            <div v-else class="px-4 py-2">
              <div class="max-w-[85%]">
                <!-- Tool Calls Badge (Anthropic style) -->
                <div v-if="msg.toolCalls && msg.toolCalls.length > 0" class="flex flex-wrap gap-1.5 mb-2">
                  <span
                    v-for="tool in msg.toolCalls"
                    :key="tool.id"
                    class="inline-flex items-center gap-1 px-2 py-1 rounded-md bg-[#F0F0EE] dark:bg-[#2A2A29] text-[12px] text-[#6B6B65] dark:text-[#989894]"
                  >
                    <component :is="tool.status === 'success' ? CheckCircle2 : (tool.status === 'running' ? Loader2 : XCircle)"
                      :class="['w-3 h-3', tool.status === 'success' ? 'text-green-500' : tool.status === 'running' ? 'text-yellow-500 animate-spin' : 'text-red-500']"
                    />
                    {{ tool.name }}
                  </span>
                </div>

                <!-- Thinking (Anthropic collapsible style) -->
                <div v-if="msg.thinking" class="mb-2">
                  <details class="group">
                    <summary class="flex items-center gap-1.5 text-[12px] text-[#6B6B65] dark:text-[#989894] cursor-pointer hover:text-[#31312D] dark:hover:text-[#EAEAE8] transition-colors list-none">
                      <span class="transform transition-transform group-open:rotate-90">▶</span>
                      {{ languageStore.current === 'zh' ? '思考中' : 'Thinking' }}
                    </summary>
                    <div class="mt-2 p-3 rounded-lg bg-[#F7F7F5] dark:bg-[#1A1A19] text-[13px] text-[#6B6B65] dark:text-[#989894] whitespace-pre-wrap leading-relaxed border border-[#E8E8E6] dark:border-[#3A3A38]">
                      {{ msg.thinking }}
                    </div>
                  </details>
                </div>

                <!-- Content -->
                <div class="text-[15px] leading-relaxed text-[#31312D] dark:text-[#EAEAE8]">
                  <div v-if="msg.content" class="markdown-content" v-html="renderMarkdown(msg.content)"></div>
                  <div v-else-if="!msg.isComplete" class="flex items-center gap-2 text-[#6B6B65]">
                    <Loader2 class="w-4 h-4 animate-spin" />
                    <span class="text-sm">{{ languageStore.t.chat.thinking }}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Input (Anthropic style) -->
      <div class="fixed bottom-0 left-0 right-0 p-4 bg-[#F7F7F5] dark:bg-[#0D0D0C] border-t border-[#E8E8E6] dark:border-[#3A3A38]">
        <div class="max-w-3xl mx-auto">
          <div class="relative flex items-end gap-2 p-1 rounded-xl border border-[#E8E8E6] dark:border-[#3A3A38] bg-white dark:bg-[#1A1A19] shadow-sm focus-within:shadow-md focus-within:border-[#0A35CC] dark:focus-within:border-[#7096FF] transition-all">
            <div class="flex-1 overflow-y-auto" style="max-height: 150px;">
              <textarea
                ref="inputRef"
                v-model="input"
                :placeholder="languageStore.current === 'zh' ? '给 RagDocMan 发送消息...' : 'Send a message to RagDocMan...'"
                rows="1"
                class="w-full resize-none bg-transparent border-none outline-none text-[#31312D] dark:text-[#EAEAE8] placeholder:text-[#989894] px-4 py-3 text-[15px]"
                style="max-height: 150px;"
                @input="adjustTextareaHeight"
                @keydown="handleKeydown"
              ></textarea>
            </div>

            <button
              :disabled="!input.trim() || isLoading"
              @click="sendMessage"
              class="m-1 p-3 rounded-xl bg-[#0A35CC] dark:bg-[#7096FF] text-white dark:text-[#0D0D0C] disabled:opacity-40 disabled:cursor-not-allowed hover:opacity-90 transition-opacity"
            >
              <Send class="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Agent Workflow Panel -->
    <div class="w-full lg:w-64 shrink-0 lg:max-h-[calc(100vh-3.5rem)] lg:sticky lg:top-14 border-l border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900">
      <div class="h-full flex flex-col overflow-hidden">
        <!-- Panel Header -->
        <div class="flex items-center justify-between px-3 py-2.5 border-b border-gray-200 dark:border-gray-800 shrink-0">
          <div class="flex items-center gap-1.5">
            <Activity class="w-3.5 h-3.5 text-gray-500" />
            <span class="text-[12px] font-medium text-gray-600 dark:text-gray-400">
              {{ languageStore.current === 'zh' ? 'Workflow' : 'Workflow' }}
            </span>
          </div>
          <Button variant="ghost" size="sm" @click="showToolsPanel = !showToolsPanel" class="p-1">
            <component :is="showToolsPanel ? ChevronDown : ChevronRight" class="w-3.5 h-3.5" />
          </Button>
        </div>

        <!-- Workflow Log -->
        <div v-show="showToolsPanel" class="flex-1 overflow-y-auto p-3 font-mono text-[11px]">
          <div v-if="workflowLog.length === 0" class="text-center text-gray-400 dark:text-gray-500 py-6">
            <Terminal class="w-6 h-6 mx-auto mb-1.5 opacity-40" />
            <p>{{ languageStore.current === 'zh' ? '等待...' : 'Waiting...' }}</p>
          </div>

          <div v-else class="space-y-0.5">
            <div
              v-for="(log, index) in workflowLog"
              :key="index"
              class="flex items-start gap-1.5 py-0.5"
              :class="{
                'text-gray-600 dark:text-gray-400': log.type === 'start' || log.type === 'tool',
                'text-green-600 dark:text-green-400': log.type === 'success' || log.type === 'done',
                'text-red-600 dark:text-red-400': log.type === 'error'
              }"
            >
              <span class="text-gray-400 dark:text-gray-500 shrink-0">{{ log.time }}</span>
              <span class="break-all">{{ log.message }}</span>
            </div>
          </div>

          <div v-if="isAgentRunning" class="mt-3 flex items-center gap-1.5 text-gray-500">
            <Loader2 class="w-3 h-3 animate-spin" />
            <span>{{ languageStore.current === 'zh' ? '运行中...' : 'Running...' }}</span>
          </div>
        </div>

        <!-- Active Tools Section -->
        <div v-if="currentToolCalls.length > 0" class="border-t border-gray-200 dark:border-gray-800 shrink-0">
          <button
            @click="toolCallsExpanded = !toolCallsExpanded"
            class="w-full px-3 py-2 text-[11px] font-medium text-gray-500 dark:text-gray-400 flex items-center justify-between hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors"
          >
            <div class="flex items-center gap-1">
              <Zap class="w-3 h-3" />
              {{ languageStore.current === 'zh' ? 'Tools' : 'Tools' }}
              <span class="text-gray-400">({{ currentToolCalls.length }})</span>
            </div>
            <ChevronDown
              class="w-3.5 h-3.5 transition-transform"
              :class="{ 'rotate-180': !toolCallsExpanded }"
            />
          </button>
          <div v-show="toolCallsExpanded" class="px-3 pb-2.5 space-y-0.5 max-h-32 overflow-y-auto">
            <div
              v-for="tool in currentToolCalls"
              :key="tool.id"
              class="flex items-center gap-1.5 text-[11px] py-0.5"
            >
              <div
                class="w-1.5 h-1.5 rounded-full shrink-0"
                :class="{
                  'bg-yellow-500 animate-pulse': tool.status === 'running',
                  'bg-green-500': tool.status === 'success',
                  'bg-red-500': tool.status === 'error',
                  'bg-gray-400': tool.status === 'pending'
                }"
              ></div>
              <span class="text-gray-600 dark:text-gray-400">{{ tool.name }}</span>
              <span v-if="tool.status === 'success'" class="text-green-500">✓</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style>
/* Transition */
.animate-fade-in {
  animation: fadeIn 0.2s ease-out;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(4px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.markdown-content {
  color: var(--color-text);
  line-height: 1.65;
}

.markdown-content h1,
.markdown-content h2,
.markdown-content h3,
.markdown-content h4 {
  margin-top: 1em;
  margin-bottom: 0.4em;
  font-weight: 600;
  color: var(--color-text);
}

.markdown-content h1 { font-size: 1.25em; }
.markdown-content h2 { font-size: 1.15em; }
.markdown-content h3 { font-size: 1.05em; }

.markdown-content p { margin-bottom: 0.65em; }

.markdown-content ul,
.markdown-content ol {
  padding-left: 1.25em;
  margin-bottom: 0.65em;
}

.markdown-content li { margin-bottom: 0.2em; }

.markdown-content code {
  background: rgba(0, 0, 0, 0.06);
  padding: 0.12em 0.35em;
  border-radius: 3px;
  font-family: 'SF Mono', monospace;
  font-size: 0.9em;
}

:global(.dark) .markdown-content code {
  background: rgba(255, 255, 255, 0.1);
}

.markdown-content pre {
  background: rgba(0, 0, 0, 0.04);
  padding: 0.75em;
  border-radius: 6px;
  overflow-x: auto;
  margin-bottom: 0.75em;
}

:global(.dark) .markdown-content pre {
  background: rgba(255, 255, 255, 0.04);
}

.markdown-content pre code {
  background: transparent;
  padding: 0;
}

.markdown-content blockquote {
  border-left: 2px solid #d4d4d4;
  padding-left: 0.75em;
  margin-left: 0;
  color: rgba(0, 0, 0, 0.6);
}

:global(.dark) .markdown-content blockquote {
  border-left-color: #555;
  color: rgba(255, 255, 255, 0.6);
}

.markdown-content a {
  color: #0A35CC;
  text-decoration: underline;
  text-decoration-color: rgba(10, 53, 204, 0.3);
}

.markdown-content a:hover {
  text-decoration-color: rgba(10, 53, 204, 0.6);
}

:global(.dark) .markdown-content a {
  color: #7096FF;
  text-decoration-color: rgba(112, 150, 255, 0.3);
}

:global(.dark) .markdown-content a:hover {
  text-decoration-color: rgba(112, 150, 255, 0.6);
}
</style>