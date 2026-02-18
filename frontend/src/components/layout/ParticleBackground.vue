<script setup lang="ts">
import { onMounted, onUnmounted, ref, watch } from 'vue'
import { useThemeStore } from '@/stores/theme'
import { loadSlim } from '@tsparticles/slim'

const themeStore = useThemeStore()
const particlesReady = ref(false)
let particlesInstance: any = null

const particleOptions = {
  background: {
    color: {
      value: 'transparent'
    }
  },
  particles: {
    color: {
      value: themeStore.isDark ? '#3B82F6' : '#2563EB'
    },
    links: {
      color: {
        value: themeStore.isDark ? '#3B82F6' : '#2563EB'
      },
      distance: 150,
      enable: true,
      opacity: 0.2
    },
    move: {
      enable: true,
      speed: 1,
      direction: 'none',
      outModes: {
        default: 'bounce'
      }
    },
    number: {
      value: 50,
      density: {
        enable: true,
        area: 800
      }
    },
    opacity: {
      value: 0.3
    },
    shape: {
      type: 'circle'
    },
    size: {
      value: { min: 1, max: 3 }
    }
  },
  interactivity: {
    events: {
      onHover: {
        enable: true,
        mode: 'grab'
      }
    },
    modes: {
      grab: {
        distance: 200,
        links: {
          opacity: 0.5
        }
      }
    }
  },
  detectRetina: true
}

async function initParticles() {
  const container = document.getElementById('particles-container')
  if (!container) return

  const engine = await loadSlim()
  particlesInstance = await engine.containerFactory.createContainer({
    id: 'particles',
    options: particleOptions
  })

  if (particlesInstance) {
    await particlesInstance.load()
    particlesReady.value = true
  }
}

watch(() => themeStore.isDark, async (isDark) => {
  if (particlesInstance) {
    const particles = particlesInstance.particles
    if (particles) {
      particles.setColor('color', isDark ? '#3B82F6' : '#2563EB')
      particles.setColor('links.color', isDark ? '#3B82F6' : '#2563EB')
    }
  }
})

onMounted(async () => {
  const mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)')
  if (!mediaQuery.matches) {
    await initParticles()
  }
})

onUnmounted(() => {
  if (particlesInstance) {
    particlesInstance.destroy()
  }
})
</script>

<template>
  <div
    id="particles-container"
    class="fixed inset-0 pointer-events-none z-0"
  ></div>
</template>

<style scoped>
#particles-container {
  background: transparent;
}
</style>
