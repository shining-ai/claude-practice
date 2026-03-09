import type { AlgorithmDefinition, Step, ArrayElement } from '../types';

export const mergeSort: AlgorithmDefinition = {
  id: 'merge-sort',
  categoryId: 'sort',
  name: 'マージソート',
  description: '配列を半分に分割し、再帰的にソートしてマージする分割統治アルゴリズム。',
  timeComplexity: { best: 'O(n log n)', average: 'O(n log n)', worst: 'O(n log n)' },
  spaceComplexity: 'O(n)',
  pseudoCode: [
    'procedure mergeSort(A, l, r):',
    '  if l >= r: return',
    '  mid = (l + r) / 2',
    '  mergeSort(A, l, mid)',
    '  mergeSort(A, mid+1, r)',
    '  merge(A, l, mid, r)',
    '',
    'procedure merge(A, l, mid, r):',
    '  left = A[l..mid], right = A[mid+1..r]',
    '  i = 0, j = 0, k = l',
    '  while i < left.len and j < right.len:',
    '    if left[i] <= right[j]: A[k++] = left[i++]',
    '    else: A[k++] = right[j++]',
    '  copy remaining elements',
  ],
  parameters: [],
  generate: () => (array: number[]) => {
    const steps: Step[] = [];
    const arr = [...array];
    let comparisons = 0;
    let swaps = 0;
    const n = arr.length;

    const snapshot = (
      highlights: { comparing?: number[]; swapping?: number[]; sorted?: number[] },
      line: number,
      description: string
    ): Step => {
      const stateMap: Record<number, ArrayElement['state']> = {};
      highlights.sorted?.forEach((i) => (stateMap[i] = 'sorted'));
      highlights.comparing?.forEach((i) => (stateMap[i] = 'comparing'));
      highlights.swapping?.forEach((i) => (stateMap[i] = 'swapping'));
      return {
        elements: arr.map((value, i) => ({ value, state: stateMap[i] ?? 'default' })),
        pseudoCodeLine: line,
        description,
        stats: { comparisons, swaps },
      };
    };

    const merge = (l: number, mid: number, r: number) => {
      const left = arr.slice(l, mid + 1);
      const right = arr.slice(mid + 1, r + 1);
      let i = 0, j = 0, k = l;

      steps.push(snapshot({ comparing: Array.from({ length: r - l + 1 }, (_, x) => l + x) }, 8, `merge([${l}..${mid}], [${mid + 1}..${r}])`));

      while (i < left.length && j < right.length) {
        comparisons++;
        steps.push(snapshot({ comparing: [l + i, mid + 1 + j] }, 10, `left[${i}]=${left[i]} vs right[${j}]=${right[j]}`));
        if (left[i] <= right[j]) {
          arr[k] = left[i++];
        } else {
          arr[k] = right[j++];
          swaps++;
        }
        steps.push(snapshot({ swapping: [k] }, 11, `A[${k}]=${arr[k]} を配置`));
        k++;
      }
      while (i < left.length) { arr[k++] = left[i++]; }
      while (j < right.length) { arr[k++] = right[j++]; }

      steps.push(snapshot({ sorted: Array.from({ length: r - l + 1 }, (_, x) => l + x) }, 13, `[${l}..${r}] のマージ完了`));
    };

    const sort = (l: number, r: number) => {
      if (l >= r) return;
      const mid = Math.floor((l + r) / 2);
      steps.push(snapshot({ comparing: [l, r] }, 2, `分割: [${l}..${r}] → mid=${mid}`));
      sort(l, mid);
      sort(mid + 1, r);
      merge(l, mid, r);
    };

    sort(0, n - 1);
    steps.push(snapshot({ sorted: Array.from({ length: n }, (_, i) => i) }, 13, 'ソート完了'));
    return steps;
  },
};
