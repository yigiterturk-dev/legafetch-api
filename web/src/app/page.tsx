"use client";

import { API_PROXY } from "@/lib/api";

import React, { useState, useRef, useEffect } from 'react';

type SourceMeta = {
  source: string;
  authority_score: number;
  jurisdiction: string;
};

type Message = {
  id: string;
  sender: 'user' | 'system';
  text: string;
  sources?: SourceMeta[];
  isTyping?: boolean;
};

export default function Home() {
  const [jurisdiction, setJurisdiction] = useState('global');
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      sender: 'user',
      text: "Anonim şirket asgari sermaye şartları nelerdir?"
    },
    {
      id: '2',
      sender: 'system',
      text: "Türkiye'de anonim şirket (A.Ş.) kurmak için asgari sermaye tutarı 250.000 TL'dir. Kurumlar vergisi genel oranı %25'tir.",
      sources: [{ source: "TTK Madde 332", authority_score: 98, jurisdiction: "TR" }]
    }
  ]);
  
  const [inputValue, setInputValue] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputValue.trim()) return;

    const currentInput = inputValue;
    setMessages(prev => [...prev, { id: Math.random().toString(), sender: 'user', text: currentInput }]);
    setInputValue('');

    const typingId = Math.random().toString();
    setMessages(prev => [...prev, { id: typingId, sender: 'system', text: "", isTyping: true }]);

    try {
      const response = await fetch(`${API_PROXY}/chat`, {
        method: "POST",
        headers: { 
          "Content-Type": "application/json"
        },
        body: JSON.stringify({ query: currentInput, jurisdiction: jurisdiction }),
      });
      const data = await response.json();

      setMessages(prev => prev.map(msg => {
        if (msg.id === typingId) {
          return {
            id: typingId,
            sender: 'system',
            text: data.text ? data.text.replace("Arama tamamlandı. Bulunan kritik pasajlar:\n\n", "") : "Bilinmeyen bir hata oluştu.",
            sources: data.sources || []
          };
        }
        return msg;
      }));
    } catch (error) {
      setMessages(prev => prev.map(msg => {
        if (msg.id === typingId) return { id: typingId, sender: 'system', text: "Error: Could not connect to API." };
        return msg;
      }));
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
       const file = e.target.files[0];
       
       const loadingId = Math.random().toString();
       setMessages(prev => [...prev, { 
         id: Math.random().toString(), 
         sender: 'user', 
         text: `[DOSYA YÜKLENDİ] ${file.name} - Sözleşme analizi başlatılıyor...`
       }]);
       
       setMessages(prev => [...prev, {
         id: loadingId,
         sender: 'system',
         text: "",
         isTyping: true
       }]);

       const formData = new FormData();
       formData.append("file", file);

       try {
         const response = await fetch(`${API_PROXY}/analyze-contract`, {
           method: "POST",
           body: formData
         });
         
         const data = await response.json();
         
         setMessages(prev => prev.map(msg => {
           if (msg.id === loadingId) {
             return {
               id: loadingId,
               sender: 'system',
               text: `DAVA/SÖZLEŞME ANALİZ RAPORU:\n\n${data.analysis}`,
               sources: data.sources || []
             };
           }
           return msg;
         }));
       } catch (error) {
         setMessages(prev => prev.map(msg => {
           if (msg.id === loadingId) {
             return { id: loadingId, sender: 'system', text: "Hata: Sunucuya bağlanılamadı veya analiz başarısız." };
           }
           return msg;
         }));
       }
    }
  }

  return (
    <div className="container">
      <header className="header">
        <div className="logo">LegaFetch</div>
        <nav style={{ display: 'flex', gap: '2rem', alignItems: 'center' }}>
          <a href="/infrastructure" style={{ color: '#94a3b8', textDecoration: 'none', fontSize: '0.9rem' }}>Infrastructure</a>
          <a href="/documentation" style={{ color: '#94a3b8', textDecoration: 'none', fontSize: '0.9rem' }}>Documentation</a>
          <a href="/admin" style={{ color: '#d4af37', textDecoration: 'none', fontSize: '0.9rem', fontWeight: 'bold' }}>Admin Dashboard</a>
          <a href="/#console" className="btn btn-secondary">Console Access</a>
        </nav>
      </header>
      
      <main>
        <section className="hero">
          <div style={{ maxWidth: '800px' }}>
            <div style={{ display: 'inline-flex', alignItems: 'center', gap: '0.5rem', border: '1px solid #27272a', padding: '0.25rem 0.75rem', borderRadius: '4px', fontSize: '0.8rem', color: '#94a3b8', marginBottom: '2rem', fontFamily: 'JetBrains Mono, monospace' }}>
              <span style={{ width: '8px', height: '8px', background: '#10b981', borderRadius: '50%' }}></span>
              Multi-Lingual Engine Active
            </div>
            <h1>Enterprise Legal Data Infrastructure</h1>
            <p className="subtitle" style={{ marginTop: '1.5rem' }}>
              High-performance semantic search and automated contract analysis. Built on an air-gapped vector architecture for absolute data sovereignty.
            </p>
          </div>

          <div id="console" className="console-window fade-in" style={{ animationDelay: '0.2s' }}>
            <div className="console-header" style={{ justifyContent: 'space-between' }}>
              <div style={{ display: 'flex', gap: '1rem' }}>
                <span>Terminal</span>
                <span style={{ color: '#3f3f46' }}>|</span>
                <span>Latency: 18ms</span>
              </div>
              <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
                <span style={{ color: '#3f3f46' }}>Jurisdiction:</span>
                <select 
                  value={jurisdiction} 
                  onChange={(e) => setJurisdiction(e.target.value)}
                  style={{ background: 'transparent', color: '#10b981', border: 'none', outline: 'none', fontFamily: 'JetBrains Mono, monospace', fontSize: '0.85rem', cursor: 'pointer' }}
                >
                  <option value="global">Global (All)</option>
                  <option value="TR">Turkey (TR)</option>
                  <option value="ES">Spain (ES)</option>
                </select>
                <button 
                  onClick={() => { setInputValue("Türkiye'deki şirketimi İspanya'ya taşırsam vergi avantajım ne olur?"); setJurisdiction("ES"); }}
                  style={{ background: 'linear-gradient(90deg, #d4af37 0%, #b8860b 100%)', color: '#000', border: 'none', padding: '4px 12px', borderRadius: '4px', fontSize: '0.75rem', fontWeight: 600, cursor: 'pointer' }}
                >
                  🇪🇸 Golden Visa Advisor
                </button>
              </div>
            </div>

            <div className="console-body">
              <div style={{ flexGrow: 1, display: 'flex', flexDirection: 'column', gap: '1.5rem', overflowY: 'auto' }}>
                {messages.map((msg) => (
                  <div key={msg.id} style={{ alignSelf: msg.sender === 'user' ? 'flex-end' : 'flex-start', maxWidth: '85%' }}>
                    {msg.sender === 'user' ? (
                      <div style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '0.9rem', color: '#94a3b8', textAlign: 'right' }}>
                        &gt; {msg.text}
                      </div>
                    ) : (
                      <div className="data-result">
                        {msg.isTyping ? (
                          <div style={{ display: 'flex', gap: '4px', alignItems: 'center', height: '20px' }}>
                            <span className="dot-typing"></span><span className="dot-typing" style={{ animationDelay: '0.2s' }}></span><span className="dot-typing" style={{ animationDelay: '0.4s' }}></span>
                          </div>
                        ) : (
                          <>
                            <div style={{ whiteSpace: 'pre-wrap', color: '#e2e8f0', lineHeight: 1.7 }}>{msg.text}</div>
                            {msg.sources && (
                              <div style={{ marginTop: '1.5rem', display: 'flex', flexWrap: 'wrap', gap: '0.75rem' }}>
                                {msg.sources.map((src, idx) => (
                                  <div key={idx} className="data-source" style={{ display: 'inline-flex', alignItems: 'center', gap: '0.75rem', padding: '0.5rem 0.75rem', border: '1px solid #27272a', background: '#0f0f11' }}>
                                    <span style={{ color: '#94a3b8' }}>{src.source}</span>
                                    <span style={{ borderLeft: '1px solid #27272a', paddingLeft: '0.75rem', color: src.authority_score > 90 ? '#10b981' : '#eab308', fontWeight: 600 }}>
                                      Auth: {src.authority_score}/100
                                    </span>
                                    <span style={{ background: '#27272a', padding: '2px 6px', borderRadius: '4px', fontSize: '0.65rem' }}>{src.jurisdiction}</span>
                                  </div>
                                ))}
                              </div>
                            )}
                          </>
                        )}
                      </div>
                    )}
                  </div>
                ))}
                <div ref={messagesEndRef} />
              </div>
            </div>

            <div className="console-input-area" style={{ display: 'flex', alignItems: 'center' }}>
              <form onSubmit={handleSubmit} style={{ display: 'flex', gap: '1rem', width: '100%' }}>
                <input 
                  type="text" 
                  value={inputValue}
                  onChange={(e) => setInputValue(e.target.value)}
                  placeholder="Enter query or type..."
                  className="console-input"
                />
                
                <label style={{ cursor: 'pointer', background: '#27272a', padding: '0.875rem 1rem', borderRadius: '6px', color: '#f8fafc', display: 'flex', alignItems: 'center', border: '1px solid #3f3f46' }}>
                  <input type="file" style={{ display: 'none' }} accept=".pdf,.doc,.txt" onChange={handleFileUpload} />
                  📎 Analyze Contract
                </label>
                
                <button type="submit" className="btn btn-primary" disabled={!inputValue.trim()}>
                  Execute
                </button>
              </form>
            </div>
          </div>
        </section>

        <section id="infrastructure" className="features">
          <div className="grid-3">
             <div className="feature-block">
              <h3>Cross-Lingual Engine</h3>
              <p>Search in Turkish, retrieve Spanish corporate law. The embedding layer uses multi-lingual transformer models to map legal concepts across languages.</p>
            </div>
            <div className="feature-block">
              <h3>Authority Scoring</h3>
              <p>Not all laws are equal. Results are ranked by their "Citation Graph", showing you exactly how authoritative a statute or case law is.</p>
            </div>
            <div className="feature-block">
              <h3>Automated Contract Analysis</h3>
              <p>Upload a contract and let the semantic engine cross-reference its clauses with millions of statutory requirements in seconds.</p>
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}
