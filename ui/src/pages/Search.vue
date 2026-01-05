<template>
  <div class="max-w-7xl mx-auto px-4 py-4">
    <!-- Page title -->
    <div class="mb-4">
      <h1 class="text-lg font-semibold tracking-wide">Search</h1>
      <p class="text-gray-500 text-xs mt-0.5">
        Search shots by visual content, dialog, faces, and metadata
      </p>
    </div>

    <!-- Search Panel -->
    <div class="bg-[#171717] rounded-sm p-3 mb-4 border border-[#2a2a2a]">
      <div class="flex flex-wrap gap-3">
        <!-- Visual Content -->
        <div class="control-group flex-1 min-w-[280px]">
          <label class="control-label">
            <span class="flex items-center gap-1.5">
              <span class="category-swatch category-swatch-visual"></span>
              Visual Content
            </span>
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
            :placeholder="serverStatus.clipLoaded ? 'robot, explosion, outdoor scene...' : 'Loading CLIP model...'"
            :disabled="!serverStatus.clipLoaded"
            class="input-field"
            :class="{ 'opacity-50 cursor-not-allowed': !serverStatus.clipLoaded }"
            @input="debouncedSearch"
          />
          <!-- Color swatches toggle -->
          <div class="mt-1">
            <button
              @click="showColorSwatches = !showColorSwatches"
              class="flex items-center gap-1 text-[10px] text-gray-500 hover:text-gray-300 transition"
            >
              <svg
                class="w-3 h-3 transition-transform"
                :class="showColorSwatches ? 'rotate-90' : ''"
                fill="none" stroke="currentColor" viewBox="0 0 24 24"
              >
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"/>
              </svg>
              <span>colors</span>
            </button>
            <div v-show="showColorSwatches" class="color-scroll mt-1">
              <div class="flex gap-1">
                <button
                  v-for="color in colorSwatches"
                  :key="color.term"
                  @click="addColorTerm(color.term)"
                  class="w-5 h-4 rounded-sm flex-shrink-0 hover:ring-1 hover:ring-white transition"
                  :class="color.class"
                  :title="color.label"
                ></button>
              </div>
            </div>
          </div>
        </div>

        <!-- Dialog -->
        <div class="control-group min-w-[200px]">
          <label class="control-label">
            <span class="flex items-center gap-1.5">
              <span class="category-swatch category-swatch-dialog"></span>
              Dialog
            </span>
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
          <div class="flex items-center gap-1.5 mt-1">
            <span
              class="text-[10px] transition"
              :class="[
                dialogSearchMode === 'semantic' ? 'text-orange-400' : 'text-gray-500',
                !serverStatus.sentenceLoaded ? 'opacity-50' : ''
              ]"
            >{{ serverStatus.sentenceLoaded ? 'Semantic' : 'Loading...' }}</span>
            <button
              @click="toggleDialogMode"
              :disabled="!serverStatus.sentenceLoaded"
              class="w-6 h-3 bg-[#333] rounded-sm flex items-center px-0.5"
              :class="{ 'opacity-50 cursor-not-allowed': !serverStatus.sentenceLoaded }"
              title="Toggle between semantic (finds synonyms) and keyword (exact match) search"
            >
              <span
                class="w-2 h-2 bg-white rounded-sm transition-all duration-200"
                :class="dialogSearchMode === 'semantic' && serverStatus.sentenceLoaded ? 'ml-0' : 'ml-auto'"
              ></span>
            </button>
            <span
              class="text-[10px] transition"
              :class="dialogSearchMode === 'keyword' || !serverStatus.sentenceLoaded ? 'text-orange-400' : 'text-gray-500'"
            >Keyword</span>
          </div>
          <div v-if="dialogSearchMode === 'semantic' && !semanticTipDismissed" class="flex items-center gap-1.5 mt-1.5 px-2 py-1 bg-amber-500/10 border border-amber-500/20 rounded-sm">
            <svg class="w-3 h-3 text-amber-400 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
              <path d="M10 2a6 6 0 00-6 6v3.586l-.707.707A1 1 0 004 14h12a1 1 0 00.707-1.707L16 11.586V8a6 6 0 00-6-6zM10 18a3 3 0 01-3-3h6a3 3 0 01-3 3z"/>
            </svg>
            <span class="text-[10px] text-amber-200/80">Works best with phrases</span>
            <button @click="dismissSemanticTip" class="ml-auto text-amber-400/50 hover:text-amber-300 text-sm leading-none">&times;</button>
          </div>
        </div>

        <!-- Metadata Filter -->
        <div class="control-group flex-1 min-w-[320px]">
          <label class="control-label">
            <span class="flex items-center gap-1.5">
              <span class="category-swatch category-swatch-metadata"></span>
              Metadata
            </span>
          </label>
          <div class="flex flex-col gap-1.5">
            <!-- Active metadata filters as lozenges -->
            <div
              class="flex flex-wrap items-center gap-1 min-h-[28px] bg-[#262626] rounded-sm px-1.5 py-1"
            >
              <template v-if="metadataFilters.length === 0">
                <span class="text-gray-600 text-[10px]">Add filters below</span>
              </template>
              <span
                v-for="(mf, idx) in metadataFilters"
                :key="idx"
                class="inline-flex items-center gap-0.5 bg-orange-600/30 text-orange-300 text-[10px] px-1.5 py-0.5 rounded-sm"
              >
                <span class="font-medium">{{ mf.label }}</span>
                <button @click="removeMetadataFilter(idx)" class="hover:text-white">×</button>
              </span>
            </div>
            <!-- Add new filter row -->
            <div class="flex items-center gap-1.5">
              <select
                v-model="newMeta.key"
                class="bg-[#262626] rounded-sm px-1.5 py-1 text-xs text-gray-300 border-none outline-none appearance-none cursor-pointer hover:bg-[#333] pr-5"
                style="background-image: url('data:image/svg+xml;charset=UTF-8,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 width=%2210%22 height=%2210%22 viewBox=%220 0 12 12%22%3E%3Cpath fill=%22%239ca3af%22 d=%22M3 4.5L6 8l3-3.5H3z%22/%3E%3C/svg%3E'); background-repeat: no-repeat; background-position: right 6px center;"
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
                class="px-1.5 py-0.5 bg-orange-600 hover:bg-orange-500 rounded-sm text-[10px]"
              >
                Add
              </button>
            </div>
          </div>
        </div>

        <!-- Face Filter -->
        <div class="control-group flex-1 min-w-[140px]">
          <label class="control-label">
            <span class="flex items-center gap-1.5">
              <span class="category-swatch category-swatch-face"></span>
              Face Filter
            </span>
            <span class="flex items-center gap-1">
              <span class="text-gray-500 text-[10px] normal-case">min</span>
              <input
                type="text"
                v-model="thresholds.face"
                class="threshold-input"
              />
            </span>
          </label>
          <div class="flex items-center gap-1.5 min-h-[28px] bg-[#262626] rounded-sm px-1.5">
            <span v-if="!faceFilter" class="text-gray-600 text-[10px]">Click face in results</span>
            <template v-else>
              <canvas ref="faceCanvas" width="24" height="24" class="rounded-sm border border-teal-500"></canvas>
              <span class="text-[10px] text-gray-300">{{ faceFilter.filename ? `${formatFilename(faceFilter.filename, 12)} #${faceFilter.sceneIndex}` : `Scene ${faceFilter.sceneIndex}` }}</span>
              <button @click="clearFaceFilter" class="text-red-400 hover:text-red-300 text-[10px] ml-auto">×</button>
            </template>
          </div>
        </div>

        <!-- Visual Match -->
        <div class="control-group flex-1 min-w-[140px]">
          <label class="control-label">
            <span class="flex items-center gap-1.5">
              <span class="category-swatch category-swatch-visual-match"></span>
              Visual Match
            </span>
            <span class="flex items-center gap-1">
              <span class="text-gray-500 text-[10px] normal-case">min</span>
              <input
                type="text"
                v-model="thresholds.visualMatch"
                class="threshold-input"
              />
            </span>
          </label>
          <div class="flex items-center gap-1.5 min-h-[28px] bg-[#262626] rounded-sm px-1.5">
            <span v-if="!visualMatch" class="text-gray-600 text-[10px]">Click thumbnail to match</span>
            <template v-else>
              <img :src="getSceneThumbnail(visualMatch.sceneId, visualMatch.filename)" class="h-6 rounded-sm border border-violet-500" />
              <span class="text-[10px] text-gray-300">{{ visualMatch.filename ? `${formatFilename(visualMatch.filename, 12)} #${visualMatch.sceneIndex}` : `Scene ${visualMatch.sceneIndex}` }}</span>
              <button @click="clearVisualMatch" class="text-red-400 hover:text-red-300 text-[10px] ml-auto">×</button>
            </template>
          </div>
        </div>

        <!-- Actions -->
        <div class="control-group flex items-end">
          <div class="flex gap-1.5">
            <button
              @click="resetFilters"
              class="px-2 py-1 bg-[#262626] hover:bg-[#333] rounded-sm text-xs transition"
            >
              Reset
            </button>
            <button
              @click="search"
              class="px-3 py-1 bg-orange-500 hover:bg-orange-600 rounded-sm text-xs font-medium transition"
            >
              Search
            </button>
          </div>
        </div>
      </div>

      <!-- Filter Chain (Lozenges) -->
      <div v-if="activeFilters.length > 0" class="mt-3 flex flex-wrap items-center gap-1.5">
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

    <!-- Results Section -->
    <div class="border-t border-[#2a2a2a] pt-4">
    <!-- Results Header -->
    <div class="mb-3 flex justify-between items-center">
      <h2 class="text-sm font-semibold text-gray-300">Results</h2>
      <div class="flex items-center gap-3">
        <span class="text-gray-500 text-xs">{{ resultCount }}</span>
        <div v-if="results.length > 0" class="flex items-center gap-2">
          <button
            @click="addAllToEdl"
            class="flex items-center gap-1 px-2 py-0.5 bg-[#262626] hover:bg-[#333] rounded-sm text-[10px] text-gray-300 transition"
            title="Add all results to EDL"
          >
            <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/>
            </svg>
            Add All to EDL
          </button>
          <transition name="fade">
            <span v-if="edlFeedback" class="text-[10px] text-orange-400 font-medium">
              {{ edlFeedback }}
            </span>
          </transition>
        </div>
        <!-- Thumbnail size slider -->
        <div class="flex items-center gap-1.5">
          <span class="text-[10px] text-gray-500">Size</span>
          <input
            type="range"
            v-model="thumbnailColumns"
            min="3"
            max="8"
            class="w-20 accent-orange-500"
          />
        </div>
      </div>
    </div>

    <!-- Search Loading -->
    <div v-if="loading" class="text-center py-8">
      <div class="inline-block w-6 h-6 border-2 border-orange-500 border-t-transparent rounded-full animate-spin"></div>
      <p class="mt-2 text-gray-400 text-xs">Searching...</p>
    </div>

    <!-- Results Grid -->
    <div
      v-else-if="results.length > 0"
      class="grid gap-2"
      :style="{ gridTemplateColumns: `repeat(${thumbnailColumns}, minmax(0, 1fr))` }"
    >
      <div
        v-for="(scene, idx) in results"
        :key="scene.id"
        class="result-card group"
        @click="openScene(scene)"
      >
        <div class="thumbnail-container" :ref="el => thumbnailRefs[idx] = el">
          <img
            :src="getSceneThumbnail(scene.id, scene.filename)"
            :alt="`Scene ${scene.scene_index}`"
            class="w-full"
            style="aspect-ratio: 864/360;"
            @load="e => renderFaceBoxes(idx, scene, e.target)"
          />
          <!-- Similarity badges (colors from centralized CSS variables) -->
          <span
            v-if="scene.similarity"
            class="similarity-badge similarity-badge-visual"
          >
            {{ Math.round(scene.similarity * 100) }}%
          </span>
          <span
            v-if="scene.face_similarity && !scene.combined_similarity"
            class="similarity-badge similarity-badge-face"
            style="top: 24px;"
          >
            {{ Math.round(scene.face_similarity * 100) }}%
          </span>
          <span
            v-if="scene.transcript_similarity"
            class="similarity-badge similarity-badge-dialog"
            :style="{ top: (scene.similarity ? 24 : 4) + (scene.face_similarity ? 20 : 0) + 'px' }"
          >
            {{ Math.round(scene.transcript_similarity * 100) }}%
          </span>
          <!-- Match button -->
          <button
            @click.stop="setVisualMatch(scene.id, scene.scene_index, scene.filename)"
            class="absolute bottom-1 right-1 bg-orange-600/80 hover:bg-orange-500 text-white text-[10px] px-1 py-0.5 rounded-sm opacity-0 group-hover:opacity-100 transition-opacity"
            title="Find visually similar scenes"
          >
            Match
          </button>
        </div>
        <div class="p-1.5">
          <div class="text-[10px] text-gray-400 truncate" :title="scene.filename">{{ scene.filename }}</div>
          <div class="text-xs font-medium">Scene {{ scene.scene_index }}</div>
          <div class="flex items-center gap-1.5">
            <span class="text-[10px] text-gray-400 font-mono">
              {{ formatTimeWithFrames(scene.start_time, scene.fps) }} - {{ formatTimeWithFrames(scene.end_time - (1 / (scene.fps || 24)), scene.fps) }}
            </span>
            <span v-if="scene.fps" class="text-[9px] bg-[#333] text-gray-400 px-1 py-0.5 rounded-sm font-medium">
              {{ scene.fps }}fps
            </span>
          </div>
          <div
            v-if="scene.transcript"
            class="text-[10px] text-gray-500 mt-0.5 truncate"
            :title="scene.transcript"
          >
            "{{ scene.transcript }}"
          </div>
        </div>
      </div>
    </div>

    <!-- Empty State -->
    <div v-else class="text-center py-8">
      <p class="text-gray-500 text-xs">Enter search criteria to find scenes</p>
    </div>

    <!-- Load More -->
    <div v-if="hasMore && !loading" class="text-center py-4">
      <button
        @click="loadMore"
        class="px-4 py-1.5 bg-[#262626] hover:bg-[#333] rounded-sm text-xs font-medium transition"
      >
        Load More Scenes
      </button>
      <span class="text-gray-500 text-[10px] ml-2">{{ remainingCount }} more</span>
    </div>
    </div>

    <!-- Scene Modal -->
    <div
      v-if="selectedScene"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-3"
      @click.self="closeModal"
    >
      <div class="bg-[#171717] rounded-sm max-w-4xl w-full max-h-[90vh] overflow-y-auto">
        <div class="p-3 border-b border-[#262626] flex justify-between items-center">
          <div>
            <div class="flex items-center gap-1.5">
              <h3 class="text-sm font-semibold">Scene {{ selectedScene.scene_index }}</h3>
              <span v-if="selectedScene.fps" class="text-[10px] bg-orange-600/30 text-orange-300 px-1 py-0.5 rounded-sm font-medium">
                {{ selectedScene.fps }}fps
              </span>
              <span v-if="selectedScene.width && selectedScene.height" class="text-[10px] bg-[#333] text-gray-400 px-1 py-0.5 rounded-sm font-medium">
                {{ selectedScene.width }}×{{ selectedScene.height }}
              </span>
            </div>
            <p class="text-[10px] text-gray-500 truncate max-w-xl" :title="selectedScene.filename || selectedScene.path">
              {{ selectedScene.filename || selectedScene.path }}
            </p>
          </div>
          <button @click="closeModal" class="text-gray-400 hover:text-white text-xl">×</button>
        </div>
        <div class="p-3">
          <!-- Custom Video Player -->
          <div class="relative rounded-sm overflow-hidden bg-black">
            <!-- Spinner overlay - only shown until first valid frame -->
            <div
              v-if="showSpinner"
              class="absolute inset-0 z-10 bg-black flex items-center justify-center pointer-events-none"
            >
              <svg class="animate-spin h-8 w-8 text-gray-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
            </div>

            <!-- Canvas displays approved frames only -->
            <canvas
              ref="playerCanvas"
              class="w-full cursor-pointer"
              @click="togglePlay"
            ></canvas>

            <!-- Hidden video for decoding -->
            <video
              ref="hiddenVideo"
              class="hidden"
              :src="getVideoUrl(selectedScene.file_id)"
              preload="auto"
              @loadeddata="onVideoLoaded"
              @play="isPlaying = true"
              @pause="isPlaying = false"
              @error="onVideoError"
            ></video>

            <!-- Video error overlay -->
            <div
              v-if="videoError"
              class="absolute inset-0 z-30 bg-black/90 flex flex-col items-center justify-center text-center p-4"
            >
              <svg class="w-10 h-10 text-red-500 mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/>
              </svg>
              <p class="text-sm text-red-400 font-medium">Media not accessible</p>
              <p class="text-[10px] text-gray-500 mt-1 max-w-[200px]">
                The drive may be offline or the file was moved
              </p>
            </div>

            <!-- Custom Controls (z-20 to appear above buffering overlay) -->
            <div class="absolute bottom-0 left-0 right-0 z-20 bg-gradient-to-t from-black/90 to-transparent p-2 pt-6 select-none">
              <!-- Progress Bar (scene-only) -->
              <div
                class="relative h-1.5 bg-gray-700 rounded-sm cursor-pointer mb-2 group"
                @mousedown="startScrubbing"
                ref="progressBar"
              >
                <div
                  class="absolute h-full bg-orange-500 rounded-sm pointer-events-none"
                  :style="{ width: sceneProgress + '%' }"
                ></div>
                <div
                  class="absolute top-1/2 -translate-y-1/2 w-3 h-3 bg-white rounded-sm shadow-lg pointer-events-none"
                  :style="{ left: sceneProgress + '%', transform: 'translate(-50%, -50%)' }"
                ></div>
              </div>
              
              <!-- Controls Row -->
              <div class="flex items-center gap-1.5">
                <!-- Play/Pause -->
                <button @click="togglePlay" class="text-white hover:text-orange-400 transition p-0.5">
                  <svg v-if="!isPlaying" class="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M8 5v14l11-7z"/>
                  </svg>
                  <svg v-else class="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z"/>
                  </svg>
                </button>

                <!-- Time display -->
                <span class="text-white text-[10px] font-mono ml-1.5">
                  {{ formatTimeWithFrames(currentSceneTime) }} / {{ formatTimeWithFrames(sceneDuration) }}
                </span>

                <div class="flex-1"></div>

                <!-- Add to EDL button -->
                <button
                  @click="toggleEdl"
                  class="flex items-center gap-1 px-2 py-0.5 rounded-sm text-[10px] font-medium transition"
                  :class="isInEdl ? 'bg-green-600/30 text-green-400' : 'bg-[#333] hover:bg-[#444] text-white'"
                  :title="isInEdl ? 'Remove from EDL' : 'Add to EDL'"
                >
                  <svg v-if="isInEdl" class="w-3 h-3" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/>
                  </svg>
                  <svg v-else class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/>
                  </svg>
                  EDL
                </button>
              </div>
            </div>
          </div>

          <!-- Metadata Grid -->
          <div class="mt-3 grid grid-cols-2 sm:grid-cols-4 gap-2">
            <div class="metadata-item">
              <span class="metadata-key">In</span>
              <span class="metadata-value font-mono text-[10px]">{{ formatTimeWithFrames(selectedScene.start_time) }}</span>
            </div>
            <div class="metadata-item">
              <span class="metadata-key">Out</span>
              <span class="metadata-value font-mono text-[10px]">{{ formatTimeWithFrames(selectedScene.end_time - (1 / (selectedScene.fps || 24))) }}</span>
            </div>
            <div class="metadata-item">
              <span class="metadata-key">Duration</span>
              <span class="metadata-value font-mono text-[10px]">{{ formatTimeWithFrames(sceneDuration) }}</span>
            </div>
            <div class="metadata-item">
              <span class="metadata-key">Faces</span>
              <span class="metadata-value text-xs">{{ selectedScene.faces?.length || 0 }}</span>
            </div>
          </div>

          <!-- Vectors info -->
          <div v-if="selectedScene.vectors?.length" class="mt-2 p-2 bg-[#0d0d0d] rounded-sm">
            <span class="metadata-key">Vectors</span>
            <div class="flex flex-wrap gap-1.5 mt-1">
              <span
                v-for="(vec, idx) in selectedScene.vectors"
                :key="idx"
                class="inline-flex items-center gap-0.5 px-1.5 py-0.5 bg-[#1a1a1a] rounded-sm text-[10px]"
                :title="`${vec.model} ${vec.version} (${vec.dimension}d)${vec.count ? ` - ${vec.count} faces` : ''}`"
              >
                <span class="text-green-400">✓</span>
                <span class="text-gray-300">{{ vec.model }}</span>
                <span class="text-gray-500">{{ vec.dimension }}d</span>
                <span v-if="vec.count" class="text-amber-400">×{{ vec.count }}</span>
              </span>
            </div>
          </div>

          <div v-if="selectedScene.transcript" class="mt-2 p-2 bg-[#0d0d0d] rounded-sm">
            <span class="metadata-key">Dialog</span>
            <p class="text-gray-300 text-xs mt-0.5 italic">"{{ selectedScene.transcript }}"</p>
          </div>

          <!-- File Details Accordion -->
          <div class="mt-3 border border-[#333] rounded-sm overflow-hidden">
            <button
              @click="showFileDetails = !showFileDetails"
              class="w-full px-2 py-1.5 bg-[#1a1a1a] hover:bg-[#222] flex items-center justify-between text-xs transition"
            >
              <span class="text-gray-300 font-medium">File Details</span>
              <svg
                class="w-3 h-3 text-gray-500 transition-transform"
                :class="{ 'rotate-180': showFileDetails }"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/>
              </svg>
            </button>
            <div v-show="showFileDetails" class="p-2 bg-[#0d0d0d] border-t border-[#333]">
              <div class="grid grid-cols-2 gap-x-4 gap-y-1.5 text-xs">
                <div>
                  <span class="text-gray-500 text-[10px]">Path</span>
                  <p class="text-gray-300 font-mono text-[10px] break-all">{{ selectedScene.path || '—' }}</p>
                </div>
                <div>
                  <span class="text-gray-500 text-[10px]">Resolution</span>
                  <p class="text-gray-300 font-mono text-[10px]">{{ selectedScene.width && selectedScene.height ? `${selectedScene.width}×${selectedScene.height}` : '—' }}</p>
                </div>
                <div>
                  <span class="text-gray-500 text-[10px]">Codec</span>
                  <p class="text-gray-300 font-mono text-[10px]">{{ selectedScene.codec || '—' }}</p>
                </div>
                <div>
                  <span class="text-gray-500 text-[10px]">Frame Rate</span>
                  <p class="text-gray-300 font-mono text-[10px]">{{ selectedScene.fps ? `${selectedScene.fps} fps` : '—' }}</p>
                </div>
                <div>
                  <span class="text-gray-500 text-[10px]">Audio Tracks</span>
                  <p class="text-gray-300 font-mono text-[10px]">{{ selectedScene.audio_tracks ?? '—' }}</p>
                </div>
                <div>
                  <span class="text-gray-500 text-[10px]">File Size</span>
                  <p class="text-gray-300 font-mono text-[10px]">{{ formatFileSize(selectedScene.file_size_bytes) }}</p>
                </div>
                <div>
                  <span class="text-gray-500 text-[10px]">File Duration</span>
                  <p class="text-gray-300 font-mono text-[10px]">{{ selectedScene.duration_seconds ? formatTime(selectedScene.duration_seconds) : '—' }}</p>
                </div>
                <div>
                  <span class="text-gray-500 text-[10px]">Modified</span>
                  <p class="text-gray-300 font-mono text-[10px]">{{ formatDate(selectedScene.file_modified_at) }}</p>
                </div>
              </div>
            </div>
          </div>

        </div>
      </div>
    </div>

    <!-- Face Select Modal -->
    <div
      v-if="faceSelectModal"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-3"
      @click.self="closeFaceModal"
    >
      <div class="bg-[#171717] rounded-sm max-w-md w-full p-4">
        <h3 class="text-sm font-semibold mb-3">Select a face to filter by</h3>
        <div class="flex gap-3 flex-wrap justify-center">
          <div
            v-for="(face, idx) in faceSelectModal.faces"
            :key="face.id"
            class="text-center cursor-pointer hover:opacity-80"
            @click="selectFaceFromModal(faceSelectModal.sceneId, faceSelectModal.sceneIndex, face.id, face.bbox, faceSelectModal.filename)"
          >
            <canvas
              :ref="el => faceSelectRefs[idx] = el"
              width="64"
              height="64"
              class="rounded-sm border border-gray-600 hover:border-teal-500"
            ></canvas>
            <div class="text-[10px] text-gray-400 mt-0.5">Face {{ idx + 1 }}</div>
          </div>
        </div>
        <button @click="closeFaceModal" class="mt-3 text-gray-400 hover:text-white text-xs">
          Cancel
        </button>
      </div>
    </div>

  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted, nextTick, watch } from 'vue'
