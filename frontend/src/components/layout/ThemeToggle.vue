<script setup lang="ts">
import { useThemeStore } from '@/stores/theme'
import { Sun, Moon } from 'lucide-vue-next'

const themeStore = useThemeStore()
</script>

<template>
  <button
    @click="themeStore.toggleTheme()"
    class="p-2 rounded-lg text-light-text/70 dark:text-dark-text/70 hover:bg-light-border/50 dark:hover:bg-dark-border/50 transition-all duration-200"
    :title="themeStore.isDark ? '切换到浅色模式' : '切换到深色模式'"
  >
    <Transition name="rotate" mode="out-in">
      <Moon v-if="themeStore.isDark" key="moon" class="w-5 h-5" />
      <Sun v-else key="sun" class="w-5 h-5" />
    </Transition>
  </button>
</template>

<style scoped>
.rotate-enter-active,
.rotate-leave-active {
  transition: all 0.2s ease;
}

.rotate-enter-from {
  opacity: 0;
  transform: rotate(-90deg) scale(0.5);
}

.rotate-leave-to {
  opacity: 0;
  transform: rotate(90deg) scale(0.5);
}
</style>
