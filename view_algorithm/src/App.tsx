import { useState } from 'react';
import { algorithmCategories } from './algorithms';
import type { AlgorithmDefinition } from './algorithms';
import { AlgorithmSelector } from './components/AlgorithmSelector';
import { ParameterPanel } from './components/ParameterPanel';
import { Visualizer } from './components/Visualizer';
import { Controls } from './components/Controls';
import { PseudoCode } from './components/PseudoCode';
import { StatsDisplay } from './components/StatsDisplay';
import { useVisualization } from './hooks/useVisualization';

export default function App() {
  const [selectedAlgorithm, setSelectedAlgorithm] = useState<AlgorithmDefinition | null>(
    algorithmCategories[0]?.algorithms[0] ?? null
  );
  const { state, actions } = useVisualization(selectedAlgorithm);

  return (
    <div className="min-h-screen bg-slate-900 text-slate-100 flex flex-col">
      {/* Header */}
      <header className="border-b border-slate-700 px-6 py-3 flex items-center gap-3">
        <h1 className="text-lg font-bold text-white">Algorithm Visualizer</h1>
        {selectedAlgorithm && (
          <span className="text-slate-400 text-sm">/ {selectedAlgorithm.name}</span>
        )}
      </header>

      <div className="flex flex-1 overflow-hidden">
        {/* Left sidebar */}
        <aside className="w-52 shrink-0 border-r border-slate-700 p-4 overflow-y-auto flex flex-col gap-6">
          <AlgorithmSelector
            categories={algorithmCategories}
            selectedAlgorithm={selectedAlgorithm}
            onSelect={setSelectedAlgorithm}
          />
          {selectedAlgorithm && (
            <ParameterPanel
              parameters={selectedAlgorithm.parameters}
              values={state.paramValues}
              arraySize={state.arraySize}
              arrayOrder={state.arrayOrder}
              onParamChange={actions.setParamValue}
              onArraySizeChange={actions.setArraySize}
              onArrayOrderChange={actions.setArrayOrder}
              onRegenerate={actions.regenerate}
              isRunning={state.isPlaying}
            />
          )}
        </aside>

        {/* Main content */}
        <main className="flex-1 flex flex-col p-6 gap-4 min-w-0 overflow-y-auto">
          {selectedAlgorithm ? (
            <>
              <div className="text-sm text-slate-400">{selectedAlgorithm.description}</div>

              {/* Visualization */}
              <div className="bg-slate-800 rounded-xl p-4">
                {state.elements.length > 0 ? (
                  <Visualizer elements={state.elements} />
                ) : (
                  <div className="h-64 flex items-center justify-center text-slate-500">
                    配列を生成中...
                  </div>
                )}
              </div>

              {/* Controls */}
              <div className="bg-slate-800 rounded-xl p-4">
                <Controls
                  isPlaying={state.isPlaying}
                  isFinished={state.isFinished}
                  currentStep={state.currentStep}
                  totalSteps={state.totalSteps}
                  speed={state.speed}
                  onPlay={actions.play}
                  onPause={actions.pause}
                  onReset={actions.reset}
                  onStepForward={actions.stepForward}
                  onStepBack={actions.stepBack}
                  onSpeedChange={actions.setSpeed}
                />
              </div>

              {/* Stats + PseudoCode */}
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-slate-800 rounded-xl p-4">
                  <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-3">
                    統計
                  </h2>
                  <StatsDisplay
                    algorithm={selectedAlgorithm}
                    comparisons={state.stats.comparisons}
                    swaps={state.stats.swaps}
                    description={state.description}
                  />
                </div>
                <div className="bg-slate-800 rounded-xl p-4">
                  <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-3">
                    疑似コード
                  </h2>
                  <PseudoCode
                    lines={selectedAlgorithm.pseudoCode}
                    currentLine={state.pseudoCodeLine}
                  />
                </div>
              </div>
            </>
          ) : (
            <div className="flex-1 flex items-center justify-center text-slate-500">
              左側のメニューからアルゴリズムを選択してください
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
