<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { Settings, Save, Loader2, Info } from 'lucide-vue-next'
import { api, type Config } from '@/api/client'
import { useLanguageStore } from '@/stores/language'
import Card from '@/components/ui/Card.vue'
import Button from '@/components/ui/Button.vue'

const languageStore = useLanguageStore()

const config = ref<Config | null>(null)
const loading = ref(false)
const saving = ref(false)

const editableFields = ref({
  debug: false,
  log_level: 'INFO',
  chunk_size: 1000,
  chunk_overlap: 200,
  retrieval_top_k: 10,
  reranking_top_k: 5
})

onMounted(async () => {
  await loadConfig()
})

async function loadConfig() {
  loading.value = true
  try {
    const res = await api.getConfig()
    if (res.success && res.data) {
      config.value = res.data
      editableFields.value = {
        debug: res.data.debug,
        log_level: res.data.log_level,
        chunk_size: res.data.chunk_size,
        chunk_overlap: res.data.chunk_overlap,
        retrieval_top_k: res.data.retrieval_top_k,
        reranking_top_k: res.data.reranking_top_k
      }
    }
  } finally {
    loading.value = false
  }
}

async function saveConfig() {
  saving.value = true
  try {
    const res = await api.updateConfig(editableFields.value)
    if (res.success && res.data) {
      config.value = res.data
    }
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div class="min-h-[calc(100vh-4rem)] max-w-3xl mx-auto px-4 py-8">
    <div class="flex items-center justify-between mb-6">
      <h1 class="font-title text-2xl font-bold text-light-text dark:text-dark-text flex items-center gap-2">
        <Settings class="w-6 h-6" />
        {{ languageStore.t.settings.title }}
      </h1>
      <Button :loading="saving" @click="saveConfig">
        <Save class="w-4 h-4" />
        {{ languageStore.t.settings.save }}
      </Button>
    </div>

    <div v-if="loading" class="flex items-center justify-center h-32">
      <div class="animate-spin w-8 h-8 border-2 border-light-cta border-t-transparent rounded-full"></div>
    </div>

    <div v-else-if="config" class="space-y-6">
      <!-- App Info -->
      <Card class="p-6">
        <h2 class="font-title font-semibold text-lg text-light-text dark:text-dark-text mb-4">{{ languageStore.t.settings.application }}</h2>
        <div class="grid grid-cols-2 gap-4">
          <div>
            <span class="text-sm text-light-text/50 dark:text-dark-text/50">{{ languageStore.t.settings.appName }}</span>
            <p class="text-light-text dark:text-dark-text">{{ config.app_name }}</p>
          </div>
          <div>
            <span class="text-sm text-light-text/50 dark:text-dark-text/50">{{ languageStore.t.settings.version }}</span>
            <p class="text-light-text dark:text-dark-text">{{ config.app_version }}</p>
          </div>
        </div>
      </Card>

      <!-- Debug Settings -->
      <Card class="p-6">
        <h2 class="font-title font-semibold text-lg text-light-text dark:text-dark-text mb-4">{{ languageStore.t.settings.debug }}</h2>
        <div class="space-y-4">
          <div class="flex items-center justify-between">
            <div>
              <p class="text-light-text dark:text-dark-text">{{ languageStore.t.settings.debugMode }}</p>
              <p class="text-sm text-light-text/50 dark:text-dark-text/50">{{ languageStore.t.settings.debugModeDesc }}</p>
            </div>
            <label class="relative inline-flex items-center cursor-pointer">
              <input type="checkbox" v-model="editableFields.debug" class="sr-only peer" />
              <div class="w-11 h-6 bg-light-border dark:bg-dark-border peer-focus:ring-2 peer-focus:ring-light-cta/50 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-light-cta peer-checked:dark:bg-dark-cta"></div>
            </label>
          </div>

          <div>
            <label class="block text-sm font-medium text-light-text dark:text-dark-text mb-1">{{ languageStore.t.settings.logLevel }}</label>
            <select
              v-model="editableFields.log_level"
              class="w-full px-3 py-2 rounded-lg border border-light-border dark:border-dark-border bg-light-card dark:bg-dark-card text-light-text dark:text-dark-text focus:outline-none focus:ring-2 focus:ring-light-cta/50"
            >
              <option value="DEBUG">DEBUG</option>
              <option value="INFO">INFO</option>
              <option value="WARNING">WARNING</option>
              <option value="ERROR">ERROR</option>
            </select>
          </div>
        </div>
      </Card>

      <!-- RAG Settings -->
      <Card class="p-6">
        <h2 class="font-title font-semibold text-lg text-light-text dark:text-dark-text mb-4 flex items-center gap-2">
          {{ languageStore.t.settings.ragConfig }}
          <span class="text-xs px-2 py-0.5 rounded-full bg-light-cta/10 dark:bg-dark-cta/10 text-light-cta dark:text-dark-cta">{{ languageStore.t.settings.editable }}</span>
        </h2>
        <div class="space-y-4">
          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="block text-sm font-medium text-light-text dark:text-dark-text mb-1">{{ languageStore.t.settings.chunkSize }}</label>
              <input
                type="number"
                v-model.number="editableFields.chunk_size"
                class="w-full px-3 py-2 rounded-lg border border-light-border dark:border-dark-border bg-light-card dark:bg-dark-card text-light-text dark:text-dark-text focus:outline-none focus:ring-2 focus:ring-light-cta/50"
                min="100"
                max="5000"
              />
            </div>
            <div>
              <label class="block text-sm font-medium text-light-text dark:text-dark-text mb-1">{{ languageStore.t.settings.chunkOverlap }}</label>
              <input
                type="number"
                v-model.number="editableFields.chunk_overlap"
                class="w-full px-3 py-2 rounded-lg border border-light-border dark:border-dark-border bg-light-card dark:bg-dark-card text-light-text dark:text-dark-text focus:outline-none focus:ring-2 focus:ring-light-cta/50"
                min="0"
                max="1000"
              />
            </div>
            <div>
              <label class="block text-sm font-medium text-light-text dark:text-dark-text mb-1">{{ languageStore.t.settings.retrievalTopK }}</label>
              <input
                type="number"
                v-model.number="editableFields.retrieval_top_k"
                class="w-full px-3 py-2 rounded-lg border border-light-border dark:border-dark-border bg-light-card dark:bg-dark-card text-light-text dark:text-dark-text focus:outline-none focus:ring-2 focus:ring-light-cta/50"
                min="1"
                max="100"
              />
            </div>
            <div>
              <label class="block text-sm font-medium text-light-text dark:text-dark-text mb-1">{{ languageStore.t.settings.rerankingTopK }}</label>
              <input
                type="number"
                v-model.number="editableFields.reranking_top_k"
                class="w-full px-3 py-2 rounded-lg border border-light-border dark:border-dark-border bg-light-card dark:bg-dark-card text-light-text dark:text-dark-text focus:outline-none focus:ring-2 focus:ring-light-cta/50"
                min="1"
                max="50"
              />
            </div>
          </div>
        </div>
      </Card>

      <!-- Model Info (Read-only) -->
      <Card class="p-6">
        <h2 class="font-title font-semibold text-lg text-light-text dark:text-dark-text mb-4">{{ languageStore.t.settings.models }}</h2>
        <div class="space-y-3">
          <div class="flex justify-between py-2 border-b border-light-border dark:border-dark-border">
            <span class="text-light-text/60 dark:text-dark-text/60">{{ languageStore.t.settings.llmProvider }}</span>
            <span class="text-light-text dark:text-dark-text">{{ config.llm_provider }}</span>
          </div>
          <div class="flex justify-between py-2 border-b border-light-border dark:border-dark-border">
            <span class="text-light-text/60 dark:text-dark-text/60">{{ languageStore.t.settings.embeddingProvider }}</span>
            <span class="text-light-text dark:text-dark-text">{{ config.embedding_provider }}</span>
          </div>
          <div class="flex justify-between py-2 border-b border-light-border dark:border-dark-border">
            <span class="text-light-text/60 dark:text-dark-text/60">{{ languageStore.t.settings.embeddingModel }}</span>
            <span class="text-light-text dark:text-dark-text">{{ config.embedding_model }}</span>
          </div>
          <div class="flex justify-between py-2">
            <span class="text-light-text/60 dark:text-dark-text/60">{{ languageStore.t.settings.rerankerModel }}</span>
            <span class="text-light-text dark:text-dark-text">{{ config.reranker_model }}</span>
          </div>
        </div>
      </Card>

      <!-- File Settings -->
      <Card class="p-6">
        <h2 class="font-title font-semibold text-lg text-light-text dark:text-dark-text mb-4">{{ languageStore.t.settings.fileUpload }}</h2>
        <div class="flex justify-between py-2 border-b border-light-border dark:border-dark-border">
          <span class="text-light-text/60 dark:text-dark-text/60">{{ languageStore.t.settings.maxFileSize }}</span>
          <span class="text-light-text dark:text-dark-text">{{ config.max_file_size_mb }} MB</span>
        </div>
        <div class="flex justify-between py-2">
          <span class="text-light-text/60 dark:text-dark-text/60">{{ languageStore.t.settings.supportedTypes }}</span>
          <span class="text-light-text dark:text-dark-text">{{ config.supported_file_types.join(', ') }}</span>
        </div>
      </Card>
    </div>
  </div>
</template>