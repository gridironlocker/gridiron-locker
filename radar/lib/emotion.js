/**
 * Fan Emotion Intelligence — spec §8
 * Detects excitement, pride, anger, frustration, nostalgia, anticipation, confidence, fear, rivalry, belonging, celebration, disappointment, redemption, identity.
 * Also flags identity language: we/our/true fans/this is Michigan/Dawg Pound/Go Blue etc.
 */

const EMOTION_LEXICON = {
  excitement: ["can't wait","hype","electric","fired up","lets go","let's go","pumped","buzzing","explosive","breakout"],
  pride: ["proud","our","we are","tradition","legacy","built for","true fans","this is michigan","dawg pound","go blue","go pack go"],
  anger: ["angry","furious","blame","fire","bench","cut him","disaster","embarrassing"],
  frustration: ["frustrating","again","same old","here we go again","stuck","not working"],
  nostalgia: ["remember when","throwback","vintage","old school","back in the day","nostalgia","classic"],
  anticipation: ["next week","season opener","week 1","countdown","almost here","coming soon","kickoff"],
  confidence: ["we got this","locked","believe","going to win","unstoppable","destined"],
  fear: ["worried","scared","nervous","what if","afraid","doom"],
  rivalry: ["rivalry","hate","revenge","beat","vs everybody","michigan vs everybody","ann arbor","big house","night games"],
  belonging: ["we","our","family","together","belong","community","fan family"],
  celebration: ["celebrate","party","champs","victory","win","hail mary","last-second","miracle"],
  disappointment: ["disappointment","let down","choked","lost","loss","blown","should have"],
  redemption: ["second act","second chance","redemption","comeback","prove them wrong","bounce back","new era"],
  identity: ["true fans","real fans","dawg pound","go blue","go pack go","how bout them cowboys","star power"]
};

const IDENTITY_PHRASES = [
  "we","our","true fans","real fans","this is michigan","dawg pound","go blue","go pack go",
  "how bout them cowboys","america's team","michigan vs everybody","here we go brownies",
  "second act","new era","our house","big house"
];

export function detectEmotion(text){
  const lower = (text||"").toLowerCase();
  const scores={};
  for(const [emo, phrases] of Object.entries(EMOTION_LEXICON)){
    let s=0;
    for(const p of phrases){
      if(lower.includes(p)) s+= p.split(" ").length>1 ? 2 : 1; // multi-word weighs more
    }
    scores[emo]=s;
  }
  const sorted = Object.entries(scores).sort((a,b)=>b[1]-a[1]);
  const primary = sorted[0]?.[1]>0 ? sorted[0][0] : "neutral";
  const intensity = Math.min(100, (sorted[0]?.[1]||0)*22 + (sorted[1]?.[1]||0)*10);
  const identityHits = IDENTITY_PHRASES.filter(p=> lower.includes(p));
  return {
    primary,
    intensity,
    breakdown: Object.fromEntries(sorted.filter(([,v])=>v>0).slice(0,5)),
    identityLanguage: identityHits,
    identityScore: Math.min(100, identityHits.length*18),
    isHighIdentity: identityHits.length>=2
  };
}

export function emotionForSignal(signalTexts){
  const combined = (signalTexts||[]).join(" \n ");
  return detectEmotion(combined);
}
