export type ParameterType = 'range' | 'select' | 'toggle';

export interface RangeParameter {
  id: string;
  label: string;
  type: 'range';
  defaultValue: number;
  min: number;
  max: number;
  step?: number;
}

export interface SelectParameter {
  id: string;
  label: string;
  type: 'select';
  defaultValue: string;
  options: { label: string; value: string }[];
}

export interface ToggleParameter {
  id: string;
  label: string;
  type: 'toggle';
  defaultValue: boolean;
}

export type AlgorithmParameter = RangeParameter | SelectParameter | ToggleParameter;

export type ElementState = 'default' | 'comparing' | 'swapping' | 'sorted' | 'pivot';

export interface ArrayElement {
  value: number;
  state: ElementState;
}

export interface Step {
  elements: ArrayElement[];
  pseudoCodeLine: number;
  description: string;
  stats: {
    comparisons: number;
    swaps: number;
  };
}

export interface AlgorithmDefinition {
  id: string;
  categoryId: string;
  name: string;
  description: string;
  timeComplexity: { best: string; average: string; worst: string };
  spaceComplexity: string;
  pseudoCode: string[];
  parameters: AlgorithmParameter[];
  generate: (params: Record<string, number | string | boolean>) => (array: number[]) => Step[];
}

export interface AlgorithmCategory {
  id: string;
  name: string;
  algorithms: AlgorithmDefinition[];
}

export type ArrayOrder = 'random' | 'ascending' | 'descending' | 'nearly-sorted';

export function generateArray(size: number, order: ArrayOrder): number[] {
  const arr = Array.from({ length: size }, (_, i) => i + 1);

  // shuffle
  for (let i = arr.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [arr[i], arr[j]] = [arr[j], arr[i]];
  }

  if (order === 'ascending') return arr.sort((a, b) => a - b);
  if (order === 'descending') return arr.sort((a, b) => b - a);
  if (order === 'nearly-sorted') {
    const sorted = arr.sort((a, b) => a - b);
    const swapCount = Math.max(1, Math.floor(size * 0.1));
    for (let i = 0; i < swapCount; i++) {
      const a = Math.floor(Math.random() * size);
      const b = Math.floor(Math.random() * size);
      [sorted[a], sorted[b]] = [sorted[b], sorted[a]];
    }
    return sorted;
  }
  return arr;
}
