# (Optional) Lab 6: Add observability to your agents

This advanced lab reuses the AgentCore Gateway from Lab 1 and the AgentCore Memory resource from
Lab 4, deploying either notebook-owned resource when it is absent. When their optional observability
cells were run, it also reuses the managed Gateway and Memory metrics, logs, and traces they generated. It captures Strands' built-in
agent, model, and tool spans, makes real Gateway calls, reuses Lab 4's resolved Lambda incident
scenario for real Memory calls, validates a safe application span contract, and correlates managed
metrics, logs, traces, extraction, consolidation, and evaluation gates.

Run `observability.ipynb` from the top. Application spans are available immediately in the
notebook; the managed Gateway trace can take several minutes to appear in CloudWatch. Allow 20–25
minutes and treat this optional lab as take-home material during the two-hour event.

The screenshots under `images/` are workshop-owned captures from live Lab 6 runs. They show the
telemetry checkpoint, real Strands spans, Gateway health and log correlation, and real Memory
operation metrics plus the extraction and consolidation lifecycle. The Gateway trace crop shows
target execution and overhead latency without resource identifiers. Account identifiers are
excluded from the published crops.
