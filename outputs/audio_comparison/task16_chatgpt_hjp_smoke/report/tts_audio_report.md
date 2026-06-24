# Croatian TTS Comparison Report

- All successful audio should be WAV mono 16 kHz 16-bit PCM.
- ASR WER/CER is a proxy for intelligibility, not clinical proof.
- Human listening review is recommended for final conclusions.

## Summary

| Adapter | Model/voice | Source model | Strategy | Class | Saturation | Type | Success rate | Format compliance |
|---|---|---|---|---:|---:|---|---:|---:|
| espeak_ng | hr | ChatGPT Plus | paper_style | N | 50.0 | word | 1.000 | 1.000 |
| coqui_vits_hr | tts_models/hr/cv/vits | ChatGPT Plus | paper_style | N | 50.0 | word | 0.000 | 0.000 |
| speecht5_hr | /mnt/d/Audiorehabilitation/models/speecht5_tts_hr | ChatGPT Plus | paper_style | N | 50.0 | word | 0.000 | 0.000 |

## Failures

- coqui_vits_hr / tts_models/hr/cv/vits: Command '['/home/deno/miniconda3/envs/coqui-tts/bin/tts', '--text', 'buba', '--model_name', 'tts_models/hr/cv/vits', '--out_path', 'outputs/audio_comparison/task16_chatgpt_hjp_smoke/coqui_vits_hr/20260604_160319_00000_raw.wav']' returned non-zero exit status 1. (1)
- coqui_vits_hr / tts_models/hr/cv/vits: Command '['/home/deno/miniconda3/envs/coqui-tts/bin/tts', '--text', 'bubanj', '--model_name', 'tts_models/hr/cv/vits', '--out_path', 'outputs/audio_comparison/task16_chatgpt_hjp_smoke/coqui_vits_hr/20260604_160319_00001_raw.wav']' returned non-zero exit status 1. (1)
- speecht5_hr / /mnt/d/Audiorehabilitation/models/speecht5_tts_hr: Can't load feature extractor for '/mnt/d/Audiorehabilitation/models/speecht5_tts_hr'. If you were trying to load it from 'https://huggingface.co/models', make sure you don't have a local directory with the same name. Otherwise, make sure '/mnt/d/Audiorehabilitation/models/speecht5_tts_hr' is the correct path to a directory containing a preprocessor_config.json file (2)
