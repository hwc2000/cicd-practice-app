"""Reusable CI repair workflow modules.

Primary modules for new code:

- ``failure_context``: parse CI artifacts into reusable structured context
- ``openai_repair``: OpenAI-backed repair/report helpers
- ``autofix_graph``: apply/verify/retry workflow used by Jenkins

Legacy compatibility modules remain available under ``debug_agent`` and
``openai_debug_agent`` while the project transitions away from Debug Agent
terminology.
"""
