# Memory Scripts Improvements

## Duplicate-Aware Promotion

**Captured**: 2026-07-04
**Status**: open
**Priority**: high

### User Problem

The memory promotion flow can propose candidates that overlap existing
canonical memory records. Without duplicate detection, repeated facts can
create churn instead of strengthening existing records.

### Product Principle

Memory tooling should prefer reinforcement and explanation over duplicate
record creation.

### V1 Improvement

Add duplicate detection against existing canonical memory records and an
explanation field describing why each candidate was proposed.

### Completed Foundation

- Promotion tool for moving reviewed candidates into canonical stores.
- Schema validation against required record fields.
- Document-access index logging so salience metadata does not force markdown
  header churn.
- Candidate extraction from memory-eligible non-summary docs changed on the
  target date.

### Future Builds

- Lightweight entity extraction for project and person hints.
- Reinforcement logic so repeated facts can strengthen existing memories.

### Acceptance Criteria

- Candidate output identifies likely duplicates before promotion.
- Reviewers can see why each candidate was proposed.
- Repeated facts can update or reinforce an existing record.
- Validation still blocks malformed records.
