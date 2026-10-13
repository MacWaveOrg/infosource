#!/usr/bin/env python3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from check_package_updates import (
    classify_arch,
    discover_updates,
    matching_asset,
    MACOS_RE,
    parse_github_release_url,
    version_from_tag,
    version_tuple,
)


class PackageUpdateTests(unittest.TestCase):
    def test_architecture_keywords(self):
        self.assertEqual(classify_arch("bat-v1.2-aarch64-apple-darwin.tar.gz"), "arm64")
        self.assertEqual(classify_arch("fzf-1.2-darwin_arm64.tar.gz"), "arm64")
        self.assertEqual(classify_arch("tool-macos-x86_64.zip"), "amd64")
        self.assertEqual(classify_arch("tool-darwin-amd64"), "amd64")
        self.assertIsNone(classify_arch("tool-universal-macos.zip"))
        self.assertIsNone(classify_arch("tool-arm64-x86_64-macos.zip"))
        self.assertEqual(classify_arch("tool-linux-aarch64.tar.gz"), "arm64")
        self.assertIsNotNone(MACOS_RE.search("tool-mac-arm64.zip"))
        self.assertIsNotNone(MACOS_RE.search("tool-macos-arm64.zip"))

    def test_version_parsing_is_conservative(self):
        self.assertEqual(version_from_tag("v1.2.3"), "1.2.3")
        self.assertEqual(version_from_tag("jq-1.8.3"), "1.8.3")
        self.assertEqual(version_from_tag("3.1.738"), "3.1.738")
        self.assertIsNone(version_from_tag("v1.0-macwaveteam2"))
        self.assertEqual(version_tuple("1.2.3"), (1, 2, 3))
        self.assertIsNone(version_tuple("1.2.3-procursus7"))

    def test_only_github_release_urls_are_supported(self):
        self.assertEqual(
            parse_github_release_url(
                "https://github.com/junegunn/fzf/releases/download/v1.2/fzf-darwin_arm64.tar.gz"
            ),
            "junegunn/fzf",
        )
        self.assertIsNone(parse_github_release_url("https://raw.githubusercontent.com/a/b/v1/file"))
        self.assertIsNone(parse_github_release_url("http://github.com/a/b/releases/download/v1/file"))

    def test_asset_matching_uses_architecture_and_existing_filename_shape(self):
        assets = [
            {"name": "fzf-0.74.6-darwin_amd64.tar.gz"},
            {"name": "fzf-0.74.6-darwin_arm64.tar.gz"},
            {"name": "fzf-0.74.6-darwin_universal.tar.gz"},
            {"name": "fzf-0.74.6-darwin_arm64.tar.gz.sha256"},
        ]
        old_url = "https://github.com/junegunn/fzf/releases/download/v0.74.5/fzf-0.74.5-darwin_arm64.tar.gz"
        match, reason = matching_asset(assets, old_url, "0.74.5", "0.74.6", "arm64")
        self.assertEqual(match["name"], "fzf-0.74.6-darwin_arm64.tar.gz")
        self.assertEqual(reason, "")
        match, _ = matching_asset(assets, old_url, "0.74.5", "0.74.6", "amd64")
        self.assertEqual(match["name"], "fzf-0.74.6-darwin_amd64.tar.gz")

    def test_ambiguous_asset_set_is_rejected(self):
        assets = [
            {"name": "tool-2.1-macos-arm64.tar.gz"},
            {"name": "tool-2.1-macos-arm64.tar.gz"},
        ]
        old_url = "https://github.com/example/tool/releases/download/v2.0/tool-2.0-macos-arm64.tar.gz"
        match, reason = matching_asset(assets, old_url, "2.0", "2.1", "arm64")
        self.assertIsNone(match)
        self.assertIn("2 arm64", reason)

    def test_versionless_asset_names_can_match_exactly(self):
        assets = [{"name": "jq-macos-arm64"}]
        old_url = "https://github.com/jqlang/jq/releases/download/jq-1.8.2/jq-macos-arm64"
        match, reason = matching_asset(assets, old_url, "1.8.2", "1.9.0", "arm64")
        self.assertEqual(match["name"], "jq-macos-arm64")
        self.assertEqual(reason, "")

    def test_discovery_creates_records_for_both_architectures(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            digest = "a" * 64
            old_digest = "b" * 64
            assets = []
            for arch, asset_arch in (("arm64", "arm64"), ("amd64", "x86_64")):
                package_dir = root / "pkg" / f"pkginfo_{arch}" / "tool"
                package_dir.mkdir(parents=True)
                (package_dir / "_tool@1.2.0").write_text(
                    f'sha256: "{old_digest}"\n'
                    f'url: "https://github.com/example/tool/releases/download/v1.2.0/tool-1.2.0-macos-{asset_arch}.zip"\n',
                    encoding="utf-8",
                )
                (package_dir / "_tool@common").write_text(
                    'hom: "https://github.com/example/tool"\n',
                    encoding="utf-8",
                )
                asset_name = f"tool-1.3.0-macos-{asset_arch}.zip"
                assets.append(
                    {
                        "name": asset_name,
                        "digest": f"sha256:{digest}",
                        "browser_download_url": (
                            f"https://github.com/example/tool/releases/download/v1.3.0/{asset_name}"
                        ),
                    }
                )

            release = {"tag_name": "v1.3.0", "assets": assets}
            with patch("check_package_updates.github_json", return_value=release) as fetch:
                updates, skipped = discover_updates(root)

        self.assertEqual(
            {(item["package"], item["version"], item["arch"]) for item in updates},
            {("tool", "1.3.0", "arm64"), ("tool", "1.3.0", "amd64")},
        )
        self.assertEqual(skipped, [])
        fetch.assert_called_once()


if __name__ == "__main__":
    unittest.main()
