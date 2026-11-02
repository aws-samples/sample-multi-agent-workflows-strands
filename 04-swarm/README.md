# Lab 4: Swarm for Lambda error analysis

`swarm.ipynb` investigates a failing AWS Lambda function with a Strands `Swarm`. Logs, code, and docs investigators on
Anthropic Claude Haiku 4.5 hand the evidence-gathering work to each other by what they find. After the Swarm stops, deterministic
notebook code verifies that every evidence source ran, then invokes an analyzer on Anthropic Claude Sonnet 5 exactly
once to write the root cause and fix. The analyzer recalls incidents from Amazon Bedrock AgentCore Memory; after the
evidence packet passes validation, deterministic notebook code records the incident once. About 20-25 minutes.

The notebook runs an evidence-gathering Swarm and its deterministic final analyzer, then reruns the investigator team
with a tight `max_handoffs` to compare a limit-triggered stop with a completed run, and recalls the analyzer's record
from a new session. There is no agent code to edit.

## Running it

Open `swarm.ipynb` in a fresh kernel. Run the `%pip` setup cell by itself first. If it installs or upgrades
anything, restart the kernel, then run through the lab-resource cell. If you plan to complete Lab 6, run
**Optional: Enable observability** before Memory data preparation; otherwise skip it. The optional cell enables
Memory application logs and managed traces. Select **Prepare the lab
data** and choose **Run > Run All Below**.

`find_or_deploy("swarm", "infra/swarm.yaml")` uses the lab stack Workshop Studio deployed, or deploys
`multi-agent-workshop-swarm` in your own account. `prepare_swarm_lab()` then invokes the failing function, seeds
`data/past_incidents.json` into memory, and waits up to 180 seconds for extraction before it falls back to the labelled
fixture `data/fallback_records.json`. The last cell deletes the stack only if the notebook deployed it.
When observability is enabled, it keeps the Memory resource and telemetry for Lab 6 instead.

The lab calls Amazon Bedrock, AgentCore Memory, AWS Lambda, CloudWatch Logs, and CloudFormation.

## Files

```text
swarm.ipynb                 The lab
infra/swarm.yaml            AgentCore Memory (semantic strategy) and the failing Lambda function
data/past_incidents.json    Incidents seeded into memory
data/fallback_records.json  Labelled fixture used only when extraction is too slow
data/evidence.json          Source code and runbooks for the investigator tools
requirements.txt            Pinned packages
../utils/live_panes.py      Side-by-side panes for stream_async events
../utils/lab_data.py        Lab data preparation
../utils/observability.py   Optional Memory telemetry setup shared with Lab 6
../utils/stacks.py          Stack discovery, deployment, and cleanup
```

## Source and license

The lab uses the core `strands.multiagent.Swarm` class; its limit settings were informed by the
[Strands Agents Swarm sample](https://github.com/strands-agents/samples/tree/main/python/01-learn/11-swarm)
(Apache License 2.0). See `LICENSE` and `NOTICE`.
