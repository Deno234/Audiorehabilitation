# Evaluation of Language Generative Models for Auditory Rehabilitation Needs

This project evaluates whether language generative models can produce Croatian words and short Croatian sentences that satisfy strict phoneme-class saturation criteria for auditory rehabilitation exercises.

The central research rule is that the model only generates candidate text. It must not be trusted to count phonemes or decide validity. All acceptance decisions are deterministic Python validation.

## GitHub packaging

The repository is prepared for GitHub with:

- `.gitignore` for Python environments, caches, local secrets, and model cache metadata
- `.gitattributes` for Git LFS tracking of model binaries and generated audio
- `docs/GITHUB_ARTIFACTS.md` describing which large files are required and how to distribute them

Code is licensed under the MIT License. Generated datasets, reports, model files, and audio artifacts are provided for research and educational reproducibility only. Generated text and audio are not clinically approved rehabilitation material. Model files may also be subject to their original upstream licenses.

Do not commit `.venv/`. Recreate the environment from `requirements.txt`. The local `models/` directory contains required model artifacts for the full audio workflow and must be distributed either through Git LFS or as a release/archive artifact that is unpacked back into `models/`.

## Quick start: order of scripts

Use this order when running the system from a fresh checkout.

1. Create and activate a Python environment:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

On Windows PowerShell use:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

2. Run the basic deterministic validation smoke test:

```bash
python -m src.pipeline --config experiments/config.yaml --adapter manual_csv --input data/manual_candidates_example.csv
python -m pytest
```

3. Export ChatGPT Plus prompts for the full Task 16 grid:

```bash
python -m src.pipeline --config experiments/task16_full_config.yaml --export-chatgpt-prompts
```

4. Copy the exported prompts into ChatGPT Plus, save each response under `outputs/chatgpt_prompts/<run_id>/responses/`, then import them:

```bash
python -m src.pipeline --config experiments/task16_full_config.yaml --import-chatgpt-responses outputs/chatgpt_prompts/<run_id>/responses --prompt-index outputs/chatgpt_prompts/<run_id>/prompt_index.csv --output data/chatgpt_plus_task16_full.csv
```

5. Validate the ChatGPT Plus candidate CSV:

```bash
python -m src.pipeline --config experiments/task16_full_config.yaml --adapter manual_csv --input data/chatgpt_plus_task16_full.csv
```

6. Run local Ollama generation for the same experiment grid:

```bash
python -m src.pipeline --config experiments/task16_full_config.yaml --adapter ollama --output data/generated_ollama_task16_full.csv
```

7. Compare the ChatGPT Plus and Ollama validation runs:

```bash
python -m src.pipeline --compare-runs --inputs outputs/reports/all_candidates_<chatgpt_run>.csv outputs/reports/all_candidates_<ollama_run>.csv --output-dir outputs/comparisons/chatgpt_vs_ollama_task16
```

8. Export and apply word-level HJP review:

```bash
python -m src.pipeline --export-hjp-word-review --input outputs/reports/all_candidates_<chatgpt_run>.csv --output data/hjp_word_review_<chatgpt_run>.csv
python -m src.pipeline --apply-hjp-word-review --input outputs/reports/all_candidates_<chatgpt_run>.csv --word-review data/hjp_word_review_<chatgpt_run>.csv --output outputs/reports/all_candidates_hjp_reviewed_<chatgpt_run>.csv
```

9. Synthesize audio from the reviewed/validated candidates:

```bash
python -m src.pipeline --synthesize-audio-comparison --input outputs/reports/validated_hjp_candidates_task16_chatgpt_20260604_160319.csv --config experiments/tts_comparison_config.yaml --output-dir outputs/audio_comparison/task16_chatgpt_hjp_tts_full
```

10. Generate the TTS technical report:

