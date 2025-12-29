<template>
  <div
    v-if="isOpen"
    class="fixed inset-0 z-50 flex items-center justify-center bg-black/80"
    @click.self="close"
  >
    <div class="bg-[#171717] rounded-lg w-[90vw] max-w-6xl h-[85vh] flex flex-col">
      <!-- Header -->
      <div class="flex items-center justify-between p-4 border-b border-gray-800">
        <div class="flex items-center gap-4">
          <h2 class="text-lg font-semibold">Browse Visual Groups</h2>
          <span class="text-gray-500 text-sm">
            {{ isFiltered ? `${clusters.length} clusters` : `${totalScenes} scenes in ${clusters.length} clusters` }}
          </span>
          <span v-if="isFiltered" class="text-xs bg-violet-600/30 text-violet-300 px-2 py-0.5 rounded">
            Filtered to selection
          </span>
        </div>
        <button @click="close" class="text-gray-400 hover:text-white">
          <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      <!-- Cluster jump tabs (scrollable) - only show when unfiltered -->
      <div v-if="!isFiltered" class="flex items-center gap-2 px-4 py-2 border-b border-gray-800 overflow-x-auto">
        <span class="text-gray-500 text-xs whitespace-nowrap">Jump to:</span>
        <button
          v-for="cluster in clusters"
          :key="cluster.id"
          @click="scrollToCluster(cluster.id)"
          class="px-2 py-1 text-xs rounded whitespace-nowrap transition"
          :class="activeCluster === cluster.id
            ? 'bg-violet-600 text-white'
            : 'bg-[#262626] text-gray-300 hover:bg-[#333]'"
        >
          Cluster {{ cluster.id + 1 }} ({{ cluster.count }})
        </button>
        <button
          v-if="unclusteredCount > 0"
          @click="scrollToCluster(-1)"
          class="px-2 py-1 text-xs rounded whitespace-nowrap transition"
          :class="activeCluster === -1
            ? 'bg-violet-600 text-white'
            : 'bg-[#262626] text-gray-300 hover:bg-[#333]'"
        >
          Unclustered ({{ unclusteredCount }})
        </button>
      </div>

      <!-- Scene grid -->
      <div
        ref="scrollContainer"
        class="flex-1 overflow-y-auto p-4"
        @scroll="onScroll"
      >
        <!-- Loading state -->
        <div v-if="loading" class="flex items-center justify-center h-full">
          <div class="animate-spin w-8 h-8 border-2 border-violet-500 border-t-transparent rounded-full"></div>
        </div>

        <!-- Filtered view: grid of cluster representatives -->
        <template v-else-if="isFiltered">
          <div class="grid grid-cols-4 sm:grid-cols-5 md:grid-cols-6 lg:grid-cols-8 gap-4">
            <div
              v-for="cluster in clustersWithScenes"
              :key="cluster.id"
              class="flex flex-col items-center"
            >
              <!-- Representative scene -->
              <div
                v-if="cluster.scenes.length > 0"
                class="relative cursor-pointer group"
                @click="selectScene(cluster.scenes[0])"
              >
                <img
                  :src="api.thumbnailUrl(cluster.scenes[0].id)"
                  class="w-full aspect-video rounded border-2 transition object-cover"
                  :class="selectedSceneId === cluster.scenes[0].id
                    ? 'border-violet-500'
                    : 'border-gray-700 group-hover:border-violet-500'"
                />
              </div>
              <!-- Cluster info and match button -->
              <span class="text-gray-500 text-xs mt-1">{{ cluster.count }} members</span>
              <button
                v-if="cluster.id !== -1 && cluster.scenes.length > 0"
                @click="selectClusterRepresentative(cluster)"
                class="mt-1 px-2 py-0.5 text-xs bg-[#262626] text-gray-300 rounded hover:bg-[#333] transition"
              >
                Match
              </button>
            </div>
          </div>
        </template>

        <!-- Unfiltered view: full cluster sections -->
        <template v-else>
          <div
            v-for="cluster in clustersWithScenes"
            :key="cluster.id"
            :ref="el => setClusterRef(cluster.id, el)"
            class="mb-8"
          >
            <!-- Cluster header (sticky) -->
            <div class="sticky top-0 bg-[#171717] py-2 mb-3 z-10 border-b border-gray-800">
              <div class="flex items-center gap-3">
                <h3 class="text-sm font-medium text-gray-300">
                  {{ cluster.id === -1 ? 'Unclustered' : `Cluster ${cluster.id + 1}` }}
                </h3>
                <span class="text-gray-500 text-xs">{{ cluster.scenes.length }} scenes</span>
                <button
                  v-if="cluster.id !== -1 && cluster.scenes.length > 0"
                  @click="selectClusterRepresentative(cluster)"
                  class="ml-auto px-3 py-1 text-xs bg-[#262626] text-gray-300 rounded hover:bg-[#333] transition"
                >
                  Match by this visual
                </button>
              </div>
            </div>

            <!-- Scene thumbnails -->
            <div class="grid grid-cols-4 sm:grid-cols-5 md:grid-cols-6 lg:grid-cols-8 gap-2">
              <div
                v-for="scene in cluster.scenes"
                :key="scene.id"
                class="relative cursor-pointer group"
                @click="selectScene(scene)"
              >
                <img
                  :src="api.thumbnailUrl(scene.id)"
                  class="w-full aspect-video rounded border-2 transition object-cover"
                  :class="selectedSceneId === scene.id
                    ? 'border-violet-500'
                    : 'border-gray-700 group-hover:border-violet-500'"
                />
                <!-- Hover overlay -->
                <div class="absolute inset-0 bg-black/60 opacity-0 group-hover:opacity-100 transition flex items-center justify-center rounded">
                  <span class="text-xs text-white">Scene {{ scene.scene_index }}</span>
                </div>
              </div>
            </div>
          </div>
        </template>
      </div>

      <!-- Footer -->
      <div class="flex items-center justify-end p-4 border-t border-gray-800">
        <button @click="close" class="px-4 py-2 text-sm bg-[#262626] text-gray-300 rounded hover:bg-[#333]">
          Close
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { api } from '../services/api'

