// website/src/components/Footer.tsx
import { Code2 } from "lucide-react";

export default function Footer() {
  const currentYear = new Date().getFullYear();

  return (
    <footer className="bg-white border-t border-slate-200 py-5 mt-auto">
      <div className="max-w-6xl mx-auto px-6 flex flex-col items-center justify-center text-center space-y-4">
        
        {/* Brand / Logo */}
        <div className="flex items-center gap-2 text-slate-700 font-bold">
          <Code2 className="w-5 h-5 text-blue-600" />
          <span>LoL Semantic Graph</span>
        </div>

        {/* Educational Disclaimer */}
        <p className="text-sm text-slate-500 leading-relaxed">
          This is an academic, educational project built to explore Semantic Web technologies (RDF/OWL), Knowledge Graph Embeddings (KGE), and RAG systems. <br className="hidden md:block"/>
          It is not endorsed by, directly affiliated with, maintained, authorized, or sponsored by Riot Games.
        </p>

        {/* Copyright & Name */}
        <div className="text-xs font-medium text-slate-400 flex items-center gap-1 mt-4 border-t border-slate-100 pt-6 w-full max-w-md justify-center">
          &copy; {currentYear} Created by Thomas Jego. All rights reserved.
        </div>
        
      </div>
    </footer>
  );
}