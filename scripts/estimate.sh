#!/bin/bash
#
# Fennec Scan Estimator
# Estimates how many files will be indexed and roughly how long it will take.
#
# Usage: ./estimate.sh /path/to/videos [/another/path ...]
#

set -e

# Supported extensions (matches scanner.py)
EXTENSIONS="mp4|mov|m4v|3gp|3g2|avi|mkv|webm|mxf|wmv|asf|flv|ts|m2ts|mts|mpg|mpeg|vob|ogv|rm|rmvb|wtv|dv|mj2|bik|bk2"

# Time estimates (seconds per file, conservative CPU estimates)
TIME_SCAN_PER_FILE=0.5        # FFprobe metadata extraction
TIME_SCENE_DETECT_PER_MIN=3   # Scene detection per minute of video
TIME_CLIP_PER_SCENE=2         # CLIP embedding per scene
TIME_WHISPER_PER_MIN=6        # Whisper transcription per minute of audio
TIME_ARCFACE_PER_SCENE=1      # Face detection per scene

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

if [ $# -eq 0 ]; then
    echo "Usage: $0 /path/to/videos [/another/path ...]"
    echo ""
    echo "Estimates how many video files Fennec will index."
    exit 1
fi

echo -e "${BLUE}🦊 Fennec Scan Estimator${NC}"
echo "================================"
echo ""

total_files=0
total_size=0

# Count files per extension
declare -A ext_counts

for search_path in "$@"; do
    if [ ! -d "$search_path" ]; then
        echo -e "${YELLOW}⚠️  Skipping (not a directory): $search_path${NC}"
        continue
    fi
    
    echo -e "Scanning: ${GREEN}$search_path${NC}"
    
    # Find all matching files
    while IFS= read -r -d '' file; do
        # Get extension (lowercase)
        ext="${file##*.}"
        ext_lower=$(echo "$ext" | tr '[:upper:]' '[:lower:]')
        
        # Increment count
        ext_counts[$ext_lower]=$((${ext_counts[$ext_lower]:-0} + 1))
        total_files=$((total_files + 1))
        
        # Get file size
        if [ -f "$file" ]; then
            size=$(stat -f%z "$file" 2>/dev/null || stat -c%s "$file" 2>/dev/null || echo 0)
            total_size=$((total_size + size))
        fi
    done < <(find "$search_path" -type f -iregex ".*\.\(${EXTENSIONS}\)$" -print0 2>/dev/null)
done

echo ""
echo "================================"
echo -e "${GREEN}Results${NC}"
echo "================================"
echo ""

if [ $total_files -eq 0 ]; then
    echo "No supported video files found."
    echo ""
    echo "Supported extensions: ${EXTENSIONS//|/, }"
    exit 0
fi

# Print breakdown by extension
echo "Files by extension:"
for ext in "${!ext_counts[@]}"; do
    printf "  .%-6s %d\n" "$ext" "${ext_counts[$ext]}"
done | sort -t' ' -k2 -rn

echo ""
echo "--------------------------------"
printf "Total files:    %d\n" "$total_files"

# Format size
if [ $total_size -gt 1099511627776 ]; then
    size_fmt=$(echo "scale=2; $total_size / 1099511627776" | bc)
    size_unit="TB"
elif [ $total_size -gt 1073741824 ]; then
    size_fmt=$(echo "scale=2; $total_size / 1073741824" | bc)
    size_unit="GB"
elif [ $total_size -gt 1048576 ]; then
    size_fmt=$(echo "scale=1; $total_size / 1048576" | bc)
    size_unit="MB"
else
    size_fmt=$total_size
    size_unit="bytes"
fi
printf "Total size:     %s %s\n" "$size_fmt" "$size_unit"

echo ""
echo "================================"
echo -e "${GREEN}Time Estimates${NC}"
echo "================================"
echo ""

# Estimate video duration (rough: 1 min per 100MB for typical HD video)
est_minutes=$((total_size / 100000000))
est_scenes=$((est_minutes * 2))  # Rough: 2 scenes per minute

# Calculate time estimates
scan_time=$((total_files * TIME_SCAN_PER_FILE))
scene_time=$((est_minutes * TIME_SCENE_DETECT_PER_MIN))
clip_time=$((est_scenes * TIME_CLIP_PER_SCENE))
whisper_time=$((est_minutes * TIME_WHISPER_PER_MIN))
arcface_time=$((est_scenes * TIME_ARCFACE_PER_SCENE))

total_time=$((scan_time + scene_time + clip_time + whisper_time + arcface_time))

# Format time
format_time() {
    local seconds=$1
    if [ $seconds -gt 86400 ]; then
        echo "$((seconds / 86400))d $((seconds % 86400 / 3600))h"
    elif [ $seconds -gt 3600 ]; then
        echo "$((seconds / 3600))h $((seconds % 3600 / 60))m"
    elif [ $seconds -gt 60 ]; then
        echo "$((seconds / 60))m $((seconds % 60))s"
    else
        echo "${seconds}s"
    fi
}

echo "Estimated video duration: ~${est_minutes} minutes (~$((est_minutes / 60)) hours)"
echo "Estimated scenes:         ~${est_scenes}"
echo ""
echo "Processing time (CPU, all models enabled):"
printf "  Initial scan:     %s\n" "$(format_time $scan_time)"
printf "  Scene detection:  %s\n" "$(format_time $scene_time)"
printf "  CLIP embeddings:  %s\n" "$(format_time $clip_time)"
printf "  Whisper (audio):  %s\n" "$(format_time $whisper_time)"
printf "  Face detection:   %s\n" "$(format_time $arcface_time)"
echo "  --------------------------------"
printf "  ${GREEN}Total estimate:    %s${NC}\n" "$(format_time $total_time)"
echo ""
echo -e "${YELLOW}Note: Times are rough estimates for CPU inference."
echo -e "Actual time varies based on video resolution, scene complexity, and hardware.${NC}"
