# skillos-strands

[Strands Agents](https://strandsagents.com) integration for [SkillOS](https://github.com/sheahawkins/skillos).

Implements the `Curator` interface from `skillos-core` using a Strands `Agent` backed by Amazon Bedrock. After each agent run, pass the conversation history to the curator and it will automatically create, update, or delete skills in your `SkillRepo`.

## Installation

```bash
pip install skillos-strands
```

Requires Python ≥ 3.10 and an AWS account with Amazon Bedrock access.

## Quick start

```python
from skillos_core import SkillRepo
from skillos_strands import StrandsCurator
from strands.models import BedrockModel

repo = SkillRepo("./my-skills")
curator = StrandsCurator(
    repo,
    model=BedrockModel("us.amazon.nova-pro-v1:0"),
)

# history is a list of role/content message dicts from your agent run
changelog = await curator.curate(history)

for change in changelog.applied:
    print(f"[{change.kind}] {change.name}")
```

## Embedding tools in your own agent

If you want to add skill-management capabilities to an existing Strands agent rather than running a dedicated curator, use `create_skill_tools` directly:

```python
from skillos_core import Changelog, SkillRepo
from skillos_strands import create_skill_tools
from strands import Agent
from strands.models import BedrockModel

repo = SkillRepo("./my-skills")
changelog = Changelog()
skill_tools = create_skill_tools(repo, changelog=changelog)

agent = Agent(
    model=BedrockModel("us.amazon.nova-pro-v1:0"),
    tools=[*your_other_tools, *skill_tools],
)
```

The five tools exposed are: `list_skills`, `read_skill`, `insert_skill`, `update_skill`, `delete_skill`.

## See also

- [skillos-core](../skillos-core/) — core abstractions and interfaces
- [Full documentation](https://sheahawkins.github.io/skillos/)
