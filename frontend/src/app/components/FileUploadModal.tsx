"use client";

import { useState, useRef, useCallback } from "react";
import {
  X, Upload, FileSpreadsheet, Building2, Receipt, FileText, Loader2, CheckCircle2,
} from "lucide-react";
import clsx from "clsx";

type FileSlot = {
  id: string;
  label: string;
  description: string;
  accept: string;
  icon: any;
  required?: boolean;
};

const FILE_SLOTS: FileSlot[] = [
  {
    id: "transactions",
    label: "ERP Transactions",
    description: "GL / Journal entries CSV export from SAP, Tally, or Oracle",
    accept: ".csv",
    icon: FileSpreadsheet,
  },
  {
    id: "bankStatement",
    label: "Bank Statement",
    description: "Bank statement CSV (HDFC, SBI, ICICI, etc.)",
    accept: ".csv",
    icon: Building2,
  },
  {
    id: "gstPortal",
    label: "GST Portal Data",
    description: "GSTR-1 / GSTR-2A / GSTR-3B CSV from GST portal",
    accept: ".csv",
    icon: Receipt,
  },
  {
    id: "form26as",
    label: "Form 26AS",
    description: "TDS certificate PDF from TRACES portal (optional)",
    accept: ".pdf",
    icon: FileText,
  },
];

const PERIODS = [
  "Q1 FY25", "Q2 FY25", "Q3 FY25", "Q4 FY25",
  "Q1 FY26", "Q2 FY26", "Q3 FY26", "Q4 FY26",
];

interface Props {
  open: boolean;
  onClose: () => void;
  onStart: (runId: string) => void;
}

