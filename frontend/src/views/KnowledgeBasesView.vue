<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Plus, BookOpen, FileText, Trash2, Edit2, FolderOpen, Upload } from 'lucide-vue-next'
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
  <div class="min-h-[calc(100vh-3.5rem)] max-w-4xl mx-auto px-4 py-6">
    <div class="flex items-center justify-between mb-5">
      <h1 class="text-lg font-medium text-gray-900 dark:text-gray-100 flex items-center gap-2">
        <BookOpen class="w-4 h-4" />
        {{ languageStore.t.knowledgeBases.title }}
      </h1>
      <Button @click="showCreateModal = true">
        <Plus class="w-3.5 h-3.5" />
        {{ languageStore.t.knowledgeBases.create }}
      </Button>
    </div>

    <div v-if="loading" class="flex items-center justify-center h-32">
      <div class="animate-spin w-5 h-5 border-2 border-gray-300 border-t-gray-600 rounded-full"></div>
    </div>

    <div v-else-if="knowledgeBases.length === 0" class="flex flex-col items-center justify-center h-56 text-center">
      <div class="w-12 h-12 rounded-xl bg-gray-100 dark:bg-gray-800 flex items-center justify-center mb-3">
        <FolderOpen class="w-5 h-5 text-gray-500 dark:text-gray-400" />
      </div>
      <h2 class="text-sm font-medium text-gray-900 dark:text-gray-100 mb-1">
        {{ languageStore.t.knowledgeBases.noKnowledgeBases }}
      </h2>
      <p class="text-[13px] text-gray-500 dark:text-gray-400 mb-4">
        {{ languageStore.t.knowledgeBases.noKnowledgeBasesDesc }}
      </p>
      <Button @click="showCreateModal = true">
        <Plus class="w-3.5 h-3.5" />
        {{ languageStore.t.knowledgeBases.createKnowledgeBase }}
      </Button>
    </div>

    <div v-else class="grid grid-cols-1 md:grid-cols-2 gap-3">
      <Card
        v-for="kb in knowledgeBases"
        :key="kb.id"
        hoverable
        class="p-3.5"
      >
        <div class="flex items-start justify-between mb-2">
          <div class="flex-1 min-w-0">
            <h3 class="font-medium text-gray-900 dark:text-gray-100 text-[14px] truncate">
              {{ kb.name }}
            </h3>
            <p class="text-[12px] text-gray-500 dark:text-gray-400 line-clamp-2 mt-0.5">
              {{ kb.description || languageStore.t.knowledgeBases.noDescription }}
            </p>
          </div>
          <div class="flex items-center gap-0.5 ml-2">
            <Button variant="ghost" size="sm" @click="openEdit(kb)">
              <Edit2 class="w-3.5 h-3.5" />
            </Button>
            <Button variant="ghost" size="sm" @click="openDelete(kb)">
              <Trash2 class="w-3.5 h-3.5" />
            </Button>
          </div>
        </div>

        <div class="flex items-center gap-3 text-[11px] text-gray-500 dark:text-gray-400 mb-3">
          <div class="flex items-center gap-1">
            <FileText class="w-3 h-3" />
            {{ kb.document_count }} {{ languageStore.t.knowledgeBases.docs }}
          </div>
          <div>{{ formatSize(kb.total_size) }}</div>
        </div>

        <div class="flex gap-1.5">
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
              variant="secondary"
              class="w-full"
              :loading="uploadingKbId === kb.id"
            >
              <Upload class="w-3.5 h-3.5" />
              {{ languageStore.t.documents.upload }}
            </Button>
          </div>
          <Button variant="secondary" @click="viewDocuments(kb)">
            <FolderOpen class="w-3.5 h-3.5" />
          </Button>
        </div>
      </Card>
    </div>

    <!-- Create Modal -->
    <Modal v-model:open="showCreateModal" :title="languageStore.t.knowledgeBases.createKnowledgeBase">
      <div class="space-y-3">
        <div>
          <label class="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">{{ languageStore.t.knowledgeBases.name }}</label>
          <Input v-model="newKb.name" :placeholder="languageStore.t.knowledgeBases.name" />
        </div>
        <div>
          <label class="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">{{ languageStore.t.knowledgeBases.description }}</label>
          <textarea
            v-model="newKb.description"
            :placeholder="languageStore.t.knowledgeBases.description"
            rows="3"
            class="w-full px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 placeholder:text-gray-400 text-[13px] focus:outline-none focus:ring-1 focus:ring-gray-400"
          ></textarea>
        </div>
      </div>
      <div class="flex justify-end gap-1.5 mt-4">
        <Button variant="secondary" @click="showCreateModal = false">{{ languageStore.t.knowledgeBases.cancel }}</Button>
        <Button :disabled="!newKb.name.trim()" @click="createKnowledgeBase">{{ languageStore.t.knowledgeBases.create }}</Button>
      </div>
    </Modal>

    <!-- Edit Modal -->
    <Modal v-model:open="showEditModal" :title="languageStore.t.knowledgeBases.title">
      <div class="space-y-3">
        <div>
          <label class="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">{{ languageStore.t.knowledgeBases.name }}</label>
          <Input v-model="newKb.name" :placeholder="languageStore.t.knowledgeBases.name" />
        </div>
        <div>
          <label class="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">{{ languageStore.t.knowledgeBases.description }}</label>
          <textarea
            v-model="newKb.description"
            :placeholder="languageStore.t.knowledgeBases.description"
            rows="3"
            class="w-full px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 placeholder:text-gray-400 text-[13px] focus:outline-none focus:ring-1 focus:ring-gray-400"
          ></textarea>
        </div>
      </div>
      <div class="flex justify-end gap-1.5 mt-4">
        <Button variant="secondary" @click="showEditModal = false">{{ languageStore.t.knowledgeBases.cancel }}</Button>
        <Button :disabled="!newKb.name.trim()" @click="updateKnowledgeBase">{{ languageStore.t.knowledgeBases.save }}</Button>
      </div>
    </Modal>

    <!-- Delete Modal -->
    <Modal v-model:open="showDeleteModal" :title="languageStore.t.knowledgeBases.delete" size="sm">
      <p class="text-[13px] text-gray-600 dark:text-gray-400">
        {{ languageStore.t.knowledgeBases.deleteConfirm.replace('{name}', editingKb?.name || '') }}
      </p>
      <div class="flex justify-end gap-1.5 mt-4">
        <Button variant="secondary" @click="showDeleteModal = false">{{ languageStore.t.knowledgeBases.cancel }}</Button>
        <Button variant="danger" @click="deleteKnowledgeBase">{{ languageStore.t.knowledgeBases.delete }}</Button>
      </div>
    </Modal>
  </div>
</template>