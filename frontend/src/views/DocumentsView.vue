<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Upload, FileText, Trash2, ArrowLeft } from 'lucide-vue-next'
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
const fileInput = ref<HTMLInputElement | null>(null)

function triggerFileInput() {
  fileInput.value?.click()
}

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
  if (!confirm(languageStore.current === 'zh' ? `Delete "${doc.name}"?` : `Delete "${doc.name}"?`)) return

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

function getFileIcon(_type: string) {
  return FileText
}
</script>

<template>
  <div class="min-h-[calc(100vh-4rem)] max-w-4xl mx-auto px-4 py-8">
    <!-- Header -->
    <div class="flex items-center gap-3 mb-6">
      <Button variant="ghost" size="sm" @click="goBack">
        <ArrowLeft class="w-4 h-4" />
      </Button>
      <div class="flex-1">
        <h1 class="text-xl font-semibold text-gray-900 dark:text-gray-100">
          {{ knowledgeBase?.name || languageStore.t.documents.title }}
        </h1>
        <p v-if="knowledgeBase?.description" class="text-sm text-gray-500 dark:text-gray-400">
          {{ knowledgeBase.description }}
        </p>
      </div>
      <label class="cursor-pointer">
        <input
          type="file"
          accept=".pdf,.docx,.doc,.md"
          class="hidden"
          @change="handleUpload"
          :disabled="uploading"
          ref="fileInput"
        />
        <button
          type="button"
          :disabled="uploading"
          class="flex items-center gap-2 px-4 py-2 bg-gray-900 dark:bg-white text-white dark:text-gray-900 rounded-lg hover:bg-gray-800 dark:hover:bg-gray-100 transition-colors disabled:opacity-50"
          @click="triggerFileInput"
        >
          <Upload class="w-4 h-4" />
          {{ uploading ? languageStore.t.documents.uploading : languageStore.t.documents.upload }}
        </button>
      </label>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="flex items-center justify-center h-32">
      <div class="animate-spin w-6 h-6 border-2 border-gray-300 border-t-gray-600 rounded-full"></div>
    </div>

    <!-- Empty -->
    <div v-else-if="documents.length === 0" class="flex flex-col items-center justify-center h-64 text-center">
      <div class="w-14 h-14 rounded-xl bg-gray-100 dark:bg-gray-800 flex items-center justify-center mb-4">
        <FileText class="w-7 h-7 text-gray-500 dark:text-gray-400" />
      </div>
      <h2 class="text-base font-semibold text-gray-900 dark:text-gray-100 mb-1">
        {{ languageStore.t.documents.noDocuments }}
      </h2>
      <p class="text-sm text-gray-500 dark:text-gray-400 mb-4">
        {{ languageStore.t.documents.noDocumentsDesc }}
      </p>
    </div>

    <!-- Document List -->
    <div v-else class="space-y-2">
      <Card
        v-for="doc in documents"
        :key="doc.id"
        hoverable
        class="p-3.5"
      >
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-3 min-w-0">
            <div class="w-9 h-9 rounded-lg bg-gray-100 dark:bg-gray-800 flex items-center justify-center flex-shrink-0">
              <component :is="getFileIcon(doc.file_type)" class="w-4 h-4 text-gray-500 dark:text-gray-400" />
            </div>
            <div class="min-w-0">
              <h3 class="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">{{ doc.name }}</h3>
              <div class="flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400">
                <span class="uppercase">{{ doc.file_type }}</span>
                <span>•</span>
                <span>{{ formatSize(doc.file_size) }}</span>
                <span>•</span>
                <span>{{ doc.chunk_count }} {{ languageStore.t.documents.chunks }}</span>
              </div>
            </div>
          </div>
          <div class="flex items-center gap-3">
            <span class="text-xs text-gray-400 dark:text-gray-500">
              {{ formatDate(doc.created_at) }}
            </span>
            <Button variant="ghost" size="sm" @click="deleteDocument(doc)">
              <Trash2 class="w-3.5 h-3.5" />
            </Button>
          </div>
        </div>
      </Card>
    </div>
  </div>
</template>