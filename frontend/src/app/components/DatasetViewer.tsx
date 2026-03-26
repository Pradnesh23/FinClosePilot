"use client";

import { useState, useEffect } from "react";
import clsx from "clsx";
import {
  Database, FileSpreadsheet, Search, ChevronRight,
  Loader2, FileText, ArrowUpDown,
} from "lucide-react";
import { API_BASE } from "@/lib/api";

interface DatasetMeta {
  name: string;
  type: string;
  size_bytes: number;
  rows?: number;
  columns?: string[];
}

interface DatasetContent {
  name: string;
  rows: Record<string, any>[];
  columns: string[];
  total_rows: number;
}

export function DatasetViewer() {
  const [datasets, setDatasets] = useState<DatasetMeta[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [content, setContent] = useState<DatasetContent | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadingContent, setLoadingContent] = useState(false);
  const [searchTerm, setSearchTerm] = useState("");
  const [sortCol, setSortCol] = useState<string | null>(null);
  const [sortAsc, setSortAsc] = useState(true);

  // Fetch dataset list on mount
  useEffect(() => {
    setLoading(true);
    fetch(`${API_BASE}/datasets`)
      .then((r) => r.json())
      .then((d) => setDatasets(d.datasets ?? []))
      .catch(() => setDatasets([]))
      .finally(() => setLoading(false));
  }, []);

  // Fetch selected dataset content
  const loadDataset = async (name: string) => {
    setSelected(name);
    setContent(null);
    setLoadingContent(true);
    setSearchTerm("");
    setSortCol(null);
    try {
      const res = await fetch(`${API_BASE}/datasets/${encodeURIComponent(name)}`);
      const data = await res.json();
      setContent(data);
    } catch {
      setContent(null);
    } finally {
      setLoadingContent(false);
    }
  };

  const handleSort = (col: string) => {
    if (sortCol === col) {
      setSortAsc(!sortAsc);
    } else {
      setSortCol(col);
      setSortAsc(true);
    }
  };

  // Filter and sort rows
  const displayRows = (() => {
    if (!content) return [];
    let rows = content.rows ?? [];

    // Search filter
    if (searchTerm) {
      const term = searchTerm.toLowerCase();
      rows = rows.filter((row) =>
        Object.values(row).some((v) =>
          String(v ?? "").toLowerCase().includes(term)
        )
      );
    }

    // Sort
    if (sortCol) {
      rows = [...rows].sort((a, b) => {
        const av = a[sortCol] ?? "";
        const bv = b[sortCol] ?? "";
        const cmp = String(av).localeCompare(String(bv), undefined, { numeric: true });
        return sortAsc ? cmp : -cmp;
      });
    }

    return rows;
  })();

  const formatSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const getFileIcon = (name: string) => {
    if (name.endsWith(".csv")) return FileSpreadsheet;
    if (name.endsWith(".pdf")) return FileText;
    return Database;
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-16 text-neutral-500">
        <Loader2 className="w-5 h-5 animate-spin mr-2" />
        Loading datasets...
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-white flex items-center gap-2">
          <Database className="w-4 h-4 text-indigo-400" />
          Demo Datasets
        </h3>
        <span className="text-xs text-neutral-500">{datasets.length} files</span>
      </div>

      {/* Dataset List */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2">
        {datasets.map((ds) => {
          const Icon = getFileIcon(ds.name);
          const isSelected = selected === ds.name;
          return (
            <button
              key={ds.name}
              onClick={() => loadDataset(ds.name)}
              className={clsx(
                "flex items-center gap-3 p-3 rounded-xl border text-left transition-all",
                isSelected
                  ? "border-indigo-500/40 bg-indigo-500/10"
                  : "border-white/5 bg-white/[0.02] hover:border-white/15 hover:bg-white/[0.04]"
              )}
            >
              <div
                className={clsx(
                  "w-9 h-9 rounded-lg flex items-center justify-center shrink-0",
                  isSelected ? "bg-indigo-500/20 text-indigo-400" : "bg-white/5 text-neutral-500"
                )}
              >
                <Icon className="w-4 h-4" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-xs font-medium text-neutral-200 truncate">{ds.name}</p>
                <p className="text-[10px] text-neutral-600">
                  {formatSize(ds.size_bytes)}
                  {ds.rows !== undefined && ` · ${ds.rows} rows`}
                </p>
              </div>
              <ChevronRight className={clsx("w-3.5 h-3.5 text-neutral-600 transition-transform", isSelected && "rotate-90")} />
            </button>
          );
        })}
      </div>

      {/* Dataset Content */}
      {selected && (
        <div className="rounded-xl border border-white/10 bg-black/30 overflow-hidden">
          {loadingContent ? (
            <div className="flex items-center justify-center py-12 text-neutral-500">
              <Loader2 className="w-5 h-5 animate-spin mr-2" />
              Loading {selected}...
            </div>
          ) : content ? (
            <>
              {/* Search Bar */}
              <div className="px-4 py-3 border-b border-white/5 flex items-center gap-3">
                <Search className="w-4 h-4 text-neutral-600 shrink-0" />
                <input
                  type="text"
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  placeholder="Search in dataset..."
                  className="bg-transparent text-sm text-neutral-200 placeholder:text-neutral-600 outline-none flex-1"
                />
                <span className="text-[10px] text-neutral-600 shrink-0">
                  {displayRows.length} / {content.total_rows} rows
                </span>
              </div>

              {/* Table */}
              <div className="overflow-x-auto max-h-[500px] overflow-y-auto">
                <table className="w-full text-xs">
                  <thead className="sticky top-0 bg-neutral-900/95 backdrop-blur-sm z-10">
                    <tr>
                      <th className="px-3 py-2 text-left text-neutral-600 font-medium w-10">#</th>
                      {(content.columns ?? []).map((col) => (
                        <th
                          key={col}
                          onClick={() => handleSort(col)}
                          className="px-3 py-2 text-left text-neutral-400 font-medium cursor-pointer hover:text-white transition-colors whitespace-nowrap"
                        >
                          <span className="flex items-center gap-1">
                            {col}
                            <ArrowUpDown className="w-3 h-3 text-neutral-600" />
                          </span>
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {displayRows.slice(0, 200).map((row, i) => (
                      <tr
                        key={i}
                        className="border-t border-white/[0.03] hover:bg-white/[0.03] transition-colors"
                      >
                        <td className="px-3 py-1.5 text-neutral-700 font-mono">{i + 1}</td>
                        {(content.columns ?? []).map((col) => (
                          <td key={col} className="px-3 py-1.5 text-neutral-300 whitespace-nowrap max-w-[200px] truncate">
                            {String(row[col] ?? "")}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {displayRows.length > 200 && (
                <div className="px-4 py-2 text-[10px] text-neutral-600 border-t border-white/5 text-center">
                  Showing first 200 of {displayRows.length} filtered rows
                </div>
              )}
            </>
          ) : (
            <div className="px-4 py-12 text-center text-neutral-600 text-sm">
              Could not load this dataset. It may be in a non-tabular format.
            </div>
          )}
        </div>
      )}
    </div>
  );
}