import { api, serverStatus } from '../services/api'
import {
  searchFilters as filters,
  searchThresholds as thresholds,
  dialogSearchMode,
  faceFilter,
  visualMatch,
  metadataFilters,
  filterOrder,
  searchResults as results,
  totalScenes,
  currentOffset,
  isSearchMode,
  thumbnailColumns,
  resetSearchState
} from '../services/searchState'

// Constants
const PAGE_SIZE = 40
const DEBOUNCE_MS = 400

// State
const loading = ref(false)
const thumbnailRefs = ref({})
const faceSelectRefs = ref({})
const faceCanvas = ref(null)
const hiddenVideo = ref(null)
const playerCanvas = ref(null)
const canvasCtx = ref(null)
const progressBar = ref(null)


// Video player state
const isPlaying = ref(false)
const showSpinner = ref(true)  // Show spinner until first valid frame
const videoError = ref(false)  // Show error when media can't load
const sceneProgress = ref(0)
const currentSceneTime = ref(0)
const isScrubbing = ref(false)
const videoFps = ref(24) // Default, will try to detect
const showPlaybackNotice = ref(!localStorage.getItem('dismissedPlaybackNotice'))

// Filters (imported from searchState)

// Default thresholds loaded from config
const defaultThresholds = reactive({
  visual: 0.10,
  face: 0.25,
  visualMatch: 0.20,
  dialog: 0.35
})

