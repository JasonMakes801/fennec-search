<template>
  <div class="max-w-7xl mx-auto px-4 py-6">
    <!-- Page title -->
    <div class="mb-6">
      <h1 class="text-2xl font-semibold tracking-wide">Search</h1>
      <p class="text-gray-500 text-sm mt-1">
        Search shots by visual content, dialog, faces, and metadata
      </p>
    </div>

    <!-- Search Panel -->
    <div class="bg-[#171717] rounded-lg p-4 mb-6">
      <div class="flex flex-wrap gap-4">
        <!-- Visual Content -->
        <div class="control-group flex-1 min-w-[280px]">
          <label class="control-label">
            <span>Visual Content</span>
            <span class="flex items-center gap-1">
              <span class="text-gray-500 text-xs normal-case">min</span>
              <input 
                type="text" 
                v-model="thresholds.visual"
                class="threshold-input"
                title="Minimum similarity threshold (0-1)"
              />
            </span>
          </label>
          <input 
            type="text"
            v-model="filters.visual"
            placeholder="robot, explosion, outdoor scene..."
            class="input-field"
            @input="debouncedSearch"
          />
          <!-- Color swatches -->
          <div class="color-scroll mt-2">
            <div class="flex gap-1.5">
              <button 
                v-for="color in colorSwatches" 
                :key="color.term"
                @click="addColorTerm(color.term)"
                class="w-6 h-5 rounded flex-shrink-0 hover:ring-2 hover:ring-white transition"
                :class="color.class"
                :title="color.label"
              ></button>
            </div>
          </div>
        </div>

        <!-- Dialog -->
        <div class="control-group min-w-[200px]">
          <label class="control-label">
            <span>Dialog</span>
            <span v-if="dialogSearchMode === 'semantic'" class="flex items-center gap-1">
              <span class="text-gray-500 text-xs normal-case">min</span>
              <input 
                type="text" 
                v-model="thresholds.dialog"
                class="threshold-input"
                title="Minimum semantic similarity (0-1)"
              />
            </span>
          </label>
          <input 
            type="text"
            v-model="filters.dialog"
            :placeholder="dialogSearchMode === 'semantic' ? 'find similar meaning...' : 'exact words...'"
            class="input-field"
            @input="debouncedSearch"
          />
          <!-- Search mode toggle -->
          <div class="flex items-center gap-2 mt-1.5">
            <span 
              class="text-xs transition"
              :class="dialogSearchMode === 'semantic' ? 'text-orange-400' : 'text-gray-500'"
            >Semantic</span>
            <button 
              @click="dialogSearchMode = dialogSearchMode === 'semantic' ? 'keyword' : 'semantic'; if (filters.dialog) debouncedSearch()"
              class="w-8 h-4 bg-[#333] rounded-full flex items-center px-0.5"
              title="Toggle between semantic (finds synonyms) and keyword (exact match) search"
            >
              <span 
                class="w-3 h-3 bg-white rounded-full transition-all duration-200"
                :class="dialogSearchMode === 'semantic' ? 'ml-0' : 'ml-auto'"
              ></span>
            </button>
            <span 
              class="text-xs transition"
              :class="dialogSearchMode === 'keyword' ? 'text-orange-400' : 'text-gray-500'"
            >Keyword</span>
          </div>
        </div>

        <!-- Metadata Filter -->
        <div class="control-group flex-1 min-w-[320px]">
          <label class="control-label">Metadata</label>
          <div class="flex flex-col gap-2">
            <!-- Active metadata filters as lozenges -->
            <div 
              class="flex flex-wrap items-center gap-1.5 min-h-[36px] bg-[#262626] rounded px-2 py-1.5"
            >
              <template v-if="metadataFilters.length === 0">
                <span class="text-gray-600 text-xs">Add filters below</span>
              </template>
              <span 
                v-for="(mf, idx) in metadataFilters" 
                :key="idx"
                class="inline-flex items-center gap-1 bg-orange-600/30 text-orange-300 text-xs px-2 py-0.5 rounded"
              >
                <span class="font-medium">{{ mf.label }}</span>
                <button @click="removeMetadataFilter(idx)" class="hover:text-white">×</button>
              </span>
            </div>
            <!-- Add new filter row -->
            <div class="flex items-center gap-2">
              <select 
                v-model="newMeta.key"
                class="bg-[#262626] rounded px-2 py-1.5 text-sm text-gray-300 border-none outline-none appearance-none cursor-pointer hover:bg-[#333] pr-6"
                style="background-image: url('data:image/svg+xml;charset=UTF-8,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 width=%2212%22 height=%2212%22 viewBox=%220 0 12 12%22%3E%3Cpath fill=%22%239ca3af%22 d=%22M3 4.5L6 8l3-3.5H3z%22/%3E%3C/svg%3E'); background-repeat: no-repeat; background-position: right 8px center;"
                @change="onMetaKeyChange"
              >
                <option value="">+ Add filter</option>
                <option value="path">Path</option>
                <option value="tc">Timecode</option>
                <option value="duration">Duration</option>
                <option value="resolution">Resolution</option>
                <option value="fps">Frame Rate</option>
                <option value="codec">Codec</option>
              </select>
              <!-- Dynamic input based on key -->
              <template v-if="newMeta.key === 'path' || newMeta.key === 'codec'">
                <input 
                  type="text"
                  v-model="newMeta.value"
                  :placeholder="newMeta.key === 'path' ? 'path substring...' : 'h264, hevc...'"
                  class="flex-1 input-field text-sm"
                  @keydown.enter="addMetadataFilter"
                />
              </template>
              <template v-else-if="newMeta.key === 'tc'">
                <div class="flex flex-col gap-1">
                  <div class="flex items-center gap-2">
                    <span class="text-gray-500 text-xs w-6">In</span>
                    <input 
                      type="text"
                      v-model="newMeta.min"
                      placeholder="HH:MM:SS:FF"
                      class="w-32 input-field font-mono text-xs text-center"
                      @blur="newMeta.min = normalizeSmpteInput(newMeta.min)"
                    />
                  </div>
                  <div class="flex items-center gap-2">
                    <span class="text-gray-500 text-xs w-6">Out</span>
                    <input 
                      type="text"
                      v-model="newMeta.max"
                      placeholder="HH:MM:SS:FF"
                      class="w-32 input-field font-mono text-xs text-center"
                      @blur="newMeta.max = normalizeSmpteInput(newMeta.max)"
                      @keydown.enter="addMetadataFilter"
                    />
                  </div>
                </div>
              </template>
              <template v-else-if="newMeta.key === 'duration'">
                <input 
                  type="text"
                  v-model="newMeta.min"
                  placeholder="0"
                  class="w-16 input-field font-mono text-xs text-center"
                />
                <span class="text-gray-500">-</span>
                <input 
                  type="text"
                  v-model="newMeta.max"
                  placeholder="∞"
                  class="w-16 input-field font-mono text-xs text-center"
                  @keydown.enter="addMetadataFilter"
                />
              </template>
              <template v-else-if="newMeta.key === 'resolution'">
                <input 
                  type="text"
                  v-model="newMeta.min"
                  placeholder="1280"
                  class="w-16 input-field font-mono text-xs text-center"
                />
                <span class="text-gray-500">×</span>
                <input 
                  type="text"
                  v-model="newMeta.max"
                  placeholder="720"
                  class="w-16 input-field font-mono text-xs text-center"
                  @keydown.enter="addMetadataFilter"
                />
                <span class="text-gray-500 text-xs">min</span>
              </template>
              <template v-else-if="newMeta.key === 'fps'">
                <input 
                  type="text"
                  v-model="newMeta.min"
                  placeholder="24"
                  class="w-14 input-field font-mono text-xs text-center"
                />
                <span class="text-gray-500">-</span>
                <input 
                  type="text"
                  v-model="newMeta.max"
                  placeholder="60"
                  class="w-14 input-field font-mono text-xs text-center"
                  @keydown.enter="addMetadataFilter"
                />
              </template>
              <button 
                v-if="newMeta.key"
                @click="addMetadataFilter"
                class="px-2 py-1 bg-orange-600 hover:bg-orange-500 rounded text-xs"
              >
                Add
              </button>
            </div>
          </div>
        </div>

        <!-- Face Filter -->
        <div class="control-group flex-1 min-w-[140px]">
          <label class="control-label">
            <span>Face Filter</span>
            <span class="flex items-center gap-1">
              <span class="text-gray-500 text-xs normal-case">min</span>
              <input 
                type="text" 
                v-model="thresholds.face"
                class="threshold-input"
              />
            </span>
          </label>
          <div class="flex items-center gap-2 min-h-[36px] bg-[#262626] rounded px-2">
            <span v-if="!faceFilter" class="text-gray-600 text-xs">Click face in results</span>
            <template v-else>
              <canvas ref="faceCanvas" width="28" height="28" class="rounded border border-teal-500"></canvas>
              <span class="text-xs text-gray-300">Scene {{ faceFilter.sceneIndex }}</span>
              <button @click="clearFaceFilter" class="text-red-400 hover:text-red-300 text-xs ml-auto">x</button>
            </template>
          </div>
          <!-- Browse faces button -->
          <button
            @click="showFaceBrowser = true"
            :disabled="!!faceFilter"
            class="mt-1.5 w-full px-2 py-1 text-xs rounded transition"
            :class="faceFilter
              ? 'bg-[#1a1a1a] text-gray-600 cursor-not-allowed'
              : 'bg-[#262626] hover:bg-[#333] text-gray-400 hover:text-white'"
          >
            {{ results.length > 0 ? 'Browse Faces in Selection' : 'Browse All Faces' }}
          </button>
        </div>

        <!-- Visual Match -->
        <div class="control-group flex-1 min-w-[140px]">
          <label class="control-label">
            <span>Visual Match</span>
            <span class="flex items-center gap-1">
              <span class="text-gray-500 text-xs normal-case">min</span>
              <input
                type="text"
                v-model="thresholds.visualMatch"
                class="threshold-input"
              />
            </span>
          </label>
          <div class="flex items-center gap-2 min-h-[36px] bg-[#262626] rounded px-2">
            <span v-if="!visualMatch" class="text-gray-600 text-xs">Click thumbnail to match</span>
            <template v-else>
              <img :src="getSceneThumbnail(visualMatch.sceneIndex)" class="h-7 rounded border border-violet-500" />
              <span class="text-xs text-gray-300">Scene {{ visualMatch.sceneIndex }}</span>
              <button @click="clearVisualMatch" class="text-red-400 hover:text-red-300 text-xs ml-auto">x</button>
            </template>
          </div>
          <button
            @click="showVisualBrowser = true"
            :disabled="!!visualMatch"
            class="mt-1.5 w-full px-2 py-1 text-xs rounded transition"
            :class="visualMatch
              ? 'bg-[#1a1a1a] text-gray-600 cursor-not-allowed'
              : 'bg-[#262626] hover:bg-[#333] text-gray-400 hover:text-white'"
          >
            Browse Visual Groups
          </button>
        </div>

        <!-- Actions -->
        <div class="control-group flex items-end">
          <div class="flex gap-2">
            <button 
              @click="resetFilters"
              class="px-3 py-2 bg-[#262626] hover:bg-[#333] rounded text-sm transition"
            >
              Reset
            </button>
            <button 
              @click="search"
              class="px-4 py-2 bg-orange-500 hover:bg-orange-600 rounded text-sm font-medium transition"
            >
              Search
            </button>
          </div>
        </div>
      </div>

      <!-- Filter Chain (Lozenges) -->
      <div v-if="activeFilters.length > 0" class="mt-4 flex flex-wrap items-center gap-2">
        <span class="text-xs text-gray-500">Filters:</span>
        <template v-for="(filter, idx) in activeFilters" :key="filter.type">
          <span v-if="idx > 0" class="text-gray-500">-></span>
          <span :class="['filter-lozenge', `filter-lozenge-${filter.type}`]">
            <span>{{ filter.label }}</span>
            <button @click="removeFilter(filter.type)">x</button>
          </span>
        </template>
      </div>
    </div>

    <!-- Results Header -->
    <div class="mb-4 flex justify-between items-center">
      <h2 class="text-lg font-semibold">Results</h2>
      <div class="flex items-center gap-4">
        <span class="text-gray-500 text-sm">{{ resultCount }}</span>
        <!-- Thumbnail size slider -->
        <div class="flex items-center gap-2">
          <span class="text-xs text-gray-500">Size</span>
          <input 
            type="range" 
            v-model="thumbnailColumns" 
            min="3" 
            max="8" 
            class="w-24 accent-orange-500"
          />
        </div>
      </div>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="text-center py-12">
      <div class="inline-block w-8 h-8 border-2 border-orange-500 border-t-transparent rounded-full animate-spin"></div>
      <p class="mt-4 text-gray-400">Searching...</p>
    </div>

    <!-- Results Grid -->
    <div 
      v-else-if="results.length > 0"
      class="grid gap-3"
      :style="{ gridTemplateColumns: `repeat(${thumbnailColumns}, minmax(0, 1fr))` }"
    >
      <div 
        v-for="(scene, idx) in results" 
        :key="scene.scene_index"
        class="result-card group"
        @click="openScene(scene)"
      >
        <div class="thumbnail-container" :ref="el => thumbnailRefs[idx] = el">
          <img 
            :src="getSceneThumbnail(scene.scene_index)" 
            :alt="`Scene ${scene.scene_index}`"
            class="w-full"
            style="aspect-ratio: 864/360;"
            @load="e => renderFaceBoxes(idx, scene, e.target)"
          />
          <!-- Similarity badges (colors match filter lozenges) -->
          <span 
            v-if="scene.similarity" 
            class="similarity-badge bg-amber-700/80"
          >
            {{ Math.round(scene.similarity * 100) }}%
          </span>
          <span 
            v-if="scene.face_similarity && !scene.combined_similarity" 
            class="similarity-badge bg-teal-700/80"
            style="top: 24px;"
          >
            {{ Math.round(scene.face_similarity * 100) }}%
          </span>
          <span 
            v-if="scene.transcript_similarity" 
            class="similarity-badge bg-slate-600/80"
            :style="{ top: (scene.similarity ? 24 : 4) + (scene.face_similarity ? 20 : 0) + 'px' }"
          >
            {{ Math.round(scene.transcript_similarity * 100) }}%
          </span>
          <!-- Match button -->
          <button 
            @click.stop="setVisualMatch(scene.scene_index)"
            class="absolute bottom-1 right-1 bg-orange-600/80 hover:bg-orange-500 text-white text-xs px-1.5 py-0.5 rounded opacity-0 group-hover:opacity-100 transition-opacity"
            title="Find visually similar scenes"
          >
            Match
          </button>
        </div>
        <div class="p-2">
          <div class="text-sm font-medium">Scene {{ scene.scene_index }}</div>
          <div class="flex items-center gap-2">
            <span class="text-xs text-gray-400 font-mono">
              {{ formatTimeWithFrames(scene.start_time, scene.fps) }} - {{ formatTimeWithFrames(scene.end_time, scene.fps) }}
            </span>
            <span v-if="scene.fps" class="text-[10px] bg-[#333] text-gray-400 px-1.5 py-0.5 rounded font-medium">
              {{ scene.fps }}fps
            </span>
          </div>
          <div 
            v-if="scene.transcript" 
            class="text-xs text-gray-500 mt-1 truncate"
            :title="scene.transcript"
          >
            "{{ scene.transcript }}"
          </div>
        </div>
      </div>
    </div>

    <!-- Empty State -->
    <div v-else class="text-center py-12">
      <p class="text-gray-500">Enter search criteria to find scenes</p>
    </div>

    <!-- Load More -->
    <div v-if="hasMore && !loading" class="text-center py-6">
      <button 
        @click="loadMore"
        class="px-6 py-2 bg-[#262626] hover:bg-[#333] rounded-lg font-medium transition"
      >
        Load More Scenes
      </button>
      <span class="text-gray-500 text-sm ml-3">{{ remainingCount }} more</span>
    </div>

    <!-- Scene Modal -->
    <div 
      v-if="selectedScene" 
      class="modal-backdrop"
      @click.self="closeModal"
    >
      <div class="bg-[#171717] rounded-lg max-w-4xl w-full mx-4 overflow-hidden">
        <div class="p-4 border-b border-[#262626] flex justify-between items-center">
          <div>
            <div class="flex items-center gap-2">
              <h3 class="font-semibold">Scene {{ selectedScene.scene_index }}</h3>
              <span v-if="selectedScene.fps" class="text-xs bg-orange-600/30 text-orange-300 px-1.5 py-0.5 rounded font-medium">
                {{ selectedScene.fps }}fps
              </span>
              <span v-if="selectedScene.width && selectedScene.height" class="text-xs bg-[#333] text-gray-400 px-1.5 py-0.5 rounded font-medium">
                {{ selectedScene.width }}×{{ selectedScene.height }}
              </span>
            </div>
            <p class="text-xs text-gray-500 truncate max-w-xl" :title="selectedScene.filename || selectedScene.path">
              {{ selectedScene.filename || selectedScene.path }}
            </p>
          </div>
          <button @click="closeModal" class="text-gray-400 hover:text-white text-2xl">×</button>
        </div>
        <div class="p-4">
          <!-- Custom Video Player -->
          <div class="relative rounded overflow-hidden bg-black">
            <!-- Poster frame overlay - shown until first play -->
            <div 
              v-if="showPosterOverlay"
              class="absolute inset-0 z-10 cursor-pointer"
              @click="startPlayback"
            >
              <img 
                :src="getSceneThumbnail(selectedScene.scene_index)"
                class="w-full h-full object-contain"
                alt="Scene poster"
              />
              <!-- Big play button -->
              <div class="absolute inset-0 flex items-center justify-center">
                <div class="w-20 h-20 rounded-full bg-black/60 flex items-center justify-center hover:bg-black/80 transition">
                  <svg class="w-10 h-10 text-white ml-1" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M8 5v14l11-7z"/>
                  </svg>
                </div>
              </div>
            </div>
            
            <video 
              ref="modalVideo"
              class="w-full"
              :src="getVideoUrl(selectedScene.file_id)"
              preload="auto"
              @loadeddata="onVideoLoaded"
              @timeupdate="onVideoTimeUpdate"
              @play="isPlaying = true"
              @pause="isPlaying = false"
              @click="togglePlay"
              @seeked="onVideoSeeked"
            ></video>
            
            <!-- Custom Controls -->
            <div class="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/90 to-transparent p-3 pt-8">
              <!-- Progress Bar (scene-only) -->
              <div 
                class="relative h-2 bg-gray-700 rounded cursor-pointer mb-3 group"
                @mousedown="startScrubbing"
                ref="progressBar"
              >
                <div 
                  class="absolute h-full bg-orange-500 rounded pointer-events-none"
                  :style="{ width: sceneProgress + '%' }"
                ></div>
                <div 
                  class="absolute top-1/2 -translate-y-1/2 w-4 h-4 bg-white rounded-full shadow-lg pointer-events-none"
                  :style="{ left: sceneProgress + '%', transform: 'translate(-50%, -50%)' }"
                ></div>
              </div>
              
              <!-- Controls Row -->
              <div class="flex items-center gap-2">
                <!-- Play/Pause -->
                <button @click="togglePlay" class="text-white hover:text-orange-400 transition p-1">
                  <svg v-if="!isPlaying" class="w-6 h-6" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M8 5v14l11-7z"/>
                  </svg>
                  <svg v-else class="w-6 h-6" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z"/>
                  </svg>
                </button>
                
                <!-- Frame navigation -->
                <div class="flex items-center gap-0.5 border-l border-gray-600 pl-2 ml-1">
                  <!-- Jump to first frame |< -->
                  <button @click="jumpToStart" class="text-gray-400 hover:text-white transition p-1" title="First frame">
                    <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
                      <path d="M18.41 16.59L13.82 12l4.59-4.59L17 6l-6 6 6 6zM6 6h2v12H6z"/>
                    </svg>
                  </button>
                  <!-- Back 5 frames << -->
                  <button @click="stepFrames(-5)" class="text-gray-400 hover:text-white transition p-1" title="-5 frames">
                    <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
                      <path d="M17.59 18L13 12l4.59-6L16 4l-6 8 6 8zM11.59 18L7 12l4.59-6L10 4l-6 8 6 8z"/>
                    </svg>
                  </button>
                  <!-- Back 1 frame < -->
                  <button @click="stepFrames(-1)" class="text-gray-400 hover:text-white transition p-1" title="-1 frame">
                    <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
                      <path d="M15.41 16.59L10.83 12l4.58-4.59L14 6l-6 6 6 6z"/>
                    </svg>
                  </button>
                  <!-- Forward 1 frame > -->
                  <button @click="stepFrames(1)" class="text-gray-400 hover:text-white transition p-1" title="+1 frame">
                    <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
                      <path d="M8.59 16.59L13.17 12 8.59 7.41 10 6l6 6-6 6z"/>
                    </svg>
                  </button>
                  <!-- Forward 5 frames >> -->
                  <button @click="stepFrames(5)" class="text-gray-400 hover:text-white transition p-1" title="+5 frames">
                    <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
                      <path d="M6.41 18L11 12 6.41 6 8 4l6 8-6 8zM12.41 18L17 12l-4.59-6L14 4l6 8-6 8z"/>
                    </svg>
                  </button>
                  <!-- Jump to last frame >| -->
                  <button @click="jumpToEnd" class="text-gray-400 hover:text-white transition p-1" title="Last frame">
                    <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
                      <path d="M5.59 7.41L10.18 12l-4.59 4.59L7 18l6-6-6-6zM16 6h2v12h-2z"/>
                    </svg>
                  </button>
                </div>
                
                <!-- Time display -->
                <span class="text-white text-xs font-mono ml-2">
                  {{ formatTimeWithFrames(currentSceneTime) }} / {{ formatTimeWithFrames(sceneDuration) }}
                </span>
                
                <div class="flex-1"></div>
                
                <!-- Replay -->
                <button @click="replayScene" class="text-gray-400 hover:text-white transition p-1" title="Replay scene">
                  <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
                  </svg>
                </button>
              </div>
            </div>
          </div>
          
          <!-- Metadata Grid -->
          <div class="mt-4 grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div class="metadata-item">
              <span class="metadata-key">In</span>
              <span class="metadata-value font-mono text-xs">{{ formatTimeWithFrames(selectedScene.start_time) }}</span>
            </div>
            <div class="metadata-item">
              <span class="metadata-key">Out</span>
              <span class="metadata-value font-mono text-xs">{{ formatTimeWithFrames(selectedScene.end_time - (1 / (selectedScene.fps || 24))) }}</span>
            </div>
            <div class="metadata-item">
              <span class="metadata-key">Duration</span>
              <span class="metadata-value font-mono text-xs">{{ formatTimeWithFrames(sceneDuration) }}</span>
            </div>
            <div class="metadata-item">
              <span class="metadata-key">Faces</span>
              <span class="metadata-value">{{ selectedScene.faces?.length || 0 }}</span>
            </div>
          </div>
          
          <!-- Vectors info -->
          <div v-if="selectedScene.vectors?.length" class="mt-3 p-3 bg-[#0d0d0d] rounded">
            <span class="metadata-key">Vectors</span>
            <div class="flex flex-wrap gap-2 mt-1">
              <span 
                v-for="(vec, idx) in selectedScene.vectors" 
                :key="idx"
                class="inline-flex items-center gap-1 px-2 py-0.5 bg-[#1a1a1a] rounded text-xs"
                :title="`${vec.model} ${vec.version} (${vec.dimension}d)`"
              >
                <span class="text-green-400">✓</span>
                <span class="text-gray-300">{{ vec.model }}</span>
                <span class="text-gray-500">{{ vec.dimension }}d</span>
              </span>
            </div>
          </div>
          
          <div v-if="selectedScene.transcript" class="mt-3 p-3 bg-[#0d0d0d] rounded">
            <span class="metadata-key">Dialog</span>
            <p class="text-gray-300 text-sm mt-1 italic">"{{ selectedScene.transcript }}"</p>
          </div>
          
          <!-- File Details Accordion -->
          <div class="mt-4 border border-[#333] rounded overflow-hidden">
            <button 
              @click="showFileDetails = !showFileDetails"
              class="w-full px-3 py-2 bg-[#1a1a1a] hover:bg-[#222] flex items-center justify-between text-sm transition"
            >
              <span class="text-gray-300 font-medium">File Details</span>
              <svg 
                class="w-4 h-4 text-gray-500 transition-transform" 
                :class="{ 'rotate-180': showFileDetails }"
                fill="none" 
                stroke="currentColor" 
                viewBox="0 0 24 24"
              >
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/>
              </svg>
            </button>
            <div v-show="showFileDetails" class="p-3 bg-[#0d0d0d] border-t border-[#333]">
              <div class="grid grid-cols-2 gap-x-6 gap-y-2 text-sm">
                <div>
                  <span class="text-gray-500">Path</span>
                  <p class="text-gray-300 font-mono text-xs break-all">{{ selectedScene.path || '—' }}</p>
                </div>
                <div>
                  <span class="text-gray-500">Resolution</span>
                  <p class="text-gray-300 font-mono text-xs">{{ selectedScene.width && selectedScene.height ? `${selectedScene.width}×${selectedScene.height}` : '—' }}</p>
                </div>
                <div>
                  <span class="text-gray-500">Codec</span>
                  <p class="text-gray-300 font-mono text-xs">{{ selectedScene.codec || '—' }}</p>
                </div>
                <div>
                  <span class="text-gray-500">Frame Rate</span>
                  <p class="text-gray-300 font-mono text-xs">{{ selectedScene.fps ? `${selectedScene.fps} fps` : '—' }}</p>
                </div>
                <div>
                  <span class="text-gray-500">Audio Tracks</span>
                  <p class="text-gray-300 font-mono text-xs">{{ selectedScene.audio_tracks ?? '—' }}</p>
                </div>
                <div>
                  <span class="text-gray-500">File Size</span>
                  <p class="text-gray-300 font-mono text-xs">{{ formatFileSize(selectedScene.file_size_bytes) }}</p>
                </div>
                <div>
                  <span class="text-gray-500">File Duration</span>
                  <p class="text-gray-300 font-mono text-xs">{{ selectedScene.duration_seconds ? formatTime(selectedScene.duration_seconds) : '—' }}</p>
                </div>
                <div>
                  <span class="text-gray-500">Modified</span>
                  <p class="text-gray-300 font-mono text-xs">{{ formatDate(selectedScene.file_modified_at) }}</p>
                </div>
              </div>
            </div>
          </div>
          
          <!-- Faces in scene -->
          <div v-if="selectedScene.faces?.length" class="mt-4">
            <span class="metadata-key mb-2 block">Faces in Scene</span>
            <div class="flex gap-2 flex-wrap">
              <canvas 
                v-for="(face, faceIdx) in selectedScene.faces"
                :key="faceIdx"
                :ref="el => modalFaceRefs[faceIdx] = el"
                width="60" 
                height="60"
                class="rounded border-2 border-gray-600 hover:border-orange-500 cursor-pointer transition-colors"
                @click="selectFaceFromModal(selectedScene.scene_index, faceIdx, face.bbox)"
              ></canvas>
            </div>
          </div>
          
          <div class="mt-4">
            <button 
              @click="findSimilar"
              class="px-4 py-2 bg-orange-600 hover:bg-orange-500 rounded text-sm transition"
            >
              Find Visually Similar Scenes
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Face Select Modal -->
    <div 
      v-if="faceSelectModal" 
      class="modal-backdrop"
      @click.self="closeFaceModal"
    >
      <div class="bg-[#171717] rounded-lg max-w-md w-full mx-4 p-6">
        <h3 class="font-semibold mb-4">Select a face to filter by</h3>
        <div class="flex gap-4 flex-wrap justify-center">
          <div 
            v-for="(face, idx) in faceSelectModal.faces"
            :key="idx"
            class="text-center cursor-pointer hover:opacity-80"
            @click="selectFaceFromModal(faceSelectModal.sceneIndex, idx, face.bbox)"
          >
            <canvas 
              :ref="el => faceSelectRefs[idx] = el"
              width="80" 
              height="80"
              class="rounded border-2 border-gray-600 hover:border-teal-500"
            ></canvas>
            <div class="text-xs text-gray-400 mt-1">Face {{ idx + 1 }}</div>
          </div>
        </div>
        <button @click="closeFaceModal" class="mt-4 text-gray-400 hover:text-white text-sm">
          Cancel
        </button>
      </div>
    </div>

    <!-- Face Browser Modal -->
    <FaceBrowserModal
      :isOpen="showFaceBrowser"
      :sceneIds="currentResultSceneIds"
      @close="showFaceBrowser = false"
      @select="onFaceBrowserSelect"
    />

    <!-- Visual Match Browser Modal -->
    <VisualMatchModal
      :isOpen="showVisualBrowser"
      :sceneIds="currentResultSceneIds"
      @close="showVisualBrowser = false"
      @select="onVisualBrowserSelect"
    />
  </div>
