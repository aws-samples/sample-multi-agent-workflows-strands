"""Enable workshop-owned AgentCore telemetry before Labs 1 and 4 generate activity.

The optional setup cells in those labs persist ownership information in the
workshop folder. Lab 6 loads the same file so its cleanup cell can remove only
the delivery configuration created by the workshop.
"""

from __future__ import annotations

import json
import re
import time
from pathlib import Path

import boto3
from botocore.exceptions import ClientError


STATE_VERSION = 1


def enable_gateway_observability(outputs: dict, state_path, region=None) -> dict:
    """Enable application logs and managed traces for the Lab 1 Gateway."""
    region = region or boto3.Session().region_name
    identity = boto3.client("sts", region_name=region).get_caller_identity()
    account_id = identity["Account"]
    partition = identity["Arn"].split(":", 2)[1]
    gateway_id = outputs.get("GatewayId") or outputs["GatewayUrl"].split("//", 1)[1].split(".", 1)[0]
    gateway_arn = outputs.get("GatewayArn") or (
        f"arn:{partition}:bedrock-agentcore:{region}:{account_id}:gateway/{gateway_id}"
    )
    gateway_log_group = (
        f"/aws/vendedlogs/bedrock-agentcore/gateway/APPLICATION_LOGS/{gateway_id}"
    )

    logs = boto3.client("logs", region_name=region)
    xray = boto3.client("xray", region_name=region)
    state_path = Path(state_path)
    state = load_observability_state(state_path, region=region)
    _ensure_transaction_search(
        state, state_path, logs, xray, partition, region, account_id
    )
    _ensure_full_trace_indexing(state, state_path, xray)
    _ensure_log_group(state, state_path, logs, gateway_log_group)

    slug = _clean_name(gateway_id)
    application_source = _clean_name(f"maw-{slug}-application-source")
    application_destination = _clean_name(f"maw-{slug}-application-destination")
    trace_source = _clean_name(f"maw-{slug}-trace-source")
    trace_destination = _clean_name(f"maw-{slug}-trace-destination")

    _ensure_source(
        state, state_path, logs, application_source, "APPLICATION_LOGS", gateway_arn
    )
    application_destination_arn = _ensure_destination(
        state,
        state_path,
        logs,
        application_destination,
        "CWL",
        f"arn:{partition}:logs:{region}:{account_id}:log-group:{gateway_log_group}",
    )
    _ensure_delivery(
        state,
        state_path,
        logs,
        "application",
        application_source,
        application_destination_arn,
    )

    _ensure_source(state, state_path, logs, trace_source, "TRACES", gateway_arn)
    trace_destination_arn = _ensure_destination(
        state, state_path, logs, trace_destination, "XRAY"
    )
    trace_state = xray.get_trace_segment_destination()
    trace_ready = (
        trace_state.get("Destination") == "CloudWatchLogs"
        and trace_state.get("Status") != "PENDING"
    )
    if trace_ready:
        _ensure_delivery(
            state,
            state_path,
            logs,
            "trace",
            trace_source,
            trace_destination_arn,
        )

    state["gateway_id"] = gateway_id
    state["gateway_log_group"] = gateway_log_group
    save_observability_state(state_path, state)

    print("Trace indexing   : 100%")
    print("Gateway app logs : enabled")
    if trace_ready:
        print("Gateway traces   : enabled")
        print("Lab 1 activity generated after this cell can be inspected in Lab 6.")
    else:
        print("Gateway traces   : pending")
        print("Wait a few minutes and rerun this cell before continuing with Lab 1.")
    return state | {"trace_delivery_ready": trace_ready}


