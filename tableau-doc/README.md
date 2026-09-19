# tableau-doc / twbdoc

Tableauの `.twb` ファイルから **Markdown仕様書・定義書** と **単一HTMLビューア** を生成するツール。

目的は「Tableauに依存せず、工数をかけずにレポートを出す」こと。twbはXMLなので、
Tableau Desktopが無くても内容を構造化して取り出せる。

## 現状（Phase A）

このツールが対応しているのは以下:

- **Markdown仕様書・定義書の生成** — データソース／計算フィールド／ワークシート／
  ダッシュボード／アクション／パラメータ／フィールド依存関係（リネージ）
- **単一HTMLビューアの生成** — 外部CDNに依存しない自己完結HTMLファイル1本。
  左ナビ・全文検索・計算式の依存ジャンプ・ダッシュボードのゾーン配置ワイヤーフレーム表示

DB接続して実データでグラフを描く「分析レポート」(Phase B) は未実装。まずはこのPhase Aで
実際のtwbファイルに対して動かしてみて、認識できなかった要素がないか確認してから着手する。

## 使い方

```bash
cd tableau-doc

# Markdown仕様書・定義書を生成（既定の出力先は docs/）
python3 -m twbdoc.cli doc workbook.twb -o docs/

# 単一HTMLビューアを生成（既定の出力先は spec.html）
python3 -m twbdoc.cli viewer workbook.twb -o spec.html
```

標準ライブラリのみで動作する（Python 3.10+）。追加のインストールは不要。

### 接続情報のマスク

`doc`/`viewer` いずれも、**既定でサーバー名・DB名・ポート・カスタムSQL本文をマスクする**。
twbファイル自体をコミットしない運用と同じ理由で、生成した仕様書にも接続先の機微情報を
そのまま載せないための挙動。表示したい場合は明示的に解除する:

```bash
python3 -m twbdoc.cli doc workbook.twb -o docs/ --show-connections
```

## パース方針: 防御的・自己申告型

実務で使われるtwbは古いバージョン（2019〜2024年台など）が多く、要素構成は版によって
揺れる。このツールは **未知の要素に遭遇しても例外を投げず、認識できなかった要素を
「未対応要素」として結果に列挙する** 設計にしている。

- Markdown: `docs/<workbook名>/README.md` の「未対応要素」節
- HTMLビューア: 「概要」タブ

未対応要素が出た場合は、内容の欠落がないか元のtwbファイルを直接確認してほしい。
（Issueなどで報告してもらえれば、パーサの対応を広げられる）

## 検証状況

`samples/synthetic.twb` は実twbファイルの代わりに手書きした検証用サンプル
（twbファイル自体はコミットしない方針のため）。2データソース・計算フィールド6種
（単純集計/ネスト/LOD式/表計算/コメント付き/文字列リテラルに紛らわしい角括弧を含むもの）・
パラメータ2種・グループ/ビン/フォルダ・ワークシート4枚・ダッシュボード2枚（ゾーン入れ子）・
アクション3種・意図的な未知要素3箇所を網羅している。

公式XSD（[tableau/tableau-document-schemas](https://github.com/tableau/tableau-document-schemas)、
`twb_2026.1.0.xsd`）に対して実際に検証し、判明した構造上の誤りは修正済み
（ビン計算式の表現、フォルダの入れ子位置、ソート要素の実際の名前、
`<view>`直下の必須要素、`selection-relaxation-option`の列挙値など）。

**既知の未解決ギャップ:** `<actions>` 内の `<source>`/`<target>`/`<filter>` 構造と
`activation` の表現は、本サンプルでは実務でよく見る2019〜2023年台のTableau出力形式
（source/target/filterのネスト構造、activation属性）を踏襲しており、2026.1スキーマが
定めるより新しい表現（`<activation>`要素化、`<command>`/`<param>`による汎用表現）とは
一致しない。新方式の実例を手元で確認できないため、確度の低い当てずっぽうで書き換えるより
広く見られる旧方式を残す判断とした。`parse.py`のアクション解析はこの旧方式を前提にしている。

つまり **本ツールはtwbの全バージョン・全要素を完全網羅する保証はない**。
未対応要素の自己申告機構はこの前提の上での安全弁として設計している。

## 実行方法（開発）

```bash
cd tableau-doc
python3 -m pytest tests/ -v
```

## ディレクトリ構成

```
tableau-doc/
  twbdoc/
    fieldref.py     # [ds].[sum:Field:qk] 形式のフィールド参照デコード
    model.py        # 内部表現(IR)のdataclass群
    parse.py        # twb XML → IR。未知要素は例外にせず収集
    calc.py         # 計算式の依存フィールド抽出・LOD/表計算の検出
    mask.py         # 接続情報のマスク処理
    render_md.py    # IR → Markdown仕様書
    render_html.py  # IR → 単一HTMLビューア
    cli.py          # doc / viewer サブコマンド
  samples/
    synthetic.twb   # 検証用の手書きサンプル
  tests/
```

## 未実装（Phase B）

DB直結で実データを取得し、Vega-Liteでグラフを描画する分析レポート機能
（`report.html`）は未着手。twbのシート定義からSQLを組み立て、LOD式・表計算を含む
シートは「変換不能としてスキップ」報告する設計を予定している。
