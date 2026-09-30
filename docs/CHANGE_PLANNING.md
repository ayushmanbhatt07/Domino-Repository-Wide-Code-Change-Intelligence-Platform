# Domino Stage 8: AI-Assisted Change Planning & Patch Generation

## Overview

Stage 8 enables developers to go beyond understanding *what* a change affects (Stage 5-7), and start planning *how* to implement the change safely. 

It consists of a two-mode architecture:
1. **Mode A (Change Planning)**: Generates a structured `ChangePlan` detailing exactly what needs to be changed and verified.
2. **Mode B (Patch Generation & Validation)**: Generates a unified diff proposal and securely validates it against the repository context.

## Architectural Principle

**The Graph is the Source of Truth. The LLM is the Reasoning Engine.**
- The system never trusts the LLM to invent files, functions, or dependencies.
- The Change Plan explicitly distinguishes between `graph_verified` facts, `llm_inferred` reasoning, and `llm_proposed` steps.

## Workflow

```text
POST /change/plan
    |-- Runs Impact Analysis (Stage 5)
    |-- Computes Risk & Hotspots (Stage 6)
    |-- Generates Structured Change Plan (Gemini LLM)
    
POST /change/patch
    |-- Consumes Change Plan
    |-- Generates Unified Diff Proposal (Gemini LLM)
    |-- Runs Patch Validation
    
POST /change/validate
    |-- Validates Syntax (heuristics)
    |-- Validates Scope (preventing modification of unallowed files)
    |-- Validates Security (preventing path traversal, .git modification, secrets)
```

## Security & Validation

- **No Arbitrary Execution**: Domino never executes the LLM-generated code automatically.
- **Untrusted Source Context**: Repository source is explicitly labeled as untrusted data in the LLM prompt to mitigate prompt-injection attacks.
- **Scope Checking**: If a generated patch attempts to modify a file that was not part of the `ChangePlan`'s explicitly approved affected files, the validator flags the scope as `invalid`.
- **Secret Protection**: Modification of `.env`, `credentials`, or files containing secrets is automatically blocked.
- **Path Traversal Protection**: Any path containing `..` or absolute prefixes is rejected.

## Endpoints

- `POST /change/plan`
- `POST /change/patch`
- `POST /change/validate`

**Note:** `PLAN != APPLY`. Domino does not provide an automatic `POST /change/apply` endpoint, ensuring that the developer retains final authority to review the generated unified diff.
