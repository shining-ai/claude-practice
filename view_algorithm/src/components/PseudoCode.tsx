interface Props {
  lines: string[];
  currentLine: number;
}

export function PseudoCode({ lines, currentLine }: Props) {
  return (
    <div className="font-mono text-sm bg-slate-950 rounded-lg p-4 overflow-auto max-h-60">
      {lines.map((line, i) => (
        <div
          key={i}
          className={`px-2 py-0.5 rounded transition-colors ${
            i === currentLine
              ? 'bg-yellow-500/20 text-yellow-300'
              : 'text-slate-400'
          }`}
        >
          <span className="select-none text-slate-600 mr-3 text-xs">{i + 1}</span>
          <span style={{ whiteSpace: 'pre' }}>{line || ' '}</span>
        </div>
      ))}
    </div>
  );
}
