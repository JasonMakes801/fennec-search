#!/bin/bash
# Download demo footage - individual vintage commercials + classic films
# Run: ./scripts/download_demo_footage.sh [output_dir]
#
# Content: ~100 files of varied footage for demo
# Great for demo: lots of faces, dialog, scene variety
# Re-run to resume interrupted downloads (skips existing files)

OUTPUT_DIR="${1:-./demo_footage}"
mkdir -p "$OUTPUT_DIR"

# Track stats
SUCCESS_COUNT=0
FAIL_COUNT=0
SKIP_COUNT=0

echo "========================================"
echo "Fennec Demo Footage Downloader"
echo "========================================"
echo ""
echo "Output: $OUTPUT_DIR"
echo ""

# Check for yt-dlp
if ! command -v yt-dlp &> /dev/null; then
    echo "❌ yt-dlp required. Install with: pip install yt-dlp"
    exit 1
fi

# Function to download from YouTube
download_youtube() {
    local url="$1"
    local output_name="$2"
    local display_name="$3"
    local output_path="${OUTPUT_DIR}/${output_name}"

    if [ -f "$output_path" ]; then
        echo "  ✓ Exists: $display_name"
        ((SKIP_COUNT++))
        return 0
    fi

    if yt-dlp -q -f "bv*[vcodec^=avc]+ba/b" -o "$output_path" "$url" 2>/dev/null; then
        echo "  ✓ $display_name"
        ((SUCCESS_COUNT++))
    else
        echo "  ✗ Failed: $display_name"
        rm -f "$output_path"
        ((FAIL_COUNT++))
    fi
}

echo "=== 1980s COMMERCIALS (individual ads, ~30 each) ==="
echo ""

# Individual 1980s commercials - all verified short clips
download_youtube "https://www.youtube.com/watch?v=idnwh6iDnXA" "1984_wendys_wheres_the_beef.mp4" "Wendy's - Where's the Beef (1984)"
download_youtube "https://www.youtube.com/watch?v=fcJAhAqhRww" "1980s_nestle_crunch.mp4" "Nestle Crunch"
download_youtube "https://www.youtube.com/watch?v=Za86WAx-lms" "1980s_sony_walkman.mp4" "Sony Walkman"
download_youtube "https://www.youtube.com/watch?v=ieALfasC6pw" "1980_taco_bell.mp4" "Taco Bell (1980)"
download_youtube "https://www.youtube.com/watch?v=9qAfN_5ZIbM" "1980s_mcdonalds_happy_meal.mp4" "McDonald's Happy Meal"
download_youtube "https://www.youtube.com/watch?v=UBg442m6C0M" "1980s_hardees.mp4" "Hardee's"
download_youtube "https://www.youtube.com/watch?v=bkQyZdy60sI" "1980s_trapper_keeper.mp4" "Mead Trapper Keeper"
download_youtube "https://www.youtube.com/watch?v=XvRcmZ3Pb58" "1980s_chick_fil_a.mp4" "Chick-fil-A"
download_youtube "https://www.youtube.com/watch?v=yBBtz-dBoT8" "1988_la_gear.mp4" "LA Gear Shoes (1988)"
download_youtube "https://www.youtube.com/watch?v=gyyf6PyZNSA" "1980s_oreo.mp4" "Oreo"
download_youtube "https://www.youtube.com/watch?v=2N54BZ6L-m0" "1980s_cinnamon_toast_crunch.mp4" "Cinnamon Toast Crunch"
download_youtube "https://www.youtube.com/watch?v=iYvxKFJXoMc" "1980s_radio_shack_xmas.mp4" "Radio Shack Christmas"
download_youtube "https://www.youtube.com/watch?v=J2jRuh1bAxw" "1980s_radio_shack_computer.mp4" "Radio Shack Computer"
download_youtube "https://www.youtube.com/watch?v=148SEdxLcoc" "1980_cadillac.mp4" "Cadillac (1980)"
download_youtube "https://www.youtube.com/watch?v=QUe8CS-Ov7w" "1980s_slinky.mp4" "Slinky"
download_youtube "https://www.youtube.com/watch?v=uhynG2yZM5w" "1980s_whatchamacallit.mp4" "Whatchamacallit Candy Bar"
download_youtube "https://www.youtube.com/watch?v=1QqP2PuBjeM" "1980s_fancy_feast.mp4" "Fancy Feast"
download_youtube "https://www.youtube.com/watch?v=e5UPjQxWsU4" "1980s_hostess.mp4" "Hostess Snacks"
download_youtube "https://www.youtube.com/watch?v=7hJmFsMFF4g" "1980s_sweet_16_makeup.mp4" "Sweet 16 Makeup"
download_youtube "https://www.youtube.com/watch?v=RBauT4ADKbw" "1980s_maxell_tape.mp4" "Maxell Tape"
download_youtube "https://www.youtube.com/watch?v=W9RTVDA9Cr0" "1980s_honeycomb_andre.mp4" "Honeycomb (Andre the Giant)"

echo ""
echo "=== 1970s COMMERCIALS ==="
echo ""

