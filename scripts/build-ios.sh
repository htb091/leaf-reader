#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
if [[ "$(uname -s)" != Darwin ]]; then
  printf 'This build requires macOS and Xcode. Use the GitHub Actions Build iOS IPA workflow.\n' >&2
  exit 1
fi
python3 scripts/check_project.py
bash ./gradlew :shared:linkReleaseFrameworkIosArm64 -PenableApple=true --stacktrace
(cd iosApp && xcodegen generate)
xcodebuild \
  -project iosApp/LeafReader.xcodeproj \
  -scheme LeafReader \
  -configuration Release \
  -sdk iphoneos \
  -destination 'generic/platform=iOS' \
  -derivedDataPath build/ios \
  CODE_SIGNING_ALLOWED=NO CODE_SIGNING_REQUIRED=NO CODE_SIGN_IDENTITY='' DEVELOPMENT_TEAM='' \
  build
APP="$ROOT/build/ios/Build/Products/Release-iphoneos/LeafReader.app"
test -f "$APP/LeafReader"
plutil -lint "$APP/Info.plist"
xcrun lipo -verify_arch arm64 "$APP/LeafReader"
python3 scripts/package_ipa.py --app "$APP" --output "$ROOT/dist/LeafReader-0.1.0-unsigned.ipa"