// Thresholds and dialog mode imported from searchState
const semanticTipDismissed = ref(localStorage.getItem('dismissedSemanticTip') === 'true')

// Face filter, visual match, filter order, and metadata filters imported from searchState
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

// Color swatches
const showColorSwatches = ref(false)
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

// EDL storage
const EDL_STORAGE_KEY = 'fennec_edl_scenes'
const edlTrigger = ref(0)  // Force reactivity on localStorage changes
const edlFeedback = ref('')  // Brief inline feedback message
let edlFeedbackTimer = null

function showEdlFeedback(msg) {
  clearTimeout(edlFeedbackTimer)
  edlFeedback.value = msg
  edlFeedbackTimer = setTimeout(() => {
    edlFeedback.value = ''
  }, 2000)
}

const isInEdl = computed(() => {
  edlTrigger.value  // Depend on trigger for reactivity
  if (!selectedScene.value) return false
  const saved = localStorage.getItem(EDL_STORAGE_KEY)
  if (!saved) return false
  try {
    const scenes = JSON.parse(saved)
    return scenes.some(s => s.sceneId === selectedScene.value.id)
  } catch {
    return false
  }
})

function toggleEdl() {
  if (!selectedScene.value) return

  const saved = localStorage.getItem(EDL_STORAGE_KEY)
  let scenes = []
  if (saved) {
    try {
      scenes = JSON.parse(saved)
    } catch {
      scenes = []
    }
  }

  const sceneId = selectedScene.value.id

  if (isInEdl.value) {
    // Remove from EDL
    scenes = scenes.filter(s => s.sceneId !== sceneId)
  } else {
    // Add to EDL
    const scene = selectedScene.value
    const fps = scene.fps || 24
    const frameTime = 1 / fps

    scenes.push({
      sceneId: scene.id,
      fileId: scene.file_id,
      filename: scene.filename || scene.path?.split('/').pop() || 'Unknown',
      inTc: scene.start_time,
      outTc: scene.end_time - frameTime,  // end_time is exclusive
      fps: fps
    })
  }

  localStorage.setItem(EDL_STORAGE_KEY, JSON.stringify(scenes))
  edlTrigger.value++
}

