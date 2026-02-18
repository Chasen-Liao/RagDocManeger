<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'

interface Option {
  value: string
  label: string
}

interface Props {
  modelValue: string
  options: Option[]
  placeholder?: string
}

const props = withDefaults(defineProps<Props>(), {
  placeholder: 'Select...'
})

const emit = defineEmits<{
  'update:modelValue': [value: string]
}>()

const isOpen = ref(false)
const selectRef = ref<HTMLElement | null>(null)

const selectedLabel = computed(() => {
  const option = props.options.find(o => o.value === props.modelValue)
  return option?.label || props.placeholder
})

function toggle() {
  isOpen.value = !isOpen.value
}

function select(value: string) {
  emit('update:modelValue', value)
  isOpen.value = false
}

function handleClickOutside(event: MouseEvent) {
  if (selectRef.value && !selectRef.value.contains(event.target as Node)) {
    isOpen.value = false
  }
}

onMounted(() => {
  document.addEventListener('click', handleClickOutside)
})

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
})
</script>

<template>
  <div ref="selectRef" class="relative">
    <button
      type="button"
      @click="toggle"
      class="appearance-none w-full px-4 py-2 pr-10 rounded-xl border border-light-border dark:border-dark-border bg-light-card dark:bg-dark-card text-light-text dark:text-dark-text text-sm font-medium cursor-pointer focus:outline-none focus:ring-2 focus:ring-light-cta/50 focus:border-light-cta dark:focus:border-dark-cta transition-all duration-200 hover:border-light-cta/50 dark:hover:border-dark-cta/50 text-left flex items-center justify-between gap-2"
    >
      <span :class="modelValue ? '' : 'text-gray-400 dark:text-gray-500'">{{ selectedLabel }}</span>
      <svg
        class="w-4 h-4 text-light-text/50 dark:text-dark-text/50 transition-transform duration-200"
        :class="isOpen && 'rotate-180'"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
      </svg>
    </button>

    <Transition
      enter-active-class="transition ease-out duration-150"
      enter-from-class="opacity-0 -translate-y-1"
      enter-to-class="opacity-100 translate-y-0"
      leave-active-class="transition ease-in duration-100"
      leave-from-class="opacity-100 translate-y-0"
      leave-to-class="opacity-0 -translate-y-1"
    >
      <div
        v-if="isOpen"
        class="absolute z-50 w-full mt-2 py-1 rounded-xl border border-light-border dark:border-dark-border bg-light-card dark:bg-dark-card shadow-lg overflow-hidden"
      >
        <button
          v-for="option in options"
          :key="option.value"
          type="button"
          @click="select(option.value)"
          class="w-full px-4 py-2.5 text-left text-sm text-light-text dark:text-dark-text hover:bg-light-cta/10 dark:hover:bg-dark-cta/10 transition-colors duration-150 flex items-center gap-2"
          :class="option.value === modelValue && 'bg-light-cta/10 dark:bg-dark-cta/10 text-light-cta dark:text-dark-cta'"
        >
          {{ option.label }}
          <svg
            v-if="option.value === modelValue"
            class="w-4 h-4 ml-auto"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
          </svg>
        </button>
      </div>
    </Transition>
  </div>
</template>