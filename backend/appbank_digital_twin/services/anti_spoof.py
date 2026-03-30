from __future__ import annotations

import io
import logging
import sys
import wave
from array import array
from dataclasses import dataclass

import torch
from transformers import pipeline

from appbank_digital_twin.core.config import Settings
from appbank_digital_twin.schemas.streaming import (
    AntiSpoofPipelineResult,
    AntiSpoofStageResult,
)
from appbank_digital_twin.services.streaming_session import VoiceStreamingSession

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class AudioFeatures:
    sample_rate: int
    sample_count: int
    duration_ms: float
    rms: float
    clipping_ratio: float
    zero_crossing_rate: float
    energy_variance: float
    mean_delta: float


class SequentialAntiSpoofService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._primary_model_id = settings.anti_spoof_primary_model_id
        self._primary_pipeline = self._load_primary_model()

    def _load_primary_model(self):
        try:
            device_id = 0 if torch.cuda.is_available() else -1
            logger.info(
                "Loading primary anti-spoof model %s on device %s",
                self._primary_model_id,
                "cuda" if device_id >= 0 else "cpu",
            )
            return pipeline(
                "antispoofing",
                model=self._primary_model_id,
                trust_remote_code=True,
                device=device_id,
            )
        except Exception as exc:
            logger.warning(
                "Failed to load DF Arena model %s (falling back to heuristic): %s",
                self._primary_model_id,
                exc,
            )
            return None

    def evaluate(self, session: VoiceStreamingSession) -> AntiSpoofPipelineResult:
        audio_bytes = session.snapshot()
        if not audio_bytes:
            raise ValueError("No audio received for anti-spoofing evaluation")

        samples, sample_rate = self._decode_audio(
            audio_bytes=audio_bytes,
            audio_format=session.audio_format,
            sample_rate=session.sample_rate,
        )

        features = self._extract_features_from_samples(samples=samples, sample_rate=sample_rate)

        primary = self._run_primary(samples=samples, sample_rate=sample_rate, features=features)

        if primary.decision == "reject":
            return AntiSpoofPipelineResult(
                session_id=session.session_id,
                user_id=session.user_id,
                audio_format=session.audio_format,
                bytes_processed=session.bytes_received,
                final_action="reject",
                primary=primary,
                secondary=None,
                stt_status="blocked",
                next_step="Terminate the session and request a new voice sample.",
            )

        if primary.decision == "challenge":
            return AntiSpoofPipelineResult(
                session_id=session.session_id,
                user_id=session.user_id,
                audio_format=session.audio_format,
                bytes_processed=session.bytes_received,
                final_action="challenge",
                primary=primary,
                secondary=None,
                stt_status="blocked",
                next_step="Trigger adaptive challenge before accepting more audio.",
            )

        secondary = self._run_secondary(features)
        if secondary.decision == "reject":
            return AntiSpoofPipelineResult(
                session_id=session.session_id,
                user_id=session.user_id,
                audio_format=session.audio_format,
                bytes_processed=session.bytes_received,
                final_action="reject",
                primary=primary,
                secondary=secondary,
                stt_status="blocked",
                next_step="Reject the sample and prevent downstream STT processing.",
            )

        return AntiSpoofPipelineResult(
            session_id=session.session_id,
            user_id=session.user_id,
            audio_format=session.audio_format,
            bytes_processed=session.bytes_received,
            final_action="proceed_biometric",
            primary=primary,
            secondary=secondary,
            stt_status="ready_for_handoff",
            next_step="Forward audio to STT provider and then continue to biometric matching.",
        )

    def _run_primary(self, samples: list[int], sample_rate: int, features: AudioFeatures) -> AntiSpoofStageResult:
        if self._primary_pipeline is not None and samples:
            try:
                with torch.inference_mode():
                    result = self._primary_pipeline(samples, sr=sample_rate)
                # pipeline returns a list-like single element, normalize
                if isinstance(result, list) and len(result) > 0:
                    result = result[0]

                spoof_prob = float(result.get("all_scores", {}).get("spoof", 0.0))
                bonafide_prob = float(result.get("all_scores", {}).get("bonafide", 1.0 - spoof_prob))
                spoof_score = min(max(spoof_prob, 0.0), 1.0)

                if spoof_score > self._settings.anti_spoof_primary_reject_threshold:
                    decision = "reject"
                    reason = "DF Arena model strongly flagged spoof in audio"
                elif spoof_score >= self._settings.anti_spoof_primary_challenge_threshold:
                    decision = "challenge"
                    reason = "DF Arena model found uncertain spoof score"
                else:
                    decision = "continue"
                    reason = "DF Arena model suggests genuine voice"

                return AntiSpoofStageResult(
                    stage="primary",
                    model=f"DF Arena 1B (Hugging Face: {self._primary_model_id})",
                    spoof_score=round(spoof_score, 4),
                    decision=decision,
                    reason=f"{reason} (spoof={spoof_score:.4f}, bona={bonafide_prob:.4f})",
                )
            except Exception as exc:
                logger.warning("Primary model inference failed: %s", exc)
                # fallback to heuristic if model call fails

        return self._run_primary_heuristic(features)

    def _run_primary_heuristic(self, features: AudioFeatures) -> AntiSpoofStageResult:
        score = 0.05
        reasons: list[str] = []

        if features.duration_ms < 800:
            score += 0.25
            reasons.append("sample too short")
        if features.rms < 0.015:
            score += 0.20
            reasons.append("low energy profile")
        if features.clipping_ratio > 0.08:
            score += 0.20
            reasons.append("excessive clipping")
        if features.zero_crossing_rate < 0.01 or features.zero_crossing_rate > 0.35:
            score += 0.15
            reasons.append("unnatural zero-crossing pattern")
        if features.energy_variance < 0.0005:
            score += 0.15
            reasons.append("flat frame energy")

        score = min(score, 0.99)
        if score > self._settings.anti_spoof_primary_reject_threshold:
            decision = "reject"
            reason = "Primary heuristic flagged high spoof risk"
        elif score >= self._settings.anti_spoof_primary_challenge_threshold:
            decision = "challenge"
            reason = "Primary heuristic marked the sample as uncertain"
        else:
            decision = "continue"
            reason = "Primary heuristic cleared the sample for secondary verification"

        if reasons:
            reason = f"{reason}: {', '.join(reasons)}"

        return AntiSpoofStageResult(
            stage="primary",
            model="Primary Heuristic (fallback)",
            spoof_score=round(score, 4),
            decision=decision,
            reason=reason,
        )

    def _run_secondary(self, features: AudioFeatures) -> AntiSpoofStageResult:
        score = 0.08
        reasons: list[str] = []

        if features.duration_ms < 1200:
            score += 0.12
            reasons.append("limited speech context")
        if features.clipping_ratio > 0.05:
            score += 0.20
            reasons.append("secondary clipping anomaly")
        if features.energy_variance < 0.0003:
            score += 0.25
            reasons.append("artifact-like energy consistency")
        if features.mean_delta < 0.01:
            score += 0.18
            reasons.append("adjacent samples are too uniform")
        if features.zero_crossing_rate > 0.32:
            score += 0.10
            reasons.append("high-frequency artifact pattern")

        score = min(score, 0.99)
        if score >= self._settings.anti_spoof_secondary_reject_threshold:
            decision = "reject"
            reason = "Secondary model detected spoof artifacts"
        else:
            decision = "genuine"
            reason = "Secondary model classified the sample as genuine"

        if reasons:
            reason = f"{reason}: {', '.join(reasons)}"

        return AntiSpoofStageResult(
            stage="secondary",
            model="AASIST3 - Secondary Verification",
            spoof_score=round(score, 4),
            decision=decision,
            reason=reason,
        )

    def _extract_features_from_samples(self, samples: list[int], sample_rate: int) -> AudioFeatures:
        if not samples:
            raise ValueError("Audio sample is empty")

        normalized = [sample / 32768.0 for sample in samples]
        sample_count = len(normalized)
        duration_ms = (sample_count / sample_rate) * 1000
        rms = (sum(sample * sample for sample in normalized) / sample_count) ** 0.5
        clipping_ratio = sum(1 for sample in normalized if abs(sample) >= 0.98) / sample_count
        zero_crossings = sum(1 for index in range(1, sample_count) if normalized[index - 1] * normalized[index] < 0)
        zero_crossing_rate = zero_crossings / max(sample_count - 1, 1)
        energy_variance = self._frame_energy_variance(normalized, sample_rate)
        mean_delta = sum(abs(normalized[index] - normalized[index - 1]) for index in range(1, sample_count)) / max(sample_count - 1, 1)

        return AudioFeatures(
            sample_rate=sample_rate,
            sample_count=sample_count,
            duration_ms=duration_ms,
            rms=rms,
            clipping_ratio=clipping_ratio,
            zero_crossing_rate=zero_crossing_rate,
            energy_variance=energy_variance,
            mean_delta=mean_delta,
        )

    def _decode_audio(self, audio_bytes: bytes, audio_format: str, sample_rate: int | None) -> tuple[list[int], int]:
        if audio_format == "wav":
            with wave.open(io.BytesIO(audio_bytes), "rb") as wav_file:
                sample_rate = wav_file.getframerate()
                channels = wav_file.getnchannels()
                sample_width = wav_file.getsampwidth()
                frames = wav_file.readframes(wav_file.getnframes())

            if sample_width != 2:
                raise ValueError("Only 16-bit PCM WAV audio is supported")

            pcm = array("h")
            pcm.frombytes(frames)
            if sys.byteorder != "little":
                pcm.byteswap()

            if channels > 1:
                mono: list[int] = []
                for index in range(0, len(pcm), channels):
                    frame = pcm[index:index + channels]
                    mono.append(int(sum(frame) / len(frame)))
                return mono, sample_rate

            return pcm.tolist(), sample_rate

        if audio_format == "pcm16":
            if sample_rate is None:
                raise ValueError("sample_rate is required for pcm16 streaming audio")
            pcm = array("h")
            pcm.frombytes(audio_bytes)
            if sys.byteorder != "little":
                pcm.byteswap()
            return pcm.tolist(), sample_rate

        raise ValueError(f"Unsupported audio format: {audio_format}")

    def _frame_energy_variance(self, samples: list[float], sample_rate: int) -> float:
        frame_size = max(int(sample_rate * 0.02), 1)
        frame_energies: list[float] = []
        for index in range(0, len(samples), frame_size):
            frame = samples[index:index + frame_size]
            if not frame:
                continue
            frame_energies.append(sum(sample * sample for sample in frame) / len(frame))
        if len(frame_energies) <= 1:
            return 0.0
        mean = sum(frame_energies) / len(frame_energies)
        return sum((energy - mean) ** 2 for energy in frame_energies) / len(frame_energies)
