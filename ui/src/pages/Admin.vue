<template>
  <div class="max-w-4xl mx-auto px-4 py-4">
    <h1 class="text-lg font-semibold mb-4">Admin</h1>

    <!-- Indexer Control -->
    <section class="bg-[#171717] rounded-sm p-3 mb-4">
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

    <!-- Watch Folders -->
    <section class="bg-[#171717] rounded-sm p-3 mb-4">
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

    <!-- Enrichment Models -->
    <section class="bg-[#171717] rounded-sm p-3 mb-4">
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

    <!-- Poster Settings -->
    <section class="bg-[#171717] rounded-sm p-3 mb-4">
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

    <!-- Queue Management -->
    <section class="bg-[#171717] rounded-sm p-3 mb-4">
      <h2 class="text-sm font-medium mb-3">Queue Management</h2>
      <p class="text-[10px] text-gray-500 mb-3">Reset stuck or failed enrichment jobs</p>

      <div class="space-y-2">
        <div class="flex items-center justify-between bg-[#262626] rounded-sm px-3 py-2">
          <div>
            <p class="text-xs text-gray-300">Reset Failed Jobs</p>
            <p class="text-[10px] text-gray-500">Move failed jobs back to pending queue for retry</p>
          </div>
          <button
            @click="resetFailed"
            :disabled="loading.resetFailed"
            class="px-3 py-1.5 bg-orange-500 hover:bg-orange-600 rounded-sm text-xs font-medium transition disabled:opacity-50"
          >
            {{ loading.resetFailed ? 'Resetting...' : 'Reset Failed' }}
          </button>
        </div>

        <div class="flex items-center justify-between bg-[#262626] rounded-sm px-3 py-2">
          <div>
            <p class="text-xs text-gray-300">Reset Stuck Jobs</p>
            <p class="text-[10px] text-gray-500">Reset jobs stuck in "processing" state</p>
          </div>
          <button
            @click="resetProcessing"
            :disabled="loading.resetProcessing"
            class="px-3 py-1.5 bg-orange-500 hover:bg-orange-600 rounded-sm text-xs font-medium transition disabled:opacity-50"
          >
            {{ loading.resetProcessing ? 'Resetting...' : 'Reset Stuck' }}
          </button>
        </div>
      </div>
    </section>

    <!-- Cleanup -->
    <section class="bg-[#171717] rounded-sm p-3 mb-4">
      <h2 class="text-sm font-medium mb-3">Cleanup</h2>
      <p class="text-[10px] text-gray-500 mb-3">Remove stale data from the database</p>

      <div class="space-y-2">
        <div class="flex items-center justify-between bg-[#262626] rounded-sm px-3 py-2">
          <div>
            <p class="text-xs text-gray-300">Purge Deleted Files</p>
            <p class="text-[10px] text-gray-500">Permanently remove soft-deleted files and their scenes/faces</p>
          </div>
          <button
            @click="purgeDeleted"
            :disabled="loading.purgeDeleted"
            class="px-3 py-1.5 bg-yellow-600 hover:bg-yellow-700 rounded-sm text-xs font-medium transition disabled:opacity-50"
          >
            {{ loading.purgeDeleted ? 'Purging...' : 'Purge Deleted' }}
          </button>
        </div>

        <div class="flex items-center justify-between bg-[#262626] rounded-sm px-3 py-2">
          <div>
            <p class="text-xs text-gray-300">Purge Orphan Files</p>
            <p class="text-[10px] text-gray-500">Remove files not under any current watch folder</p>
          </div>
          <button
            @click="purgeOrphans"
            :disabled="loading.purgeOrphans"
            class="px-3 py-1.5 bg-yellow-600 hover:bg-yellow-700 rounded-sm text-xs font-medium transition disabled:opacity-50"
          >
            {{ loading.purgeOrphans ? 'Purging...' : 'Purge Orphans' }}
          </button>
        </div>
      </div>
    </section>

    <!-- Danger Zone -->
    <section class="bg-[#171717] rounded-sm p-3 border border-red-900/50">
      <h2 class="text-sm font-medium mb-3 text-red-400">Danger Zone</h2>
      <p class="text-[10px] text-gray-500 mb-3">Destructive actions that cannot be undone</p>

      <div class="flex items-center justify-between bg-[#262626] rounded-sm px-3 py-2">
        <div>
          <p class="text-xs text-gray-300">Wipe Database</p>
          <p class="text-[10px] text-gray-500">Delete all files, scenes, faces, and embeddings. Config is preserved.</p>
        </div>
        <button
          @click="confirmWipe"
          :disabled="loading.wipe"
          class="px-3 py-1.5 bg-red-600 hover:bg-red-700 rounded-sm text-xs font-medium transition disabled:opacity-50"
        >
          {{ loading.wipe ? 'Wiping...' : 'Wipe All Data' }}
        </button>
      </div>
    </section>

    <!-- Result message -->
    <div
      v-if="message"
      class="mt-4 px-3 py-2 rounded-sm text-xs"
      :class="messageType === 'error' ? 'bg-red-900/50 text-red-200' : 'bg-green-900/50 text-green-200'"
    >
      {{ message }}
    </div>
  </div>