```bash
python -m src.pipeline --compare-tts-audio --audio-manifest outputs/audio_comparison/task16_chatgpt_hjp_tts_full/tts_comparison_manifest.csv --output-dir outputs/audio_comparison/task16_chatgpt_hjp_tts_full/report
```

11. Evaluate the combined TTS manifest with local ASR:

```bash
python -m src.pipeline --evaluate-audio --audio-manifest outputs/audio_comparison/task16_chatgpt_hjp_tts_full/tts_comparison_manifest.csv --asr-profile fast --config experiments/tts_comparison_config.yaml --output outputs/audio_eval/task16_chatgpt_hjp_tts_full_fast
```

12. Export a balanced listening-review CSV, fill human scores, and summarize results:

```bash
python -m src.pipeline --export-listening-review-sample --audio-manifest outputs/audio_comparison/task16_chatgpt_hjp_tts_full/tts_comparison_manifest.csv --output data/listening_review_sample_task16_chatgpt_hjp_tts_full.csv --per-adapter 20
```

13. Build the final report:

```bash
python -m src.pipeline --build-final-report --comparison-dir outputs/comparisons/chatgpt_vs_ollama_task16 --audio-eval-dir outputs/audio_eval/task16_chatgpt_hjp_tts_full_fast --output outputs/final_report/task16_chatgpt_hjp_tts_full.md
```

Generated text and audio are research material only. They are not clinically approved rehabilitation material.

## First milestone

The first complete workflow requires only:

- manual CSV input
- deterministic Croatian phoneme validation
- metrics
- reports
- pytest passing

Ollama automation is available for local text generation. OpenAI API, TTS, and ASR are not part of this milestone.

Run the milestone pipeline:

```bash
python -m src.pipeline --config experiments/config.yaml --adapter manual_csv --input data/manual_candidates_example.csv
pytest
```

## Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Manual CSV input

Manual input must be UTF-8 CSV with these columns:

```text
candidate,model,prompt_strategy,target_class,saturation_level,text_type
```

Target class may use either code aliases (`N`, `SN`, `S`, `SV`, `V`) or Croatian names (`Niski`, `Srednjeniski`, `Srednji`, `Srednjevisoki`, `Visoki`).

Use `data/manual_experiment_template.csv` when starting a larger manual experiment.
The extended demo file `data/manual_candidates_extended_example.csv` also includes a `notes` column. That column is documentation-only: it is preserved in candidate-level reports when present, but it never affects validation.

## Creating candidates manually with an LLM

You can use ChatGPT, Codex, or any other LLM to draft candidates, then paste them into a UTF-8 CSV for deterministic evaluation.

Recommended workflow:

1. Pick a target class, saturation level, and text type from `experiments/config.yaml`.
2. Ask the LLM for many more candidates than needed because some will fail validation.
3. Tell the LLM to return only Croatian words or 3-5 word Croatian sentences, one candidate per line.
4. Paste candidates into the CSV columns `candidate,model,prompt_strategy,target_class,saturation_level,text_type`.
5. Save the CSV as UTF-8 so `č`, `ć`, `đ`, `š`, `ž`, `dž`, `lj`, and `nj` are preserved.
6. Run the pipeline and use `all_candidates_<run_id>.csv` to inspect every pass/fail reason.

Example prompt idea:

```text
Generate 80 Croatian 3-5 word sentences for auditory rehabilitation research.
Target phoneme class: SV.
Required saturation: at least 60%.
Return only the candidate sentences, one per line.
Do not explain or number the rows.
```

The LLM output is only a candidate source. Python validation remains the only acceptance mechanism.

## Running the first real manual LLM experiment

Use the manual prompt files in `experiments/prompts/` when you are ready to collect the first real candidate set:

- `manual_word_generation_prompt.txt` for isolated Croatian words
- `manual_sentence_generation_prompt.txt` for Croatian 3-5 word sentences
- `manual_repair_prompt.txt` for replacing candidates that failed deterministic validation

Workflow:

