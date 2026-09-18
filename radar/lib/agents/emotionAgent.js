/**
 * EMOTION AGENT — wraps lib/emotion.js for pipeline.
 */
import { detectEmotion } from "../emotion.js";
export function analyzeEmotion(signals){
  const combined = signals.map(s=> s.text).join("\n");
  return detectEmotion(combined);
}
