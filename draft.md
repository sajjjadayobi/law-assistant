I think we have complited product and functional specifications. but I'm not sure about the tech stack here?
my goal is to use great open source software and glue them to gather to build a great agent. for each thing I say my current guess and if I have doubt about it start it with an * sign and you must think and search to find alternative and tell me which one (including my one guess is better for my application)

lang: python
agent framwork: pydantic ai
*db: sqlite
model: claude sonnet 4.6
deyployment: docker compose
package manager: uv
interface: chainlit
*admin pannel: langfuse, or arise phonix
*query language: Direct SQL tool, simple middleware API, ...




here's what I'm thinking about and I want an opensource solution for it

# Admin pannel for non coder domain expert:
Monitoring agent performance and conversations
Reviewing user feedback (thumbs up/down)
Managing evaluation datasets
changing prompts and versionit
runing evals and seeing the results
Who uses the admin panel? non coder domain expert

What functionality is essential?
- View all conversations/traces with filtering
- View token usage and costs per conversation
- Manually grade conversations for eval
- Add/edit questions to the golden eval set
- Update table_of_content.md
- Reviewing agent responses and marking pass/fail

Separate web app