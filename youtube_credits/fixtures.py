"""実際に YouTube Data API から取得した概要欄を、そのままテスト用に保持する。

歌詞セクションは長いため冒頭数行だけに切り詰めてあるが、
◆Lyrics が2回出てくるという構造はそのまま残している。
全角スペース・綴り揺れ(IIlustration)・ゼロ幅文字は原文どおり。
"""

COVER_SHOUJO_REI = {
    "id": "Y2MOUQY48_s",
    "snippet": {
        "title": "【とり憑かれた6人で】少女レイ / みきとP【Cover】【シクフォニ】",
        "publishedAt": "2026-08-31T10:00:06Z",
        "channelTitle": "シクフォニ【SIXFONIA】",
        "description": """＿＿＿愛し合えたら

××× 毎日更新＿＿＿現在464日目！ ×××

▼Cover Song Playlist
https://www.youtube.com/playlist?list=PLppXIlUC-oPw8uCDchVYal9ibApaYP-4R

┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄

▼本家様
みきとP 『 少女レイ 』 MV
https://youtu.be/JW3N-HvU0MA

┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄

運命を掴み取る最強の6人による2.5次元タレントグループ

Color：赤
暇72
https://x.com/hima72_25

Color：緑
すち
https://x.com/suchi_paint


◆Mix
ソノイ(In Fleur Inc.) 　( https://x.com/_Sonoi )

◆Instrumental
Studio Rabbits　( https://x.com/studio_rabbits )

◆Illustration
麺　( https://x.com/mendayooo )

◆Movie
MERO　( https://x.com/M3ro_pv )

※敬称略

┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄
◆スケジュール
長尺動画投稿 ▶ 週2　基本毎週火・金曜日
┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄


#歌ってみた #少女レイ #みきとP #シクフォニ""",
    },
}

# ◆の並び順が上と逆。Instrumental は URL ではなく所属会社名が括弧に入る。
COVER_KYOURAN = {
    "id": "G7uwWGXB11s",
    "snippet": {
        "title": "【狂乱な共犯者で】狂乱 Hey Kids!! / THE ORAL CIGARETTES【Cover】【暇72×すち / シクフォニ】",
        "publishedAt": "2026-08-21T10:00:06Z",
        "channelTitle": "シクフォニ【SIXFONIA】",
        "description": """＿＿＿Tonight We honor the hero!!”

××× 毎日更新＿＿＿現在454日目！ ×××

▼本家様
＜ノラガミARAGOTO＞OPテーマ THE ORAL CIGARETTES「狂乱 Hey Kids!!」MusicVideo
https://youtu.be/C-o8pTi6vd8

┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄

運命を掴み取る最強の6人による2.5次元タレントグループ

Color：赤
暇72
https://x.com/hima72_25

◆Instrumental
呉井辰吉(SUPA LOVE)

◆Mix
kokoro no yami　( https://x.com/kny_mix )

◆Illustration
JIGENN　( https://x.com/JIGENN_x_ )

◆Movie
らる　( https://x.com/rc2lx )

※敬称略

┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄


#歌ってみた #狂乱HeyKids #THEORALCIGARETTES #ノラガミ #シクフォニ""",
    },
}

# タイトルに U+200D が2つ入る。◆Lyrics が「クレジット」と「歌詞見出し」で2回出る。
ORIGINAL_SIX_NATION = {
    "id": "U-hMQG9kcqs",
    "snippet": {
        "title": "シクフォニ - SiX N4TioN ‍‍[Official Music Video]",
        "publishedAt": "2026-08-12T11:00:06Z",
        "channelTitle": "シクフォニ【SIXFONIA】",
        "description": """＿＿＿It all depends on you.

××× 毎日更新＿＿＿現在445日目！ ×××

▼Streaming & Download
https://nex-tone.link/A00224492

┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄

運命を掴み取る最強の6人による2.5次元タレントグループ

Color：赤
暇72
https://x.com/hima72_25


◆Music
ケンカイヨシ

◆Lyrics
ケンカイヨシ

◆Arrange
小木岳司

◆Basic Instruments Programming
ケンカイヨシ

◆Mix
藤浪 潤一郎　( https://x.com/2273xxx )

◆Edit
Satori

◆Illustration
すわだ　( https://x.com/suwada_yo )

◆Movie
スンセア　( https://x.com/sunsea2019 )


※敬称略
┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄
◆Lyrics

ジョーカーじゃ足りない!
エースじゃ、まだ満ちない!
その先には......。
(SiX N4TioN)

鼓動の先に観えるパノラマ
決意を知らぬバイアス

(以下、歌詞が100行以上続く)

┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄
◆スケジュール
長尺動画投稿 ▶ 週2　基本毎週火・金曜日
┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄


#SiXN4TioN #シクフォニ #オリジナル曲""",
    },
}

