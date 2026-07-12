'use client';

import { useRouter } from 'next/navigation';
import { useState, useRef, useEffect } from 'react';
import { Paperclip, ImageIcon, Mic } from 'lucide-react';
import ReactMarkdown from 'react-markdown';

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';

const LOADING_STEPS = [
  'Parsing patient symptoms...',
  'BM25 sparse retrieval...',
  'Vector semantic retrieval...',
  'RRF fusion & reranking...',
  'Building dynamic few-shot prompt...',
  'DeepSeek LLM generation...',
];

interface FormulaItem {
  id: string;
  name: string;
  syndrome: string;
  symptoms: string;
  effects: string;
  ingredients: string;
  notes: string;
  category: string;
  source: string;
  similarity_score: number;
  hybrid_score?: number;
  vector_rank?: number;
  bm25_rank?: number;
}

interface FewshotItem extends FormulaItem {
  example_case: string;
}

interface AnalyzeResult {
  query: string;
  analysis: string;
  retrieved: FormulaItem[];
  fewshot: FewshotItem[];
  pipeline_steps: string[];
}

export default function WorkspacePage() {
  const router = useRouter();
  const videoRef = useRef<HTMLVideoElement>(null);
  const [input, setInput] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);
  const [results, setResults] = useState<AnalyzeResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState('similar cases');

  useEffect(() => {
    if (videoRef.current) videoRef.current.playbackRate = 1;
  }, []);

  const handleGenerate = async () => {
    if (!input.trim()) return;
    setLoadingStep(0);
    setIsGenerating(true);
    setError(null);
    setResults(null);
    try {
      const res = await fetch(`${API_BASE}/analyze`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: input.trim(), top_k: 5 }),
      });
      if (!res.ok) {
        const detail = await res.json().catch(() => ({}));
        throw new Error(detail?.detail || `Server error ${res.status}`);
      }
      const data: AnalyzeResult = await res.json();
      setResults(data);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Unknown error');
    } finally {
      setIsGenerating(false);
    }
  };
  const [loadingStep, setLoadingStep] = useState(0);

  useEffect(() => {
    if (!isGenerating) return;
    const interval = setInterval(() => {
      setLoadingStep((s) => Math.min(s + 1, LOADING_STEPS.length - 1));
    }, 1800);
    return () => clearInterval(interval);
  }, [isGenerating]);

  const hasContent = results !== null || isGenerating || error !== null;

  return (
    <div style={{ position: 'relative', minHeight: '100vh', color: '#F5F5F5' }}>

      {/* Background Video */}
      <div style={{ position: 'fixed', top: 0, left: 0, width: '100%', height: '100%', zIndex: 0, overflow: 'hidden' }}>
        <video ref={videoRef} autoPlay muted loop playsInline
          style={{ width: '100%', height: '100%', objectFit: 'cover', position: 'absolute', top: 0, left: 0 }}>
          <source src="/images/workspace-bg2.mp4" type="video/mp4" />
        </video>
        {/* Darken overlay */}
        <div style={{ position: 'absolute', top: 0, left: 0, width: '100%', height: '100%', background: 'rgba(0,0,0,0.45)' }} />
      </div>

      {/* Sliding content layer */}
      <div className="page-slide" style={{ position: 'relative', zIndex: 1, minHeight: '100vh' }}>

        {/* Top Nav — logo left, home button right */}
        <nav style={{
          position: 'fixed', top: 0, left: 0, right: 0, height: '60px',
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          paddingLeft: '32px', paddingRight: '32px',
          background: 'rgba(0,0,0,0.15)', backdropFilter: 'blur(8px)',
          zIndex: 100,
        }}>
          {/* Return home CTA */}
          <button onClick={() => router.push('/')} className="btn-nav">
            ← Home
          </button>
        </nav>

        {/* Hero input area — centered when no results */}
        <div style={{
          display: 'flex', flexDirection: 'column', alignItems: 'center',
          justifyContent: hasContent ? 'flex-start' : 'center',
          minHeight: '100vh',
          paddingTop: hasContent ? '100px' : '0',
          transition: 'padding-top 0.4s ease',
        }}>

          {/* Title — hidden after first generation */}
          {!hasContent && (
            <div className="anim-fade-up delay-0" style={{ textAlign: 'center', marginBottom: '40px' }}>
              <h1 style={{
                fontSize: '2rem', fontWeight: '400', lineHeight: '1.2',
                marginBottom: '12px', color: '#F5F5F5',
              }}>
                TCM Insomnia{' '}
                <span style={{ fontFamily: "'Playfair Display', Georgia, serif", color: '#EFE58B' }}>
                  Prescription Assistant
                </span>
              </h1>
              <p style={{ fontSize: '0.9rem', color: 'rgba(255,255,255,0.55)', letterSpacing: '0.3px' }}>
                Enter patient symptoms to get traceable prescription assistance
              </p>
            </div>
          )}

          {/* Input card */}
          <div className={!hasContent ? 'anim-fade-up delay-1' : ''} style={{
            width: '100%', maxWidth: '680px',
            paddingLeft: '24px', paddingRight: '24px',
            marginBottom: hasContent ? '40px' : '0',
          }}>
            {/* Outer glass container */}
            <div style={{
              background: 'rgba(255,255,255,0.08)',
              backdropFilter: 'blur(24px)',
              WebkitBackdropFilter: 'blur(24px)',
              borderRadius: '20px',
              border: '1px solid rgba(255,255,255,0.15)',
              padding: '12px',
              boxShadow: '0 8px 40px rgba(0,0,0,0.3)',
            }}>
              {/* Inner white input box — text area only */}
              <div style={{
                background: 'rgba(255,255,255,0.95)',
                borderRadius: '12px',
                padding: '12px 16px',
              }}>
                <textarea
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  placeholder="Enter patient information: chief complaint, sleep symptoms, tongue, pulse..."
                  onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleGenerate(); }}}
                  style={{
                    width: '100%', background: 'transparent', border: 'none', outline: 'none',
                    resize: 'none', fontSize: '0.95rem', lineHeight: '1.6',
                    color: '#1A1A1A', fontFamily: 'var(--font-sans)',
                    minHeight: '44px', maxHeight: '160px',
                    display: 'block',
                  }}
                  rows={2}
                  disabled={isGenerating}
                />
              </div> {/* end inner white box */}

              {/* Bottom row inside glass but outside white box */}
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: '10px', paddingLeft: '4px', paddingRight: '4px' }}>
                <div style={{ display: 'flex', gap: '4px' }}>
                  {[
                    { icon: <Paperclip size={15} />, label: 'File' },
                    { icon: <ImageIcon size={15} />, label: 'Image' },
                    { icon: <Mic size={15} />, label: 'Voice' },
                  ].map(({ icon, label }) => (
                    <button key={label} title={label} style={{
                      background: 'rgba(255,255,255,0.12)', border: '1px solid rgba(255,255,255,0.2)',
                      borderRadius: '8px', padding: '5px 10px',
                      fontSize: '0.78rem', cursor: 'pointer', color: 'rgba(255,255,255,0.75)',
                      transition: 'all 0.15s', display: 'flex', alignItems: 'center', gap: '5px',
                    }}
                    onMouseEnter={(e) => { e.currentTarget.style.background = 'rgba(255,255,255,0.2)'; }}
                    onMouseLeave={(e) => { e.currentTarget.style.background = 'rgba(255,255,255,0.12)'; }}
                    >
                      {icon}
                      {label}
                    </button>
                  ))}
                </div>
                <button
                  onClick={handleGenerate}
                  disabled={!input.trim() || isGenerating}
                  style={{
                    background: input.trim() && !isGenerating ? '#4A9B8E' : 'rgba(255,255,255,0.15)',
                    color: input.trim() && !isGenerating ? '#fff' : 'rgba(255,255,255,0.35)',
                    border: 'none', borderRadius: '10px',
                    padding: '8px 20px', fontSize: '0.88rem', fontWeight: '600',
                    cursor: input.trim() && !isGenerating ? 'pointer' : 'default',
                    transition: 'all 0.2s', flexShrink: 0,
                  }}
                >
                  {isGenerating ? 'Generating...' : 'Generate'}
                </button>
              </div> {/* end bottom row */}
            </div> {/* end glass container */}
          </div>

          {/* Results area — appears below input after generation */}
          {hasContent && (
            <div style={{ width: '100%', maxWidth: '680px', paddingLeft: '24px', paddingRight: '24px', paddingBottom: '60px' }}>

              {/* Error */}
              {error && (
                <div style={{
                  background: 'rgba(180,40,40,0.15)', border: '1px solid rgba(180,40,40,0.35)',
                  borderRadius: '14px', padding: '16px 20px', marginBottom: '16px',
                }}>
                  <p style={{ fontSize: '0.85rem', color: '#F87171' }}>
                    Connection error: {error}. Make sure the backend is running at {API_BASE}.
                  </p>
                </div>
              )}

              {/* Loading */}
              {isGenerating && (
                <div style={{
                  background: 'rgba(0,0,0,0.2)', backdropFilter: 'blur(12px)',
                  border: '1px solid rgba(74,155,142,0.2)', borderRadius: '16px',
                  padding: '18px 20px', marginBottom: '16px',
                }}>
                  <p style={{ fontSize: '0.82rem', color: '#B0B0B0', marginBottom: '12px', fontWeight: '600' }}>Running RAG Pipeline</p>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                    {LOADING_STEPS.map((step, idx) => (
                      <div key={idx} style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <span style={{
                          fontSize: '0.72rem', fontWeight: '700', minWidth: '18px',
                          color: idx < loadingStep ? '#4A9B8E' : idx === loadingStep ? '#EFE58B' : 'rgba(255,255,255,0.2)',
                        }}>
                          {idx < loadingStep ? '✓' : idx === loadingStep ? '▶' : '○'}
                        </span>
                        <span style={{
                          fontSize: '0.8rem',
                          color: idx < loadingStep ? '#6EC5B8' : idx === loadingStep ? '#EFE58B' : 'rgba(255,255,255,0.25)',
                          transition: 'color 0.4s',
                        }}>{step}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Analysis result card */}
              {results && !isGenerating && (
                <div style={{
                  background: 'rgba(0,0,0,0.2)', backdropFilter: 'blur(16px)',
                  border: '1px solid rgba(100,60,20,0.2)', borderRadius: '20px',
                  overflow: 'hidden', display: 'flex', marginBottom: '16px',
                }}>
                  <div style={{ width: '5px', background: 'linear-gradient(180deg,#EFE58B,#643C14)', flexShrink: 0 }} />
                  <div style={{ padding: '24px', flex: 1 }}>
                    {/* Top retrieved match summary */}
                    {results.retrieved.length > 0 && (
                      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginBottom: '20px' }}>
                        <div>
                          <p style={{ fontSize: '0.75rem', color: '#B0B0B0', marginBottom: '4px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Top Match Syndrome</p>
                          <p style={{ fontSize: '1.1rem', fontWeight: '700', color: '#EFE58B' }}>{results.retrieved[0].syndrome}</p>
                        </div>
                        <div>
                          <p style={{ fontSize: '0.75rem', color: '#B0B0B0', marginBottom: '4px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Reference Formula</p>
                          <p style={{ fontSize: '0.95rem', fontWeight: '600', color: '#F5F5F5' }}>{results.retrieved[0].name}</p>
                        </div>
                      </div>
                    )}

                    {/* Full analysis text */}
                    <p style={{ fontSize: '0.75rem', color: '#B0B0B0', marginBottom: '10px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Analysis</p>
                    <div style={{
                      background: 'rgba(255,255,255,0.04)', borderRadius: '10px',
                      padding: '16px', marginBottom: '16px',
                      maxHeight: '360px', overflowY: 'auto',
                    }}>
                      <ReactMarkdown
                        components={{
                          h2: ({ children }) => (
                            <p style={{ fontSize: '0.85rem', fontWeight: '700', color: '#EFE58B', marginTop: '14px', marginBottom: '6px' }}>{children}</p>
                          ),
                          p: ({ children }) => (
                            <p style={{ fontSize: '0.85rem', color: '#D0D0D0', lineHeight: '1.7', marginBottom: '4px' }}>{children}</p>
                          ),
                          li: ({ children }) => (
                            <li style={{ fontSize: '0.85rem', color: '#D0D0D0', lineHeight: '1.7', marginLeft: '16px' }}>{children}</li>
                          ),
                          ul: ({ children }) => (
                            <ul style={{ marginBottom: '8px' }}>{children}</ul>
                          ),
                          strong: ({ children }) => (
                            <strong style={{ color: '#F5F5F5', fontWeight: '600' }}>{children}</strong>
                          ),
                        }}
                      >
                        {results.analysis}
                      </ReactMarkdown>
                    </div>

                    {/* Disclaimer */}
                    <div style={{
                      background: 'rgba(100,60,20,0.1)', border: '1px solid rgba(100,60,20,0.25)',
                      borderRadius: '10px', padding: '12px 16px',
                    }}>
                      <p style={{ fontSize: '0.8rem', color: '#B0B0B0', lineHeight: '1.6' }}>
                        <span style={{ color: '#EFE58B', fontWeight: '600' }}>仅供辅助参考 · </span>
                        不能替代执业医师诊疗，实际用药需专业医师审核。
                      </p>
                    </div>
                  </div>
                </div>
              )}

              {/* RAG Tabs */}
              {results && !isGenerating && (
                <div style={{
                  background: 'rgba(0,0,0,0.2)', backdropFilter: 'blur(12px)',
                  border: '1px solid rgba(255,255,255,0.06)', borderRadius: '16px',
                  overflow: 'hidden',
                }}>
                  <div style={{ display: 'flex', borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
                    {['Similar Cases', 'Few-shot', 'Pipeline'].map((tab) => (
                      <button key={tab} onClick={() => setActiveTab(tab.toLowerCase())}
                        style={{
                          flex: 1, padding: '12px 0', background: 'transparent', border: 'none',
                          fontSize: '0.82rem', fontWeight: '600', cursor: 'pointer',
                          color: activeTab === tab.toLowerCase() ? '#EFE58B' : '#909090',
                          borderBottom: activeTab === tab.toLowerCase() ? '2px solid #EFE58B' : '2px solid transparent',
                          transition: 'all 0.2s',
                        }}
                      >{tab}</button>
                    ))}
                  </div>

                  <div style={{ padding: '16px' }}>

                    {/* Similar Cases tab */}
                    {activeTab === 'similar cases' && (
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                        {results.retrieved.map((item, idx) => (
                          <div key={item.id} style={{
                            background: 'rgba(255,255,255,0.04)', borderRadius: '10px',
                            padding: '12px 14px', borderLeft: '2px solid rgba(239,229,139,0.3)',
                          }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '6px' }}>
                              <span style={{ fontSize: '0.88rem', fontWeight: '600', color: '#EFE58B' }}>
                                #{idx + 1} {item.name}
                              </span>
                              <div style={{ display: 'flex', gap: '6px' }}>
                                {item.hybrid_score !== undefined ? (
                                  <span style={{ fontSize: '0.75rem', color: '#4A9B8E', background: 'rgba(74,155,142,0.1)', padding: '2px 8px', borderRadius: '6px' }}>
                                    hybrid {(item.hybrid_score * 1000).toFixed(2)}
                                  </span>
                                ) : (
                                  <span style={{ fontSize: '0.75rem', color: '#4A9B8E', background: 'rgba(74,155,142,0.1)', padding: '2px 8px', borderRadius: '6px' }}>
                                    sim {(item.similarity_score * 100).toFixed(0)}%
                                  </span>
                                )}
                                {item.vector_rank && <span style={{ fontSize: '0.72rem', color: '#909090' }}>vec#{item.vector_rank}</span>}
                                {item.bm25_rank && <span style={{ fontSize: '0.72rem', color: '#909090' }}>bm25#{item.bm25_rank}</span>}
                              </div>
                            </div>
                            <p style={{ fontSize: '0.8rem', color: '#B0B0B0', marginBottom: '4px' }}>
                              <span style={{ color: '#D0D0D0' }}>证型：</span>{item.syndrome}
                            </p>
                            <p style={{ fontSize: '0.78rem', color: '#909090', lineHeight: '1.5' }}>
                              {item.symptoms.slice(0, 80)}{item.symptoms.length > 80 ? '…' : ''}
                            </p>
                          </div>
                        ))}
                      </div>
                    )}

                    {/* Few-shot tab */}
                    {activeTab === 'few-shot' && (
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                        {results.fewshot.length === 0 ? (
                          <p style={{ fontSize: '0.85rem', color: '#909090', textAlign: 'center', padding: '16px 0' }}>No few-shot examples selected.</p>
                        ) : results.fewshot.map((item, idx) => (
                          <div key={item.id} style={{
                            background: 'rgba(255,255,255,0.04)', borderRadius: '10px',
                            padding: '12px 14px', borderLeft: '2px solid rgba(74,155,142,0.4)',
                          }}>
                            <p style={{ fontSize: '0.88rem', fontWeight: '600', color: '#4A9B8E', marginBottom: '4px' }}>
                              Example {idx + 1}: {item.name}
                            </p>
                            <p style={{ fontSize: '0.8rem', color: '#B0B0B0', marginBottom: '4px' }}>证型：{item.syndrome}</p>
                            {item.example_case && (
                              <p style={{ fontSize: '0.78rem', color: '#909090', lineHeight: '1.5' }}>
                                {item.example_case.slice(0, 120)}{item.example_case.length > 120 ? '…' : ''}
                              </p>
                            )}
                          </div>
                        ))}
                      </div>
                    )}

                    {/* Pipeline tab */}
                    {activeTab === 'pipeline' && (
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                        {results.pipeline_steps.map((step, idx) => (
                          <div key={idx} style={{
                            display: 'flex', alignItems: 'center', gap: '10px',
                            background: 'rgba(255,255,255,0.03)', borderRadius: '8px', padding: '10px 12px',
                          }}>
                            <span style={{ color: '#4A9B8E', fontSize: '0.85rem', fontWeight: '700', minWidth: '20px' }}>{idx + 1}</span>
                            <span style={{ fontSize: '0.82rem', color: '#D0D0D0' }}>{step}</span>
                          </div>
                        ))}
                      </div>
                    )}

                  </div>
                </div>
              )}
            </div>
          )}

        </div>
      </div>

      <style>{`
        @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.5} }
      `}</style>
    </div>
  );
}
