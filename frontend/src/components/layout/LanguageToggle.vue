<script setup lang="ts">
import { useLanguageStore } from '@/stores/language'

const languageStore = useLanguageStore()
</script>

<template>
  <button
    @click="languageStore.toggleLanguage()"
    class="px-2 py-1 rounded-lg text-sm font-medium text-light-text/70 dark:text-dark-text/70 hover:bg-light-border/50 dark:hover:bg-dark-border/50 transition-all duration-200"
    :title="languageStore.current === 'zh' ? 'Switch to English' : '切换到中文'"
  >
    {{ languageStore.current === 'zh' ? 'EN' : '中文' }}
  </button>
</template>