# Original Song Playlist 所属だが ◆Music も ◆Lyrics も無い(メドレー)。
ORIGINAL_MEDLEY = {
    "id": "2wUgZh7B7fc",
    "snippet": {
        "title": "シクフォニ - SIXFONIA \"J to 3rd\" Archive Medley ‍‍[Official Music Video]",
        "publishedAt": "2026-08-10T10:00:06Z",
        "channelTitle": "シクフォニ【SIXFONIA】",
        "description": """＿＿＿どこまでも走れよ 朝も夜も超えて

××× 毎日更新＿＿＿現在443日目！ ×××

運命を掴み取る最強の6人による2.5次元タレントグループ

Color：赤
暇72
https://x.com/hima72_25

◆Instrumental
呉井辰吉(SUPA LOVE)

◆Arrange
呉井辰吉(SUPA LOVE)

◆Mix
赤ティン　( https://twitter.com/akatibitintin )

◆Edit
Satori

◆Illustration
こよせ　( https://x.com/koyose_ )

◆Movie
POhL　( https://x.com/BlurPohl )

※敬称略

#SIXFONIAJto3rdArchiveMedley #歌ってみた #メドレー #シクフォニ #オリジナル曲""",
    },
}

# ◆Lyrics に2人が「 / 」で併記される。◆Movie には URL が無い。
ORIGINAL_T4XI = {
    "id": "sZUSjWvxWXs",
    "snippet": {
        "title": "シクフォニ - T4xi DЯiver ‍‍[Official Music Video]",
        "publishedAt": "2026-06-06T10:00:06Z",
        "channelTitle": "シクフォニ【SIXFONIA】",
        "description": """＿＿＿海で洗浄

××× 毎日更新＿＿＿現在378日目！ ×××

運命を掴み取る最強の6人による2.5次元タレントグループ

Color：赤
暇72
https://x.com/hima72_25


◆Music
ふぁるすてぃ

◆Lyrics
ふぁるすてぃ / 暇72

◆Original Story
暇72

◆Arrange
ふぁるすてぃ

◆Mix
赤ティン　( https://x.com/akatibitintin )

◆Edit
安部良太

◆Illustration
鮫　( https://x.com/aa_832 )

◆Movie
やさね。


※敬称略
┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄
◆Lyrics

とある日の雑談
「──今日変なお客さん乗ってきてね」

(以下、歌詞が続く)

┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄


 #T4xiDЯiver #シクフォニ #オリジナル曲""",
    },
}

# ラベルが「◆Main Animation ＆ IIlustration」(綴り揺れ + 全角＆)で、値が4行にわたる。
ORIGINAL_APRIL_FOOL = {
    "id": "eTWukuLut7c",
    "snippet": {
        "title": "シクフォニ - 今日もボクらは歩いてく ‍‍[Official Music Video]",
        "publishedAt": "2026-04-01T09:00:06Z",
        "channelTitle": "シクフォニ【SIXFONIA】",
        "description": """＿＿＿生きてるだけでOKじゃん

××× 毎日更新＿＿＿現在312日目！ ×××

運命を掴み取る最強の6人による2.5次元タレントグループ

Color：赤
暇72
https://x.com/hima72_25

◆Music
クレハリュウイチ

◆Lyrics
クレハリュウイチ

◆Arrange
クレハリュウイチ

◆Mix
赤ティン　( https://x.com/akatibitintin )

◆Edit
安部良太

◆Main Animation ＆ IIlustration
緒文　( https://x.com/shobo_n023 )
成田無限
重光亮摩 (mico.animation)　( https://mico-animation.co.jp/ )
稗苗 一糸

◆Dance Animation
斜め　( https://x.com/4nanome )

◆Movie
骨付きくぁるび　( https://x.com/SAN_Q_SAN )

◆Cast
27丸(つなまる)　 暇72
ここサメ　　雨乃こさめ

※エイプリルフール企画です。
※敬称略
┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄
◆Lyrics

バタバタバタ uh バタバタバタ yeah
ギリギリギリ oh ギリギリギリ hey

(以下、歌詞が続く)

┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄


#今日もボクらは歩いてく #シクフォニ #オリジナル曲 #エイプリルフール""",
    },
}

COVERS = [COVER_SHOUJO_REI, COVER_KYOURAN]
ORIGINALS = [ORIGINAL_SIX_NATION, ORIGINAL_MEDLEY, ORIGINAL_T4XI, ORIGINAL_APRIL_FOOL]
ALL_SAMPLES = [(v, "cover") for v in COVERS] + [(v, "original") for v in ORIGINALS]
