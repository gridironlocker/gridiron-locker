/**
 * Emerging Signal Detection — velocity, acceleration, persistence.
 * Spec §7: do not rank by total mentions; detect acceleration.
 * 20 → 75 → 240 → 700 is more interesting than 500→600.
 */

export function velocity(series){
  // series: [n0,n1,n2,...] oldest→newest
  if(series.length<2) return 0;
  const a = series[series.length-2], b = series[series.length-1];
  if(a===0) return b>0 ? 100 : 0;
  return ((b-a)/a)*100;
}

export function acceleration(series){
  if(series.length<3) return 0;
  const v1 = velocity(series.slice(0,-1));
  const v2 = velocity(series);
  return v2 - v1;
}

export function repetitionScore(series){
  // how consistently the phrase reappears (not a one-day spike)
  if(series.length<3) return 0;
  const nonzero = series.filter(n=>n>0).length;
  return Math.round((nonzero/series.length)*100);
}

export function persistence(series, window=4){
  const recent = series.slice(-window);
  return recent.every(n=>n>0) ? 100 : Math.round((recent.filter(n=>n>0).length/window)*100);
}

export function novelty(series){
  // higher if prior history was quiet
  if(series.length<4) return 50;
  const prior = series.slice(0,-3);
  const priorMax = Math.max(...prior, 0);
  const recent = Math.max(...series.slice(-3));
  if(priorMax===0 && recent>0) return 100;
  if(priorMax===0) return 0;
  return Math.min(100, Math.round((recent/(priorMax||1))*30));
}

export function classifySeries(series){
  const v = velocity(series);
  const a = acceleration(series);
  const rep = repetitionScore(series);
  const pers = persistence(series);
  let label="WATCH";
  if(v>180 && a>30 && pers>60) label="EMERGING";
  else if(v>80 && a>10) label="DEVELOPING";
  else if(v>40) label="WATCH";
  else if(v< -20) label="DECLINING";
  return { velocity: Math.round(v), acceleration: Math.round(a), repetition: rep, persistence: pers, label };
}

/**
 * Opportunity-level velocity synthesis (§12): merges mention velocity with conversation growth, cross-platform spread, etc.
 */
export function opportunityVelocity({ mentionSeries, commentDepthSeries, sourceCountSeries }){
  const m = classifySeries(mentionSeries||[0]);
  const c = commentDepthSeries ? classifySeries(commentDepthSeries) : { velocity:0 };
  const s = sourceCountSeries ? Math.min(100, (sourceCountSeries[sourceCountSeries.length-1]||0)*25) : 0;
  return {
    mentionVelocity: m.velocity,
    commentGrowth: c.velocity,
    sourceSpread: s,
    composite: Math.round((m.velocity*0.6 + c.velocity*0.3 + s*0.1))
  };
}
