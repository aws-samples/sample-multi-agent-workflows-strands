# Security

## Reporting Security Issues

AWS takes security seriously. If you discover a potential security issue in this project,
please **do not** create a public GitHub issue. Instead, report it via the
[AWS Vulnerability Disclosure Program](https://hackerone.com/aws_vdp) or by email to
[aws-security@amazon.com](mailto:aws-security@amazon.com).

---

## About This Workshop

This repository is **educational sample code** for the AWS re:Invent 2026 workshop
OPN307 — *Build Multi-Agent Workflows with Strands Agents SDK on AWS*.

**This code is NOT intended for production use.** It is designed to run in a sandbox
or AWS-managed workshop account with synthetic data only. Review the
[Production Hardening Recommendations](#production-hardening-recommendations) before
adapting any part of this code for production workloads.

---

## Deployed AWS Services (per lab)

| Lab | Services |
|-----|---------|
| 1 — Agents as Tools | Amazon Cognito (user pool + client credentials), Amazon Bedrock AgentCore Gateway, AWS Lambda (MCP tool handler), Amazon CloudWatch Logs |
| 2 — Graph | Amazon S3 (session state), Amazon Bedrock (Nova Pro, Claude Sonnet 5) |
| 3 — Workflow | Amazon S3 (receipt images + decision records), Amazon Bedrock (Nova Pro reads the receipt images directly for OCR, Claude Sonnet 5 for the policy and audit reviewers) |
| 4 — Swarm | Amazon Bedrock AgentCore Memory, AWS Lambda (intentionally failing — workshop fixture), Amazon CloudWatch Logs, Amazon Bedrock (Claude Haiku 4.5, Claude Sonnet 5) |
| 5 — A2A | Local A2A servers in-notebook only — no AWS resources deployed |
| 6 — Observability (optional) | Amazon CloudWatch Logs (vended-log delivery sources/destinations/deliveries and a log group with 7-day retention), AWS X-Ray Transaction Search (trace segment destination set to CloudWatch Logs + full trace indexing rule), a CloudWatch Logs resource policy granting `logs:PutLogEvents` to `xray.amazonaws.com` (scoped by `aws:SourceArn`/`aws:SourceAccount`), Amazon CloudWatch Application Signals (`aws/spans`, `/aws/application-signals/data` log groups). Enables observability on the Lab 1 Gateway and Lab 4 Memory resources; deploys no new stack of its own |

All labs use **Amazon Bedrock** for model inference (all models are pre-approved AWS services).

---

## Security Controls in Place

- **IAM least privilege**: All IAM roles are scoped to specific resource ARNs. No `Resource: "*"` wildcards. The AgentCore Gateway role includes a `aws:SourceAccount` condition.
- **Cognito JWT auth on AgentCore Gateway**: Lab 1 uses client-credentials OAuth with a resource server scope (`expense-tools/invoke`). The gateway accepts only tokens from the specific workshop client.
- **S3 hardening**: All buckets enforce SSL (`DenyInsecureTransport`), block all public access, and use `BucketOwnerEnforced` ownership.
- **Synthetic data only**: All Lambda fixtures, incident records, and receipt images are fictional. No real customer or business data is used.
- **No hardcoded credentials**: Cognito client secret is retrieved at runtime; all AWS calls use IAM role credentials.
- **Workshop data is ephemeral**: All CloudFormation stacks use `DeletionPolicy: Delete`. AgentCore Memory events expire after 7 days. Cleanup cells remove all resources.

---

## Known Trade-offs and Accepted Risks

| Item | Category | Rationale |
|------|----------|-----------|
| S3 buckets use SSE-KMS with the AWS-managed `aws/s3` key | By design | The workshop buckets hold only synthetic data and are disposable, so they use SSE-KMS with the AWS managed `aws/s3` key: objects are encrypted at rest with no key to create, manage, or schedule for deletion. For production, use a customer managed key so you control its key policy, rotation, and lifecycle — see Production Hardening Recommendations |
| Lambda CloudWatch log groups not KMS-encrypted | Security Debt | 7-day retention, synthetic/workshop data only; acceptable for educational content |
| S3 access logging not configured | Non-blocking | Disposable workshop buckets; access audit trails not needed for synthetic data |
| S3 versioning not enabled | By design | Session and receipt data is synthetic and re-uploadable; unversioned buckets empty cleanly |
| Lambda functions not inside a VPC | By design | These functions access no VPC resources; adding a VPC would require NAT infrastructure with no security benefit |

---

## Production Hardening Recommendations

Before adapting any part of this code for production:

1. **Upgrade S3 encryption to a customer-managed key**: The workshop uses the AWS-managed `aws/s3` key. For production, provision a CMK with annual rotation and set `KMSMasterKeyID` to its ARN.
2. **Enable KMS encryption on CloudWatch log groups**: Add `KmsKeyId` referencing a CMK to all `AWS::Logs::LogGroup` resources.
3. **Enable S3 server access logging**: Add `LoggingConfiguration` pointing to a dedicated audit bucket.
4. **Add input validation**: If Lambda functions accept external input (beyond workshop fixtures), validate all fields before processing.
5. **Review IAM roles before production use**: The workshop IAM roles are scoped for workshop accounts; review and tighten for production account boundaries.
6. **Replace synthetic data**: All `RECEIPTS`, `POLICIES`, `PRIOR_CLAIMS`, `USERS` dicts in the Lambda `ZipFile` code are fictional — replace with real data sources using secure access patterns.
7. **Authenticate A2A callers (Lab 5)**: The workshop notebook runs local A2A servers without authentication. Add OAuth bearer tokens or IAM SigV4 before exposing A2A endpoints.

---

## Resource Cleanup

Each notebook includes a cleanup cell. Run it before ending a session to delete all workshop resources.

Manual verification:
```bash
aws cloudformation list-stacks --stack-status-filter CREATE_COMPLETE \
  --query 'StackSummaries[?starts_with(StackName,`multi-agent-workshop`)].StackName'
```

Any remaining stacks can be deleted from the CloudFormation console.

---

## Dependencies

| Dependency | Version | Labs (pinned in requirements.txt) | Notes |
|-----------|---------|-----------------------------------|-------|
| strands-agents | 1.56.0 | Labs 1, 2, 3, 4, 5, 6 | AWS open source, Apache 2.0 (Lab 5 pins the `strands-agents[a2a]` extra) |
| markdown-it-py | 4.2.0 | Labs 1, 2, 3, 4, 5 | Markdown rendering for notebook live panes |
| mcp | 1.30.0 | Labs 1, 6 | Model Context Protocol client |
| httpx | 0.28.1 | Labs 1, 5, 6 | HTTP client |
| bedrock-agentcore | 1.23.1 | Labs 4, 6 | AWS SDK (AgentCore Memory / observability) |
| strands-agents-tools | 0.8.9 | Lab 5 | Strands tools package |
| a2a-sdk | 0.3.26 | Lab 5 | Agent-to-Agent protocol SDK |
| opentelemetry-sdk | 1.44.0 | Lab 6 | OpenTelemetry tracing SDK |

> `boto3` is not pinned in any lab's `requirements.txt`; it is provided by the SageMaker/Jupyter (workshop) environment and used by the notebooks and `utils/` helpers.
