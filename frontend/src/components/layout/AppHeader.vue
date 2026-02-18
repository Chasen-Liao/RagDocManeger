<script setup lang="ts">
import { useRoute } from 'vue-router'
import { MessageCircle, MessageSquare, BookOpen, Settings } from 'lucide-vue-next'
import ThemeToggle from './ThemeToggle.vue'
import LanguageToggle from './LanguageToggle.vue'
import { useLanguageStore } from '@/stores/language'

const route = useRoute()
const languageStore = useLanguageStore()

const navItems = [
  { path: '/', icon: MessageCircle, nameKey: 'chat' as const },
  { path: '/sessions', icon: MessageSquare, nameKey: 'sessions' as const },
  { path: '/knowledge-bases', icon: BookOpen, nameKey: 'knowledgeBases' as const },
  { path: '/settings', icon: Settings, nameKey: 'settings' as const }
]

function isActive(path: string) {
  return route.path === path || route.path.startsWith(path + '/')
}

function getNavName(item: typeof navItems[0]) {
  return languageStore.t.nav[item.nameKey]
}
</script>

<template>
  <header class="fixed top-0 left-0 right-0 z-40 glass border-b border-light-border/50 dark:border-dark-border/50">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      <div class="flex items-center justify-between h-16">
        <!-- Logo -->
        <router-link to="/" class="flex items-center gap-2 group">
          <div class="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center">
            <span class="text-white font-bold text-sm">RD</span>
          </div>
          <span class="font-title font-bold text-xl text-light-text dark:text-dark-text group-hover:text-light-cta dark:hover:text-dark-cta transition-colors">
            RagDocMan
          </span>
        </router-link>

        <!-- Navigation -->
        <nav class="hidden md:flex items-center gap-1">
          <router-link
            v-for="item in navItems"
            :key="item.path"
            :to="item.path"
            :class="[
              'flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200',
              isActive(item.path)
                ? 'bg-light-cta/10 dark:bg-dark-cta/10 text-light-cta dark:text-dark-cta'
                : 'text-light-text/70 dark:text-dark-text/70 hover:bg-light-border/50 dark:hover:bg-dark-border/50 hover:text-light-text dark:hover:text-dark-text'
            ]"
          >
            <component :is="item.icon" class="w-4 h-4" />
            {{ getNavName(item) }}
          </router-link>
        </nav>

        <!-- Right side -->
        <div class="flex items-center gap-2">
          <LanguageToggle />
          <ThemeToggle />
        </div>
      </div>
    </div>
  </header>
</template>

<style scoped>
</style>