def enable_memory_observability(outputs: dict, state_path, region=None) -> dict:
    """Enable application logs and managed traces for the Lab 4 Memory."""
    region = region or boto3.Session().region_name
    identity = boto3.client("sts", region_name=region).get_caller_identity()
    account_id = identity["Account"]
    partition = identity["Arn"].split(":", 2)[1]
    memory_id = outputs["MemoryId"]
    memory_arn = outputs.get("MemoryArn") or (
        f"arn:{partition}:bedrock-agentcore:{region}:{account_id}:memory/{memory_id}"
    )
    memory_log_group = (
        f"/aws/vendedlogs/bedrock-agentcore/memory/APPLICATION_LOGS/{memory_id}"
    )

    logs = boto3.client("logs", region_name=region)
    xray = boto3.client("xray", region_name=region)
    state_path = Path(state_path)
    state = load_observability_state(state_path, region=region)
    _ensure_transaction_search(
        state, state_path, logs, xray, partition, region, account_id
    )
    _ensure_full_trace_indexing(state, state_path, xray)
    _ensure_log_group(state, state_path, logs, memory_log_group)

    slug = _clean_name(memory_id)
    application_source = _clean_name(f"maw-{slug}-application-source")
    application_destination = _clean_name(f"maw-{slug}-application-destination")
    trace_source = _clean_name(f"maw-{slug}-trace-source")
    trace_destination = _clean_name(f"maw-{slug}-trace-destination")
    _ensure_source(
        state, state_path, logs, application_source, "APPLICATION_LOGS", memory_arn
    )
    destination_arn = _ensure_destination(
        state,
        state_path,
        logs,
        application_destination,
        "CWL",
        f"arn:{partition}:logs:{region}:{account_id}:log-group:{memory_log_group}",
    )
    _ensure_delivery(
        state,
        state_path,
        logs,
        "memory-application",
        application_source,
        destination_arn,
    )

    _ensure_source(state, state_path, logs, trace_source, "TRACES", memory_arn)
    trace_destination_arn = _ensure_destination(
        state, state_path, logs, trace_destination, "XRAY"
    )
    trace_state = xray.get_trace_segment_destination()
    trace_ready = (
        trace_state.get("Destination") == "CloudWatchLogs"
        and trace_state.get("Status") != "PENDING"
    )
    if trace_ready:
        _ensure_delivery(
            state,
            state_path,
            logs,
            "memory-trace",
            trace_source,
            trace_destination_arn,
        )

    state["memory_id"] = memory_id
    state["memory_log_group"] = memory_log_group
    save_observability_state(state_path, state)
    print("Memory metrics   : automatic")
    print("Memory app logs  : enabled")
    if trace_ready:
        print("Memory traces    : enabled")
        print("Lab 4 activity generated after this cell can be inspected in Lab 6.")
    else:
        print("Memory traces    : pending")
        print("Wait a few minutes and rerun this cell before continuing with Lab 4.")
    return state | {"trace_delivery_ready": trace_ready}


def load_observability_state(state_path, region=None) -> dict:
    """Load the shared cleanup manifest, or return a new one."""
    path = Path(state_path)
    if path.exists():
        state = json.loads(path.read_text())
        if state.get("version") != STATE_VERSION:
            raise RuntimeError(
                f"Unsupported observability state version in {path}; remove it and rerun setup."
            )
        if region and state.get("region") not in {None, region}:
            raise RuntimeError(
                f"Observability state belongs to Region {state['region']}, not {region}."
            )
    else:
        state = {
            "version": STATE_VERSION,
            "region": region,
            "previous_trace_destination": None,
            "transaction_search_changed": False,
            "resource_policy_created": False,
            "previous_resource_policy_document": None,
            "previous_indexing_percentage": None,
            "indexing_changed": False,
            "log_groups": {},
            "delivery_sources": {},
            "delivery_destinations": {},
            "deliveries": {},
            "memory_event": None,
            "memory_records": [],
        }
    state.setdefault("region", region)
    for key in ("log_groups", "delivery_sources", "delivery_destinations", "deliveries"):
        state.setdefault(key, {})
    state.setdefault("memory_event", None)
    state.setdefault("memory_records", [])
    return state


def save_observability_state(state_path, state: dict) -> None:
    """Atomically persist ownership information for Lab 6 cleanup."""
    path = Path(state_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(state, indent=2, sort_keys=True))
    temporary.replace(path)


def delete_observability_state(state_path) -> None:
    """Remove the manifest after Lab 6 has restored the previous configuration."""
    Path(state_path).unlink(missing_ok=True)


def _clean_name(value):
    return re.sub(r"[^\w-]", "-", value)[:60]


def _is_missing(error):
    return error.response["Error"]["Code"] in {
        "ResourceNotFoundException",
        "NotFoundException",
        "404",
    }


def _wait_for_trace_destination(xray, expected, timeout_seconds=60):
    deadline = time.monotonic() + timeout_seconds
    while True:
        state = xray.get_trace_segment_destination()
        if state.get("Destination") == expected and state.get("Status") != "PENDING":
            return state
        if time.monotonic() >= deadline:
            return state
        time.sleep(5)


