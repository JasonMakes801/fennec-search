<template>
  <div class="max-w-4xl mx-auto px-4 py-4">
    <h1 class="text-lg font-semibold mb-4">Admin</h1>

    <!-- Queue Management -->
    <section class="bg-[#171717] rounded-sm p-3 mb-4">
      <h2 class="text-sm font-medium mb-3">Queue Management</h2>
      <p class="text-[10px] text-gray-500 mb-3">Reset stuck or failed enrichment jobs</p>

      <div class="space-y-2">
        <div class="flex items-center justify-between bg-[#262626] rounded-sm px-3 py-2">
          <div>
            <p class="text-xs text-gray-300">Reset Failed Jobs</p>
            <p class="text-[10px] text-gray-500">Move failed jobs back to pending queue for retry</p>
          </div>
          <button
            @click="resetFailed"
            :disabled="loading.resetFailed"
            class="px-3 py-1.5 bg-orange-500 hover:bg-orange-600 rounded-sm text-xs font-medium transition disabled:opacity-50"
          >
            {{ loading.resetFailed ? 'Resetting...' : 'Reset Failed' }}
          </button>
        </div>

        <div class="flex items-center justify-between bg-[#262626] rounded-sm px-3 py-2">
          <div>
            <p class="text-xs text-gray-300">Reset Stuck Jobs</p>
            <p class="text-[10px] text-gray-500">Reset jobs stuck in "processing" state</p>
          </div>
          <button
            @click="resetProcessing"
            :disabled="loading.resetProcessing"
            class="px-3 py-1.5 bg-orange-500 hover:bg-orange-600 rounded-sm text-xs font-medium transition disabled:opacity-50"
          >
            {{ loading.resetProcessing ? 'Resetting...' : 'Reset Stuck' }}
          </button>
        </div>
      </div>
    </section>

    <!-- Cleanup -->
    <section class="bg-[#171717] rounded-sm p-3 mb-4">
      <h2 class="text-sm font-medium mb-3">Cleanup</h2>
      <p class="text-[10px] text-gray-500 mb-3">Remove stale data from the database</p>

      <div class="space-y-2">
        <div class="flex items-center justify-between bg-[#262626] rounded-sm px-3 py-2">
          <div>
            <p class="text-xs text-gray-300">Purge Deleted Files</p>
            <p class="text-[10px] text-gray-500">Permanently remove soft-deleted files and their scenes/faces</p>
          </div>
          <button
            @click="purgeDeleted"
            :disabled="loading.purgeDeleted"
            class="px-3 py-1.5 bg-yellow-600 hover:bg-yellow-700 rounded-sm text-xs font-medium transition disabled:opacity-50"
          >
            {{ loading.purgeDeleted ? 'Purging...' : 'Purge Deleted' }}
          </button>
        </div>

        <div class="flex items-center justify-between bg-[#262626] rounded-sm px-3 py-2">
          <div>
            <p class="text-xs text-gray-300">Purge Orphan Files</p>
            <p class="text-[10px] text-gray-500">Remove files not under any current watch folder</p>
          </div>
          <button
            @click="purgeOrphans"
            :disabled="loading.purgeOrphans"
            class="px-3 py-1.5 bg-yellow-600 hover:bg-yellow-700 rounded-sm text-xs font-medium transition disabled:opacity-50"
          >
            {{ loading.purgeOrphans ? 'Purging...' : 'Purge Orphans' }}
          </button>
        </div>
      </div>
    </section>

    <!-- Danger Zone -->
    <section class="bg-[#171717] rounded-sm p-3 border border-red-900/50">
      <h2 class="text-sm font-medium mb-3 text-red-400">Danger Zone</h2>
      <p class="text-[10px] text-gray-500 mb-3">Destructive actions that cannot be undone</p>

      <div class="flex items-center justify-between bg-[#262626] rounded-sm px-3 py-2">
        <div>
          <p class="text-xs text-gray-300">Wipe Database</p>
          <p class="text-[10px] text-gray-500">Delete all files, scenes, faces, and embeddings. Config is preserved.</p>
        </div>
        <button
          @click="confirmWipe"
          :disabled="loading.wipe"
          class="px-3 py-1.5 bg-red-600 hover:bg-red-700 rounded-sm text-xs font-medium transition disabled:opacity-50"
        >
          {{ loading.wipe ? 'Wiping...' : 'Wipe All Data' }}
        </button>
      </div>
    </section>

    <!-- Result message -->
    <div
      v-if="message"
      class="mt-4 px-3 py-2 rounded-sm text-xs"
      :class="messageType === 'error' ? 'bg-red-900/50 text-red-200' : 'bg-green-900/50 text-green-200'"
    >
      {{ message }}
    </div>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { api } from '../services/api'

const loading = reactive({
  resetFailed: false,
  resetProcessing: false,
  purgeDeleted: false,
  purgeOrphans: false,
  wipe: false
})

const message = ref('')
const messageType = ref('success')

function showMessage(text, type = 'success') {
  message.value = text
  messageType.value = type
  setTimeout(() => { message.value = '' }, 5000)
}

async function resetFailed() {
  loading.resetFailed = true
  try {
    const result = await api.resetFailedJobs()
    showMessage(`Reset ${result.reset_count} failed jobs to pending`)
  } catch (err) {
    showMessage(`Failed: ${err.message}`, 'error')
  } finally {
    loading.resetFailed = false
  }
}

async function resetProcessing() {
  loading.resetProcessing = true
  try {
    const result = await api.resetProcessingJobs()
    showMessage(`Reset ${result.reset_count} stuck jobs to pending`)
  } catch (err) {
    showMessage(`Failed: ${err.message}`, 'error')
  } finally {
    loading.resetProcessing = false
  }
}

async function purgeDeleted() {
  loading.purgeDeleted = true
  try {
    const result = await api.purgeDeleted()
    showMessage(`Permanently removed ${result.purged_count} deleted files`)
  } catch (err) {
    showMessage(`Failed: ${err.message}`, 'error')
  } finally {
    loading.purgeDeleted = false
  }
}

async function purgeOrphans() {
  loading.purgeOrphans = true
  try {
    const result = await api.purgeOrphans()
    showMessage(`Removed ${result.purged_count} orphan files`)
  } catch (err) {
    showMessage(`Failed: ${err.message}`, 'error')
  } finally {
    loading.purgeOrphans = false
  }
}

async function confirmWipe() {
  const confirmed = window.confirm(
    'Are you sure you want to wipe ALL indexed data?\n\n' +
    'This will delete all files, scenes, faces, and embeddings.\n' +
    'This action cannot be undone!'
  )
  if (!confirmed) return

  loading.wipe = true
  try {
    const result = await api.wipeDatabase()
    showMessage(`Wiped ${result.wiped.files} files, ${result.wiped.scenes} scenes, ${result.wiped.faces} faces`)
  } catch (err) {
    showMessage(`Failed: ${err.message}`, 'error')
  } finally {
    loading.wipe = false
  }
}
</script>
