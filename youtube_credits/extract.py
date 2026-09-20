"""シクフォニの楽曲動画の概要欄から、クレジットを抽出する。

ネットワークには触らない純粋なパース処理だけを置く。
"""

import re

MEMBERS = ["暇72", "雨乃こさめ", "いるま", "LAN", "すち", "みこと"]
GROUP_NAME = "シクフォニ"

# NFKC等の強い正規化は曲名の意匠(T4xi DЯiver 等)を壊すため、ゼロ幅文字の除去だけ行う
_ZERO_WIDTH = dict.fromkeys(map(ord, "​‌‍⁠﻿"), None)

_DIVIDER = re.compile(r"^[┄─━―—=＝\-]{4,}$")
_HONORIFIC = re.compile(r"敬称略")
_NAME_CUT = re.compile(r"[　(（]")
_MULTI_NAME = re.compile(r"\s*[/／]\s*")

# 「絵」「動画」は Main Animation ＆ IIlustration のような複合ラベルがあるため部分一致。
# 綴り揺れ(IIlustration)を吸収するため i/l の繰り返しを許す。
# 「作詞」「作曲」は Music Video 等への誤爆を避けるため完全一致。
_LABEL_RULES = [
    ("作曲", [r"^music$", r"^composer?$", r"^compose$", r"^作曲$"], True),
    ("作詞", [r"^lyrics?$", r"^作詞$"], True),
    ("絵", [r"i{1,3}l{0,3}ustrat", r"イラスト", r"作画"], False),
    ("動画", [r"movie", r"^動画$"], False),
]

# 歌詞全文をクレジットとして誤取得しないための上限
_MAX_VALUE_LINES = 8
_MAX_NAME_LEN = 40


def strip_invisible(text):
    return (text or "").translate(_ZERO_WIDTH)


def _normalize_label(label):
    return re.sub(r"[^0-9a-zぁ-んァ-ヶ一-龥]", "", label.lower())


def _clean_name(raw):
    """`藤浪 潤一郎　( https://... )` や `呉井辰吉(SUPA LOVE)` から名前だけ取り出す。

    区切りは全角スペースか括弧の開始位置。名前自体が半角スペースを含むため、
    空白全般で切ってはいけない。
    """
    s = raw.strip()
    cut = _NAME_CUT.search(s)
    if cut:
        s = s[: cut.start()]
    return s.strip(" 　")


def _names_from(value_lines):
    names = []
    for line in value_lines:
        cleaned = _clean_name(line)
        if not cleaned:
            continue
        names.extend(p.strip() for p in _MULTI_NAME.split(cleaned) if p.strip())
    return names


def parse_credit_blocks(description):
    """概要欄から ◆ラベル のクレジット項目を順に拾う。

    「敬称略」の行より後ろは歌詞全文などの別セクションとみなし、cutoff 済みとして印を付ける。
    """
    lines = strip_invisible(description).split("\n")
    blocks = []
    before_cutoff = True
    i = 0
    while i < len(lines):
        line = lines[i]
        if _HONORIFIC.search(line):
            before_cutoff = False
            i += 1
            continue
        if not line.startswith("◆"):
            i += 1
            continue

        label = line[1:].strip().strip("◆")
        values = []
        j = i + 1
        while j < len(lines):
            nxt = lines[j]
            if not nxt.strip():
                break
            if nxt.startswith("◆") or _DIVIDER.match(nxt.strip()) or _HONORIFIC.search(nxt):
                break
            values.append(nxt)
            j += 1
        blocks.append({"label": label, "values": values, "before_cutoff": before_cutoff})
        i = j
    return blocks


def _match_column(label):
    normalized = _normalize_label(label)
    for column, patterns, exact in _LABEL_RULES:
        for pattern in patterns:
            if exact:
                if re.fullmatch(pattern.strip("^$"), normalized):
                    return column
            elif re.search(pattern, normalized):
                return column
    return None


def credits_by_column(description):
    """列名 -> {names, suspect} の辞書。取れなかった列は入らない。"""
    found = {}
    for block in parse_credit_blocks(description):
        column = _match_column(block["label"])
        if column is None or column in found:
            continue  # 同じラベルの2回目(歌詞見出し等)は無視する
        names = _names_from(block["values"])
        suspect = None
        if not block["before_cutoff"]:
            suspect = f"{column}: 敬称略より後ろのラベルしか無い"
        elif not names:
            suspect = f"{column}: ラベルはあるが値が空"
        elif len(names) > _MAX_VALUE_LINES:
            suspect = f"{column}: 値が{len(names)}件あり多すぎる"
        elif any(len(n) > _MAX_NAME_LEN for n in names):
            suspect = f"{column}: 値が長すぎる(歌詞混入の疑い)"
        found[column] = {"names": names, "suspect": suspect, "label": block["label"]}
    return found