</template>

<script setup>
import { ref, reactive, computed, watch, onMounted, nextTick } from 'vue'
import { api } from '../services/api'
import FaceBrowserModal from '../components/FaceBrowserModal.vue'
import VisualMatchModal from '../components/VisualMatchModal.vue'

// Constants
const PAGE_SIZE = 40
const DEBOUNCE_MS = 400

// State
const loading = ref(false)
const results = ref([])
const totalScenes = ref(0)
const currentOffset = ref(0)
const isSearchMode = ref(false)
const thumbnailColumns = ref(5)
const thumbnailRefs = ref({})
const modalFaceRefs = ref({})
const faceSelectRefs = ref({})
const faceCanvas = ref(null)
const modalVideo = ref(null)
const progressBar = ref(null)

// Video player state
const isPlaying = ref(false)
const showPosterOverlay = ref(true)  // Show poster until first play
const sceneProgress = ref(0)
const currentSceneTime = ref(0)
const isScrubbing = ref(false)
const videoFps = ref(24) // Default, will try to detect

// Filters
const filters = reactive({
  visual: '',
  dialog: ''
})

// Default thresholds loaded from config
const defaultThresholds = reactive({
  visual: 0.10,
  face: 0.25,
  visualMatch: 0.20,
  dialog: 0.35
})