function addAllToEdl() {
  if (results.value.length === 0) return

  const saved = localStorage.getItem(EDL_STORAGE_KEY)
  let scenes = []
  if (saved) {
    try {
      scenes = JSON.parse(saved)
    } catch {
      scenes = []
    }
  }

  // Get existing scene IDs to avoid duplicates
  const existingIds = new Set(scenes.map(s => s.sceneId))
  let addedCount = 0

  for (const result of results.value) {
    if (existingIds.has(result.id)) continue

    const fps = result.fps || 24
    const frameTime = 1 / fps

    scenes.push({
      sceneId: result.id,
      fileId: result.file_id,
      filename: result.filename || result.path?.split('/').pop() || 'Unknown',
      inTc: result.start_time,
      outTc: result.end_time - frameTime,
      fps: fps
    })
    addedCount++
  }

  localStorage.setItem(EDL_STORAGE_KEY, JSON.stringify(scenes))
  edlTrigger.value++

  if (addedCount > 0) {
    showEdlFeedback(`+${addedCount} added`)
  } else {
    showEdlFeedback('Already in EDL')
  }
}

// Helper to format filename for display (truncate if too long)
function formatFilename(filename, maxLen = 20) {
  if (!filename) return ''
  // Remove extension for cleaner display
  const name = filename.replace(/\.[^/.]+$/, '')
  if (name.length <= maxLen) return name
  return name.slice(0, maxLen) + '...'
}

