"""In-process STT using Faster Whisper."""
import logging
import os
from dataclasses import dataclass
from typing import Optional

import numpy as np
from faster_whisper import WhisperModel

from livekit import rtc
from livekit.agents import APIConnectionError, APIConnectOptions, stt
from livekit.agents.utils import AudioBuffer

from .utils import find_time

logger = logging.getLogger(__name__)


@dataclass
class WhisperOptions:
    """Configuration options for WhisperSTT."""
    language: str
    model: str
    device: str
    compute_type: str
    model_cache_directory: Optional[str] = None


class WhisperSTT(stt.STT):
    """In-process STT implementation using Faster Whisper."""
    
    def __init__(
        self,
        language: str = "ur",  # Urdu
        model: str = "base",  # base, small, medium, large-v2, large-v3
        device: str = "cuda",  # cuda or cpu
        compute_type: str = "float16",  # float16, float32, int8
        model_cache_directory: Optional[str] = None,
    ):
        """Initialize the WhisperSTT instance.
        
        Args:
            language: Language code (ur for Urdu, en for English)
            model: Whisper model size
            device: Device to use (cuda or cpu)
            compute_type: Compute type for GPU
            model_cache_directory: Directory to cache models
        """
        super().__init__(
            capabilities=stt.STTCapabilities(streaming=False, interim_results=False)
        )
        
        self._opts = WhisperOptions(
            language=language,
            model=model,
            device=device,
            compute_type=compute_type,
            model_cache_directory=model_cache_directory,
        )
        
        self._model = None
        self._initialize_model()

    def _initialize_model(self):
        """Initialize the Whisper model."""
        device = self._opts.device
        compute_type = self._opts.compute_type
        
        logger.info(f"Loading Whisper model: {self._opts.model} on {device} with {compute_type}")
        
        # Ensure cache directory exists
        model_cache_dir = self._opts.model_cache_directory
        if model_cache_dir:
            os.makedirs(model_cache_dir, exist_ok=True)
            logger.info(f"Using model cache directory: {model_cache_dir}")
        
        try:
            self._model = WhisperModel(
                model_size_or_path=self._opts.model,
                device=device,
                compute_type=compute_type,
                download_root=model_cache_dir
            )
            logger.info("✅ Whisper model loaded successfully")
        except Exception as e:
            logger.error(f"❌ Failed to load Whisper model: {e}")
            # Fallback to CPU if CUDA fails
            if device == "cuda":
                logger.warning("Falling back to CPU...")
                self._opts.device = "cpu"
                self._opts.compute_type = "int8"
                self._model = WhisperModel(
                    model_size_or_path=self._opts.model,
                    device="cpu",
                    compute_type="int8",
                    download_root=model_cache_dir
                )
                logger.info("✅ Whisper model loaded on CPU")

    async def _recognize_impl(
        self,
        buffer: AudioBuffer,
        *,
        language: Optional[str],
        conn_options: APIConnectOptions,
    ) -> stt.SpeechEvent:
        """Implement speech recognition.
        
        Args:
            buffer: Audio buffer
            language: Language to detect (overrides default)
            conn_options: Connection options
            
        Returns:
            Speech recognition event
        """
        try:
            logger.debug("Transcribing audio with Faster Whisper")
            
            # Use provided language or default
            target_language = language or self._opts.language
            
            # Convert audio buffer to WAV bytes
            audio_data = rtc.combine_audio_frames(buffer).to_wav_bytes()
            
            # Convert WAV to numpy array
            audio_array = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0
            
            # Transcribe with timing
            with find_time('STT_inference'):
                segments, info = self._model.transcribe(
                    audio_array,
                    language=target_language,
                    beam_size=1,
                    best_of=1,
                    condition_on_previous_text=True,
                    vad_filter=False,
                    vad_parameters=dict(min_silence_duration_ms=500),
                )

            # Combine all segments
            segments_list = list(segments)
            full_text = " ".join(segment.text.strip() for segment in segments_list)
            
            logger.info(f"Transcribed: {full_text}")

            return stt.SpeechEvent(
                type=stt.SpeechEventType.FINAL_TRANSCRIPT,
                alternatives=[
                    stt.SpeechData(
                        text=full_text or "",
                        language=target_language,
                    )
                ],
            )

        except Exception as e:
            logger.error(f"Error in speech recognition: {e}", exc_info=True)
            raise APIConnectionError() from e