const thresholds = reactive({
  visual: '0.10',
  face: '0.25',
  visualMatch: '0.20',
  dialog: '0.35'
})

// Dialog search mode: 'semantic' (embeddings) or 'keyword' (exact match)
const dialogSearchMode = ref('semantic')

const faceFilter = ref(null)
const visualMatch = ref(null)
const filterOrder = ref([])

// Metadata filters
const metadataFilters = ref([])
const newMeta = reactive({
  key: '',
  value: '',
  min: '',
  max: ''
})

// Modal state
const selectedScene = ref(null)
const faceSelectModal = ref(null)
const showFileDetails = ref(false)
const showFaceBrowser = ref(false)
const showVisualBrowser = ref(false)

// Color swatches
const colorSwatches = [
  { term: 'orange tones', class: 'bg-orange-500/50 border border-orange-500', label: 'Warm/Orange' },
  { term: 'red tones', class: 'bg-red-600/50 border border-red-600', label: 'Red' },
  { term: 'magenta tones', class: 'bg-pink-500/50 border border-pink-500', label: 'Magenta/Pink' },
  { term: 'purple tones', class: 'bg-purple-600/50 border border-purple-600', label: 'Purple' },
  { term: 'blue tones', class: 'bg-blue-500/50 border border-blue-500', label: 'Cool/Blue' },
  { term: 'cyan tones', class: 'bg-cyan-500/50 border border-cyan-500', label: 'Cyan/Teal' },
  { term: 'green tones', class: 'bg-green-600/50 border border-green-600', label: 'Green' },
  { term: 'yellow tones', class: 'bg-yellow-400/50 border border-yellow-400', label: 'Yellow/Golden' },
  { term: 'dark shadows', class: 'bg-gray-900 border border-gray-600', label: 'Dark/Shadows' },
  { term: 'bright daylight', class: 'bg-gray-100 border border-gray-600', label: 'Bright/Daylight' },
  { term: 'desaturated tones', class: 'bg-gray-500 border border-gray-600', label: 'Desaturated' },
  { term: 'high contrast', class: 'bg-gradient-to-r from-black to-white border border-gray-600', label: 'High Contrast' }
]

