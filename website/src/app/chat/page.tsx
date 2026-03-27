"use client";

import { useState, useRef, useEffect } from "react";
import { Send, Bot, User, Code2, Loader2, Info } from "lucide-react";

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
      content: "Hello! I am your League of Legends Knowledge Graph Assistant. What would you like to know?",
    }
  ]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [expandedSparql, setExpandedSparql] = useState<Record<string, boolean>>({});
  
  // Ref to track if auto-submit has already run to prevent duplicates
  const hasAutoSubmitted = useRef(false);
  // Ref for the scrollable container itself
  const scrollContainerRef = useRef<HTMLDivElement>(null);

  /**
   * Check for pre-written questions in the URL on mount
   */
  useEffect(() => {
    if (hasAutoSubmitted.current) return;
    
    const params = new URLSearchParams(window.location.search);
    const preWrittenQuestion = params.get("q");
    if (preWrittenQuestion) {
      hasAutoSubmitted.current = true;
      handleAutoSubmit(preWrittenQuestion);
    }
  }, []);

  /**
   * FIX: Manual Scroll Logic
   * Instead of scrollIntoView (which scrolls the whole window), 
   * we manually set the scrollTop of the message container.
   */
  const scrollToBottom = () => {
    if (scrollContainerRef.current) {
      const { scrollHeight, clientHeight } = scrollContainerRef.current;
      scrollContainerRef.current.scrollTo({
        top: scrollHeight - clientHeight,
        behavior: "smooth"
      });
    }
  };

  // Only auto-scroll when a NEW message arrives or while loading
  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  const toggleSparql = (id: string) => {
    setExpandedSparql(prev => ({ ...prev, [id]: !prev[id] }));
  };

  // Helper function to generate unique IDs
  const generateId = () => `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;

  // Helper function to handle submission logic for both manual and auto-submit
  const processQuery = async (queryText: string) => {
    if (!queryText.trim() || isLoading) return;

    const userMsg: Message = { id: generateId(), role: "user", content: queryText };
    setMessages((prev) => [...prev, userMsg]);
    setIsLoading(true);

    try {
      const response = await fetch("http://localhost:8000/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ 
          message: queryText
        })
      });
      
      const data = await response.json();

      if (!response.ok) {
        if (response.status === 429) {
          setMessages(prev => [...prev, {
            id: generateId(),
            role: "system",
            content: data.detail || "Request limit reached. Please try again later."
          }]);
        } else {
          throw new Error(data.detail || "An error occurred.");
        }
        setIsLoading(false);
        return;
      }

      const botMsg: Message = {
        id: generateId(),
        role: "assistant",
        content: data.content,
        sparql: data.sparql
      };
      
      setMessages((prev) => [...prev, botMsg]);
    } catch (error: any) {
      setMessages(prev => [...prev, {
        id: generateId(),
        role: "system",
        content: `Error: ${error.message}.`
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const query = input;
    setInput("");
    await processQuery(query);
  };

  const handleAutoSubmit = async (query: string) => {
    // Small delay to ensure the UI is ready
    setTimeout(() => {
      processQuery(query);
    }, 500);
  };

  return (
    /* Container fits the viewport minus the navbar. 
      Using 'h-[calc(100vh-4rem)]' and 'overflow-hidden' prevents the body from scrolling.
    */
    <div className="flex flex-col h-[calc(100vh-4rem)] bg-slate-50 text-slate-900 overflow-hidden">
      
      {/* Fixed Header */}
      <header className="bg-white border-b border-slate-200 px-6 py-4 flex flex-col sm:flex-row items-start sm:items-center justify-between z-10 shadow-sm gap-4 flex-shrink-0">
        <div className="flex items-center gap-3">
          <div className="bg-blue-100 p-2 rounded-xl text-blue-600">
            <Bot className="w-5 h-5" />
          </div>
          <div>
            <h1 className="font-bold text-lg leading-tight">LoL Graph Assistant</h1>
            <p className="text-xs text-slate-500 font-medium">Powered by Cloud LLM Architecture</p>
          </div>
        </div>
      </header>

      {/* INTERNAL SCROLL AREA:
          We use 'ref={scrollContainerRef}' to target this specific div for scrolling.
      */}
      <main 
        ref={scrollContainerRef}
        className="flex-1 overflow-y-auto w-full scroll-smooth bg-slate-50/50"
      >
        <div className="max-w-4xl mx-auto p-4 md:p-6 space-y-6">
          {messages.map((msg) => (
            <div key={msg.id} className={`flex gap-4 ${msg.role === "user" ? "flex-row-reverse" : "flex-row"} animate-in fade-in slide-in-from-bottom-2 duration-300`}>
              <div className={`flex-shrink-0 w-10 h-10 rounded-full flex items-center justify-center shadow-sm ${
                msg.role === "user" ? "bg-slate-900 text-white" : 
                msg.role === "system" ? "bg-red-100 text-red-600 border border-red-200" :
                "bg-white border border-slate-200 text-blue-600"
              }`}>
                {msg.role === "user" ? <User className="w-5 h-5" /> : 
                 msg.role === "system" ? <Info className="w-5 h-5" /> : 
                 <Bot className="w-5 h-5" />}
              </div>

              <div className={`flex flex-col max-w-[80%] ${msg.role === "user" ? "items-end" : "items-start"}`}>
                <div className={`px-5 py-3.5 rounded-2xl shadow-sm text-[15px] leading-relaxed ${
                  msg.role === "user" ? "bg-slate-900 text-white rounded-tr-none" : 
                  msg.role === "system" ? "bg-red-50 border border-red-100 text-red-700 rounded-tl-none font-medium" :
                  "bg-white border border-slate-200 text-slate-800 rounded-tl-none"
                }`}>
                  {msg.content}
                </div>

                {msg.sparql && msg.sparql !== "No SPARQL query generated." && (
                  <div className="mt-2 w-full">
                    <button 
                      onClick={() => toggleSparql(msg.id)}
                      className="flex items-center gap-1.5 text-xs font-semibold text-slate-500 hover:text-blue-600 transition-colors bg-white border border-slate-200 shadow-sm px-3 py-1.5 rounded-full"
                    >
                      <Code2 className="w-3.5 h-3.5" />
                      {expandedSparql[msg.id] ? "Hide SPARQL Query" : "Show SPARQL Query"}
                    </button>
                    {expandedSparql[msg.id] && (
                      <div className="mt-2 bg-slate-900 rounded-xl p-4 overflow-x-auto shadow-inner relative group animate-in zoom-in-95 duration-200">
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
            <div className="flex gap-4 animate-pulse">
              <div className="flex-shrink-0 w-10 h-10 rounded-full bg-white border border-slate-200 text-blue-600 flex items-center justify-center shadow-sm">
                <Bot className="w-5 h-5" />
              </div>
              <div className="bg-white border border-slate-200 px-5 py-4 rounded-2xl rounded-tl-none shadow-sm flex items-center gap-2 text-slate-500 text-sm">
                <Loader2 className="w-4 h-4 animate-spin" />
                Consulting the knowledge graph...
              </div>
            </div>
          )}
          {/* Bottom padding to ensure the last message isn't tight against the edge */}
          <div className="h-4" />
        </div>
      </main>

      {/* Fixed Input Bar */}
      <div className="bg-white border-t border-slate-200 p-4 flex-shrink-0">
        <div className="max-w-4xl mx-auto relative">
          <form onSubmit={handleSubmit} className="relative flex items-end gap-2">
            <div className="relative w-full">
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Ask about champions, lore, or Wikidata connections..."
                className="w-full bg-slate-50 border border-slate-200 rounded-2xl py-4 pl-5 pr-14 outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all text-slate-800 placeholder:text-slate-400 shadow-inner"
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
          <div className="text-center mt-2 flex items-center justify-center gap-1.5 text-[10px] text-slate-400 uppercase tracking-widest font-bold">
            <Info className="w-3 h-3" />
            <span>Fact-checked via RDF Graph</span>
          </div>
        </div>
      </div>

    </div>
  );
}