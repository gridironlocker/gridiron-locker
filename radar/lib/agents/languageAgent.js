/**
 * LANGUAGE AGENT — discovers emerging vocabulary, nicknames, phrases, memes.
 */
import { discoverVocabulary } from "../graph.js";

export function analyzeLanguage(signals){
  const texts = signals.map(s=> s.text).filter(Boolean);
  const vocab = discoverVocabulary(texts);
  // phrase frequency
  const freq={}; for(const t of texts){ const w=t.toLowerCase(); for(const phrase of ["second act","new era","dawg pound","go blue","go pack go","hail mary","expiration date","let him rip"]) if(w.includes(phrase)) freq[phrase]=(freq[phrase]||0)+1; }
  return { ...vocab, phraseFreq: freq };
}