// Computed
const resultCount = computed(() => {
  if (isSearchMode.value) {
    return `${results.value.length} results`
  }
  return `Showing ${results.value.length} of ${totalScenes.value} scenes`
})

const hasMore = computed(() => {
  return !isSearchMode.value && results.value.length < totalScenes.value
})

const remainingCount = computed(() => {
  return totalScenes.value - results.value.length
})

const sceneDuration = computed(() => {
  if (!selectedScene.value) return 0
  // end_time is exclusive, so actual duration is one frame less
  const fps = selectedScene.value.fps || 24
  const frameTime = 1 / fps
  return (selectedScene.value.end_time || 0) - (selectedScene.value.start_time || 0) - frameTime
})

const activeFilters = computed(() => {
  const list = []
  for (const type of filterOrder.value) {
    if (type === 'visual' && filters.visual) {
      list.push({ type: 'visual', label: `Visual: ${filters.visual.slice(0, 20)}${filters.visual.length > 20 ? '...' : ''}` })
    } else if (type === 'dialog' && filters.dialog) {
      list.push({ type: 'dialog', label: `Dialog: "${filters.dialog.slice(0, 15)}${filters.dialog.length > 15 ? '...' : ''}"` })
    } else if (type === 'face' && faceFilter.value) {
      list.push({ type: 'face', label: `Face from Scene ${faceFilter.value.sceneIndex}` })
    } else if (type === 'visual-match' && visualMatch.value) {
      list.push({ type: 'visual-match', label: `Similar to Scene ${visualMatch.value.sceneIndex}` })
    } else if (type === 'metadata' && metadataFilters.value.length > 0) {
      list.push({ type: 'metadata', label: `${metadataFilters.value.length} metadata filter${metadataFilters.value.length > 1 ? 's' : ''}` })
    }
  }
  return list
})

