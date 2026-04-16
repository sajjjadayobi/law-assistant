# What we want: Law Agent
We have gathered all the law in Iran into a DB and want to answer questions related to Iran's law using an AI assistant.
## Functional Requirements:
What the agent needs to do: Law Assistant Agent (ChatGPT-style, not deep research)
- Agent introduction: Tell what it does clearly and concisely to the user

- Clarifying questions only if the agent is not sure: Ask clarifying questions at any point (especially at first) to understand what the user wants to know about law
  - Maximum 2-3 clarifying questions before answering
  - Questions are optional - agent makes best guess if user doesn't answer
  - May ask mid-search if finding multiple interpretations: "I found two relevant opinions with different perspectives. Which is more relevant to your situation?"
  - Does NOT ask about user expertise - infers from query style

- Knowledge base navigation: Have a table_of_content.md loaded in its context that knows what we have in the knowledge database
  - Always loaded at start of every conversation
  - Hierarchical structure: Categories → Subcategories → Single example document + count
  - Manually created once
  - Helps agent decide WHERE to search and WHAT exists

- Agentic search: Based on table_of_content.md search agentically in the database to find all relevant docs
  - Multi-hop search: Initial search → extract key terms → refined search (like Claude Code does)
  - PostgreSQL full-text search (no embeddings), it may use tags, categories and titles to narrow done the search
  - May ask clarifying questions in the middle of searches as well

- Context assembly: Retrieve documents intelligently
  - Most of the time: only retrieve direct answer documents
  - When needed: fetch parent laws (ancestors) for legal basis
  - Use DAG structure in relations table when relevant

- Answer synthesis: Combine retrieved knowledge with common sense and knowledge of the law
  - Based on user style of asking and query complexity, infer expertise level
  - Adapt style per message (not fixed across conversation)
  - Two personas: Layperson (plain language, practical guidance) and Business/Organization (risk assessment, compliance guidance)
  - Provide concise, clear and to the point answers 

- Citations: Inline citation format with numbered references
  ```
  طبق ماده ۲۷۰ قانون مجازات اسلامی [1]، حداکثر مجازات...

  منابع:
  [1] قانون مجازات اسلامی - مصوب ۱۳۹۲ - ماده ۲۷۰
  ```
  - Citations are clickable links (in first version, all go to iran.ir)
  - Paraphrase sources, don't quote exact text
  - Handle contradictory sources by presenting both and explaining nuance
  - Only cite final sources related to user's original question (not reasoning process)

- Follow-up suggestions: Generate 2-3 follow-up questions after each answer
  - LLM-generated based on the answer and question
  - Prioritize: clarifying questions first, then exploratory questions
  - Prevent repetitive suggestions across conversation turns

- Multi-turn conversations: Support detailed follow-up questions in a few rounds (typically 5-10 turns, may vary)
  - Use conversation history only (no scratchpad in first version)
  - Hard limit: 50 messages to prevent runaway costs
  - User-driven termination (no forced summaries)
  - Context window overflow is not expected

- Humble transparency & graceful rejection:
  - Say "I don't know what you currently asking" and ask more clarifying questions when:
    - No relevant documents found in DB
    - Documents are ambiguous or contradictory
    - Question is outside Iranian law scope
  - "I don't know" responses include:
    - Explanation of what was searched
    - Request for more context
  - Only answers questions about Iran's law and what it has in DB

- Language: Must always respond and talk to the user in Persian. But can use English in whatever other places possible

## Stack and Technical Decisions

- Data source: We have a PostgreSQL DB (1.3GB, 47K+ documents) from existing website
  - This is a one-time migration - agent is completely separated from that website
  - We don't need the PostgreSQL anymore after migration, but we start with it

- Framework: PydanticAI (simpler, lighter, better for ChatGPT-style assistant)
- Model: Sonnet 4.5 (claude-sonnet-4.5) for the start

* Database tool/API: The agent uses DB query language/API as its tool to do search
  - Simple query API based on tags, keywords, and summaries of metadata
  - Check only summary or related paragraph in search
  - When answering, use full versions of the docs

- UI: Chainlit chat interface for testing
  - Must show all actions/tool calls and thinking of the model
  - Has chat section to check old chats and return to them
  - Must be RTL (right-to-left for Persian)
  - Shows agent thinking in concise way to keep user engaged
  - Shows 3-5 random example questions at start (not blank canvas)
  - Has thumbs up/down for responses (written to traces and observability)

- Deployment: Must run cleanly using docker compose
- Logging: Very high detail and clean implemented logging

- Observability: Very detailed but clean observability dashboard
  - All traces
  - Token usage
  - Thumbs up/down feedback
  * Anything else possible that is relavant for error analysis and managment

- Configuration: config.yaml is the center of application control
  - Every single configuration there (nothing hardcoded)
  - Model configuration (primary model, temperature, max_tokens, etc.)
  - Database configuration (host, port, credentials via env vars)
  - Search configuration (max_results, graph_traversal_depth)
  - Conversation configuration (max_turns: 50, ...)
  - UI configuration (show_thinking, show_tool_calls, enable_feedback, example_questions)
  - Document each field with comments
  - Use environment variables for secrets

## Evaluation
- Golden set: 50 QAs with reference answers for task completion
- Eval frequency: Run evals every prompt change
- Metrics: Task completion (binary pass/fail)
  - Did the agent answer the user's legal question?
  - Grading: Human expert or LLM-as-judge
- Eval harness: Reproducible environment

## Engineering Practices: Based on the accelerated book
- Git: Use git like an experienced engineer in this repo
  - Incremental commits with descriptive messages
- AGENT.md: Captures the soul of the agent
  - During tests, when receiving feedback about agent work, concisely put it there at meta level

## Error Handling
- No docs found: Say "I don't know" with explanation of what was searched, ask for more context
- Contradictory laws: Present both sources and explain nuance/discrepancy
- Search rounds: Multi-hop agentic search (2-3 rounds), then give best answer or say "I don't know"
