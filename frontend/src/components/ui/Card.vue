<script setup lang="ts">
interface Props {
  hoverable?: boolean
}

defineProps<Props>()
</script>

<template>
  <div
    :class="[
      'rounded-xl border border-gray-200 bg-white dark:border-gray-800 dark:bg-gray-800 shadow-soft transition-all duration-150',
      hoverable && 'hover:shadow-card-hover hover:border-gray-300 dark:hover:border-gray-700 cursor-pointer'
    ]"
  >
    <slot />
  </div>
</template>