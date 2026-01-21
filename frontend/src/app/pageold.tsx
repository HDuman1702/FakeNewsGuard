"use client";

import { useQuery } from "@tanstack/react-query";

import Link from "next/link";

// hier wird dem Frontend gezeigt, wo Backend läuft
const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

export default function DashboardPage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["dashboard"],
    queryFn: async () => {
      const res = await fetch(`${API_BASE_URL}/dashboard`);
      if (!res.ok) throw new Error("Dashboard konnte nicht geladen werden");
      return res.json();
    },
    refetchInterval: 5 * 60 * 1000, // alle 5 Minuten
  });
  console.log("DASHBOARD DATA:", data);


  return (
    <main className="min-h-screen p-6">
      <div className="max-w-4xl mx-auto space-y-6">
        <h1 className="text-2xl font-bold">FakeNewsGuard – Dashboard</h1>
        <Link
          href="/analyze"
          className="rounded-md bg-sky-500 text-white px-4 py-2 text-sm font-medium hover:bg-sky-600"
        >
          URL analysieren
        </Link>

        {isLoading && <p>Lade Analysen…</p>}
        {error && <p className="text-red-400">Fehler beim Laden</p>}

        {data?.map((item: any, i: number) => (
          <div
            key={i}
            className="rounded-xl border border-slate-700 bg-slate-900 p-4 space-y-2"
          >
            {!item.result ? (
              <p className="text-sm text-slate-400">
                ⏳ Analyse läuft oder fehlgeschlagen
              </p>
            ) : (
              <>
                <div className="flex justify-between">
                  <h2 className="font-semibold">{item.result.title}</h2>
                  <span>{item.result.confidence}%</span>
                </div>

                <p className="text-sm text-slate-300">
                  <strong>Label:</strong>{" "}
                  {item.result.label === "likely_fake"
                    ? "Wahrscheinlich Fake"
                    : item.result.label === "likely_real"
                      ? "Wahrscheinlich seriös"
                      : "Unsicher"}{" "}
                  • {item.result.word_count} Wörter
                </p>
              </>




            )}
          </div>
        ))}


      </div>
    </main >

  );
}