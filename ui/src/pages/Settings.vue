<template>
  <div class="max-w-4xl mx-auto px-4 py-4">
    <h1 class="text-lg font-semibold mb-4">Settings</h1>

    <!-- Indexer Control -->
    <section v-if="!demoMode" class="bg-[#171717] rounded-sm p-3 mb-4">
      <h2 class="text-sm font-medium mb-3">Indexer Control</h2>
      <div class="flex items-center justify-between">
        <div>
          <p class="text-xs text-gray-300">Indexer Status</p>
          <p class="text-[10px] text-gray-500">
            {{ indexerState === 'running' ? 'Actively scanning and enriching files' : 'Paused - no new files will be processed' }}
          </p>
        </div>
        <button
          @click="toggleIndexer"
          class="px-3 py-1.5 rounded-sm text-xs font-medium transition"
          :class="indexerState === 'running'
            ? 'bg-yellow-600 hover:bg-yellow-700'
            : 'bg-green-600 hover:bg-green-700'"
        >
          {{ indexerState === 'running' ? 'Pause' : 'Resume' }}
        </button>
      </div>
    </section>

    <!-- Watch Folders (read-only, configured in docker-compose.yml) -->
    <section v-if="!demoMode" class="bg-[#171717] rounded-sm p-3 mb-4">
      <div class="flex items-center justify-between mb-3">
        <h2 class="text-sm font-medium">Watch Folders</h2>
        <div class="flex items-center gap-2">
          <button
            v-if="hasInaccessibleFolders"
            @click="reconnectMedia"
            :disabled="reconnecting"
            class="px-2 py-1 text-[10px] bg-orange-500 hover:bg-orange-600 text-white rounded-sm transition disabled:opacity-50"
            title="Restart server to detect remounted drives"
          >
            <span v-if="reconnecting">Reconnecting...</span>
            <span v-else>Reconnect Media</span>
          </button>
          <button
            @click="refreshWatchFolders"
            :disabled="refreshingFolders"
            class="px-2 py-1 text-[10px] text-gray-400 hover:text-white hover:bg-[#262626] rounded-sm transition disabled:opacity-50"
            title="Check mount status"
          >
            <span v-if="refreshingFolders">Checking...</span>
            <span v-else>↻ Refresh</span>
          </button>
        </div>
      </div>
      <p class="text-[10px] text-gray-500 mb-3">Configured via WATCH_FOLDERS in docker-compose.yml</p>

      <div class="space-y-1.5">
        <div
          v-for="(folder, idx) in watchFolders"
          :key="idx"
          class="flex items-center justify-between bg-[#262626] rounded-sm px-2 py-1.5"
        >
          <div class="flex items-center gap-2 min-w-0">
            <span
              class="w-2 h-2 rounded-full flex-shrink-0"
              :class="folder.accessible ? 'bg-green-500' : 'bg-red-500'"
              :title="folder.accessible ? 'Mounted' : 'Not mounted'"
            ></span>
            <span class="font-mono text-[10px] truncate">{{ folder.path }}</span>
          </div>
          <span
            v-if="!folder.accessible"
            class="text-[9px] text-red-400 bg-red-500/20 px-1.5 py-0.5 rounded-sm flex-shrink-0"
          >
            Drive not mounted
          </span>
        </div>
        <div v-if="watchFolders.length === 0" class="text-gray-500 text-[10px] py-1.5">
          No watch folders configured
        </div>
      </div>
    </section>

    <!-- Model Settings -->
    <section v-if="!demoMode" class="bg-[#171717] rounded-sm p-3 mb-4">
      <h2 class="text-sm font-medium mb-3">Enrichment Models</h2>
      <p class="text-[10px] text-gray-500 mb-3">Toggle which models run during enrichment</p>

      <div class="space-y-2">
        <label class="flex items-center justify-between cursor-pointer">
          <div>
            <span class="text-xs text-gray-300">CLIP</span>
            <p class="text-[10px] text-gray-500">Visual embeddings for text-to-image search</p>
          </div>
          <input
            type="checkbox"
            v-model="models.clip"
            @change="saveModels"
            class="w-4 h-4 rounded-sm accent-orange-500"
          />
        </label>

        <label class="flex items-center justify-between cursor-pointer">
          <div>
            <span class="text-xs text-gray-300">Whisper</span>
            <p class="text-[10px] text-gray-500">Speech-to-text transcription</p>
          </div>
          <input
            type="checkbox"
            v-model="models.whisper"
            @change="saveModels"
            class="w-4 h-4 rounded-sm accent-orange-500"
          />
        </label>

        <label class="flex items-center justify-between cursor-pointer">
          <div>
            <span class="text-xs text-gray-300">ArcFace</span>
            <p class="text-[10px] text-gray-500">Face detection and recognition</p>
          </div>
          <input
            type="checkbox"
            v-model="models.arcface"
            @change="saveModels"
            class="w-4 h-4 rounded-sm accent-orange-500"
          />
        </label>
      </div>
    </section>

    <!-- Search Thresholds -->
    <section class="bg-[#171717] rounded-sm p-3 mb-4">
      <h2 class="text-sm font-medium mb-3">Search Thresholds</h2>
      <p class="text-[10px] text-gray-500 mb-3">Default minimum similarity thresholds for search (0.0 - 1.0). Lower values return more results.</p>

      <div class="space-y-3 max-w-md">
        <div>
          <label class="block text-[10px] text-gray-400 mb-1">Visual Search (CLIP)</label>
          <div class="flex items-center gap-2">
            <input
              v-model.number="thresholds.visual"
              type="range"
              min="0"
              max="1"
              step="0.01"
              class="flex-1 accent-orange-500"
            />
            <input
              v-model.number="thresholds.visual"
              type="number"
              min="0"
              max="1"
              step="0.01"
              class="w-16 bg-[#262626] text-white px-1.5 py-1 rounded-sm text-[10px] text-center focus:outline-none focus:ring-1 focus:ring-orange-500"
            />
          </div>
          <p class="text-[10px] text-gray-500 mt-0.5">Text-to-image similarity threshold</p>
        </div>

        <div>
          <label class="block text-[10px] text-gray-400 mb-1">Visual Match (Scene-to-Scene)</label>
          <div class="flex items-center gap-2">
            <input
              v-model.number="thresholds.visualMatch"
              type="range"
              min="0"
              max="1"
              step="0.01"
              class="flex-1 accent-orange-500"
            />
            <input
              v-model.number="thresholds.visualMatch"
              type="number"
              min="0"
              max="1"
              step="0.01"
              class="w-16 bg-[#262626] text-white px-1.5 py-1 rounded-sm text-[10px] text-center focus:outline-none focus:ring-1 focus:ring-orange-500"
            />
          </div>
          <p class="text-[10px] text-gray-500 mt-0.5">Similarity threshold for "find similar" searches</p>
        </div>

        <div>
          <label class="block text-[10px] text-gray-400 mb-1">Face Match (ArcFace)</label>
          <div class="flex items-center gap-2">
            <input
              v-model.number="thresholds.face"
              type="range"
              min="0"
              max="1"
              step="0.01"
              class="flex-1 accent-orange-500"
            />
            <input
              v-model.number="thresholds.face"
              type="number"
              min="0"
              max="1"
              step="0.01"
              class="w-16 bg-[#262626] text-white px-1.5 py-1 rounded-sm text-[10px] text-center focus:outline-none focus:ring-1 focus:ring-orange-500"
            />
          </div>
          <p class="text-[10px] text-gray-500 mt-0.5">Face similarity threshold for person searches</p>
        </div>
      </div>

      <button
        @click="saveThresholds"
        class="mt-3 px-3 py-1.5 bg-orange-500 hover:bg-orange-600 rounded-sm text-xs font-medium transition"
      >
        Save Thresholds
      </button>
    </section>

    <!-- Poster Settings -->
    <section v-if="!demoMode" class="bg-[#171717] rounded-sm p-3">
      <h2 class="text-sm font-medium mb-3">Poster Settings</h2>
      <p class="text-[10px] text-gray-500 mb-3">Settings for scene poster frame extraction (WebP format)</p>

      <div class="grid grid-cols-2 gap-3 max-w-md">
        <div>
          <label class="block text-[10px] text-gray-400 mb-1">Width (px)</label>
          <input
            v-model="poster.width"
            type="number"
            class="w-full bg-[#262626] text-white px-2 py-1.5 rounded-sm text-xs focus:outline-none focus:ring-1 focus:ring-orange-500"
          />
        </div>
        <div>
          <label class="block text-[10px] text-gray-400 mb-1">Quality (1-100)</label>
          <input
            v-model="poster.quality"
            type="number"
            min="1"
            max="100"
            class="w-full bg-[#262626] text-white px-2 py-1.5 rounded-sm text-xs focus:outline-none focus:ring-1 focus:ring-orange-500"
          />
        </div>
      </div>

      <button
        @click="savePosterSettings"
        class="mt-3 px-3 py-1.5 bg-orange-500 hover:bg-orange-600 rounded-sm text-xs font-medium transition"
      >
        Save Poster Settings
      </button>
    </section>

    <!-- CLI Commands Reference -->
    <section v-if="!demoMode" class="bg-[#171717] rounded-sm p-3">
      <h2 class="text-sm font-medium mb-3">CLI Commands</h2>
      <p class="text-[10px] text-gray-500 mb-3">Use these commands in your terminal for maintenance operations</p>

      <div class="space-y-2 text-[10px] font-mono">
        <div class="bg-[#262626] rounded-sm px-2 py-1.5">
          <span class="text-gray-400"># Restart containers</span><br/>
          <span class="text-gray-200">docker compose restart</span>
        </div>
        <div class="bg-[#262626] rounded-sm px-2 py-1.5">
          <span class="text-gray-400"># View ingest logs</span><br/>
          <span class="text-gray-200">docker compose logs -f ingest</span>
        </div>
        <div class="bg-[#262626] rounded-sm px-2 py-1.5">
          <span class="text-gray-400"># Clear database and start fresh</span><br/>
          <span class="text-gray-200">docker compose down -v && docker compose up -d</span>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { api } from '../services/api'

