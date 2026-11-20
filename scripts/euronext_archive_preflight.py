"""Fail fast when private Euronext derived-price archiving lacks reviewed rights.

The manual workflow input expresses a request, NOT legal approval.
Do not fetch exchange files, issue an archive claim, or log secret values.
"""
import os
import sys

def check(requested, general_approved, derived_approved, branch):
    if requested not in ("true", "false"):
        raise ValueError("Invalid private-retention request")
    if requested == "false":
        return "ephemeral_only"
    if branch != "refs/heads/main":
        raise ValueError("Private retention requires main branch")
    if general_approved != "true":
        raise ValueError("Private R2 retention blocked: STOCKWATCH_R2_RETENTION_APPROVED is not true; review source rights before activating")
    if derived_approved != "true":
        raise ValueError("Derived Euronext data retention blocked: STOCKWATCH_EURONEXT_STAGE_RETENTION_APPROVED is not true; review source rights before activating")
    return "approved_private_r2"

def main():
    try:
        status=check(os.environ.get("RETAIN","false"),
                     os.environ.get("STOCKWATCH_R2_RETENTION_APPROVED",""),
                     os.environ.get("STOCKWATCH_EURONEXT_STAGE_RETENTION_APPROVED",""),
                     os.environ.get("GITHUB_REF",""))
    except ValueError as exc:
        print("::error title=Euronext archive approval gate::"+str(exc),flush=True)
        return 1
    print("EURONEXT_ARCHIVE_PREFLIGHT "+status,flush=True)
    return 0

if __name__=="__main__":sys.exit(main())
