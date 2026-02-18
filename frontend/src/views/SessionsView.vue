<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { MessageSquare, Trash2, ChevronRight, Bot } from 'lucide-vue-next'
import { useLanguageStore } from '@/stores/language'
import Card from '@/components/ui/Card.vue'
import Button from '@/components/ui/Button.vue'

const languageStore = useLanguageStore()
const router = useRouter()

interface Session {
  id: string
  kbId: string
  messages: { role: string; content: string }[]
  createdAt: string
}

const sessions = ref<Session[]>([])
const selectedSession = ref<Session | null>(null)

onMounted(() => {
  loadSessions()
})

function loadSessions() {
  const saved = localStorage.getItem('ragdocman_sessions')
  if (saved) {
    try {
      sessions.value = JSON.parse(saved)
    } catch {
      sessions.value = []
    }
  }
}

function deleteSession(id: string) {
  sessions.value = sessions.value.filter(s => s.id !== id)
  localStorage.setItem('ragdocman_sessions', JSON.stringify(sessions.value))
}

function loadSession(session: Session) {
  // Save current session first
  const current = localStorage.getItem('ragdocman_current')
  if (current) {
    try {
      const currentSession = JSON.parse(current)
      const allSessions = localStorage.getItem('ragdocman_sessions')
      if (allSessions) {
        const sessionList = JSON.parse(allSessions)
        const index = sessionList.findIndex((s: Session) => s.id === currentSession.id)
        if (index >= 0) {
          sessionList[index] = currentSession
          localStorage.setItem('ragdocman_sessions', JSON.stringify(sessionList))
        }
      }
    } catch {
      // Ignore
    }
  }

  // Load selected session
  selectedSession.value = session
  localStorage.setItem('ragdocman_current', JSON.stringify(session))
  router.push('/')
}

function clearAllSessions() {
  sessions.value = []
  localStorage.removeItem('ragdocman_sessions')
  localStorage.removeItem('ragdocman_current')
}

function formatDate(dateStr: string) {
  const date = new Date(dateStr)
  const locale = languageStore.current === 'zh' ? 'zh-CN' : 'en-US'
  return date.toLocaleDateString(locale, {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

function getPreview(messages: { role: string; content: string }[]) {
  const firstUser = messages.find(m => m.role === 'user')
  return firstUser?.content?.slice(0, 50) || languageStore.t.sessions.empty
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

    <div v-if="sessions.length === 0" class="flex flex-col items-center justify-center h-64 text-center">
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

    <div v-else class="space-y-3">
      <Card
        v-for="session in sessions"
        :key="session.id"
        hoverable
        class="p-4 cursor-pointer group"
        @click="loadSession(session)"
      >
        <div class="flex items-center justify-between">
          <div class="flex-1 min-w-0">
            <div class="flex items-center gap-2 text-sm text-light-text/50 dark:text-dark-text/50 mb-1">
              <Bot class="w-4 h-4" />
              {{ formatDate(session.createdAt) }}
            </div>
            <p class="text-light-text dark:text-dark-text truncate">
              {{ getPreview(session.messages) }}
            </p>
          </div>
          <div class="flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
            <Button variant="ghost" size="sm" @click.stop="deleteSession(session.id)">
              <Trash2 class="w-4 h-4" />
            </Button>
            <ChevronRight class="w-5 h-5 text-light-text/30 dark:text-dark-text/30" />
          </div>
        </div>
      </Card>
    </div>
  </div>
</template>