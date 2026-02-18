<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Plus, BookOpen, FileText, Trash2, Edit2, FolderOpen, Upload, Loader2 } from 'lucide-vue-next'
import { api, type KnowledgeBase } from '@/api/client'
import { useLanguageStore } from '@/stores/language'
import Card from '@/components/ui/Card.vue'
import Button from '@/components/ui/Button.vue'
import Input from '@/components/ui/Input.vue'
import Modal from '@/components/ui/Modal.vue'

const languageStore = useLanguageStore()
const router = useRouter()

const knowledgeBases = ref<KnowledgeBase[]>([])
const loading = ref(false)
const showCreateModal = ref(false)
const showEditModal = ref(false)
const showDeleteModal = ref(false)
const editingKb = ref<KnowledgeBase | null>(null)
const newKb = ref({ name: '', description: '' })
const uploadingKbId = ref<string | null>(null)

onMounted(async () => {
  await loadKnowledgeBases()
})

async function loadKnowledgeBases() {
  loading.value = true
  try {
    const res = await api.getKnowledgeBases()
    if (res.success && res.data) {
      knowledgeBases.value = res.data
    }
  } finally {
    loading.value = false
  }
}

async function createKnowledgeBase() {
  if (!newKb.value.name.trim()) return

  const res = await api.createKnowledgeBase({
    name: newKb.value.name.trim(),
    description: newKb.value.description.trim()
  })

  if (res.success && res.data) {
    knowledgeBases.value.unshift(res.data)
    showCreateModal.value = false
    newKb.value = { name: '', description: '' }
  }
}

async function updateKnowledgeBase() {
  if (!editingKb.value || !newKb.value.name.trim()) return

  const res = await api.updateKnowledgeBase(editingKb.value.id, {
    name: newKb.value.name.trim(),
    description: newKb.value.description.trim()
  })

  if (res.success && res.data) {
    const index = knowledgeBases.value.findIndex(kb => kb.id === editingKb.value!.id)
    if (index >= 0) {
      knowledgeBases.value[index] = res.data
    }
    showEditModal.value = false
    editingKb.value = null
    newKb.value = { name: '', description: '' }
  }
}

async function deleteKnowledgeBase() {
  if (!editingKb.value) return

  const res = await api.deleteKnowledgeBase(editingKb.value.id)
  if (res.success) {
    knowledgeBases.value = knowledgeBases.value.filter(kb => kb.id !== editingKb.value!.id)
    showDeleteModal.value = false
    editingKb.value = null
  }
}

function openEdit(kb: KnowledgeBase) {
  editingKb.value = kb
  newKb.value = { name: kb.name, description: kb.description }
  showEditModal.value = true
}

function openDelete(kb: KnowledgeBase) {
  editingKb.value = kb
  showDeleteModal.value = true
}

function viewDocuments(kb: KnowledgeBase) {
  router.push(`/documents/${kb.id}`)
}

function formatSize(bytes: number) {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

async function handleUpload(event: Event, kb: KnowledgeBase) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return

  uploadingKbId.value = kb.id
  try {
    const res = await api.uploadDocument(kb.id, file)
    if (res.success && res.data) {
      // Refresh the knowledge base to get updated document count
      const kbRes = await api.getKnowledgeBase(kb.id)
      if (kbRes.success && kbRes.data) {
        const index = knowledgeBases.value.findIndex(k => k.id === kb.id)
        if (index >= 0) {
          knowledgeBases.value[index] = kbRes.data
        }
      }
    }
  } finally {
    uploadingKbId.value = null
    input.value = ''
  }
}
</script>

