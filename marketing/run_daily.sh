#!/usr/bin/env bash
set -e
cd "$(dirname "$0")/.."
echo "== Gridiron Locker Daily Revenue Build =="
echo "Step 1: live engine (trends → drops → unique captions → pinterest)"
python marketing/live_engine.py
echo ""
echo "Step 2: rebuild site (includes /drops/ page)"
python src/build.py
echo ""
echo "Step 3: verify"
ls -lh site/drops/index.html marketing/live_drops.json marketing/pinterest_feed.csv | awk '{print $9, $5}'
echo ""
echo "Counts:"
echo -n "  live drops: "; python -c "import json; print(len(json.load(open('marketing/live_drops.json'))['drops']))"
echo -n "  pinterest pins: "; wc -l < marketing/pinterest_feed.csv
echo -n "  plan queue: "; python -c "import json; print(len(json.load(open('marketing/plan.json'))['queue']))"
echo -n "  unique IG: "; python -c "import json, collections; q=json.load(open('marketing/plan.json'))['queue']; ig=[x['platforms']['instagram']['caption'] for x in q]; print(f'{len(set(ig))}/{len(ig)}')"
echo ""
echo "Done. Next: upload marketing/pinterest_feed.csv to Pinterest, post top 3 from marketing/live.html"
echo "Public page: site/drops/index.html (priority 0.95)"
