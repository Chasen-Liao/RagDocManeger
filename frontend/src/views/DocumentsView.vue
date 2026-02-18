<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Upload, FileText, Trash2, ArrowLeft, Loader2 } from 'lucide-vue-next'
import { api, type Document, type KnowledgeBase } from '@/api/client'
import { useLanguageStore } from '@/stores/language'
import Card from '@/components/ui/Card.vue'
import Button from '@/components/ui/Button.vue'

const languageStore = useLanguageStore()
const route = useRoute()
const router = useRouter()
const kbId = route.params.kbId as string

const documents = ref<Document[]>([])
const knowledgeBase = ref<KnowledgeBase | null>(null)
const loading = ref(false)
const uploading = ref(false)

onMounted(async () => {
  await Promise.all([loadKnowledgeBase(), loadDocuments()])
})

async function loadKnowledgeBase() {
  const res = await api.getKnowledgeBase(kbId)
  if (res.success && res.data) {
    knowledgeBase.value = res.data
  }
}

async function loadDocuments() {
  loading.value = true
  try {
    const res = await api.getDocuments(kbId)
    if (res.success && res.data) {
      documents.value = res.data
    }
  } finally {
    loading.value = false
  }
}

async function handleUpload(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return

  uploading.value = true
  try {
    const res = await api.uploadDocument(kbId, file)
    if (res.success && res.data) {
      documents.value.unshift(res.data)
    }
  } finally {
    uploading.value = false
    input.value = ''
  }
}

async function deleteDocument(doc: Document) {
  if (!confirm(languageStore.current === 'zh' ? `删除 "${doc.name}"？` : `Delete "${doc.name}"?`)) return

  const res = await api.deleteDocument(kbId, doc.id)
  if (res.success) {
    documents.value = documents.value.filter(d => d.id !== doc.id)
  }
}

function goBack() {
  router.push('/knowledge-bases')
}

function formatSize(bytes: number) {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

function formatDate(dateStr: string) {
  const locale = languageStore.current === 'zh' ? 'zh-CN' : 'en-US'
  return new Date(dateStr).toLocaleDateString(locale, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

function getFileIcon(type: string) {
  return FileText
}
</script>

<template>
  <div class="min-h-[calc(100vh-4rem)] max-w-5xl mx-auto px-4 py-8">
    <!-- Header -->
    <div class="flex items-center gap-4 mb-6">
      <Button variant="ghost" size="sm" @click="goBack">
        <ArrowLeft class="w-4 h-4" />
      </Button>
      <div class="flex-1">
        <h1 class="font-title text-2xl font-bold text-light-text dark:text-dark-text">
          {{ knowledgeBase?.name || languageStore.t.documents.title }}
        </h1>
        <p v-if="knowledgeBase?.description" class="text-sm text-light-text/60 dark:text-dark-text/60">
          {{ knowledgeBase.description }}
        </p>
      </div>
      <label class="cursor-pointer">
        <input type="file" accept=".pdf,.docx,.doc,.md" class="hidden" @change="handleUpload" :disabled="uploading" />
        <Button :loading="uploading">
          <Upload class="w-4 h-4" />
          {{ languageStore.t.documents.upload }}
        </Button>
      </label>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="flex items-center justify-center h-32">
      <div class="animate-spin w-8 h-8 border-2 border-light-cta border-t-transparent rounded-full"></div>
    </div>

    <!-- Empty -->
    <div v-else-if="documents.length === 0" class="flex flex-col items-center justify-center h-64 text-center">
      <div class="w-16 h-16 rounded-2xl bg-gradient-to-br from-blue-500/20 to-purple-600/20 flex items-center justify-center mb-4">
        <FileText class="w-8 h-8 text-light-cta dark:text-dark-cta" />
      </div>
      <h2 class="text-xl font-title font-semibold text-light-text dark:text-dark-text mb-2">
        {{ languageStore.t.documents.noDocuments }}
      </h2>
      <p class="text-light-text/60 dark:text-dark-text/60 mb-4">
        {{ languageStore.t.documents.noDocumentsDesc }}
      </p>
    </div>

    <!-- Document List -->
    <div v-else class="space-y-3">
      <Card
        v-for="doc in documents"
        :key="doc.id"
        class="p-4"
      >
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-4 min-w-0">
            <div class="w-10 h-10 rounded-lg bg-light-cta/10 dark:bg-dark-cta/10 flex items-center justify-center flex-shrink-0">
              <component :is="getFileIcon(doc.file_type)" class="w-5 h-5 text-light-cta dark:text-dark-cta" />
            </div>
            <div class="min-w-0">
              <h3 class="font-medium text-light-text dark:text-dark-text truncate">{{ doc.name }}</h3>
              <div class="flex items-center gap-3 text-sm text-light-text/50 dark:text-dark-text/50">
                <span>{{ doc.file_type.toUpperCase() }}</span>
                <span>{{ formatSize(doc.file_size) }}</span>
                <span>{{ doc.chunk_count }} {{ languageStore.t.documents.chunks }}</span>
              </div>
            </div>
          </div>
          <div class="flex items-center gap-2">
            <span class="text-sm text-light-text/50 dark:text-dark-text/50">
              {{ formatDate(doc.created_at) }}
            </span>
            <Button variant="ghost" size="sm" @click="deleteDocument(doc)">
              <Trash2 class="w-4 h-4" />
            </Button>
          </div>
        </div>
      </Card>
    </div>
  </div>
</template>