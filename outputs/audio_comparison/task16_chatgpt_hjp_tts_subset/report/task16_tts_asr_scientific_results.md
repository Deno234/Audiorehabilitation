# Task 16 TTS and ASR Evaluation Results

Run date: 2026-06-04

## Input Candidate Set

- Source CSV: `data/tts_candidate_subset_task16_chatgpt_20260604_160319.csv`
- Source model: ChatGPT Plus
- Candidate selection: deterministic valid + Hunspell-screened + manual HJP word-review valid
- Requested design: 5 phoneme classes x 2 saturation levels x 2 text types x 5 candidates = 100 candidates
- Actual subset: 96 candidates
- Underfilled group: `target_class=S`, `saturation_level=70`, `text_type=word` had only 1 available reviewed valid candidate

## TTS Technical Validation

- TTS manifest: `outputs/audio_comparison/task16_chatgpt_hjp_tts_subset/tts_comparison_manifest.csv`
- TTS technical report: `outputs/audio_comparison/task16_chatgpt_hjp_tts_subset/report/tts_audio_report.md`
- Required output format: WAV, mono, 16 kHz, 16-bit PCM

| TTS adapter | Model / voice | Candidates | Success rate | Format compliance | Avg duration (s) | Avg RMS | Avg clipping rate |
|---|---|---:|---:|---:|---:|---:|---:|
| coqui_vits_hr | tts_models/hr/cv/vits | 96 | 1.000 | 1.000 | 1.267 | 4793.9 | 0.000035 |
| espeak_ng | hr | 96 | 1.000 | 1.000 | 0.974 | 2417.8 | 0.000000 |
| speecht5_hr | /mnt/d/Audiorehabilitation/models/speecht5_tts_hr | 96 | 1.000 | 1.000 | 1.372 | 495.7 | 0.000000 |

All three configured TTS systems synthesized all 96 selected text candidates successfully. All successful audio files met the required WAV format constraints.

## ASR-Based WER/CER Evaluation

- ASR summary: `outputs/audio_eval/task16_chatgpt_hjp_tts_fast/audio_eval_summary.csv`
- ASR profile: `fast`
- ASR model: `large-v3-turbo`
- ASR adapter: local `faster_whisper`
- Language: Croatian (`hr`)

| TTS adapter | Evaluated | Failed | Average WER | Average CER |
|---|---:|---:|---:|---:|
| coqui_vits_hr | 96 | 0 | 1.187 | 0.693 |
| espeak_ng | 96 | 0 | 1.076 | 0.443 |
| speecht5_hr | 96 | 0 | 0.967 | 0.438 |

Lower WER/CER indicates closer ASR transcription to the known source text. In this run, SpeechT5 had the lowest average WER and CER, followed by eSpeak NG, while Coqui VITS had the highest WER/CER.

## Worst ASR Examples

### coqui_vits_hr

| Candidate ID | WER | CER | Source | ASR transcription |
|---|---:|---:|---|---|
| 20260604_160319_00001 | 3.000 | 0.833 | bubanj | to ba ne |
| 20260604_160319_00649 | 3.000 | 4.000 | sisa | hvala što pratite |
| 20260604_160319_00383 | 2.333 | 0.667 | draga dara radi | da da da da da da de |

### espeak_ng

| Candidate ID | WER | CER | Source | ASR transcription |
|---|---:|---:|---|---|
| 20260604_160319_00321 | 3.000 | 1.000 | radar | da da da |
| 20260604_160319_00485 | 3.000 | 1.200 | češće | hr h h |
| 20260604_160319_00399 | 2.667 | 1.133 | ratar krade rak | ba ba ba ba ba ba ba ba |

### speecht5_hr

| Candidate ID | WER | CER | Source | ASR transcription |
|---|---:|---:|---|---|
| 20260604_160319_00540 | 3.000 | 1.071 | čete tiše šute | i žete tije u te u te u te |
| 20260604_160319_00094 | 3.000 | 1.167 | bubnju | hlubo v o |
| 20260604_160319_00601 | 2.667 | 0.875 | dječje čete teže | die te die te te te te te |

## Scientific Interpretation

1. The technical synthesis pipeline is now operational for all three TTS systems: eSpeak NG Croatian, Coqui Croatian VITS, and local SpeechT5 Croatian.
2. The format-normalization requirement was satisfied for every generated audio file, so downstream ASR comparison used consistent WAV properties rather than adapter-specific output formats.
3. ASR WER/CER suggests SpeechT5 was the strongest of the three systems in this run, but this should be treated as a relative ASR-based proxy, not clinical proof of pronunciation quality.
4. Coqui VITS produced technically valid WAV files but had worse ASR agreement than eSpeak NG and SpeechT5 on this phoneme-heavy material.
5. The generated material intentionally overuses specific phoneme classes, so high WER/CER may reflect TTS errors, ASR weaknesses, or the unusual phonetic composition of the research stimuli.
6. Human listening review remains necessary before making claims about naturalness, pronunciation quality, or clinical suitability for auditory rehabilitation.

