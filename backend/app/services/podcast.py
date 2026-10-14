"""Turn a finished digest into a two-voice audio episode.

The same Groq model that writes the digest rewrites it as a dialogue between a
host and a co-host, each line prefixed with a speaker marker. Every line is then
synthesised with its own voice and the MP3 segments are concatenated into one
episode, which the delivery layer attaches to the Discord message.

The whole step is optional. It runs only when PODCAST_ENABLED is set and Google
credentials are present; any failure is logged and the text digest goes out
regardless.
"""

import logging
from datetime import UTC, datetime

from app.config import settings
from app.integrations.groq import GroqClient
from app.integrations.tts import GoogleTTSClient, TTSNotConfigured

logger = logging.getLogger(__name__)

HOST_MARKER = "ALEX:"
GUEST_MARKER = "SARA:"


class PodcastService:
    @staticmethod
    def is_enabled() -> bool:
        """True when the feature is switched on and credentials are available."""
        return bool(settings.PODCAST_ENABLED) and GoogleTTSClient.is_configured()

    @staticmethod
    def generate_script(digest: str, language: str = "Deutsch") -> str:
        """Rewrite the digest as a dialogue, one speaker marker per line."""
        groq = GroqClient()
        today = datetime.now(UTC).strftime("%d.%m.%Y")

        prompt = f"""You write a daily news podcast in {language}. Today is {today}.

Here is today's digest:

{digest}

---
TASK:
Write a natural conversation script for two hosts:
- ALEX: the main host, explains the news factually and in a clear order
- SARA: the co-host, asks good follow-up questions and adds context

RULES:
- Every line starts with exactly "{HOST_MARKER}" or "{GUEST_MARKER}" — no other format
- Natural spoken {language}, no bullet points and no markdown
- Short, easy sentences: this is spoken, not read
- Cover every article from the digest
- Intro: Alex welcomes the listener, Sara opens the first topic
- Outro: a short shared conclusion and a goodbye
- Target length: about five minutes of speech (roughly 750 words)

Start with the script, no preamble."""

        return groq.create_completion(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.6,
            max_tokens=2048,
        )

    @staticmethod
    def parse_script(script: str) -> list[tuple[str, str]]:
        """Split a script into (voice_name, text) pairs, dropping unmarked lines.

        The model occasionally emits a stage direction or a blank separator; those
        carry no speaker and are skipped rather than read aloud in the wrong voice.
        """
        turns: list[tuple[str, str]] = []
        for raw_line in script.strip().splitlines():
            line = raw_line.strip()
            if line.startswith(HOST_MARKER):
                text, voice = line[len(HOST_MARKER) :].strip(), settings.PODCAST_VOICE_HOST
            elif line.startswith(GUEST_MARKER):
                text, voice = line[len(GUEST_MARKER) :].strip(), settings.PODCAST_VOICE_GUEST
            else:
                continue
            if text:
                turns.append((voice, text))
        return turns

    @staticmethod
    def build_episode(digest: str, language: str = "Deutsch") -> bytes | None:
        """Produce the episode as MP3 bytes, or None if it cannot be produced.

        Returning None is a normal outcome — the feature is off, not configured,
        or the script came back without a single usable line.
        """
        if not PodcastService.is_enabled():
            return None

        try:
            script = PodcastService.generate_script(digest, language=language)
        except Exception as e:
            logger.error("Could not generate podcast script: %s", e)
            return None

        turns = PodcastService.parse_script(script)
        if not turns:
            logger.error("Podcast script contained no speaker-marked lines")
            return None

        try:
            client = GoogleTTSClient()
        except TTSNotConfigured as e:
            logger.warning("Podcast skipped: %s", e)
            return None

        # MP3 frames are self-contained, so concatenating the per-line segments
        # yields a single playable file without re-encoding.
        segments: list[bytes] = []
        for voice, text in turns:
            try:
                segments.append(
                    client.synthesize(
                        text,
                        voice_name=voice,
                        language_code=settings.PODCAST_LANGUAGE_CODE,
                        speaking_rate=settings.PODCAST_SPEAKING_RATE,
                    )
                )
            except Exception as e:
                logger.error("Text-to-speech failed on a line, aborting episode: %s", e)
                return None

        episode = b"".join(segments)
        logger.info("Podcast rendered: %d lines, %d KB", len(turns), len(episode) // 1024)
        return episode

    @staticmethod
    def episode_filename(now: datetime | None = None) -> str:
        stamp = (now or datetime.now(UTC)).strftime("%Y-%m-%d")
        return f"news-digest-{stamp}.mp3"