const demoMode = ref(false)
const indexerState = ref('unknown')
const watchFolders = ref([])
const refreshingFolders = ref(false)
const reconnecting = ref(false)

const models = reactive({
  clip: true,
  whisper: true,
  arcface: true
})

const poster = reactive({
  width: 1280,
  quality: 80
})

const thresholds = reactive({
  visual: 0.10,
  visualMatch: 0.20,
  face: 0.25
})

async function loadWatchFolders() {
  try {
    const result = await api.getWatchFolders()
    watchFolders.value = result.folders
  } catch (err) {
    console.error('Failed to load watch folders:', err)
  }
}

async function refreshWatchFolders() {
  refreshingFolders.value = true
  try {
    await loadWatchFolders()
  } finally {
    refreshingFolders.value = false
  }
}

const hasInaccessibleFolders = computed(() => {
  return watchFolders.value.some(f => !f.accessible)
})

async function reconnectMedia() {
  reconnecting.value = true
  try {
    await api.restartServer()
    // Wait for server to restart, then refresh
    await new Promise(resolve => setTimeout(resolve, 3000))
    await loadWatchFolders()
  } catch (err) {
    console.error('Failed to reconnect:', err)
  } finally {
    reconnecting.value = false
  }
}

async function loadConfig() {
  try {
    const [state, modelConfig, posterWidth, posterQuality, thresholdVisual, thresholdVisualMatch, thresholdFace] = await Promise.all([
      api.getConfig('indexer_state'),
      api.getConfig('enrichment_models'),
      api.getConfig('poster_width'),
      api.getConfig('poster_quality'),
      api.getConfig('search_threshold_visual'),
      api.getConfig('search_threshold_visual_match'),
      api.getConfig('search_threshold_face')
    ])

    indexerState.value = state.value || 'unknown'

    if (modelConfig.value) {
      models.clip = modelConfig.value.clip ?? true
      models.whisper = modelConfig.value.whisper ?? true
      models.arcface = modelConfig.value.arcface ?? true
    }

    poster.width = posterWidth.value || 1280
    poster.quality = posterQuality.value || 80

    thresholds.visual = thresholdVisual.value ?? 0.10
    thresholds.visualMatch = thresholdVisualMatch.value ?? 0.20
    thresholds.face = thresholdFace.value ?? 0.25
  } catch (err) {
    console.error('Failed to load config:', err)
  }
}

