# skillos-strands

[Strands Agents](https://strandsagents.com) integration for SkillOS.

Provides `StrandsCurator`, a `Curator` implementation that uses a Strands `Agent` (Amazon Bedrock) to analyse OpenTelemetry traces and keep a `SkillRepo` up to date.

## Installation

```bash
pip install skillos-strands
```

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

# After each agent run, pass the OpenTelemetry trace
changelog = await curator.curate(trace)
print(f"{len(changelog.applied)} skill(s) changed")
```

## Using the tools directly

`create_skill_tools` returns the underlying Strands tools so you can embed them in your own agent:

```python
from skillos_core import Changelog, SkillRepo
from skillos_strands import create_skill_tools
from strands import Agent
from strands.models import BedrockModel

repo = SkillRepo("./my-skills")
changelog = Changelog()
tools = create_skill_tools(repo, changelog=changelog)

agent = Agent(
    model=BedrockModel("us.amazon.nova-pro-v1:0"),
    tools=[*your_other_tools, *tools],
)
```

The tools are: `list_skills`, `read_skill`, `insert_skill`, `update_skill`, `delete_skill`.