_COVER_MARK = "【Cover】"
_ORIGINAL_TITLE = re.compile(r"^\s*シクフォニ\s*[-‐－ー–—]\s*(?P<song>.+?)\s*\[Official")
_HONKE_SONG = re.compile(r"[『「]\s*(?P<song>[^』」]+?)\s*[』」]")
_TRAILING_BRACKET = re.compile(r"【(?P<inner>[^【】]*)】\s*$")
_MEMBER_SPLIT = re.compile(r"\s*[×xX＆&,、・･]\s*")


def extract_song(title, description):
    """曲名と原曲アーティストを返す。取れなければ (None, None, 理由)。"""
    title = strip_invisible(title)

    if _COVER_MARK in title:
        head = title.split(_COVER_MARK)[0]
        if "】" in head:
            head = head[head.rindex("】") + 1 :]
        if "/" in head:
            song, _, artist = head.rpartition("/")
            return song.strip(), artist.strip(), None
        if head.strip():
            return head.strip(), None, "原曲アーティストが分離できない"
        return None, None, "【Cover】はあるが曲名が取れない"

    original = _ORIGINAL_TITLE.match(title)
    if original:
        return original.group("song").strip(), GROUP_NAME, None

    honke = _HONKE_SONG.search(_honke_block(description))
    if honke:
        return honke.group("song").strip(), None, "タイトルから取れず本家様欄から推定"

    return None, None, "タイトルが既知の形式に当てはまらない"


def _honke_block(description):
    text = strip_invisible(description)
    if "▼本家様" not in text:
        return ""
    after = text.split("▼本家様", 1)[1]
    return "\n".join(after.split("\n")[:4])


def extract_singers(title):
    """歌っているメンバー。タイトルに手掛かりが無ければ全員と仮置きし、推定フラグを返す。"""
    title = strip_invisible(title)
    bracket = _TRAILING_BRACKET.search(title)
    if bracket:
        inner = bracket.group("inner")
        # 「暇72×すち / シクフォニ」からグループ名の部分を落とす
        parts = [p.strip() for p in re.split(r"\s*[/／]\s*", inner)]
        parts = [p for p in parts if p and GROUP_NAME not in p]
        if parts:
            names = []
            for part in parts:
                names.extend(n.strip() for n in _MEMBER_SPLIT.split(part) if n.strip())
            unknown = [n for n in names if n not in MEMBERS]
            if names and not unknown:
                return names, None
            if names:
                return names, f"メンバー名簿に無い表記: {'/'.join(unknown)}"

    return list(MEMBERS), "タイトルに歌唱者の表記が無く全員と仮置き"


def to_jst_date(published_at):
    """publishedAt(UTC, ISO8601) を JST の日付文字列にする。"""
    from datetime import datetime, timedelta, timezone

    dt = datetime.strptime(published_at, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    return (dt + timedelta(hours=9)).strftime("%Y-%m-%d")


ROW_FIELDS = [
    "曲名",
    "投稿日",
    "チャンネル",
    "タイトル",
    "歌ってる人",
    "作詞",
    "作曲",
    "絵",
    "動画",
    "category",
    "原曲アーティスト",
    "video_id",
    "動画URL",
    "要確認",
    "要確認理由",
    "raw_description",
]


def build_row(video, category):
    """videos.list の1件を表の1行にする。"""
    snippet = video["snippet"]
    title = snippet["title"]
    description = snippet.get("description", "")

    song, original_artist, song_note = extract_song(title, description)
    singers, singer_note = extract_singers(title)
    credits = credits_by_column(description)

    notes = [n for n in (song_note, singer_note) if n]
    values = {}
    for column in ("作詞", "作曲", "絵", "動画"):
        entry = credits.get(column)
        if entry is None:
            values[column] = ""
            notes.append(f"{column}: 該当ラベルが概要欄に無い")
            continue
        if entry["suspect"]:
            notes.append(entry["suspect"])
            values[column] = ""
            continue
        values[column] = " / ".join(entry["names"])

    return {
        "曲名": song or "",
        "投稿日": to_jst_date(snippet["publishedAt"]),
        "チャンネル": snippet.get("channelTitle", ""),
        # 曲名の抽出に失敗した行を人手で直すには元タイトルが要る
        "タイトル": strip_invisible(title),
        "歌ってる人": " / ".join(singers),
        "作詞": values["作詞"],
        "作曲": values["作曲"],
        "絵": values["絵"],
        "動画": values["動画"],
        "category": category,
        "原曲アーティスト": original_artist or "",
        "video_id": video["id"],
        "動画URL": f"https://youtu.be/{video['id']}",
        "要確認": "要確認" if notes else "",
        "要確認理由": " / ".join(notes),
        "raw_description": description,
    }