export function FileUploadModal({ open, onClose, onStart }: Props) {
  const [files, setFiles] = useState<Record<string, File | null>>({});
  const [period, setPeriod] = useState("Q3 FY26");
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [dragOver, setDragOver] = useState<string | null>(null);
  const inputRefs = useRef<Record<string, HTMLInputElement | null>>({});

  const totalFiles = Object.values(files).filter(Boolean).length;

  const handleFile = useCallback((slotId: string, file: File | null) => {
    setFiles((prev) => ({ ...prev, [slotId]: file }));
    setError(null);
  }, []);

  const handleDrop = useCallback(
    (slotId: string) => (e: React.DragEvent) => {
      e.preventDefault();
      setDragOver(null);
      const file = e.dataTransfer.files?.[0];
      if (file) handleFile(slotId, file);
    },
    [handleFile]
  );

  const handleSubmit = async () => {
    if (totalFiles === 0) {
      setError("Please upload at least one file to start the pipeline.");
      return;
    }
    setUploading(true);
    setError(null);
    try {
      const { uploadFiles } = await import("@/lib/api");
      const res = await uploadFiles({
        transactions: files.transactions ?? undefined,
        bankStatement: files.bankStatement ?? undefined,
        gstPortal: files.gstPortal ?? undefined,
        form26as: files.form26as ?? undefined,
        period,
      });
      onStart(res.run_id);
    } catch (e: any) {
      setError(e.message || "Upload failed. Make sure the backend is running.");
    } finally {
      setUploading(false);
    }
  };

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/70 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="relative w-full max-w-2xl mx-4 rounded-2xl border border-white/10 bg-neutral-900/95 backdrop-blur-xl shadow-2xl shadow-indigo-500/5 animate-in fade-in zoom-in-95 duration-200">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-white/5">
          <div>
            <h2 className="text-lg font-semibold text-white flex items-center gap-2">
              <Upload className="w-5 h-5 text-indigo-400" />
              Upload Financial Data
            </h2>
            <p className="text-xs text-neutral-500 mt-0.5">
              Upload your own CSVs to run the full agent pipeline on real data
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg hover:bg-white/5 text-neutral-500 hover:text-white transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* File Slots */}
        <div className="px-6 py-5 space-y-3 max-h-[60vh] overflow-y-auto">
          {FILE_SLOTS.map((slot) => {
            const file = files[slot.id];
            const Icon = slot.icon;
            const isDragTarget = dragOver === slot.id;

            return (
              <div
                key={slot.id}
                className={clsx(
                  "relative rounded-xl border border-dashed p-4 transition-all duration-200 cursor-pointer group",
                  file
                    ? "border-emerald-500/40 bg-emerald-500/5"
                    : isDragTarget
                    ? "border-indigo-400 bg-indigo-500/10 scale-[1.01]"
                    : "border-white/10 bg-white/[0.02] hover:border-white/20 hover:bg-white/[0.04]"
                )}
                onDragOver={(e) => { e.preventDefault(); setDragOver(slot.id); }}
                onDragLeave={() => setDragOver(null)}
                onDrop={handleDrop(slot.id)}
                onClick={() => inputRefs.current[slot.id]?.click()}
              >
                <input
                  ref={(el) => { inputRefs.current[slot.id] = el; }}
                  type="file"
                  accept={slot.accept}
                  className="hidden"
                  onChange={(e) => handleFile(slot.id, e.target.files?.[0] ?? null)}
                />

                <div className="flex items-center gap-4">
                  <div
                    className={clsx(
                      "w-10 h-10 rounded-lg flex items-center justify-center shrink-0 transition-colors",
                      file
                        ? "bg-emerald-500/20 text-emerald-400"
                        : "bg-white/5 text-neutral-500 group-hover:text-neutral-300"
                    )}
                  >
                    {file ? (
                      <CheckCircle2 className="w-5 h-5" />
                    ) : (
                      <Icon className="w-5 h-5" />
                    )}
                  </div>

                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium text-neutral-200">
                        {slot.label}
                      </span>
                      <span className="text-[10px] text-neutral-600 uppercase tracking-widest">
                        {slot.accept}
                      </span>
                    </div>
                    {file ? (
                      <p className="text-xs text-emerald-400/80 mt-0.5 truncate">
                        {file.name}{" "}
                        <span className="text-neutral-600">
                          ({(file.size / 1024).toFixed(1)} KB)
                        </span>
                      </p>
                    ) : (
                      <p className="text-xs text-neutral-600 mt-0.5">
                        {slot.description}
                      </p>
                    )}
                  </div>

                  {file && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleFile(slot.id, null);
                      }}
                      className="p-1 rounded hover:bg-white/10 text-neutral-600 hover:text-red-400 transition-colors"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-white/5 flex items-center justify-between gap-4">
          {/* Period Selector */}
          <div className="flex items-center gap-2">
            <label className="text-xs text-neutral-500">Period</label>
            <select
              value={period}
              onChange={(e) => setPeriod(e.target.value)}
              className="bg-neutral-800 border border-white/10 rounded-lg px-3 py-1.5 text-xs text-neutral-200 focus:outline-none focus:ring-1 focus:ring-indigo-500"
            >
              {PERIODS.map((p) => (
                <option key={p} value={p}>
                  {p}
                </option>
              ))}
            </select>
          </div>

          <div className="flex items-center gap-3">
            {error && (
              <p className="text-xs text-red-400 max-w-[200px] truncate">{error}</p>
            )}

            <button
              onClick={handleSubmit}
              disabled={uploading || totalFiles === 0}
              className={clsx(
                "flex items-center gap-2 px-5 py-2 rounded-lg text-sm font-semibold transition-all",
                uploading || totalFiles === 0
                  ? "bg-neutral-800 text-neutral-600 cursor-not-allowed"
                  : "bg-gradient-to-r from-indigo-500 to-purple-600 text-white hover:brightness-110 shadow-lg shadow-indigo-500/20"
              )}
            >
              {uploading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Uploading…
                </>
              ) : (
                <>
                  <Upload className="w-4 h-4" />
                  Start Pipeline ({totalFiles} file{totalFiles !== 1 ? "s" : ""})
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
