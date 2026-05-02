"use client";

import React, { useState } from "react";
import { Search, Loader2 } from "lucide-react";

export default function TestShell() {
  const [loading, setLoading] = useState(false);
  const [showDashboard, setShowDashboard] = useState(false);

  const handleTestSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setShowDashboard(false);
    
    // Simulate the rendering delay
    setTimeout(() => {
      setLoading(false);
      setShowDashboard(true);
    }, 2000);
  };

  return (
    <div className="min-h-screen bg-[#050505] text-white p-12">
      <h1 className="text-4xl font-black mb-8">Integrated Shell Prototype</h1>
      
      <div className="max-w-2xl mb-12">
        <form onSubmit={handleTestSubmit} className="flex items-center bg-[#111] border border-white/10 rounded-full p-2 pl-6">
          <Search className="w-5 h-5 text-white/30 mr-4" />
          <input 
            placeholder="Type anything to test the iframe..."
            className="flex-1 bg-transparent outline-none text-white text-lg"
          />
          <button 
            type="submit"
            className="bg-orange-500 text-black px-8 py-3 rounded-full font-black text-sm uppercase"
          >
            {loading ? "Testing..." : "Inject Dashboard"}
          </button>
        </form>
      </div>

      <div className="w-full h-[700px] border-2 border-dashed border-white/10 rounded-2xl overflow-hidden bg-white/5 relative">
        {!showDashboard && !loading && (
          <div className="absolute inset-0 flex items-center justify-center text-white/20 font-mono">
            Waiting for injection...
          </div>
        )}
        
        {loading && (
          <div className="absolute inset-0 flex items-center justify-center bg-black/40 backdrop-blur-sm">
            <Loader2 className="w-8 h-8 animate-spin text-orange-500" />
          </div>
        )}

        {showDashboard && (
          <iframe 
            src="http://127.0.0.1:5175" 
            className="w-full h-full border-0"
            title="Integrated Dashboard Test"
          />
        )}
      </div>
      
      <div className="mt-8 p-6 bg-orange-500/10 border border-orange-500/20 rounded-xl text-orange-500 text-sm font-mono">
        [PROTOTYPE INFO]: This page attempts to frame http://127.0.0.1:5175. 
        If the box above is blank, check the console for "Refused to frame" errors.
      </div>
    </div>
  );
}