download_youtube "https://www.youtube.com/watch?v=bvLqAXCEFts" "1970s_mcdonalds_big_mac.mp4" "McDonald's Big Mac"
download_youtube "https://www.youtube.com/watch?v=dXN14aA4_p4" "1970s_coca_cola_hilltop.mp4" "Coca-Cola Hilltop"
download_youtube "https://www.youtube.com/watch?v=0WOlDGXJbKs" "1970s_oscar_mayer_bologna.mp4" "Oscar Mayer Bologna"
download_youtube "https://www.youtube.com/watch?v=UNa7LiXKJXo" "1970s_mikey_life_cereal.mp4" "Life Cereal (Mikey)"
download_youtube "https://www.youtube.com/watch?v=Km4f-eRE4Kc" "1970s_miller_lite.mp4" "Miller Lite"
download_youtube "https://www.youtube.com/watch?v=fN5JvLe7qZs" "1970s_burger_king.mp4" "Burger King"
download_youtube "https://www.youtube.com/watch?v=1jgE-lrfZ3k" "1970s_oscar_mayer_wiener.mp4" "Oscar Mayer Wiener"
download_youtube "https://www.youtube.com/watch?v=dJRsWJqDjFE" "1979_mcdonalds.mp4" "McDonald's (1979)"
download_youtube "https://www.youtube.com/watch?v=78KNS6cL2y8" "1970s_mr_clean.mp4" "Mr. Clean"
download_youtube "https://www.youtube.com/watch?v=zWEbGD-vPRQ" "1970s_kool_aid.mp4" "Kool-Aid"

echo ""
echo "=== 1990s COMMERCIALS ==="
echo ""

download_youtube "https://www.youtube.com/watch?v=eyd51lvu3xw" "1990s_budweiser_frogs.mp4" "Budweiser Frogs"
download_youtube "https://www.youtube.com/watch?v=WOi0sgAGbSg" "1990s_got_milk.mp4" "Got Milk?"
download_youtube "https://www.youtube.com/watch?v=1VM2eLhvsSM" "1990s_pepsi_cindy_crawford.mp4" "Pepsi (Cindy Crawford)"
download_youtube "https://www.youtube.com/watch?v=owGykVbfgUE" "1990s_mcdonalds.mp4" "McDonald's (1990s)"
download_youtube "https://www.youtube.com/watch?v=w2Nb6kYvCkY" "1990s_pizza_hut_bigfoot.mp4" "Pizza Hut Bigfoot"
download_youtube "https://www.youtube.com/watch?v=5R0Fmq2qL-s" "1990s_gatorade_jordan.mp4" "Gatorade (Michael Jordan)"
download_youtube "https://www.youtube.com/watch?v=c2VVy8gVrNo" "1990s_rice_krispies.mp4" "Rice Krispies"
download_youtube "https://www.youtube.com/watch?v=Y6rE0EakhG8" "1990s_nintendo_64.mp4" "Nintendo 64"
download_youtube "https://www.youtube.com/watch?v=ZqaCEPwWGtc" "1990s_skip_it.mp4" "Skip-It"
download_youtube "https://www.youtube.com/watch?v=4dJO0n1GPdg" "1990s_crossfire.mp4" "Crossfire"

echo ""
echo "=== 1950s-1960s COMMERCIALS ==="
echo ""

download_youtube "https://www.youtube.com/watch?v=oQbei5JGiT8" "1950s_winston_cigarettes.mp4" "Winston Cigarettes (Flintstones)"
download_youtube "https://www.youtube.com/watch?v=2gFsOoKAHZg" "1960s_folgers.mp4" "Folgers Coffee"
download_youtube "https://www.youtube.com/watch?v=bxfSgQsC_A4" "1960s_jello.mp4" "Jello"
download_youtube "https://www.youtube.com/watch?v=OsIL-rFl5u4" "1950s_lucky_strike.mp4" "Lucky Strike"
download_youtube "https://www.youtube.com/watch?v=L0A9lP7WQ7g" "1960s_alka_seltzer.mp4" "Alka-Seltzer"

echo ""
echo "=== CLASSIC FILMS (public domain) ==="
echo ""

# Design for Dreaming - 10 min, color, stunning 1950s GM Motorama
download_youtube \
    "https://www.youtube.com/watch?v=4_ccAf82RQ8" \
    "design_for_dreaming_1956.mp4" \
    "Design for Dreaming (1956)"

# Night of the Living Dead - iconic
download_youtube \
    "https://www.youtube.com/watch?v=J7Yvhe5fKmM" \
    "night_of_the_living_dead_1968.mp4" \
    "Night of the Living Dead (1968)"

echo ""
echo "=== MODERN (public domain) ==="
echo ""

# NASA ISS Tour
download_youtube \
    "https://www.youtube.com/watch?v=nmBbcNTUkOg" \
    "nasa_iss_tour.mp4" \
    "NASA ISS Tour"

echo ""
echo "========================================"
echo "Download Complete"
echo "========================================"
echo ""
echo "Results: $SUCCESS_COUNT downloaded, $SKIP_COUNT skipped, $FAIL_COUNT failed"
if [ $FAIL_COUNT -gt 0 ]; then
    echo "(Re-run to retry failed downloads)"
fi
echo ""

# Count total files
total_files=$(find "$OUTPUT_DIR" -type f -name "*.mp4" | wc -l | tr -d ' ')

ls -la "$OUTPUT_DIR"
echo ""
echo "Total: $(du -sh "$OUTPUT_DIR" | cut -f1) in $total_files files"
echo ""
echo "Next: Add '$(cd "$OUTPUT_DIR" && pwd)' as watch folder in Settings"
