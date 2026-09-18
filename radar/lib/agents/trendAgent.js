/**
 * TREND AGENT — computes Fan Trend Index, velocity, acceleration per entity.
 */
import { velocity, acceleration, persistence } from "../velocity.js";

export function analyzeTrends(trends){
  // trends is data/trends.json enriched shape
  const fti = trends.fan_trend_index;
  const rows = fti?.rows||[];
  // Add velocity if we have history (mock trajectory for now using mentions as proxy)
  return rows.map(r=>{
    const series = [Math.max(0, r.mentions-12), Math.max(0, r.mentions-8), Math.max(0, r.mentions-3), r.mentions];
    return {
      ...r,
      velocity: velocity(series),
      acceleration: acceleration(series),
      persistence: persistence(series)
    };
  });
}
