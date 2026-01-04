<template>
  <div class="min-h-screen flex flex-col">
    <!-- Header -->
    <header class="bg-[#171717] border-b border-[#262626] sticky top-0 z-50">
      <div class="max-w-7xl mx-auto px-4">
        <div class="flex items-center justify-between h-10">
          <!-- Logo and brand -->
          <router-link to="/" class="flex items-center gap-2">
            <img
              src="/fennec-logo-lg.png"
              alt="Fennec"
              class="h-7 w-auto object-contain"
            />
          </router-link>

          <!-- Navigation -->
          <nav class="flex items-center gap-0.5">
            <router-link
              v-for="link in navLinks"
              :key="link.to"
              :to="link.to"
              class="nav-link"
            >
              {{ link.label }}<sup
                v-if="link.to === '/edl' && edlCount > 0"
                class="ml-0.5 px-1 text-[8px] font-semibold bg-amber-600/80 text-amber-100 rounded-sm"
              >{{ edlCount }}</sup>
            </router-link>
          </nav>

          <!-- Server status -->
          <div class="flex items-center gap-1.5">
            <span
              class="w-1.5 h-1.5 rounded-full"
              :class="statusDotClass"
            ></span>
            <span class="text-[10px] text-gray-400">{{ statusLabel }}</span>
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
import { api, serverStatus } from './services/api'

const adminEnabled = ref(false)

const navLinks = computed(() => {
  const links = [
    { to: '/', label: 'Search' },
    { to: '/report', label: 'Report' },
    { to: '/edl', label: 'EDL' },
    { to: '/settings', label: 'Settings' }
  ]
  if (adminEnabled.value) {
    links.push({ to: '/admin', label: 'Admin' })
  }
  return links
})

// EDL count for badge
const EDL_STORAGE_KEY = 'fennec_edl_scenes'
const edlCount = ref(0)

function updateEdlCount() {
  try {
    const saved = localStorage.getItem(EDL_STORAGE_KEY)
    edlCount.value = saved ? JSON.parse(saved).length : 0
  } catch {
    edlCount.value = 0
  }
}

// Listen for storage changes (from other tabs or Search.vue updates)
window.addEventListener('storage', (e) => {
  if (e.key === EDL_STORAGE_KEY) updateEdlCount()
})

const indexerState = ref('offline')
const modelsReady = ref(false)

const statusLabel = computed(() => {
  if (!modelsReady.value) return 'Loading models...'
  if (indexerState.value === 'running') return 'Indexing'
  if (indexerState.value === 'paused') return 'Paused'
  return 'Ready'
})

const statusDotClass = computed(() => {
  if (!modelsReady.value) return 'bg-orange-500'
  if (indexerState.value === 'paused') return 'bg-yellow-500'
  return 'bg-green-500'  // Ready or Indexing
})

const fetchStatus = async () => {
  try {
    const status = await api.getReady()
    modelsReady.value = status.models_ready
    indexerState.value = status.indexer_state || 'offline'
    // Update shared state for other components
    serverStatus.modelsReady = status.models_ready
    serverStatus.clipLoaded = status.clip_loaded
    serverStatus.sentenceLoaded = status.sentence_loaded
    serverStatus.indexerState = status.indexer_state || 'offline'
  } catch (e) {
    indexerState.value = 'offline'
    modelsReady.value = false
  }
}

async function checkAdminStatus() {
  try {
    const status = await api.getAdminStatus()
    adminEnabled.value = status.admin_enabled
  } catch {
    adminEnabled.value = false
  }
}

onMounted(() => {
  fetchStatus()
  updateEdlCount()
  checkAdminStatus()
  // Poll every 5 seconds to keep status current
  setInterval(fetchStatus, 5000)
  // Poll EDL count every 2 seconds (for same-tab updates)
  setInterval(updateEdlCount, 2000)
})
</script>
