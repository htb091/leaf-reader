#!/usr/bin/env bash
# 轮询已触发的 Actions run，成功后下载 artifact 并校验/落地 IPA。
set -euo pipefail
TOKEN=${GITHUB_TOKEN:?缺少 GITHUB_TOKEN}
REPO=${REPO:-htb091/leaf-reader}
OUT=${OUT:-/root/workspace/miuix-local-reader/dist}
API=https://api.github.com

api() { curl -sS -H "Authorization: Bearer $TOKEN" -H "Accept: application/vnd.github+json" "$API$1"; }

echo "[$(date +%H:%M:%S)] 等待 run 出现"
RUN_ID=""
for i in $(seq 1 30); do
  RUN_ID=$(api "/repos/$REPO/actions/runs?per_page=1" | python3 -c "import json,sys;r=json.load(sys.stdin).get('workflow_runs') or [];print(r[0]['id'] if r else '')")
  [ -n "$RUN_ID" ] && break
  sleep 20
done
[ -n "$RUN_ID" ] || { echo "没有 run"; exit 3; }
echo "[$(date +%H:%M:%S)] run=$RUN_ID"

LAST=""
for i in $(seq 1 120); do
  J=$(api "/repos/$REPO/actions/runs/$RUN_ID")
  read -r STATUS CONCL <<<"$(printf '%s' "$J" | python3 -c "import json,sys;d=json.load(sys.stdin);print(d.get('status'),d.get('conclusion') or 'none')")"
  CUR="$STATUS/$CONCL"
  if [ "$CUR" != "$LAST" ]; then echo "[$(date +%H:%M:%S)] $CUR"; LAST="$CUR"; fi
  [ "$STATUS" = "completed" ] && break
  sleep 45
done

JOBS=$(api "/repos/$REPO/actions/runs/$RUN_ID/jobs?per_page=20")
printf '%s' "$JOBS" | python3 -c "
import json,sys
for j in json.load(sys.stdin).get('jobs',[]):
    print(f\"  job: {j['name']} -> {j['status']}/{j.get('conclusion')}\")
    for s in j.get('steps',[]):
        print(f\"    - {s['name']}: {s['status']}/{s.get('conclusion')}\")
"

if [ "$STATUS" != "completed" ]; then echo "超时"; exit 4; fi

if [ "$CONCL" != "success" ]; then
  echo "构建失败: $CONCL"
  CUR_JOB=$(printf '%s' "$JOBS" | python3 -c "
import json,sys
for j in json.load(sys.stdin).get('jobs',[]):
    if j.get('conclusion')=='failure':
        for s in j.get('steps',[]):
            if s.get('conclusion')=='failure': print(j['id'], s['name'])
")
  echo "失败步骤: $CUR_JOB"
  exit 5
fi

echo "[$(date +%H:%M:%S)] 下载 artifact"
ART=$(api "/repos/$REPO/actions/runs/$RUN_ID/artifacts" | python3 -c "import json,sys;d=json.load(sys.stdin);print(next((a['id'] for a in d.get('artifacts',[]) if 'LeafReader' in a['name']),''))")
[ -n "$ART" ] || { echo "没有 IPA artifact"; exit 6; }
mkdir -p "$OUT" && cd "$OUT"
curl -sSL -H "Authorization: Bearer $TOKEN" "$API/repos/$REPO/actions/artifacts/$ART/zip" -o artifact.zip
rm -rf unpacked && mkdir unpacked && unzip -q -o artifact.zip -d unpacked
IPA=$(find unpacked -name "*.ipa" | head -1)
[ -n "$IPA" ] || { echo "artifact 中没有 .ipa"; exit 7; }
ls -la unpacked
sha256sum unpacked/*.ipa
unzip -l "$IPA" | head -8
mkdir -p /sdcard/Download/DSH-Go/LeafReader
cp -f "$IPA" /sdcard/Download/DSH-Go/LeafReader/
cp -f unpacked/*.sha256 /sdcard/Download/DSH-Go/LeafReader/ 2>/dev/null || true
echo "完成: $(basename "$IPA") -> /sdcard/Download/DSH-Go/LeafReader/"
