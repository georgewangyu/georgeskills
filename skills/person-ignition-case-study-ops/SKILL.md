---
name: person-ignition-case-study-ops
description: Research how a public creator, founder, builder, or operator got their initial audience, reputation, open-source traction, or credibility spike; focuses on ignition events, preconditions, distribution surfaces, and repeatable lessons.
memory_tags:
  - domain:research
  - workflow:person-ignition-case-study
  - repo_boundary:tools
  - inputs:web
  - outputs:case-study
  - risk:medium
---

# Person Ignition Case Study Ops

## Trigger

Use when:
- the user names a person and asks how they got started, broke out, became known, or accumulated unusual GitHub stars, followers, subscribers, press, or reputation
- the user asks for a person's "ignition event", first spike, breakout moment, launch path, or audience-growth mechanics
- the goal is to extract a transferable playbook from one public person's trajectory

Do not use when:
- the target is a company or product and the user mainly wants revenue-density mechanics; use `asymmetric-revenue-case-study-ops`
- the user wants a broad list of breakout candidates rather than a single-person deep dive
- the research would require private, doxxing, leaked, or non-public personal information

## Inputs

- Required: public person, handle, profile, project, or domain to investigate
- Optional: suspected breakout asset, platform of interest, date range, metric to explain, comparable people, desired depth

## Workflow

1. Establish the public baseline:
   - current public identity and role
   - pre-breakout background and credibility
   - prior audience, publishing, community, or institutional advantages
   - named projects, handles, and public profiles
2. Build a timestamped evidence trail from primary or near-primary sources:
   - launch posts, demo posts, pinned posts, newsletters, talks, podcasts, repos, changelogs, commits, issues, directories, and profile snapshots
   - platform metrics when visible, such as views, likes, reposts, followers, stars, forks, subscribers, installs, comments, or nominations
   - third-party amplification such as GitHub Trending, Product Hunt, Hacker News, newsletters, directories, creator reposts, or community lists
3. Identify candidate ignition events:
   - first major public spike
   - first compounding distribution surface
   - first credible endorsement or directory listing
   - first artifact that made the person's taste, insight, or skill legible
4. Test causality against timing:
   - compare post timestamps to metric inflection points
   - separate initial spark from later accelerants
   - call out whether the visible spike may be a symptom of already-existing hidden distribution
5. Analyze the ignition mechanics:
   - why the artifact was easy to understand or demo
   - why the audience cared at that moment
   - what social proof or status signal made sharing natural
   - what pre-existing taste, credibility, network, or content backlog reduced friction
6. Analyze the post-ignition capture loop:
   - profile positioning, pinned links, repo README, install path, newsletter, community, calls, talks, or follow-up launches
   - whether later projects reuse the same audience, category, format, or proof
7. Write or update a durable case-study artifact when a filesystem target is available:
   - use the repo's existing person/project ignition case-study folder or the user-named docs location
   - prefer a dedicated `ignition-event-case-studies/` folder when one exists
   - if no ignition-specific convention exists, create a standalone markdown note in the nearest relevant case-study folder and update local routing docs if appropriate
   - include required frontmatter when the target repo requires it
   - update the relevant index, atlas, or list doc if one exists
8. Extract transferable lessons:
   - replicable mechanics
   - context-specific advantages that should not be blindly copied
   - weakest evidence and follow-up checks

## Outputs

Create or update a standalone markdown case-study artifact when local docs are
available, then return a concise summary with:
- target snapshot
- baseline before ignition
- strongest ignition-event hypothesis
- timestamped evidence table
- initial spark versus later accelerants
- post-ignition capture loop
- transferable playbook
- confidence level and unknowns
- recommended follow-up research question
- artifact path and any index/list docs updated

## Boundaries

- Use only public information and avoid sensitive personal details that are not necessary to explain the public trajectory.
- Do not imply certainty from vanity metrics alone; label inference separately from sourced fact.
- Do not treat consistency, generic posting, or "being active online" as an ignition event unless a specific spike is supported by timestamps.
- Do not invent follower, star, install, or revenue numbers. If using sampled data, say how it was sampled.
- Keep the skill reusable: no hardcoded personal handles, emails, account ids, credentials, or user-specific defaults.
