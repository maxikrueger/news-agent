"""Google Cloud Text-to-Speech integration for the audio digest.

Authentication goes through GOOGLE_APPLICATION_CREDENTIALS, the path to a
service-account JSON file — the same mechanism every Google Cloud client
library uses. Without it the podcast is skipped; the text digest is unaffected.

The google-cloud-texttospeech package is imported lazily so that neither the
package nor the credentials are needed to import or run the rest of the app.
"""

import logging
import os

from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


class TTSNotConfigured(Exception):
    """No usable Google Cloud credentials, or the client library is missing."""


class GoogleTTSClient:
    """Synthesises single utterances; the caller assembles the episode."""

    def __init__(self) -> None:
        if not self.is_configured():
            raise TTSNotConfigured("GOOGLE_APPLICATION_CREDENTIALS is not set or does not point at a file")
        try:
            from google.cloud import texttospeech
        except ImportError as exc:  # pragma: no cover - depends on the install extra
            raise TTSNotConfigured("google-cloud-texttospeech is not installed") from exc

        self._tts = texttospeech
        self._client = texttospeech.TextToSpeechClient()

    @staticmethod
    def is_configured() -> bool:
        """True when a service-account file is configured and present."""
        path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "").strip()
        return bool(path) and os.path.isfile(path)

    @retry(
        wait=wait_exponential(multiplier=1, min=2, max=30),
        stop=stop_after_attempt(3),
        reraise=True,
    )
    def synthesize(
        self,
        text: str,
        voice_name: str,
        language_code: str = "de-DE",
        speaking_rate: float = 1.0,
    ) -> bytes:
        """Render one line of dialogue to MP3 bytes."""
        response = self._client.synthesize_speech(
            input=self._tts.SynthesisInput(text=text),
            voice=self._tts.VoiceSelectionParams(language_code=language_code, name=voice_name),
            audio_config=self._tts.AudioConfig(
                audio_encoding=self._tts.AudioEncoding.MP3,
                speaking_rate=speaking_rate,
            ),
        )
        return bytes(response.audio_content)
