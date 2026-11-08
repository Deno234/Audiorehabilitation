# GitHub artifact policy

This repository contains code, experiment configuration, datasets, generated reports, local model folders, and generated audio examples.

## What is committed normally

- `src/`, `tests/`, `scripts/`, and `experiments/`
- small CSV/JSON/Markdown research outputs
- prompt files and manually reviewed CSV files
- README and documentation

## What uses Git LFS

The repository tracks large model and audio formats with Git LFS through `.gitattributes`:

- model binaries: `*.bin`, `*.safetensors`, `*.pth`, `*.pth.tar`, `*.pt`, `*.onnx`, `*.npy`
- generated audio: `*.wav`, `*.flac`, `*.mp3`, `*.ogg`
- optional packed artifacts: `*.zip`, `*.tar`, `*.tar.gz`, `*.7z`

The largest local files at packaging time are:

- `models/faster-whisper-large-v3-turbo/model.bin` (~1.5 GB)
- `models/speecht5_processor/pytorch_model.bin` (~558 MB)
- `models/speecht5_tts_hr/model.safetensors` (~551 MB)
- `models/coqui_tts/tts/tts_models--hr--cv--vits/model_file.pth.tar` (~104 MB)
- `models/speecht5_hifigan/pytorch_model.bin` (~48 MB)

## If Git LFS quota is not available

If the GitHub account cannot store all model/audio artifacts in Git LFS, keep the code repository small and upload a `models.zip` or `artifacts.zip` file to a GitHub Release or another file-sharing location. The archive should preserve paths relative to the repository root, for example:

```text
models/faster-whisper-large-v3-turbo/model.bin
models/speecht5_tts_hr/model.safetensors
models/speecht5_hifigan/pytorch_model.bin
models/speecht5_processor/pytorch_model.bin
models/coqui_tts/tts/tts_models--hr--cv--vits/model_file.pth.tar
```

After unpacking the archive into the repository root, the paths in `experiments/tts_comparison_config.yaml` should work without further changes.

## Sharing a MATLAB audio export

Use the README's single-rate export command with `--sample-rates 22050 --zip`. The exporter builds `audio_22050Hz.zip` from verified PCM16 WAV files and includes a manifest with relative audio paths. It rejects raw Git LFS pointers and publishes the archive only when every selected conversion succeeds. Share the generated ZIP directly, for example as a release attachment. If distributing a ZIP tracked by Git LFS, obtain its actual binary content before sending it to collaborators.

Keep each synthesis run's native `*_raw.wav` files and comparison manifest together for future exports. The ZIP contains only the selected derivatives and their source identifiers and hashes.

## What is intentionally ignored

- `.venv/` and other virtual environments
- Python caches and test caches
- Hugging Face cache metadata under `models/**/.cache/`
- macOS archive metadata such as `__MACOSX/` and `._*`

