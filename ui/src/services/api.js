// API service for communicating with FastAPI backend
import { reactive } from 'vue'

const API_BASE = '/api'

// Shared server status state - updated by App.vue, read by Search.vue
export const serverStatus = reactive({
  modelsReady: false,
  clipLoaded: false,
  sentenceLoaded: false,
  indexerState: 'offline'
})

async function fetchJSON(url, options = {}) {
  const response = await fetch(API_BASE + url, {
    headers: {
      'Content-Type': 'application/json',
      ...options.headers
    },
    ...options
  })
  
  if (!response.ok) {
    throw new Error(`API error: ${response.status}`)
  }
  
  return response.json()
}

export const api = {
  // Search with combined filters
  async search(params) {
    const query = new URLSearchParams()
    if (params.visual) query.set('visual', params.visual)
    if (params.visual_threshold) query.set('visual_threshold', params.visual_threshold)
    if (params.transcript) query.set('transcript', params.transcript)
    if (params.transcript_semantic) query.set('transcript_semantic', params.transcript_semantic)
    if (params.transcript_threshold) query.set('transcript_threshold', params.transcript_threshold)
    if (params.face_scene !== undefined) query.set('face_scene', params.face_scene)
    if (params.face_index !== undefined) query.set('face_index', params.face_index)
    if (params.face_id !== undefined) query.set('face_id', params.face_id)
    if (params.face_threshold) query.set('face_threshold', params.face_threshold)
    if (params.visual_match_scene_id !== undefined) query.set('visual_match_scene_id', params.visual_match_scene_id)
    if (params.visual_match_threshold) query.set('visual_match_threshold', params.visual_match_threshold)
    if (params.tc_min !== undefined) query.set('tc_min', params.tc_min)
    if (params.tc_max !== undefined) query.set('tc_max', params.tc_max)
    // Metadata filters
    if (params.path) query.set('path', params.path)
    if (params.duration_min !== undefined) query.set('duration_min', params.duration_min)
    if (params.duration_max !== undefined) query.set('duration_max', params.duration_max)
    if (params.width_min !== undefined) query.set('width_min', params.width_min)
    if (params.width_max !== undefined) query.set('width_max', params.width_max)
    if (params.height_min !== undefined) query.set('height_min', params.height_min)
    if (params.height_max !== undefined) query.set('height_max', params.height_max)
    if (params.fps_min !== undefined) query.set('fps_min', params.fps_min)
    if (params.fps_max !== undefined) query.set('fps_max', params.fps_max)
    if (params.codec) query.set('codec', params.codec)
    
    return fetchJSON(`/search?${query}`)
  },
  
  // Generic GET for any endpoint
  async get(endpoint) {
    return fetchJSON(endpoint)
  },
  
  // Thumbnail URL for a scene (by scene_id)
  thumbnailUrl(sceneId) {
    return `${API_BASE}/thumbnail/${sceneId}`
  },
  
  // Get scenes (paginated browse)
  async getScenes(limit = 40, offset = 0) {
    return fetchJSON(`/scenes?limit=${limit}&offset=${offset}`)
  },
  
  // Get single scene details
  async getScene(sceneIndex) {
    return fetchJSON(`/scene/${sceneIndex}`)
  },
  
  // Files
  async getFiles(limit = 10, completed = false) {
    return fetchJSON(`/files?limit=${limit}&completed=${completed}`)
  },
  
  async getFile(id) {
    return fetchJSON(`/files/${id}`)
  },
  
  // Stats
  async getStats() {
    return fetchJSON('/stats')
  },

  async getReady() {
    return fetchJSON('/ready')
  },
  
  // Vector stats (coverage by model)
  async getVectorStats() {
    return fetchJSON('/stats/vectors')
  },

  // Faces
  async getFaces(params = {}) {
    const query = new URLSearchParams()
    if (params.limit) query.set('limit', params.limit)
    return fetchJSON(`/faces?${query}`)
  },
  
  // Queue
  async getQueue() {
    return fetchJSON('/queue')
  },

  // Scan progress
  async getScanProgress() {
    return fetchJSON('/scan/progress')
  },

  // Config
  async getConfig(key) {
    return fetchJSON(`/config/${key}`)
  },
  
  async setConfig(key, value) {
    return fetchJSON(`/config/${key}`, {
      method: 'PUT',
      body: JSON.stringify({ value })
    })
  },

  // Watch folders with accessibility status
  async getWatchFolders() {
    return fetchJSON('/watch-folders')
  },

  // Admin
  async getAdminStatus() {
    return fetchJSON('/admin/status')
  },

  async resetFailedJobs() {
    return fetchJSON('/admin/reset-failed-jobs', { method: 'POST' })
  },

  async resetProcessingJobs() {
    return fetchJSON('/admin/reset-processing-jobs', { method: 'POST' })
  },

  async purgeDeleted() {
    return fetchJSON('/admin/purge-deleted', { method: 'POST' })
  },

  async purgeOrphans() {
    return fetchJSON('/admin/purge-orphans', { method: 'POST' })
  },

  async wipeDatabase() {
    return fetchJSON('/admin/database', { method: 'DELETE' })
  },

  async restartServer() {
    return fetchJSON('/admin/restart-server', { method: 'POST' })
  }
}
