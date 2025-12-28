<template>
  <div class="max-w-4xl mx-auto px-4 py-6">
    <h1 class="text-2xl font-semibold mb-6">Report</h1>

    <!-- Stats Cards -->
    <div class="grid grid-cols-4 gap-4 mb-6">
      <div class="bg-[#171717] rounded-lg p-4">
        <div class="text-3xl font-semibold text-orange-500">{{ stats.shots }}</div>
        <div class="text-sm text-gray-400 mt-1">Shots</div>
      </div>
      <div class="bg-[#171717] rounded-lg p-4">
        <div class="text-3xl font-semibold text-orange-500">{{ stats.scenes }}</div>
        <div class="text-sm text-gray-400 mt-1">Scenes</div>
      </div>
      <div class="bg-[#171717] rounded-lg p-4">
        <div class="text-3xl font-semibold text-orange-500">{{ stats.faces }}</div>
        <div class="text-sm text-gray-400 mt-1">Faces</div>
      </div>
      <div class="bg-[#171717] rounded-lg p-4">
        <div class="text-3xl font-semibold text-orange-500">{{ formatDuration(stats.totalDuration) }}</div>
        <div class="text-sm text-gray-400 mt-1">Total Duration</div>
      </div>
    </div>

    <!-- Currently Processing -->
    <section v-if="queue.current" class="bg-[#171717] rounded-lg p-6 mb-6 border border-blue-500/30">
      <div class="flex items-center gap-2 mb-4">
        <div class="w-2 h-2 bg-blue-500 rounded-full animate-pulse"></div>
        <h2 class="text-lg font-medium">Currently Processing</h2>
      </div>
      
      <div class="bg-[#262626] rounded-lg p-4">
        <div class="flex items-center justify-between mb-3">
          <div class="font-medium text-gray-200 truncate">📁 {{ queue.current.filename }}</div>
          <div class="text-xs text-gray-500 flex-shrink-0 ml-2">
            {{ formatDuration(queue.current.duration_seconds) }}
          </div>
        </div>
        
        <!-- Stage indicator -->
        <div class="flex items-center gap-2 mb-3">
          <span class="text-sm text-blue-400">{{ formatStageName(queue.current.current_stage) }}</span>
          <span class="text-xs text-gray-500">(step {{ queue.current.current_stage_num }} of {{ queue.current.total_stages }})</span>
        </div>
        
        <!-- Stage progress bar: shows completed stages + partial for in-progress -->
        <div class="h-2 bg-[#1a1a1a] rounded-full overflow-hidden flex">
          <!-- Completed stages (solid) -->
          <div 
            class="h-full bg-blue-500 transition-all duration-300"
            :style="{ width: `${((queue.current.current_stage_num - 1) / queue.current.total_stages) * 100}%` }"
          ></div>
          <!-- Current stage (animated/pulsing) -->
          <div 
            class="h-full bg-blue-400 animate-pulse"
            :style="{ width: `${(1 / queue.current.total_stages) * 100}%` }"
          ></div>
        </div>
        
        <!-- Stage steps -->
        <div class="flex justify-between mt-2 text-xs">
          <span 
            v-for="(stage, idx) in stages" 
            :key="stage.id"
            :class="[
              idx < queue.current.current_stage_num - 1 ? 'text-blue-400' : 
              idx === queue.current.current_stage_num - 1 ? 'text-blue-300 font-medium' : 'text-gray-600'
            ]"
          >
            {{ stage.short }}
          </span>
        </div>
      </div>
    </section>

    <!-- Queue Status -->
    <section class="bg-[#171717] rounded-lg p-6 mb-6">
      <h2 class="text-lg font-medium mb-4">Enrichment Queue</h2>
      
      <div class="grid grid-cols-4 gap-4 mb-4">
        <div class="text-center">
          <div class="text-2xl font-semibold text-gray-400">{{ queue.pending }}</div>
          <div class="text-xs text-gray-500">Pending</div>
        </div>
        <div class="text-center">
          <div class="text-2xl font-semibold text-blue-400">{{ queue.processing }}</div>
          <div class="text-xs text-gray-500">Processing</div>
        </div>
        <div class="text-center">
          <div class="text-2xl font-semibold text-green-400">{{ queue.complete }}</div>
          <div class="text-xs text-gray-500">Complete</div>
        </div>
        <div class="text-center">
          <div class="text-2xl font-semibold text-red-400">{{ queue.failed }}</div>
          <div class="text-xs text-gray-500">Failed</div>
        </div>
      </div>

      <!-- Overall progress bar -->
      <div v-if="queue.total > 0" class="mt-4">
        <div class="flex justify-between text-xs text-gray-500 mb-1">
          <span>Overall Progress</span>
          <span>{{ Math.round((queue.complete / queue.total) * 100) }}%</span>
        </div>
        <div class="h-2 bg-[#262626] rounded-full overflow-hidden">
          <div 
            class="h-full bg-green-500 transition-all"
            :style="{ width: `${(queue.complete / queue.total) * 100}%` }"
          ></div>
        </div>
      </div>
    </section>

    <!-- Vector Coverage -->
    <section class="bg-[#171717] rounded-lg p-6 mb-6">
      <h2 class="text-lg font-medium mb-4">Vector Coverage</h2>
      
      <div v-if="vectorStats.models.length === 0" class="text-gray-500 text-sm py-4 text-center">
        No embeddings generated yet
      </div>
      
      <div v-else class="space-y-3">
        <div 
          v-for="model in vectorStats.models" 
          :key="model.model"
          class="bg-[#262626] rounded p-3"
        >
          <div class="flex items-center justify-between mb-2">
            <div class="flex items-center gap-2">
              <span class="text-sm font-medium text-gray-200">{{ model.name }}</span>
              <span class="text-xs text-gray-500">{{ model.version }}</span>
              <span class="text-xs bg-[#333] text-gray-400 px-1.5 py-0.5 rounded">{{ model.dimension }}d</span>
            </div>
            <span class="text-sm text-gray-400">
              <template v-if="model.partial_expected">
                {{ model.found }} found in {{ model.scanned }} scanned
              </template>
              <template v-else>
                {{ model.found }}/{{ vectorStats.total_scenes }} scenes
                <span class="text-orange-400">({{ model.coverage }}%)</span>
              </template>
              <span v-if="model.total_detected" class="text-gray-500 ml-1">· {{ model.total_detected }} total</span>
            </span>
          </div>
          <!-- Progress bar: for partial models, show scanned (teal) + found (orange) -->
          <div class="h-1.5 bg-[#1a1a1a] rounded-full overflow-hidden">
            <template v-if="model.partial_expected && vectorStats.total_scenes > 0">
              <!-- Scanned bar with found overlay -->
              <div class="h-full flex">
                <div 
                  class="h-full bg-orange-500"
                  :style="{ width: `${(model.found / vectorStats.total_scenes) * 100}%` }"
                ></div>
                <div 
                  class="h-full bg-teal-600"
                  :style="{ width: `${((model.scanned - model.found) / vectorStats.total_scenes) * 100}%` }"
                ></div>
              </div>
            </template>
            <template v-else>
              <div 
                class="h-full bg-orange-500 transition-all"
                :style="{ width: `${model.coverage}%` }"
              ></div>
            </template>
          </div>
          <!-- Legend for partial models -->
          <div v-if="model.partial_expected" class="flex items-center gap-4 mt-1.5 text-xs text-gray-500">
            <span class="flex items-center gap-1">
              <span class="w-2 h-2 bg-orange-500 rounded-sm"></span>
              {{ model.name === 'Faces' ? 'Has faces' : 'Has dialog' }}
            </span>
            <span class="flex items-center gap-1">
              <span class="w-2 h-2 bg-teal-600 rounded-sm"></span>
              Scanned, none found
            </span>
          </div>
        </div>
      </div>
    </section>

    <!-- Recent Files -->
    <section class="bg-[#171717] rounded-lg p-6">
      <h2 class="text-lg font-medium mb-4">Recent Shots</h2>
      
      <div class="space-y-2">
        <div 
          v-for="file in recentFiles" 
          :key="file.id"
          class="flex items-center justify-between bg-[#262626] rounded px-3 py-2"
        >
          <div class="flex-1 min-w-0">
            <div class="font-medium text-sm truncate">{{ file.filename }}</div>
            <div class="text-xs text-gray-500">
              {{ formatDuration(file.duration_seconds) }} | 
              {{ file.width }}x{{ file.height }} | 
              {{ file.codec }}
            </div>
          </div>
          <div class="text-xs text-gray-500 ml-4 flex-shrink-0">
            {{ formatDate(file.indexed_at) }}
          </div>
        </div>
        
        <div v-if="recentFiles.length === 0" class="text-gray-500 text-sm py-4 text-center">
          No files indexed yet
        </div>
      </div>
    </section>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted } from 'vue'
