<script setup lang="ts">
interface Props {
  hoverable?: boolean
}

defineProps<Props>()
</script>

<template>
  <div
    :class="[
      'rounded-xl border border-light-border dark:border-dark-border bg-light-card dark:bg-dark-card shadow-glass dark:shadow-glass-dark transition-all duration-200',
      hoverable && 'hover:shadow-lg hover:border-light-cta/30 dark:hover:border-dark-cta/30'
    ]"
  >
    <slot />
  </div>
</template>
