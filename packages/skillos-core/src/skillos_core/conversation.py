from __future__ import annotations

from typing import Any

# TODO: The AI agent ecosystem badly needs a cross-framework standard for
# conversation history. Right now every framework (Strands, LangChain,
# PydanticAI, ADK) has its own message format. We use litellm/OpenAI's
# message shape as the convention here, but framework packages can pass
# their native format and handle formatting themselves.
#
# Candidates to watch:
#   - Pydantic AI's ModelMessage types (closest to a typed standard)
#   - OpenAI message format via litellm (de facto lingua franca)
#   - A2A protocol message types

Message = dict[str, Any]
ConversationHistory = list[Message]
