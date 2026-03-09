import type { AlgorithmParameter, ArrayOrder } from '../algorithms';

interface Props {
  parameters: AlgorithmParameter[];
  values: Record<string, number | string | boolean>;
  arraySize: number;
  arrayOrder: ArrayOrder;
  onParamChange: (id: string, value: number | string | boolean) => void;
  onArraySizeChange: (size: number) => void;
  onArrayOrderChange: (order: ArrayOrder) => void;
  onRegenerate: () => void;
  isRunning: boolean;
}

const ORDER_OPTIONS: { label: string; value: ArrayOrder }[] = [
  { label: 'ランダム', value: 'random' },
  { label: '昇順', value: 'ascending' },
  { label: '降順', value: 'descending' },
  { label: 'ほぼ整列', value: 'nearly-sorted' },
];

export function ParameterPanel({
  parameters,
  values,
  arraySize,
  arrayOrder,
  onParamChange,
  onArraySizeChange,
  onArrayOrderChange,
  onRegenerate,
  isRunning,
}: Props) {
  return (
    <div className="flex flex-col gap-4">
      <div>
        <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">
          配列サイズ: {arraySize}
        </label>
        <input
          type="range"
          min={5}
          max={80}
          value={arraySize}
          disabled={isRunning}
          onChange={(e) => onArraySizeChange(Number(e.target.value))}
          className="w-full accent-blue-500 disabled:opacity-50"
        />
      </div>

      <div>
        <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">
          初期配列
        </label>
        <select
          value={arrayOrder}
          disabled={isRunning}
          onChange={(e) => onArrayOrderChange(e.target.value as ArrayOrder)}
          className="w-full bg-slate-700 text-slate-200 text-sm rounded-lg px-3 py-2 border border-slate-600 disabled:opacity-50"
        >
          {ORDER_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>{opt.label}</option>
          ))}
        </select>
      </div>

      {parameters.map((param) => (
        <div key={param.id}>
          <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">
            {param.label}
            {param.type === 'range' && `: ${values[param.id]}`}
          </label>

          {param.type === 'range' && (
            <input
              type="range"
              min={param.min}
              max={param.max}
              step={param.step ?? 1}
              value={values[param.id] as number}
              disabled={isRunning}
              onChange={(e) => onParamChange(param.id, Number(e.target.value))}
              className="w-full accent-blue-500 disabled:opacity-50"
            />
          )}

          {param.type === 'select' && (
            <select
              value={values[param.id] as string}
              disabled={isRunning}
              onChange={(e) => onParamChange(param.id, e.target.value)}
              className="w-full bg-slate-700 text-slate-200 text-sm rounded-lg px-3 py-2 border border-slate-600 disabled:opacity-50"
            >
              {param.options.map((opt) => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
              ))}
            </select>
          )}

          {param.type === 'toggle' && (
            <button
              onClick={() => onParamChange(param.id, !values[param.id])}
              disabled={isRunning}
              className={`px-4 py-1.5 rounded-lg text-sm font-medium transition-colors disabled:opacity-50 ${
                values[param.id] ? 'bg-blue-600 text-white' : 'bg-slate-700 text-slate-300'
              }`}
            >
              {values[param.id] ? 'ON' : 'OFF'}
            </button>
          )}
        </div>
      ))}

      <button
        onClick={onRegenerate}
        disabled={isRunning}
        className="w-full py-2 rounded-lg bg-slate-700 hover:bg-slate-600 text-slate-200 text-sm font-medium transition-colors disabled:opacity-50 cursor-pointer"
      >
        配列を再生成
      </button>
    </div>
  );
}
