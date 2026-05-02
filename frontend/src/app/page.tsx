"use client";

import React, { useState, useEffect, useRef } from "react";
import { Search, History, Loader2, X } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

export default function IPLDashboard() {
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [blueprint, setBlueprint] = useState<any>(null);
  const [history, setHistory] = useState<any[]>([]);
  const [showHistory, setShowHistory] = useState(false);
  const [status, setStatus] = useState("");

  const fetchHistory = async () => {
    try {
      const res = await fetch("/api/history");
      const data = await res.json();
      setHistory(Object.values(data).sort((a: any, b: any) => 
        new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
      ));
    } catch (err) { console.error(err); }
  };

  useEffect(() => { fetchHistory(); }, []);

  const handleSearch = async (e?: React.FormEvent, overrideData?: any) => {
    if (e) e.preventDefault();
    if (!query && !overrideData) return;

    setLoading(true);
    setBlueprint(null);
    setStatus("Designing...");

    try {
      const res = await fetch("/api/query", {
        method: overrideData ? "PATCH" : "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(overrideData ? { data: overrideData } : { query }),
      });
      const data = await res.json();
      setBlueprint(data.blueprint);
      fetchHistory();
    } catch (err) {
      console.error(err);
      setStatus("Error designing dashboard.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#050505] text-white selection:bg-orange-500/30 overflow-x-hidden">
      {/* --- History Toggle --- */}
      <button 
        onClick={() => setShowHistory(true)}
        className="fixed top-6 left-6 z-50 p-3 bg-white/5 hover:bg-white/10 border border-white/10 rounded-full backdrop-blur-xl transition-all group"
      >
        <History className="w-5 h-5 text-white/40 group-hover:text-orange-500 transition-colors" />
      </button>

      {/* --- Sidebar Vault --- */}
      <AnimatePresence>
        {showHistory && (
          <>
            <motion.div 
              initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
              onClick={() => setShowHistory(false)}
              className="fixed inset-0 bg-black/60 backdrop-blur-sm z-[60]"
            />
            <motion.div 
              initial={{ x: -400 }} animate={{ x: 0 }} exit={{ x: -400 }}
              className="fixed top-0 left-0 h-full w-80 bg-[#0a0a0a] border-r border-white/10 z-[70] p-6 shadow-2xl flex flex-col"
            >
              <div className="flex justify-between items-center mb-8">
                <h2 className="text-xl font-black tracking-tight">History Vault</h2>
                <button onClick={() => setShowHistory(false)} className="p-2 hover:bg-white/5 rounded-full"><X className="w-4 h-4" /></button>
              </div>
              <div className="flex-1 overflow-y-auto space-y-3 pr-2 scrollbar-hide">
                {history.map((item) => (
                  <button
                    key={item.id}
                    onClick={() => { handleSearch(undefined, item.data); setShowHistory(false); }}
                    className="w-full text-left p-4 rounded-xl bg-white/5 border border-white/5 hover:border-orange-500/30 hover:bg-white/10 transition-all group"
                  >
                    <div className="text-xs text-white/30 mb-1">{new Date(item.timestamp).toLocaleTimeString()}</div>
                    <div className="font-bold text-sm text-white/80 group-hover:text-white truncate">
                      {item.data?.name || item.data?.title || "Search Result"}
                    </div>
                  </button>
                ))}
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>

      {/* --- Main Dashboard --- */}
      <main className="w-full min-h-screen flex flex-col items-center pt-16 pb-24 px-6 md:px-12">
        
        <header className="w-full max-w-4xl text-center mb-16 space-y-8">
          <h1 className="text-6xl md:text-7xl font-black tracking-tighter leading-none">
            IPL 2026 <span className="text-transparent bg-clip-text bg-gradient-to-r from-orange-500 to-yellow-500">Insights</span>
          </h1>

          <form onSubmit={handleSearch} className="relative group max-w-2xl mx-auto pt-4">
            <div className="absolute inset-0 bg-orange-500/10 blur-2xl group-focus-within:bg-orange-500/30 transition-all rounded-full" />
            <div className="relative flex items-center bg-[#111] border border-white/10 rounded-full p-2 pl-6 focus-within:border-orange-500/50 transition-all">
              <Search className="w-5 h-5 text-white/30 mr-4" />
              <input 
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Search players, standings, or match history..."
                className="flex-1 bg-transparent outline-none text-white text-lg placeholder:text-white/20"
              />
              <button 
                type="submit"
                disabled={loading}
                className="bg-orange-500 hover:bg-orange-600 disabled:bg-white/10 text-black px-8 py-3 rounded-full font-black text-sm uppercase tracking-wider transition-all"
              >
                {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : "Analyze"}
              </button>
            </div>
          </form>
        </header>

        {/* --- Render Canvas --- */}
        <div className="w-full max-w-[1600px]">
          {loading ? (
            <div className="flex flex-col items-center justify-center py-32 gap-6">
              <Loader2 className="w-12 h-12 text-orange-500 animate-spin" />
              <div className="text-white/40 font-mono text-sm uppercase tracking-widest">{status}</div>
            </div>
          ) : blueprint?.action === "refresh_iframe" ? (
            <div className="w-full bg-white/5 border border-white/10 rounded-2xl overflow-hidden h-[800px] shadow-2xl">
                <iframe 
                    src={`${blueprint.url}?t=${Date.now()}`} 
                    className="w-full h-full border-0"
                    title="Prefab Generated App"
                />
            </div>
          ) : null}
        </div>
      </main>

      {/* Decorative Gradients */}
      <div className="fixed top-0 left-1/4 w-[500px] h-[500px] bg-orange-500/5 rounded-full blur-[120px] pointer-events-none -z-10" />
      <div className="fixed bottom-0 right-1/4 w-[600px] h-[600px] bg-blue-500/5 rounded-full blur-[150px] pointer-events-none -z-10" />
    </div>
  );
}
