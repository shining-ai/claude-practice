import type { ArrayElement } from '../algorithms';

interface Props {
  elements: ArrayElement[];
}

const STATE_COLORS: Record<ArrayElement['state'], string> = {
  default: 'bg-slate-500',
  comparing: 'bg-yellow-400',
  swapping: 'bg-red-500',
  sorted: 'bg-green-500',
  pivot: 'bg-purple-500',
};

export function Visualizer({ elements }: Props) {
  const maxValue = Math.max(...elements.map((e) => e.value), 1);

  return (
    <div className="w-full h-64 flex items-end gap-0.5 px-2">
      {elements.map((el, i) => {
        const heightPercent = (el.value / maxValue) * 100;
        return (
          <div
            key={i}
            className="flex-1 flex flex-col items-center justify-end min-w-0"
            style={{ height: '100%' }}
          >
            <div
              className={`w-full rounded-t transition-all duration-100 flex items-center justify-center overflow-hidden ${STATE_COLORS[el.state]}`}
              style={{ height: `${heightPercent}%` }}
            >
              <span className="text-white font-bold select-none leading-none text-xs">
                {el.value}
              </span>
            </div>
          </div>
        );
      })}
    </div>
  );
}
