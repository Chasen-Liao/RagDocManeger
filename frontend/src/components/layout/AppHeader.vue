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
  <header class="fixed top-0 left-0 right-0 z-50 backdrop-header border-b border-gray-200 dark:border-gray-800">
    <div class="max-w-5xl mx-auto px-4">
      <div class="flex items-center justify-between h-14">
        <!-- Logo -->
        <router-link to="/" class="flex items-center gap-2.5 group">
          <div class="w-7 h-7 rounded-md bg-gray-900 dark:bg-gray-100 flex items-center justify-center">
            <span class="text-white dark:text-gray-900 font-semibold text-xs">R</span>
          </div>
          <span class="font-semibold text-gray-900 dark:text-gray-100 text-[15px]">
            RagDocMan
          </span>
        </router-link>

        <!-- Navigation -->
        <nav class="hidden md:flex items-center gap-0.5">
          <router-link
            v-for="item in navItems"
            :key="item.path"
            :to="item.path"
            :class="[
              'flex items-center gap-1.5 px-3 py-1.5 rounded-md text-[13px] font-medium transition-colors duration-150',
              isActive(item.path)
                ? 'bg-gray-200/60 dark:bg-gray-800/60 text-gray-900 dark:text-gray-100'
                : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800/50'
            ]"
          >
            <component :is="item.icon" class="w-[15px] h-[15px]" />
            {{ getNavName(item) }}
          </router-link>
        </nav>

        <!-- Right side -->
        <div class="flex items-center gap-0.5">
          <LanguageToggle />
          <ThemeToggle />
        </div>
      </div>
    </div>
  </header>
</template>