1. Choose `target_class`, `saturation_level`, and `text_type` from your experiment design.
2. Copy the matching manual prompt.
3. Replace placeholders such as `{target_class}`, `{saturation_level}`, and `{candidate_count}`.
4. Ask the LLM for candidates.
5. Paste the candidates into a copy of `data/manual_experiment_template.csv`.
6. Fill `model`, `prompt_strategy`, `target_class`, `saturation_level`, and `text_type` for every row.
7. Run the pipeline:

```bash
python -m src.pipeline --config experiments/config.yaml --adapter manual_csv --input data/manual_experiment_template.csv
```

8. Inspect the outputs for the new `run_id`:

- `outputs/reports/all_candidates_<run_id>.csv` for every candidate and failure reason
- `outputs/reports/validated_candidates_<run_id>.csv` for candidates that passed deterministic validation
- `outputs/reports/experiment_summary_<run_id>.csv` for grouped pass rates and diversity metrics
- `outputs/reports/report_<run_id>.md` for the human-readable summary

Do not manually remove failed rows before reporting. Keeping failures makes pass rates and failure reasons reproducible.

## Manual ChatGPT Plus experiment with exported prompts

You can export ready-to-copy prompt files for the full experiment grid. This does not use the OpenAI API.

```bash
python -m src.pipeline --config experiments/config.yaml --export-chatgpt-prompts
```

The command writes prompts to:

```text
outputs/chatgpt_prompts/<run_id>/
```

Use this workflow:

1. Open each generated `.txt` prompt file.
2. Copy and paste the prompt into ChatGPT Plus.
3. Paste the returned candidates into a CSV based on `data/manual_experiment_template.csv`.
4. Fill `model`, `prompt_strategy`, `target_class`, `saturation_level`, and `text_type` from `prompt_index.csv`.
5. Run deterministic validation with the manual CSV pipeline.
6. Inspect `all_candidates_<run_id>.csv`, `validated_candidates_<run_id>.csv`, `experiment_summary_<run_id>.csv`, and `report_<run_id>.md`.

The `paper_style` prompts include an HJP instruction because it mirrors the paper-style prompt design. That instruction is only a prompt constraint, not proof that a candidate is valid in HJP. True HJP validity requires manual checking or a configured dictionary/manual-review validation step.

## Full comparison: ChatGPT Plus vs Ollama

For the full comparison, set `candidate_count_per_condition: 20` in `experiments/config.yaml`. With 5 target classes, 2 saturation levels, 2 text types, and 2 prompt strategies, this gives 40 conditions and 800 candidates per source.

Export prompts:

```bash
python -m src.pipeline --config experiments/config.yaml --export-chatgpt-prompts
```

For each prompt file in `outputs/chatgpt_prompts/<run_id>/`, copy the prompt into ChatGPT Plus and save the returned candidate list into the matching response file under `outputs/chatgpt_prompts/<run_id>/responses/`. The response file name must exactly match the prompt file name. For example:

```text
outputs/chatgpt_prompts/<run_id>/chatgpt_paper_style_word_N_50.txt
outputs/chatgpt_prompts/<run_id>/responses/chatgpt_paper_style_word_N_50.txt
```

Import ChatGPT Plus responses into CSV:

```bash
python -m src.pipeline --config experiments/config.yaml --import-chatgpt-responses outputs/chatgpt_prompts/<run_id>/responses --prompt-index outputs/chatgpt_prompts/<run_id>/prompt_index.csv --output data/chatgpt_plus_full_experiment.csv
```

Check the import summary for expected, found, and missing response files, plus total parsed candidates.

Validate the ChatGPT Plus CSV:

```bash
python -m src.pipeline --config experiments/config.yaml --adapter manual_csv --input data/chatgpt_plus_full_experiment.csv
```

Run local Ollama generation:

```bash
python -m src.pipeline --config experiments/config.yaml --adapter ollama --output data/generated_ollama_experiment.csv
```