import { api } from '../services/api'

const stats = reactive({
  shots: 0,
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

const recentFiles = ref([])
let pollInterval = null

// Stage definitions for display
const stages = [
  { id: 'scene_detection', name: 'Scene Detection', short: 'Scenes' },
  { id: 'clip', name: 'CLIP Embeddings', short: 'CLIP' },
  { id: 'whisper', name: 'Whisper Transcription', short: 'Whisper' },
  { id: 'transcript_embed', name: 'Transcript Embeddings', short: 'Transcript' },
  { id: 'arcface', name: 'Face Detection', short: 'Faces' }
]

function formatStageName(stageId) {
  if (!stageId || stageId === 'starting') return 'Starting...'
  const stage = stages.find(s => s.id === stageId)
  return stage ? stage.name : stageId
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
    stats.shots = data.files || 0
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
    const data = await api.getFiles(10)
    recentFiles.value = data.files || []
  } catch (err) {
    console.error('Failed to load recent files:', err)
  }
}

onMounted(() => {
  loadStats()
  loadQueue()
  loadVectorStats()
  loadRecentFiles()
  
  // Poll queue status every 3 seconds for live updates
  pollInterval = setInterval(() => {
    loadQueue()
    // Also refresh stats when processing
    if (queue.processing > 0) {
      loadStats()
      loadVectorStats()
    }
  }, 3000)
})

onUnmounted(() => {
  if (pollInterval) {
    clearInterval(pollInterval)
  }
})
</script>
