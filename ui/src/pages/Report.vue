<template>
  <div class="max-w-4xl mx-auto px-4 py-4">
    <h1 class="text-lg font-semibold mb-4">Report</h1>

    <!-- Stats Cards -->
    <div class="grid grid-cols-4 gap-2 mb-4">
      <div class="bg-[#171717] rounded-sm p-2">
        <div class="text-xl font-semibold text-orange-500">{{ stats.files }}</div>
        <div class="text-[10px] text-gray-400 mt-0.5">Files</div>
      </div>
      <div class="bg-[#171717] rounded-sm p-2">
        <div class="text-xl font-semibold text-orange-500">{{ stats.scenes }}</div>
        <div class="text-[10px] text-gray-400 mt-0.5">Scenes</div>
      </div>
      <div class="bg-[#171717] rounded-sm p-2">
        <div class="text-xl font-semibold text-orange-500">{{ stats.faces }}</div>
        <div class="text-[10px] text-gray-400 mt-0.5">Faces</div>
      </div>
      <div class="bg-[#171717] rounded-sm p-2">
        <div class="text-xl font-semibold text-orange-500">{{ formatDuration(stats.totalDuration) }}</div>
        <div class="text-[10px] text-gray-400 mt-0.5">Total Duration</div>
      </div>
    </div>

    <!-- Processing Progress (shown when scanning or processing) -->
    <section v-if="isProcessing" class="bg-[#171717] rounded-sm p-3 mb-4">
      <!-- Overall progress bar -->
      <div class="mb-3">
        <div class="flex justify-between text-xs mb-1.5">
          <span class="text-gray-300">Processing Files</span>
          <span class="text-gray-400">{{ queue.complete }} / {{ queue.total }} complete</span>
        </div>
        <div class="h-1.5 bg-[#262626] rounded-sm overflow-hidden">
          <div
            class="h-full bg-orange-500 transition-all duration-300"
            :style="{ width: `${progressPercent}%` }"
          ></div>
        </div>
      </div>

      <!-- Current file with spinner -->
      <div v-if="queue.current" class="flex items-center gap-2 bg-[#262626] rounded-sm p-2">
        <div class="w-4 h-4 border-2 border-orange-500 border-t-transparent rounded-full animate-spin flex-shrink-0"></div>
        <div class="flex-1 min-w-0">
          <div class="text-xs text-gray-200 truncate">{{ queue.current.filename }}</div>
          <div class="text-[10px] text-orange-400">{{ formatStageName(queue.current.current_stage) }}</div>
        </div>
      </div>

      <!-- Scanning indicator (when discovering files) -->
      <div v-else-if="scanProgress.phase !== 'idle' && scanProgress.phase !== 'complete'" class="flex items-center gap-2 bg-[#262626] rounded-sm p-2">
        <div class="w-4 h-4 border-2 border-yellow-500 border-t-transparent rounded-full animate-spin flex-shrink-0"></div>
        <div class="flex-1">
          <div class="text-xs text-gray-200">{{ formatScanPhase(scanProgress.phase) }}</div>
          <div v-if="scanProgress.files_found > 0" class="text-[10px] text-yellow-400">
            Found {{ scanProgress.files_found }} files
          </div>
        </div>
      </div>

      <!-- Pending/Failed counts -->
      <div class="flex items-center gap-3 mt-2 text-[10px] text-gray-500">
        <span v-if="queue.pending > 0">{{ queue.pending }} pending</span>
        <span v-if="queue.failed > 0" class="text-red-400">{{ queue.failed }} failed</span>
      </div>
    </section>

    <!-- Idle state - everything complete -->
    <section v-else-if="queue.total > 0" class="bg-[#171717] rounded-sm p-3 mb-4">
      <div class="flex items-center gap-2">
        <div class="w-6 h-6 bg-green-500/20 rounded-sm flex items-center justify-center flex-shrink-0">
          <svg class="w-4 h-4 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/>
          </svg>
        </div>
        <div>
          <div class="text-xs text-gray-200">All files processed</div>
          <div class="text-[10px] text-gray-500">{{ queue.complete }} files complete</div>
        </div>
      </div>
    </section>

    <!-- Empty state -->
    <section v-else class="bg-[#171717] rounded-sm p-3 mb-4">
      <div class="text-center text-gray-500 text-xs py-3">
        No files in queue. Add video files to your watch folder to begin.
      </div>
    </section>

    <!-- Details Section (collapsible) -->
    <div class="border border-[#333] rounded-sm overflow-hidden">
      <button
        @click="showDetails = !showDetails"
        class="w-full px-3 py-2 bg-[#171717] hover:bg-[#1a1a1a] flex items-center justify-between text-xs transition"
      >
        <span class="text-gray-300 font-medium">Details</span>
        <svg
          class="w-3 h-3 text-gray-500 transition-transform"
          :class="{ 'rotate-180': showDetails }"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/>
        </svg>
      </button>

      <div v-show="showDetails" class="bg-[#0d0d0d] border-t border-[#333]">
        <!-- Vector Coverage -->
        <div class="p-3 border-b border-[#262626]">
          <h3 class="text-xs font-medium text-gray-400 mb-2">Vector Coverage</h3>

          <div v-if="vectorStats.models.length === 0" class="text-gray-500 text-[10px]">
            No embeddings generated yet
          </div>

          <div v-else class="space-y-1.5">
            <div
              v-for="model in vectorStats.models"
              :key="model.model"
              class="flex items-center gap-2"
            >
              <span class="text-[10px] text-gray-300 w-20">{{ model.name }}</span>
              <div class="flex-1 h-1 bg-[#262626] rounded-sm overflow-hidden flex">
                <!-- Scenes with content (orange) -->
                <div
                  class="h-full bg-orange-500"
                  :style="{ width: `${model.coverage}%` }"
                ></div>
                <!-- Scenes scanned but no content - only for partial_expected models (blue) -->
                <div
                  v-if="model.partial_expected && getScannedWithoutContent(model) > 0"
                  class="h-full bg-blue-500/60"
                  :style="{ width: `${getScannedWithoutContent(model)}%` }"
                ></div>
              </div>
              <span class="text-[10px] text-gray-500 w-12 text-right">{{ model.found }}/{{ vectorStats.total_scenes }}</span>
            </div>
          </div>

          <!-- Legend -->
          <div v-if="hasPartialModels" class="flex items-center gap-3 mt-2 text-[10px] text-gray-500">
            <span class="flex items-center gap-1">
              <span class="w-2 h-2 bg-orange-500 rounded-sm"></span>
              With content
            </span>
            <span class="flex items-center gap-1">
              <span class="w-2 h-2 bg-blue-500/60 rounded-sm"></span>
              No dialog/faces
            </span>
            <span class="flex items-center gap-1">
              <span class="w-2 h-2 bg-[#262626] rounded-sm"></span>
              Not processed
            </span>
          </div>
        </div>

        <!-- Recent Files -->
        <div class="p-3">
          <h3 class="text-xs font-medium text-gray-400 mb-2">Recent Files</h3>

          <div class="space-y-1">
            <div
              v-for="file in recentFiles"
              :key="file.id"
              class="flex items-center justify-between text-[10px]"
            >
              <span class="text-gray-300 truncate flex-1 mr-3">{{ file.filename }}</span>
              <span class="text-gray-500 flex-shrink-0">{{ formatDate(file.indexed_at) }}</span>
            </div>

            <div v-if="recentFiles.length === 0" class="text-gray-500 text-[10px]">
              No files indexed yet
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { api } from '../services/api'