</template>

<script setup>
import { reactive, ref, computed, onMounted } from 'vue'
import { api } from '../services/api'

// Indexer state
const indexerState = ref('unknown')

// Watch folders
const watchFolders = ref([])
const refreshingFolders = ref(false)
const reconnecting = ref(false)

const hasInaccessibleFolders = computed(() => {
  return watchFolders.value.some(f => !f.accessible)
})

// Models
const models = reactive({
  clip: true,
  whisper: true,
  arcface: true
})

// Poster settings
const poster = reactive({
  width: 1280,
  quality: 80
})

// Loading states for admin operations
const loading = reactive({
  resetFailed: false,
  resetProcessing: false,
  purgeDeleted: false,
  purgeOrphans: false,
  wipe: false
})

const message = ref('')
const messageType = ref('success')

function showMessage(text, type = 'success') {
  message.value = text
  messageType.value = type
  setTimeout(() => { message.value = '' }, 5000)
}

// Indexer control
async function toggleIndexer() {
  const newState = indexerState.value === 'running' ? 'paused' : 'running'
  try {
    await api.setConfig('indexer_state', newState)
    indexerState.value = newState
  } catch (err) {
    console.error('Failed to toggle indexer:', err)
  }
}

// Watch folders
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

async function reconnectMedia() {
  reconnecting.value = true
  try {
    await api.restartServer()
    await new Promise(resolve => setTimeout(resolve, 3000))
    await loadWatchFolders()
  } catch (err) {
    console.error('Failed to reconnect:', err)
  } finally {
    reconnecting.value = false
  }
}

// Models
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

// Poster settings
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

// Load config on mount
async function loadConfig() {
  try {
    const [state, modelConfig, posterWidth, posterQuality] = await Promise.all([
      api.getConfig('indexer_state'),
      api.getConfig('enrichment_models'),
      api.getConfig('poster_width'),
      api.getConfig('poster_quality')
    ])

    indexerState.value = state.value || 'unknown'

    if (modelConfig.value) {
      models.clip = modelConfig.value.clip ?? true
      models.whisper = modelConfig.value.whisper ?? true
      models.arcface = modelConfig.value.arcface ?? true
    }

    poster.width = posterWidth.value || 1280
    poster.quality = posterQuality.value || 80
  } catch (err) {
    console.error('Failed to load config:', err)
  }
}

// Admin operations
async function resetFailed() {
  loading.resetFailed = true
  try {
    const result = await api.resetFailedJobs()
    showMessage(`Reset ${result.reset_count} failed jobs to pending`)
  } catch (err) {
    showMessage(`Failed: ${err.message}`, 'error')
  } finally {
    loading.resetFailed = false
  }
}

async function resetProcessing() {
  loading.resetProcessing = true
  try {
    const result = await api.resetProcessingJobs()
    showMessage(`Reset ${result.reset_count} stuck jobs to pending`)
  } catch (err) {
    showMessage(`Failed: ${err.message}`, 'error')
  } finally {
    loading.resetProcessing = false
  }
}

async function purgeDeleted() {
  loading.purgeDeleted = true
  try {
    const result = await api.purgeDeleted()
    showMessage(`Permanently removed ${result.purged_count} deleted files`)
  } catch (err) {
    showMessage(`Failed: ${err.message}`, 'error')
  } finally {
    loading.purgeDeleted = false
  }
}

async function purgeOrphans() {
  loading.purgeOrphans = true
  try {
    const result = await api.purgeOrphans()
    showMessage(`Removed ${result.purged_count} orphan files`)
  } catch (err) {
    showMessage(`Failed: ${err.message}`, 'error')
  } finally {
    loading.purgeOrphans = false
  }
}

async function confirmWipe() {
  const confirmed = window.confirm(
    'Are you sure you want to wipe ALL indexed data?\n\n' +
    'This will delete all files, scenes, faces, and embeddings.\n' +
    'This action cannot be undone!'
  )
  if (!confirmed) return

  loading.wipe = true
  try {
    const result = await api.wipeDatabase()
    showMessage(`Wiped ${result.wiped.files} files, ${result.wiped.scenes} scenes, ${result.wiped.faces} faces`)
  } catch (err) {
    showMessage(`Failed: ${err.message}`, 'error')
  } finally {
    loading.wipe = false
  }
}

onMounted(() => {
  loadConfig()
  loadWatchFolders()
})
</script>
