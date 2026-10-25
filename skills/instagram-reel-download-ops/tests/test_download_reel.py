import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

try:
    from yt_dlp import YoutubeDL
    from yt_dlp.utils import DownloadError
except ImportError:
    YoutubeDL = None

SPEC = importlib.util.spec_from_file_location("download_reel", Path(__file__).resolve().parents[1] / "scripts/download_reel.py")
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)


class SingleReelTests(unittest.TestCase):
    def test_carousel_rejected_before_any_media_download(self):
        for info in ({"_type": "playlist", "id": "post", "entries": [{"id": "child"}]},
                     {"_type": "multi_video", "id": "post"},
                     {"id": "post", "entries": []}):
            with self.subTest(info=info), tempfile.TemporaryDirectory() as directory:
                with patch.object(M, "downloader_command", return_value=["yt-dlp"]), patch.object(M.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, json.dumps(info))) as run:
                    with self.assertRaisesRegex(ValueError, "Multi-item"):
                        M.download("https://www.instagram.com/reel/example/", Path(directory))
                    self.assertEqual(1, run.call_count, "must stop after metadata, before media download")
                    self.assertFalse((Path(directory) / "example.mp4").exists())

    def test_single_video_downloads_validated_metadata_and_records_child_identity(self):
        def invoke(command, **kwargs):
            if "--dump-single-json" in command:
                return subprocess.CompletedProcess(command, 0, json.dumps({"id": "media-1", "_type": "video", "webpage_url": "https://www.instagram.com/reel/example/"}))
            metadata = Path(command[command.index("--load-info-json") + 1])
            self.assertEqual("media-1", json.loads(metadata.read_text())["id"])
            self.assertNotIn("webpage_url", json.loads(metadata.read_text()))
            Path(command[command.index("--output") + 1].replace("%(ext)s", "mp4")).write_bytes(b"synthetic-media")
            return subprocess.CompletedProcess(command, 0)
        with tempfile.TemporaryDirectory() as directory, patch.object(M, "downloader_command", return_value=["yt-dlp"]), patch.object(M.subprocess, "run", side_effect=invoke), patch.object(M, "media_info", return_value={"duration_seconds": 1, "width": 10, "height": 10}):
            result = M.download("https://www.instagram.com/reel/example/", Path(directory))
            self.assertEqual("media-1", result["media_id"])
            self.assertEqual(b"synthetic-media", Path(result["path"]).read_bytes())
            self.assertEqual(64, len(result["sha256"]))

    def test_invalid_metadata_rejected(self):
        for info in ([], {}, {"id": "item", "_type": "url"}, {"id": ""}):
            with self.subTest(info=info), self.assertRaises(ValueError):
                M.single_video_id(info)

    def test_download_copy_omits_reextraction_url_without_changing_source(self):
        original = {"id": "media-1", "url": "https://media.example/video.mp4", "webpage_url": "https://www.instagram.com/reel/example/"}
        safe = M.download_metadata(original)
        self.assertNotIn("webpage_url", safe)
        self.assertEqual(original["url"], safe["url"])
        self.assertIn("webpage_url", original)

    @unittest.skipIf(YoutubeDL is None, "requires existing yt-dlp package for offline integration")
    def test_saved_info_failure_never_reextracts_url(self):
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory) / "source.json"
            p.write_text(json.dumps(M.download_metadata({"id": "media-1", "title": "Synthetic", "webpage_url": "https://www.instagram.com/reel/example/"})))
            with YoutubeDL({"quiet": True, "no_warnings": True}) as ydl:
                with patch.object(ydl, "process_ie_result", side_effect=DownloadError("synthetic expired format")), patch.object(ydl, "download") as refetch:
                    with self.assertRaises(DownloadError):
                        ydl.download_with_info_file(str(p))
                    refetch.assert_not_called()

    def test_existing_file_remains_untouched(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(M.subprocess, "run") as run:
            output = Path(directory) / "example.mp4"
            output.write_bytes(b"existing")
            with self.assertRaises(FileExistsError):
                M.download("https://www.instagram.com/reel/example/", Path(directory))
            self.assertEqual(b"existing", output.read_bytes())
            run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