Compare the generated reports in `outputs/reports/`. The HJP wording in `paper_style` prompts is only a prompt constraint; deterministic validity remains Python-based, and true HJP validity requires manual checking or dictionary/manual-review validation.

## Complete scientific workflow

Choose a config:

- Paper reproduction: `experiments/paper_reproduction_config.yaml`
- Full task 16 comparison: `experiments/task16_full_config.yaml`

For the full task 16 comparison, `candidate_count_per_condition` is `20`. The paper reproduction config uses separate word/sentence blocks matching the reference structure more closely.

1. Export ChatGPT Plus prompts:

```bash
python -m src.pipeline --config experiments/task16_full_config.yaml --export-chatgpt-prompts
```

2. Copy each exported prompt into ChatGPT Plus and save the response into the matching file in:

```text
outputs/chatgpt_prompts/<run_id>/responses/
```

3. Import ChatGPT Plus responses:

```bash
python -m src.pipeline --config experiments/task16_full_config.yaml --import-chatgpt-responses outputs/chatgpt_prompts/<run_id>/responses --prompt-index outputs/chatgpt_prompts/<run_id>/prompt_index.csv --output data/chatgpt_plus_full_experiment.csv
```

4. Validate ChatGPT Plus responses:

```bash
python -m src.pipeline --config experiments/task16_full_config.yaml --adapter manual_csv --input data/chatgpt_plus_full_experiment.csv
```

5. Run local Ollama generation:

```bash
python -m src.pipeline --config experiments/task16_full_config.yaml --adapter ollama --output data/generated_ollama_experiment.csv
```

6. Compare ChatGPT Plus and Ollama reports:

```bash
python -m src.pipeline --compare-runs --inputs outputs/reports/all_candidates_<chatgpt_run>.csv outputs/reports/all_candidates_<ollama_run>.csv --output-dir outputs/comparisons/<comparison_id>
```

7. Export word-level HJP review:

```bash
python -m src.pipeline --export-hjp-word-review --input outputs/reports/all_candidates_<run_id>.csv --output data/hjp_word_review_<run_id>.csv
```

8. Apply word-level HJP review:

```bash
python -m src.pipeline --apply-hjp-word-review --input outputs/reports/all_candidates_<run_id>.csv --word-review data/hjp_word_review_<run_id>.csv --output outputs/reports/all_candidates_hjp_reviewed_<run_id>.csv
```

9. Optionally export/apply semantic and clinical suitability review:

```bash
python -m src.pipeline --export-manual-review --input outputs/reports/all_candidates_<run_id>.csv --output data/manual_review_<run_id>.csv
python -m src.pipeline --apply-manual-review --input outputs/reports/all_candidates_<run_id>.csv --review data/manual_review_<run_id>.csv --output outputs/reports/all_candidates_reviewed_<run_id>.csv
```

10. Synthesize Croatian audio from validated candidates:

```bash
python -m src.pipeline --synthesize-audio --input outputs/reports/validated_candidates_<run_id>.csv --adapter espeak_ng --output-dir outputs/audio/<run_id> --limit 50
```

11. Evaluate audio technically and optionally with local ASR or manual transcription:

```bash
python -m src.pipeline --evaluate-audio --audio-manifest outputs/audio/<run_id>/audio_manifest.csv --asr-adapter faster_whisper --output outputs/audio_eval/<run_id>
python -m src.pipeline --evaluate-audio --audio-manifest outputs/audio/<run_id>/audio_manifest.csv --manual-transcriptions data/manual_audio_transcriptions_<run_id>.csv --output outputs/audio_eval/<run_id>
```

Audio WER/CER is computed after Croatian-safe normalization: lowercase, punctuation removal, whitespace normalization, and preservation of `č`, `ć`, `đ`, `š`, `ž`. ASR-based WER/CER is a proxy for audio intelligibility, not a perfect pronunciation measure.

12. Build the final scientific report:

