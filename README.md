# Build multi-agent workflows with Strands Agents SDK on AWS

Companion code for the AWS re:Invent 2026 workshop OPN307: six Jupyter notebook labs covering five Strands
multi-agent patterns plus an optional AgentCore observability lab. Each takes about 20–25 minutes, and no agent code
needs editing. Labs 1 and 4 contain an optional observability cell to run before their first Gateway or Memory
activity when you plan to try Lab 6.

> **Important:** This is sample code for demonstration and educational purposes. It is not intended for production use without additional security testing and review. See [SECURITY.md](SECURITY.md).

| Lab | Folder / notebook | Pattern | External connection |
| --- | --- | --- | --- |
| 1 | [`01-agents-as-tools/agents_as_tools.ipynb`](./01-agents-as-tools/agents_as_tools.ipynb) | Agents as Tools | MCP through AgentCore Gateway to a Lambda target, Cognito JWT inbound auth |
| 2 | [`02-graph/graph.ipynb`](./02-graph/graph.ipynb) | Graph | Human approval interrupt; `S3SessionManager` on an S3 bucket |
| 3 | [`03-workflow/workflow.ipynb`](./03-workflow/workflow.ipynb) | Workflow (fixed code orchestration, typed handoffs) | S3 receipt bucket; decision records written back to S3 |
| 4 | [`04-swarm/swarm.ipynb`](./04-swarm/swarm.ipynb) | Swarm | AgentCore Memory as tools; CloudWatch Logs from a failing Lambda function |
| 5 | [`05-a2a/a2a.ipynb`](./05-a2a/a2a.ipynb) | A2A | Local `A2AServer` instances in the notebook; `A2AClientToolProvider` on the caller |
| 6 (optional) | [`06-observability/observability.ipynb`](./06-observability/observability.ipynb) | Observability | AgentCore Observability for the Lab 1 Gateway: application logs, traces, and CloudWatch GenAI Observability |

## Prerequisites

- **A US AWS Region.** The labs use `us.amazon.nova-pro-v1:0`, a US cross-Region inference profile, so run the
  notebooks in a US Region.
- **Python 3.11 or later.**
- **Amazon Bedrock model access** for Amazon Nova Pro, Anthropic Claude Sonnet 5, and Anthropic Claude Haiku 4.5.
- **IAM permissions** to deploy and delete the Labs 1-4 CloudFormation stacks and the resources they create.

> **Cost note (Lab 6):** Lab 6 (and the optional observability cells in Labs 1 and 4) enables CloudWatch
> Transaction Search with 100% span indexing, which incurs CloudWatch charges. Run the Lab 6 cleanup cell afterwards.

## Running a lab

Open the notebook in SageMaker Studio JupyterLab, or in any Jupyter with AWS credentials and Amazon Bedrock
access. Run the `%pip` setup cell by itself first. If it installs or upgrades anything, restart the kernel;
then follow the notebook's run instructions. This avoids a package-triggered restart silently ending a one-click
**Run All** after setup. To install a lab's dependencies yourself, run `pip install -r requirements.txt` from that
lab's folder (or `%pip install -r requirements.txt` in the notebook).

## Notebook conventions

**Cell shape.** Setup, what to look for, run, inspect the evidence, change, verify, clean up. Evidence
checks are short assertions on result objects and tool telemetry. When a scenario requires an evidence packet,
checks verify required labels and named fixtures, not writing quality. Every lab writes a final JSON validation
artifact outside the notebook output.

**Model cell.** Every lab creates its models in the Region of the notebook's session. Labs 1, 2, 3, and 5 use these
three lines. Lab 4 creates `haiku` (`global.anthropic.claude-haiku-4-5-20251001-v1:0`) in place of `nova`:

```python
region = boto3.Session().region_name
nova = BedrockModel(model_id="us.amazon.nova-pro-v1:0", region_name=region)
sonnet = BedrockModel(model_id="global.anthropic.claude-sonnet-5", region_name=region)
```

**Agents in the cell.** Each experiment cell defines its Agents directly; repetition is fine. Every Agent sets
`callback_handler=None`, because the default handler would print the stream a second time below the panes.

**Live panes.** When several Agents work in one run, their streamed text interleaves. `utils/live_panes.py`
splits it into one pane per node or specialist. The loop stays visible in the cell:

```python
panes = LivePanes()
async for event in swarm.stream_async(task):
    panes.show(event)
```

A pane appears on its source's first event (`multiagent_node_*` events, or `as_tool` specialist events). A
Workflow, whose stages are plain Agents in your own code, passes `panes.show(event, name=...)`. After the run the
cell reads the result: `status`, `execution_order` or `node_history`, `results`, `accumulated_usage`.

## AWS resources

Labs 1-4 ship a CloudFormation template in `<lab>/infra/`. Lab 6 reuses the Lab 1 stack.
`utils/stacks.py` handles both deployment modes:

- `find_or_deploy(lab, template)` finds the stack by its export `multi-agent-workshop:<lab>:stack`. At a Workshop
  Studio event the stack is already deployed; in your own account the notebook deploys
  `multi-agent-workshop-<lab>` and waits for it.
- `cleanup(lab)` deletes the stack only if the notebook deployed it, emptying the lab's buckets first. It leaves
  Workshop Studio stacks in place.

`utils/lab_data.py` puts the data Labs 3 and 4 need into those resources. Lab 5 creates no AWS resources; its
clean-up cell stops the local servers. Optional cells in Labs 1 and 4 can create CloudWatch delivery
configuration before those labs generate activity. Lab 6 reuses that configuration and activity, completes any
missing telemetry setup, and removes the workshop-owned delivery objects in its final cleanup cell.

## Security

See [SECURITY.md](SECURITY.md) for the security controls, accepted trade-offs, and production hardening
recommendations. To report a potential security issue, follow the instructions in [SECURITY.md](SECURITY.md);
do not open a public GitHub issue.

## License

This library is licensed under the MIT-0 License. See the [LICENSE](LICENSE) file.

Labs 2 and 4 include material adapted from the [strands-agents/samples](https://github.com/strands-agents/samples)
repository, licensed under the Apache License 2.0. See [`02-graph/LICENSE`](02-graph/LICENSE),
[`02-graph/NOTICE`](02-graph/NOTICE), [`04-swarm/LICENSE`](04-swarm/LICENSE), and
[`04-swarm/NOTICE`](04-swarm/NOTICE).