const activeFilters = computed(() => {
  const list = []
  for (const type of filterOrder.value) {
    if (type === 'visual' && filters.visual) {
      list.push({ type: 'visual', label: `Visual: ${filters.visual.slice(0, 20)}${filters.visual.length > 20 ? '...' : ''}` })
    } else if (type === 'dialog' && filters.dialog) {
      list.push({ type: 'dialog', label: `Dialog: "${filters.dialog.slice(0, 15)}${filters.dialog.length > 15 ? '...' : ''}"` })
    } else if (type === 'face' && faceFilter.value) {
      const f = faceFilter.value
      const label = f.filename
        ? `Face: ${formatFilename(f.filename)} #${f.sceneIndex}`
        : `Face from Scene ${f.sceneIndex}`
      list.push({ type: 'face', label })
    } else if (type === 'visual-match' && visualMatch.value) {
      const v = visualMatch.value
      const label = v.filename
        ? `Visual: ${formatFilename(v.filename)} #${v.sceneIndex}`
        : `Similar to Scene ${v.sceneIndex}`
      list.push({ type: 'visual-match', label })
    } else if (type === 'metadata' && metadataFilters.value.length > 0) {
      list.push({ type: 'metadata', label: `${metadataFilters.value.length} metadata filter${metadataFilters.value.length > 1 ? 's' : ''}` })
    }
  }
  return list
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

function getSceneThumbnail(sceneId, filename = '') {
  // Include filename for cache-busting across re-indexes (scene_id alone can be reused)
  const params = filename ? `?f=${encodeURIComponent(filename)}` : ''
  return `/api/thumbnail/${sceneId}${params}`
}

function getVideoUrl(fileId) {
  return `/api/video/${fileId}`
}

// Custom video player functions
// Playback range: true start to end-1frame (end_time is exclusive per scenedetect)
// requestVideoFrameCallback masks GOP decode catch-up, so no frame trimming needed
function getPlaybackRange() {
  const fps = selectedScene.value?.fps || 24
  const frameTime = 1 / fps
  const startTime = selectedScene.value?.start_time || 0
  const endTimeExclusive = selectedScene.value?.end_time || hiddenVideo.value?.duration || 0
  return {
    start: startTime,
    end: endTimeExclusive - frameTime,  // last valid frame (end is exclusive)
    frameTime
  }
}

// Canvas render loop - only draws frames within scene bounds
// This is the "gatekeeper" - out-of-bounds frames are simply not drawn
function renderFrame(_now, metadata) {
  if (!hiddenVideo.value || !canvasCtx.value) return

  const { start, end } = getPlaybackRange()

  // Only draw if frame is within scene bounds
  if (metadata.mediaTime >= start - 0.01 && metadata.mediaTime < end + 0.01) {
    canvasCtx.value.drawImage(
      hiddenVideo.value,
      0, 0,
      playerCanvas.value.width,
      playerCanvas.value.height
    )

    // First valid frame = hide spinner and unmute
    if (showSpinner.value) {
      showSpinner.value = false
      hiddenVideo.value.muted = false
    }

    // Update progress
    const duration = end - start
    currentSceneTime.value = Math.max(0, metadata.mediaTime - start)
    sceneProgress.value = duration > 0 ? Math.min(100, (currentSceneTime.value / duration) * 100) : 0
  }
  // else: canvas keeps showing last valid frame (automatic!)

  // Check for end of scene
  if (metadata.mediaTime >= end) {
    hiddenVideo.value.pause()
    sceneProgress.value = 100
    return
  }

  // Continue render loop if still playing
  if (!hiddenVideo.value.paused) {
    hiddenVideo.value.requestVideoFrameCallback(renderFrame)
  }
}

function onVideoLoaded() {
  if (!hiddenVideo.value || !playerCanvas.value || selectedScene.value?.start_time == null) return

  videoFps.value = selectedScene.value.fps || 24
  const { start } = getPlaybackRange()

  // Set canvas dimensions to match video
  playerCanvas.value.width = hiddenVideo.value.videoWidth
  playerCanvas.value.height = hiddenVideo.value.videoHeight
  canvasCtx.value = playerCanvas.value.getContext('2d')

  // Reset state
  sceneProgress.value = 0
  currentSceneTime.value = 0

  // Seek to start (muted during decode)
  hiddenVideo.value.muted = true
  hiddenVideo.value.currentTime = start

  hiddenVideo.value.addEventListener('seeked', () => {
    // Play to decode frames, render loop will draw first valid frame
    hiddenVideo.value.play()
    hiddenVideo.value.requestVideoFrameCallback(renderFrame)
  }, { once: true })
}

function onVideoError() {
  showSpinner.value = false
  videoError.value = true
}

function togglePlay() {
  if (!hiddenVideo.value) return

  if (hiddenVideo.value.paused) {
    const { start, end } = getPlaybackRange()

    // At end? Seek back to start
    if (hiddenVideo.value.currentTime >= end - 0.05) {
      showSpinner.value = true
      sceneProgress.value = 0
      currentSceneTime.value = 0
      hiddenVideo.value.muted = true
      hiddenVideo.value.currentTime = start

      hiddenVideo.value.addEventListener('seeked', () => {
        hiddenVideo.value.muted = false
        hiddenVideo.value.play()
        hiddenVideo.value.requestVideoFrameCallback(renderFrame)
      }, { once: true })
      return
    }

    // Normal play from current position
    hiddenVideo.value.muted = false
    hiddenVideo.value.play()
    hiddenVideo.value.requestVideoFrameCallback(renderFrame)
  } else {
    hiddenVideo.value.pause()
  }
}

function startScrubbing(event) {
  if (!hiddenVideo.value || !progressBar.value || !selectedScene.value) return

  isScrubbing.value = true
  hiddenVideo.value.pause()

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
  if (!hiddenVideo.value || !progressBar.value || !selectedScene.value) return

  const rect = progressBar.value.getBoundingClientRect()
  const percent = Math.max(0, Math.min(1, (event.clientX - rect.left) / rect.width))

  const { start, end } = getPlaybackRange()
  const duration = end - start

  const newTime = start + (percent * duration)
  hiddenVideo.value.currentTime = newTime

  // Update UI immediately for responsiveness
  currentSceneTime.value = percent * duration
  sceneProgress.value = percent * 100

  // Draw frame to canvas after seek
  hiddenVideo.value.addEventListener('seeked', () => {
    if (canvasCtx.value && hiddenVideo.value) {
      canvasCtx.value.drawImage(
        hiddenVideo.value,
        0, 0,
        playerCanvas.value.width,
        playerCanvas.value.height
      )
    }
  }, { once: true })
}

function dismissPlaybackNotice() {
  showPlaybackNotice.value = false
  localStorage.setItem('dismissedPlaybackNotice', 'true')
}

function dismissSemanticTip() {
  semanticTipDismissed.value = true
  localStorage.setItem('dismissedSemanticTip', 'true')
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
      // Fall back to keyword if sentence model not loaded
      if (dialogSearchMode.value === 'semantic' && serverStatus.sentenceLoaded) {
        params.transcript_semantic = filters.dialog
        params.transcript_threshold = parseFloat(thresholds.dialog) || 0.35
      } else {
        params.transcript = filters.dialog
      }
    }
    if (faceFilter.value) {
      // Always use face_id for accurate lookup (face_scene/face_index was broken - scene_index isn't globally unique)
      params.face_id = faceFilter.value.faceId
      params.face_threshold = parseFloat(thresholds.face) || 0.25
    }
    if (visualMatch.value) {
      params.visual_match_scene_id = visualMatch.value.sceneId
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

async function loadMore() {
  if (!isSearchMode.value) {
    const previousCount = results.value.length
    await loadScenes(false)
    // Scroll to show newly loaded thumbnails
    await nextTick()
    const firstNewThumb = thumbnailRefs.value[previousCount]
    if (firstNewThumb) {
      firstNewThumb.scrollIntoView({ behavior: 'smooth', block: 'start' })
    }
  }
}

function resetFilters() {
  resetSearchState(defaultThresholds)
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
        showFaceSelectModal(scene.id, scene.scene_index, scene.faces, scene.filename)
      } else {
        // Use face.id directly for accurate lookup
        selectFace(scene.id, scene.scene_index, face.id, bbox, scene.filename)
      }
    }

    container.appendChild(box)
  })
}

