<template>
  <div class="max-w-4xl mx-auto px-4 py-4">
    <h1 class="text-lg font-semibold mb-4">Settings</h1>

    <!-- Search Thresholds -->
    <section class="bg-[#171717] rounded-sm p-3">
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
  </div>
</template>

<script setup>
import { reactive, onMounted } from 'vue'
import { api } from '../services/api'

const thresholds = reactive({
  visual: 0.10,
  visualMatch: 0.20,
  face: 0.25
})

async function loadConfig() {
  try {
    const [thresholdVisual, thresholdVisualMatch, thresholdFace] = await Promise.all([
      api.getConfig('search_threshold_visual'),
      api.getConfig('search_threshold_visual_match'),
      api.getConfig('search_threshold_face')
    ])

    thresholds.visual = thresholdVisual.value ?? 0.10
    thresholds.visualMatch = thresholdVisualMatch.value ?? 0.20
    thresholds.face = thresholdFace.value ?? 0.25
  } catch (err) {
    console.error('Failed to load config:', err)
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
