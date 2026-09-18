/**
 * OUTCOME AGENT — learns which signals correlated with useful outcomes.
 */
import { outcomeCorrelations } from "../history.js";
export function learn(history){ return outcomeCorrelations(history); }
