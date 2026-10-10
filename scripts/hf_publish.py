#!/usr/bin/env python
"""Make the HF dataset repo public but GATED, with the Replica terms as the access
condition, and upload the dataset card (documentation/hf/README.md).

Why gated, not open: the Replica terms allow publishing for non-commercial research, but
sharing only with people who "first agree to be bound by these terms". A gated repo asks
every visitor to accept them before downloading, so the data stay traceable without
breaking that condition (decisions D30). Not legal advice — check with your institution.

Usage:  HF_TOKEN=<write token> uvx --from 'huggingface_hub>=0.30' python scripts/hf_publish.py [--repo DoninhaD/prism-bench-inputs] [--dry-run]
"""
import argparse
import os
from pathlib import Path

from huggingface_hub import HfApi

ap = argparse.ArgumentParser()
ap.add_argument("--repo", default=os.environ.get("INPUTS_HF_REPO", "DoninhaD/prism-bench-inputs"))
ap.add_argument("--dry-run", action="store_true")
a = ap.parse_args()
card = Path(__file__).resolve().parents[1] / "documentation" / "hf" / "README.md"
api = HfApi(token=os.environ.get("HF_TOKEN"))
info = api.repo_info(a.repo, repo_type="dataset")
print(f"{a.repo}: private={info.private} gated={getattr(info, 'gated', None)}")
if a.dry_run:
    print(f"would upload {card} as README.md, then set private=False, gated='auto'")
    raise SystemExit(0)
api.upload_file(path_or_fileobj=str(card), path_in_repo="README.md", repo_id=a.repo,
                repo_type="dataset", commit_message="dataset card: Replica terms, gated access")
api.update_repo_settings(a.repo, repo_type="dataset", gated="auto")   # gate BEFORE going public
api.update_repo_settings(a.repo, repo_type="dataset", private=False)
info = api.repo_info(a.repo, repo_type="dataset")
print(f"done: private={info.private} gated={getattr(info, 'gated', None)} -> https://huggingface.co/datasets/{a.repo}")
