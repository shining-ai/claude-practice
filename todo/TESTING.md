# テスト仕様書

React TODO アプリのテストコード一覧です。
テストフレームワーク: **Vitest** + **@testing-library/react**

## テスト実行

```bash
npm test           # 全テストを1回実行
npm run test:watch # ウォッチモード（ファイル変更時に自動再実行）
npm run test:ui    # ブラウザUIで結果確認
```

---

## テスト一覧

### 合計: 51 テスト（6 ファイル）

---

## `src/utils/storage.test.ts` — ローカルストレージ操作（9件）

| # | テスト名 | 概要 |
|---|---|---|
| 1 | `loadTodos` › returns empty array when localStorage is empty | localStorage が空のとき `[]` を返す |
| 2 | `loadTodos` › returns stored todos | 保存済みの todos を正しく取得できる |
| 3 | `loadTodos` › returns multiple stored todos in order | 複数件の todos を順序を保って取得できる |
| 4 | `loadTodos` › returns empty array when localStorage contains invalid JSON | 不正な JSON の場合は `[]` を返してクラッシュしない |
| 5 | `saveTodos` › saves todos to localStorage as JSON | todos を JSON 形式で localStorage に保存する |
| 6 | `saveTodos` › saves empty array | 空配列も正しく保存できる |
| 7 | `saveTodos` › overwrites previously saved todos | 既存データを新しいデータで上書きする |
| 8 | `clearTodos` › removes todos from localStorage | localStorage から todos を削除する |
| 9 | `clearTodos` › does not throw when localStorage is already empty | localStorage が空の状態でエラーにならない |

---

## `src/hooks/useTodos.test.ts` — TODO 管理カスタムフック（9件）

| # | テスト名 | 概要 |
|---|---|---|
| 1 | initializes with empty todos and isLoading false | 初期状態は空配列・isLoading が false |
| 2 | loads todos from localStorage on mount | マウント時に localStorage から todos を読み込む |
| 3 | addTodo creates a todo with all specified fields | 指定した全フィールド（title・description・priority・category・dueDate）を持つ todo を作成する |
| 4 | addTodo accepts null dueDate | dueDate に null を渡せる |
| 5 | deleteTodo removes only the specified todo | 指定した ID の todo だけを削除する |
| 6 | toggleComplete flips completed from false to true and back | 完了状態を true/false で反転できる |
| 7 | updateTodo updates only specified fields and leaves others unchanged | 指定フィールドのみ更新し、他フィールドは変更しない |
| 8 | persists added todos to localStorage | todo 追加後に localStorage へ自動保存される |
| 9 | persists deletion to localStorage | todo 削除後に localStorage へ自動反映される |

---

## `src/components/TodoForm.test.tsx` — タスク追加フォーム（7件）

| # | テスト名 | 概要 |
|---|---|---|
| 1 | renders all form fields and submit button | タイトル・説明・優先度・カテゴリ・期日の全入力欄と送信ボタンが表示される |
| 2 | calls onAddTodo with all entered values on submission | 入力した値が正しく `onAddTodo` に渡される |
| 3 | does not call onAddTodo when title is empty | タイトルが空のとき送信されない |
| 4 | does not call onAddTodo when title is only whitespace | タイトルが空白のみのとき送信されない |
| 5 | resets all fields to defaults after successful submission | 送信後にフォームが初期値にリセットされる |
| 6 | uses "General" as category when category field is left empty | カテゴリ未入力時はデフォルト値 `"General"` が渡される |
| 7 | passes null for dueDate when due date field is left empty | 期日未入力時は `null` が渡される |

---

## `src/components/TodoItem.test.tsx` — 個別 TODO アイテム（15件）

### 表示

| # | テスト名 | 概要 |
|---|---|---|
| 1 | renders title, description, priority, and category | タイトル・説明・優先度・カテゴリが表示される |
| 2 | does not render description when it is empty | 説明が空のとき説明欄を表示しない |
| 3 | renders due date when provided | 期日が設定されているとき表示される |
| 4 | does not render due date when dueDate is null | 期日が null のとき表示されない |

### 完了チェックボックス

| # | テスト名 | 概要 |
|---|---|---|
| 5 | calls onToggleComplete with the todo id when checkbox is clicked | チェックボックスクリックで `onToggleComplete` が todo ID と共に呼ばれる |
| 6 | shows checkbox as checked for completed todo | 完了済み todo のチェックボックスはチェック状態になる |
| 7 | shows checkbox as unchecked for incomplete todo | 未完了 todo のチェックボックスはチェックなし状態になる |

### 編集

| # | テスト名 | 概要 |
|---|---|---|
| 8 | switches to edit mode when edit button is clicked | 編集ボタンクリックで編集フォームに切り替わる |
| 9 | calls onUpdate with edited title and description when Save is clicked | 変更後に Save をクリックすると `onUpdate` が新しい値と共に呼ばれる |
| 10 | does not call onUpdate when Save is clicked with empty title | タイトルを空にして Save しても `onUpdate` は呼ばれない |
| 11 | restores original values and exits edit mode when Cancel is clicked | Cancel クリックで元の値に戻り編集モードを終了する |

### 削除

| # | テスト名 | 概要 |
|---|---|---|
| 12 | calls onDelete when delete is confirmed | 削除確認ダイアログで OK を選択すると `onDelete` が呼ばれる |
| 13 | does not call onDelete when delete is cancelled | 削除確認ダイアログでキャンセルすると `onDelete` は呼ばれない |

### 期限切れ表示

| # | テスト名 | 概要 |
|---|---|---|
| 14 | applies overdue class for incomplete todo with past due date | 期限切れ（過去日付）かつ未完了の todo に `overdue` クラスが適用される |
| 15 | does not apply overdue class for completed todo with past due date | 期限切れでも完了済みの todo には `overdue` クラスが適用されない |

---

## `src/components/TodoList.test.tsx` — TODO リスト（3件）

| # | テスト名 | 概要 |
|---|---|---|
| 1 | shows empty state message when there are no todos | todos が空のとき「No TODOs yet」メッセージを表示する |
| 2 | renders each todo in the list | todos の各アイテムがリストに表示される |
| 3 | does not show empty state message when there are todos | todos がある場合は空メッセージを表示しない |

---

## `src/components/TodoFilters.test.tsx` — フィルター・ソート操作（8件）

| # | テスト名 | 概要 |
|---|---|---|
| 1 | renders priority filter with all options | 優先度フィルターに All / Low / Medium / High の選択肢が表示される |
| 2 | calls onFilterChange with selected priority | 優先度を選択すると `onFilterChange` が正しい値と共に呼ばれる |
| 3 | renders category filter with categories from todos | todos のカテゴリ一覧がカテゴリフィルターに表示される |
| 4 | calls onFilterChange with selected category | カテゴリを選択すると `onFilterChange` が正しい値と共に呼ばれる |
| 5 | calls onSortChange when sort option is changed | ソート変更で `onSortChange` が呼ばれる |
| 6 | calls onFilterChange when Completed checkbox is toggled | Completed チェックボックスのトグルで `onFilterChange` が呼ばれる |
| 7 | calls onFilterChange when Incomplete checkbox is toggled | Incomplete チェックボックスのトグルで `onFilterChange` が呼ばれる |
| 8 | resets all filters and sort to defaults when Clear Filters is clicked | Clear Filters クリックで全フィルターとソートが初期値にリセットされる |
