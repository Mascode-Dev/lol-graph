"use client";

import { useState, useRef, useEffect } from "react";
import { Send, Bot, User, Code2, Loader2, Info, Key } from "lucide-react";

type Message = {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  sparql?: string;
};

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "welcome",
      role: "assistant",
      content: "Hello! I am your League of Legends Knowledge Graph Assistant. You have 3 free requests. What would you like to know?",
    }
  ]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [expandedSparql, setExpandedSparql] = useState<Record<string, boolean>>({});
  
  // BYOK (Bring Your Own Key) State
  const [apiKey, setApiKey] = useState("");
  const [showKeyInput, setShowKeyInput] = useState(false);
  
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Load the API key from local storage when the page loads
  useEffect(() => {
    const savedKey = localStorage.getItem("groq_api_key");
    if (savedKey) setApiKey(savedKey);
  }, []);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };
  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  const toggleSparql = (id: string) => {
    setExpandedSparql(prev => ({ ...prev, [id]: !prev[id] }));
  };

  // Save key to local storage
  const handleSaveKey = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    setApiKey(val);
    localStorage.setItem("groq_api_key", val);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMsg: Message = { id: Date.now().toString(), role: "user", content: input };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setIsLoading(true);

    try {
      const response = await fetch("http://localhost:8000/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ 
          message: input,
          api_key: apiKey // Pass the key to the backend!
        })
      });
      
      const data = await response.json();

      // Handle the Rate Limit Error (429) from FastAPI
      if (!response.ok) {
        if (response.status === 429) {
          setMessages(prev => [...prev, {
            id: Date.now().toString(),
            role: "system",
            content: data.detail || "Free trial limit reached. Please enter your Groq API Key by clicking the key icon at the top right."
          }]);
          setShowKeyInput(true); // Automatically open the key input for them!
        } else {
          throw new Error(data.detail || "An error occurred.");
        }
        setIsLoading(false);
        return;
      }

      const botMsg: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: data.content,
        sparql: data.sparql
      };
      
      setMessages((prev) => [...prev, botMsg]);
    } catch (error: any) {
      setMessages(prev => [...prev, {
        id: Date.now().toString(),
        role: "system",
        content: `Error: ${error.message}. If you entered a key, ensure it is valid.`
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col min-h-[calc(100vh-4rem)] bg-slate-50 text-slate-900">
      
      {/* Header with API Key Toggle */}
      <header className="bg-white border-b border-slate-200 px-6 py-4 flex flex-col sm:flex-row items-start sm:items-center justify-between sticky top-0 z-10 shadow-sm gap-4">
        <div className="flex items-center gap-3">
          <div className="bg-blue-100 p-2 rounded-xl text-blue-600">
            <Bot className="w-5 h-5" />
          </div>
          <div>
            <h1 className="font-bold text-lg leading-tight">LoL Graph Assistant</h1>
            <p className="text-xs text-slate-500 font-medium">Powered by Groq & LLaMA 3</p>
          </div>
        </div>

        {/* API Key Input Area */}
        <div className="flex items-center gap-2 w-full sm:w-auto">
          {showKeyInput && (
            <input 
              type="password"
              placeholder="gsk_..."
              value={apiKey}
              onChange={handleSaveKey}
              className="px-3 py-1.5 text-sm bg-slate-50 border border-slate-200 rounded-lg outline-none focus:ring-2 focus:ring-blue-500 w-full sm:w-48 font-mono"
            />
          )}
          <button 
            onClick={() => setShowKeyInput(!showKeyInput)}
            className={`p-2 rounded-xl transition-colors border shadow-sm ${
              apiKey ? "bg-emerald-50 text-emerald-600 border-emerald-200 hover:bg-emerald-100" : "bg-white text-slate-400 border-slate-200 hover:text-slate-900 hover:bg-slate-50"
            }`}
            title={apiKey ? "API Key Active" : "Add Groq API Key"}
          >
            <Key className="w-5 h-5" />
          </button>
        </div>
      </header>

      {/* Chat Area */}
      <main className="flex-1 overflow-y-auto w-full max-w-4xl mx-auto p-4 md:p-6 space-y-6">
        {messages.map((msg) => (
          <div key={msg.id} className={`flex gap-4 ${msg.role === "user" ? "flex-row-reverse" : "flex-row"}`}>
            
            {/* Avatar */}
            <div className={`flex-shrink-0 w-10 h-10 rounded-full flex items-center justify-center shadow-sm ${
              msg.role === "user" ? "bg-slate-900 text-white" : 
              msg.role === "system" ? "bg-red-100 text-red-600 border border-red-200" :
              "bg-white border border-slate-200 text-blue-600"
            }`}>
              {msg.role === "user" ? <User className="w-5 h-5" /> : 
               msg.role === "system" ? <Info className="w-5 h-5" /> : 
               <Bot className="w-5 h-5" />}
            </div>

            {/* Message Content */}
            <div className={`flex flex-col max-w-[80%] ${msg.role === "user" ? "items-end" : "items-start"}`}>
              <div className={`px-5 py-3.5 rounded-2xl shadow-sm text-[15px] leading-relaxed ${
                msg.role === "user" ? "bg-slate-900 text-white rounded-tr-none" : 
                msg.role === "system" ? "bg-red-50 border border-red-100 text-red-700 rounded-tl-none font-medium" :
                "bg-white border border-slate-200 text-slate-800 rounded-tl-none"
              }`}>
                {msg.content}
              </div>

              {/* SPARQL Toggle */}
              {msg.sparql && msg.sparql !== "No SPARQL query generated." && (
                <div className="mt-2 w-full">
                  <button 
                    onClick={() => toggleSparql(msg.id)}
                    className="flex items-center gap-1.5 text-xs font-semibold text-slate-500 hover:text-blue-600 transition-colors bg-slate-100 hover:bg-blue-50 px-3 py-1.5 rounded-full"
                  >
                    <Code2 className="w-3.5 h-3.5" />
                    {expandedSparql[msg.id] ? "Hide SPARQL Query" : "Show SPARQL Query"}
                  </button>
                  {expandedSparql[msg.id] && (
                    <div className="mt-2 bg-slate-900 rounded-xl p-4 overflow-x-auto shadow-inner relative group">
                      <div className="absolute top-3 right-3 text-slate-500 text-xs font-mono uppercase tracking-wider">SPARQL</div>
                      <pre className="text-sm font-mono text-emerald-400">
                        <code>{msg.sparql}</code>
                      </pre>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        ))}

        {isLoading && (
          <div className="flex gap-4">
            <div className="flex-shrink-0 w-10 h-10 rounded-full bg-white border border-slate-200 text-blue-600 flex items-center justify-center shadow-sm">
              <Bot className="w-5 h-5" />
            </div>
            <div className="bg-white border border-slate-200 px-5 py-4 rounded-2xl rounded-tl-none shadow-sm flex items-center gap-2 text-slate-500 text-sm">
              <Loader2 className="w-4 h-4 animate-spin" />
              Consulting the knowledge graph...
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </main>

      {/* Input Area */}
      <div className="bg-white border-t border-slate-200 p-4 sticky bottom-0">
        <div className="max-w-4xl mx-auto relative">
          <form onSubmit={handleSubmit} className="relative flex items-end gap-2">
            <div className="relative w-full">
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Ask about champions, lore, or Wikidata connections..."
                className="w-full bg-slate-50 border border-slate-200 rounded-2xl py-4 pl-5 pr-14 outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all text-slate-800 placeholder:text-slate-400"
                disabled={isLoading}
              />
              <div className="absolute right-3 top-1/2 -translate-y-1/2">
                <button
                  type="submit"
                  disabled={!input.trim() || isLoading}
                  className="bg-blue-600 text-white p-2 rounded-xl hover:bg-blue-700 disabled:opacity-50 disabled:hover:bg-blue-600 transition-colors shadow-sm"
                >
                  <Send className="w-4 h-4" />
                </button>
              </div>
            </div>
          </form>
          <div className="text-center mt-3 flex items-center justify-center gap-1.5 text-xs text-slate-400">
            <Info className="w-3 h-3" />
            <span>AI can make mistakes. Verify information against the raw KG data.</span>
          </div>
        </div>
      </div>

    </div>
  );
}