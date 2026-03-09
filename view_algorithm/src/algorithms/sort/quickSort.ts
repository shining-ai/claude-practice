import type { AlgorithmDefinition, Step, ArrayElement } from '../types';

export const quickSort: AlgorithmDefinition = {
  id: 'quick-sort',
  categoryId: 'sort',
  name: 'クイックソート',
  description: 'ピボットを基準に要素を分割し、再帰的にソートする分割統治アルゴリズム。',
  timeComplexity: { best: 'O(n log n)', average: 'O(n log n)', worst: 'O(n²)' },
  spaceComplexity: 'O(log n)',
  pseudoCode: [
    'procedure quickSort(A, lo, hi):',
    '  if lo < hi:',
    '    p = partition(A, lo, hi)',
    '    quickSort(A, lo, p-1)',
    '    quickSort(A, p+1, hi)',
    '',
    'procedure partition(A, lo, hi):',
    '  pivot = A[hi]',
    '  i = lo - 1',
    '  for j = lo to hi-1:',
    '    if A[j] <= pivot:',
    '      i++; swap(A[i], A[j])',
    '  swap(A[i+1], A[hi])',
    '  return i + 1',
  ],
  parameters: [
    {
      id: 'pivotStrategy',
      label: 'ピボット選択',
      type: 'select',
      defaultValue: 'last',
      options: [
        { label: '末尾要素', value: 'last' },
        { label: '先頭要素', value: 'first' },
        { label: 'ランダム', value: 'random' },
        { label: '中央値', value: 'median' },
      ],
    },
  ],
  generate: (params) => (array: number[]) => {
    const steps: Step[] = [];
    const arr = [...array];
    let comparisons = 0;
    let swaps = 0;
    const n = arr.length;
    const sortedSet = new Set<number>();

    const snapshot = (
      highlights: { pivot?: number; comparing?: number[]; swapping?: number[] },
      line: number,
      description: string
    ): Step => {
      const stateMap: Record<number, ArrayElement['state']> = {};
      sortedSet.forEach((i) => (stateMap[i] = 'sorted'));
      highlights.comparing?.forEach((i) => (stateMap[i] = 'comparing'));
      highlights.swapping?.forEach((i) => (stateMap[i] = 'swapping'));
      if (highlights.pivot !== undefined) stateMap[highlights.pivot] = 'pivot';
      return {
        elements: arr.map((value, i) => ({ value, state: stateMap[i] ?? 'default' })),
        pseudoCodeLine: line,
        description,
        stats: { comparisons, swaps },
      };
    };

    const getPivotIndex = (lo: number, hi: number): number => {
      const strategy = params.pivotStrategy as string;
      if (strategy === 'first') return lo;
      if (strategy === 'random') return lo + Math.floor(Math.random() * (hi - lo + 1));
      if (strategy === 'median') {
        const mid = Math.floor((lo + hi) / 2);
        const candidates = [[arr[lo], lo], [arr[mid], mid], [arr[hi], hi]] as [number, number][];
        candidates.sort((a, b) => a[0] - b[0]);
        return candidates[1][1];
      }
      return hi;
    };

    const partition = (lo: number, hi: number): number => {
      const pivotIdx = getPivotIndex(lo, hi);
      if (pivotIdx !== hi) {
        [arr[pivotIdx], arr[hi]] = [arr[hi], arr[pivotIdx]];
        swaps++;
      }
      const pivot = arr[hi];
      steps.push(snapshot({ pivot: hi }, 7, `pivot = A[${hi}] = ${pivot}`));
      let i = lo - 1;

      for (let j = lo; j < hi; j++) {
        comparisons++;
        steps.push(snapshot({ pivot: hi, comparing: [j] }, 10, `A[${j}]=${arr[j]} と pivot=${pivot} を比較`));

        if (arr[j] <= pivot) {
          i++;
          if (i !== j) {
            steps.push(snapshot({ pivot: hi, swapping: [i, j] }, 11, `A[${i}] と A[${j}] をスワップ`));
            [arr[i], arr[j]] = [arr[j], arr[i]];
            swaps++;
          }
        }
      }

      const pivotFinal = i + 1;
      steps.push(snapshot({ pivot: pivotFinal, swapping: [pivotFinal, hi] }, 12, `pivot を位置 ${pivotFinal} に配置`));
      [arr[pivotFinal], arr[hi]] = [arr[hi], arr[pivotFinal]];
      swaps++;
      sortedSet.add(pivotFinal);
      steps.push(snapshot({}, 12, `位置 ${pivotFinal} が確定`));
      return pivotFinal;
    };

    const sort = (lo: number, hi: number) => {
      if (lo >= hi) {
        if (lo === hi) sortedSet.add(lo);
        return;
      }
      steps.push(snapshot({}, 1, `quickSort([${lo}..${hi}])`));
      const p = partition(lo, hi);
      sort(lo, p - 1);
      sort(p + 1, hi);
    };

    sort(0, n - 1);
    Array.from({ length: n }, (_, i) => i).forEach((i) => sortedSet.add(i));
    steps.push(snapshot({}, 13, 'ソート完了'));
    return steps;
  },
};