def _ensure_transaction_search(
    state, state_path, logs, xray, partition, region, account_id
):
    current = xray.get_trace_segment_destination()
    current_destination = current.get("Destination") or "XRay"
    if state.get("previous_trace_destination") is None:
        state["previous_trace_destination"] = current_destination
        save_observability_state(state_path, state)
    if current.get("Status") == "PENDING":
        current = _wait_for_trace_destination(xray, current_destination)
    if current_destination == "CloudWatchLogs":
        return current

    policy_name = "AgentCoreTransactionSearch"
    policies = logs.describe_resource_policies(limit=50).get("resourcePolicies", [])
    existing = next(
        (item for item in policies if item.get("policyName") == policy_name), None
    )
    if existing and state.get("previous_resource_policy_document") is None:
        state["previous_resource_policy_document"] = existing.get("policyDocument")
    if not existing:
        state["resource_policy_created"] = True
    policy = {
        "Version": "2012-10-17",
        "Statement": [{
            "Sid": "TransactionSearchXRayAccess",
            "Effect": "Allow",
            "Principal": {"Service": "xray.amazonaws.com"},
            "Action": "logs:PutLogEvents",
            "Resource": [
                f"arn:{partition}:logs:{region}:{account_id}:log-group:aws/spans:*",
                (
                    f"arn:{partition}:logs:{region}:{account_id}:"
                    "log-group:/aws/application-signals/data:*"
                ),
            ],
            "Condition": {
                "ArnLike": {
                    "aws:SourceArn": f"arn:{partition}:xray:{region}:{account_id}:*"
                },
                "StringEquals": {"aws:SourceAccount": account_id},
            },
        }],
    }
    logs.put_resource_policy(
        policyName=policy_name, policyDocument=json.dumps(policy)
    )
    save_observability_state(state_path, state)
    xray.update_trace_segment_destination(Destination="CloudWatchLogs")
    state["transaction_search_changed"] = True
    save_observability_state(state_path, state)
    return _wait_for_trace_destination(xray, "CloudWatchLogs")


def _ensure_full_trace_indexing(state, state_path, xray):
    rules = xray.get_indexing_rules().get("IndexingRules", [])
    default = next((item for item in rules if item.get("Name") == "Default"), None)
    percentage = (
        default.get("Rule", {})
        .get("Probabilistic", {})
        .get("DesiredSamplingPercentage", 1.0)
        if default
        else 1.0
    )
    if percentage == 100.0:
        return
    if state.get("previous_indexing_percentage") is None:
        state["previous_indexing_percentage"] = percentage
    xray.update_indexing_rule(
        Name="Default",
        Rule={"Probabilistic": {"DesiredSamplingPercentage": 100.0}},
    )
    state["indexing_changed"] = True
    save_observability_state(state_path, state)


def _ensure_log_group(state, state_path, logs, name):
    exists = any(
        item.get("logGroupName") == name
        for item in logs.describe_log_groups(
            logGroupNamePrefix=name, limit=50
        ).get("logGroups", [])
    )
    if not exists:
        logs.create_log_group(logGroupName=name)
        state["log_groups"][name] = True
        save_observability_state(state_path, state)
    logs.put_retention_policy(logGroupName=name, retentionInDays=7)
    state["log_groups"][name] = state["log_groups"].get(name, False) or not exists
    save_observability_state(state_path, state)


def _ensure_source(state, state_path, logs, name, log_type, resource_arn):
    try:
        source = logs.get_delivery_source(name=name)["deliverySource"]
        created = False
    except ClientError as error:
        if not _is_missing(error):
            raise
        source = logs.put_delivery_source(
            name=name, logType=log_type, resourceArn=resource_arn
        )["deliverySource"]
        created = True
    state["delivery_sources"][name] = (
        state["delivery_sources"].get(name, False) or created
    )
    save_observability_state(state_path, state)
    return source["arn"]


def _ensure_destination(
    state, state_path, logs, name, destination_type, log_group_arn=None
):
    try:
        destination = logs.get_delivery_destination(name=name)["deliveryDestination"]
        created = False
    except ClientError as error:
        if not _is_missing(error):
            raise
        kwargs = {"name": name, "deliveryDestinationType": destination_type}
        if log_group_arn:
            kwargs["deliveryDestinationConfiguration"] = {
                "destinationResourceArn": log_group_arn
            }
            kwargs["outputFormat"] = "json"
        destination = logs.put_delivery_destination(**kwargs)["deliveryDestination"]
        created = True
    state["delivery_destinations"][name] = (
        state["delivery_destinations"].get(name, False) or created
    )
    save_observability_state(state_path, state)
    return destination["arn"]


def _ensure_delivery(
    state, state_path, logs, label, source_name, destination_arn
):
    existing = None
    for page in logs.get_paginator("describe_deliveries").paginate():
        existing = next(
            (
                item
                for item in page.get("deliveries", [])
                if item["deliverySourceName"] == source_name
                and item["deliveryDestinationArn"] == destination_arn
            ),
            None,
        )
        if existing:
            break
    if existing:
        delivery_id = existing["id"]
    else:
        delivery_id = logs.create_delivery(
            deliverySourceName=source_name,
            deliveryDestinationArn=destination_arn,
        )["delivery"]["id"]
        state["deliveries"][label] = delivery_id
    save_observability_state(state_path, state)
    return delivery_id
