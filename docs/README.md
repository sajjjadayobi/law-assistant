# Law Agent Documentation

Welcome to the Law Agent documentation! This directory contains all the documentation you need to understand, build, and maintain the Law Agent system.

## Documentation Structure

```
docs/
├── README.md (you are here)
├── architecture/            # System design and architecture
│   └── migration/          # Database migration scripts
├── development/             # Developer guides and workflows
├── best-practices/          # Engineering best practices
└── features/                # Feature-specific documentation
```

---

## Quick Start

**New to the project?** Start here:

1. **Read**: [`architecture/design.md`](architecture/design.md) - Complete system design
2. **Read**: [`architecture/search.md`](architecture/search.md) - Agent search strategy
3. **Read**: [`../CLAUDE.md`](../CLAUDE.md) - Project overview and guidelines for Claude Code
4. **Follow**: [`development/workflow.md`](development/workflow.md) - Developer workflow
5. **Start**: [`development/tasks.md`](development/tasks.md) - Task breakdown

---

## Documentation Index

### 📚 Architecture

Core system design and technical decisions.

- **[`architecture/design.md`](architecture/design.md)** - Complete functional requirements and technical design
  - Product requirements
  - Agentic search philosophy
  - Document hierarchy and schema
  - Agent behavior and conversation flow
  - UI requirements

- **[`architecture/search.md`](architecture/search.md)** - Agent search strategy and system prompt
  - Agentic vs algorithmic search
  - Three core tools
  - Multi-hop search patterns
  - **Important**: This becomes the agent's system prompt

- **[`architecture/database.md`](architecture/database.md)** - Database schema and structure
  - PostgreSQL schema documentation
  - Documents and relations tables
  - Full-text search configuration
  - DAG structure and relationships

- **[`architecture/migration/`](architecture/migration/)** - Database migration
  - Migration scripts (HTML → clean text)
  - README with migration instructions
  - Database schema SQL

---

### 💻 Development

Guides for building and contributing to the project.

- **[`development/workflow.md`](development/workflow.md)** - Developer workflow guide
  - **Plan, Build, Document, Learn** philosophy
  - How to start a task (plan.md and progress.md)
  - Testing, committing, and code review
  - Logging and debugging
  - Engineering principles from Accelerate

- **[`development/tasks.md`](development/tasks.md)** - Hierarchical task breakdown
  - 9 phases from onboarding to deployment
  - ~70 tasks with Definition of Done
  - Dependencies and success criteria
  - Designed for junior developers

- **[`development/v0.0.2-tasks.md`](development/v0.0.2-tasks.md)** - Phase 11 (Enhanced UI/UX) detailed guide
  - ✅ Task 11.1: Centered welcome screen
  - ✅ Task 11.2: Conversation history sidebar (auth + Persian UI)
  - 📋 Task 11.3: Thinking steps visualization ← **current**
  - Exact code examples and file references for each task
  - Key learnings from completed tasks

**Also see**: [`../CLAUDE.md`](../CLAUDE.md) in the project root - Instructions for Claude Code with project overview, tech stack, and development patterns.

---

### ✨ Best Practices

Proven patterns and practices for building AI agents and robust systems.

- **[`best-practices/agent-engineering.md`](best-practices/agent-engineering.md)** - Agent engineering patterns
  - Multi-context window workflows
  - Progressive disclosure
  - Trust and transparency
  - Verification strategies
  - State management

- **[`best-practices/evaluation.md`](best-practices/evaluation.md)** - Evaluation methodology
  - Eval-driven development
  - Building golden sets
  - LLM-as-judge patterns
  - Metrics and grading
  - Error analysis

---

### 🎯 Features

Feature-specific documentation created during development.

**Location**: `features/`

Each feature has its own directory with:
- `plan.md` - Design decisions, alternatives, success criteria
- `progress.md` - Development journal with learnings and blockers

**Phase 11 features (current work)**:
```
features/phase-11-enhanced-ui/
├── task-11.2-conversation-sidebar/
│   ├── plan.md
│   ├── progress.md          ← key learnings on Chainlit DB schema
│   └── screenshots/         ← proof screenshots (8 + 9 show Persian UI)
└── (task-11.3 coming next)
```

**Key learnings in `task-11.2-conversation-sidebar/progress.md`**:
- Chainlit requires camelCase columns + TEXT timestamps (not TIMESTAMP)
- Auth callback + JWT secret needed for per-user history
- Never override `execute_sql()` — parent handles it

