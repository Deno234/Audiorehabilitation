# Croatian TTS Comparison Report

- All successful audio should be WAV mono 16 kHz 16-bit PCM.
- ASR WER/CER is a proxy for intelligibility, not clinical proof.
- Human listening review is recommended for final conclusions.

## Summary

| Adapter | Model/voice | Source model | Strategy | Class | Saturation | Type | Success rate | Format compliance |
|---|---|---|---|---:|---:|---|---:|---:|
| espeak_ng | hr | ChatGPT Plus | paper_style | N | 50.0 | word | 1.000 | 1.000 |
| coqui_vits_hr | tts_models/hr/cv/vits | ChatGPT Plus | paper_style | N | 50.0 | word | 1.000 | 1.000 |
| speecht5_hr | /mnt/d/Audiorehabilitation/models/speecht5_tts_hr | ChatGPT Plus | paper_style | N | 50.0 | word | 0.000 | 0.000 |

## Failures

- speecht5_hr / /mnt/d/Audiorehabilitation/models/speecht5_tts_hr: 
SpeechT5Tokenizer requires the SentencePiece library but it was not found in your environment. Check out the instructions on the
installation page of its repo: https://github.com/google/sentencepiece#installation and follow the ones
that match your environment. Please note that you may need to restart your runtime after installation.
 (2)
