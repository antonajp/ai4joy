"""Room Agent Text-to-Speech for Ambient Audio

This module provides TTS capabilities for the Room Agent to generate
ambient audio reactions (laughs, gasps, brief commentary) during scenes.

Uses Gemini's native TTS capability with response_modalities=["AUDIO"]
to generate speech that can be mixed with the main audio stream.
"""

import asyncio
import base64
import random
from typing import Optional

from google import genai
from google.genai import types

from app.config import get_settings
from app.audio.voice_config import get_voice_config
from app.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()

# Pre-defined ambient reactions for quick responses
AMBIENT_REACTIONS = {
    "positive": [
        "Ooh!",
        "Ha!",
        "Nice!",
        "Yes!",
        "Love it!",
        "Mmm!",
        "Ah!",
    ],
    "very_positive": [
        "Ha ha ha!",
        "Whoo!",
        "That's great!",
        "Amazing!",
        "Brilliant!",
        "Oh wow!",
    ],
    "negative": [
        "Ohh...",
        "Hmm...",
        "Uh oh...",
        "Oops...",
    ],
    "very_negative": [
        "Oh no...",
        "Yikes...",
        "Oof...",
    ],
    "neutral": [
        "Mm-hmm...",
        "Ah...",
        "Hmm...",
    ],
    "tension": [
        "*gasp*",
        "Ohh...",
        "Wait...",
    ],
    "laughter": [
        "Ha!",
        "Ha ha!",
        "Ha ha ha!",
        "Heh heh!",
    ],
}


class RoomAgentTTS:
    """Generates TTS audio for Room Agent ambient reactions.

    Uses Gemini's native TTS capability to generate short audio clips
    that can be mixed with the main audio stream at lower volume.
    """

    def __init__(self):
        """Initialize the Room Agent TTS generator."""
        self._client: Optional[genai.Client] = None
        self._voice_config = get_voice_config("room")
        logger.info(
            "RoomAgentTTS initialized",
            voice=self._voice_config.voice_name,
        )

    @property
    def client(self) -> genai.Client:
        """Get or create Gemini client."""
        if self._client is None:
            self._client = genai.Client(
                vertexai=True,
                project=settings.gcp_project_id,
                location=settings.gcp_location,
            )
        return self._client

    def get_reaction_text(
        self,
        sentiment: str,
        energy_level: float = 0.5,
    ) -> str:
        """Get a brief reaction text based on sentiment and energy.

        Args:
            sentiment: Sentiment level ("positive", "negative", "neutral", etc.)
            energy_level: Energy level from 0.0 to 1.0

        Returns:
            Brief reaction text suitable for TTS
        """
        # Map sentiment to reaction category
        if sentiment == "very_positive" or (sentiment == "positive" and energy_level > 0.7):
            category = "very_positive"
        elif sentiment == "positive":
            category = "positive"
        elif sentiment == "very_negative":
            category = "very_negative"
        elif sentiment == "negative":
            category = "negative"
        elif energy_level > 0.8:
            # High energy but neutral sentiment = laughter
            category = "laughter"
        else:
            category = "neutral"

        reactions = AMBIENT_REACTIONS.get(category, AMBIENT_REACTIONS["neutral"])
        return random.choice(reactions)

    async def generate_reaction_audio(
        self,
        text: str,
        timeout: float = 5.0,
    ) -> Optional[bytes]:
        """Generate TTS audio for a brief reaction.

        Uses Gemini's native TTS with the Room Agent voice (Charon)
        to generate ambient audio.

        Args:
            text: Brief text to speak (should be 1-5 words)
            timeout: Maximum time to wait for TTS generation

        Returns:
            Raw audio bytes (16-bit PCM, 24kHz) or None if failed
        """
        try:
            # Build the TTS request
            # Using Gemini's native TTS capability
            config = types.GenerateContentConfig(
                response_modalities=["AUDIO"],
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(
                            voice_name=self._voice_config.voice_name,
                        ),
                    ),
                ),
            )

            # Generate TTS audio
            response = await asyncio.wait_for(
                asyncio.to_thread(
                    self.client.models.generate_content,
                    model="gemini-2.5-flash-preview-tts",  # TTS-specific model
                    contents=text,
                    config=config,
                ),
                timeout=timeout,
            )

            # Extract audio data from response
            if response.candidates:
                for part in response.candidates[0].content.parts:
                    if hasattr(part, "inline_data") and part.inline_data:
                        # Decode base64 audio data
                        audio_data = base64.b64decode(part.inline_data.data)
                        logger.debug(
                            "Room TTS audio generated",
                            text=text,
                            audio_bytes=len(audio_data),
                        )
                        return audio_data

            logger.warning(
                "No audio data in TTS response",
                text=text,
            )
            return None

        except asyncio.TimeoutError:
            logger.warning(
                "Room TTS generation timed out",
                text=text,
                timeout=timeout,
            )
            return None
        except Exception as e:
            logger.error(
                "Room TTS generation failed",
                text=text,
                error=str(e),
            )
            return None

    async def generate_ambient_reaction(
        self,
        sentiment: str,
        energy_level: float = 0.5,
        context: Optional[str] = None,
    ) -> Optional[bytes]:
        """Generate ambient reaction audio based on sentiment.

        This is the main method for generating Room Agent reactions.
        It selects an appropriate reaction text and generates TTS audio.

        Args:
            sentiment: Sentiment level
            energy_level: Energy level from 0.0 to 1.0
            context: Optional context (currently unused, for future enhancement)

        Returns:
            Raw audio bytes or None if failed
        """
        # Get reaction text
        text = self.get_reaction_text(sentiment, energy_level)

        logger.info(
            "Generating ambient reaction",
            sentiment=sentiment,
            energy_level=energy_level,
            text=text,
        )

        # Generate audio
        return await self.generate_reaction_audio(text)


# Singleton instance
_room_tts: Optional[RoomAgentTTS] = None


def get_room_tts() -> RoomAgentTTS:
    """Get or create the Room Agent TTS singleton."""
    global _room_tts
    if _room_tts is None:
        _room_tts = RoomAgentTTS()
    return _room_tts