const props = defineProps({
  isOpen: Boolean,
  sceneIds: {
    type: Array,
    default: null  // null = all scenes, array = filter to these scene IDs
  }
})

const emit = defineEmits(['close', 'select'])

// State
const loading = ref(false)
const clusters = ref([])
const unclusteredCount = ref(0)
const scenes = ref([])
const activeCluster = ref(null)
const selectedSceneId = ref(null)
const isFiltered = ref(false)

// Refs
const scrollContainer = ref(null)
const clusterRefs = ref({})

// Helper function for refs
function setClusterRef(clusterId, el) {
  if (el) {
    clusterRefs.value[clusterId] = el
  }
}

// Computed
const totalScenes = computed(() => scenes.value.length)

const clustersWithScenes = computed(() => {
  const grouped = {}

  // Initialize clusters
  for (const cluster of clusters.value) {
    grouped[cluster.id] = {
      id: cluster.id,
      count: cluster.count,
      scenes: []
    }
  }

  // Add unclustered group (-1)
  grouped[-1] = {
    id: -1,
    count: unclusteredCount.value,
    scenes: []
  }

  // Assign scenes to clusters
  for (const scene of scenes.value) {
    const clusterId = (scene.cluster_id === null || scene.cluster_id === -1) ? -1 : scene.cluster_id
    if (grouped[clusterId]) {
      grouped[clusterId].scenes.push(scene)
    } else {
      grouped[-1].scenes.push(scene)
    }
  }

  // Sort: clusters by size desc, unclustered last
  const result = Object.values(grouped)
    .filter(c => c.scenes.length > 0)
    .sort((a, b) => {
      if (a.id === -1) return 1
      if (b.id === -1) return -1
      return b.count - a.count
    })

  return result
})

// Methods
async function loadScenes() {
  loading.value = true
  try {
    let url = '/scenes/browse'
    if (props.sceneIds && props.sceneIds.length > 0) {
      url += `?scene_ids=${props.sceneIds.join(',')}`
    }
    const data = await api.get(url)
    clusters.value = data.clusters || []
    unclusteredCount.value = data.unclustered_count || 0
    scenes.value = data.scenes || []
    isFiltered.value = data.filtered || false

    // Set active cluster to first one
    if (clusters.value.length > 0) {
      activeCluster.value = clusters.value[0].id
    }
  } catch (err) {
    console.error('Failed to load scenes:', err)
  } finally {
    loading.value = false
  }
}

function scrollToCluster(clusterId) {
  const el = clusterRefs.value[clusterId]
  if (el && scrollContainer.value) {
    el.scrollIntoView({ behavior: 'smooth', block: 'start' })
    activeCluster.value = clusterId
  }
}

function onScroll() {
  if (!scrollContainer.value) return

  const containerRect = scrollContainer.value.getBoundingClientRect()

  for (const cluster of clustersWithScenes.value) {
    const el = clusterRefs.value[cluster.id]
    if (el) {
      const rect = el.getBoundingClientRect()
      if (rect.top <= containerRect.top + 100 && rect.bottom > containerRect.top) {
        activeCluster.value = cluster.id
        break
      }
    }
  }
}

function selectScene(scene) {
  emit('select', scene)
  close()
}

function selectClusterRepresentative(cluster) {
  if (cluster.scenes.length > 0) {
    selectScene(cluster.scenes[0])
  }
}

function close() {
  emit('close')
  selectedSceneId.value = null
}

// Watch for modal open
watch(() => props.isOpen, (isOpen) => {
  if (isOpen) {
    loadScenes()
  }
})
</script>
