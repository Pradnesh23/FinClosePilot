"use client";

import React from "react";
import { 
  Zap, ShieldCheck, BarChart3, Globe2, 
  ArrowRight, CheckCircle2, Cpu, LineChart, 
  Database, FileText, LayoutDashboard, Search,
  Upload, Clock, IndianRupee
} from "lucide-react";
import clsx from "clsx";

export function LandingPage({ onGetStarted }: { onGetStarted: () => void }) {
  return (
    <div className="min-h-screen bg-neutral-950 text-white selection:bg-indigo-500/30 selection:text-indigo-200">
      {/* ── Background Glows ── */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-[-10%] left-[-10%] w-[50%] h-[50%] bg-indigo-600/10 blur-[150px] rounded-full animate-pulse" />
        <div className="absolute bottom-[-10%] right-[-10%] w-[50%] h-[50%] bg-purple-600/10 blur-[150px] rounded-full animate-pulse delay-1000" />
        <div className="absolute top-[30%] left-[20%] w-[30%] h-[30%] bg-blue-600/5 blur-[120px] rounded-full" />
      </div>

      {/* ── Navbar ── */}
      <nav className="fixed top-0 w-full z-50 border-b border-white/5 bg-black/50 backdrop-blur-md">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-indigo-500 to-purple-600 flex items-center justify-center shadow-lg shadow-indigo-500/20">
              <Zap className="w-4 h-4 text-white" />
            </div>
            <span className="text-xl font-bold tracking-tight">FinClosePilot</span>
          </div>
          <div className="hidden md:flex items-center gap-8 text-sm font-medium text-neutral-400">
            <a href="#features" className="hover:text-white transition-colors">Features</a>
            <a href="#how-it-works" className="hover:text-white transition-colors">How it Works</a>
            <a href="#benefits" className="hover:text-white transition-colors">Benefits</a>
          </div>
          <button 
            onClick={onGetStarted}
            className="px-5 py-2 rounded-full bg-white text-black text-sm font-bold hover:bg-neutral-200 transition-all shadow-lg active:scale-95"
          >
            Launch Demo
          </button>
        </div>
      </nav>

      {/* ── Hero Section ── */}
      <section className="relative pt-32 pb-20 px-6">
        <div className="max-w-7xl mx-auto text-center space-y-8">
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-white/5 border border-white/10 text-indigo-400 text-xs font-bold animate-in fade-in slide-in-from-bottom-2 duration-700">
            <Cpu className="w-3.5 h-3.5" />
            INDIA&apos;S FIRST AI-NATIVE FINANCIAL CLOSE PLATFORM
          </div>
          <h1 className="text-5xl md:text-7xl font-black tracking-tight leading-[1.1] animate-in fade-in slide-in-from-bottom-4 duration-1000">
            Automate Your Quarter-End <br />
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-indigo-400 via-purple-400 to-blue-400">
              With Forensic AI Precision
            </span>
          </h1>
          <p className="max-w-3xl mx-auto text-neutral-400 text-lg md:text-xl leading-relaxed animate-in fade-in slide-in-from-bottom-6 duration-1000 delay-200">
            Ditch the spreadsheets. FinClosePilot orchestrates expert AI agents to handle 
            GST reconciliation, anomaly detection, and regulatory reporting in minutes, not weeks.
          </p>
          <div className="flex flex-wrap items-center justify-center gap-4 pt-6 animate-in fade-in slide-in-from-bottom-8 duration-1000 delay-300">
            <button 
              onClick={onGetStarted}
              className="group h-14 px-10 bg-gradient-to-r from-indigo-500 to-purple-600 text-white rounded-full font-bold text-lg hover:brightness-110 shadow-2xl shadow-indigo-500/30 transition-all flex items-center gap-3"
            >
              Get Started for Free
              <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
            </button>
            <a 
              href="#how-it-works"
              className="h-14 px-10 border border-white/10 bg-white/5 text-white rounded-full font-bold text-lg hover:bg-white/10 transition-all flex items-center justify-center"
            >
              Learn More
            </a>
          </div>

          {/* ── Visual Demo Window ── */}
          <div className="mt-20 relative max-w-5xl mx-auto p-2 rounded-[2.5rem] bg-indigo-500/5 border border-white/10 shadow-2xl animate-in fade-in zoom-in duration-1000 delay-500">
            <div className="absolute -inset-1 bg-gradient-to-tr from-indigo-500/20 to-purple-500/20 blur-xl opacity-50 -z-10" />
            <div className="rounded-[2rem] overflow-hidden border border-white/10 bg-neutral-900 shadow-inner min-h-[400px] flex flex-col">
              {/* Mock Header */}
              <div className="h-14 border-b border-white/5 bg-black/40 flex items-center px-6 justify-between">
                <div className="flex gap-1.5">
                  <div className="w-3 h-3 rounded-full bg-red-500/20" />
                  <div className="w-3 h-3 rounded-full bg-amber-500/20" />
                  <div className="w-3 h-3 rounded-full bg-emerald-500/20" />
                </div>
                <div className="flex items-center gap-4">
                  <div className="w-32 h-2 rounded-full bg-white/5" />
                  <div className="w-20 h-6 rounded-lg bg-indigo-500/20" />
                </div>
              </div>
              {/* Mock Content */}
              <div className="flex-1 grid grid-cols-3 gap-4 p-6">
                <div className="col-span-1 space-y-4">
                  <div className="h-24 rounded-2xl bg-white/[0.02] border border-white/5 p-4 space-y-3">
                    <div className="w-1/2 h-2 rounded-full bg-indigo-400/20" />
                    <div className="w-3/4 h-8 rounded-lg bg-indigo-400/10" />
                  </div>
                  <div className="h-40 rounded-2xl bg-white/[0.02] border border-white/5 p-4 space-y-3">
                    <div className="w-1/3 h-2 rounded-full bg-purple-400/20" />
                    <div className="space-y-2">
                       <div className="w-full h-1.5 rounded-full bg-white/5" />
                       <div className="w-full h-1.5 rounded-full bg-white/5" />
                       <div className="w-2/3 h-1.5 rounded-full bg-white/5" />
                    </div>
                  </div>
                </div>
                <div className="col-span-2 rounded-2xl bg-black/40 border border-white/5 p-6 flex flex-col">
                  <div className="flex justify-between items-center mb-6">
                    <div className="w-1/3 h-3 rounded-full bg-white/5" />
                    <div className="flex gap-2">
                      <div className="w-16 h-6 rounded bg-white/5" />
                      <div className="w-16 h-6 rounded bg-white/5" />
                    </div>
                  </div>
                  <div className="flex-1 border-t border-white/5 pt-6 space-y-4">
                    {[1,2,3].map(i => (
                      <div key={i} className="flex items-center gap-4">
                         <div className="w-10 h-10 rounded-lg bg-white/5" />
                         <div className="flex-1 space-y-2">
                            <div className="w-1/4 h-2 rounded-full bg-white/10" />
                            <div className="w-1/2 h-1.5 rounded-full bg-white/5" />
                         </div>
                         <div className="w-20 h-2 rounded-full bg-emerald-500/20" />
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
            {/* Absolute Floating Badge */}
            <div className="absolute -bottom-6 -right-6 p-4 rounded-2xl bg-neutral-800 border border-white/10 shadow-xl flex items-center gap-3 animate-bounce">
              <ShieldCheck className="w-6 h-6 text-emerald-400" />
              <div>
                <p className="text-[10px] text-neutral-500 font-bold uppercase tracking-wider">Guardrail Health</p>
                <p className="text-sm font-bold text-white tracking-tight">100% Compliant</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── Features Grid ── */}
      <section id="features" className="py-24 bg-neutral-900/50">
        <div className="max-w-7xl mx-auto px-6">
          <div className="text-center space-y-3 mb-16">
            <h2 className="text-3xl font-bold tracking-tight">Advanced Platform Features</h2>
            <p className="text-neutral-500 max-w-xl mx-auto">
              Everything you need for a forensic-grade financial close pipeline.
            </p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <FeatureCard 
              icon={BarChart3} 
              title="Hybrid Recon" 
              desc="Matching books to bank & GST using deterministic logic + LLM reasoning for 99.9% accuracy."
            />
            <FeatureCard 
              icon={Search} 
              title="Anomaly Detection" 
              desc="Statistical Z-Score analysis and Benford&apos;s Law to spot fraud or fat-finger errors."
            />
            <FeatureCard 
              icon={ShieldCheck} 
              title="Hard Guardrails" 
              desc="Real-time compliance checks for Indian Tax laws (CGST 17(5)) ensuring zero leakages."
            />
            <FeatureCard 
              icon={Globe2} 
              title="Reg Monitor" 
              desc="Automatic tracking of CBIC and SEBI notifications to keep your close process up to date."
            />
            <FeatureCard 
              icon={FileText} 
              title="Audit-Ready PDF" 
              desc="Generate comprehensive, professional reports with complete forensic audit trails."
            />
            <FeatureCard 
              icon={LayoutDashboard} 
              title="Multi-User RBAC" 
              desc="Secure manager/employee views with complete data isolation and oversight hooks."
            />
          </div>
        </div>
      </section>

      {/* ── How it Works ── */}
      <section id="how-it-works" className="py-24 px-6 border-y border-white/5">
        <div className="max-w-7xl mx-auto">
           <div className="grid grid-cols-1 lg:grid-cols-2 gap-16 items-center">
              <div className="space-y-8">
                <h2 className="text-4xl font-bold tracking-tight">The 3-Step Close Pipeline</h2>
                <p className="text-neutral-400 text-lg">FinClosePilot transforms a typically manual 15-day process into a streamlined 15-minute execution.</p>
                
                <div className="space-y-6">
                  <Step icon={Upload} step="01" title="Injest & Normalise" desc="Upload your GL, Bank Statements, and GSTR2A. Our agents handle format mapping automatically." />
                  <Step icon={Cpu} step="02" title="Parallel Execution" desc="Agents run recon, anomalies, and guardrail checks in parallel using LangGraph orchestration." />
                  <Step icon={CheckCircle2} step="03" title="Certify & Report" desc="Review AI-flagged escalations and export professional, CFO-ready audit packages." />
                </div>
              </div>
              <div className="relative aspect-square rounded-[3rem] bg-indigo-600/5 border border-white/10 p-12 overflow-hidden flex items-center justify-center">
                <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,rgba(99,102,241,0.1),transparent)]" />
                <div className="relative w-full h-full flex items-center justify-center">
                   {/* Visual graph representation */}
                   <div className="w-24 h-24 rounded-full bg-indigo-500/20 border-2 border-indigo-500/30 flex items-center justify-center z-10 shadow-2xl shadow-indigo-500/40">
                      <Zap className="w-10 h-10 text-white" />
                   </div>
                   {/* Orbital agents */}
                   <AgentNode className="top-0 left-1/2 -translate-x-1/2" icon={BarChart3} label="Recon" />
                   <AgentNode className="bottom-1/4 right-0" icon={Search} label="Anomaly" />
                   <AgentNode className="bottom-1/4 left-0" icon={ShieldCheck} label="Compliance" />
                   <AgentNode className="top-1/4 right-0" icon={IndianRupee} label="Tax" />
                </div>
              </div>
           </div>
        </div>
      </section>

      {/* ── Benefits ── */}
      <section id="benefits" className="py-24 px-6">
        <div className="max-w-7xl mx-auto grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-12">
           <Benefit icon={Clock} title="High Velocity" desc="Close your books 10x faster with AI-orchestrated workflows." />
           <Benefit icon={ShieldCheck} title="Zero Risk" desc="Real-time compliance guardrails stop tax leakages before they happen." />
           <Benefit icon={Search} title="Deep Insights" desc="Discover hidden patterns and saving opportunities in minutes." />
           <Benefit icon={Database} title="Full Audit Trail" desc="Every decision made by AI is documented with supporting evidence." />
        </div>
      </section>

      {/* ── Final CTA ── */}
      <section className="py-32 px-6">
        <div className="max-w-4xl mx-auto rounded-[3rem] bg-gradient-to-tr from-indigo-600 to-purple-700 p-12 md:p-20 text-center space-y-10 shadow-2xl shadow-indigo-500/30 relative overflow-hidden">
           <div className="absolute inset-0 opacity-10 bg-[size:20px_20px] bg-[linear-gradient(to_right,white_1px,transparent_1px),linear-gradient(to_bottom,white_1px,transparent_1px)]" />
           <div className="relative z-10 space-y-6">
              <h2 className="text-4xl md:text-5xl font-black text-white">Ready to elevate your finance operations?</h2>
              <p className="text-indigo-100/80 text-lg max-w-xl mx-auto leading-relaxed">
                Join 500+ Indian finance teams automating their close process with FinClosePilot.
              </p>
              <button 
                onClick={onGetStarted}
                className="inline-flex items-center gap-2 px-10 py-4 bg-white text-indigo-700 rounded-full font-black text-xl hover:bg-neutral-100 transition-all shadow-xl active:scale-95"
              >
                Launch Demo Now
                <ArrowRight className="w-6 h-6" />
              </button>
           </div>
        </div>
      </section>

      {/* ── Footer ── */}
      <footer className="py-12 px-6 border-t border-white/5 bg-black/60">
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-8">
           <div className="flex items-center gap-3">
              <div className="w-6 h-6 rounded bg-indigo-600 flex items-center justify-center">
                 <Zap className="w-3.5 h-3.5 text-white" />
              </div>
              <span className="font-bold tracking-tight">FinClosePilot</span>
           </div>
           <div className="flex gap-12 text-sm text-neutral-500">
              <span>Privacy Policy</span>
              <span>Terms of Service</span>
              <span>Security</span>
           </div>
           <p className="text-xs text-neutral-600 font-mono">© 2026 FinClosePilot India Edition. Built for the modern CFO.</p>
        </div>
      </footer>
    </div>
  );
}

function FeatureCard({ icon: Icon, title, desc }: any) {
  return (
    <div className="p-8 rounded-[2rem] bg-white/[0.02] border border-white/5 hover:border-indigo-500/30 hover:bg-indigo-500/5 transition-all group">
      <div className="w-12 h-12 rounded-xl bg-indigo-500/10 flex items-center justify-center mb-6 group-hover:scale-110 transition-transform">
        <Icon className="w-6 h-6 text-indigo-400" />
      </div>
      <h3 className="text-xl font-bold mb-3">{title}</h3>
      <p className="text-neutral-500 text-sm leading-relaxed">{desc}</p>
    </div>
  );
}

function Step({ icon: Icon, step, title, desc }: any) {
  return (
    <div className="flex gap-6 items-start group">
      <div className="w-12 h-12 rounded-2xl bg-white/5 border border-white/10 flex items-center justify-center text-indigo-500 font-black text-lg group-hover:bg-indigo-500 group-hover:text-white transition-all shrink-0">
        <Icon className="w-5 h-5" />
      </div>
      <div className="space-y-1">
        <div className="flex items-center gap-2">
          <span className="text-[10px] font-black text-indigo-500 uppercase tracking-widest">{step}</span>
          <h4 className="font-bold text-white">{title}</h4>
        </div>
        <p className="text-sm text-neutral-500 leading-relaxed">{desc}</p>
      </div>
    </div>
  );
}

function Benefit({ icon: Icon, title, desc }: any) {
  return (
    <div className="space-y-4">
      <div className="w-10 h-10 rounded-full bg-indigo-500/10 flex items-center justify-center">
        <Icon className="w-5 h-5 text-indigo-400" />
      </div>
      <h3 className="font-bold text-white">{title}</h3>
      <p className="text-xs text-neutral-500 leading-relaxed uppercase tracking-tighter">{desc}</p>
    </div>
  );
}

function AgentNode({ icon: Icon, label, className }: { icon: any, label: string, className: string }) {
  return (
    <div className={clsx("absolute flex flex-col items-center gap-2 animate-bounce", className)}>
       <div className="w-14 h-14 rounded-2xl bg-white/5 border border-white/10 backdrop-blur-md flex items-center justify-center shadow-2xl hover:border-indigo-500/50 transition-colors">
          <Icon className="w-6 h-6 text-indigo-400" />
       </div>
       <span className="text-[10px] font-bold text-neutral-500 uppercase tracking-wider">{label}</span>
    </div>
  );
}
