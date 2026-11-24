#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
# ParserTests is hostless: it compiles the actual importer without Shared.framework.
SIMULATOR_ID="$(xcrun simctl list devices available --json | python3 -c '
import json,sys
for runtime, devices in json.load(sys.stdin)["devices"].items():
    if "iOS" not in runtime:
        continue
    for device in devices:
        if device.get("isAvailable") and device["name"].startswith("iPhone"):
            print(device["udid"])
            sys.exit(0)
raise SystemExit("No available iOS simulator found")
')"
xcodebuild \
  -project iosApp/LeafReader.xcodeproj \
  -scheme ParserTests \
  -configuration Debug \
  -destination "platform=iOS Simulator,id=$SIMULATOR_ID" \
  -derivedDataPath build/parser-tests \
  -resultBundlePath build/ParserTests.xcresult \
  CODE_SIGNING_ALLOWED=NO CODE_SIGNING_REQUIRED=NO \
  test
