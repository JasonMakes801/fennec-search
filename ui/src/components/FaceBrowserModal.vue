<template>
  <div 
    v-if="isOpen" 
    class="fixed inset-0 z-50 flex items-center justify-center bg-black/80"
    @click.self="close"
  >
    <div class="bg-[#171717] rounded-lg w-[90vw] max-w-6xl h-[85vh] flex flex-col">
      <!-- Header with cluster jump tabs -->
      <div class="flex items-center justify-between p-4 border-b border-gray-800">
        <div class="flex items-center gap-4">
          <h2 class="text-lg font-semibold">Browse Faces</h2>
          <span class="text-gray-500 text-sm">{{ totalFaces }} faces in {{ clusters.length }} clusters</span>
        </div>
        <button @click="close" class="text-gray-400 hover:text-white">
          <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>
      
      <!-- Cluster jump tabs (scrollable) -->
      <div class="flex items-center gap-2 px-4 py-2 border-b border-gray-800 overflow-x-auto">
        <span class="text-gray-500 text-xs whitespace-nowrap">Jump to:</span>
        <button
          v-for="cluster in clusters"
          :key="cluster.id"
          @click="scrollToCluster(cluster.id)"
          class="px-2 py-1 text-xs rounded whitespace-nowrap transition"
          :class="activeCluster === cluster.id 
            ? 'bg-orange-600 text-white' 
            : 'bg-[#262626] text-gray-300 hover:bg-[#333]'"
        >
          Cluster {{ cluster.id + 1 }} ({{ cluster.count }})
        </button>
        <button
          v-if="unclusteredCount > 0"
          @click="scrollToCluster(-1)"
          class="px-2 py-1 text-xs rounded whitespace-nowrap transition"
          :class="activeCluster === -1 
            ? 'bg-orange-600 text-white' 
            : 'bg-[#262626] text-gray-300 hover:bg-[#333]'"
        >
          Unclustered ({{ unclusteredCount }})
        </button>
      </div>
      
      <!-- Face grid with cluster sections -->
      <div 
        ref="scrollContainer"
        class="flex-1 overflow-y-auto p-4"
        @scroll="onScroll"
      >
        <!-- Loading state -->
        <div v-if="loading" class="flex items-center justify-center h-full">
          <div class="animate-spin w-8 h-8 border-2 border-orange-500 border-t-transparent rounded-full"></div>
        </div>
        
        <!-- Face clusters -->
        <template v-else>
          <div 
            v-for="cluster in clustersWithFaces" 
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
                <span class="text-gray-500 text-xs">{{ cluster.faces.length }} faces</span>
                <button
                  v-if="cluster.id !== -1 && cluster.faces.length > 0"
                  @click="selectClusterRepresentative(cluster)"
                  class="ml-auto px-3 py-1 text-xs bg-[#262626] text-gray-300 rounded hover:bg-[#333] transition"
                >
                  Filter by this person
                </button>
              </div>
            </div>
            
            <!-- Face thumbnails -->
            <div class="grid grid-cols-6 sm:grid-cols-8 md:grid-cols-10 lg:grid-cols-12 gap-2">
              <div 
                v-for="face in cluster.faces" 
                :key="face.id"
                class="relative cursor-pointer group"
                @click="selectFace(face)"
              >
                <canvas 
                  :ref="el => setFaceCanvas(face.id, el)"
                  width="64" 
                  height="64"
                  class="w-full aspect-square rounded border-2 transition"
                  :class="selectedFaceId === face.id 
                    ? 'border-teal-500' 
                    : 'border-gray-700 group-hover:border-teal-500'"
                ></canvas>
                <!-- Hover overlay -->
                <div class="absolute inset-0 bg-black/60 opacity-0 group-hover:opacity-100 transition flex items-center justify-center">
                  <span class="text-xs text-white">Scene {{ face.scene_index }}</span>
                </div>
              </div>
            </div>
          </div>
        </template>
      </div>
      
      <!-- Footer - just close button -->
      <div class="flex items-center justify-end p-4 border-t border-gray-800">
        <button @click="close" class="px-4 py-2 text-sm bg-[#262626] text-gray-300 rounded hover:bg-[#333]">
          Close
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, nextTick, onMounted } from 'vue'
import { api } from '../services/api'

const props = defineProps({
  isOpen: Boolean
})

const emit = defineEmits(['close', 'select'])

// State
const loading = ref(false)
const clusters = ref([])
const unclusteredCount = ref(0)
const faces = ref([])
const activeCluster = ref(null)
const selectedFaceId = ref(null)
const selectedFace = ref(null)

// Refs
const scrollContainer = ref(null)
const clusterRefs = ref({})
const faceCanvasRefs = ref({})

// Image cache
const imageCache = ref({})

// Helper functions for refs
function setFaceCanvas(faceId, el) {
  if (el) {
    faceCanvasRefs.value[faceId] = el
  }
}

function setClusterRef(clusterId, el) {
  if (el) {
    clusterRefs.value[clusterId] = el
  }
}

