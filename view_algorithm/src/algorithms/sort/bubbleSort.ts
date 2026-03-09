import type { AlgorithmDefinition, Step, ArrayElement } from '../types';

export const bubbleSort: AlgorithmDefinition = {
  id: 'bubble-sort',
  categoryId: 'sort',
  name: 'バブルソート',
  description: '隣接する要素を比較・交換しながら最大値を末尾へ移動させることを繰り返すアルゴリズム。',
  timeComplexity: { best: 'O(n)', average: 'O(n²)', worst: 'O(n²)' },
  spaceComplexity: 'O(1)',
  pseudoCode: [
    'procedure bubbleSort(A):',
    '  for i = 0 to n-1:',
    '    swapped = false',
    '    for j = 0 to n-i-2:',
    '      if A[j] > A[j+1]:',
    '        swap(A[j], A[j+1])',
    '        swapped = true',
    '    if not swapped: break',
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
      let swapped = false;
      steps.push(snapshot({ ...Object.fromEntries(Array.from({ length: i }, (_, k) => [n - 1 - k, 'sorted' as const])) }, 1, `外側ループ i=${i}`));

      for (let j = 0; j < n - i - 1; j++) {
        const sortedStates = Object.fromEntries(Array.from({ length: i }, (_, k) => [n - 1 - k, 'sorted' as const]));
        steps.push(snapshot({ ...sortedStates, [j]: 'comparing', [j + 1]: 'comparing' }, 4, `A[${j}]=${arr[j]} と A[${j + 1}]=${arr[j + 1]} を比較`));
        comparisons++;

        if (arr[j] > arr[j + 1]) {
          steps.push(snapshot({ ...sortedStates, [j]: 'swapping', [j + 1]: 'swapping' }, 5, `A[${j}] > A[${j + 1}] なのでスワップ`));
          [arr[j], arr[j + 1]] = [arr[j + 1], arr[j]];
          swaps++;
          swapped = true;
        }
      }

      const newSortedStates = Object.fromEntries(Array.from({ length: i + 1 }, (_, k) => [n - 1 - k, 'sorted' as const]));
      steps.push(snapshot(newSortedStates, 6, `位置 ${n - 1 - i} が確定`));

      if (!swapped) {
        steps.push(snapshot(Object.fromEntries(arr.map((_, k) => [k, 'sorted' as const])), 7, 'スワップなし → ソート完了'));
        break;
      }
    }

    return steps;
  },
};
