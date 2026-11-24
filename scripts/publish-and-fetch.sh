#!/usr/bin/env bash
# 用 GitHub REST API 完成：建公开仓库 → 推送 → 触发 Actions → 等 macOS 构建 → 下载未签名 IPA。
# 用法：GITHUB_TOKEN=xxx [REPO_NAME=leaf-reader] bash scripts/publish-and-fetch.sh
set -euo pipefail

TOKEN=${GITHUB_TOKEN:-}
REPO_NAME=${REPO_NAME:-leaf-reader}
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT_DIR=${OUT_DIR:-$ROOT/dist}
API=https://api.github.com

[ -n "$TOKEN" ] || { echo "缺少 GITHUB_TOKEN" >&2; exit 2; }

api() { # api METHOD PATH [DATA]
  local method=$1 path=$2 data=${3:-}
  if [ -n "$data" ]; then
    curl -sS -X "$method" -H "Authorization: Bearer $TOKEN" \
      -H "Accept: application/vnd.github+json" -H "X-GitHub-Api-Version: 2022-11-28" \
      -H "Content-Type: application/json" -d "$data" "$API$path"
  else
    curl -sS -X "$method" -H "Authorization: Bearer $TOKEN" \
      -H "Accept: application/vnd.github+json" -H "X-GitHub-Api-Version: 2022-11-28" "$API$path"
  fi
}

json() { python3 -c "import json,sys;d=json.load(sys.stdin);print(eval(sys.argv[1]))" "$1"; }

echo "== 1. 校验 token"
ME=$(api GET /user)
OWNER=$(printf '%s' "$ME" | json "d.get('login','')")
[ -n "$OWNER" ] || { echo "token 无效: $ME" >&2; exit 3; }
echo "   账号: $OWNER"

echo "== 2. 建仓库 $OWNER/$REPO_NAME（public，免费 macOS Actions）"
CREATE=$(api POST /user/repos "{\"name\":\"$REPO_NAME\",\"private\":false,\"auto_init\":false,\"has_issues\":false,\"has_wiki\":false}")
PRIVATE=$(printf '%s' "$CREATE" | json "str(d.get('private','?')).lower()")
if [ "$PRIVATE" = "true" ]; then
  echo "   仓库是 private，macOS runner 会消耗额度，继续但请注意" >&2
fi
printf '%s' "$CREATE" | grep -q '"full_name"\|already exists' || { echo "建仓失败: $CREATE" >&2; exit 4; }

echo "== 3. 推送 main"
cd "$ROOT"
git rev-parse --git-dir >/dev/null 2>&1 || { echo "当前目录不是 git 仓库" >&2; exit 5; }
git branch -M main 2>/dev/null || true
git remote remove origin 2>/dev/null || true
git remote add origin "https://x-access-token:$TOKEN@github.com/$OWNER/$REPO_NAME.git"
git push -q -u origin main --force
git remote set-url origin "https://github.com/$OWNER/$REPO_NAME.git"
COMMIT=$(git rev-parse HEAD)
echo "   已推送 $COMMIT"

echo "== 4. 触发 workflow_dispatch（push 也会自动触发）"
api POST "/repos/$OWNER/$REPO_NAME/actions/workflows/ios-ipa.yml/dispatches" '{"ref":"main"}' >/dev/null || \
  echo "   dispatch 未成功，依赖 push 触发"

echo "== 5. 等待 macOS 构建（最长 100 分钟）"
RUN_ID=""
for i in $(seq 1 200); do
  sleep 30
  RUNS=$(api GET "/repos/$OWNER/$REPO_NAME/actions/runs?per_page=5")
  RUN_ID=$(printf '%s' "$RUNS" | json "(d.get('workflow_runs') or [{}])[0].get('id','')")
  STATUS=$(printf '%s' "$RUNS" | json "(d.get('workflow_runs') or [{}])[0].get('status','')")
  CONCL=$(printf '%s' "$RUNS" | json "(d.get('workflow_runs') or [{}])[0].get('conclusion') or ''")
  [ -n "$RUN_ID" ] || { echo "   还未出现 run（第 ${i} 次）"; continue; }
  echo "   run=$RUN_ID status=$STATUS conclusion=$CONCL"
  [ "$STATUS" = "completed" ] && break
done
[ "$STATUS" = "completed" ] || { echo "超时未完成，去看 https://github.com/$OWNER/$REPO_NAME/actions" >&2; exit 6; }
if [ "$CONCL" != "success" ]; then
  echo "构建失败（$CONCL），日志: https://github.com/$OWNER/$REPO_NAME/actions/runs/$RUN_ID" >&2
  exit 7
fi

echo "== 6. 下载 IPA artifact"
ARTS=$(api GET "/repos/$OWNER/$REPO_NAME/actions/runs/$RUN_ID/artifacts")
ART_ID=$(printf '%s' "$ARTS" | json "next((a['id'] for a in d.get('artifacts',[]) if 'LeafReader' in a['name']),'')")
[ -n "$ART_ID" ] || { echo "没找到 IPA artifact: $ARTS" >&2; exit 8; }
mkdir -p "$OUT_DIR"
curl -sSL -H "Authorization: Bearer $TOKEN" -H "Accept: application/vnd.github+json" \
  "$API/repos/$OWNER/$REPO_NAME/actions/artifacts/$ART_ID/zip" -o "$OUT_DIR/artifact.zip"
cd "$OUT_DIR" && rm -rf unpacked && mkdir unpacked && unzip -q -o artifact.zip -d unpacked
IPA=$(find unpacked -name "*.ipa" | head -1)
[ -n "$IPA" ] || { echo "artifact 里没有 .ipa" >&2; exit 9; }

echo "== 7. 校验"
ls -la unpacked
( cd unpacked && sha256sum -c ./*.sha256 2>/dev/null || sha256sum "$(basename "$IPA")" )
unzip -l "$IPA" | head -10
unzip -p "$IPA" "Payload/"*/Info.plist > /tmp/ipa-info.plist 2>/dev/null && \
  python3 -c "import plistlib;d=plistlib.load(open('/tmp/ipa-info.plist','rb'));print('bundle:',d.get('CFBundleIdentifier'),'ver:',d.get('CFBundleShortVersionString'),'minOS:',d.get('MinimumOSVersion'))" || true

PHONE=/sdcard/Download/DSH-Go/LeafReader
mkdir -p "$PHONE" && cp "$IPA" "$PHONE"/ && cp -f ./*.sha256 "$PHONE"/ 2>/dev/null || true
echo "== 完成: $PHONE/$(basename "$IPA")"
echo "   仓库: https://github.com/$OWNER/$REPO_NAME  运行: https://github.com/$OWNER/$REPO_NAME/actions/runs/$RUN_ID"
