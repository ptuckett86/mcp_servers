---
name: interview-assistant
description: >-
  Guides technical interview workflows for DSA coding and backend/system design.
  Uses interview-assistant MCP tools for pattern detection, architecture advice,
  FastAPI/SQL scaffolds, test generation, and solution review. Use when the
  user is doing interview prep, LeetCode-style problems, system design, FastAPI
  challenges, SQL schema design, or asks to analyze/review/scaffold an interview problem.
  Use when asked about time complexity, space complexity, Big-O, or to recall interview
  code patterns (BFS, trie, median, brackets, tree height, FizzBuzz).
---

# Interview Assistant

## Guardrail

Tools accelerate thinking; the user must be able to explain every line. Do not dump full solutions unprompted. Ask "explain why" prompts. Faster thinking, not outsourced thinking.

## Workflow

Copy this checklist and track progress:

```
Interview Progress:
- [ ] Classify: DSA / backend / mixed
- [ ] Analyze (MCP before coding)
- [ ] Plan (pseudocode + data model)
- [ ] Scaffold (if backend)
- [ ] Implement (user-led, concise)
- [ ] Review (tests + senior checklist)
```

### Step 1 — Classify

| Type | Signals |
|------|---------|
| DSA | arrays, trees, graphs, optimize, complexity |
| Backend | API, DB, borrow, upload, scale, auth |
| Mixed | e.g. library system with algorithms for search |

### Step 2 — Analyze (call MCP first)

| Problem type | MCP tool |
|--------------|----------|
| Any | `interview_analyze` (one-shot) |
| DSA only | `detect_pattern` |
| Backend | `advise_architecture` |

Present the MCP result, then add your own brief interpretation. Do not skip analysis.

### Step 3 — Plan

Use this template:

```markdown
## Problem restatement
[Constraints, inputs, outputs]

## Approach
[Pattern or architecture choice and why]

## Pseudocode / API sketch
[Steps or endpoints]

## Data structures / schema
[Key types or tables]

## Complexity / tradeoffs
[Time/space or consistency/latency]
```

For DSA pattern reference, see [dsa-patterns.md](dsa-patterns.md).
For system design checklist, see [system-design-checklist.md](system-design-checklist.md).
For complexity narration and your past solutions, see [complexity-cheatsheet.md](complexity-cheatsheet.md) and [interview-snippets.md](interview-snippets.md).

### Step 4 — Scaffold (backend only)

Call MCP tools:
- `generate_sql_schema` — DDL, indexes, transactional queries
- `generate_fastapi_scaffold` — router, schemas, service stubs

Place generated files in the user's project structure. Implement business logic in service layer; do not overwrite user code.

### Step 5 — Implement

- Write clean, explainable code with meaningful names
- Narrate tradeoffs as you go
- For backend: use transactions for inventory/borrow flows
- Stop short of completing everything if the user should practice explaining

### Step 6 — Review

Call MCP:
- `generate_tests` — edge, boundary, stress, invalid cases
- `review_solution` — checklist + heuristic flags
- `analyze_complexity` — time/space narration for your code
- `lookup_snippet` — recall a known pattern (trie, BFS, median, brackets)

Walk through each flag and test category. Ask the user to state complexity aloud **before** showing MCP complexity results.

## MCP Tool Reference

| Tool | When |
|------|------|
| `interview_analyze` | Start of any problem |
| `detect_pattern` | DSA pattern identification |
| `generate_tests` | Before or after implementation |
| `review_solution` | After implementation |
| `generate_fastapi_scaffold` | REST API needed |
| `generate_sql_schema` | Database design needed |
| `advise_architecture` | System design discussion |
| `analyze_complexity` | Time/space Big-O + interview narration |
| `lookup_snippet` | Find your past solutions by keyword |

## Example Prompts

**DSA:** "Analyze: find longest substring without repeating characters"
→ `interview_analyze` → plan → implement → `generate_tests` → `review_solution`

**Complexity:** "What's the complexity of my BFS solution?" → user states Big-O first → `analyze_complexity` → compare

**Snippet recall:** "Show me my trie contacts pattern" → `lookup_snippet`

**Backend:** "Design a library book borrowing API with multiple copies"
→ `interview_analyze` → `generate_sql_schema` + `generate_fastapi_scaffold` → implement borrow with transaction → `review_solution`

## Anti-patterns

- Skipping MCP analysis and guessing the pattern
- Generating entire solutions when the user only asked for a hint
- Ignoring `heuristic_flags` from review (especially race conditions)
- Using MCP output verbatim without explaining it
