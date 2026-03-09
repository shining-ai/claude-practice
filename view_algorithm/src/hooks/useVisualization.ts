import { useState, useEffect, useRef, useCallback } from 'react';
import type { AlgorithmDefinition, ArrayElement, Step, ArrayOrder } from '../algorithms';
import { generateArray } from '../algorithms';

const DEFAULT_ARRAY_SIZE = 30;
const BASE_INTERVAL_MS = 300;

interface VisualizationState {
  elements: ArrayElement[];
  currentStep: number;
  totalSteps: number;
  isPlaying: boolean;
  isFinished: boolean;
  speed: number;
  stats: { comparisons: number; swaps: number };
  description: string;
  pseudoCodeLine: number;
  arraySize: number;
  arrayOrder: ArrayOrder;
  paramValues: Record<string, number | string | boolean>;
}

export function useVisualization(algorithm: AlgorithmDefinition | null) {
  const [arraySize, setArraySize] = useState(DEFAULT_ARRAY_SIZE);
  const [arrayOrder, setArrayOrder] = useState<ArrayOrder>('random');
  const [paramValues, setParamValues] = useState<Record<string, number | string | boolean>>({});
  const [steps, setSteps] = useState<Step[]>([]);
  const [currentStep, setCurrentStep] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [speed, setSpeed] = useState(1);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Reset param values when algorithm changes
  useEffect(() => {
    if (!algorithm) return;
    const defaults: Record<string, number | string | boolean> = {};
    algorithm.parameters.forEach((p) => {
      defaults[p.id] = p.defaultValue;
    });
    setParamValues(defaults);
  }, [algorithm?.id]);

  const regenerate = useCallback((size: number, order: ArrayOrder, algo: AlgorithmDefinition | null, params: Record<string, number | string | boolean>) => {
    if (!algo) return [];
    const arr = generateArray(size, order);
    return algo.generate(params)(arr);
  }, []);

  // Rebuild steps when relevant inputs change
  useEffect(() => {
    setIsPlaying(false);
    if (intervalRef.current) clearInterval(intervalRef.current);

    if (!algorithm) {
      setSteps([]);
      setCurrentStep(0);
      return;
    }

    const newSteps = regenerate(arraySize, arrayOrder, algorithm, paramValues);
    setSteps(newSteps);
    setCurrentStep(0);
  }, [algorithm?.id, arraySize, arrayOrder, paramValues]);

  // Playback interval
  useEffect(() => {
    if (intervalRef.current) clearInterval(intervalRef.current);
    if (!isPlaying) return;

    intervalRef.current = setInterval(() => {
      setCurrentStep((prev) => {
        if (prev >= steps.length - 1) {
          setIsPlaying(false);
          return prev;
        }
        return prev + 1;
      });
    }, BASE_INTERVAL_MS / speed);

    return () => { if (intervalRef.current) clearInterval(intervalRef.current); };
  }, [isPlaying, speed, steps.length]);

  const currentStepData = steps[currentStep] ?? null;
  const isFinished = currentStep >= steps.length - 1 && steps.length > 0;

  const state: VisualizationState = {
    elements: currentStepData?.elements ?? [],
    currentStep,
    totalSteps: Math.max(0, steps.length - 1),
    isPlaying,
    isFinished,
    speed,
    stats: currentStepData?.stats ?? { comparisons: 0, swaps: 0 },
    description: currentStepData?.description ?? '',
    pseudoCodeLine: currentStepData?.pseudoCodeLine ?? 0,
    arraySize,
    arrayOrder,
    paramValues,
  };

  const actions = {
    play: () => { if (!isFinished) setIsPlaying(true); },
    pause: () => setIsPlaying(false),
    reset: () => {
      setIsPlaying(false);
      setCurrentStep(0);
    },
    stepForward: () => {
      if (!isFinished) setCurrentStep((p) => Math.min(p + 1, steps.length - 1));
    },
    stepBack: () => {
      setCurrentStep((p) => Math.max(p - 1, 0));
    },
    setSpeed,
    setArraySize: (size: number) => {
      setArraySize(size);
    },
    setArrayOrder: (order: ArrayOrder) => {
      setArrayOrder(order);
    },
    setParamValue: (id: string, value: number | string | boolean) => {
      setParamValues((prev) => ({ ...prev, [id]: value }));
    },
    regenerate: () => {
      if (!algorithm) return;
      const newSteps = regenerate(arraySize, arrayOrder, algorithm, paramValues);
      setSteps(newSteps);
      setCurrentStep(0);
      setIsPlaying(false);
    },
  };

  return { state, actions };
}
