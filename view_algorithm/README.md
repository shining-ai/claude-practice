# Algorithm Visualizer

アルゴリズムの動作をブラウザ上でリアルタイムに可視化する学習用 Web アプリです。

**公開URL:** https://shining-ai.github.io/claude-practice/view_algorithm/

## 機能

- **アルゴリズム選択** — カテゴリ別にアルゴリズムを選択
- **ステップ再生** — 再生 / 一時停止 / 1ステップ前進・後退
- **速度調整** — 0.5x〜10x の5段階
- **パラメータ変更** — 配列サイズ・初期順序・アルゴリズム固有パラメータをリアルタイムに変更
- **統計表示** — 比較回数・スワップ回数・時間/空間計算量
- **疑似コード** — 現在実行中の行をハイライト表示

## 実装済みアルゴリズム

| アルゴリズム | 平均計算量 | 空間計算量 |
|------------|-----------|-----------|
| バブルソート | O(n²) | O(1) |
| 選択ソート | O(n²) | O(1) |
| 挿入ソート | O(n²) | O(1) |
| マージソート | O(n log n) | O(n) |
| クイックソート | O(n log n) | O(log n) |

## セットアップ

```bash
npm install
npm run dev
```

ブラウザで `http://localhost:5173` を開いてください。

## ビルド

```bash
npm run build
```

## 技術スタック

- [React](https://react.dev/) + [TypeScript](https://www.typescriptlang.org/)
- [Vite](https://vite.dev/)
- [Tailwind CSS v4](https://tailwindcss.com/)

## アルゴリズムの追加方法

1. `src/algorithms/<カテゴリ>/` に新しいファイルを作成
2. `AlgorithmDefinition` 型に従って定義を実装
3. `src/algorithms/index.ts` の対応カテゴリに追加

```ts
// src/algorithms/sort/mySort.ts
import type { AlgorithmDefinition } from '../types';

export const mySort: AlgorithmDefinition = {
  id: 'my-sort',
  categoryId: 'sort',
  name: '〇〇ソート',
  description: '説明文',
  timeComplexity: { best: 'O(...)', average: 'O(...)', worst: 'O(...)' },
  spaceComplexity: 'O(...)',
  pseudoCode: ['line 1', 'line 2'],
  parameters: [],
  generate: (params) => (array) => {
    // ステップ配列を返す
  },
};
```

## ディレクトリ構成

```
src/
  algorithms/
    types.ts              # 共通型定義
    index.ts              # カテゴリ・アルゴリズム登録
    sort/                 # ソートアルゴリズム実装
  components/
    AlgorithmSelector.tsx # アルゴリズム選択サイドバー
    ParameterPanel.tsx    # パラメータ設定UI
    Visualizer.tsx        # バーチャート可視化
    Controls.tsx          # 再生コントロール
    PseudoCode.tsx        # 疑似コード表示
    StatsDisplay.tsx      # 統計・計算量表示
  hooks/
    useVisualization.ts   # 再生制御ロジック
```
