// Scratch: search for a 5×5 position where
//   (A) the scripted "obvious attack" (black fills white's last outside liberty)
//       lets white's scripted reply put BLACK's big group into serious danger
//       (captured or ≤1 liberty) — "动两块": the fight wrecks black's shape too;
//   (B) black's calm alternative (strengthen/pass) leaves BOTH groups alive with
//       ≥2 liberties (双活-flavored coexistence);
//   (C) every move legal.
// Run: node tools/find-position.mjs
import { emptyPosition, play, BLACK, WHITE, groupAt, key } from "../app/rules.js";

const size = 5;
function posFrom(cells) { // cells: [[r,c,color],...]
  const pos = emptyPosition(size);
  for (const [r, c, col] of cells) {
    const res = play(pos, key(r, c), col);
    if (!res.ok) return null; // candidate must place legally
    pos.stones = res.pos.stones;
  }
  return pos;
}
function groupInfo(pos, k) {
  const g = groupAt(pos, k);
  return { stones: g.stones.size, libs: g.liberties.size, libList: [...g.liberties] };
}
function tryPlace(pos, k, color) {
  const res = play(pos, k, color);
  return res.ok ? res.pos : null;
}

// Candidate family: black wall with an eye on the left; white pressing group
// adjacent on the right with few liberties; shared/adjacent tension.
// Cells: [r, c, color]
const candidates = [];
// family 1: black L-group bottom-left with eye at (5,1); white group right of it
candidates.push({
  name: "corner-press",
  cells: [
    [4, 1, BLACK], [4, 2, BLACK], [5, 1, BLACK], [5, 2, BLACK],
    [3, 2, WHITE], [4, 3, WHITE], [5, 3, WHITE],
  ],
  attack: [5, 3 - 1 - 1], // placeholder, recomputed below
});
// we instead do a generic scan: for each candidate, enumerate black "attack"
// moves adjacent to white groups with ≤2 libs, and white's scripted reply
// adjacent to black groups with ≤3 libs, and check the (A)/(B) properties.

function enumerate(cand) {
  const base = posFrom(cand.cells);
  if (!base) return [];
  const results = [];
  const empties = [];
  for (let r = 1; r <= size; r++)
    for (let c = 1; c <= size; c++)
      if (!base.stones.has(key(r, c))) empties.push([r, c]);
  for (const [r, c] of empties) {
    const atk = tryPlace(base, key(r, c), BLACK);
    if (!atk) continue;
    // white's scripted reply: any legal white move that maximizes damage to black
    for (const [r2, c2] of empties) {
      if (r2 === r && c2 === c) continue;
      const after = tryPlace(atk, key(r2, c2), WHITE);
      if (!after) continue;
      // measure black's biggest group after the exchange
      let worst = null;
      for (const [kk, v] of after.stones) {
        if (v !== BLACK) continue;
        const gi = groupInfo(after, kk);
        if (!worst || gi.stones > worst.stones) worst = gi;
      }
      // (A): black big group captured or ≤1 liberty
      const damaged = (!worst && baseBlackCount(cand) > 0) || (worst && worst.libs <= 1);
      if (!damaged) continue;
      // (B) for the calm alternative: black plays a calm empty point (not r,c),
      // then white plays its scripted reply (same r2,c2 if legal), and both
      // groups alive with ≥2 liberties
      for (const [r3, c3] of empties) {
        if (r3 === r && c3 === c) continue;
        if (r3 === r2 && c3 === c2) continue;
        const calm = tryPlace(base, key(r3, c3), BLACK);
        if (!calm) continue;
        const afterCalm = tryPlace(calm, key(r2, c2), WHITE);
        const finalPos = afterCalm ?? calm;
        const okBlack = allBlackAlive(finalPos, 2);
        const okWhite = allWhiteAlive(finalPos, 2);
        if (okBlack && okWhite) {
          results.push({ attack: [r, c], wReply: [r2, c2], calm: [r3, c3] });
          if (results.length >= 5) return results;
        }
      }
    }
  }
  return results;
}
function baseBlackCount(cand) { return cand.cells.filter((x) => x[2] === BLACK).length; }
function allBlackAlive(pos, minLibs) {
  const seen = new Set();
  for (const [k, v] of pos.stones) {
    if (v !== BLACK || seen.has(k)) continue;
    const g = groupAt(pos, k);
    for (const s of g.stones) seen.add(s);
    if (g.liberties.size < minLibs) return false;
  }
  return seen.size > 0;
}
function allWhiteAlive(pos, minLibs) {
  const seen = new Set();
  for (const [k, v] of pos.stones) {
    if (v !== WHITE || seen.has(k)) continue;
    const g = groupAt(pos, k);
    for (const s of g.stones) seen.add(s);
    if (g.liberties.size < minLibs) return false;
  }
  return seen.size > 0;
}

for (const cand of candidates) {
  const found = enumerate(cand);
  console.log(cand.name, JSON.stringify(found.slice(0, 5), null, 1));
}
