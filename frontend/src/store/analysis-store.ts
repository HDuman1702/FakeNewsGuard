import { create } from "zustand";

export type Claim = {
  text: string;
  type: "factual" | "opinion";
  needs_verification: boolean;
};

export type AnalysisResult = {
  label: "likely_fake" | "uncertain" | "likely_real";
  confidence: number;
  red_flags: string[];
  claims: Claim[];
  reasoning_summary: string;
  suggested_counter_sources: string[];
};

type State = {
  lastAnalysis: AnalysisResult | null;
  setLastAnalysis: (result: AnalysisResult | null) => void;
};

export const useAnalysisStore = create<State>((set) => ({
  lastAnalysis: null,
  setLastAnalysis: (result) => set({ lastAnalysis: result }),
}));
