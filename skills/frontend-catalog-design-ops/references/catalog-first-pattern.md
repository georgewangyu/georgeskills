# Catalog-First Pattern

Use this reference for library, index, directory, radar, resource hub, and searchable blog frontends.

## Loops Radar Case Pattern

The successful Loops Radar prototype used a dependency-free static mockup with three tabs:

1. Plain Codex index
   - direct searchable catalog
   - left collection rail
   - main loop rows
   - category/status pills
   - copy action
   - selected item detail band
   - bottom contribution form

2. Editorial reference catalog
   - larger typographic lead
   - article-like numbered rows
   - field-guide/sidebar explanation
   - contribution form after the list
   - best for blog-like libraries where browsing matters as much as copying

3. Product catalog
   - app-like sidebar
   - search and status filters
   - table/list center
   - right detail panel
   - structured form controls
   - best when the selected item is frequently inspected or acted on

## Recommended Screen Anatomy

```text
Brand / catalog name                         Submit

Search input                                 Filters

Collection rail       Item list              Detail preview
                      Item
                      Item
                      Item

Selected item detail / example / copy block

Contribution form
```

For mobile, collapse to:

```text
Brand + Submit
Tabs / filters
Search
Collections
Items
Selected detail
Contribution form
```

## Item Schema

Use compact, scannable metadata:

- name
- one-line outcome
- category
- status: verified, ready, draft, review, needs examples
- copy/open action
- optional: source, updated date, difficulty, example count

## Detail Page / Panel Anatomy

- what this does
- when to use it
- inputs
- steps
- expected output
- example or receipt
- copy/install/open action
- suggest improvement action

## Prototype Discipline

- Build local clickable prototypes when evaluating visual direction.
- Save screenshots for every option.
- Include at least one mobile screenshot.
- Check horizontal overflow on mobile.
- Fix raw browser default controls before review.
- Keep implementation choices reversible until the user picks a direction.