// Scene IDs for filtering modals to current selection
const currentResultSceneIds = computed(() => {
  if (results.value.length === 0) return null
  return results.value.map(r => r.id)
})

// Methods
function addFilter(type) {
  if (!filterOrder.value.includes(type)) {
    filterOrder.value.push(type)
  }
}

function removeFilter(type) {
  filterOrder.value = filterOrder.value.filter(t => t !== type)
  if (type === 'visual') filters.visual = ''
  if (type === 'dialog') filters.dialog = ''
  if (type === 'face') faceFilter.value = null
  if (type === 'visual-match') visualMatch.value = null
  if (type === 'metadata') metadataFilters.value = []
  search()
}

// Metadata filter methods
function onMetaKeyChange() {
  newMeta.value = ''
  newMeta.min = ''
  newMeta.max = ''
}

function addMetadataFilter() {
  if (!newMeta.key) return
  
  let filter = { key: newMeta.key }
  let label = ''
  
  switch (newMeta.key) {
    case 'path':
      if (!newMeta.value) return
      filter.value = newMeta.value
      label = `path: *${newMeta.value}*`
      break
    case 'codec':
      if (!newMeta.value) return
      filter.value = newMeta.value
      label = `codec: ${newMeta.value}`
      break
    case 'tc':
      filter.min = newMeta.min ? parseTimecode(newMeta.min) : null
      filter.max = newMeta.max ? parseTimecode(newMeta.max) : null
      if (filter.min === null && filter.max === null) return
      label = `tc: ${filter.min !== null ? formatTimecodeForLabel(filter.min) : '00:00:00:00'} - ${filter.max !== null ? formatTimecodeForLabel(filter.max) : '∞'}`
      break
    case 'duration':
      filter.min = newMeta.min ? parseFloat(newMeta.min) : null
      filter.max = newMeta.max ? parseFloat(newMeta.max) : null
      if (filter.min === null && filter.max === null) return
      label = `duration: ${newMeta.min || '0'}s - ${newMeta.max || '∞'}s`
      break
    case 'resolution':
      filter.widthMin = newMeta.min ? parseInt(newMeta.min) : null
      filter.heightMin = newMeta.max ? parseInt(newMeta.max) : null
      if (filter.widthMin === null && filter.heightMin === null) return
      label = `res: ≥${newMeta.min || '?'}×${newMeta.max || '?'}`
      break
    case 'fps':
      filter.min = newMeta.min ? parseFloat(newMeta.min) : null
      filter.max = newMeta.max ? parseFloat(newMeta.max) : null
      if (filter.min === null && filter.max === null) return
      label = `fps: ${newMeta.min || '0'} - ${newMeta.max || '∞'}`
      break
  }
  
  filter.label = label
  metadataFilters.value.push(filter)
  addFilter('metadata')
  
  // Reset
  newMeta.key = ''
  newMeta.value = ''
  newMeta.min = ''
  newMeta.max = ''
  
  search()
}

