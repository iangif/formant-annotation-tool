#!/usr/bin/env bash
set -euo pipefail

# Remote host
REMOTE_USER_HOST="igiffo@oka"
REMOTE_BASE="/media/share/corpora/formants/ls_eng/common"

# Local project root
PROJECT_ROOT="$HOME/formant-annotation-tool"
# Local images folder
LOCAL_IMAGES="$PROJECT_ROOT/app/static/images"
# Local audio folder
LOCAL_AUDIO="$PROJECT_ROOT/app/static/audio"
# Local data folder for CSV
LOCAL_DATA="$PROJECT_ROOT/data"
LOCAL_CSV="$LOCAL_DATA/common_pilot_0_49.csv"

mkdir -p "$LOCAL_IMAGES" "$LOCAL_AUDIO" "$LOCAL_DATA"

echo "Copying pilot images and audio files..."

for i in $(seq 43 49); do
    prefix=$(printf "%05d" "$i")

    scp "${REMOTE_USER_HOST}:${REMOTE_BASE}/fasttrack/${prefix}_*.png" "$LOCAL_IMAGES/"
    scp "${REMOTE_USER_HOST}:${REMOTE_BASE}/audio/${prefix}_*.wav" "$LOCAL_AUDIO/"
    scp "${REMOTE_USER_HOST}:${REMOTE_BASE}/audio/${prefix}_*.TextGrid" "$LOCAL_AUDIO/"
done

echo "Copying and filtering CSV rows..."

ssh "$REMOTE_USER_HOST" "awk -F, 'NR == 1 || (\$1 >= 0 && \$1 <= 49)' ${REMOTE_BASE}/common.csv" > "$LOCAL_CSV"

echo "Done."
echo "Images copied to: $LOCAL_IMAGES"
echo "Audio copied to:  $LOCAL_AUDIO"
echo "CSV written to:   $LOCAL_CSV"