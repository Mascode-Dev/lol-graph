"use client";
import { 
  Network, 
  Database, 
  BrainCircuit, 
  GitMerge, 
  Code2, 
  LineChart, 
  Search,
  Cpu
} from "lucide-react";

export default function AboutPage() {
  return (
    <div className="min-h-screen bg-white text-slate-900 pb-24 selection:bg-blue-100 selection:text-blue-900">
      
      {/* Header */}
      <header className="bg-slate-50 border-b border-slate-200 px-6 py-16 md:py-24 text-center">
        <div className="max-w-4xl mx-auto space-y-6">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-blue-100 text-blue-700 font-bold text-sm tracking-wide uppercase mb-4">
            <Cpu className="w-4 h-4" /> System Architecture
          </div>
          <h1 className="text-4xl md:text-6xl font-extrabold tracking-tight text-slate-900">
            Behind the Graph
          </h1>
          <p className="text-lg md:text-xl text-slate-600 max-w-2xl mx-auto leading-relaxed">
            A deep dive into the data engineering, semantic reasoning, and machine learning pipeline that powers the League of Legends Knowledge Base.
          </p>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-6 mt-16 space-y-32">
        
        {/* Section 1: Data Pipeline */}
        <section>
          <div className="flex items-center gap-4 mb-8">
            <div className="w-12 h-12 rounded-2xl bg-blue-50 text-blue-600 flex items-center justify-center border border-blue-100">
              <Database className="w-6 h-6" />
            </div>
            <h2 className="text-3xl font-bold">1. Data Extraction & Pipeline</h2>
          </div>
          
          <div className="grid md:grid-cols-3 gap-6">
            <div className="p-8 rounded-3xl bg-slate-50 border border-slate-100 shadow-sm">
              <Search className="w-6 h-6 text-slate-400 mb-4" />
              <h3 className="text-xl font-bold mb-3">API Crawling</h3>
              <p className="text-slate-600 leading-relaxed text-sm">
                Raw JSON data was aggregated from Riot's Data Dragon (DDragon) and community Wikis. This provided base stats, lore paragraphs, and spell descriptions for over 160 champions.
              </p>
            </div>
            <div className="p-8 rounded-3xl bg-slate-50 border border-slate-100 shadow-sm">
              <Code2 className="w-6 h-6 text-slate-400 mb-4" />
              <h3 className="text-xl font-bold mb-3">NLP Processing</h3>
              <p className="text-slate-600 leading-relaxed text-sm">
                Custom Natural Language Processing scripts (`nlp_extractor.py`) parsed unstructured lore text to dynamically identify entities, relationships, and implicit regional ties.
              </p>
            </div>
            <div className="p-8 rounded-3xl bg-slate-50 border border-slate-100 shadow-sm">
              <GitMerge className="w-6 h-6 text-slate-400 mb-4" />
              <h3 className="text-xl font-bold mb-3">RDF Merging</h3>
              <p className="text-slate-600 leading-relaxed text-sm">
                The cleaned data was merged into a unified RDF graph (`merged_for_swrl.owl`), strictly adhering to our custom `lol:` ontology defining classes like Champions, Spells, and Regions.
              </p>
            </div>
          </div>
        </section>

        {/* Section 2: Semantic Reasoning */}
        <section>
          <div className="flex items-center gap-4 mb-8">
            <div className="w-12 h-12 rounded-2xl bg-indigo-50 text-indigo-600 flex items-center justify-center border border-indigo-100">
              <Network className="w-6 h-6" />
            </div>
            <h2 className="text-3xl font-bold">2. SWRL Reasoning & Ontology</h2>
          </div>
          <div className="bg-slate-900 rounded-[2.5rem] p-8 md:p-12 text-white shadow-xl relative overflow-hidden">
            <div className="relative z-10 grid md:grid-cols-2 gap-12 items-center">
              <div>
                <h3 className="text-2xl font-bold mb-4">Inferring Hidden Knowledge</h3>
                <p className="text-slate-300 leading-relaxed mb-6">
                  Before applying machine learning, I used Semantic Web Rule Language (SWRL) to inject logic into the graph. By running a reasoner, the system automatically generated new facts. 
                </p>
                <ul className="space-y-3 text-sm text-slate-400">
                  <li className="flex items-center gap-3">
                    <span className="w-1.5 h-1.5 bg-indigo-400 rounded-full"></span>
                    If Champion A is from Demacia, Champion A is hostile to Noxus.
                  </li>
                  <li className="flex items-center gap-3">
                    <span className="w-1.5 h-1.5 bg-indigo-400 rounded-full"></span>
                    If a Spell deals Physical Damage, it scales with Attack Damage.
                  </li>
                </ul>
              </div>
              <div className="bg-slate-800 border border-slate-700 p-6 rounded-2xl font-mono text-xs text-indigo-300 overflow-x-auto">
                <p className="mb-2"># Example OWL/SWRL Structure</p>
                <p>lol:Champion(?c) ^</p>
                <p>lol:belongsToRegion(?c, lol:Demacia) ^</p>
                <p>lol:Region(lol:Noxus)</p>
                <p className="text-emerald-400 mt-2">-&gt; lol:isEnemyOf(?c, lol:Noxus)</p>
              </div>
            </div>
          </div>
        </section>

        {/* Section 3: KGE & Wikidata Alignment */}
        <section>
          <div className="flex items-center gap-4 mb-8">
            <div className="w-12 h-12 rounded-2xl bg-emerald-50 text-emerald-600 flex items-center justify-center border border-emerald-100">
              <LineChart className="w-6 h-6" />
            </div>
            <h2 className="text-3xl font-bold">3. Knowledge Graph Embeddings</h2>
          </div>
          
          <div className="grid md:grid-cols-2 gap-12 items-center mb-12">
            <div>
              <p className="text-slate-600 leading-relaxed mb-6">
                Using the <strong>PyKEEN</strong> library, I trained machine learning models (TransE and DistMult) on our final knowledge graph. By embedding entities and relations into a continuous vector space, the system can predict missing links with high confidence.
              </p>
              <div className="space-y-4">
                <div className="border border-slate-200 p-4 rounded-2xl bg-white shadow-sm">
                  <h4 className="font-bold text-slate-900 mb-1">TransE (Translating Embeddings)</h4>
                  <p className="text-sm text-slate-500">Models relationships as translations in the vector space (Subject + Relation ≈ Object). Excellent for 1-to-1 relationships.</p>
                </div>
                <div className="border border-slate-200 p-4 rounded-2xl bg-white shadow-sm">
                  <h4 className="font-bold text-slate-900 mb-1">DistMult</h4>
                  <p className="text-sm text-slate-500">Uses bilinear diagonal models. Performed exceptionally well on our dataset for link prediction and entity alignment.</p>
                </div>
              </div>
            </div>
            
            {/* Make sure the image is in public/plots/kge_tsne.png */}
            <div className="bg-slate-50 p-4 rounded-3xl border border-slate-200 shadow-inner">
              <img 
                src="/plots/kge_tsne.png" 
                alt="t-SNE Plot of KGE Embeddings" 
                className="w-full h-auto rounded-2xl shadow-sm bg-white"
                onError={(e) => {
                  e.currentTarget.style.display = 'none';
                  e.currentTarget.parentElement!.innerHTML = '<div class="p-8 text-center text-slate-400 text-sm border-2 border-dashed border-slate-200 rounded-2xl">Move kge_tsne.png to public/plots/ to view the embedding clusters.</div>';
                }}
              />
              <p className="text-center text-xs text-slate-400 mt-4 font-medium">t-SNE Dimensionality Reduction of Entity Embeddings</p>
            </div>
          </div>
        </section>

        {/* Section 4: Text-to-SPARQL RAG */}
        <section className="mb-24">
          <div className="flex items-center gap-4 mb-8">
            <div className="w-12 h-12 rounded-2xl bg-purple-50 text-purple-600 flex items-center justify-center border border-purple-100">
              <BrainCircuit className="w-6 h-6" />
            </div>
            <h2 className="text-3xl font-bold">4. AI-Powered Retrieval (RAG)</h2>
          </div>
          
          <div className="p-8 rounded-3xl bg-purple-50/50 border border-purple-100">
            <p className="text-slate-700 leading-relaxed mb-8 max-w-3xl">
              The Chat Assistant doesn't just hallucinate answers. It uses a strictly constrained Retrieval-Augmented Generation (RAG) pipeline. When a user asks a question, the LLM acts as a translator, not an oracle.
            </p>
            
            <div className="grid md:grid-cols-4 gap-4 relative">
              {/* Connection Lines (Hidden on mobile) */}
              <div className="hidden md:block absolute top-1/2 left-[10%] right-[10%] h-0.5 bg-purple-200 -z-10 -translate-y-1/2"></div>
              
              <div className="bg-white p-6 rounded-2xl border border-purple-100 shadow-sm text-center">
                <div className="w-8 h-8 mx-auto bg-slate-900 text-white rounded-full flex items-center justify-center font-bold text-sm mb-4 shadow-md">1</div>
                <h4 className="font-bold text-sm mb-2">User Query</h4>
                <p className="text-xs text-slate-500">"What are Garen's spells?"</p>
              </div>
              
              <div className="bg-white p-6 rounded-2xl border border-purple-100 shadow-sm text-center">
                <div className="w-8 h-8 mx-auto bg-slate-900 text-white rounded-full flex items-center justify-center font-bold text-sm mb-4 shadow-md">2</div>
                <h4 className="font-bold text-sm mb-2">Text-to-SPARQL</h4>
                <p className="text-xs text-slate-500">LLM translates natural language into a valid RDF query.</p>
              </div>

              <div className="bg-white p-6 rounded-2xl border border-purple-100 shadow-sm text-center">
                <div className="w-8 h-8 mx-auto bg-slate-900 text-white rounded-full flex items-center justify-center font-bold text-sm mb-4 shadow-md">3</div>
                <h4 className="font-bold text-sm mb-2">Graph Execution</h4>
                <p className="text-xs text-slate-500">FastAPI queries `final_kb.nt` to extract absolute facts.</p>
              </div>

              <div className="bg-white p-6 rounded-2xl border border-purple-100 shadow-sm text-center">
                <div className="w-8 h-8 mx-auto bg-slate-900 text-white rounded-full flex items-center justify-center font-bold text-sm mb-4 shadow-md">4</div>
                <h4 className="font-bold text-sm mb-2">Fact-Based Reply</h4>
                <p className="text-xs text-slate-500">LLM formats the raw database results into a natural response.</p>
              </div>
            </div>
          </div>
        </section>

      </main>
    </div>
  );
}