<template>
  <div class="max-w-4xl mx-auto px-4 py-6">
    <h1 class="text-2xl font-semibold mb-6">Settings</h1>

    <!-- Indexer Control -->
    <section class="bg-[#171717] rounded-lg p-6 mb-6">
      <h2 class="text-lg font-medium mb-4">Indexer Control</h2>
      <div class="flex items-center justify-between">
        <div>
          <p class="text-gray-300">Indexer Status</p>
          <p class="text-sm text-gray-500">
            {{ indexerState === 'running' ? 'Actively scanning and enriching files' : 'Paused - no new files will be processed' }}
          </p>
        </div>
        <button 
          @click="toggleIndexer"
          class="px-4 py-2 rounded font-medium transition"
          :class="indexerState === 'running' 
            ? 'bg-yellow-600 hover:bg-yellow-700' 
            : 'bg-green-600 hover:bg-green-700'"
        >
          {{ indexerState === 'running' ? 'Pause' : 'Resume' }}
        </button>
      </div>
    </section>

    <!-- Watch Folders -->
    <section class="bg-[#171717] rounded-lg p-6 mb-6">
      <h2 class="text-lg font-medium mb-4">Watch Folders</h2>
      <p class="text-sm text-gray-500 mb-4">Directories that will be scanned for video files</p>
      
      <div class="space-y-2 mb-4">
        <div 
          v-for="(folder, idx) in watchFolders" 
          :key="idx"
          class="flex items-center bg-[#262626] rounded px-3 py-2"
        >
          <span class="font-mono text-sm">{{ folder }}</span>
        </div>
        <div v-if="watchFolders.length === 0" class="text-gray-500 text-sm py-2">
          No watch folders configured
        </div>
      </div>
      
      <p class="text-xs text-gray-500">
        Watch folders are configured via the <code class="bg-[#262626] px-1 rounded">WATCH_FOLDERS</code> 
        environment variable in <code class="bg-[#262626] px-1 rounded">docker-compose.yml</code>.
      </p>
    </section>

    <!-- Model Settings -->
    <section class="bg-[#171717] rounded-lg p-6 mb-6">
      <h2 class="text-lg font-medium mb-4">Enrichment Models</h2>
      <p class="text-sm text-gray-500 mb-4">Toggle which models run during enrichment</p>
      
      <div class="space-y-3">
        <label class="flex items-center justify-between cursor-pointer">
          <div>
            <span class="text-gray-300">CLIP</span>
            <p class="text-xs text-gray-500">Visual embeddings for text-to-image search</p>
          </div>
          <input 
            type="checkbox" 
            v-model="models.clip"
            @change="saveModels"
            class="w-5 h-5 rounded accent-orange-500"
          />
        </label>
        
        <label class="flex items-center justify-between cursor-pointer">
          <div>
            <span class="text-gray-300">Whisper</span>
            <p class="text-xs text-gray-500">Speech-to-text transcription</p>
          </div>
          <input 
            type="checkbox" 
            v-model="models.whisper"
            @change="saveModels"
            class="w-5 h-5 rounded accent-orange-500"
          />
        </label>
        
        <label class="flex items-center justify-between cursor-pointer">
          <div>
            <span class="text-gray-300">ArcFace</span>
            <p class="text-xs text-gray-500">Face detection and recognition</p>
          </div>
          <input 
            type="checkbox" 
            v-model="models.arcface"
            @change="saveModels"
            class="w-5 h-5 rounded accent-orange-500"
          />
        </label>
      </div>
    </section>

    <!-- Search Thresholds -->
    <section class="bg-[#171717] rounded-lg p-6 mb-6">
      <h2 class="text-lg font-medium mb-4">Search Thresholds</h2>
      <p class="text-sm text-gray-500 mb-4">Default minimum similarity thresholds for search (0.0 - 1.0). Lower values return more results.</p>
      
      <div class="space-y-4 max-w-md">
        <div>
          <label class="block text-sm text-gray-400 mb-1">Visual Search (CLIP)</label>
          <div class="flex items-center gap-3">
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
              class="w-20 bg-[#262626] text-white px-2 py-1 rounded text-sm text-center focus:outline-none focus:ring-1 focus:ring-orange-500"
            />
          </div>
          <p class="text-xs text-gray-500 mt-1">Text-to-image similarity threshold</p>
        </div>
        
        <div>
          <label class="block text-sm text-gray-400 mb-1">Visual Match (Scene-to-Scene)</label>
          <div class="flex items-center gap-3">
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
              class="w-20 bg-[#262626] text-white px-2 py-1 rounded text-sm text-center focus:outline-none focus:ring-1 focus:ring-orange-500"
            />
          </div>
          <p class="text-xs text-gray-500 mt-1">Similarity threshold for "find similar" searches</p>
        </div>
        
        <div>
          <label class="block text-sm text-gray-400 mb-1">Face Match (ArcFace)</label>
          <div class="flex items-center gap-3">
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
              class="w-20 bg-[#262626] text-white px-2 py-1 rounded text-sm text-center focus:outline-none focus:ring-1 focus:ring-orange-500"
            />
          </div>
          <p class="text-xs text-gray-500 mt-1">Face similarity threshold for person searches</p>
        </div>
      </div>
      
      <button 
        @click="saveThresholds"
        class="mt-4 px-4 py-2 bg-orange-500 hover:bg-orange-600 rounded text-sm font-medium transition"
      >
        Save Thresholds
      </button>
    </section>

    <!-- Poster Settings -->
    <section class="bg-[#171717] rounded-lg p-6">
      <h2 class="text-lg font-medium mb-4">Poster Settings</h2>
      <p class="text-sm text-gray-500 mb-4">Settings for scene poster frame extraction (WebP format)</p>
      
      <div class="grid grid-cols-2 gap-4 max-w-md">
        <div>
          <label class="block text-sm text-gray-400 mb-1">Width (px)</label>
          <input 
            v-model="poster.width"
            type="number"
            class="w-full bg-[#262626] text-white px-3 py-2 rounded text-sm focus:outline-none focus:ring-1 focus:ring-orange-500"
          />
        </div>
        <div>
          <label class="block text-sm text-gray-400 mb-1">Quality (1-100)</label>
          <input 
            v-model="poster.quality"
            type="number"
            min="1"
            max="100"
            class="w-full bg-[#262626] text-white px-3 py-2 rounded text-sm focus:outline-none focus:ring-1 focus:ring-orange-500"
          />
        </div>
      </div>
      
      <button 
        @click="savePosterSettings"
        class="mt-4 px-4 py-2 bg-orange-500 hover:bg-orange-600 rounded text-sm font-medium transition"
      >
        Save Poster Settings
      </button>
    </section>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { api } from '../services/api'

const indexerState = ref('unknown')
const watchFolders = ref([])

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

async function loadConfig() {
  try {
    const [state, folders, modelConfig, posterWidth, posterQuality, thresholdVisual, thresholdVisualMatch, thresholdFace] = await Promise.all([
      api.getConfig('indexer_state'),
      api.getConfig('watch_folders'),
      api.getConfig('enrichment_models'),
      api.getConfig('poster_width'),
      api.getConfig('poster_quality'),
      api.getConfig('search_threshold_visual'),
      api.getConfig('search_threshold_visual_match'),
      api.getConfig('search_threshold_face')
    ])
    
    indexerState.value = state.value || 'unknown'
    watchFolders.value = folders.value || []
    
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

onMounted(() => {
  loadConfig()
})
</script>
