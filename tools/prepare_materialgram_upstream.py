#!/usr/bin/env python3
"""Prepare the pinned Telegram Android submodule for a MaterialGram debug build.

Secrets are injected only into the ephemeral GitHub Actions checkout. This script
never prints API credentials and never writes them back to the parent repository.
"""
from __future__ import annotations

import base64
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UPSTREAM = ROOT / "upstream" / "Telegram-Android"
PACKAGE = "org.materialgram"


def fail(message: str) -> "NoReturn":
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def read_text(path: Path) -> str:
    if not path.is_file():
        fail(f"Required upstream file is missing: {path.relative_to(ROOT)}")
    return path.read_text(encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def replace_line(content: str, pattern: str, replacement: str, description: str) -> str:
    updated, count = re.subn(pattern, replacement, content, count=1, flags=re.MULTILINE)
    if count == 1:
        return updated
    if re.search(re.escape(replacement), content):
        return content
    fail(f"Could not find the expected {description} setting in the pinned upstream source")


def set_java_value(content: str, field: str, value: str) -> str:
    pattern = rf'(?m)^(\s*public static (?:int|boolean|String) {re.escape(field)} = ).*?;'
    updated, count = re.subn(pattern, lambda m: m.group(1) + value + ";", content, count=1)
    if count != 1:
        fail(f"Could not safely patch BuildVars.{field}")
    return updated


def main() -> None:
    if not UPSTREAM.is_dir():
        fail("Telegram submodule is not checked out. Use actions/checkout with submodules: recursive.")

    api_id_raw = os.environ.get("TELEGRAM_API_ID", "").strip()
    api_hash = os.environ.get("TELEGRAM_API_HASH", "").strip()
    if not api_id_raw or not api_hash:
        fail(
            "Telegram API credentials are missing. Add TELEGRAM_API_ID and TELEGRAM_API_HASH "
            "as GitHub Actions repository secrets; do not paste them into source files or chat."
        )
    if not api_id_raw.isdecimal() or int(api_id_raw) <= 0:
        fail("TELEGRAM_API_ID must be a positive integer.")
    if not re.fullmatch(r"[0-9a-fA-F]{32}", api_hash):
        fail("TELEGRAM_API_HASH must be a 32-character hexadecimal value.")

    props_path = UPSTREAM / "gradle.properties"
    props = read_text(props_path)
    props = replace_line(props, r"^APP_PACKAGE=.*$", f"APP_PACKAGE={PACKAGE}", "APP_PACKAGE")
    write_text(props_path, props)

    app_gradle_path = UPSTREAM / "TMessagesProj_App" / "build.gradle"
    app_gradle = read_text(app_gradle_path)
    app_gradle, suffix_count = re.subn(
        r'(?m)^\s*applicationIdSuffix\s+"\.beta"\s*\n', "", app_gradle, count=1
    )
    if suffix_count != 1 and 'applicationIdSuffix ".beta"' in app_gradle:
        fail("Could not remove the upstream .beta applicationId suffix safely.")

    firebase_b64 = os.environ.get("MATERIALGRAM_GOOGLE_SERVICES_JSON_BASE64", "").strip()
    firebase_config_path = UPSTREAM / "TMessagesProj_App" / "google-services.json"
    upstream_firebase_path = UPSTREAM / "TMessagesProj" / "google-services.json"
    if firebase_b64:
        try:
            firebase_raw = base64.b64decode(firebase_b64, validate=True)
            firebase_config = json.loads(firebase_raw.decode("utf-8"))
        except Exception:
            fail("MATERIALGRAM_GOOGLE_SERVICES_JSON_BASE64 is not valid base64-encoded Firebase JSON.")
        packages = {
            client.get("client_info", {}).get("android_client_info", {}).get("package_name")
            for client in firebase_config.get("client", [])
        }
        if PACKAGE not in packages:
            fail("The supplied Firebase config must contain an Android app with package org.materialgram.")
        write_text(firebase_config_path, json.dumps(firebase_config, indent=2) + "\n")
        write_text(upstream_firebase_path, json.dumps(firebase_config, indent=2) + "\n")
    else:
        app_gradle, _ = re.subn(
            r"(?m)^apply plugin: 'com\.google\.gms\.google-services'\s*\n?", "",
            app_gradle
        )
        firebase_config_path.unlink(missing_ok=True)
        upstream_firebase_path.unlink(missing_ok=True)
        print("Firebase config not supplied: the APK will build without Firebase push notifications.")

    write_text(app_gradle_path, app_gradle)

    build_vars_path = UPSTREAM / "TMessagesProj" / "src" / "main" / "java" / "org" / "telegram" / "messenger" / "BuildVars.java"
    build_vars = read_text(build_vars_path)
    build_vars = set_java_value(build_vars, "APP_ID", api_id_raw)
    build_vars = set_java_value(build_vars, "APP_HASH", json.dumps(api_hash))
    build_vars = set_java_value(build_vars, "SAFETYNET_KEY", json.dumps(""))
    build_vars = set_java_value(build_vars, "GOOGLE_AUTH_CLIENT_ID", json.dumps(""))
    build_vars = set_java_value(build_vars, "HUAWEI_APP_ID", json.dumps(""))
    build_vars = set_java_value(build_vars, "HUAWEI_STORE_URL", json.dumps(""))
    build_vars = set_java_value(build_vars, "PLAYSTORE_APP_URL", json.dumps("https://github.com/v0idty/MaterialGram"))
    build_vars = set_java_value(build_vars, "CHECK_UPDATES", "false")
    build_vars = set_java_value(build_vars, "IS_BILLING_UNAVAILABLE", "true")
    build_vars = set_java_value(build_vars, "SUPPORTS_PASSKEYS", "false")
    build_vars = set_java_value(build_vars, "SUPPORTS_FPNV", "false")
    write_text(build_vars_path, build_vars)

    resource_root = UPSTREAM / "TMessagesProj" / "src" / "main" / "res"
    for strings_path in resource_root.glob("values*/strings.xml"):
        strings = read_text(strings_path)
        strings, _ = re.subn(
            r'(<string\s+name="AppName"[^>]*>).*?(</string>)',
            rf"\g<1>MaterialGram\g<2>", strings, count=1
        )
        strings, _ = re.subn(
            r'(<string\s+name="AppNameBeta"[^>]*>).*?(</string>)',
            rf"\g<1>MaterialGram\g<2>", strings, count=1
        )
        write_text(strings_path, strings)

    icon_path = resource_root / "drawable" / "ic_materialgram_icon.xml"
    icon_path.parent.mkdir(parents=True, exist_ok=True)
    icon = """<?xml version="1.0" encoding="utf-8"?>
<vector xmlns:android="http://schemas.android.com/apk/res/android"
    android:width="108dp"
    android:height="108dp"
    android:viewportWidth="108"
    android:viewportHeight="108">
    <path
        android:fillColor="#6750A4"
        android:pathData="M12,0H96A12,12 0,0 1,108 12V96A12,12 0,0 1,96 108H12A12,12 0,0 1,0 96V12A12,12 0,0 1,12 0Z" />
    <path
        android:fillColor="#FFFFFF"
        android:pathData="M54,18C35,18 20,31 20,48C20,65 34,78 52,78H63L78,91V75C85,69 89,60 89,48C89,31 74,18 54,18Z" />
    <path
        android:fillColor="#6750A4"
        android:pathData="M37,41H44L54,52L64,41H71V68H64V51L54,62L44,51V68H37Z" />
</vector>
"""
    write_text(icon_path, icon)

    manifest_paths = [
        UPSTREAM / "TMessagesProj" / "src" / "main" / "AndroidManifest.xml",
        UPSTREAM / "TMessagesProj" / "config" / "debug" / "AndroidManifest.xml",
        UPSTREAM / "TMessagesProj" / "config" / "debug" / "AndroidManifest_SDK23.xml",
        UPSTREAM / "TMessagesProj" / "config" / "release" / "AndroidManifest.xml",
        UPSTREAM / "TMessagesProj" / "config" / "release" / "AndroidManifest_SDK23.xml",
        UPSTREAM / "TMessagesProj" / "config" / "release" / "AndroidManifest_standalone.xml",
    ]
    for manifest_path in manifest_paths:
        if not manifest_path.is_file():
            continue
        manifest = read_text(manifest_path)
        manifest = manifest.replace(
            'android:icon="@mipmap/ic_launcher"',
            'android:icon="@drawable/ic_materialgram_icon"'
        )
        manifest = manifest.replace(
            'android:roundIcon="@mipmap/ic_launcher_round"',
            'android:roundIcon="@drawable/ic_materialgram_icon"'
        )
        manifest = re.sub(
            r'\s*<meta-data\s+android:name="com\.google\.android\.maps\.v2\.API_KEY"[^>]*/>',
            "", manifest
        )
        write_text(manifest_path, manifest)

    print("MaterialGram branding and package ID applied.")
    print("Telegram API credentials injected into the temporary build checkout (values hidden).")
    print("Unofficial-app-only features tied to Telegram's official package have been disabled.")


if __name__ == "__main__":
    main()
