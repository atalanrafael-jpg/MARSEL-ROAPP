"""Read-only MARSEL ROAPP system synchronization/drift audit."""
from pathlib import Path
import json, re, sys

ROOT=Path(__file__).resolve().parents[1]
REGISTRY=ROOT/"config/marsel_system_sync_registry.json"
REQUIRED={
"MARSEL_ROAPP_UNIFIED_SYSTEM.md",
"docs/PROJECT_MASTER_CONTROL.md",
"docs/MARSEL_AI_CONTROL_PLANE.md",
"01_MASTER/MARSEL_ROAPP_PRODUCTIZATION_MVP.md",
".github/workflows/marsel-unified-control-plane.yml",
"config/marsel_system_sync_registry.json",
}

def main():
    registry=json.loads(REGISTRY.read_text(encoding="utf-8"))
    canonical=registry["canonical"]
    failures=[]
    if canonical["repository"]!="atalanrafael-jpg/MARSEL-ROAPP": failures.append("CANONICAL_REPOSITORY_MISMATCH")
    if canonical["branch"]!="main": failures.append("CANONICAL_BRANCH_MISMATCH")
    if registry["rules"]["no_secret_values"] is not True: failures.append("SECRET_POLICY_INVALID")
    if registry["rules"]["no_production_mutation"] is not True: failures.append("WRITE_POLICY_INVALID")
    if registry["synchronization_policy"]["readonly_default"] is not True: failures.append("READONLY_DEFAULT_INVALID")
    for p in REQUIRED:
        if not (ROOT/p).exists(): failures.append("MISSING_REQUIRED_FILE="+p)
    unified=(ROOT/canonical["architecture"]).read_text(encoding="utf-8")
    master=(ROOT/canonical["master_control"]).read_text(encoding="utf-8")
    workflow=(ROOT/canonical["control_plane"]).read_text(encoding="utf-8")
    for marker in ["MARSEL ROAPP","atalanrafael-jpg/MARSEL-ROAPP","main"]:
        if marker not in unified: failures.append("ARCHITECTURE_MISSING_MARKER="+marker)
        if marker not in master: failures.append("MASTER_CONTROL_MISSING_MARKER="+marker)
    if "PRODUCTION_WRITE=DISABLED" not in workflow and "Production WRITE" not in workflow:
        failures.append("UNIFIED_WORKFLOW_WRITE_GUARD_NOT_FOUND")
    patterns=[r"sk-[A-Za-z0-9_-]{20,}",r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",r"ghp_[A-Za-z0-9]{20,}"]
    for p in ROOT.rglob("*"):
        if not p.is_file() or ".git" in p.parts or p.suffix.lower() not in {".py",".yml",".yaml",".json",".md",".txt"}: continue
        try: s=p.read_text(encoding="utf-8",errors="ignore")
        except OSError: continue
        if any(re.search(pattern,s) for pattern in patterns):
            failures.append("SECRET_PATTERN_DETECTED="+str(p.relative_to(ROOT)))
    result="PASS" if not failures else "REVIEW_REQUIRED"
    print("SYNC_AUDIT_RESULT="+result)
    print("REQUIRED_FILES="+str(len(REQUIRED)))
    print("FAILURE_COUNT="+str(len(failures)))
    for f in failures: print("FINDING="+f)
    return 0 if not failures else 1

if __name__=="__main__":
    sys.exit(main())