```bash
python -m src.pipeline --build-final-report --comparison-dir outputs/comparisons/<comparison_id> --audio-eval-dir outputs/audio_eval/<run_id> --output outputs/final_report/final_report_<timestamp>.md
```

Do not treat automatically generated text or audio as clinically approved rehabilitation material. It is research/demo material until reviewed by a qualified expert.

## Hunspell lexical screening

Hunspell validation is optional automatic Croatian dictionary/spellcheck screening. It is not HJP validation and it is not final linguistic or clinical approval. Hunspell may reject valid inflected Croatian words or accept words that are not appropriate for the rehabilitation context, so use it as scalable lexical screening before manual review.

Install the local Croatian Hunspell tools in WSL only when you want to enable this mode:

```bash
sudo apt update
sudo apt install -y hunspell hunspell-hr
```

Use the opt-in example config:

```bash
python -m src.pipeline --config experiments/hunspell_validation_config.yaml --adapter manual_csv --input data/manual_candidates_example.csv
```

The relevant config block is:

```yaml
validation:
  dictionary:
    mode: hunspell_cli
    hunspell_executable: "hunspell"
    hunspell_dictionary: "hr_HR"
```

Hunspell result columns are named as Croatian dictionary/spellcheck screening, for example `dictionary_word_validity` and `dictionary_invalid_words`. Keep HJP separate by exporting and applying manual word-level HJP review:

```bash
python -m src.pipeline --export-hjp-word-review --input outputs/reports/all_candidates_<run_id>.csv --output data/hjp_word_review_<run_id>.csv
python -m src.pipeline --apply-hjp-word-review --input outputs/reports/all_candidates_<run_id>.csv --word-review data/hjp_word_review_<run_id>.csv --output outputs/reports/all_candidates_hjp_reviewed_<run_id>.csv
```

To reduce manual review work, export a prioritized lexical queue:

```bash
python -m src.pipeline --export-lexical-review-queue --input outputs/reports/all_candidates_<run_id>.csv --output data/lexical_review_queue_<run_id>.csv
```

Use Hunspell for scalable automatic filtering, then use manual HJP review for high-priority and final candidate words. Never treat ChatGPT's claim that a word exists in HJP as evidence. ChatGPT Plus may be used informally to inspect suspicious words, but store that only in a notes column such as `llm_review_note`, not in `hjp_valid`.

## Optional local audio adapters

eSpeak NG remains the reproducible Croatian TTS baseline. The optional `external_command` TTS adapter is only a scaffold for explicitly configured local Croatian TTS systems such as Piper or another local model. It does not download models and refuses to run unless the user confirms the configured command uses a Croatian voice or model.

Optional local ASR can use `faster_whisper` if installed and configured with a local model path:

```yaml
audio_eval:
  asr_profiles:
    fast:
      adapter: faster_whisper
      model_name: large-v3-turbo
      model_path: "/path/to/local/faster-whisper-large-v3-turbo"
      language: "hr"
      device: "cpu"
      compute_type: "int8"
      local_files_only: true
```

The project does not download ASR models automatically. ASR-based WER/CER is only a proxy for intelligibility, not proof of TTS pronunciation or clinical audio quality. For the main TTS comparison, use one fixed ASR profile to avoid confounding TTS comparison with ASR-model differences.

## Croatian TTS comparison

The TTS comparison workflow synthesizes the same validated Croatian candidates with multiple local adapters and writes one combined manifest for reporting and ASR/human review.

- eSpeak NG is the reproducible lightweight baseline and uses Croatian voice `hr`.
- Coqui Croatian VITS is an optional local neural TTS option using model `tts_models/hr/cv/vits`.
- SpeechT5 Croatian is an optional heavier local neural option using `nikolab/speecht5_tts_hr` or a configured local model path. It requires a local model folder, local HiFi-GAN vocoder folder, and a local speaker embedding `.npy`, unless you explicitly enable the experimental zero-vector fallback.
- Piper remains scaffold-only unless you configure a Croatian Piper voice model path.
- Successful audio is normalized to WAV mono 16 kHz 16-bit PCM.
- ASR WER/CER compares transcription of generated audio against the known source text. It is a proxy for intelligibility, not clinical proof of TTS quality.
- ASR WER/CER is a proxy, not clinical proof.
- Human listening review is recommended for final conclusions.

