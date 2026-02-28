# React TODO App

React + TypeScript + Vite で構築したTODOアプリです。

## 機能

- タスクの追加・編集・削除
- タスクの完了/未完了の切り替え
- 優先度設定（低・中・高）
- カテゴリ設定
- 期日設定
- フィルタリング（優先度・カテゴリ・完了状態）
- ソート（期日・優先度・作成日・タイトル）
- データのローカルストレージへの自動保存

## 技術スタック

- **React** 18
- **TypeScript** 5
- **Vite** 5
- CSS Modules

## セットアップ

```bash
npm install
```

## 開発サーバーの起動

```bash
npm run dev
```

ブラウザで http://localhost:5173 を開きます。

## ビルド

```bash
npm run build
```

## ディレクトリ構成

```
src/
├── components/     # UIコンポーネント
│   ├── TodoApp     # メインコンポーネント
│   ├── TodoForm    # タスク追加フォーム
│   ├── TodoList    # タスク一覧
│   ├── TodoItem    # 個々のタスク
│   └── TodoFilters # フィルター・ソート
├── hooks/
│   └── useTodos.ts # タスク管理カスタムフック
├── types/
│   └── todo.ts     # 型定義
├── utils/
│   └── storage.ts  # ローカルストレージ操作
└── styles/         # グローバルスタイル
```
