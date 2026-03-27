"use client";

import { useState, useEffect } from "react";
import { Database, TableProperties, Link as LinkIcon, Search, LayoutGrid, Loader2, X, Sparkles, Activity } from "lucide-react";

type TabType = "champions" | "ontology" | "alignment";

export default function ExplorePage() {
  const [activeTab, setActiveTab] = useState<TabType>("champions");
  const [searchTerm, setSearchTerm] = useState("");
  
  const [champions, setChampions] = useState<any[]>([]);
  const [alignments, setAlignments] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [schema, setSchema] = useState<any[]>([]);
  

  // NEW: State to hold the champion clicked for the modal
  const [selectedChampion, setSelectedChampion] = useState<any | null>(null);

  const ontology = [
    { prefix: "lol:", name: "championName", type: "DatatypeProperty", domain: "Champion", range: "xsd:string" },
    { prefix: "lol:", name: "belongsToRegion", type: "ObjectProperty", domain: "Champion", range: "Region" },
    { prefix: "lol:", name: "hasRole", type: "ObjectProperty", domain: "Champion", range: "Role" },
    { prefix: "lol:", name: "hasSpell", type: "ObjectProperty", domain: "Champion", range: "Spell" },
    { prefix: "lol:", name: "spellName", type: "DatatypeProperty", domain: "Spell", range: "xsd:string" },
    { prefix: "lol:", name: "cooldownBurn", type: "DatatypeProperty", domain: "Spell", range: "xsd:string" },
    { prefix: "lol:", name: "lore", type: "DatatypeProperty", domain: "Champion", range: "xsd:string" },
  ];
  
  // Helper to format names for DDragon URLs (e.g., "Lee Sin" -> "LeeSin", "Kha'Zix" -> "Khazix")
  const getCleanName = (name: string) => {
    if (!name) return "Unknown";
    // Fix notorious Riot naming exceptions
    if (name === "Wukong") return "MonkeyKing";
    if (name === "Nunu & Willump") return "Nunu";
    if (name === "Renata Glasc") return "Renata";
    if (name === "Bel'Veth") return "Belveth";
    
    return name.replace(/[' \.]/g, '');
  };
  
  const requestConfig = {
    method: "GET",
    headers: {
      "Content-Type": "application/json",
      "ngrok-skip-browser-warning": "true", // CRUCIAL
      "User-Agent": "Custom" // Parfois nécessaire pour certains tunnels
    },
  };

  useEffect(() => {
    const fetchGraphData = async () => {
      setIsLoading(true);
      try {
        const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
        const [champRes, alignRes, schemaRes] = await Promise.all([
            fetch(`${API_BASE}/api/champions`, requestConfig),
            fetch(`${API_BASE}/api/alignments`, requestConfig),
            fetch(`${API_BASE}/api/schema`, requestConfig)
          ]);
        
          // Vérifie si la réponse est bien du JSON avant de parser
          const contentType = champRes.headers.get("content-type");
          if (!contentType || !contentType.includes("application/json")) {
            const text = await champRes.text();
            console.error("Le serveur n'a pas renvoyé de JSON mais :", text.substring(0, 100));
            throw new Error("Réponse invalide du serveur (HTML au lieu de JSON)");
          }
        
          const [champions, alignments, schema] = await Promise.all([
            champRes.json(),
            alignRes.json(),
            schemaRes.json()
          ]);
      } catch (error) {
        console.error("Failed to fetch graph data", error);
      } finally {
        setIsLoading(false);
      }
    };

    fetchGraphData();
  }, []);

  const filteredChampions = champions.filter(c => 
    c.name?.toLowerCase().includes(searchTerm.toLowerCase()) || 
    c.region?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    c.role?.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const filteredAlignments = alignments.filter(a => 
    a.entity?.toLowerCase().includes(searchTerm.toLowerCase()) || 
    a.wdTarget?.toLowerCase().includes(searchTerm.toLowerCase())
  );
  
  const filteredSchema = schema.filter(s => 
      s.name?.toLowerCase().includes(searchTerm.toLowerCase()) || 
      s.domain?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      s.type?.toLowerCase().includes(searchTerm.toLowerCase())
    );

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 pb-20 relative">
      
      {/* ... (Header and Tabs remain the same) ... */}
      <header className="bg-white border-b border-slate-200 px-6 py-8 md:py-12 text-center">
        <div className="max-w-3xl mx-auto space-y-4">
          <div className="w-16 h-16 bg-blue-100 text-blue-600 rounded-2xl flex items-center justify-center mx-auto mb-6 shadow-sm">
            <Database className="w-8 h-8" />
          </div>
          <h1 className="text-3xl md:text-4xl font-extrabold tracking-tight">Knowledge Base Explorer</h1>
          <p className="text-slate-500 text-lg">
            Browse the entire knowledge graph, containing {champions.length > 0 ? champions.length : "all"} extracted champions and {alignments.length > 0 ? alignments.length : "their"} Wikidata alignments.
          </p>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-4 sm:px-6 pt-8">
        
        <div className="flex flex-wrap items-center justify-center gap-2 mb-8">
          <button onClick={() => setActiveTab("champions")} className={`flex items-center gap-2 px-6 py-3 rounded-full font-semibold transition-all shadow-sm ${activeTab === "champions" ? "bg-slate-900 text-white" : "bg-white text-slate-600 hover:bg-slate-100 border border-slate-200"}`}>
            <TableProperties className="w-4 h-4" /> Champions Data
          </button>
          <button onClick={() => setActiveTab("ontology")} className={`flex items-center gap-2 px-6 py-3 rounded-full font-semibold transition-all shadow-sm ${activeTab === "ontology" ? "bg-slate-900 text-white" : "bg-white text-slate-600 hover:bg-slate-100 border border-slate-200"}`}>
            <LayoutGrid className="w-4 h-4" /> LoL Schema
          </button>
          <button onClick={() => setActiveTab("alignment")} className={`flex items-center gap-2 px-6 py-3 rounded-full font-semibold transition-all shadow-sm ${activeTab === "alignment" ? "bg-slate-900 text-white" : "bg-white text-slate-600 hover:bg-slate-100 border border-slate-200"}`}>
            <LinkIcon className="w-4 h-4" /> Wikidata Alignment
          </button>
        </div>

        {(activeTab === "champions" || activeTab === "alignment") && (
          <div className="mb-6 relative max-w-md mx-auto">
            <Search className="w-5 h-5 text-slate-400 absolute left-4 top-1/2 -translate-y-1/2" />
            <input 
              type="text" 
              placeholder={`Search ${activeTab === "champions" ? "champions, roles, or regions" : "entities or Wikidata targets"}...`}
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-12 pr-4 py-3 bg-white border border-slate-200 shadow-sm rounded-full text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all w-full"
            />
          </div>
        )}

        {isLoading ? (
          <div className="flex flex-col items-center justify-center py-20 text-slate-500">
            <Loader2 className="w-8 h-8 animate-spin text-blue-600 mb-4" />
            <p className="font-medium">Loading graph data from backend...</p>
          </div>
        ) : (
          <>
            {activeTab === "champions" && (
              <div className="bg-white rounded-3xl border border-slate-200 shadow-sm overflow-hidden animate-in fade-in slide-in-from-bottom-4 duration-500">
                <div className="overflow-x-auto max-h-[600px] overflow-y-auto">
                  <table className="w-full text-left text-sm relative">
                    <thead className="bg-slate-50 text-slate-500 font-medium border-b border-slate-200 sticky top-0 z-10 shadow-sm">
                      <tr>
                        <th className="px-6 py-4">Champion Name</th>
                        <th className="px-6 py-4">Title</th>
                        <th className="px-6 py-4">Role</th>
                        <th className="px-6 py-4">Region</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {filteredChampions.map((champ, i) => (
                        <tr 
                          key={i} 
                          onClick={() => setSelectedChampion(champ)}
                          className="hover:bg-blue-50/50 transition-colors cursor-pointer group"
                        >
                          <td className="px-6 py-4 font-semibold text-slate-900 group-hover:text-blue-600 transition-colors flex items-center gap-4">
                            {/* CHAMPION AVATAR */}
                            <img 
                              src={`https://ddragon.leagueoflegends.com/cdn/16.6.1/img/champion/${getCleanName(champ.name)}.png`}
                              alt={champ.name}
                              className="w-10 h-10 rounded-full border border-slate-200 shadow-sm bg-slate-100"
                              onError={(e) => { e.currentTarget.style.display = 'none'; }} // Hide if Riot doesn't have the image
                            />
                            {champ.name}
                          </td>
                          <td className="px-6 py-4 text-slate-600">{champ.title}</td>
                          <td className="px-6 py-4">
                            <span className="bg-blue-50 text-blue-700 border border-blue-100 px-2.5 py-1 rounded-md text-xs font-semibold">
                              {champ.role}
                            </span>
                          </td>
                          <td className="px-6 py-4 text-slate-600">{champ.region}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* ... (Ontology and Alignment Tabs remain the same) ... */}
            {/* Tab Content: Ontology Schema */}
            {activeTab === "ontology" && (
              <div className="bg-white rounded-3xl border border-slate-200 shadow-sm overflow-hidden animate-in fade-in slide-in-from-bottom-4 duration-500">
                <div className="overflow-x-auto max-h-[600px] overflow-y-auto">
                  <table className="w-full text-left text-sm relative">
                    <thead className="bg-slate-50 text-slate-500 font-medium border-b border-slate-200 sticky top-0 z-10 shadow-sm">
                      <tr>
                        <th className="px-6 py-4">Property IRI</th>
                        <th className="px-6 py-4">Type</th>
                        <th className="px-6 py-4">Domain (Subject)</th>
                        <th className="px-6 py-4">Range (Object)</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {filteredSchema.map((item, i) => (
                        <tr key={i} className="hover:bg-slate-50/50 transition-colors">
                          <td className="px-6 py-4 font-mono text-xs">
                            <span className="text-slate-400">{item.prefix}</span>
                            <span className="text-blue-600 font-semibold">{item.name}</span>
                          </td>
                          <td className="px-6 py-4">
                            <span className={`px-2.5 py-1 rounded-md text-[11px] font-semibold uppercase tracking-wider border ${
                              item.type === "ObjectProperty" ? "bg-indigo-50 text-indigo-700 border-indigo-200" : "bg-emerald-50 text-emerald-700 border-emerald-200"
                            }`}>
                              {item.type}
                            </span>
                          </td>
                          <td className="px-6 py-4 text-slate-700 font-semibold">{item.domain}</td>
                          <td className="px-6 py-4 text-slate-500 font-mono text-xs">{item.range}</td>
                        </tr>
                      ))}
                      {filteredSchema.length === 0 && (
                        <tr>
                          <td colSpan={4} className="px-6 py-8 text-center text-slate-500">No properties match your search.</td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
              )}
              
            {/* Tab Content: Alignment */}
            {activeTab === "alignment" && (
              <div className="bg-white rounded-3xl border border-slate-200 shadow-sm overflow-hidden animate-in fade-in slide-in-from-bottom-4 duration-500">
                <div className="overflow-x-auto max-h-[600px] overflow-y-auto">
                  <table className="w-full text-left text-sm relative">
                    <thead className="bg-slate-50 text-slate-500 font-medium border-b border-slate-200 sticky top-0 z-10 shadow-sm">
                      <tr>
                        <th className="px-6 py-4 text-center">Wikidata Entity (Target)</th>
                        <th className="px-6 py-4 text-center">Champion Label</th>
                        <th className="px-6 py-4 text-center">Internal Entity (Source)</th>
                        <th className="px-6 py-4 text-center">Confidence</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {filteredAlignments.map((item, i) => {
                        // Fallbacks in case the CSV parsing failed
                        const displayLabel = item.label || item.entity?.split("/").at(-1).replace("_", " ") || "Unknown";
                        
                        return (
                          <tr key={i} className="hover:bg-red-50/30 transition-colors">
                            
                            {/* 1. WIKIDATA TARGET (MAIN METRIC IN RED) */}
                            <td className="px-6 py-4 font-mono">
                                {item.wdTarget === "Unlinked" ? (
                                  <span className="text-slate-400 italic font-sans text-xs">No Match Found</span>
                                ) : (
                                  <a 
                                    href={`https://www.wikidata.org/wiki/${item.wdProperty.split("/").at(-1)}`} 
                                    target="_blank" 
                                    rel="noopener noreferrer"
                                    className="flex items-center gap-1.5 px-6 py-4 font-mono text-xs text-slate-500"
                                  >
                                    <LinkIcon className="w-4 h-4" />
                                    {item.wdProperty}
                                  </a>
                                )}
                            </td>

                            {/* 2. CHAMPION LABEL & AVATAR */}
                            <td className="px-6 py-4 font-bold text-slate-900 flex items-center gap-3 mt-1">
                              <img 
                                src={`https://ddragon.leagueoflegends.com/cdn/16.6.1/img/champion/${getCleanName(displayLabel)}.png`}
                                alt={displayLabel}
                                className="w-8 h-8 rounded-full border border-slate-200 bg-slate-100 shadow-sm"
                                onError={(e) => { e.currentTarget.style.display = 'none'; }}
                              />
                              {displayLabel}
                            </td>

                            {/* 3. INTERNAL ENTITY */}
                            <td className="px-6 py-4 font-mono text-xs text-slate-500">{item.entity}</td>
                            
                            {/* 4. CONFIDENCE BADGE */}
                            <td className="px-6 py-4 text-center">
                              <span className={`px-3 py-1.5 rounded-full text-xs font-bold tracking-wide ${
                                item.wdTarget >= 0.9 ? "bg-emerald-100 text-emerald-700 border border-emerald-200" :
                                item.wdTarget > 0 ? "bg-amber-100 text-amber-700 border border-amber-200" :
                                "bg-slate-100 text-slate-500 border border-slate-200"
                              }`}>
                                {(item.wdTarget * 100).toFixed(0)}%
                              </span>
                            </td>
                            
                          </tr>
                        );
                      })}
                      {filteredAlignments.length === 0 && (
                        <tr>
                          <td colSpan={4} className="px-6 py-8 text-center text-slate-500">No alignments match your search.</td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </>
        )}
      </main>

      {/* NEW: CHAMPION MODAL OVERLAY */}
      {selectedChampion && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="bg-white w-full max-w-2xl max-h-[85vh] rounded-3xl shadow-2xl overflow-hidden flex flex-col animate-in zoom-in-95 duration-200">
            
            {/* Modal Header */}
            <div className="px-8 py-6 border-b border-slate-100 flex justify-between items-start bg-slate-50/50">
              <div className="flex items-center gap-6">
                {/* LARGE CHAMPION ICON */}
                <img 
                  src={`https://ddragon.leagueoflegends.com/cdn/16.6.1/img/champion/${getCleanName(selectedChampion.name)}.png`}
                  alt={selectedChampion.name}
                  className="w-20 h-20 md:w-24 md:h-24 rounded-2xl shadow-md border border-slate-200 bg-white"
                  onError={(e) => { e.currentTarget.style.display = 'none'; }}
                />
                <div>
                  <h2 className="text-3xl font-extrabold text-slate-900">{selectedChampion.name}</h2>
                  <p className="text-slate-500 font-medium capitalize text-lg">{selectedChampion.title}</p>
                  <div className="flex gap-2 mt-3">
                    <span className="bg-blue-100 text-blue-700 px-3 py-1 rounded-full text-xs font-bold tracking-wide uppercase">
                      {selectedChampion.role}
                    </span>
                    <span className="bg-slate-200 text-slate-700 px-3 py-1 rounded-full text-xs font-bold tracking-wide uppercase">
                      {selectedChampion.region}
                    </span>
                  </div>
                </div>
              </div>
              <button 
                onClick={() => setSelectedChampion(null)}
                className="p-2 bg-white border border-slate-200 rounded-full text-slate-400 hover:text-slate-900 hover:bg-slate-100 transition-colors shrink-0"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Modal Body (Scrollable) */}
            <div className="p-8 overflow-y-auto space-y-8">
              
              {/* Lore Section */}
              <section>
                <h3 className="text-sm font-bold text-slate-400 uppercase tracking-wider mb-3">Biography</h3>
                <p className="text-slate-700 leading-relaxed text-[15px] bg-slate-50 p-5 rounded-2xl border border-slate-100">
                  {selectedChampion.lore}
                </p>
              </section>

              {/* Spells Section */}
              {selectedChampion.spells && selectedChampion.spells.length > 0 && (
                <section>
                  <h3 className="flex items-center gap-2 text-sm font-bold text-slate-400 uppercase tracking-wider mb-4">
                    <Sparkles className="w-4 h-4 text-indigo-500" />
                    Abilities
                  </h3>
                  
                  {/* Changed to a 2-column grid for better readability */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {selectedChampion.spells.map((spell: any, idx: number) => {
                      // Riot's DDragon always returns spells in Q, W, E, R order
                      const spellSlots = ["Q", "W", "E", "R"];
                      
                      // Check if your backend passed a specific spellSlot, otherwise fallback to the index
                      const slot = spell.spellSlot || spellSlots[idx] || "?";

                      return (
                        <div key={idx} className="p-5 border border-slate-100 rounded-2xl hover:border-indigo-200 hover:bg-indigo-50/40 transition-all shadow-sm group">
                          
                          {/* Spell Header: Badge + Name */}
                          <div className="flex items-center gap-3 mb-3">
                            <img 
                              // Riot typically uses the internal spell ID for image names. If your JSON has 'id', it's safer. 
                              // Otherwise we fallback to the spell name with spaces removed.
                              src={`https://ddragon.leagueoflegends.com/cdn/16.6.1/img/spell/${spell.id || getCleanName(spell.name)}.png`} 
                              alt={spell.name}
                              className="w-10 h-10 rounded-xl shadow-sm border border-slate-200 bg-slate-100"
                              onError={(e) => { e.currentTarget.style.display = 'none'; }}
                            />
                            <span className="w-9 h-9 flex items-center justify-center bg-indigo-100 text-indigo-700 font-black rounded-xl text-sm shadow-inner group-hover:bg-indigo-600 group-hover:text-white transition-colors">
                              {slot}
                            </span>
                            <h4 className="font-bold text-slate-900 leading-tight">
                              {spell.name || "Unknown Spell"}
                            </h4>
                          </div>

                          {/* Cooldown Badge */}
                          <div className="mb-3">
                            <span className="text-[11px] font-mono bg-slate-100 px-2.5 py-1 rounded-md text-slate-500 uppercase tracking-wider font-semibold border border-slate-200">
                              Cooldown: {spell.cooldown_burn || "N/A"}
                            </span>
                          </div>

                          {/* Spell Description */}
                          <p className="text-sm text-slate-600 leading-relaxed">
                            {spell.description 
                              ? spell.description.replace(/<[^>]*>?/gm, '') // Strip Riot's raw HTML tags
                              : "No description available."}
                          </p>
                          
                        </div>
                      );
                    })}
                  </div>
                </section>
              )}

              {/* Base Stats Section */}
              {selectedChampion.stats && Object.keys(selectedChampion.stats).length > 0 && (
                <section>
                  <h3 className="flex items-center gap-2 text-sm font-bold text-slate-400 uppercase tracking-wider mb-4">
                    <Activity className="w-4 h-4 text-emerald-500" />
                    Base Stats
                  </h3>
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                    <div className="bg-slate-50 border border-slate-100 p-3 rounded-xl text-center">
                      <div className="text-xs text-slate-400 font-semibold mb-1">HP</div>
                      <div className="font-bold text-slate-800">{selectedChampion.stats.hp || "N/A"}</div>
                    </div>
                    <div className="bg-slate-50 border border-slate-100 p-3 rounded-xl text-center">
                      <div className="text-xs text-slate-400 font-semibold mb-1">Armor</div>
                      <div className="font-bold text-slate-800">{selectedChampion.stats.armor || "N/A"}</div>
                    </div>
                    <div className="bg-slate-50 border border-slate-100 p-3 rounded-xl text-center">
                      <div className="text-xs text-slate-400 font-semibold mb-1">Attack Damage</div>
                      <div className="font-bold text-slate-800">{selectedChampion.stats.attackdamage || "N/A"}</div>
                    </div>
                    <div className="bg-slate-50 border border-slate-100 p-3 rounded-xl text-center">
                      <div className="text-xs text-slate-400 font-semibold mb-1">Attack Range</div>
                      <div className="font-bold text-slate-800">{selectedChampion.stats.attackrange || "N/A"}</div>
                    </div>
                  </div>
                </section>
              )}
              
            </div>
          </div>
        </div>
      )}
    </div>
  );
}