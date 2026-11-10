# Parallel-build templates

## questions/<ID>-<n>.md (builder)
```
Question: <one line>
The specification says: "<quote>" (<file, section>)
Options: A <...>  B <...>
My pick and why: <...>
Who else depends on the answer: <task ids>
All gaps found in the sections I read: <list, so one request covers them all>
```

## change-requests/<ID>-<n>.md (builder)
```
The change: <exact file, field, new type or value>
Why: <the specification's words that need it, and why no change inside my own files would do>
All gaps found in the sections I read: <list>
```

## reports/<ID>.md (builder)
```
<what was built, in a page; commands run; deviations>
Lesson: <a rule, if something cost me or an earlier attempt a retry>
```

## Decision entry, appended to <n>-integration-log.md (main)
```
### R<n> <ID>: <the question in one line>
**Answer.** <the exact value or shape; the choice, with the reason>
**Spec files:** <paths>. **Applies to:** <every task id it concerns, including done tasks to rebuild>
```

## owner-questions.md (main)
```
### OQ<n> <ID>: <question>
Options: A <...>  B <...>
**Provisional default (in use now):** <A>
Asked: <date>. Answered: <pending | date, answer>
```

## handoff.md (main; written before the first long run, refreshed at every stop)
```
# Hand-off: <slice>, stopped <date>
## State
<output of plan.py status>
## Half-done
<task: what is on disk, what the last check said>
## Resume, in order
1. python3 agents/scripts/plan.py status <P>
2. <check-first for each half-done task, then the ready list>
## Never do
- re-initialise or regenerate the skeleton; discard uncommitted work (reset, checkout, clean, stash)
- delete specs, tests, docs or tools; edit a command's text in the plan
## Open
<owner questions, pending change requests>
```