const route = useRoute()

const stats = reactive({
  files: 0,
  scenes: 0,
  faces: 0,
  totalDuration: 0
})

const queue = reactive({
  pending: 0,
  processing: 0,
  complete: 0,
  failed: 0,
  total: 0,
  current: null
})

const vectorStats = reactive({
  total_scenes: 0,
  models: []
})

const scanProgress = reactive({
  phase: 'idle',
  current_folder: null,
  dirs_scanned: 0,
  files_found: 0,
  files_processed: 0,
  files_new: 0,
  files_updated: 0,
  files_skipped: 0
})

const recentFiles = ref([])
const showDetails = ref(false)
let pollInterval = null

// Stage definitions for display
const stages = [
  { id: 'metadata', name: 'Extracting metadata' },
  { id: 'scene_detection', name: 'Detecting scenes' },
  { id: 'clip', name: 'Generating visual embeddings' },
  { id: 'whisper', name: 'Transcribing audio' },
  { id: 'transcript_embed', name: 'Embedding transcripts' },
  { id: 'arcface', name: 'Detecting faces' }
]

// Computed
const isProcessing = computed(() => {
  return queue.pending > 0 || queue.processing > 0 || (scanProgress.phase !== 'idle' && scanProgress.phase !== 'complete')
})

const progressPercent = computed(() => {
  if (queue.total === 0) return 0
  return Math.round((queue.complete / queue.total) * 100)
})

