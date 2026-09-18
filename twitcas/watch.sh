#!/usr/bin/env bash
# ツイキャスの配信開始を監視して、始まったら自動で録画する常駐スクリプト。
# リスナー側（他人の配信を追う側）の想定。
#
#   usage: watch.sh <user_id>
#   env:
#     TWITCAS_OUTDIR      保存先ディレクトリ (既定: ~/twitcas)
#     TWITCAS_INTERVAL    監視間隔(秒)       (既定: 30)
#     TWITCAS_PASSWORD    合言葉つき配信のパスワード
#     TWITCAS_EXTRA_ARGS  streamlink に足したい引数
#                         例: 限定配信を録る --http-cookie 'keyword=value'
#     TWITCAS_NOTIFY_URL  配信開始/録画完了の通知先
#                         ntfy.sh の URL か Discord の Webhook URL
#
# 必要なもの: bash, curl, jq, streamlink
set -euo pipefail

user_id="${1:?usage: watch.sh <user_id>}"
outdir="${TWITCAS_OUTDIR:-$HOME/twitcas}"
interval="${TWITCAS_INTERVAL:-30}"
ua="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"

mkdir -p "$outdir"

log() { printf '%s [%s] %s\n' "$(date '+%F %T')" "$user_id" "$*" >&2; }

# 配信開始に気づけないのがリスナー側の一番の課題なので、手元にも飛ばす。
# 通知が落ちても録画は続けたいので、失敗しても無視する。
notify() {
  local msg="$1"
  [[ -n "${TWITCAS_NOTIFY_URL:-}" ]] || return 0
  if [[ "$TWITCAS_NOTIFY_URL" == *discord.com/api/webhooks/* ]]; then
    curl -fsS --max-time 10 -H 'Content-Type: application/json' \
      -d "$(jq -nc --arg c "$msg" '{content: $c}')" \
      "$TWITCAS_NOTIFY_URL" >/dev/null 2>&1 || log "notify failed"
  else
    curl -fsS --max-time 10 -d "$msg" "$TWITCAS_NOTIFY_URL" >/dev/null 2>&1 || log "notify failed"
  fi
}

# streamlink の twitcasting プラグインが見ているのと同じ、認証不要のエンドポイント。
# 生存なら "live <movie_id>"、そうでなければ "offline" / "unknown" を返す。
live_status() {
  curl -fsS --max-time 10 -A "$ua" \
    "https://twitcasting.tv/streamserver.php?target=${user_id}&mode=client&player=pc_web" 2>/dev/null \
    | jq -r 'if (.movie.id // null) != null and ((.movie.live == true) or (.movie.live == 1))
             then "live \(.movie.id)" else "offline" end' 2>/dev/null \
    || echo "unknown"
}

# 配信が続いているあいだブロックして録り続ける。
record() {
  local movie_id="$1"
  local out="${outdir}/${user_id}_$(date '+%Y%m%d_%H%M%S')_${movie_id}.ts"
  local -a args=(
    --loglevel info
    --retry-streams 5    # 配信開始直後、まだストリームが生えていない瞬間の取りこぼし対策
    --retry-open 5
    --stream-timeout 60
    --hls-live-restart   # HLS が保持している分だけ頭が巻き戻せることがある(効かない配信もある)
    -o "$out"
  )
  if [[ -n "${TWITCAS_PASSWORD:-}" ]]; then
    args+=(--twitcasting-password "$TWITCAS_PASSWORD")
  fi
  if [[ -n "${TWITCAS_EXTRA_ARGS:-}" ]]; then
    local -a extra
    read -ra extra <<<"$TWITCAS_EXTRA_ARGS"
    args+=("${extra[@]}")
  fi

  log "recording -> $out"
  notify "🔴 ${user_id} が配信開始。録画をはじめました → https://twitcasting.tv/${user_id}"
  streamlink "${args[@]}" "https://twitcasting.tv/${user_id}" best || log "streamlink exited: $?"

  if [[ -s "$out" ]]; then
    local size
    size="$(du -h "$out" | cut -f1)"
    log "saved: $out ($size)"
    notify "⏹ ${user_id} の録画が終わりました ($size) — $(basename "$out")"
  else
    rm -f "$out"
    log "nothing recorded, removed empty file"
    notify "⚠️ ${user_id} の録画に失敗しました（中身が空）"
  fi
}

log "watching (interval=${interval}s, outdir=${outdir})"
while :; do
  status="$(live_status)"
  case "$status" in
    "live "*) record "${status#live }" ;;
    unknown)  log "status unknown (network?)" ;;
  esac
  sleep "$interval"
done
