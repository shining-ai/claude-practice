interface Props {
  isPlaying: boolean;
  isFinished: boolean;
  currentStep: number;
  totalSteps: number;
  speed: number;
  onPlay: () => void;
  onPause: () => void;
  onReset: () => void;
  onStepForward: () => void;
  onStepBack: () => void;
  onSpeedChange: (speed: number) => void;
}

const SPEED_OPTIONS = [
  { label: '0.5x', value: 0.5 },
  { label: '1x', value: 1 },
  { label: '2x', value: 2 },
  { label: '5x', value: 5 },
  { label: '10x', value: 10 },
];

export function Controls({
  isPlaying,
  isFinished,
  currentStep,
  totalSteps,
  speed,
  onPlay,
  onPause,
  onReset,
  onStepForward,
  onStepBack,
  onSpeedChange,
}: Props) {
  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center gap-2 justify-center">
        <button
          onClick={onReset}
          className="px-3 py-2 rounded-lg bg-slate-700 hover:bg-slate-600 text-slate-200 text-sm font-medium transition-colors cursor-pointer"
          title="リセット"
        >
          ↩ リセット
        </button>
        <button
          onClick={onStepBack}
          disabled={currentStep === 0}
          className="px-3 py-2 rounded-lg bg-slate-700 hover:bg-slate-600 text-slate-200 text-sm font-medium transition-colors disabled:opacity-40 cursor-pointer"
          title="1ステップ戻る"
        >
          ◀◀
        </button>
        <button
          onClick={isPlaying ? onPause : onPlay}
          disabled={isFinished && !isPlaying}
          className={`px-6 py-2 rounded-lg text-white text-sm font-semibold transition-colors cursor-pointer ${
            isPlaying
              ? 'bg-yellow-500 hover:bg-yellow-400'
              : 'bg-blue-600 hover:bg-blue-500 disabled:opacity-40'
          }`}
        >
          {isPlaying ? '⏸ 一時停止' : isFinished ? '完了' : '▶ 再生'}
        </button>
        <button
          onClick={onStepForward}
          disabled={isFinished}
          className="px-3 py-2 rounded-lg bg-slate-700 hover:bg-slate-600 text-slate-200 text-sm font-medium transition-colors disabled:opacity-40 cursor-pointer"
          title="1ステップ進む"
        >
          ▶▶
        </button>
      </div>

      <div className="flex items-center gap-3">
        <span className="text-xs text-slate-400 whitespace-nowrap">
          {currentStep} / {totalSteps}
        </span>
        <input
          type="range"
          min={0}
          max={totalSteps}
          value={currentStep}
          onChange={() => {}}
          className="flex-1 accent-blue-500"
          readOnly
        />
        <div className="flex gap-1">
          {SPEED_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              onClick={() => onSpeedChange(opt.value)}
              className={`px-2 py-1 rounded text-xs font-medium transition-colors cursor-pointer ${
                speed === opt.value
                  ? 'bg-blue-600 text-white'
                  : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
              }`}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
