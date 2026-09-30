'use client';

import { useState } from 'react';
import { CheckCircle2, CircleHelp, ShieldCheck, XCircle } from 'lucide-react';
import { Chunk } from '@/lib/types';

type Evidence = { source_id: string; title: string | null; url: string | null; relevance: number; snippet: string };
type Claim = { claim_id: string; claim: string; label: 'SUPPORTED' | 'CONTRADICTED' | 'UNCERTAIN'; confidence: number; evidence: Evidence[]; rationale: string };
type Result = { claims: Claim[]; trust: { overall_trust: number | null; supported_count: number; contradicted_count: number; uncertain_count: number; explanation: string } };

const iconFor = (label: Claim['label']) => label === 'SUPPORTED' ? <CheckCircle2 className="text-emerald-600 dark:text-emerald-400" size={17} /> : label === 'CONTRADICTED' ? <XCircle className="text-red-600 dark:text-red-400" size={17} /> : <CircleHelp className="text-amber-600 dark:text-amber-400" size={17} />;

export default function VerificationPanel({ query, answer, sources }: { query: string; answer: string; sources: Chunk[] }) {
  const [result, setResult] = useState<Result | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [open, setOpen] = useState(false);
  const [expanded, setExpanded] = useState<string | null>(null);
  const verify = async () => {
    setLoading(true); setError(null);
    try {
      const response = await fetch('/api/verify', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ query, answer, sources }) });
      const data = await response.json();
      if (!response.ok) throw new Error(data.message || 'Verification failed.');
      setResult(data); setOpen(true);
    } catch (err) { setError(err instanceof Error ? err.message : 'Verification failed.'); }
    finally { setLoading(false); }
  };
  if (!result) return <div className="mt-4 rounded-xl border border-light-200 dark:border-dark-200 p-3 bg-light-secondary/50 dark:bg-dark-secondary/50"><button onClick={verify} disabled={loading} className="text-sm font-medium px-3 py-1.5 rounded-lg bg-teal-600 hover:bg-teal-700 disabled:opacity-60 text-white">{loading ? 'Verifying answer… Analyzing claims…' : 'Verify answer'}</button>{error && <p className="mt-2 text-sm text-red-600 dark:text-red-400">Verification failed: {error} <button onClick={verify} className="underline">Retry</button></p>}</div>;
  const trust = result.trust;
  return <section className="mt-4 rounded-xl border border-light-200 dark:border-dark-200 bg-light-secondary/50 dark:bg-dark-secondary/50 p-4 text-black dark:text-white"><div className="flex items-start justify-between gap-3"><div><div className="flex items-center gap-2 font-medium"><ShieldCheck size={18} /> Verification</div><p className="mt-1 text-sm text-black/60 dark:text-white/60">{trust.supported_count} Supported · {trust.uncertain_count} Uncertain · {trust.contradicted_count} Contradicted</p></div><div className="text-right"><p className="text-2xl font-semibold">{trust.overall_trust === null ? '—' : `${Math.round(trust.overall_trust * 100)}%`}</p><p className="text-xs text-black/60 dark:text-white/60">Overall Trust</p></div></div><button onClick={() => setOpen(!open)} className="mt-3 text-sm font-medium text-teal-700 dark:text-teal-300">{open ? 'Hide claim analysis' : 'Show claim analysis'}</button>{open && <div className="mt-4 space-y-2"><p className="text-sm text-black/70 dark:text-white/70">{trust.explanation}</p>{result.claims.map((claim) => <div key={claim.claim_id} className="rounded-lg border border-light-200 dark:border-dark-200 p-3"><button className="w-full text-left flex gap-2" onClick={() => setExpanded(expanded === claim.claim_id ? null : claim.claim_id)}>{iconFor(claim.label)}<span className="flex-1 text-sm"><b>{claim.claim_id} · {claim.label}</b><br />{claim.claim}</span><span className="text-sm">{Math.round(claim.confidence * 100)}%</span></button>{expanded === claim.claim_id && <div className="mt-3 pl-6 text-sm space-y-2"><p><b>Rationale:</b> {claim.rationale}</p><p><b>Evidence:</b></p>{claim.evidence.map((evidence) => <div key={evidence.source_id} className="rounded bg-light-100 dark:bg-dark-100 p-2"><p>“{evidence.snippet}”</p><p className="mt-1 text-xs text-black/60 dark:text-white/60">{evidence.source_id} · {evidence.title || 'Untitled'} {evidence.url && <a className="ml-1 underline" href={evidence.url} target="_blank" rel="noreferrer">Open source</a>}</p></div>)}</div>}</div>)}</div>}</section>;
}