function showFaceSelectModal(sceneId, sceneIndex, faces, filename) {
  faceSelectModal.value = { sceneId, sceneIndex, faces, filename }
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
    img.src = getSceneThumbnail(sceneId, filename)
  })
}

function selectFace(sceneId, sceneIndex, faceId, bbox, filename) {
  // Use unique face.id for accurate server lookup (not scene_index which isn't globally unique)
  faceFilter.value = { sceneId, sceneIndex, faceId, bbox, filename }
  addFilter('face')
  closeFaceModal()

  // Draw face in filter display
  nextTick(() => {
    if (faceCanvas.value) {
      const img = new Image()
      img.crossOrigin = 'anonymous'
      img.onload = () => drawFaceCrop(faceCanvas.value, img, bbox, 28)
      img.src = getSceneThumbnail(sceneId, filename)
    }
  })

  search()
}

function selectFaceFromModal(sceneId, sceneIndex, faceId, bbox, filename) {
  selectFace(sceneId, sceneIndex, faceId, typeof bbox === 'string' ? JSON.parse(bbox) : bbox, filename)
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
function setVisualMatch(sceneId, sceneIndex, filename = null) {
  visualMatch.value = { sceneId, sceneIndex, filename }
  addFilter('visual-match')
  search()
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
  showSpinner.value = true  // Show spinner until first valid frame
  videoError.value = false  // Reset error state
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
}

function closeModal() {
  if (hiddenVideo.value) hiddenVideo.value.pause()
  selectedScene.value = null
}

function closeFaceModal() {
  faceSelectModal.value = null
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

function toggleDialogMode() {
  if (!serverStatus.sentenceLoaded) return
  dialogSearchMode.value = dialogSearchMode.value === 'semantic' ? 'keyword' : 'semantic'
  if (filters.dialog) debouncedSearch()
}

async function loadThresholds() {
  try {
    const [visualCfg, visualMatchCfg, faceCfg, dialogCfg] = await Promise.all([
      api.getConfig('search_threshold_visual'),
      api.getConfig('search_threshold_visual_match'),
      api.getConfig('search_threshold_face'),
      api.getConfig('search_threshold_transcript')
    ])

    defaultThresholds.visual = visualCfg.value ?? 0.10
    defaultThresholds.visualMatch = visualMatchCfg.value ?? 0.20
    defaultThresholds.face = faceCfg.value ?? 0.25
    defaultThresholds.dialog = dialogCfg.value ?? 0.35

    // Only set thresholds to defaults on first load (when they're still at initial values)
    if (thresholds.visual === '0.10' && thresholds.face === '0.25') {
      thresholds.visual = String(defaultThresholds.visual)
      thresholds.visualMatch = String(defaultThresholds.visualMatch)
      thresholds.face = String(defaultThresholds.face)
      thresholds.dialog = String(defaultThresholds.dialog)
    }
  } catch (err) {
    console.error('Failed to load threshold config:', err)
  }
}

onMounted(() => {
  loadThresholds()
  // Only load scenes if we don't already have results (preserves state when returning to page)
  if (results.value.length === 0) {
    loadScenes()
  }
  document.addEventListener('keydown', handleKeydown)
})

onUnmounted(() => {
  document.removeEventListener('keydown', handleKeydown)
})

// Auto-switch to semantic mode when sentence model loads (if no dialog filter entered)
watch(() => serverStatus.sentenceLoaded, (loaded) => {
  if (loaded && !filters.dialog && dialogSearchMode.value === 'keyword') {
    dialogSearchMode.value = 'semantic'
  }
})
</script>
