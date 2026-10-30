# Voice Evaluation Protocol

1. Record each test utterance naturally using a consenting speaker. Keep one utterance per file and avoid background personal information.
2. Run the audio through Prisma; save the raw response and transcript.
3. Compare transcript with `gold_transcript` for qualitative review. For ASR scoring, calculate WER/CER only after defining tokenization and language normalization rules.
4. Run the transcript through the order parser and compare product IDs, quantities, units and expected action against `voice_test_cases.json`.
5. Report product identification accuracy, quantity/unit accuracy, exact-cart accuracy, clarification accuracy, false order rate, stock validation failures and median/p95 latency.
6. Keep the test set fixed across Prisma model versions; do not change expected labels after seeing model output without documenting a correction.
7. A safe failure (asking for clarification) is preferable to a confidently incorrect product selection or order.
