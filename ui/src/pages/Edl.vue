<template>
  <div class="max-w-4xl mx-auto px-4 py-4">
    <div class="flex items-center justify-between mb-4">
      <h1 class="text-lg font-semibold">EDL Export</h1>
      <button
        v-if="scenes.length > 0"
        @click="clearAll"
        class="px-2.5 py-1 bg-red-600/20 hover:bg-red-600/40 text-red-400 rounded-sm text-xs transition"
      >
        Clear All
      </button>
    </div>

    <!-- Empty state -->
    <div v-if="scenes.length === 0" class="bg-[#171717] rounded-sm p-8 text-center">
      <p class="text-gray-400 text-sm mb-2">No scenes added to EDL</p>
      <p class="text-gray-500 text-xs">Use the + button in the scene player to add scenes here</p>
    </div>

    <!-- Scene list -->
    <div v-else class="space-y-2 mb-6">
      <div
        v-for="(scene, idx) in scenes"
        :key="scene.sceneId"
        class="bg-[#171717] rounded-sm p-3"
      >
        <div class="flex items-start gap-3">
          <!-- Reorder buttons -->
          <div class="flex flex-col gap-0.5 pt-1">
            <button
              @click="moveUp(idx)"
              :disabled="idx === 0"
              class="p-0.5 rounded hover:bg-[#333] disabled:opacity-30 disabled:cursor-not-allowed transition"
              title="Move up"
            >
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 15l7-7 7 7"/>
              </svg>
            </button>
            <button
              @click="moveDown(idx)"
              :disabled="idx === scenes.length - 1"
              class="p-0.5 rounded hover:bg-[#333] disabled:opacity-30 disabled:cursor-not-allowed transition"
              title="Move down"
            >
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/>
              </svg>
            </button>
          </div>

          <!-- Thumbnail -->
          <img
            :src="`/api/thumbnail/${scene.sceneId}`"
            :alt="scene.filename"
            class="w-20 h-8 object-cover rounded-sm flex-shrink-0"
          />

          <!-- Scene info -->
          <div class="flex-1 min-w-0">
            <div class="flex items-center gap-2 mb-2">
              <span class="text-gray-500 text-xs">{{ idx + 1 }}.</span>
              <span class="font-mono text-xs truncate">{{ scene.filename }}</span>
            </div>

            <!-- TC inputs -->
            <div class="flex flex-wrap items-center gap-4 text-xs">
              <div class="flex items-center gap-1.5">
                <span class="text-gray-500">In:</span>
                <input
                  type="text"
                  :value="formatTc(scene.inTc, scene.fps)"
                  @blur="updateInTc(idx, $event)"
                  class="font-mono bg-[#262626] border border-[#333] rounded px-2 py-1 w-28 text-center focus:border-blue-500 focus:outline-none"
                />
              </div>
              <div class="flex items-center gap-1.5">
                <span class="text-gray-500">Out:</span>
                <input
                  type="text"
                  :value="formatTc(scene.outTc, scene.fps)"
                  @blur="updateOutTc(idx, $event)"
                  class="font-mono bg-[#262626] border border-[#333] rounded px-2 py-1 w-28 text-center focus:border-blue-500 focus:outline-none"
                />
              </div>
              <div class="flex items-center gap-1.5 text-gray-500">
                <span>Duration:</span>
                <span class="font-mono">{{ formatTc(scene.outTc - scene.inTc, scene.fps) }}</span>
              </div>
            </div>
          </div>

          <!-- Remove button -->
          <button
            @click="removeScene(idx)"
            class="p-1 text-gray-500 hover:text-red-400 transition"
            title="Remove"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
            </svg>
          </button>
        </div>
      </div>
    </div>

    <!-- Export button -->
    <div v-if="scenes.length > 0" class="flex justify-center">
      <button
        @click="exportEdl"
        :disabled="exporting"
        class="px-8 py-3 bg-amber-600 hover:bg-amber-500 disabled:bg-amber-600/50 rounded-sm text-sm font-medium transition"
      >
        {{ exporting ? 'Exporting...' : 'Export EDL' }}
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'

const scenes = ref([])
const exporting = ref(false)

const STORAGE_KEY = 'fennec_edl_scenes'

// Load from localStorage on mount
onMounted(() => {
  const saved = localStorage.getItem(STORAGE_KEY)
  if (saved) {
    try {
      scenes.value = JSON.parse(saved)
    } catch (e) {
      console.error('Failed to parse saved EDL scenes:', e)
    }
  }
})

// Save to localStorage on change
watch(scenes, (val) => {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(val))
}, { deep: true })

// Format seconds to SMPTE timecode
function formatTc(seconds, fps = 29.97) {
  const totalFrames = Math.round(seconds * fps)
  const frames = totalFrames % Math.round(fps)
  const totalSecs = Math.floor(totalFrames / Math.round(fps))
  const secs = totalSecs % 60
  const totalMins = Math.floor(totalSecs / 60)
  const mins = totalMins % 60
  const hours = Math.floor(totalMins / 60)
  return `${String(hours).padStart(2, '0')}:${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}:${String(frames).padStart(2, '0')}`
}

// Parse SMPTE timecode to seconds
function parseTc(tc, fps = 29.97) {
  const match = tc.match(/^(\d{1,2}):(\d{2}):(\d{2}):(\d{2})$/)
  if (!match) return null
  const [, h, m, s, f] = match.map(Number)
  const totalFrames = h * 3600 * fps + m * 60 * fps + s * fps + f
  return totalFrames / fps
}

function updateInTc(idx, event) {
  const parsed = parseTc(event.target.value, scenes.value[idx].fps)
  if (parsed !== null) {
    scenes.value[idx].inTc = parsed
  }
  // Reset to current value if invalid
  event.target.value = formatTc(scenes.value[idx].inTc, scenes.value[idx].fps)
}

function updateOutTc(idx, event) {
  const parsed = parseTc(event.target.value, scenes.value[idx].fps)
  if (parsed !== null) {
    scenes.value[idx].outTc = parsed
  }
  // Reset to current value if invalid
  event.target.value = formatTc(scenes.value[idx].outTc, scenes.value[idx].fps)
}

function moveUp(idx) {
  if (idx > 0) {
    const item = scenes.value.splice(idx, 1)[0]
    scenes.value.splice(idx - 1, 0, item)
  }
}

function moveDown(idx) {
  if (idx < scenes.value.length - 1) {
    const item = scenes.value.splice(idx, 1)[0]
    scenes.value.splice(idx + 1, 0, item)
  }
}

function removeScene(idx) {
  scenes.value.splice(idx, 1)
}

function clearAll() {
  if (confirm('Remove all scenes from the EDL?')) {
    scenes.value = []
  }
}

async function exportEdl() {
  if (scenes.value.length === 0) return

  exporting.value = true
  try {
    const response = await fetch('/api/export/edl', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        title: 'Fennec Export',
        scenes: scenes.value.map(s => ({
          sceneId: s.sceneId,
          inTc: s.inTc,
          outTc: s.outTc
        }))
      })
    })

    if (!response.ok) {
      throw new Error('Export failed')
    }

    // Download the file
    const blob = await response.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'Fennec Export.edl'
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  } catch (e) {
    console.error('Export failed:', e)
    alert('Failed to export EDL')
  } finally {
    exporting.value = false
  }
}
</script>
