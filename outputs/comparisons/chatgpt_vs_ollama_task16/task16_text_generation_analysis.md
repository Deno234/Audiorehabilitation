# Task 16 Text-Generation Comparison Analysis

Run date: 2026-06-04

## Inputs

- ChatGPT Plus imported candidates: `data/chatgpt_plus_task16_full.csv`
- Ollama generated candidates: `data/generated_ollama_task16_full.csv`
- ChatGPT normal validation run: `20260604_160116`
- ChatGPT Hunspell validation run: `20260604_160319`
- Ollama normal validation run: `20260604_143739`
- Ollama Hunspell validation run: `20260604_151847`

## Overall Results

| Source | Candidates | Technical valid | Technical valid rate | Saturation pass rate | Main failure reasons |
|---|---:|---:|---:|---:|---|
| ChatGPT Plus | 797 | 387 | 48.6% | 85.9% | duplicate=361; failed_saturation=112 |
| Ollama llama3.1:8b | 757 | 34 | 4.5% | 4.6% | failed_saturation=722; wrong_word_count=195; duplicate=30; repeated_words=9 |

Technical validity means deterministic Python validity before Hunspell dictionary screening. It includes saturation, allowed Croatian characters, duplicate detection, repeated-word detection, and word-count checks.

## Hunspell Screening

| Source | Candidates | Hunspell-valid rows | Hunspell valid rate | Technical + Hunspell valid | Technical + Hunspell valid rate |
|---|---:|---:|---:|---:|---:|
| ChatGPT Plus | 797 | 760 | 95.4% | 359 | 45.0% |
| Ollama llama3.1:8b | 757 | 581 | 76.8% | 28 | 3.7% |

Hunspell is automatic lexical screening only. It is not HJP proof and not final clinical or linguistic approval.

## Prompt Strategy And Text Type

| Source | Prompt strategy | Text type | Candidates | Technical valid rate | Saturation pass rate | Average saturation | Main failures |
|---|---|---|---:|---:|---:|---:|---|
| ChatGPT Plus | paper_style | sentence | 198 | 67.7% | 75.8% | 68.4% | failed_saturation=48; duplicate=35 |
| ChatGPT Plus | paper_style | word | 200 | 71.5% | 92.5% | 77.2% | duplicate=53; failed_saturation=15 |
| ChatGPT Plus | strict_plain_list | sentence | 199 | 49.7% | 83.9% | 69.7% | duplicate=85; failed_saturation=32 |
| ChatGPT Plus | strict_plain_list | word | 200 | 5.5% | 91.5% | 77.3% | duplicate=188; failed_saturation=17 |
| Ollama llama3.1:8b | paper_style | sentence | 191 | 0.0% | 0.0% | 20.8% | failed_saturation=191; wrong_word_count=121; repeated_words=6 |
| Ollama llama3.1:8b | paper_style | word | 167 | 16.8% | 16.8% | 30.0% | failed_saturation=139; wrong_word_count=9; duplicate=5 |
| Ollama llama3.1:8b | strict_plain_list | sentence | 200 | 0.5% | 0.5% | 21.4% | failed_saturation=199; wrong_word_count=63; duplicate=8 |
| Ollama llama3.1:8b | strict_plain_list | word | 199 | 2.5% | 3.0% | 23.1% | failed_saturation=193; duplicate=16; invalid_characters=3 |

## Key Findings

1. ChatGPT Plus substantially outperformed local Ollama for this Task 16 text-generation setup.

ChatGPT Plus produced a 48.6% technical valid rate, while Ollama produced 4.5%. The difference is mostly explained by phoneme saturation: ChatGPT Plus passed saturation for 85.9% of candidates, while Ollama passed saturation for only 4.6%.

2. Ollama failed mainly at the core phonetic criterion.

Ollama generated many Croatian-looking strings, but most did not satisfy the requested target-class saturation. It also had sentence-structure problems: 195 rows failed the 3-5 word sentence requirement.

3. ChatGPT Plus failed mainly through duplication.

For ChatGPT Plus, the largest failure source was duplicate candidates, not phoneme saturation. This means ChatGPT Plus generally understood the phoneme-control task better, but repeated itself heavily across conditions, especially in strict_plain_list word generation.

4. The paper_style prompt worked better than strict_plain_list for ChatGPT Plus words.

For ChatGPT Plus words, paper_style reached 71.5% technical validity, while strict_plain_list reached only 5.5%. The strict prompt still achieved high saturation pass rate, but it generated many repeated words.

5. ChatGPT Plus sentences were more balanced than words under strict_plain_list.

Strict_plain_list sentences had 49.7% technical validity, much higher than strict_plain_list words at 5.5%. This suggests that asking for short sentences gives the model more room to vary phoneme content without repeating identical single-word candidates.

6. Higher saturation remained difficult, especially for some classes.

In ChatGPT Plus outputs, 70% conditions were generally harder than 50% conditions. Examples include sentence N dropping from 95.0% valid at 50% to 37.5% at 70%, sentence SN from 65.0% to 15.0%, and word V from 55.0% to 22.5%.

7. Lexical screening favored ChatGPT Plus.

Hunspell accepted 95.4% of ChatGPT Plus rows but only 76.8% of Ollama rows. Ollama produced more suspicious or nonstandard forms such as `banjotop`, `gnusiti`, `grđati`, `važnostju`, and `perajuči` in normalized report output.

8. Diversity was measurable but affected by duplicates.

ChatGPT Plus had PCD summaries for 35 groups with a mean group-average PCD of 0.398. Ollama had only 11 groups with PCD summaries and a lower mean group-average PCD of 0.274. This reflects both lower valid yield and lower usable phonetic diversity.

## Scientific Conclusion

For Task 16 text generation, manual ChatGPT Plus generation is currently the stronger source for Croatian phoneme-saturated candidate material. It produces many candidates that satisfy deterministic phoneme saturation, but it still requires duplicate removal, lexical screening, and human review.

Local Ollama with `llama3.1:8b` is not yet adequate for this strict Croatian phoneme-saturation task under the current prompting setup. Its main weakness is not just Croatian lexical quality, but failure to satisfy deterministic phoneme saturation. It may still be useful for exploratory generation after prompt tuning, larger local models, or multi-pass repair, but it should not be treated as comparable to ChatGPT Plus in the current configuration.

The next recommended step is to select technically valid, Hunspell-screened ChatGPT Plus candidates for HJP/manual word-level review before moving into TTS. Audio should be synthesized only from validated text candidates.

## HJP Word-Level Review Outcome

Manual HJP word review was applied to the ChatGPT Plus Hunspell-screened candidate file:

- Word-review CSV: `data/hjp_word_review_task16_chatgpt_20260604_160319.csv`
- HJP-reviewed candidate CSV: `outputs/reports/all_candidates_hjp_reviewed_task16_chatgpt_20260604_160319.csv`
- TTS-ready reviewed candidate pool: `outputs/reports/validated_hjp_candidates_task16_chatgpt_20260604_160319.csv`

The HJP review covered all candidate rows after word-level propagation:

| Metric | Count |
|---|---:|
| Candidate rows reviewed | 797 |
| Candidate HJP valid: yes | 776 |
| Candidate HJP valid: no | 21 |
| HJP review complete | 797 |
| Pipeline-valid + HJP-valid candidates | 355 |

The 355 TTS-ready candidates are the recommended pool for the next audio stage because they satisfy deterministic validation, Hunspell lexical screening, and manual word-level HJP review.