<template>
  <div class="min-h-[calc(100vh-4rem)] max-w-5xl mx-auto px-4 py-8">
    <div class="flex items-center justify-between mb-6">
      <h1 class="font-title text-2xl font-bold text-light-text dark:text-dark-text flex items-center gap-2">
        <BookOpen class="w-6 h-6" />
        {{ languageStore.t.knowledgeBases.title }}
      </h1>
      <Button @click="showCreateModal = true">
        <Plus class="w-4 h-4" />
        {{ languageStore.t.knowledgeBases.create }}
      </Button>
    </div>

    <div v-if="loading" class="flex items-center justify-center h-32">
      <div class="animate-spin w-8 h-8 border-2 border-light-cta border-t-transparent rounded-full"></div>
    </div>

    <div v-else-if="knowledgeBases.length === 0" class="flex flex-col items-center justify-center h-64 text-center">
      <div class="w-16 h-16 rounded-2xl bg-gradient-to-br from-blue-500/20 to-purple-600/20 flex items-center justify-center mb-4">
        <FolderOpen class="w-8 h-8 text-light-cta dark:text-dark-cta" />
      </div>
      <h2 class="text-xl font-title font-semibold text-light-text dark:text-dark-text mb-2">
        {{ languageStore.t.knowledgeBases.noKnowledgeBases }}
      </h2>
      <p class="text-light-text/60 dark:text-dark-text/60 mb-4">
        {{ languageStore.t.knowledgeBases.noKnowledgeBasesDesc }}
      </p>
      <Button @click="showCreateModal = true">
        <Plus class="w-4 h-4" />
        {{ languageStore.t.knowledgeBases.createKnowledgeBase }}
      </Button>
    </div>

    <div v-else class="grid grid-cols-1 md:grid-cols-2 gap-4">
      <Card
        v-for="kb in knowledgeBases"
        :key="kb.id"
        hoverable
        class="p-5"
      >
        <div class="flex items-start justify-between mb-3">
          <div class="flex-1 min-w-0">
            <h3 class="font-title font-semibold text-lg text-light-text dark:text-dark-text truncate">
              {{ kb.name }}
            </h3>
            <p class="text-sm text-light-text/60 dark:text-dark-text/60 line-clamp-2 mt-1">
              {{ kb.description || languageStore.t.knowledgeBases.noDescription }}
            </p>
          </div>
          <div class="flex items-center gap-1 ml-2">
            <Button variant="ghost" size="sm" @click="openEdit(kb)">
              <Edit2 class="w-4 h-4" />
            </Button>
            <Button variant="ghost" size="sm" @click="openDelete(kb)">
              <Trash2 class="w-4 h-4" />
            </Button>
          </div>
        </div>

        <div class="flex items-center gap-4 text-sm text-light-text/50 dark:text-dark-text/50 mb-4">
          <div class="flex items-center gap-1">
            <FileText class="w-4 h-4" />
            {{ kb.document_count }} {{ languageStore.t.knowledgeBases.docs }}
          </div>
          <div>{{ formatSize(kb.total_size) }}</div>
        </div>

        <div class="flex gap-2">
          <div class="flex-1 relative">
            <input
              :id="'upload-' + kb.id"
              type="file"
              accept=".pdf,.docx,.doc,.md,.txt"
              class="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
              @change="(e) => handleUpload(e, kb)"
              :disabled="uploadingKbId === kb.id"
            />
            <Button
              variant="primary"
              class="w-full"
              :loading="uploadingKbId === kb.id"
            >
              <Upload class="w-4 h-4" />
              {{ languageStore.t.documents.upload }}
            </Button>
          </div>
          <Button variant="secondary" @click="viewDocuments(kb)">
            <FolderOpen class="w-4 h-4" />
          </Button>
        </div>
      </Card>
    </div>

    <!-- Create Modal -->
    <Modal v-model:open="showCreateModal" :title="languageStore.t.knowledgeBases.createKnowledgeBase">
      <div class="space-y-4">
        <div>
          <label class="block text-sm font-medium text-light-text dark:text-dark-text mb-1">{{ languageStore.t.knowledgeBases.name }}</label>
          <Input v-model="newKb.name" :placeholder="languageStore.t.knowledgeBases.name" />
        </div>
        <div>
          <label class="block text-sm font-medium text-light-text dark:text-dark-text mb-1">{{ languageStore.t.knowledgeBases.description }}</label>
          <textarea
            v-model="newKb.description"
            :placeholder="languageStore.t.knowledgeBases.description"
            rows="3"
            class="w-full px-4 py-2.5 rounded-lg border border-light-border dark:border-dark-border bg-light-card dark:bg-dark-card text-light-text dark:text-dark-text placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-light-cta/50"
          ></textarea>
        </div>
      </div>
      <div class="flex justify-end gap-3 mt-6">
        <Button variant="secondary" @click="showCreateModal = false">{{ languageStore.t.knowledgeBases.cancel }}</Button>
        <Button :disabled="!newKb.name.trim()" @click="createKnowledgeBase">{{ languageStore.t.knowledgeBases.create }}</Button>
      </div>
    </Modal>

    <!-- Edit Modal -->
    <Modal v-model:open="showEditModal" :title="languageStore.t.knowledgeBases.title">
      <div class="space-y-4">
        <div>
          <label class="block text-sm font-medium text-light-text dark:text-dark-text mb-1">{{ languageStore.t.knowledgeBases.name }}</label>
          <Input v-model="newKb.name" :placeholder="languageStore.t.knowledgeBases.name" />
        </div>
        <div>
          <label class="block text-sm font-medium text-light-text dark:text-dark-text mb-1">{{ languageStore.t.knowledgeBases.description }}</label>
          <textarea
            v-model="newKb.description"
            :placeholder="languageStore.t.knowledgeBases.description"
            rows="3"
            class="w-full px-4 py-2.5 rounded-lg border border-light-border dark:border-dark-border bg-light-card dark:bg-dark-card text-light-text dark:text-dark-text placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-light-cta/50"
          ></textarea>
        </div>
      </div>
      <div class="flex justify-end gap-3 mt-6">
        <Button variant="secondary" @click="showEditModal = false">{{ languageStore.t.knowledgeBases.cancel }}</Button>
        <Button :disabled="!newKb.name.trim()" @click="updateKnowledgeBase">{{ languageStore.t.knowledgeBases.save }}</Button>
      </div>
    </Modal>

    <!-- Delete Modal -->
    <Modal v-model:open="showDeleteModal" :title="languageStore.t.knowledgeBases.delete" size="sm">
      <p class="text-light-text/70 dark:text-dark-text/70">
        {{ languageStore.t.knowledgeBases.deleteConfirm.replace('{name}', editingKb?.name || '') }}
      </p>
      <div class="flex justify-end gap-3 mt-6">
        <Button variant="secondary" @click="showDeleteModal = false">{{ languageStore.t.knowledgeBases.cancel }}</Button>
        <Button variant="danger" @click="deleteKnowledgeBase">{{ languageStore.t.knowledgeBases.delete }}</Button>
      </div>
    </Modal>
  </div>
</template>