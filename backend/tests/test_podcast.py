"""Tests for the audio digest (script generation, synthesis, Discord upload)"""

from unittest.mock import MagicMock, patch

import pytest

from app.services.delivery import DeliveryService
from app.services.podcast import PodcastService

SCRIPT = """ALEX: Guten Morgen und willkommen zum Daily Digest.
SARA: Heute geht es um die Lage im Nahen Osten.

(Pause)
ALEX: Fangen wir mit der Waffenruhe an.
SARA:
SARA: Danke fürs Zuhören."""


class TestScriptParsing:
    def test_keeps_only_speaker_marked_lines(self):
        turns = PodcastService.parse_script(SCRIPT)

        # The stage direction, the blank line and the empty SARA line are dropped
        assert len(turns) == 4
        assert [text for _, text in turns] == [
            "Guten Morgen und willkommen zum Daily Digest.",
            "Heute geht es um die Lage im Nahen Osten.",
            "Fangen wir mit der Waffenruhe an.",
            "Danke fürs Zuhören.",
        ]

    def test_alternates_between_the_two_voices(self):
        voices = [voice for voice, _ in PodcastService.parse_script(SCRIPT)]

        assert voices[0] == voices[2]  # both ALEX
        assert voices[1] == voices[3]  # both SARA
        assert voices[0] != voices[1]

    def test_script_without_markers_yields_nothing(self):
        assert PodcastService.parse_script("Just prose, no speakers here.") == []


class TestBuildEpisode:
    def test_returns_none_when_disabled(self, monkeypatch):
        monkeypatch.setattr("app.services.podcast.settings.PODCAST_ENABLED", False)

        assert PodcastService.build_episode("digest") is None

    def test_returns_none_without_credentials(self, monkeypatch):
        monkeypatch.setattr("app.services.podcast.settings.PODCAST_ENABLED", True)
        monkeypatch.delenv("GOOGLE_APPLICATION_CREDENTIALS", raising=False)

        assert PodcastService.build_episode("digest") is None

    def test_concatenates_one_segment_per_line(self, monkeypatch):
        monkeypatch.setattr("app.services.podcast.settings.PODCAST_ENABLED", True)

        client = MagicMock()
        client.synthesize.side_effect = lambda text, **kwargs: f"<{text[:4]}>".encode()

        with (
            patch.object(PodcastService, "generate_script", return_value=SCRIPT),
            patch("app.services.podcast.GoogleTTSClient") as tts_cls,
        ):
            tts_cls.is_configured.return_value = True
            tts_cls.return_value = client

            episode = PodcastService.build_episode("digest")

        assert episode == b"<Gute><Heut><Fang><Dank>"
        assert client.synthesize.call_count == 4

    def test_script_failure_does_not_raise(self, monkeypatch):
        monkeypatch.setattr("app.services.podcast.settings.PODCAST_ENABLED", True)

        with (
            patch.object(PodcastService, "generate_script", side_effect=RuntimeError("groq down")),
            patch("app.services.podcast.GoogleTTSClient") as tts_cls,
        ):
            tts_cls.is_configured.return_value = True

            assert PodcastService.build_episode("digest") is None

    def test_synthesis_failure_does_not_raise(self, monkeypatch):
        monkeypatch.setattr("app.services.podcast.settings.PODCAST_ENABLED", True)

        client = MagicMock()
        client.synthesize.side_effect = RuntimeError("quota exceeded")

        with (
            patch.object(PodcastService, "generate_script", return_value=SCRIPT),
            patch("app.services.podcast.GoogleTTSClient") as tts_cls,
        ):
            tts_cls.is_configured.return_value = True
            tts_cls.return_value = client

            assert PodcastService.build_episode("digest") is None


class TestDiscordUpload:
    WEBHOOK = "https://discord.com/api/webhooks/123456/abcdef"

    @pytest.mark.parametrize("status_code", [200, 204])
    def test_accepts_both_success_codes(self, status_code):
        with patch("app.services.delivery.requests.post") as mock_post:
            mock_post.return_value = MagicMock(status_code=status_code)

            ok = DeliveryService.deliver_file_via_discord(self.WEBHOOK, "episode.mp3", b"audio")

        assert ok is True
        files = mock_post.call_args[1]["files"]
        assert files["file"][0] == "episode.mp3"
        assert files["file"][2] == "audio/mpeg"

    def test_rejects_file_above_the_limit(self):
        with patch("app.services.delivery.requests.post") as mock_post:
            ok = DeliveryService.deliver_file_via_discord(
                self.WEBHOOK, "episode.mp3", b"x" * 1024, max_bytes=512
            )

        assert ok is False
        mock_post.assert_not_called()

    def test_rejects_empty_payload(self):
        with patch("app.services.delivery.requests.post") as mock_post:
            assert DeliveryService.deliver_file_via_discord(self.WEBHOOK, "episode.mp3", b"") is False
            mock_post.assert_not_called()

    def test_reports_failure_on_error_status(self):
        with patch("app.services.delivery.requests.post") as mock_post:
            mock_post.return_value = MagicMock(status_code=413, text="Payload too large")

            assert DeliveryService.deliver_file_via_discord(self.WEBHOOK, "e.mp3", b"audio") is False


class TestFilename:
    def test_filename_carries_the_date(self):
        from datetime import UTC, datetime

        name = PodcastService.episode_filename(datetime(2026, 4, 17, tzinfo=UTC))

        assert name == "news-digest-2026-04-17.mp3"
