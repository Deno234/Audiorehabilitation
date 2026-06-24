# Croatian TTS Comparison Report

- All successful audio should be WAV mono 16 kHz 16-bit PCM.
- ASR WER/CER is a proxy for intelligibility, not clinical proof.
- Human listening review is recommended for final conclusions.

## Summary

| Adapter | Model/voice | Source model | Strategy | Class | Saturation | Type | Success rate | Format compliance |
|---|---|---|---|---:|---:|---|---:|---:|
| espeak_ng | hr | ChatGPT Plus | paper_style | N | 50.0 | word | 1.000 | 1.000 |
| coqui_vits_hr | tts_models/hr/cv/vits | ChatGPT Plus | paper_style | N | 50.0 | word | 1.000 | 1.000 |
| speecht5_hr | /mnt/d/Audiorehabilitation/models/speecht5_tts_hr | ChatGPT Plus | paper_style | N | 50.0 | word | 1.000 | 1.000 |

## Failures

- No synthesis failures recorded.
