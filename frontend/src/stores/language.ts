import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export type Language = 'zh' | 'en'

const translations = {
  zh: {
    nav: {
      chat: '对话',
      sessions: '会话',
      knowledgeBases: '知识库',
      settings: '设置'
    },
    chat: {
      title: '对话',
      newChat: '新对话',
      selectKb: '选择知识库',
      placeholder: '输入您的问题...',
      thinking: '正在思考...',
      sources: '参考来源',
      welcome: '欢迎使用 RagDocMan',
      welcomeDesc: '请选择一个知识库，然后开始提问。AI 将根据知识库中的文档内容为您提供答案。'
    },
    sessions: {
      title: '会话历史',
      clearAll: '清空全部',
      noHistory: '暂无历史',
      noHistoryDesc: '开始一个新对话即可在此显示。',
      empty: '空对话'
    },
    knowledgeBases: {
      title: '知识库',
      create: '创建',
      name: '名称',
      description: '描述',
      docs: '文档',
      manageDocs: '管理文档',
      delete: '删除',
      cancel: '取消',
      save: '保存',
      deleteConfirm: '确定要删除知识库 "{name}" 吗？这将同时删除所有文档，且无法恢复。',
      noKnowledgeBases: '暂无知识库',
      noKnowledgeBasesDesc: '创建您的第一个知识库来开始管理文档。',
      createKnowledgeBase: '创建知识库',
      noDescription: '暂无描述'
    },
    documents: {
      title: '文档',
      upload: '上传',
      delete: '删除',
      noDocuments: '暂无文档',
      noDocumentsDesc: '上传您的第一个文档来构建知识库。',
      chunks: '块'
    },
    settings: {
      title: '设置',
      save: '保存',
      application: '应用信息',
      appName: '名称',
      version: '版本',
      debug: '调试',
      debugMode: '调试模式',
      debugModeDesc: '启用详细日志',
      logLevel: '日志级别',
      ragConfig: 'RAG 配置',
      editable: '可编辑',
      chunkSize: '文本块大小',
      chunkOverlap: '块重叠大小',
      retrievalTopK: '检索 Top K',
      rerankingTopK: '重排序 Top K',
      models: '模型',
      llmProvider: 'LLM 提供商',
      embeddingProvider: '嵌入模型提供商',
      embeddingModel: '嵌入模型',
      rerankerModel: '重排序模型',
      fileUpload: '文件上传',
      maxFileSize: '最大文件大小',
      supportedTypes: '支持的文件类型'
    }
  },
  en: {
    nav: {
      chat: 'Chat',
      sessions: 'Sessions',
      knowledgeBases: 'Knowledge Bases',
      settings: 'Settings'
    },
    chat: {
      title: 'Chat',
      newChat: 'New Chat',
      selectKb: 'Select Knowledge Base',
      placeholder: 'Enter your question...',
      thinking: 'Thinking...',
      sources: 'Sources',
      welcome: 'Welcome to RagDocMan',
      welcomeDesc: 'Select a knowledge base and start asking questions. AI will answer based on your documents.'
    },
    sessions: {
      title: 'History',
      clearAll: 'Clear All',
      noHistory: 'No History',
      noHistoryDesc: 'Start a new conversation to see it here.',
      empty: 'Empty conversation'
    },
    knowledgeBases: {
      title: 'Knowledge Bases',
      create: 'Create',
      name: 'Name',
      description: 'Description',
      docs: 'docs',
      manageDocs: 'Manage Documents',
      delete: 'Delete',
      cancel: 'Cancel',
      save: 'Save',
      deleteConfirm: 'Are you sure you want to delete "{name}"? This will also delete all documents and cannot be undone.',
      noKnowledgeBases: 'No Knowledge Bases',
      noKnowledgeBasesDesc: 'Create your first knowledge base to start managing documents.',
      createKnowledgeBase: 'Create Knowledge Base',
      noDescription: 'No description'
    },
    documents: {
      title: 'Documents',
      upload: 'Upload',
      delete: 'Delete',
      noDocuments: 'No Documents',
      noDocumentsDesc: 'Upload your first document to start building your knowledge base.',
      chunks: 'chunks'
    },
    settings: {
      title: 'Settings',
      save: 'Save',
      application: 'Application',
      appName: 'Name',
      version: 'Version',
      debug: 'Debug',
      debugMode: 'Debug Mode',
      debugModeDesc: 'Enable detailed logging',
      logLevel: 'Log Level',
      ragConfig: 'RAG Configuration',
      editable: 'Editable',
      chunkSize: 'Chunk Size',
      chunkOverlap: 'Chunk Overlap',
      retrievalTopK: 'Retrieval Top K',
      rerankingTopK: 'Reranking Top K',
      models: 'Models',
      llmProvider: 'LLM Provider',
      embeddingProvider: 'Embedding Provider',
      embeddingModel: 'Embedding Model',
      rerankerModel: 'Reranker Model',
      fileUpload: 'File Upload',
      maxFileSize: 'Max File Size',
      supportedTypes: 'Supported Types'
    }
  }
}

export const useLanguageStore = defineStore('language', () => {
  const current = ref<Language>('zh')

  const t = computed(() => translations[current.value])

  function initLanguage() {
    const saved = localStorage.getItem('language')
    if (saved && (saved === 'zh' || saved === 'en')) {
      current.value = saved
    }
  }

  function setLanguage(lang: Language) {
    current.value = lang
    localStorage.setItem('language', lang)
  }

  function toggleLanguage() {
    setLanguage(current.value === 'zh' ? 'en' : 'zh')
  }

  return {
    current,
    t,
    initLanguage,
    setLanguage,
    toggleLanguage
  }
})