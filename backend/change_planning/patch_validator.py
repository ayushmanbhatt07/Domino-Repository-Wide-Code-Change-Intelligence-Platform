import ast
import re
from typing import List, Tuple
from .models import ChangePlan

class PatchValidator:
    def validate(self, patch: str, plan: ChangePlan) -> dict:
        valid = True
        warnings = []
        
        # 1. Syntax Status
        # To strictly do this, we'd need the modified content. Since we only have unified diff, 
        # doing full AST parse is hard without original code. 
        # We will do a basic check for now.
        syntax_status = "unverified (requires full file)"
        
        # 2. Scope Status
        files_modified = self._extract_modified_files(patch)
        scope_status = "valid"
        
        allowed_files = set()
        if plan:
            for f in plan.affected_files:
                if f.path:
                    allowed_files.add(f.path)
            for f in plan.affected_functions:
                if f.path:
                    allowed_files.add(f.path)
            for s in plan.implementation_steps:
                if s.target_file:
                    allowed_files.add(s.target_file)
                    
            for f in files_modified:
                if f not in allowed_files:
                    valid = False
                    scope_status = "invalid"
                    warnings.append(f"Modified file {f} is not explicitly allowed in ChangePlan.")
        
        # 3. Security Status
        security_status = "valid"
        for f in files_modified:
            if ".." in f or f.startswith("/"):
                valid = False
                security_status = "invalid"
                warnings.append(f"Path traversal detected: {f}")
            if ".git" in f:
                valid = False
                security_status = "invalid"
                warnings.append(f"Modification of .git is not allowed: {f}")
            if f.endswith(".env") or "secret" in f.lower() or "credentials" in f.lower():
                valid = False
                security_status = "invalid"
                warnings.append(f"Modification of potential secrets is not allowed: {f}")
                
        test_status = "unverified"
        
        return {
            "valid": valid,
            "syntax_status": syntax_status,
            "scope_status": scope_status,
            "security_status": security_status,
            "test_status": test_status,
            "warnings": warnings,
            "files_changed": files_modified
        }
        
    def _extract_modified_files(self, patch: str) -> List[str]:
        # matches `+++ b/path/to/file.py`
        files = []
        for line in patch.splitlines():
            if line.startswith("+++ "):
                path = line[4:].strip()
                if path.startswith("b/"):
                    path = path[2:]
                files.append(path)
        return files
