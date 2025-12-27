<template>
  <div class="min-h-screen flex flex-col">
    <!-- Header -->
    <header class="bg-[#171717] border-b border-[#262626] sticky top-0 z-50">
      <div class="max-w-7xl mx-auto px-4">
        <div class="flex items-center justify-between h-16">
          <!-- Logo and brand -->
          <router-link to="/" class="flex items-center gap-3">
            <img 
              src="/fennec-logo-lg.png" 
              alt="Fennec" 
              class="h-12 w-auto object-contain"
            />
            <!-- <span class="text-sm font-light text-white">
              fennec
            </span> -->
          </router-link>
          
          <!-- Navigation -->
          <nav class="flex items-center gap-1">
            <router-link 
              v-for="link in navLinks" 
              :key="link.to"
              :to="link.to" 
              class="nav-link"
            >
              {{ link.label }}
            </router-link>
          </nav>
          
          <!-- Indexer status -->
          <div class="flex items-center gap-2">
            <span 
              class="w-2 h-2 rounded-full" 
              :class="{
                'bg-green-500': indexerState === 'running',
                'bg-yellow-500': indexerState === 'paused',
                'bg-gray-500': indexerState === 'offline'
              }"
            ></span>
            <span class="text-sm text-gray-400">{{ statusLabel }}</span>
          </div>
        </div>
      </div>
    </header>
    
    <!-- Main content -->
    <main class="flex-1">
      <router-view />
    </main>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { api } from './services/api'

const navLinks = [
  { to: '/', label: 'Search' },
  { to: '/report', label: 'Report' },
  { to: '/settings', label: 'Settings' }
]

const indexerState = ref('unknown')

const statusLabel = computed(() => {
  if (indexerState.value === 'running') return 'Indexing'
  if (indexerState.value === 'paused') return 'Paused'
  return 'Offline'
})

const fetchIndexerState = async () => {
  try {
    const config = await api.getConfig('indexer_state')
    // Handle both direct value and nested JSON string
    let state = config.value
    if (typeof state === 'string' && (state === 'running' || state === 'paused')) {
      indexerState.value = state
    } else {
      indexerState.value = 'offline'
    }
  } catch (e) {
    indexerState.value = 'offline'
  }
}

onMounted(() => {
  fetchIndexerState()
  // Poll every 10 seconds to keep status current
  setInterval(fetchIndexerState, 10000)
})
</script>
