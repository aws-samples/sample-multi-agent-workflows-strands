# Lab 3: Workflow for a receipt batch

`workflow.ipynb` reviews a batch of four synthetic expense claims with a fixed Workflow written in plain Python, as the
[Strands Workflow guide](https://strandsagents.com/docs/user-guide/sdk/multi-agent/workflow/) describes. For each claim,
an extractor on Amazon Nova Pro reads the receipt image from Amazon S3 and returns typed `ReceiptFacts`. A policy
reviewer and an audit reviewer on Anthropic Claude Sonnet 5 then check those facts in parallel, and Python joins both
reviews, sets the recommendation, and writes a decision record back to S3. About 20-25 minutes.

```text
S3 receipt image -> extract -> (policy + audit) -> join -> decide -> S3 decision record
```

The notebook runs the batch, shows the evidence for each stage, and then runs a decision stage with an output
invariant on the claim whose receipt date is under a stain (every stage succeeds, but the evidence is not enough).
Participants only run the cells; nothing needs editing.

## Running it

Open `workflow.ipynb` in a fresh kernel. Run the `%pip` setup cell by itself first. If it installs or upgrades
anything, restart the kernel; then select the next cell and choose **Run > Run All Below**.

`find_or_deploy("workflow", "infra/workflow.yaml")` uses the lab stack Workshop Studio deployed, or deploys
`multi-agent-workshop-workflow` in your own account. `upload_receipts()` then uploads `data/receipts/*.png` under
`receipts/` and skips images that are already there. The workflow writes its records under `decisions/<run>/`. The last
cell empties the bucket and deletes the stack only if the notebook deployed it.

The lab calls Amazon Bedrock, Amazon S3, and CloudFormation.

## Files

```text
workflow.ipynb              The lab
infra/workflow.yaml         The receipt bucket
data/receipts/*.png         Four synthetic receipts; the date on r-1045.png is under a stain
images/topology.png         The workflow's stages and join
requirements.txt            Pinned packages
../utils/live_panes.py      Side-by-side panes for stream_async events
../utils/lab_data.py        Receipt upload
../utils/stacks.py          Stack discovery, deployment, and cleanup
```
