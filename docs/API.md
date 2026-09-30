# Domino API

## 1. `POST /ingest`
Clones a GitHub repository to the local workspace.
**Body:** `{"repo_url": "https://github.com/...", "repo_name": "optional"}`

## 2. `POST /analyze`
Analyzes a local repository path and persists the AST graph to Neo4j.
**Body:** `{"path": "workspace/...", "repo_name": "...", "keep_clone": false}`

## 3. `POST /impact-analysis`
Runs an impact analysis based on a single changed entity.
**Body:**
```json
{
  "repo": "repo_name",
  "function_name": "my_func",
  "file_name": "optional_disambiguator.py",
  "depth": 3
}
```

## 4. `POST /intelligence`
Runs the Stage 6 Engineering Intelligence pipeline, producing risk metrics and test recommendations.
Takes the exact same body as `/impact-analysis`.
Returns:
```json
{
  "status": "success",
  "report": { ... },
  "markdown": "..."
}
```
