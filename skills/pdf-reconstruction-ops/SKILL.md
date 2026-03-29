---
name: pdf-reconstruction-ops
description: Modular tooling for PDF/image text extraction and OCR pre-processing.
memory_tags:
  - domain:pdf-reconstruction
  - workflow:extract-ocr
  - repo_boundary:tools
  - data_class:private-derived
  - risk:medium
---

# PDF Reconstruction Ops

## Trigger

Use this skill when extracting text from PDFs/images or preparing OCR inputs for
manual/agent reconstruction workflows.

## Boundaries

- Specification source: `liferepo` documentation/workflows
- Private state source: `<private-repo>` document locations

## Current Script Surface

Implementations currently live in:
- `skills/pdf-reconstruction-ops/scripts/`

Legacy entrypoints remain in `<private-repo>/scripts/pdf-reconstruction/` as
wrappers that delegate to this skill.