## Listening Review

- Listening-review sample: `data/listening_review_sample_task16_chatgpt_hjp_tts_subset.csv`
- Sample size: 10 rows per TTS adapter, 30 rows total
- Recommended human scores: intelligibility 1-5, naturalness 1-5, pronunciation notes, clinical suitability notes

## Balanced Human Listening Review

- Review CSV: `data/listening_review_balanced_task16_chatgpt_hjp_tts_subset.csv`
- Summary CSV: `outputs/audio_comparison/task16_chatgpt_hjp_tts_subset/report/listening_review_summary.csv`
- Reviewed audio rows: 60
- Design: balanced across 3 TTS adapters, 5 phoneme classes, 2 saturation levels, and word/sentence text type.

| TTS adapter | Reviewed | Avg intelligibility | Median intelligibility | Avg naturalness | Median naturalness | ASR WER on sample | ASR CER on sample |
|---|---:|---:|---:|---:|---:|---:|---:|
| coqui_vits_hr | 20 | 2.150 | 2.000 | 2.100 | 2.000 | 1.233 | 0.828 |
| espeak_ng | 20 | 4.650 | 5.000 | 3.300 | 3.000 | 0.967 | 0.389 |
| speecht5_hr | 20 | 3.350 | 3.500 | 3.600 | 4.000 | 0.958 | 0.485 |

### By Text Type

| Group | Reviewed | Avg intelligibility | Avg naturalness |
|---|---:|---:|---:|
| coqui_vits_hr / sentence | 10 | 2.700 | 2.600 |
| coqui_vits_hr / word | 10 | 1.600 | 1.600 |
| espeak_ng / sentence | 10 | 4.600 | 2.800 |
| espeak_ng / word | 10 | 4.700 | 3.800 |
| speecht5_hr / sentence | 10 | 3.800 | 4.200 |
| speecht5_hr / word | 10 | 2.900 | 3.000 |

### By Saturation Level

| Group | Reviewed | Avg intelligibility | Avg naturalness |
|---|---:|---:|---:|
| coqui_vits_hr / 50.0 | 10 | 2.200 | 2.200 |
| coqui_vits_hr / 70.0 | 10 | 2.100 | 2.000 |
| espeak_ng / 50.0 | 10 | 4.600 | 3.300 |
| espeak_ng / 70.0 | 10 | 4.700 | 3.300 |
| speecht5_hr / 50.0 | 10 | 3.600 | 3.700 |
| speecht5_hr / 70.0 | 10 | 3.100 | 3.500 |

### By Phoneme Class

| Group | Reviewed | Avg intelligibility | Avg naturalness |
|---|---:|---:|---:|
| coqui_vits_hr / N | 4 | 2.000 | 2.000 |
| coqui_vits_hr / S | 4 | 2.750 | 2.500 |
| coqui_vits_hr / SN | 4 | 1.750 | 1.750 |
| coqui_vits_hr / SV | 4 | 2.000 | 2.000 |
| coqui_vits_hr / V | 4 | 2.250 | 2.250 |
| espeak_ng / N | 4 | 5.000 | 4.250 |
| espeak_ng / S | 4 | 4.000 | 2.750 |
| espeak_ng / SN | 4 | 4.750 | 3.250 |
| espeak_ng / SV | 4 | 4.500 | 3.250 |
| espeak_ng / V | 4 | 5.000 | 3.000 |
| speecht5_hr / N | 4 | 4.000 | 4.250 |
| speecht5_hr / S | 4 | 4.500 | 4.750 |
| speecht5_hr / SN | 4 | 3.000 | 3.500 |
| speecht5_hr / SV | 4 | 1.250 | 1.250 |
| speecht5_hr / V | 4 | 4.000 | 4.250 |

### Human Review Interpretation

- Highest mean human intelligibility: `espeak_ng` (4.650/5).
- Highest mean human naturalness: `speecht5_hr` (3.600/5).
- Compare this human review with ASR carefully: ASR WER/CER is an automatic proxy, while the listening scores reflect one human review pass over a balanced sample.
- Clinical suitability still requires expert judgment; these scores do not clinically approve the audio material.


## Caveat

ASR WER/CER is used here as a relative proxy for TTS intelligibility. It is not a perfect measure of pronunciation quality. High WER/CER may be caused by the TTS model, the ASR model, or by the phoneme-heavy nature of the generated Croatian stimuli.