Install tools only when you want to use them:

```bash
sudo apt install -y espeak-ng
python -m pip install TTS
python -m pip install transformers torch scipy numpy
python -m pip install faster-whisper
```

The checked-in comparison config enables all three Croatian TTS adapters. To limit a fresh run for a smoke test:

```bash
python -m src.pipeline --synthesize-audio-comparison --input outputs/reports/validated_candidates_<run_id>.csv --config experiments/tts_comparison_config.yaml --output-dir outputs/audio_comparison/<run_id> --limit 50
```

### Native recordings and sample-rate exports

From the repository root in WSL, install the Python requirements in the active environment with `python -m pip install -r requirements.txt`. The comparison config uses the local Croatian eSpeak NG voice, Coqui wrapper, and SpeechT5 model/vocoder paths under `/mnt/d/Audiorehabilitation`. Check those paths and the cached models before synthesis on another machine.

The validated input for run `20260604_160319` contains **355 unique candidates**. A complete synthesis produces **1,065 native recordings** across the three adapters and one 16 kHz mono PCM16 derivative per recording. The historical `tts_subset` directory contains 96 candidates and is reserved for verification. Synthesize the full input into a fresh directory:

```bash
python -m src.pipeline --synthesize-audio-comparison \
  --input outputs/reports/validated_hjp_candidates_task16_chatgpt_20260604_160319.csv \
  --config experiments/tts_comparison_config.yaml \
  --output-dir outputs/audio_comparison/task16_chatgpt_hjp_tts_full
```

Keep the complete run directory, including `tts_comparison_manifest.csv` and each adapter's `<candidate_id>_raw.wav`. The raw file is the native synthesis result. eSpeak NG and Coqui retain their emitted WAV bytes. Fresh SpeechT5 runs save the float32 waveform at the vocoder rate, preserving precision that older PCM16 raw files already quantized. A comparison run stops before inference if its destinations collide with an existing experiment.

Generate the collaborator ZIP directly from those raw recordings:

```bash
python -m src.pipeline --export-audio-formats \
  --input-dir outputs/audio_comparison/task16_chatgpt_hjp_tts_full \
  --sample-rates 22050 \
  --output-dir outputs/audio_exports/task16_full_polyphase \
  --zip
```

The archive is `outputs/audio_exports/task16_full_polyphase/audio_22050Hz.zip`. A complete full-run ZIP contains 1,065 WAVs plus its UTF-8 manifest. To export multiple rates, use `--sample-rates 16000 22050 44100 48000`. Each rate is derived directly from the raw file. A later single-rate ZIP includes only the rate requested on that invocation. Rows in the directory manifest cover the available exports, while rows in the ZIP correspond to its members.

Rerun the same export command after an interruption. It verifies source and derivative SHA-256 hashes and conversion settings before reuse. A failed conversion sets a nonzero exit status and appears in `export_error` in `audio_export_manifest.csv`. Restore the indicated raw file if it is missing, corrupt, or a Git LFS pointer, then retry. Export does not invoke the TTS adapters.

#### Historical comparisons

Both comparison synthesis and export default to `polyphase`. The converter uses a band-limited polyphase FIR filter (Kaiser window, beta 5, zero padding), averages channels in float64 for mono, and quantizes to PCM16 with nearest-even rounding. It retains the input level except when a single gain factor is needed to prevent overload. Equal-rate audio bypasses filtering. The manifest records the selected method, whether filtering or sample-rate conversion was applied, gain, format, frame counts, software versions, and hashes.

