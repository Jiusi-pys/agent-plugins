# Index Schemas

## File metadata

Stored in `.scanmeta/files/*.json`.

```json
{
  "path": "src/runtime/runtime.c",
  "kind": "source_code",
  "language": "c",
  "role": "core_impl",
  "summary": "Implements runtime scheduler state and wakeup logic.",
  "tags": ["source_code", "c", "runtime"],
  "keywords": ["runtime", "scheduler", "init"],
  "exports": ["runtime_init"],
  "defines": ["MAX_RETRY"],
  "depends_on": ["runtime.h"],
  "related_files": ["src/runtime/runtime.h"],
  "related_tests": ["tests/runtime_test.c"],
  "priority_sections": [{"id": "s1", "reason": "Initialization entry point."}],
  "importance": "high",
  "complexity": "medium",
  "token_estimate": 5100,
  "confidence": "medium"
}
```

## Section index

Stored in `.scanmeta/sections/*.json`.

```json
{
  "path": "src/runtime/runtime.c",
  "sections": [
    {
      "id": "s1",
      "title": "Runtime initialization",
      "start_line": 60,
      "end_line": 140,
      "summary": "Initializes runtime state and scheduler hooks.",
      "symbols": ["runtime_init"]
    }
  ]
}
```

## Directory summary

Stored in `.scanmeta/dirs/*.json`.

```json
{
  "path": "src/runtime",
  "role": "implementation directory",
  "key_files": ["src/runtime/runtime.c", "src/runtime/runtime.h"],
  "entrypoints": [],
  "core_files": ["src/runtime/runtime.c"],
  "test_files": [],
  "config_files": [],
  "topics": ["runtime", "scheduler"],
  "pitfalls": ["Check matching tests before editing implementation files in this directory."],
  "read_order": ["src/runtime/runtime.c"],
  "confidence": "medium"
}
```

## Read plan

Computed in memory by `read_planner.py`.

```json
{
  "task": "patch exact bug in scheduler wakeup path",
  "candidate_dirs": ["src/runtime"],
  "candidate_files": ["src/runtime/runtime.c"],
  "steps": [
    "read_root_guides",
    "read_dir_summaries",
    "read_file_frontmatter",
    "read_section_indexes",
    "read_relevant_sections",
    "read_full_files"
  ],
  "full_read_required": true
}
```
