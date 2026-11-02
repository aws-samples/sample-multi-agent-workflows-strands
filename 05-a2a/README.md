# Lab 5: A2A for a publishing decision

`a2a.ipynb` decides whether an analyst may publish a buy note on a ticker. A market-data specialist and a compliance
specialist on Amazon Nova Pro each run behind their own Agent-to-Agent (A2A) server, and an orchestrator on Anthropic
Claude Sonnet 5 reaches them only through `A2AClientToolProvider`. About 20-25 minutes.

After the first run the notebook reads each agent card, the orchestrator's A2A calls, and the Agents each server built.
It then sends follow-ups with the same and a new `context_id`, and reads which Agent each context reached.

## Running it

Open `a2a.ipynb` in a fresh kernel. Run the `%pip` setup cell by itself first. If it installs or upgrades
anything, restart the kernel; then select the next cell and choose **Run > Run All Below**.

The servers are `A2AServer` instances with an `agent_factory`, served by uvicorn in background threads on
`127.0.0.1`. The lab has no stack and creates no AWS resources; it calls only Amazon Bedrock. The last cell stops every
server.

## Files

```text
a2a.ipynb               The lab
requirements.txt        Pinned packages
../utils/live_panes.py  Live pane for the orchestrator's stream_async events, and the peers' conversations
```

## Source and license

The lab uses `A2AServer` from the Strands Agents SDK and `A2AClientToolProvider` from Strands Agents Tools, both
licensed under Apache License 2.0.
