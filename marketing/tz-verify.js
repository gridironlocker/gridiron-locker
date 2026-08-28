#!/usr/bin/env node
/*
 * Verifies the dashboard's timezone conversion helpers against known cases.
 *
 * The helpers live inline in dashboard.html (between the tz-helpers-start/end
 * markers) so the planner stays a standalone single file. This script extracts
 * that exact block, evaluates it, and asserts the conversions the operator
 * cares about — plan times are authored in America/New_York and displayed in
 * the viewer's device zone (Africa/Casablanca for the operator).
 *
 * Run from the repository root:  node marketing/tz-verify.js
 */
'use strict';

const fs = require('fs');
const path = require('path');
const vm = require('vm');

const htmlPath = path.join(__dirname, 'dashboard.html');
const html = fs.readFileSync(htmlPath, 'utf8');
const match = html.match(/\/\* tz-helpers-start[\s\S]*?\*\/([\s\S]*?)\/\* tz-helpers-end \*\//);
if (!match) {
  console.error('FAIL: could not find the tz-helpers block in dashboard.html');
  process.exit(1);
}
// Evaluate the shipped helper block in a vm context and pull the functions out:
// tzOffsetMs, wallClockToUtc, formatUtcInZone, convertPlanTime, convertClockRange,
// weekdayIndexFor, anchorDateForWeekday.
const sandbox = {};
vm.createContext(sandbox);
vm.runInContext(match[1], sandbox);
const { convertPlanTime, convertClockRange, anchorDateForWeekday } = sandbox;
if (typeof convertPlanTime !== 'function' || typeof convertClockRange !== 'function' || typeof anchorDateForWeekday !== 'function') {
  console.error('FAIL: helper block did not define the expected functions');
  process.exit(1);
}

const SOURCE = 'America/New_York';
const VIEWER = 'Africa/Casablanca';

let failures = 0;
function check(label, actual, expected) {
  const ok = JSON.stringify(actual) === JSON.stringify(expected);
  if (!ok) failures += 1;
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${label}  ->  ${JSON.stringify(actual)}${ok ? '' : '  (expected ' + JSON.stringify(expected) + ')'}`);
}

// --- The cases quoted in the change request ---------------------------------
// Summer: New York is EDT (UTC-4), Casablanca is UTC+1 -> +5 hours.
const ig = convertPlanTime('2026-08-27', '12:00', SOURCE, VIEWER);
check('Instagram default 12:00 ET (Aug)', ig.time + ' shift ' + ig.dayShift, '17:00 shift 0');

// Evening slot rolls past midnight in Morocco.
const tt = convertPlanTime('2026-08-27', '19:30', SOURCE, VIEWER);
check('TikTok default 19:30 ET (Aug)', tt.time + ' shift ' + tt.dayShift + ' date ' + tt.date, '00:30 shift 1 date 2026-08-28');

// Winter: New York is EST (UTC-5), Casablanca is UTC+1 -> +6 hours.
const winter = convertPlanTime('2026-01-15', '09:00', SOURCE, VIEWER);
check('X default 09:00 ET (Jan)', winter.time + ' shift ' + winter.dayShift, '15:00 shift 0');

// --- DST-awareness guards ----------------------------------------------------
// US DST ends 2026-11-01: ET flips from UTC-4 to UTC-5, so the same clock time
// converts differently before/after the transition. Per-day anchoring must win.
const beforeEnd = convertPlanTime('2026-10-31', '09:00', SOURCE, VIEWER); // EDT
const afterEnd = convertPlanTime('2026-11-02', '09:00', SOURCE, VIEWER); // EST
check('09:00 ET on 2026-10-31 (EDT)', beforeEnd.time + ' shift ' + beforeEnd.dayShift, '14:00 shift 0');
check('09:00 ET on 2026-11-02 (EST)', afterEnd.time + ' shift ' + afterEnd.dayShift, '15:00 shift 0');

// --- Window ranges ------------------------------------------------------------
const calendarDates = [
  '2026-08-27', '2026-08-28', '2026-08-29', '2026-08-30', '2026-08-31',
  '2026-09-01', '2026-09-02', '2026-09-03', '2026-09-04', '2026-09-05',
  '2026-09-06', '2026-09-07', '2026-09-08', '2026-09-09'
];
check('weekday anchor for Tue', anchorDateForWeekday('Tue', calendarDates), '2026-09-01');
check('weekday anchor for Sun', anchorDateForWeekday('Sun', calendarDates), '2026-08-30');

const tiktokWindow = convertClockRange('Tue–Thu · 18:30–21:00', anchorDateForWeekday('Tue', calendarDates), SOURCE, VIEWER);
check('TikTok window', tiktokWindow.prefix + tiktokWindow.start.time + '–' + tiktokWindow.end.time + ' (end shift ' + tiktokWindow.end.dayShift + ')', 'Tue–Thu · 23:30–02:00 (end shift 1)');

const xWindow = convertClockRange('Mon–Fri · 08:00–10:00', anchorDateForWeekday('Mon', calendarDates), SOURCE, VIEWER);
check('X window', xWindow.prefix + xWindow.start.time + '–' + xWindow.end.time + ' (end shift ' + xWindow.end.dayShift + ')', 'Mon–Fri · 13:00–15:00 (end shift 0)');

// Windows without clock times are left untouched.
check('Game-day window left as-is', convertClockRange('Game days · 30 min before kickoff', calendarDates[0], SOURCE, VIEWER), null);

// Identity when the viewer is already on the plan zone.
const same = convertPlanTime('2026-08-27', '12:00', SOURCE, SOURCE);
check('same-zone is identity', same.time + ' shift ' + same.dayShift, '12:00 shift 0');

if (failures) {
  console.error(`\n${failures} check(s) FAILED`);
  process.exit(1);
}
console.log('\nAll timezone conversions verified.');
