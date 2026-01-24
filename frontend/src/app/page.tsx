"use client";

import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

const CATEGORIES = [
    "Satire / Parodie",
    "Propaganda",
    "Clickbait",
    "Irreführende Inhalte",
    "Falschmeldung",
    "Manipulation",
    "Seriöse Nachricht",

] as const;







type Claim = { text: string; type: "factual" | "opinion"; needs_verification: boolean };

type AnalysisResult = {
    confidence: number;
    category?: (typeof CATEGORIES)[number];
    signals?: string[];
    rationale?: string;
    red_flags: string[];
    claims: Claim[];
    reasoning_summary: string;
    suggested_counter_sources: string[];
    title: string;
    word_count: number;
    excerpt: string;
    topics?: string[];
};

type DashboardItem = {
    url: string;
    source_domain?: string;
    domain?: string;
    analyzed_at?: string;
    result: AnalysisResult & {
        source_domain?: string;
    };

};

export default function HomePage() {
    const [q, setQ] = useState("");
    const [minConf, setMinConf] = useState("");
    const [onlyFailed, setOnlyFailed] = useState(false);
    const [order, setOrder] = useState<"asc" | "desc">("desc");
    const [sort, setSort] = useState("created_at");
    const [refreshInfo, setRefreshInfo] = useState<string | null>(null);
    const [catChecks, setCatChecks] = useState<Record<string, boolean>>(
        Object.fromEntries(CATEGORIES.map(c => [c, false]))
    );


    const queryString = useMemo(() => {
        const params = new URLSearchParams();

        params.set("limit", "50");
        params.set("sort", sort);
        params.set("order", order);

        if (minConf) params.set("min_conf", minConf);
        if (onlyFailed) params.set("only_failed", "true");

        const selectedCategories = Object.entries(catChecks)
            .filter(([_, checked]) => checked)
            .map(([cat]) => cat);

        if (selectedCategories.length > 0) {
            params.set("categories", selectedCategories.join(","));
        }

        return params.toString();
    }, [catChecks, sort, order, minConf, onlyFailed]);


    const { data, isLoading, error, refetch, isFetching } = useQuery({
        queryKey: ["dashboard", queryString],
        queryFn: async () => {
            const res = await fetch(`${API_BASE_URL}/dashboard?${queryString}`);
            if (!res.ok) throw new Error("Dashboard konnte nicht geladen werden");
            return res.json();
        },
        refetchOnWindowFocus: false,
    });



    const { data: trendingTopics } = useQuery({
        queryKey: ["trendingTopics", 3],
        queryFn: async () => {
            const res = await fetch(`${API_BASE_URL}/topics/trending?days=3&min_conf=70&limit=12`);
            if (!res.ok) return [];
            return (await res.json()) as { topic: string; count: number }[];
        },
        refetchOnWindowFocus: false,
    });

    const handleRefresh = async () => {
        setRefreshInfo(null);

        const beforeCount = data?.length ?? 0;
        const result = await refetch();
        const afterCount = result.data?.length ?? 0;

        if (afterCount === beforeCount) {
            setRefreshInfo("Dashboard ist bereits auf dem neuesten Stand.");
        } else {
            setRefreshInfo(`${afterCount - beforeCount} neue Einträge geladen.`);
        }

        // Meldung nach 3 Sekunden ausblenden
        setTimeout(() => setRefreshInfo(null), 3000);
    };


    return (
        <main className="min-h-screen p-6">
            <div className="max-w-5xl mx-auto space-y-6">
                <section className="rounded-lg border border-slate-800 bg-slate-950 p-4">
                    <div className="flex items-center justify-between">
                        <h2 className="text-sm font-semibold text-slate-200">Themen-Hotspots (letzte 3 Tage)</h2>
                        <span className="text-xs text-slate-400">nur bösartige Fake-News-Kategorien, Confidence ≥ 70</span>
                    </div>
                    <div className="mt-3 flex flex-wrap gap-2">
                        {(trendingTopics || []).length ? (
                            (trendingTopics || []).map((t) => (
                                <span
                                    key={t.topic}
                                    className="rounded-full border border-slate-700 bg-slate-900 px-3 py-1 text-xs text-slate-200"
                                    title={`${t.count} Artikel`}
                                >
                                    {t.topic} <span className="text-slate-400">({t.count})</span>
                                </span>
                            ))
                        ) : (
                            <span className="text-xs text-slate-400">Noch keine Topic-Daten.</span>
                        )}
                    </div>
                </section>

                <div className="flex items-start justify-between gap-3">
                    <div>
                        <h1 className="text-3xl font-bold tracking-tight">FakeNewsGuard</h1>
                        <p className="text-sm text-slate-300"> Automatisches News-Dashboard mit On-Demand-Analyse und manueller URL-Prüfung.</p>
                    </div>

                    <div className="flex items-center gap-3">
                        {/* Status Badge */}
                        {!isLoading && (
                            <span className="rounded-full border border-slate-700 bg-slate-900 px-3 py-1 text-xs text-slate-400">
                                {data?.length
                                    ? `${data.length} Artikel geladen`
                                    : "Keine neuen Artikel"}
                            </span>
                        )}

                        {/* Buttons */}
                        <button
                            className="rounded-md border border-slate-700 px-4 py-2 text-sm hover:bg-slate-800 disabled:opacity-50"
                            onClick={handleRefresh}
                            disabled={isFetching}
                            type="button"
                        >
                            {isFetching ? "Aktualisiere..." : "Aktualisieren"}
                        </button>



                        {refreshInfo && (
                            <span className="inline-block mt-2 rounded-full bg-slate-800 px-3 py-1 text-xs text-slate-300">
                                {refreshInfo}
                            </span>
                        )}



                        <Link
                            href="/analyze"
                            className="rounded-md bg-slate-200 px-4 py-2 text-sm font-medium text-slate-900 hover:bg-white"
                        >
                            URL analysieren
                        </Link>
                    </div>

                </div>

                {isLoading && <p className="text-slate-300">Lade Dashboard…</p>}
                {error && <p className="text-red-400">{(error as Error).message}</p>}

                <div className="rounded-xl border border-slate-700 bg-slate-900 p-4 space-y-3">
                    <div className="grid grid-cols-1 md:grid-cols-6 gap-2">
                        <input
                            className="md:col-span-2 rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-sm"
                            placeholder="Suche (Titel oder URL)"
                            value={q}
                            onChange={(e) => setQ(e.target.value)}
                        />

                        <div className="md:col-span-2 flex flex-wrap gap-3 rounded-md border border-slate-800 bg-slate-950 p-3">
                            <div className="w-full text-xs text-slate-400">Kategorien</div>
                            {CATEGORIES.map((c) => (
                                <label key={c} className="flex items-center gap-2 text-sm text-slate-200">
                                    <input
                                        type="checkbox"
                                        checked={!!catChecks[c]}
                                        onChange={(e) => setCatChecks((prev) => ({ ...prev, [c]: e.target.checked }))}
                                    />
                                    <span>{c}</span>
                                </label>
                            ))}
                        </div>



                        <input
                            className="rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-sm"
                            placeholder="Min. Konf. (0-100)"
                            value={minConf}
                            onChange={(e) => setMinConf(e.target.value)}
                        />

                        <button
                            className="rounded-md border border-slate-700 px-3 py-2 text-sm hover:bg-slate-800"
                            onClick={() => setOrder((o) => (o === "desc" ? "asc" : "desc"))}
                            type="button"
                            title="Sortierreihenfolge umschalten"
                        >
                            {order === "desc" ? "↓" : "↑"}
                        </button>
                    </div>

                    <label className="flex items-center gap-2 text-sm text-slate-300">
                        <input type="checkbox" checked={onlyFailed} onChange={(e) => setOnlyFailed(e.target.checked)} />
                        Nur fehlerhafte / unvollständige Artikel
                    </label>
                </div>

                <div className="overflow-x-auto rounded-xl border border-slate-700">
                    <table className="w-full text-sm">
                        <thead className="bg-slate-950">
                            <tr className="text-left text-slate-300">
                                <th className="p-3">Zeit</th>
                                <th className="p-3">Quelle</th>
                                <th className="p-3">Titel</th>
                                <th className="p-3">Kategorie</th>
                                <th className="p-3">Konf.</th>
                                <th className="p-3">Wörter</th>
                            </tr>
                        </thead>
                        <tbody>
                            {(data ?? []).map((item: DashboardItem, index: number) => (
                                <tr key={`${item.url}-${index}`} className="border-t border-slate-800 bg-slate-900 align-top">
                                    <td className="p-3 whitespace-nowrap text-slate-400">
                                        {item.analyzed_at ? new Date(item.analyzed_at).toLocaleString() : "—"}
                                    </td>
                                    <td className="p-3 text-slate-400">
                                        {item.source_domain ?? item.domain ?? item.result?.source_domain ?? "—"}
                                    </td>
                                    <td className="p-3">
                                        <div className="space-y-1">
                                            <a className="underline text-sky-400 wrap-break-words" href={item.url} target="_blank" rel="noreferrer">
                                                {item.result?.title || item.url}
                                            </a>
                                            <div className="text-xs text-slate-500 break-all">{item.url}</div>
                                            {item.result?.excerpt ? <div className="text-xs text-slate-300">{item.result.excerpt}</div> : null}
                                            {item.result?.red_flags?.length ? (
                                                <div className="text-xs text-amber-300">{item.result.red_flags[0]}</div>
                                            ) : null}
                                            {item.result?.topics?.length ? (
                                                <div className="mt-2 flex flex-wrap gap-2">
                                                    {item.result.topics.slice(0, 8).map((t: string) => (
                                                        <span key={t} className="rounded-full border border-slate-700 bg-slate-950 px-2 py-0.5 text-[11px] text-slate-200">
                                                            {t}
                                                        </span>
                                                    ))}
                                                </div>
                                            ) : null}
                                        </div>
                                    </td>
                                    <td className="p-3 text-slate-300">{item.result?.category ?? "—"}</td>
                                    <td className="p-3 text-slate-200">{item.result?.confidence !== null ? `${item.result.confidence}%` : "—"}</td>
                                    <td className="p-3 text-slate-200">{item.result?.word_count ?? 0}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>
        </main>
    );
}
