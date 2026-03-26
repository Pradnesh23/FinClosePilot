"use client";
import { useState } from "react";
import { Search, Loader2, MessageSquare } from "lucide-react";
import { postAuditQuery } from "@/lib/api";

export function AuditQuery({ runId }: { runId?: string }) {
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<any[]>([]);
  const [answer, setAnswer] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const suggestions = [
    "Why was ITC blocked for Grand Hyatt?",
    "Show all HARD_BLOCK guardrail fires",
    "What caused the travel budget variance?",
    "List all duplicate payments detected",
  ];

  const handleQuery = async (q?: string) => {
    const query = q || question;
    if (!query.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const data = await postAuditQuery(query, runId);
      setResults(data.results || []);
      setAnswer(data.answer || null);
    } catch (err: any) {
      setError("Query failed — is the backend running?");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex gap-2">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-500" />
          <input
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleQuery()}
            placeholder="Ask anything about this close period..."
            className="w-full pl-10 pr-4 py-2.5 bg-black/40 border border-white/10 rounded-xl text-sm text-white placeholder:text-neutral-600 focus:outline-none focus:border-indigo-500/50 transition-colors"
          />
        </div>
        <button
          onClick={() => handleQuery()}
          disabled={loading}
          className="px-4 py-2.5 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 rounded-xl text-sm font-medium transition-colors shadow-lg shadow-indigo-500/20"
        >
          {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : "Ask"}
        </button>
      </div>

      {/* Suggestions */}
      <div className="flex flex-wrap gap-2">
        {suggestions.map((s) => (
          <button
            key={s}
            onClick={() => { setQuestion(s); handleQuery(s); }}
            className="px-3 py-1.5 text-[10px] font-bold uppercase tracking-wider rounded-lg bg-neutral-800 hover:bg-neutral-700 text-neutral-400 hover:text-white transition-colors border border-white/5 active:scale-95"
          >
            {s}
          </button>
        ))}
      </div>

      {error && <p className="text-sm text-red-400 bg-red-500/10 rounded-xl px-4 py-3 border border-red-500/20">{error}</p>}

      {answer && (
        <div className="p-4 rounded-xl bg-indigo-600/10 border border-indigo-500/20 space-y-2 animate-in slide-in-from-top-2 duration-500">
          <div className="flex items-center gap-2 text-indigo-400 font-bold text-[10px] uppercase tracking-widest">
            <MessageSquare className="w-3.5 h-3.5" />
            Auditor Summary
          </div>
          <p className="text-sm text-white leading-relaxed">{answer}</p>
        </div>
      )}

      {results.length > 0 && (
        <div className="space-y-2 max-h-80 overflow-y-auto pr-1 custom-scrollbar">
          <div className="text-[10px] text-neutral-600 font-bold uppercase tracking-widest px-1">Supporting Evidence ({results.length})</div>
          {results.map((r, i) => (

            <div key={i} className="p-3 rounded-lg bg-neutral-900 border border-white/5 text-sm">
              <div className="flex items-center gap-2 text-xs text-neutral-500 mb-1">
                <MessageSquare className="w-3.5 h-3.5" />
                <span>{r.agent || r.event || "Result"}</span>
                {r.logged_at && <span>{new Date(r.logged_at).toLocaleTimeString()}</span>}
              </div>
              <p className="text-neutral-300">
                {r.action || r.violation_detail || r.details?.message || JSON.stringify(r).slice(0, 200)}
              </p>
            </div>
          ))}
        </div>
      )}

      {results.length === 0 && !loading && question && (
        <p className="text-center text-xs text-neutral-600 py-4">No results found for that query.</p>
      )}
    </div>
  );
}