For exact reproduction of the old PCM16 conversion from the same archived raw files, select `--resampling-method legacy-nearest` on synthesis or export. It uses the original integer stereo downmix, frame-count rounding, and nearest-sample indexing from revision `224397cf9f15db551adc5db93ce45c12fd5767fe`. For example:

```bash
python -m src.pipeline --export-audio-formats \
  --input-dir outputs/audio_comparison/task16_chatgpt_hjp_tts_subset \
  --sample-rates 16000 --resampling-method legacy-nearest \
  --output-dir outputs/audio_exports/task16_subset_legacy_verification
```

Use separate export directories for the two methods. New polyphase 16 kHz recordings can differ from archived 16 kHz recordings in sample values, spectra, RMS, clipping, and downstream ASR metrics. Fresh inference can also differ across model versions, speaker embeddings, or stochastic generation. Keep the raw hashes, candidate IDs, model identifiers and preprocessing method with any published results.

Compare models on the same candidates, at one common rate and with one method and ASR profile. Report native sample rates as well. Upsampling from 16,000 to 22,050 Hz changes the sample spacing. Frequencies above the original 8 kHz Nyquist limit cannot be recovered. Comparison and evaluation summaries group by target rate and method. Old manifests use a 16,000 Hz fallback and label the method `unrecorded`. Supply `--expected-sample-rate 22050` when evaluating an older experiment known to have used that target.

#### MATLAB

Extract the ZIP anywhere. The `audio_path` column is relative to the extracted manifest. `source_run`, `raw_audio_path` (relative to that run), and `raw_sha256` identify the archived source. Only the exported WAVs are required for MATLAB:

```matlab
folder = "task16_matlab";
unzip("audio_22050Hz.zip", folder);
T = readtable(fullfile(folder, "audio_export_manifest.csv"), "TextType", "string");
p = fullfile(folder, T.audio_path(1));
info = audioinfo(p);
[x, Fs] = audioread(p);
assert(Fs == 22050 && info.BitsPerSample == 16 && info.NumChannels == 1);
assert(size(x, 1) == T.frames(1));
```

Generate the TTS audio comparison report:

```bash
python -m src.pipeline --compare-tts-audio --audio-manifest outputs/audio_comparison/<run_id>/tts_comparison_manifest.csv --output-dir outputs/audio_comparison/<run_id>/report
```

Evaluate the combined TTS manifest with local ASR if configured:

```bash
python -m src.pipeline --evaluate-audio --audio-manifest outputs/audio_comparison/<run_id>/tts_comparison_manifest.csv --asr-profile fast --config experiments/tts_comparison_config.yaml --output outputs/audio_eval/<run_id>_tts_fast
```

Use `fast` / `large-v3-turbo` for the main TTS comparison. Use `best` / `large-v3` only for a smaller confirmation subset if your machine can handle it. Use `lightweight` / `small` only if the machine is weak. Before running profile-based ASR, set `audio_eval.asr_profiles.<profile>.model_path` to a local faster-whisper model folder.

Export a balanced listening review sample:

```bash
python -m src.pipeline --export-listening-review-sample --audio-manifest outputs/audio_comparison/<run_id>/tts_comparison_manifest.csv --output data/listening_review_sample_<run_id>.csv --per-adapter 10
```

To enable Coqui after installing `TTS`, edit `experiments/tts_comparison_config.yaml` and set `coqui_vits_hr.enabled: true`. Real Coqui use may download the model on first run unless it is already cached locally.

To enable SpeechT5, install `transformers`, `torch`, `scipy`, and `numpy`, configure local `model_path`, `vocoder_path`, and `speaker_embedding_path`, keep `local_files_only: true`, and set `speecht5_hr.enabled: true`. The project does not auto-download SpeechT5 models by default.

For an experimental smoke test without a real speaker embedding, set:

