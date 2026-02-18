<script setup lang="ts">
import { watch } from 'vue'

interface Props {
  open: boolean
  title?: string
  size?: 'sm' | 'md' | 'lg'
}

const props = withDefaults(defineProps<Props>(), {
  title: '',
  size: 'md'
})

const emit = defineEmits<{
  'update:open': [value: boolean]
}>()

const sizeClasses = {
  sm: 'max-w-sm',
  md: 'max-w-md',
  lg: 'max-w-2xl'
}

watch(() => props.open, (isOpen) => {
  if (isOpen) {
    document.body.style.overflow = 'hidden'
  } else {
    document.body.style.overflow = ''
  }
})
</script>

<template>
  <Teleport to="body">
    <Transition name="modal">
      <div v-if="open" class="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div class="absolute inset-0 bg-black/50 backdrop-blur-sm" @click="emit('update:open', false)"></div>
        <div
          :class="[
            'relative w-full rounded-2xl border border-light-border dark:border-dark-border bg-light-card dark:bg-dark-card shadow-xl',
            sizeClasses[size]
          ]"
        >
          <div v-if="title" class="flex items-center justify-between px-6 py-4 border-b border-light-border dark:border-dark-border">
            <h3 class="text-lg font-semibold font-title text-light-text dark:text-dark-text">{{ title }}</h3>
            <button
              class="p-1 rounded-lg hover:bg-light-border/50 dark:hover:bg-dark-border/50 transition-colors"
              @click="emit('update:open', false)"
            >
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
          <div class="p-6">
            <slot />
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.modal-enter-active,
.modal-leave-active {
  transition: opacity 0.2s ease;
}

.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}

.modal-enter-active .relative,
.modal-leave-active .relative {
  transition: transform 0.2s ease;
}

.modal-enter-from .relative,
.modal-leave-to .relative {
  transform: scale(0.95);
}
</style>
