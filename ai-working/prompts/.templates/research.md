You are acting as a senior engineer performing research on the FormatIQ project.
Target: ORM/service reconciliation (Job schema updates drafted; ScoreImprovement alignment pending)

## Next Steps
- [ ] Finish Step 3 by reconciling ScoreImprovement ORM/service logic and stitching migrations into Alembic flow
- [ ] Smoke-test async session usage (e.g., `AsyncSessionLocal().execute("SELECT 1")`) and run targeted service tests after schema updates

## Questions/Blockers
- [ ] Should ScoreImprovement endpoints be revived in this pass or deferred until Celery async strategy (Step 4)?
- [ ] Do frontend consumers rely on any legacy `ProcessedJob` JSON shape (dict-wrapped responsibilities) that requires backward compatibility helpers?

## Risk Flags
- Schema migration stack (`apps/backend/database`) is not yet integrated with Alembic script_location; risk of drift until we wire it up
- ScoreImprovement contracts remain inconsistent between services and models; hitting those endpoints would still fail under Supabase constraints

## Cross-System Alignment
- Job API response now returns arrays for responsibilities/keywords to match frontend polling in `apps/frontend/lib/services/api-service.ts`
- Resume API contract unchanged; existing frontend integrations stay valid

Instructions:

Identify all relevant files in the repo for the target.

Map relationships (e.g., which modules call each other, how frontend ↔ backend flow works, how DB ↔ API contracts work).

Highlight potential solutions/approaches to improve or extend the target.

Document limitations, risks, or technical debt affecting this area.

Output Format:

# Research: {Target}
## Key Files
- [list]

## Code Relationships
- [describe flow/dependencies]

## Potential Solutions
- [options + tradeoffs]

## Known Limitations
- [risks/debt]