```yaml
- name: speecht5_hr
  enabled: true
  model_path: "/mnt/d/Audiorehabilitation/models/speecht5_tts_hr"
  vocoder_path: "/mnt/d/Audiorehabilitation/models/speecht5_hifigan"
  local_files_only: true
  device: "cpu"
  croatian_voice_or_model_confirmed: true
  speaker_embedding_path: ""
  speaker_embedding_dim: 512
  allow_default_zero_speaker_embedding: true
```

Then run a tiny comparison first:

```bash
python -m src.pipeline --synthesize-audio-comparison --input outputs/reports/validated_candidates_<run_id>.csv --config experiments/tts_comparison_config.yaml --output-dir outputs/audio_comparison/<run_id> --limit 2
```

## Free local generation with Ollama

Ollama generation is local-only and does not use the OpenAI API. It asks a local model for candidate text, then the same deterministic Python validation decides which candidates pass. Ollama uses the same `paper_style` and `strict_plain_list` prompt strategies as the exported ChatGPT Plus prompts, so results can be compared across manual ChatGPT Plus and local Ollama sources.

Install Ollama from the official Ollama distribution for your platform, then pull a local model:

```bash
ollama pull llama3.1:8b
```

Verify that Ollama is running and that the model is available:

```bash
ollama list
```

The default config uses `candidate_count_per_condition: 5` so the first local test is fast. For the real experiment, increase it to `20` in `experiments/config.yaml`. Keep `request_extra_factor: 2` if you want Ollama to generate twice as many candidates as the final per-condition target.

Preview the planned requests without contacting Ollama:

```bash
python -m src.pipeline --config experiments/config.yaml --adapter ollama --dry-run
```

Run real local generation only when Ollama is running:

```bash
python -m src.pipeline --config experiments/config.yaml --adapter ollama --output data/generated_ollama_experiment.csv
```

Generated candidates are saved to the `--output` CSV path. Raw model responses are saved as JSONL in `outputs/raw_generations/raw_ollama_generations_<run_id>.jsonl`. Reports are written to `outputs/reports/`, including `all_candidates_<run_id>.csv`, `validated_candidates_<run_id>.csv`, `experiment_summary_<run_id>.csv`, and `report_<run_id>.md`.

No OpenAI API is used. Manual ChatGPT Plus generation through the app remains supported through the CSV workflow above.

## Outputs

Every run gets a timestamp `run_id`. CSV files are read/written explicitly as UTF-8, and output filenames include `run_id` so repeated runs do not overwrite earlier results.

Reports are written to `outputs/reports/`, including:

- `all_candidates_<run_id>.csv`
- `validated_candidates_<run_id>.csv`
- `experiment_summary_<run_id>.csv`
- `audio_eval_summary_<run_id>.csv`
- `pcd_matrix_<run_id>.csv`
- `pcd_summary_<run_id>.csv`
- `report_<run_id>.md`
- `config_snapshot_<run_id>.yaml`

Raw generation metadata is written to `outputs/raw_generations/`, and validated intermediate rows are written to `outputs/validated/`.

## Phoneme validation

The deterministic Croatian phonemizer:

- lowercases text
- preserves `č`, `ć`, `đ`, `š`, `ž`
- removes punctuation for phoneme counting
- treats `dž`, `lj`, and `nj` as single phonemes using longest-match-first parsing
- ignores spaces for total phoneme counts

Failure reasons include:

- `failed_saturation`
- `invalid_characters`
- `wrong_word_count`
- `duplicate`
- `repeated_words`
- `dictionary_failed`

## Phase-two audio adapters

Local/free TTS and audio-evaluation scaffolds are available, but generated text acceptance still depends on deterministic Python validation. Audio remains research/demo material until reviewed by a qualified listener or clinician.

## Add new adapters

Text generators should return rows compatible with the manual CSV schema plus run metadata. TTS adapters should synthesize only candidates that passed validation. ASR adapters should be used only for audio verification and should report WER/CER against source text.