async function toggleIndexer() {
  const newState = indexerState.value === 'running' ? 'paused' : 'running'
  try {
    await api.setConfig('indexer_state', newState)
    indexerState.value = newState
  } catch (err) {
    console.error('Failed to toggle indexer:', err)
  }
}

async function saveModels() {
  try {
    await api.setConfig('enrichment_models', {
      clip: models.clip,
      whisper: models.whisper,
      arcface: models.arcface
    })
  } catch (err) {
    console.error('Failed to save models:', err)
  }
}

async function savePosterSettings() {
  try {
    await Promise.all([
      api.setConfig('poster_width', poster.width),
      api.setConfig('poster_quality', poster.quality)
    ])
  } catch (err) {
    console.error('Failed to save poster settings:', err)
  }
}

async function saveThresholds() {
  try {
    await Promise.all([
      api.setConfig('search_threshold_visual', thresholds.visual),
      api.setConfig('search_threshold_visual_match', thresholds.visualMatch),
      api.setConfig('search_threshold_face', thresholds.face)
    ])
  } catch (err) {
    console.error('Failed to save thresholds:', err)
  }
}

async function loadAdminStatus() {
  try {
    const status = await api.getAdminStatus()
    demoMode.value = status.demo_mode
  } catch (err) {
    console.error('Failed to load admin status:', err)
  }
}

onMounted(() => {
  loadAdminStatus()
  loadConfig()
  loadWatchFolders()
})
</script>
