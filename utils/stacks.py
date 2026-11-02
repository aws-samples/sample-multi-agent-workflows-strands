"""Find, deploy, and delete a lab's AWS CloudFormation stack from a notebook.

Workshop plumbing, not a Strands API. At an event, Workshop Studio deploys each lab
stack before you start; on your own account, the notebook deploys it. Either way the
stack exports its name as `multi-agent-workshop:<lab>:stack`, which is how the notebook
finds it, and the notebook only deletes a stack that it deployed itself.
"""

from contextlib import suppress
from pathlib import Path

import boto3
from botocore.exceptions import ClientError, WaiterError


def find_or_deploy(lab: str, template_path, region=None, wait_minutes=10) -> dict:
    """Return the lab stack's Outputs as a dict, deploying the stack first if there is none."""
    cfn = boto3.client("cloudformation", region_name=region)
    stack = _find_stack(cfn, lab)
    if stack is None:
        name = f"multi-agent-workshop-{lab}"
        print(f"Deploying stack {name} (this takes a few minutes)...")
        cfn.create_stack(
            StackName=name,
            TemplateBody=Path(template_path).read_text(),
            # ProvisionedBy=notebook marks the stack as this notebook's, so cleanup() may delete it.
            Parameters=[
                {
                    "ParameterKey": "ProvisionedBy",
                    "ParameterValue": "notebook",
                },
            ],
            Capabilities=["CAPABILITY_IAM"],  # acknowledges that the template creates IAM roles
            Tags=[
                {
                    "Key": "multi-agent-workshop:lab",
                    "Value": lab,
                },
                {
                    "Key": "multi-agent-workshop:provisioned-by",
                    "Value": "notebook",
                },
            ],
        )
        # A stand-in record, so the wait below runs without describing the stack again.
        stack = {"StackName": name, "StackStatus": "CREATE_IN_PROGRESS"}

    name = stack["StackName"]
    if stack["StackStatus"] == "CREATE_IN_PROGRESS":
        print(f"Waiting up to {wait_minutes} minutes for stack {name}...")
        # On timeout or failure, fall through and report the stack's status.
        with suppress(WaiterError):
            # The waiter polls describe_stacks every Delay seconds: 4 polls per minute.
            cfn.get_waiter("stack_create_complete").wait(
                StackName=name, WaiterConfig={"Delay": 15, "MaxAttempts": wait_minutes * 4}
            )
        stack = _describe(cfn, name)

    status = stack["StackStatus"]
    # Any *_COMPLETE status is a finished, usable stack, except ROLLBACK_COMPLETE: a create that failed.
    if status.endswith("_COMPLETE") and status != "ROLLBACK_COMPLETE":
        outputs = {o["OutputKey"]: o["OutputValue"] for o in stack.get("Outputs", [])}
        print(f"Using stack {name} ({status}, provisioned by {_provisioned_by(stack)}).")
        return outputs
    raise RuntimeError(_advice(lab, stack))


def cleanup(lab: str, region=None, empty_buckets=()):
    """Delete the lab stack if the notebook deployed it, emptying the given buckets first."""
    cfn = boto3.client("cloudformation", region_name=region)
    stack = _find_stack(cfn, lab)
    if stack is None:
        print(f"No stack found for lab {lab}; nothing to delete.")
        return
    name = stack["StackName"]
    # Never delete a stack that Workshop Studio deployed: it owns that stack's lifecycle.
    if _provisioned_by(stack) != "notebook":
        print(f"Stack {name} is managed by Workshop Studio; leaving it in place.")
        return

    # CloudFormation cannot delete a bucket that still holds objects, so empty each one first.
    s3 = boto3.resource("s3", region_name=region)
    for bucket in empty_buckets:
        print(f"Emptying bucket {bucket}...")
        with suppress(s3.meta.client.exceptions.NoSuchBucket):
            # Lists every object and deletes them in batches of up to 1,000 keys.
            s3.Bucket(bucket).objects.all().delete()

    print(f"Deleting stack {name}...")
    cfn.delete_stack(StackName=name)
    try:
        # Up to 40 polls, 15 seconds apart: about 10 minutes.
        cfn.get_waiter("stack_delete_complete").wait(
            StackName=name,
            WaiterConfig={"Delay": 15, "MaxAttempts": 40},
        )
    except WaiterError:
        status = (_describe(cfn, name) or {}).get("StackStatus", "unknown")
        raise RuntimeError(
            f"Stack {name} did not delete ({status}). "
            "Check its Events tab in the CloudFormation console, then rerun this cell."
        ) from None
    print(f"Deleted stack {name}.")


def _find_stack(cfn, lab):
    """Return the stack that serves the lab, or None if there is none."""
    # Every lab stack exports its own name under this key, whoever deployed it and whatever its name.
    export = f"multi-agent-workshop:{lab}:stack"
    exports = cfn.get_paginator("list_exports").paginate()
    # search() runs the JMESPath filter on each page and yields matching values; the first match wins.
    for stack_name in exports.search(f"Exports[?Name=='{export}'].Value"):
        return _describe(cfn, stack_name)
    # A stack that is still being created, or that failed to create, exports nothing yet.
    return _describe(cfn, f"multi-agent-workshop-{lab}")


def _describe(cfn, stack_name):
    try:
        return cfn.describe_stacks(StackName=stack_name)["Stacks"][0]
    except ClientError as error:
        # describe_stacks raises a ValidationError for a missing stack; treat that as "no stack".
        if "does not exist" in error.response["Error"]["Message"]:
            return None
        raise


def _provisioned_by(stack):
    """Read ProvisionedBy from the Outputs, or from the parameter if the stack has no Outputs."""
    # The value is "notebook" or "workshop-studio". A stack that failed to create has no Outputs.
    for item in stack.get("Outputs", []):
        if item["OutputKey"] == "ProvisionedBy":
            return item["OutputValue"]
    for item in stack.get("Parameters", []):
        if item["ParameterKey"] == "ProvisionedBy":
            return item["ParameterValue"]
    return None


def _advice(lab, stack):
    name, status = stack["StackName"], stack["StackStatus"]
    if status.endswith("_IN_PROGRESS"):
        return f"Stack {name} is still {status}. Wait a few minutes, then rerun this cell."
    if _provisioned_by(stack) == "notebook":
        return (
            f"Stack {name} is {status}. Check its Events tab in the CloudFormation console, "
            f"run cleanup({lab!r}), then rerun this cell."
        )
    return f"Stack {name} is {status}. Workshop Studio manages it: ask a workshop facilitator for help."
