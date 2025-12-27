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

      <!-- Progress bar -->
      <div v-if="queue.total > 0" class="mt-4">
        <div class="flex justify-between text-xs text-gray-500 mb-1">
          <span>Progress</span>
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
import { ref, reactive, onMounted } from 'vue'
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
  total: 0
})

const recentFiles = ref([])

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
  } catch (err) {
    console.error('Failed to load queue:', err)
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
  loadRecentFiles()
})
</script>
