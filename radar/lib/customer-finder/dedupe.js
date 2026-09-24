// 3. DEDUPLICATION — unique identifier = platform + post URL + author + relevant content.
import crypto from "crypto";
import { fingerprintBasis } from "./dedupe-core.js";
export { canonicalUrl, normalizeText, urlKey, fingerprintBasis } from "./dedupe-core.js";

export function fingerprint(item) {
  return crypto.createHash("sha256").update(fingerprintBasis(item)).digest("hex");
}
