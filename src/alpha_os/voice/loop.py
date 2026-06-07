"""Server-side always-on wake phrase listener → Hermes command relay."""

from __future__ import annotations

import asyncio
import logging
from typing import Awaitable, Callable, Optional

from alpha_os.voice.wakeword import (
    DEFAULT_WAKE_WORD,
    contains_wake_word,
    normalize_wake_word,
    strip_wake_word,
)

logger = logging.getLogger("alpha_os.voice")

TranscriptHandler = Callable[[str], Awaitable[None]]


def voice_available() -> bool:
    try:
        import speech_recognition  # noqa: F401
        return True
    except ImportError:
        return False


class VoiceLoop:
    """Background mic listener. Requires `pip install alpha-os[voice]`."""

    def __init__(
        self,
        wake_word: str = DEFAULT_WAKE_WORD,
        on_transcript: Optional[TranscriptHandler] = None,
    ):
        self.wake_word = normalize_wake_word(wake_word)
        self.on_transcript = on_transcript
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._armed = False

    async def start(self) -> bool:
        if not voice_available():
            logger.warning(
                "Voice extras not installed — use: pip install 'alpha-os[voice]' "
                "or use the browser wake listener in the dashboard"
            )
            return False
        if self._running:
            return True
        self._running = True
        self._task = asyncio.create_task(self._run())
        logger.info("Voice loop started (wake phrase: %s)", self.wake_word)
        return True

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    async def _run(self) -> None:
        import speech_recognition as sr

        recognizer = sr.Recognizer()
        mic = sr.Microphone()
        loop = asyncio.get_event_loop()

        with mic as source:
            recognizer.adjust_for_ambient_noise(source, duration=0.5)

        while self._running:
            try:
                with mic as source:
                    audio = await loop.run_in_executor(
                        None,
                        lambda: recognizer.listen(source, timeout=5, phrase_time_limit=15),
                    )
                text = await loop.run_in_executor(
                    None,
                    lambda: recognizer.recognize_google(audio),
                )
                text = (text or "").strip()
                if not text:
                    continue

                if contains_wake_word(text, self.wake_word):
                    command = strip_wake_word(text, self.wake_word)
                    if command and self.on_transcript:
                        logger.info("Voice command: %s", command)
                        await self.on_transcript(command)
                    elif not command:
                        self._armed = True
                        logger.info("Wake phrase heard — awaiting command")
                    continue

                if self._armed and self.on_transcript:
                    self._armed = False
                    logger.info("Voice command (armed): %s", text)
                    await self.on_transcript(text)

            except sr.WaitTimeoutError:
                continue
            except sr.UnknownValueError:
                continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning("Voice loop error: %s", e)
                await asyncio.sleep(2)