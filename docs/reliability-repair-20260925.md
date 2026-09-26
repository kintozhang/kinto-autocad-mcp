# Nameplate workflow MCP reliability repair — 2026-09-25

The desktop drawing was not edited, saved, or closed. All live writes used a new synthetic test drawing.

Changes:
- Bounded fresh ActiveDocument.FullName metadata retries for transient COM dispatch failures. General AttributeError and all write calls remain non-retriable.
- Explicit worker pre-entry failure receipts. Such failures release the operation gate because the tool was never entered.
- Audited read-only allowlist (active drawing, drawing list, project info, metadata) releases the gate after query failure. Unknown tools and uncertain writes still quarantine the session; interrupted locks are never automatically cleared.
- MCP failures now set isError=true and preserve structuredContent. Verified with actual stdio protocol tests and a live wrong-target rejection.
- Long internally generated AutoLISP expressions use a private UTF-8 data file and a short guarded command. No changes to trusted paths or SECURELOAD. No automatic replay after uncertain submission; source files and receipts remain for diagnosis.

Validation: 291 non-integration tests passed, including five new regression cases. Live evidence: work/acceptance/reliability-20260925-221635/report.json; drawing: test.dwg in that directory. MCP circle creation, target rejection, subsequent query, a >5 KB expression creating text, and save/reopen entity readback passed. The first long-expression fixture exceeded AutoLISP's argument-count limit; its error receipt was inspected, the fixture was corrected to use a quoted list, and the corrected case passed. An initial new-document dispatch readiness failure was also captured before test SaveAs; the test harness now refreshes metadata without replaying Add.

Desktop SHA-256 before/after: 99fe012e21fabbd03f9585286d112819e40c4b3876fd174d3700e56d2dfcd8b8. Size 41613 bytes; mtime unchanged. In-memory original entity count 76 and Saved=true remained unchanged.

Limits: These changes do not guarantee that AutoCAD never rejects COM calls, do not repair SVG logo geometry, and do not add general editing tools. Worker execution deadlines and uncertain-write quarantine remain. Already running MCP servers must be restarted to load revised code; no existing user process was killed.

Source snapshots before repair: work/repair-backup-20260925-220959. Existing repository modifications were preserved.

Final repeatable live run with the finalized code also passed: work/acceptance/reliability-20260925-221948/report.json. The new-document readiness check and UTF-8 file transport were exercised end to end. Final regression suite: 291 passed, 3 integration tests deselected.
