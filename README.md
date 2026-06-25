# Intelligent Candidate Discovery & Ranking (AI Recruiter POC)

This repository contains the candidate ranking solution developed for the **Senior AI Engineer — Founding Team** job description at Redrob AI.

## Project Structure
- `rank.py`: The core ranking script that streams, filters, scores, and ranks candidates.
- `requirements.txt`: Project dependencies (PyYAML only, standard library used for ranking).
- `submission_metadata.yaml`: Team identity and compute metadata.
- `validate_submission.py`: Hackathon format validator.
- `candidates.jsonl`: Unpacked candidate pool (100,000 profiles).

## How to Run

1. Make sure Python 3.8+ is installed.
2. Run the ranking script using:
   ```bash
   python rank.py --candidates ./candidates.jsonl --out ./teamnextmatrix.csv
   ```
3. Validate the generated CSV:
   ```bash
   python validate_submission.py teamnextmatrix.csv
   ```

## Methodology

This system implements a multi-criteria scoring algorithm combined with a high-precision honeypot and anomaly filter:
1. **Anomaly & Honeypot Detection**: Excludes candidates violating dataset integrity (such as expert skill with 0 duration, profile YoE mismatch, and Krutrim/Sarvam AI dates mismatch).
2. **Core Skill Alignment**: Matches candidates on essential NLP, Retrieval, Vector Search, and Evaluation skills (NDCG, MAP).
3. **Experience Suitability**: Awards maximum score for candidates in the 5–9 years range.
4. **Behavioral multiplier**: Factors in platform activity, responsiveness, notice period, and open-to-work signals.
5. **Dynamic Reasoning**: Generates unique, data-backed 1-2 sentence reasonings for each ranked candidate.
