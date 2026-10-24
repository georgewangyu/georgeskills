# Registry format

One YAML file (needs PyYAML) or JSON file. Top level:

```yaml
identity:
  forbidden_email_patterns: ['@work\.example$']   # regexes; a match in OUR commits on a public repo is a leak

pairs:
  - id: lavish-showroom          # short, unique
    class: M                     # V vendored core, M merge fork, P port by content, C canonical + overlay, R retire
    status: active               # active | parked | planned | retire-candidate
    direction: upstream -> downstream, in words
    upstream:
      repo: ~/code/showroom      # local clone that holds the upstream ref
      url: https://...           # optional; with --fetch, a missing repo is partial-cloned here
      remote: upstream           # remote to fetch (default: first part of ref)
      ref: upstream/main         # what we track
      path: subdir               # optional; count only commits touching this path
    pin_file: ~/pkg/**/UPSTREAM.md   # optional; first SHA after "pin/sha/commit" wins over reviewed_through
    reviewed_through: 1d3f6ac    # upstream SHA reviewed (advance on adopt OR skip)
    landed_through: 1d3f6ac      # upstream SHA actually merged or ported (advance only when landed)
    since: 2026-08-10            # fallback when there is no pin: count commits since this date
    downstream:
      repo: ~/code/showroom
      upstream_ref: upstream/main    # set when downstream shares history; gives behind/ahead
    public: true                 # downstream is public: check pre-push hook + identity of our commits
    internal: true               # downstream is private: flag remotes that can push to a local path or github.com
    compare_skill_dirs:          # class C: list skills present on one side only
      here: ~/private/skills
      there: ~/public/skills
      strip_suffix: -ops
    tracking: path to the doc or ledger for this pair (informational)
```

## Base used for "new commits"

1. `pin_file` SHA, if the file exists and has one.
2. `reviewed_through`.
3. `landed_through`.
4. `since` date (reported as a finding: record a pin).

## Defaults the report suggests

| Condition | Default |
|---|---|
| `planned` | none |
| `retire-candidate` or class R | name-only: retire? |
| leak or identity finding | fix it first (safe, mechanical) |
| `parked` | defer |
| security hints | review them, adopt real fixes |
| 0 new commits | safe: advance `reviewed_through` |
| otherwise | V: draft subtree pull. M: draft merge of the latest release tag. P: review and port matches. C: promote or vendor |
