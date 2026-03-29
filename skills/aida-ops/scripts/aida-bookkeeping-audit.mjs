#!/usr/bin/env node

import fs from 'node:fs/promises';
import path from 'node:path';

async function findRepoRoot(startDir) {
  let cur = startDir;
  for (let i = 0; i < 6; i++) {
    const candidate = path.join(cur, 'TODO_AIDA.md');
    try {
      await fs.access(candidate);
      return cur;
    } catch {
      // continue
    }
    const parent = path.dirname(cur);
    if (parent === cur) break;
    cur = parent;
  }
  return startDir;
}

const ROOT =
  process.env.PRIVATE_REPO_ROOT ||
  process.env.LIFEREPO_ROOT ||
  (await findRepoRoot(process.cwd()));
const TODO_AIDA = path.join(ROOT, 'TODO_AIDA.md');
const PROJECTS = path.join(ROOT, 'openclaw', 'workspace', 'projects');

const STATUS_MAP = {
  in_progress: 'in-progress',
  awaiting_owner: 'waiting-on-owner',
  review_ready: 'review-ready',
  done: 'done',
  backlog: 'backlog',
};

const TASK_LINE_RE = /^\s*-\s*\[[ xX]\]\s*`([^`]+)`\s*\|\s*`([^`]+)`\s*\|\s*`([^`]+)`\s*$/;

async function exists(p) {
  try {
    await fs.access(p);
    return true;
  } catch {
    return false;
  }
}

async function walk(dir) {
  const out = [];
  const entries = await fs.readdir(dir, { withFileTypes: true });
  for (const e of entries) {
    const full = path.join(dir, e.name);
    if (e.isDirectory()) out.push(...(await walk(full)));
    else out.push(full);
  }
  return out;
}

async function main() {
  const raw = await fs.readFile(TODO_AIDA, 'utf8');
  const tasks = [];
  for (const line of raw.split(/\r?\n/)) {
    const m = line.match(TASK_LINE_RE);
    if (!m) continue;
    tasks.push({ id: m[1].trim(), status: m[2].trim(), prio: m[3].trim() });
  }

  const problems = [];
  for (const t of tasks) {
    const folder = STATUS_MAP[t.status];
    if (!folder) {
      problems.push({ id: t.id, status: t.status, issue: 'unknown-status' });
      continue;
    }

    const baseDir = path.join(PROJECTS, folder);
    if (!(await exists(baseDir))) {
      problems.push({ id: t.id, status: t.status, issue: `missing-status-dir:${folder}` });
      continue;
    }

    const files = await walk(baseDir);
    const hasRef = files.some((f) => path.basename(f).includes(t.id));
    if (!hasRef) {
      problems.push({ id: t.id, status: t.status, issue: `missing-artifact-in:${folder}` });
    }
  }

  if (problems.length === 0) {
    console.log('OK: bookkeeping audit passed');
    return;
  }

  console.log('BOOKKEEPING_GAPS:');
  for (const p of problems) {
    console.log(`- ${p.id} (${p.status}): ${p.issue}`);
  }
  process.exitCode = 2;
}

main().catch((e) => {
  console.error('audit failed:', e);
  process.exit(1);
});
