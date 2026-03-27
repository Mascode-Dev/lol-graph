// website/src/components/Navbar.tsx
"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Network, MessageSquare, Database, BookOpen } from "lucide-react";

export default function Navbar() {
  const pathname = usePathname();

  const navLinks = [
    { name: "Assistant", href: "/chat", icon: MessageSquare },
    { name: "Explorer", href: "/explore", icon: Database },
    { name: "Methodology", href: "/about", icon: BookOpen },
  ];

  return (
    <nav className="fixed top-0 w-full z-50 bg-white/80 backdrop-blur-md border-b border-slate-200 shadow-sm">
      <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
        
        {/* Logo */}
        <Link href="/" className="flex items-center gap-2 font-bold text-xl tracking-tight group">
          <div className="bg-blue-600 text-white p-1.5 rounded-lg group-hover:bg-blue-700 transition-colors">
            <Network className="w-5 h-5" />
          </div>
          <span className="text-slate-900">LoL Graph</span>
        </Link>

        {/* Navigation Links */}
        <div className="flex items-center gap-1 md:gap-4">
          {navLinks.map((link) => {
            const isActive = pathname === link.href;
            const Icon = link.icon;
            
            return (
              <Link 
                key={link.name} 
                href={link.href}
                className={`flex items-center gap-2 px-3 py-2 md:px-4 md:py-2 rounded-full text-sm font-semibold transition-all ${
                  isActive 
                    ? "bg-slate-900 text-white shadow-md" 
                    : "text-slate-500 hover:text-slate-900 hover:bg-slate-100"
                }`}
              >
                <Icon className={`w-4 h-4 ${isActive ? "text-blue-400" : ""}`} />
                <span className="hidden sm:inline">{link.name}</span>
              </Link>
            );
          })}
        </div>

      </div>
    </nav>
  );
}