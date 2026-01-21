"use client";

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import Link from "next/link";

const API_URL = process.env.NEXT_PUBLIC_API_URL!;

type Claim = { text: string; type: "factual" | "opinion"; needs_verification: boolean };

type AnalysisResult = {
  label: "likely_fake" | "uncertain" | "likely_real";
  confidence: number;
  red_flags: string[];
  claims: Claim[];
  reasoning_summary: string;
  analysis_text: string;
  suggested_counter_sources: string[];
  title: string;
  word_count: number;
  excerpt: string;
};



export default function AnalyzePage() {
  const [url, setUrl] = useState("");
  const [result, setResult] = useState<AnalysisResult | null>(null);

  const mutation = useMutation({
    mutationFn: async (targetUrl: string) => {
      const res = await fetch(`${API_URL}/analyze`, {
        method: "POST",
        headers: { "Content-Type": "application/json; charset=utf-8" },
        body: JSON.stringify({ url: targetUrl }),
      });
      if (!res.ok) {
        const text = await res.text();
        throw new Error(text || "Analyse fehlgeschlagen");
      }
      return (await res.json()) as AnalysisResult;
    },
    onSuccess: (data) => setResult(data),
  });

  return (
    <main className="min-h-screen p-6">
      <div className="max-w-3xl mx-auto space-y-6">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold tracking-tight">URL analysieren</h1>
          <Link className="text-sm underline text-sky-400" href="/">
            Zurück zum Dashboard
          </Link>
        </div>

        <form
          onSubmit={(e) => {
            e.preventDefault();
            if (!url) return;
            mutation.mutate(url);
          }}
          className="flex gap-2"
        >
          <input
            className="flex-1 rounded-md border border-slate-700 bg-slate-900 px-3 py-2 text-sm"
            placeholder="https://de.wikipedia.org/wiki/Fake_News"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
          />
          <button
            className="rounded-md bg-slate-100 text-slate-950 px-4 py-2 text-sm font-medium hover:bg-white disabled:opacity-60"
            type="submit"
            disabled={mutation.isPending}
          >
            {mutation.isPending ? "Analysiere..." : "Analysieren"}
          </button>
        </form>

        {mutation.isError && <p className="text-sm text-red-400">{(mutation.error as Error).message}</p>}

        {result && (
          <div className="rounded-xl border border-slate-700 bg-slate-900 p-4 space-y-3">
            <div className="flex items-baseline justify-between">
              <div>
                <p className="text-xs uppercase text-slate-400">Titel</p>
                <p className="text-lg font-semibold">{result.title}</p>
              </div>
              <div className="text-right">
                <p className="text-xs uppercase text-slate-400">Konfidenz</p>
                <p className="text-xl font-bold">{result.confidence}%</p>
              </div>
            </div>

            <p className="text-sm text-slate-300">
              <span className="font-semibold">Label:</span>{" "}
              {result.label === "likely_fake" && "Wahrscheinlich Fake"}
              {result.label === "uncertain" && "Unsicher"}
              {result.label === "likely_real" && "Wahrscheinlich seriös"} •{" "}
              {result.word_count} Wörter
            </p>

            <p className="text-sm text-slate-200">{result.excerpt}</p>

            {result.red_flags?.length > 0 && (
              <div>
                <p className="text-xs uppercase text-slate-400 mb-1">Auffälligkeiten</p>
                <ul className="list-disc list-inside text-sm text-slate-300 space-y-1">
                  {result.red_flags.map((f, i) => (
                    <li key={i}>{f}</li>
                  ))}
                </ul>
              </div>
            )}

            {result.suggested_counter_sources?.length > 0 && (
              <div>
                <p className="text-xs uppercase text-slate-400 mb-1">Gegenprüfung</p>
                <ul className="list-disc list-inside text-sm text-slate-300 space-y-1">
                  {result.suggested_counter_sources.map((s, i) => (
                    <li key={i}>
                      <a className="underline text-sky-400" href={s} target="_blank" rel="noreferrer">
                        {s}
                      </a>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {result.reasoning_summary && (
              <div>
                <p className="text-xs uppercase text-slate-400 mb-1">Summary</p>
                <p className="text-sm text-slate-200 whitespace-pre-wrap">{result.reasoning_summary}</p>
              </div>
            )}

            {result.analysis_text && (
              <div>
                <p className="text-xs uppercase text-slate-400 mb-1">Analyse</p>
                <p className="text-sm text-slate-200 whitespace-pre-wrap">
                  {result.analysis_text}
                </p>
              </div>
            )}

          </div>
        )}
      </div>
    </main>
  );
}
