# DS Performance Reports

Delivery metrics for Database Services, rebuilt from Jira and published as a
static site. Same codebase as EDW; what differs is data, not code.

## What is configured here

| Thing | Where it lives | Value |
| --- | --- | --- |
| Team name, prefix, site title | `data/frozen.json` → `TEAM` | DS / Database Services |
| Release grouping | `data/frozen.json` → `RELEASES` | 9.04 to 9.08 |
| Board, project, Confluence pages | `.github/workflows/refresh.yml` → `env` | see below |
| Jira credentials | repository secrets | `JIRA_EMAIL`, `JIRA_TOKEN` |

`JIRA_EMAIL` is the address of the **Atlassian account** the token belongs to,
which is not necessarily a company address — an Atlassian login created under a
vendor or personal domain stays that account's identity forever. A token always
authenticates as the account that created it, and any other address with it gives
a 401 that reads as a bad token when the token is fine.

The two Confluence pages:

* capacity — `3755671557`, *[2026] DS Team Capacity Schedule (PTO & Holidays)*
* sign-off — `3756425218`, *DS Report Sign-off Register*

Both live in the **Data Services** space. They are not optional: since September the
scripts refuse to fall back to EDW's pages, so a missing id stops the run instead of
quietly reporting EDW's plan as DS's.

## Two boards, and which one the report reads

DS runs on two boards: **39** is the Kanban board the team uses day to day to watch
the flow, and **257** is the Scrum board that holds the backlog and the sprints.
`BOARD_ID` is 257, because sprints are what a sprint report needs and a Kanban board
has none.

That split is not a limitation, because the two halves of the report come from
different places. Throughput, cycle time, discards and unplanned work are queried
against the **project**, so they cover every DS item however it was tracked. Only the
sprint half — day-1 commitment, scope change, burndown, spillover — comes from the
Scrum board. Work that lives only on the Kanban board and never enters a sprint is
counted in the flow metrics and absent from the sprint metrics, which is the accurate
description of it rather than a gap.

The workflow checks each of these three values for a leftover placeholder by name
before it calls Jira, so a missing one fails in two seconds instead of reporting
another team's board.

## Where the release grouping comes from

The company *Release Schedule 2026* assigns releases by sprint **number** — 9.06 is
sprints 16, 17 and 18; 9.07 is 19 and 20; 9.08 is 21 and 22 — and DS sprint names
carry that number. So the grouping is derived from the calendar, not decided here.
It is written into `data/frozen.json` and mirrored on the capacity page, where a
human can see it.

Three things about DS's sprints that the reports will keep pointing at, because they
are true: two sprints are numbered 16 (the second is really 17), five sprint numbers
are missing, and sprint 20 lasted two days. Releases 9.04 and 9.05 therefore cover one
sprint each. None of that is a reporting bug.

## No numbers are committed here

`data/frozen.json` carries the release skeleton — names, dates, which sprints belong
to which release — and zeros for every statistic. The figures arrive from the first
successful run against Jira. Nothing in this repository claims a number that was not
measured, and no HTML is committed before that run, so a failed run leaves no site
rather than a site full of invented figures.

## First publish

1. `git init && git add -A && git commit -m "DS delivery reports: first cut"`
2. `git branch -M main`
3. `git remote add origin https://github.com/leopoldflanagan/ds-performance-reports.git`
4. `git push -u origin main`
5. Settings → Pages → Deploy from a branch → `main` / `/ (root)`
6. Actions → Refresh → Run workflow

Step 6 is what creates the pages. Until it succeeds the site is a 404, which is the
safe direction to fail in.

## Refresh cadence

Three things can start a run, and they are not equally reliable:

| Trigger | What it is | How dependable |
|---|---|---|
| `schedule: */30` | GitHub's own timer | best effort; routinely late, sometimes skipped under load |
| `repository_dispatch` | an external scheduler calling the API | fires when it says it will |
| `workflow_dispatch` | the **Run workflow** button | on demand |

GitHub throttles scheduled workflows, so `schedule:` is the fallback, not the plan.
For an interval you can count on, have an external scheduler (cron-job.org, the same
one EDW uses) call the dispatch endpoint:

- **URL** `https://api.github.com/repos/leopoldflanagan/ds-performance-reports/dispatches`
- **Method** `POST`
- **Headers**
  - `Accept: application/vnd.github+json`
  - `Authorization: Bearer <GitHub token>`
  - `Content-Type: application/json`
- **Body** `{"event_type":"refresh"}`

The GitHub token is a **fine-grained personal access token**, scoped to this one
repository, with a single permission: **Contents: read and write**. Nothing else. Set
it to expire and renew it — a token that lives in a third-party scheduler forever is
the part of this setup most worth keeping short.

A successful dispatch returns **204 No Content** with an empty body.

### What interval is right

Every run that finds a change commits it. A shorter interval means fresher numbers and
more commits, and those commits are what make a local `git push` bounce while you are
working on the repo. Fifteen minutes suits a board being watched during a sprint;
thirty is plenty for DS today and halves the churn. The `schedule:` line and the
external interval do not have to match — the external one is what actually governs.
