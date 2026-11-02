# Lab 2: Graph for expense approval

`graph.ipynb` decides an expense claim with a Strands `Graph`. An intake node fans out to a policy check and a receipt
check on Amazon Nova Pro, and a reviewer on Anthropic Claude Sonnet 5 joins them into a typed decision. An over-limit
claim goes to a manager-approval node (Claude Sonnet 5) whose tool raises a human approval interrupt. The graph keeps
its state in Amazon S3 with `S3SessionManager`, and a fresh graph instance with the same session ID resumes it with the
manager's answer. About 20-25 minutes.

After the resume, the notebook routes a rejected manager answer twice: once on text, which pays the claim, and once on a
validated `ManagerDecision`, which does not.

## Running it

Open `graph.ipynb` in a fresh kernel. Run the `%pip` setup cell by itself first. If it installs or upgrades
anything, restart the kernel; then select the next cell and choose **Run > Run All Below**. You do not change
any code.

`find_or_deploy("graph", "infra/graph.yaml")` uses the lab stack Workshop Studio deployed, or deploys
`multi-agent-workshop-graph` in your own account. The stack holds one S3 bucket, `maw-graph-sessions-<account>-<region>`,
which the notebook reads from the `SessionBucketName` output. The last cell empties the bucket and deletes the stack,
but only if the notebook deployed it.

The lab calls Amazon Bedrock, Amazon S3, and CloudFormation.

## Files

```text
graph.ipynb             The lab
infra/graph.yaml        The S3 bucket for the graph session
requirements.txt        Pinned packages
../utils/live_panes.py  Side-by-side panes for stream_async events
../utils/stacks.py      Stack discovery, deployment, and cleanup
LICENSE                 Apache License 2.0
NOTICE                  Source attribution
```

## Source and license

The lab uses the core `strands.multiagent.Graph` class. An earlier version was adapted from the
[Strands Agents Graph sample](https://github.com/strands-agents/samples/tree/main/python/01-learn/12-graph)
(Apache License 2.0, commit `04b9f0263b2957ddb307c5aaedc4dfb59f031311`). The scenario, prompts, code, and text were
rewritten for this workshop. See `LICENSE` and `NOTICE`.