See [`development/workflow.md`](development/workflow.md) for how to create feature documentation.

---

## How to Use This Documentation

### As a New Developer

1. **Onboarding** (Day 1-2):
   - Read `architecture/design.md` to understand the system
   - Read `architecture/search.md` to understand the core innovation
   - Read `../CLAUDE.md` for project context and guidelines
   - Follow onboarding tasks in `development/tasks.md` (Phase 0)

2. **Before Building** (Every Feature):
   - Read `development/workflow.md` for the development process
   - Check `development/tasks.md` for task details and Definition of Done
   - Review `architecture/` docs for relevant design decisions
   - Create `features/{feature-name}/plan.md` before coding

3. **While Building** (Continuously):
   - Follow workflow in `development/workflow.md`
   - Update `features/{feature-name}/progress.md` as you work
   - Reference `best-practices/` for patterns and approaches
   - Check `architecture/database.md` for schema details

4. **When Stuck**:
   - Check `features/` for similar features (read other progress.md files)
   - Review relevant sections in `architecture/design.md`
   - Consult `best-practices/` for guidance
   - Ask questions and document answers in your progress.md

### As a Team Lead

- **Onboarding**: Direct new developers to this README → `development/workflow.md` → `development/tasks.md`
- **Code Review**: Check that `features/{feature-name}/plan.md` and `progress.md` are committed with code
- **Knowledge Sharing**: Encourage team to read `features/` documentation from other developers
- **Process Improvement**: Update `development/workflow.md` based on team feedback

### As a Maintainer

- **Understanding Decisions**: Read feature's `plan.md` to understand why it was built that way
- **Debugging Issues**: Check feature's `progress.md` for known issues and solutions
- **Refactoring**: Review original design decisions before making changes
- **Onboarding New Team Members**: Point them to this documentation structure

---

## Documentation Principles

**1. Documentation IS Development**
- Write plan.md before coding (design decisions)
- Write progress.md while coding (living journal)
- Commit documentation with code (they are one)

**2. Capture WHY, Not Just WHAT**
- Design decisions include alternatives and trade-offs
- Progress logs explain reasoning in the moment
- Blockers include attempted solutions and lessons learned

**3. Write for Future Developers**
- Assume they don't know the context
- Explain terminology and concepts
- Include examples and references
- Make it easy to find related information

**4. Keep It Living**
- Update docs as system evolves
- Mark outdated information
- Add new patterns as discovered
- Refine based on feedback

---

## Contributing to Documentation

### Adding New Documentation

1. **Architecture docs**: For system-wide design changes, update `architecture/`
2. **Workflow changes**: Update `development/workflow.md`
3. **Task breakdown**: Update `development/tasks.md`
4. **New patterns**: Add to `best-practices/`
5. **Feature docs**: Create in `features/{feature-name}/`

### Documentation Style Guide

- **Use Markdown** for all documentation
- **Use descriptive headers** (H2 `##` for main sections, H3 `###` for subsections)
- **Use code blocks** with language tags for code examples
- **Use checklists** for success criteria and verification steps
- **Use bold** for important concepts
- **Use links** to reference other docs (relative paths)
- **Use examples** to illustrate concepts
- **Keep it concise** but comprehensive

### When to Update Documentation

- **Before starting**: Create plan.md
- **While coding**: Update progress.md continuously
- **After completion**: Write final summary in progress.md
- **When refactoring**: Update architecture docs if design changes
- **When discovering patterns**: Add to best-practices/
- **When process improves**: Update workflow.md

---

## Questions?

- **Architecture questions**: Check `architecture/design.md` and `architecture/search.md`
- **Workflow questions**: Check `development/workflow.md`
- **Task questions**: Check `development/tasks.md`
- **Pattern questions**: Check `best-practices/`
- **Feature questions**: Check `features/{feature-name}/plan.md` and `progress.md`

**Still stuck?** Ask your team lead or document your question in your progress.md as you find the answer - future developers will thank you!

---

## Documentation Maintenance

This documentation structure is maintained by the development team. If you find:
- **Outdated information**: Update it and commit
- **Missing information**: Add it and commit
- **Unclear explanations**: Improve them and commit
- **Broken links**: Fix them and commit

Documentation is code. Treat it with the same care.
