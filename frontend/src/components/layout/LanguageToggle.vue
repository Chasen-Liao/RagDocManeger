<script setup lang="ts">
import { useLanguageStore } from '@/stores/language'

const languageStore = useLanguageStore()
</script>

<template>
  <button
    @click="languageStore.toggleLanguage()"
    class="px-2 py-1 rounded-md text-xs font-medium text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors duration-150"
    :title="languageStore.current === 'zh' ? 'Switch to English' : '切换到中文'"
  >
    {{ languageStore.current === 'zh' ? 'EN' : '中文' }}
  </button>
</template>