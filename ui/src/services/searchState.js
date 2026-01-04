// Shared search state - persists across page navigation, clears on app restart
import { reactive, ref } from 'vue'

// Module-level state persists when components unmount/remount
// but resets when the app is refreshed or restarted

export const searchFilters = reactive({
  visual: '',
  dialog: ''
})

export const searchThresholds = reactive({
  visual: '0.10',
  face: '0.25',
  visualMatch: '0.20',
  dialog: '0.35'
})

export const dialogSearchMode = ref('keyword')
export const faceFilter = ref(null)
export const visualMatch = ref(null)
export const metadataFilters = ref([])
export const filterOrder = ref([])

// Results state (so user sees previous results when returning to page)
export const searchResults = ref([])
export const totalScenes = ref(0)
export const currentOffset = ref(0)
export const isSearchMode = ref(false)

// UI preferences
export const thumbnailColumns = ref(5)

// Reset all search state (called by Reset button)
export function resetSearchState(defaultThresholds) {
  searchFilters.visual = ''
  searchFilters.dialog = ''
  searchThresholds.visual = String(defaultThresholds?.visual ?? 0.10)
  searchThresholds.face = String(defaultThresholds?.face ?? 0.25)
  searchThresholds.visualMatch = String(defaultThresholds?.visualMatch ?? 0.20)
  searchThresholds.dialog = String(defaultThresholds?.dialog ?? 0.35)
  dialogSearchMode.value = 'semantic'
  faceFilter.value = null
  visualMatch.value = null
  metadataFilters.value = []
  filterOrder.value = []
  searchResults.value = []
  totalScenes.value = 0
  currentOffset.value = 0
  isSearchMode.value = false
}
