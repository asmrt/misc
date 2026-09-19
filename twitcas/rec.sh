#!/usr/bin/env bash
# いま録りたい1本だけを録る。外出先から SSH でこれを叩く用。
# 配信前でも --retry-streams で開始まで待ってくれるので、始まる前に仕掛けてもよい。
#
#   usage: rec.sh <user_id> [待ち時間の上限(分), 既定 180]
set -euo pipefail

user_id="${1:?usage: rec.sh <user_id> [max_wait_minutes]}"
max_wait_min="${2:-180}"
outdir="${TWITCAS_OUTDIR:-$HOME/twitcas}"
mkdir -p "$outdir"

out="${outdir}/${user_id}_$(date '+%Y%m%d_%H%M%S').ts"
retry_interval=10
retry_max=$(( max_wait_min * 60 / retry_interval ))

args=(
  --retry-streams "$retry_interval"
  --retry-max "$retry_max"
  --retry-open 5
  --stream-timeout 60
  --hls-live-restart
  -o "$out"
)
if [[ -n "${TWITCAS_PASSWORD:-}" ]]; then
  args+=(--twitcasting-password "$TWITCAS_PASSWORD")
fi

echo "recording -> $out" >&2
streamlink "${args[@]}" "https://twitcasting.tv/${user_id}" best
