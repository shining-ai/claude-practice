import type { AlgorithmCategory } from './types';
import { bubbleSort } from './sort/bubbleSort';
import { selectionSort } from './sort/selectionSort';
import { insertionSort } from './sort/insertionSort';
import { mergeSort } from './sort/mergeSort';
import { quickSort } from './sort/quickSort';

export const algorithmCategories: AlgorithmCategory[] = [
  {
    id: 'sort',
    name: 'ソートアルゴリズム',
    algorithms: [bubbleSort, selectionSort, insertionSort, mergeSort, quickSort],
  },
];

export * from './types';
