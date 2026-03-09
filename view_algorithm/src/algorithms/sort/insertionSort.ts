import type { AlgorithmDefinition, Step, ArrayElement } from '../types';

export const insertionSort: AlgorithmDefinition = {
  id: 'insertion-sort',
  categoryId: 'sort',
  name: '挿入ソート',
  description: '未ソート部分の先頭要素をソート済み部分の適切な位置に挿入することを繰り返すアルゴリズム。',
  timeComplexity: { best: 'O(n)', average: 'O(n²)', worst: 'O(n²)' },
  spaceComplexity: 'O(1)',
  pseudoCode: [
    'procedure insertionSort(A):',
    '  for i = 1 to n-1:',
    '    key = A[i]',
    '    j = i - 1',
    '    while j >= 0 and A[j] > key:',
    '      A[j+1] = A[j]',
    '      j = j - 1',
    '    A[j+1] = key',
    '  return A',
  ],
  parameters: [],
  generate: () => (array: number[]) => {
    const steps: Step[] = [];
    const arr = [...array];
    let comparisons = 0;
    let swaps = 0;
    const n = arr.length;

    const snapshot = (states: Record<number, ArrayElement['state']>, line: number, description: string): Step => ({
      elements: arr.map((value, i) => ({ value, state: states[i] ?? 'default' })),
      pseudoCodeLine: line,
      description,
      stats: { comparisons, swaps },
    });

    steps.push(snapshot({ 0: 'sorted' }, 0, '初期状態: A[0] はソート済み'));

    for (let i = 1; i < n; i++) {
      const key = arr[i];
      let j = i - 1;
      const sortedBase = Object.fromEntries(Array.from({ length: i }, (_, k) => [k, 'sorted' as const]));
      steps.push(snapshot({ ...sortedBase, [i]: 'comparing' }, 2, `key = A[${i}] = ${key} を挿入`));

      while (j >= 0 && arr[j] > key) {
        comparisons++;
        steps.push(snapshot({ ...sortedBase, [j]: 'comparing', [j + 1]: 'swapping' }, 4, `A[${j}]=${arr[j]} > key=${key} → 右にシフト`));
        arr[j + 1] = arr[j];
        swaps++;
        j--;
      }
      if (j >= 0) comparisons++;

      arr[j + 1] = key;
      const newSortedStates = Object.fromEntries(Array.from({ length: i + 1 }, (_, k) => [k, 'sorted' as const]));
      steps.push(snapshot(newSortedStates, 7, `key=${key} を位置 ${j + 1} に挿入`));
    }

    return steps;
  },
};
