# Submission checklist

Tick each item yourself. Items marked **(you)** cannot be done by anyone else.

## Before you submit
- [ ] **(you)** Create a virtual environment, run `pip install -r requirements.txt`, `python run_analysis.py` and `python -m pytest` on your own machine. Note any difference from the README in your own words.
- [ ] **(you)** Open every PNG in `outputs/figures/` and check it looks right on your machine (fonts differ slightly between machines).
- [ ] **(you)** Read `outputs/insights_report.md` and `docs/evaluator_report.md` and make sure you can explain every statement. Use `docs/interview_prep.md`.
- [ ] **(you)** Check QSkill's rules on AI assistance. If disclosure is expected, add a short honest line to the README, for example: "Code and documentation were prepared with AI assistance (Claude) and reviewed and run by me." Only write that if it is true for you.
- [ ] **(you)** Decide whether to add your name, internship ID and date at the top of the README.
- [ ] **(you)** Create the GitHub repository and push. `data/` is git-ignored on purpose (licence unverified); the pipeline downloads the CSV itself.
- [ ] If QSkill wants the charts inside the repo, they are in `outputs/figures/` (not ignored).

## Already covered in the project
- [x] README with provenance, licence status, limitations, structure, setup, run command, cleaning decisions, methodology, outputs, findings, tests.
- [x] `requirements.txt`, `.gitignore`, tests, reusable modules, one-command run.
- [x] Raw data not committed; checksum verification; documented fallback if download fails.
- [x] Charts, tables and reports generated from the data (see `outputs/`).

## Known gaps to mention honestly if asked
- Dataset is fictional; licence unverified; no cost data.
- Tested only on one Python/pandas version and one operating system (see README "Tests").
- No statistical significance testing or predictive modelling (not required by the task).