function removeMetadataFilter(idx) {
  metadataFilters.value.splice(idx, 1)
  if (metadataFilters.value.length === 0) {
    filterOrder.value = filterOrder.value.filter(t => t !== 'metadata')
  }
  search()
}

function parseTimecode(tc, fps = 24) {
  if (!tc || tc.trim() === '') return null
  tc = tc.trim()
  
  // Handle pure number input (interpret as hours)
  if (/^\d+$/.test(tc)) {
    const hrs = parseInt(tc)
    if (isNaN(hrs)) return null
    return hrs * 3600
  }
  
  const parts = tc.split(':')
  // Support both MM:SS and HH:MM:SS:FF formats
  if (parts.length === 2) {
    // MM:SS format (legacy)
    const mins = parseInt(parts[0])
    const secs = parseInt(parts[1])
    if (isNaN(mins) || isNaN(secs)) return null
    return mins * 60 + secs
  } else if (parts.length === 4) {
    // HH:MM:SS:FF SMPTE format
    const hrs = parseInt(parts[0])
    const mins = parseInt(parts[1])
    const secs = parseInt(parts[2])
    const frames = parseInt(parts[3])
    if (isNaN(hrs) || isNaN(mins) || isNaN(secs) || isNaN(frames)) return null
    return hrs * 3600 + mins * 60 + secs + (frames / fps)
  } else if (parts.length === 3) {
    // HH:MM:SS format (no frames)
    const hrs = parseInt(parts[0])
    const mins = parseInt(parts[1])
    const secs = parseInt(parts[2])
    if (isNaN(hrs) || isNaN(mins) || isNaN(secs)) return null
    return hrs * 3600 + mins * 60 + secs
  }
  return null
}

function normalizeSmpteInput(input) {
  if (!input || input.trim() === '') return ''
  input = input.trim()
  
  // Pure number -> treat as hours
  if (/^\d+$/.test(input)) {
    const hrs = parseInt(input)
    return `${hrs.toString().padStart(2, '0')}:00:00:00`
  }
  
  const parts = input.split(':')
  
  // Normalize each part to 2 digits, fill missing parts with 00
  const hrs = parts[0] ? parseInt(parts[0]) || 0 : 0
  const mins = parts[1] ? parseInt(parts[1]) || 0 : 0
  const secs = parts[2] ? parseInt(parts[2]) || 0 : 0
  const frames = parts[3] ? parseInt(parts[3]) || 0 : 0
  
  // Clamp values to valid ranges
  const clampedMins = Math.min(mins, 59)
  const clampedSecs = Math.min(secs, 59)
  const clampedFrames = Math.min(frames, 23)
  
  return `${hrs.toString().padStart(2, '0')}:${clampedMins.toString().padStart(2, '0')}:${clampedSecs.toString().padStart(2, '0')}:${clampedFrames.toString().padStart(2, '0')}`
}

function formatTimecodeForLabel(seconds, fps = 24) {
  if (seconds === undefined || seconds === null) return '00:00:00:00'
  const hrs = Math.floor(seconds / 3600)
  const mins = Math.floor((seconds % 3600) / 60)
  const secs = Math.floor(seconds % 60)
  const frames = Math.floor((seconds % 1) * fps)
  return `${hrs.toString().padStart(2, '0')}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}:${frames.toString().padStart(2, '0')}`
}

function formatTime(seconds) {
  if (seconds === undefined || seconds === null) return '--:--'
  const mins = Math.floor(seconds / 60)
  const secs = Math.floor(seconds % 60)
  return `${mins}:${secs.toString().padStart(2, '0')}`
}

