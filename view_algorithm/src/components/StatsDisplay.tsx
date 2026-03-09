import type { AlgorithmDefinition } from '../algorithms';

interface Props {
  algorithm: AlgorithmDefinition;
  comparisons: number;
  swaps: number;
  description: string;
}

export function StatsDisplay({ algorithm, comparisons, swaps, description }: Props) {
  return (
    <div className="flex flex-col gap-3">
      <div className="grid grid-cols-2 gap-2">
        <div className="bg-slate-800 rounded-lg p-3 text-center">
          <div className="text-2xl font-bold text-yellow-400">{comparisons}</div>
          <div className="text-xs text-slate-400 mt-1">比較回数</div>
        </div>
        <div className="bg-slate-800 rounded-lg p-3 text-center">
          <div className="text-2xl font-bold text-red-400">{swaps}</div>
          <div className="text-xs text-slate-400 mt-1">スワップ回数</div>
        </div>
      </div>

      <div className="bg-slate-800 rounded-lg p-3">
        <div className="text-xs text-slate-400 mb-2 font-semibold uppercase tracking-wider">計算量</div>
        <div className="grid grid-cols-3 gap-2 text-xs text-center">
          <div>
            <div className="text-slate-400">Best</div>
            <div className="text-green-400 font-mono font-medium">{algorithm.timeComplexity.best}</div>
          </div>
          <div>
            <div className="text-slate-400">Avg</div>
            <div className="text-yellow-400 font-mono font-medium">{algorithm.timeComplexity.average}</div>
          </div>
          <div>
            <div className="text-slate-400">Worst</div>
            <div className="text-red-400 font-mono font-medium">{algorithm.timeComplexity.worst}</div>
          </div>
        </div>
        <div className="mt-2 text-center text-xs">
          <span className="text-slate-400">空間: </span>
          <span className="text-blue-400 font-mono font-medium">{algorithm.spaceComplexity}</span>
        </div>
      </div>

      {description && (
        <div className="bg-slate-800 rounded-lg px-3 py-2 text-sm text-slate-300 min-h-8">
          {description}
        </div>
      )}
    </div>
  );
}
