<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { MessageSquare, Trash2, ChevronRight, Bot, Loader2 } from 'lucide-vue-next'
import { useLanguageStore } from '@/stores/language'
import { api } from '@/api/client'
import Card from '@/components/ui/Card.vue'
import Button from '@/components/ui/Button.vue'

const languageStore = useLanguageStore()
const router = useRouter()

interface Session {
  session_id: string
  last_message_at: string
  preview: string
  message_count: number
}

interface HistoryMessage {
  role: string
  content: string
  created_at: string
}

const sessions = ref<Session[]>([])
const isLoading = ref(false)

onMounted(async () => {
  await loadSessions()
})

async function loadSessions() {
  isLoading.value = true
  try {
    const res = await api.listSessions()
    if (res.success && res.data) {
      sessions.value = res.data
    }
  } catch (error) {
    console.error('Failed to load sessions:', error)
  } finally {
    isLoading.value = false
  }
}

async function deleteSession(sessionId: string) {
  try {
    await api.clearAgentSession(sessionId)
    sessions.value = sessions.value.filter(s => s.session_id !== sessionId)
  } catch (error) {
    console.error('Failed to delete session:', error)
  }
}

function loadSession(session: Session) {
  // Save selected session ID to localStorage for chat page to use
  localStorage.setItem('ragdocman_current_session', session.session_id)
  router.push('/')
}

async function clearAllSessions() {
  // Clear all sessions one by one
  for (const session of sessions.value) {
    await api.clearAgentSession(session.session_id)
  }
  sessions.value = []
  localStorage.removeItem('ragdocman_current_session')
}

function formatDate(dateStr: string | null) {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  const locale = languageStore.current === 'zh' ? 'zh-CN' : 'en-US'
  return date.toLocaleDateString(locale, {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

function getPreviewText(preview: string) {
  return preview?.slice(0, 50) || languageStore.t.sessions.empty
}
</script>

<template>
  <div class="min-h-[calc(100vh-4rem)] max-w-4xl mx-auto px-4 py-8">
    <div class="flex items-center justify-between mb-6">
      <h1 class="font-title text-2xl font-bold text-light-text dark:text-dark-text flex items-center gap-2">
        <MessageSquare class="w-6 h-6" />
        {{ languageStore.t.sessions.title }}
      </h1>
      <Button v-if="sessions.length > 0" variant="ghost" size="sm" @click="clearAllSessions">
        {{ languageStore.t.sessions.clearAll }}
      </Button>
    </div>

    <!-- Loading state -->
    <div v-if="isLoading" class="flex items-center justify-center h-64">
      <Loader2 class="w-8 h-8 animate-spin text-cyan-500" />
    </div>

    <!-- Empty state -->
    <div v-else-if="sessions.length === 0" class="flex flex-col items-center justify-center h-64 text-center">
      <div class="w-16 h-16 rounded-2xl bg-gradient-to-br from-blue-500/20 to-purple-600/20 flex items-center justify-center mb-4">
        <Bot class="w-8 h-8 text-light-cta dark:text-dark-cta" />
      </div>
      <h2 class="text-xl font-title font-semibold text-light-text dark:text-dark-text mb-2">
        {{ languageStore.t.sessions.noHistory }}
      </h2>
      <p class="text-light-text/60 dark:text-dark-text/60">
        {{ languageStore.t.sessions.noHistoryDesc }}
      </p>
    </div>

    <!-- Session list -->
    <div v-else class="space-y-3">
      <Card
        v-for="session in sessions"
        :key="session.session_id"
        hoverable
        class="p-4 cursor-pointer group"
        @click="loadSession(session)"
      >
        <div class="flex items-center justify-between">
          <div class="flex-1 min-w-0">
            <div class="flex items-center gap-2 text-sm text-light-text/50 dark:text-dark-text/50 mb-1">
              <Bot class="w-4 h-4" />
              {{ formatDate(session.last_message_at) }}
              <span class="text-xs text-light-text/30 dark:text-dark-text/30">
                ({{ session.message_count }} {{ languageStore.current === 'zh' ? '条消息' : 'messages' }})
              </span>
            </div>
            <p class="text-light-text dark:text-dark-text truncate">
              {{ getPreviewText(session.preview) }}
            </p>
          </div>
          <div class="flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
            <Button variant="ghost" size="sm" @click.stop="deleteSession(session.session_id)">
              <Trash2 class="w-4 h-4" />
            </Button>
            <ChevronRight class="w-5 h-5 text-light-text/30 dark:text-dark-text/30" />
          </div>
        </div>
      </Card>
    </div>
  </div>
</template>