function formatFileSize(bytes) {
  if (bytes === undefined || bytes === null) return '—'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`
}

function formatDate(dateStr) {
  if (!dateStr) return '—'
  const date = new Date(dateStr)
  return date.toLocaleDateString('en-US', { 
    year: 'numeric', 
    month: 'short', 
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

function getSceneThumbnail(sceneIndex) {
  const sceneId = `scene_${String(sceneIndex).padStart(4, '0')}`
  return `/api/thumbnail/${sceneId}`
}

function getVideoUrl(fileId) {
  return `/api/video/${fileId}`
}

// Custom video player functions
function onVideoLoaded() {
  if (modalVideo.value && selectedScene.value?.start_time != null) {
    // Try to get FPS from the scene data, default to 24
    videoFps.value = selectedScene.value.fps || 24
    modalVideo.value.currentTime = selectedScene.value.start_time
    sceneProgress.value = 0
    currentSceneTime.value = 0
  }
}

function onVideoSeeked() {
  // Update display after seek completes
  if (!modalVideo.value || !selectedScene.value) return
  const currentTime = modalVideo.value.currentTime
  const startTime = selectedScene.value.start_time || 0
  currentSceneTime.value = Math.max(0, currentTime - startTime)
}

function onVideoTimeUpdate() {
  if (!modalVideo.value || !selectedScene.value || isScrubbing.value) return
  
  const currentTime = modalVideo.value.currentTime
  const startTime = selectedScene.value.start_time || 0
  // end_time is EXCLUSIVE (first frame of next scene), so actual last frame is end_time - 1 frame
  const fps = selectedScene.value.fps || 24
  const frameTime = 1 / fps
  const endTimeExclusive = selectedScene.value.end_time || modalVideo.value.duration
  const endTimeInclusive = endTimeExclusive - frameTime  // last playable frame
  const duration = endTimeExclusive - startTime - frameTime  // scene duration in playable frames
  
  // Update progress relative to scene bounds
  currentSceneTime.value = Math.max(0, currentTime - startTime)
  sceneProgress.value = duration > 0 ? Math.min(100, (currentSceneTime.value / duration) * 100) : 0
  
  // Stop at scene end (before the exclusive end frame)
  if (currentTime >= endTimeInclusive) {
    modalVideo.value.pause()
    modalVideo.value.currentTime = endTimeInclusive
    sceneProgress.value = 100
  }
}

function startPlayback() {
  // Called when clicking the poster overlay
  showPosterOverlay.value = false
  if (modalVideo.value) {
    modalVideo.value.play()
  }
}

function togglePlay() {
  if (!modalVideo.value) return
  if (modalVideo.value.paused) {
    // If at or near scene end, restart from beginning
    const fps = selectedScene.value.fps || 24
    const frameTime = 1 / fps
    const endTimeInclusive = selectedScene.value.end_time - frameTime
    // Use small tolerance for floating point comparison
    if (modalVideo.value.currentTime >= endTimeInclusive - 0.01) {
      modalVideo.value.currentTime = selectedScene.value.start_time
    }
    modalVideo.value.play()
  } else {
    modalVideo.value.pause()
  }
}

function startScrubbing(event) {
  if (!modalVideo.value || !progressBar.value || !selectedScene.value) return
  
  isScrubbing.value = true
  modalVideo.value.pause()
  
  seekFromEvent(event)
  
  const onMouseMove = (e) => seekFromEvent(e)
  const onMouseUp = () => {
    isScrubbing.value = false
    document.removeEventListener('mousemove', onMouseMove)
    document.removeEventListener('mouseup', onMouseUp)
  }
  
  document.addEventListener('mousemove', onMouseMove)
  document.addEventListener('mouseup', onMouseUp)
}

function seekFromEvent(event) {
  if (!modalVideo.value || !progressBar.value || !selectedScene.value) return
  
  const rect = progressBar.value.getBoundingClientRect()
  const percent = Math.max(0, Math.min(1, (event.clientX - rect.left) / rect.width))
  
  const fps = selectedScene.value.fps || 24
  const frameTime = 1 / fps
  const startTime = selectedScene.value.start_time || 0
  const endTimeExclusive = selectedScene.value.end_time || modalVideo.value.duration
  const endTimeInclusive = endTimeExclusive - frameTime
  const duration = endTimeInclusive - startTime
  
  const newTime = startTime + (percent * duration)
  modalVideo.value.currentTime = newTime
  
  // Update UI immediately for responsiveness
  currentSceneTime.value = percent * duration
  sceneProgress.value = percent * 100
}

function stepFrames(frames) {
  if (!modalVideo.value || !selectedScene.value) return
  
  const frameTime = 1 / videoFps.value
  const startTime = selectedScene.value.start_time || 0
  const endTimeExclusive = selectedScene.value.end_time || modalVideo.value.duration
  const endTimeInclusive = endTimeExclusive - frameTime
  
  let newTime = modalVideo.value.currentTime + (frames * frameTime)
  newTime = Math.max(startTime, Math.min(endTimeInclusive, newTime))
  
  modalVideo.value.currentTime = newTime
}

function jumpToStart() {
  if (!modalVideo.value || !selectedScene.value) return
  modalVideo.value.currentTime = selectedScene.value.start_time || 0
}

function jumpToEnd() {
  if (!modalVideo.value || !selectedScene.value) return
  const frameTime = 1 / videoFps.value
  const endTimeExclusive = selectedScene.value.end_time || modalVideo.value.duration
  modalVideo.value.currentTime = endTimeExclusive - frameTime
}

function replayScene() {
  if (!modalVideo.value || !selectedScene.value) return
  modalVideo.value.currentTime = selectedScene.value.start_time || 0
  modalVideo.value.play()
}

function formatTimeWithFrames(seconds, fps = null) {
  if (seconds === undefined || seconds === null) return '00:00:00:00'
  const useFps = fps || videoFps.value || 24
  const hrs = Math.floor(seconds / 3600)
  const mins = Math.floor((seconds % 3600) / 60)
  const secs = Math.floor(seconds % 60)
  const frames = Math.floor((seconds % 1) * useFps)
  return `${hrs.toString().padStart(2, '0')}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}:${frames.toString().padStart(2, '0')}`
}

function getSimilarityClass(sim) {
  if (sim < 0.23) return 'bg-orange-600/70'
  if (sim < 0.26) return 'bg-yellow-600/70'
  return 'bg-green-600/70'
}

function addColorTerm(term) {
  const current = filters.visual.trim()
  filters.visual = current ? `${current}, ${term}` : term
  addFilter('visual')
  debouncedSearch()
}

let debounceTimer = null
function debouncedSearch() {
  clearTimeout(debounceTimer)
  debounceTimer = setTimeout(() => search(), DEBOUNCE_MS)
}

async function loadScenes(reset = true) {
  if (reset) {
    currentOffset.value = 0
    results.value = []
  }
  
  isSearchMode.value = false
  loading.value = true
  
  try {
    const data = await api.getScenes(PAGE_SIZE, currentOffset.value)
    const newScenes = data.scenes || []
    results.value = reset ? newScenes : [...results.value, ...newScenes]
    totalScenes.value = data.total || 155
    currentOffset.value += PAGE_SIZE
  } catch (err) {
    console.error('Failed to load scenes:', err)
  } finally {
    loading.value = false
  }
}

async function search() {
  // Track filters
  if (filters.visual) addFilter('visual')
  else filterOrder.value = filterOrder.value.filter(t => t !== 'visual')
  
  if (filters.dialog) addFilter('dialog')
  else filterOrder.value = filterOrder.value.filter(t => t !== 'dialog')
  
  const hasFilters = filters.visual || filters.dialog || faceFilter.value || visualMatch.value || metadataFilters.value.length > 0
  
  if (!hasFilters) {
    loadScenes(true)
    return
  }
  
  isSearchMode.value = true
  loading.value = true
  results.value = []
  
  try {
    const params = {}
    if (filters.visual) {
      params.visual = filters.visual
      params.visual_threshold = parseFloat(thresholds.visual) || 0.10
    }
    if (filters.dialog) {
      // Use semantic search (embeddings) or keyword search (exact match)
      if (dialogSearchMode.value === 'semantic') {
        params.transcript_semantic = filters.dialog
        params.transcript_threshold = parseFloat(thresholds.dialog) || 0.35
      } else {
        params.transcript = filters.dialog
      }
    }
    if (faceFilter.value) {
      // Support both face_id (from browser) and face_scene+face_index (from clicking results)
      if (faceFilter.value.faceId) {
        params.face_id = faceFilter.value.faceId
      } else {
        params.face_scene = faceFilter.value.sceneIndex
        params.face_index = faceFilter.value.faceIndex
      }
      params.face_threshold = parseFloat(thresholds.face) || 0.25
    }
    if (visualMatch.value) {
      params.visual_match_scene = visualMatch.value.sceneIndex
      params.visual_match_threshold = parseFloat(thresholds.visualMatch) || 0.20
    }
    
    // Apply metadata filters
    for (const mf of metadataFilters.value) {
      switch (mf.key) {
        case 'path':
          params.path = mf.value
          break
        case 'codec':
          params.codec = mf.value
          break
        case 'tc':
          if (mf.min !== null) params.tc_min = mf.min
          if (mf.max !== null) params.tc_max = mf.max
          break
        case 'duration':
          if (mf.min !== null) params.duration_min = mf.min
          if (mf.max !== null) params.duration_max = mf.max
          break
        case 'resolution':
          if (mf.widthMin !== null) params.width_min = mf.widthMin
          if (mf.heightMin !== null) params.height_min = mf.heightMin
          break
        case 'fps':
          if (mf.min !== null) params.fps_min = mf.min
          if (mf.max !== null) params.fps_max = mf.max
          break
      }
    }
    
    const data = await api.search(params)
    results.value = data.results || []
  } catch (err) {
    console.error('Search failed:', err)
  } finally {
    loading.value = false
  }
}

function loadMore() {
  if (!isSearchMode.value) {
    loadScenes(false)
  }
}

function resetFilters() {
  filters.visual = ''
  filters.dialog = ''
  thresholds.visual = String(defaultThresholds.visual)
  thresholds.face = String(defaultThresholds.face)
  thresholds.visualMatch = String(defaultThresholds.visualMatch)
  thresholds.dialog = String(defaultThresholds.dialog)
  dialogSearchMode.value = 'semantic'
  faceFilter.value = null
  visualMatch.value = null
  metadataFilters.value = []
  filterOrder.value = []
  loadScenes(true)
}

// Face handling
function renderFaceBoxes(idx, scene, imgElement) {
  if (!scene.faces?.length) return
  
  const container = thumbnailRefs.value[idx]
  if (!container) return
  
  // Remove existing face boxes
  container.querySelectorAll('.face-box').forEach(el => el.remove())
  
  const sourceWidth = imgElement.naturalWidth || 864
  const sourceHeight = imgElement.naturalHeight || 360
  const displayWidth = imgElement.clientWidth
  const displayHeight = imgElement.clientHeight
  
  if (displayWidth === 0 || displayHeight === 0) {
    requestAnimationFrame(() => renderFaceBoxes(idx, scene, imgElement))
    return
  }
  
  const scaleX = displayWidth / sourceWidth
  const scaleY = displayHeight / sourceHeight
  
  scene.faces.forEach((face, faceIdx) => {
    const bbox = typeof face.bbox === 'string' ? JSON.parse(face.bbox) : face.bbox
    const [x, y, w, h] = bbox
    
    const box = document.createElement('div')
    box.className = 'face-box'
    box.style.left = `${x * scaleX}px`
    box.style.top = `${y * scaleY}px`
    box.style.width = `${w * scaleX}px`
    box.style.height = `${h * scaleY}px`
    box.title = `Face ${faceIdx + 1} - Click to filter`
    box.onclick = (e) => {
      e.stopPropagation()
      if (scene.faces.length > 1) {
        showFaceSelectModal(scene.scene_index, scene.faces)
      } else {
        selectFace(scene.scene_index, faceIdx, bbox)
      }
    }
    
    container.appendChild(box)
  })
}

function showFaceSelectModal(sceneIndex, faces) {
  faceSelectModal.value = { sceneIndex, faces }
  nextTick(() => {
    const img = new Image()
    img.crossOrigin = 'anonymous'
    img.onload = () => {
      faces.forEach((face, idx) => {
        const bbox = typeof face.bbox === 'string' ? JSON.parse(face.bbox) : face.bbox
        const canvas = faceSelectRefs.value[idx]
        if (canvas) drawFaceCrop(canvas, img, bbox, 80)
      })
    }
    img.src = getSceneThumbnail(sceneIndex)
  })
}

function selectFace(sceneIndex, faceIndex, bbox) {
  faceFilter.value = { sceneIndex, faceIndex, bbox }
  addFilter('face')
  closeFaceModal()
  
  // Draw face in filter display
  nextTick(() => {
    if (faceCanvas.value) {
      const img = new Image()
      img.crossOrigin = 'anonymous'
      img.onload = () => drawFaceCrop(faceCanvas.value, img, bbox, 28)
      img.src = getSceneThumbnail(sceneIndex)
    }
  })
  
  search()
}

function selectFaceFromModal(sceneIndex, faceIndex, bbox) {
  selectFace(sceneIndex, faceIndex, typeof bbox === 'string' ? JSON.parse(bbox) : bbox)
}

function onFaceBrowserSelect(face) {
  // Face browser returns a face object with scene_index and bbox
  // We need to find the face index within the scene
  // For now, use face.id as a unique identifier
  const bbox = face.bbox
  const sceneIndex = face.scene_index
  
  // Set filter with face id instead of face index (more reliable for browse)
  faceFilter.value = { 
    sceneIndex, 
    faceIndex: 0,  // Will be looked up by face_id on server
    faceId: face.id,  // Use face id for exact match
    bbox 
  }
  addFilter('face')
  
  // Draw face in filter display
  nextTick(() => {
    if (faceCanvas.value) {
      const img = new Image()
      img.crossOrigin = 'anonymous'
      img.onload = () => drawFaceCrop(faceCanvas.value, img, bbox, 28)
      img.src = api.thumbnailUrl(face.scene_id)
    }
  })
  
  search()
}

function clearFaceFilter() {
  faceFilter.value = null
  filterOrder.value = filterOrder.value.filter(t => t !== 'face')
  search()
}

function drawFaceCrop(canvas, img, bbox, size) {
  const ctx = canvas.getContext('2d')
  const [x, y, w, h] = bbox
  
  const padding = Math.max(w, h) * 0.3
  const sx = Math.max(0, x - padding)
  const sy = Math.max(0, y - padding)
  const sw = Math.min(img.width - sx, w + padding * 2)
  const sh = Math.min(img.height - sy, h + padding * 2)
  
  ctx.drawImage(img, sx, sy, sw, sh, 0, 0, size, size)
}

// Visual match
function setVisualMatch(sceneIndex) {
  visualMatch.value = { sceneIndex }
  addFilter('visual-match')
  search()
}

function onVisualBrowserSelect(scene) {
  setVisualMatch(scene.scene_index)
}

function clearVisualMatch() {
  visualMatch.value = null
  filterOrder.value = filterOrder.value.filter(t => t !== 'visual-match')
  search()
}

// Scene modal
async function openScene(scene) {
  // Set initial scene data from search results
  selectedScene.value = scene
  showPosterOverlay.value = true  // Reset poster state for new scene
  showFileDetails.value = false  // Collapse file details for new scene
  
  // Fetch full scene details (includes vectors)
  try {
    const fullScene = await api.getScene(scene.scene_index)
    // Merge vectors into selected scene
    if (fullScene.vectors) {
      selectedScene.value = { ...selectedScene.value, vectors: fullScene.vectors }
    }
  } catch (err) {
    console.error('Failed to fetch scene vectors:', err)
  }
  
  nextTick(() => {
    if (scene.faces?.length && modalVideo.value) {
      const img = new Image()
      img.crossOrigin = 'anonymous'
      img.onload = () => {
        scene.faces.forEach((face, idx) => {
          const bbox = typeof face.bbox === 'string' ? JSON.parse(face.bbox) : face.bbox
          const canvas = modalFaceRefs.value[idx]
          if (canvas) drawFaceCrop(canvas, img, bbox, 60)
        })
      }
      img.src = getSceneThumbnail(scene.scene_index)
    }
  })
}

function closeModal() {
  if (modalVideo.value) modalVideo.value.pause()
  selectedScene.value = null
}

function closeFaceModal() {
  faceSelectModal.value = null
}

function findSimilar() {
  if (selectedScene.value) {
    closeModal()
    setVisualMatch(selectedScene.value.scene_index)
  }
}

// Keyboard shortcuts
function handleKeydown(e) {
  if (e.key === 'Escape') {
    closeModal()
    closeFaceModal()
  }
  if (e.key === 'Enter' && !selectedScene.value) {
    search()
  }
}

async function loadThresholds() {
  try {
    const [visual, visualMatch, face, dialog] = await Promise.all([
      api.getConfig('search_threshold_visual'),
      api.getConfig('search_threshold_visual_match'),
      api.getConfig('search_threshold_face'),
      api.getConfig('search_threshold_transcript')
    ])
    
    defaultThresholds.visual = visual.value ?? 0.10
    defaultThresholds.visualMatch = visualMatch.value ?? 0.20
    defaultThresholds.face = face.value ?? 0.25
    defaultThresholds.dialog = dialog.value ?? 0.35
    
    // Set current thresholds to defaults on load
    thresholds.visual = String(defaultThresholds.visual)
    thresholds.visualMatch = String(defaultThresholds.visualMatch)
    thresholds.face = String(defaultThresholds.face)
    thresholds.dialog = String(defaultThresholds.dialog)
  } catch (err) {
    console.error('Failed to load threshold config:', err)
  }
}

onMounted(() => {
  loadThresholds()
  loadScenes()
  document.addEventListener('keydown', handleKeydown)
})
</script>