// Computed
const totalFaces = computed(() => faces.value.length)

const clustersWithFaces = computed(() => {
  const grouped = {}
  
  // Initialize clusters
  for (const cluster of clusters.value) {
    grouped[cluster.id] = {
      id: cluster.id,
      count: cluster.count,
      faces: []
    }
  }
  
  // Add unclustered group (-1) - always add if we have any faces
  grouped[-1] = {
    id: -1,
    count: unclusteredCount.value,
    faces: []
  }
  
  // Assign faces to clusters
  for (const face of faces.value) {
    // null or -1 both go to unclustered
    const clusterId = (face.cluster_id === null || face.cluster_id === -1) ? -1 : face.cluster_id
    if (grouped[clusterId]) {
      grouped[clusterId].faces.push(face)
    } else {
      // Unknown cluster, put in unclustered
      grouped[-1].faces.push(face)
    }
  }
  
  // Sort: clusters by size desc, unclustered last
  const result = Object.values(grouped)
    .filter(c => c.faces.length > 0)
    .sort((a, b) => {
      if (a.id === -1) return 1
      if (b.id === -1) return -1
      return b.count - a.count
    })
  
  return result
})

// Methods
async function loadFaces() {
  loading.value = true
  try {
    const data = await api.get('/faces/browse')
    clusters.value = data.clusters || []
    unclusteredCount.value = data.unclustered_count || 0
    faces.value = data.faces || []
    
    // Set active cluster to first one
    if (clusters.value.length > 0) {
      activeCluster.value = clusters.value[0].id
    }
    
    // Render face thumbnails after DOM updates
    await nextTick()
    // Small delay to ensure canvases are mounted
    setTimeout(() => renderAllFaces(), 100)
  } catch (err) {
    console.error('Failed to load faces:', err)
  } finally {
    loading.value = false
  }
}

function renderAllFaces() {
  for (const face of faces.value) {
    renderFace(face)
  }
}

async function renderFace(face) {
  const canvas = faceCanvasRefs.value[face.id]
  if (!canvas) return
  
  const ctx = canvas.getContext('2d')
  
  // Get or load image
  let img = imageCache.value[face.poster_path]
  if (!img) {
    img = new Image()
    img.crossOrigin = 'anonymous'
    
    try {
      await new Promise((resolve, reject) => {
        img.onload = resolve
        img.onerror = (e) => reject(new Error(`Failed to load image for face ${face.id}`))
        // Use scene_id to get thumbnail
        img.src = api.thumbnailUrl(face.scene_id)
      })
      
      imageCache.value[face.poster_path] = img
    } catch (err) {
      console.error(err)
      // Draw placeholder
      ctx.fillStyle = '#333'
      ctx.fillRect(0, 0, 64, 64)
      ctx.fillStyle = '#666'
      ctx.font = '10px sans-serif'
      ctx.textAlign = 'center'
      ctx.fillText('Error', 32, 36)
      return
    }
  }
  
  // Calculate crop region
  const [bx, by, bw, bh] = face.bbox
  const padding = 0.3 // 30% padding around face
  const px = bw * padding
  const py = bh * padding
  
  const sx = Math.max(0, bx - px)
  const sy = Math.max(0, by - py)
  const sw = Math.min(img.width - sx, bw + px * 2)
  const sh = Math.min(img.height - sy, bh + py * 2)
  
  // Draw cropped face
  ctx.drawImage(img, sx, sy, sw, sh, 0, 0, 64, 64)
}

function scrollToCluster(clusterId) {
  const el = clusterRefs.value[clusterId]
  if (el && scrollContainer.value) {
    el.scrollIntoView({ behavior: 'smooth', block: 'start' })
    activeCluster.value = clusterId
  }
}

function onScroll() {
  // Update active cluster based on scroll position
  if (!scrollContainer.value) return
  
  const scrollTop = scrollContainer.value.scrollTop
  const containerRect = scrollContainer.value.getBoundingClientRect()
  
  for (const cluster of clustersWithFaces.value) {
    const el = clusterRefs.value[cluster.id]
    if (el) {
      const rect = el.getBoundingClientRect()
      // Check if cluster header is near top of container
      if (rect.top <= containerRect.top + 100 && rect.bottom > containerRect.top) {
        activeCluster.value = cluster.id
        break
      }
    }
  }
}

function selectFace(face) {
  // Immediately emit and close when a face is clicked
  emit('select', face)
  close()
}

function selectClusterRepresentative(cluster) {
  // Select the first face in the cluster (most representative, lowest cluster_order)
  if (cluster.faces.length > 0) {
    selectFace(cluster.faces[0])
  }
}

function close() {
  emit('close')
  selectedFaceId.value = null
  selectedFace.value = null
}

// Watch for modal open
watch(() => props.isOpen, (isOpen) => {
  if (isOpen) {
    loadFaces()
  } else {
    // Clear image cache when closing (save memory)
    imageCache.value = {}
  }
})
</script>