const hasPartialModels = computed(() => {
  return vectorStats.models.some(m => m.partial_expected)
})

// Calculate percentage of scenes scanned but without content for partial models
function getScannedWithoutContent(model) {
  if (!model.partial_expected || vectorStats.total_scenes === 0) return 0
  const scannedPercent = (model.scanned / vectorStats.total_scenes) * 100
  const foundPercent = model.coverage
  return Math.max(0, scannedPercent - foundPercent)
}

// Methods
function formatStageName(stageId) {
  if (!stageId || stageId === 'starting') return 'Starting...'
  const stage = stages.find(s => s.id === stageId)
  return stage ? stage.name : stageId
}

function formatScanPhase(phase) {
  const phases = {
    'idle': '',
    'discovering': 'Scanning for video files...',
    'processing': 'Adding files to database...',
    'checking_missing': 'Checking for removed files...',
    'complete': 'Scan complete'
  }
  return phases[phase] || phase
}

function formatDuration(seconds) {
  if (!seconds) return '0:00'
  const hrs = Math.floor(seconds / 3600)
  const mins = Math.floor((seconds % 3600) / 60)
  const secs = Math.floor(seconds % 60)
  if (hrs > 0) {
    return `${hrs}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
  }
  return `${mins}:${secs.toString().padStart(2, '0')}`
}

function formatDate(dateStr) {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

async function loadStats() {
  try {
    const data = await api.getStats()
    stats.files = data.files || 0
    stats.scenes = data.scenes || 0
    stats.faces = data.faces || 0
    stats.totalDuration = data.total_duration || 0
  } catch (err) {
    console.error('Failed to load stats:', err)
  }
}

async function loadQueue() {
  try {
    const data = await api.getQueue()
    queue.pending = data.pending || 0
    queue.processing = data.processing || 0
    queue.complete = data.complete || 0
    queue.failed = data.failed || 0
    queue.total = queue.pending + queue.processing + queue.complete + queue.failed
    queue.current = data.current || null
  } catch (err) {
    console.error('Failed to load queue:', err)
  }
}

async function loadVectorStats() {
  try {
    const data = await api.getVectorStats()
    vectorStats.total_scenes = data.total_scenes || 0
    vectorStats.models = data.models || []
  } catch (err) {
    console.error('Failed to load vector stats:', err)
  }
}

async function loadRecentFiles() {
  try {
    const data = await api.getFiles(5)
    recentFiles.value = data.files || []
  } catch (err) {
    console.error('Failed to load recent files:', err)
  }
}

async function loadScanProgress() {
  try {
    const data = await api.getScanProgress()
    scanProgress.phase = data.phase || 'idle'
    scanProgress.current_folder = data.current_folder || null
    scanProgress.dirs_scanned = data.dirs_scanned || 0
    scanProgress.files_found = data.files_found || 0
    scanProgress.files_processed = data.files_processed || 0
    scanProgress.files_new = data.files_new || 0
    scanProgress.files_updated = data.files_updated || 0
    scanProgress.files_skipped = data.files_skipped || 0
  } catch (err) {
    console.error('Failed to load scan progress:', err)
  }
}

function loadAll() {
  loadStats()
  loadQueue()
  loadVectorStats()
  loadRecentFiles()
  loadScanProgress()
}

// Reload data when navigating to this page
watch(() => route.path, (newPath) => {
  if (newPath === '/report') {
    loadAll()
  }
})

onMounted(() => {
  loadAll()

  // Track previous processing state to detect completion
  let prevProcessingCount = 0

  // Poll for live updates every 2 seconds
  pollInterval = setInterval(async () => {
    const wasProcessing = prevProcessingCount > 0

    await Promise.all([loadQueue(), loadScanProgress()])

    const currentlyProcessing = queue.processing > 0 || (scanProgress.phase !== 'idle' && scanProgress.phase !== 'complete')

    // Refresh stats when processing or scanning
    if (currentlyProcessing) {
      loadStats()
      loadVectorStats()
    }

    // Refresh all data when processing just completed
    if (wasProcessing && !currentlyProcessing) {
      loadStats()
      loadVectorStats()
      loadRecentFiles()
    }

    prevProcessingCount = queue.processing + queue.pending
  }, 2000)
})

onUnmounted(() => {
  if (pollInterval) {
    clearInterval(pollInterval)
  }
})
</script>
