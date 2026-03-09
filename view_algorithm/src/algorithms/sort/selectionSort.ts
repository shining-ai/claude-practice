import type { AlgorithmDefinition, Step, ArrayElement } from '../types';

export const selectionSort: AlgorithmDefinition = {
  id: 'selection-sort',
  categoryId: 'sort',
  name: '選択ソート',
  description: '未ソート部分から最小値を選択し、先頭と交換することを繰り返すアルゴリズム。',
  timeComplexity: { best: 'O(n²)', average: 'O(n²)', worst: 'O(n²)' },
  spaceComplexity: 'O(1)',
  pseudoCode: [
    'procedure selectionSort(A):',
    '  for i = 0 to n-1:',
    '    minIdx = i',
    '    for j = i+1 to n-1:',
    '      if A[j] < A[minIdx]:',
    '        minIdx = j',
    '    if minIdx != i:',
    '      swap(A[i], A[minIdx])',
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

    for (let i = 0; i < n; i++) {
      const sortedStates = Object.fromEntries(Array.from({ length: i }, (_, k) => [k, 'sorted' as const]));
      let minIdx = i;
      steps.push(snapshot({ ...sortedStates, [i]: 'pivot' }, 2, `i=${i}: 最小値探索開始`));

      for (let j = i + 1; j < n; j++) {
        steps.push(snapshot({ ...sortedStates, [minIdx]: 'pivot', [j]: 'comparing' }, 4, `A[${j}]=${arr[j]} と 現在の最小値 A[${minIdx}]=${arr[minIdx]} を比較`));
        comparisons++;

        if (arr[j] < arr[minIdx]) {
          minIdx = j;
          steps.push(snapshot({ ...sortedStates, [minIdx]: 'pivot' }, 5, `最小値を更新: A[${minIdx}]=${arr[minIdx]}`));
        }
      }

      if (minIdx !== i) {
        steps.push(snapshot({ ...sortedStates, [i]: 'swapping', [minIdx]: 'swapping' }, 7, `A[${i}] と A[${minIdx}] をスワップ`));
        [arr[i], arr[minIdx]] = [arr[minIdx], arr[i]];
        swaps++;
      }

      const newSortedStates = Object.fromEntries(Array.from({ length: i + 1 }, (_, k) => [k, 'sorted' as const]));
      steps.push(snapshot(newSortedStates, 8, `位置 ${i} が確定`));
    }

    return steps;
  },
};
