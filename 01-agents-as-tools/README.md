# Lab 1: Agents as Tools for an expense assistant

`agents_as_tools.ipynb` answers expense questions with an orchestrator Agent that calls receipt, policy, and audit
specialists as tools. The specialists run on Amazon Nova Pro and the orchestrator on Anthropic Claude Sonnet 5. Each
specialist reaches an AWS Lambda function through Model Context Protocol (MCP) tools on Amazon Bedrock AgentCore
Gateway, with its own `tool_filters` allow list. About 20-25 minutes.

After a first run with all three specialists and a look at the evidence, the notebook shows a fact lost between two
specialists, then carries it across with a small result contract (status, findings, evidence, uncertainties) returned
as structured output.

## Running it

Open `agents_as_tools.ipynb` in a fresh kernel. Run the `%pip` setup cell by itself first. If it installs or
upgrades anything, restart the kernel, then run through the lab-resource cell. If you plan to try Lab 6,
run **Optional: Enable observability** before the first Gateway call; otherwise skip it. Select **List the
Gateway tools** and choose **Run > Run All Below**. There is no agent code to change.

`find_or_deploy("agents-as-tools", "infra/agents-as-tools.yaml")` uses the lab stack Workshop Studio deployed, or
deploys `multi-agent-workshop-agents-as-tools` in your own account, which takes about two minutes. The notebook reads the
Gateway URL and the Amazon Cognito values from the stack outputs, reads the app client secret with
`cognito-idp:DescribeUserPoolClient`, and gets a one-hour access token with the OAuth client-credentials grant. The last
cell deletes the stack only if the notebook deployed it, unless the optional observability step saved it for Lab 6.

The lab calls Amazon Bedrock, AgentCore Gateway, AWS Lambda (through the Gateway), Amazon Cognito, and CloudFormation.

## Files

```text
agents_as_tools.ipynb       The lab
infra/agents-as-tools.yaml  AgentCore Gateway, its Lambda target with the expense tools, and the Cognito user pool
requirements.txt            Pinned packages
../utils/live_panes.py      Side-by-side panes for stream_async events
../utils/observability.py   Optional Gateway telemetry setup shared with Lab 6
../utils/stacks.py          Stack discovery, deployment, and cleanup
```
