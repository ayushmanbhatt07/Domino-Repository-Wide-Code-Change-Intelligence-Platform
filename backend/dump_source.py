import os
import re

files_to_dump = [
    "backend/analysis.py",
    "backend/dependency_graph.py",
    "backend/graph_store.py",
    "backend/ingestion.py",
    "backend/main.py",
    "backend/config.py",
    "backend/impact_analysis/matcher.py",
    "backend/impact_analysis/models.py",
    "backend/impact_analysis/traversal.py",
    "backend/test_impact.py",
    "backend/requirements.txt"
]

out = []
for fpath in files_to_dump:
    full_path = os.path.join("d:/Domino-Repository-Wide-Code-Change-Intelligence-Platform", fpath)
    if os.path.exists(full_path):
        with open(full_path, "r", encoding="utf-8") as f:
            content = f.read()
            # Redact secrets in config.py
            if "config.py" in fpath:
                content = re.sub(r'os\.getenv\("NEO4J_PASSWORD"[^\)]*\)', 'os.getenv("NEO4J_PASSWORD", "[REDACTED]")', content)
                # also redact if it was hardcoded
                content = re.sub(r'NEO4J_PASSWORD\s*=\s*".*"', 'NEO4J_PASSWORD = "[REDACTED]"', content)
            
            out.append(f"## {fpath}\n```python\n{content}\n```\n")

with open("d:/Domino-Repository-Wide-Code-Change-Intelligence-Platform/docs/SOURCE_DUMP.md", "w", encoding="utf-8") as f:
    f.write("\n".join(out))
