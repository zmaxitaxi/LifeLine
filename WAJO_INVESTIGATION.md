# Wajo investigation and agent decision

Investigated November 13, 2026. The user subsequently chose **a local model**, replacing the initial Claude preference. The application uses **Llama 3.1 8B through Ollama**, not Claude or Fo. No Anthropic key is needed.

## What was actually verified

- Python/httpx connected to `https://mcp.api.wajo.ai/fo` using Streamable HTTP MCP. Anonymous calls returned HTTP 401 with protected-resource metadata. After the user supplied a key privately, initialization and tool discovery succeeded.
- Authentication used `X-API-Key` from the ignored `.env.local`. Official docs also describe Bearer keys and OAuth. No login bypass was attempted.
- The live Fo profile exposed **five** tools: `ask_fo`, `get_fo_reply`, `list_fo_conversations`, `get_fo_conversation`, and `start_fo_call`. Input/output schemas and annotations are preserved in [sanitized evidence](docs/evidence/wajo-investigation.json). The public catalogue did not list the voice tool; the authenticated discovery is the observed surface.
- A read-only listing succeeded. No private transcripts were read. One isolated greeting explicitly prohibited tools, connected-account access, contacting people and external actions. Fo returned the requested greeting in **24.795 seconds**. No calls, emails, purchases or bookings were requested. This is a single connectivity test, not a reliability or safety benchmark.
- `ask_fo` is annotated as open-world, non-read-only and potentially destructive. The `/fo` profile does not accept client-supplied tool definitions or return LifeLine tool-call blocks. Successful connectivity therefore does not establish constrained energy-planning orchestration.

## Feasibility and unresolved questions

[Wajo's MCP documentation](https://wajo.ai/docs/mcp-server.md) describes account-scoped keys/OAuth. Its separate [`/mcp` platform](https://wajo.ai/docs/mcp-tools.md) supports agent creation, API connectors and remote MCP registration. [Typed API connectors](https://wajo.ai/docs/connectors.md) could theoretically expose an authenticated deployed LifeLine service to a constrained custom agent. [Sessions](https://wajo.ai/docs/sessions.md) provide continuity and polling. That path would require a deployment, account configuration, restricted capabilities and a separate end-to-end validation; none was provisioned. Localhost is not reachable by Wajo's hosted runtime.

An owned interface could proxy MCP calls, but authorization for public redistribution, tenant isolation, rate limits and production embedding was not established. No application integration, SLA, sustained-latency study or account-specific usage entitlement is claimed. The [public pricing page](https://wajo.ai/) advertises free Fo Mini with a daily allowance and an invite tier; it does not establish this account's MCP quota. The [privacy notice](https://wajo.ai/privacy) describes prompt/content processing and service providers. Do not send patient data or infer clinical-data suitability from marketing claims.

## Architecture comparison

| Option | Feasibility and complexity | Reliability, tools and user experience | Security/privacy | Cost and relevance |
|---|---|---|---|---|
| A: Fo as primary | Authenticated conversation works; custom LifeLine orchestration/embedding unverified. Additional hosted connector work. | Conversation/polling supported; one greeting took about 25 s. Fo is broader than the planning task. | Existing Fo capabilities include external actions; prompt-only restrictions do not equal a technical allowlist. | Account-specific MCP terms unverified. Coordination is not needed for the MVP's energy decision. |
| B: Claude + Wajo | Client tool calling is documented, but two providers and extra account/deployment work. Not implemented. | More failure boundaries; Wajo adds no demonstrated energy-planning capability. | Two external data processors and a broad coordination layer. | Claude tokens plus unverified Wajo entitlement; weakest fit for the remaining demo time. |
| C: Claude alone | Technically straightforward client tools; no key configured and user preferred avoiding setup. | Documented structured tool calls; real-provider behavior not tested here. | Backend-only secret and allowlisted tools would be needed. | Usage billed by tokens; the user's approximate credit balance was not independently verified. |
| D: local Ollama | Already installed; existing Llama 3.1 8B weights. No hosted key, new infrastructure or model download. Implemented. | Actual tool selections tested. Bounded requests, strict argument checks, visible fallback. Quality/latency depend on hardware. | Loopback-only model URL, remote/cloud tags rejected, no code execution or write tools. Weather still leaves the machine. | No hosted inference bill; local memory/power cost. Directly demonstrates a constrained planning assistant and supports disconnected reasoning. |

**Decision:** D, following the user's local-model instruction. It provides useful language understanding while keeping computation and permissions inside LifeLine. Claude remains a possible future adapter; Wajo is an isolated, successful proof of concept, not a dependency. See [local-agent architecture](ARCHITECTURE.md).

Anthropic's [client tool interface](https://platform.claude.com/docs/en/agents-and-tools/tool-use/overview) supports C in principle. Ollama's [tool-calling API](https://docs.ollama.com/capabilities/tool-calling) supports D. Neither documentation nor a small prompt sample establishes general reliability.

To repeat only the isolated Wajo checks: `.venv/bin/python scripts/check_wajo.py`. Add `--greeting` only for the static no-action greeting. The script never prints credentials, internal conversation handles, account titles or transcripts. The application does not load or use the Wajo key.
