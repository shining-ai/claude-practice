import type { AlgorithmCategory, AlgorithmDefinition } from '../algorithms';

interface Props {
  categories: AlgorithmCategory[];
  selectedAlgorithm: AlgorithmDefinition | null;
  onSelect: (algorithm: AlgorithmDefinition) => void;
}

export function AlgorithmSelector({ categories, selectedAlgorithm, onSelect }: Props) {
  return (
    <div className="flex flex-col gap-4">
      {categories.map((category) => (
        <div key={category.id}>
          <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2 px-1">
            {category.name}
          </h3>
          <ul className="flex flex-col gap-1">
            {category.algorithms.map((algo) => {
              const isSelected = selectedAlgorithm?.id === algo.id;
              return (
                <li key={algo.id}>
                  <button
                    onClick={() => onSelect(algo)}
                    className={`w-full text-left px-3 py-2 rounded-lg text-sm transition-colors cursor-pointer ${
                      isSelected
                        ? 'bg-blue-600 text-white font-medium'
                        : 'text-slate-300 hover:bg-slate-700'
                    }`}
                  >
                    {algo.name}
                  </button>
                </li>
              );
            })}
          </ul>
        </div>
      ))}
    </div>
  );
}
