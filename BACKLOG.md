# Backlog

This backlog is organized to lean on DeepAgents / LangChain capabilities where possible so we avoid reinventing features already available through skills, subagents, memory, and middleware.

## Query UX

- [ ] Add plain-English explanation area in the UI
- [ ] Add answer area in the UI for user-facing natural-language results
- [ ] Add answer-generation subagent for question + query + result summarization

## Query grounding and accuracy

- [ ] Add constrained DB lookup tool for distinct/sample field values
- [ ] Evaluate whether profiling snapshots are better than live lookup for common categorical fields
- [ ] Continue refining skill/reference files to keep examples domain-aligned and reduce unnecessary tool reads
- [ ] Revisit whether cross-domain examples are helpful only as clearly labeled pattern examples

## Reliability and recovery

- [ ] Add retry flow for failed query execution using error-aware repair
- [ ] Use middleware for retry/logging where DeepAgents/LangChain already supports it
- [ ] Surface retry/failure feedback in the UI

## Learning and memory

- [ ] Use DeepAgents memory for persistent agent learning
- [ ] Define what should be remembered vs what should remain in skills/schema files
- [ ] Optionally add structured learning store later if built-in memory is not enough

## Performance and architecture

- [x] Cache agents (currently reads every time)
- [ ] Verify whether skill file reads still occur per invocation and reduce them where possible
- [ ] Keep agent roles separated: query generation, answer generation, and repair
- [ ] Avoid reinventing features already available in DeepAgents middleware, subagents, skills, and memory

## Merged notes from earlier backlog items

- [ ] Retry when we have errors -> represented by the retry/repair flow above
- [ ] Allow DB to query data via query data tool -> represented by the constrained DB lookup tool above
- [ ] Update learning -> represented by DeepAgents memory and later structured learning if needed
- [ ] Add English explanation -> represented by the UI explanation area above
- [ ] Select AI tool -> clarify later whether this means a dedicated Oracle Select AI integration or the answer-generation subagent/tool