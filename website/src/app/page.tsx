import Link from "next/link";
import { 
  Database, 
  BrainCircuit, 
  Network, 
  MessageSquare, 
  Search 
} from "lucide-react";

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-white text-slate-900 selection:bg-slate-200">
      <main className="max-w-6xl mx-auto px-6 pt-20 pb-24">
        
        {/* 1. Hero Section */}
        <section className="text-center space-y-8 max-w-4xl mx-auto mb-24">
          <h1 className="text-5xl md:text-7xl font-extrabold tracking-tighter text-slate-900 leading-tight">
            The League of Legends <br className="hidden md:block"/>
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-600 to-indigo-600">
              Knowledge Graph
            </span>
          </h1>
          <p className="text-lg md:text-xl text-slate-600 max-w-2xl mx-auto leading-relaxed">
            An AI-powered semantic search engine and exploratory graph built on RDF/OWL. 
            Query the rich lore, champion stats, and hidden connections of Runeterra using natural language.
          </p>
          
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4 pt-4">
            <Link 
              href="/chat" 
              className="flex items-center gap-2 bg-slate-900 text-white px-8 py-4 rounded-full font-semibold hover:bg-slate-800 transition-all shadow-lg hover:shadow-xl hover:-translate-y-0.5"
            >
              <MessageSquare className="w-5 h-5" />
              Start Chatting
            </Link>
            <Link 
              href="/explore" 
              className="flex items-center gap-2 bg-white text-slate-900 border border-slate-200 px-8 py-4 rounded-full font-semibold hover:bg-slate-50 transition-all hover:border-slate-300"
            >
              <Database className="w-5 h-5 text-slate-500" />
              Explore the Data
            </Link>
          </div>
        </section>

        {/* 2. Quick Stats / Features */}
        <section className="grid md:grid-cols-3 gap-8 mb-24">
          <div className="p-8 rounded-3xl bg-slate-50 border border-slate-100 hover:border-blue-100 transition-colors group">
            <div className="w-12 h-12 bg-white rounded-2xl flex items-center justify-center shadow-sm mb-6 text-blue-600 group-hover:scale-110 transition-transform">
              <Database className="w-6 h-6" />
            </div>
            <h3 className="text-xl font-bold mb-3">Rich RDF Ontology</h3>
            <p className="text-slate-600 leading-relaxed">
              Constructed from DDragon and the official Wiki. Contains thousands of triples linking Champions, Regions, Items, and Lore.
            </p>
          </div>

          <div className="p-8 rounded-3xl bg-slate-50 border border-slate-100 hover:border-indigo-100 transition-colors group">
            <div className="w-12 h-12 bg-white rounded-2xl flex items-center justify-center shadow-sm mb-6 text-indigo-600 group-hover:scale-110 transition-transform">
              <BrainCircuit className="w-6 h-6" />
            </div>
            <h3 className="text-xl font-bold mb-3">AI Text-to-SPARQL</h3>
            <p className="text-slate-600 leading-relaxed">
              Powered by Groq and LLaMA models. Ask questions in plain English, and the engine dynamically translates them into exact SPARQL queries.
            </p>
          </div>

          <div className="p-8 rounded-3xl bg-slate-50 border border-slate-100 hover:border-purple-100 transition-colors group">
            <div className="w-12 h-12 bg-white rounded-2xl flex items-center justify-center shadow-sm mb-6 text-purple-600 group-hover:scale-110 transition-transform">
              <Network className="w-6 h-6" />
            </div>
            <h3 className="text-xl font-bold mb-3">KGE Link Prediction</h3>
            <p className="text-slate-600 leading-relaxed">
              Utilizes TransE and DistMult embeddings to infer hidden relationships and align entities with real-world Wikidata concepts.
            </p>
          </div>
        </section>

        {/* 3. Sample Prompts */}
        <section className="bg-slate-900 rounded-[2.5rem] p-10 md:p-16 text-white text-center relative overflow-hidden">
          {/* Subtle background glow effects */}
          <div className="absolute top-0 right-0 p-32 bg-blue-500/10 blur-[100px] rounded-full pointer-events-none"></div>
          <div className="absolute bottom-0 left-0 p-32 bg-indigo-500/10 blur-[100px] rounded-full pointer-events-none"></div>
          
          <div className="relative z-10">
            <h2 className="text-3xl font-bold mb-8">Try asking the Assistant...</h2>
            <div className="flex flex-wrap justify-center gap-4">
              {[
                // "How much attack damage does Ashe have?",
                "What is the cooldown of Darius' E spell?",
                "What is the Caitlyn's attack range?",
                // "How much base HP does Sion have?"
              ].map((prompt, i) => (
                <Link 
                  key={i}
                  href={`/chat?q=${encodeURIComponent(prompt)}`}
                  className="bg-white/10 hover:bg-white/20 border border-white/10 px-6 py-3 rounded-2xl text-sm md:text-base transition-colors flex items-center gap-2 group"
                >
                  <Search className="w-4 h-4 text-slate-400 group-hover:text-white transition-colors" />
                  {prompt}
                </Link>
              ))}
            </div>
          </div>
        </section>

      </main>
    </div>
  );
}