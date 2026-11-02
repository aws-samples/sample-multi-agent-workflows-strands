"""Prepare the data a lab needs in its AWS resources, one status line per step.

Workshop plumbing, not a Strands API. Lab 3 needs its receipt images in S3. Lab 4 needs past
incidents in AgentCore Memory and real CloudWatch Logs from its failing Lambda function before the
swarm can investigate anything.
"""

import hashlib
import json
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path

import boto3
from botocore.exceptions import ClientError

ACTOR_ID = "lambda-oncall"  # whose memory it is: the on-call team, in every session
EXTRACTION_WAIT_SECONDS = 180
POLL_SECONDS = 10


@dataclass
class SwarmLabData:
    memory_id: str
    actor_id: str
    namespace: str
    function_name: str
    log_group: str
    request_id: str
    fixture_records: list = field(default_factory=list)  # empty unless extraction was too slow


def prepare_swarm_lab(outputs: dict, region=None, data_dir="data") -> SwarmLabData:
    """Invoke the failing function, seed past incidents into memory, and wait for extraction."""
    # Imported here because only Lab 4 installs bedrock-agentcore.
    from bedrock_agentcore.memory import MemoryClient

    data = Path(data_dir)
    memory = MemoryClient(region_name=region)
    memory_id, function_name = outputs["MemoryId"], outputs["FailingFunctionName"]
    # The stack exports the namespace as a template, such as /incidents/{actorId}/; fill in the actor.
    namespace = outputs["MemoryStrategyNamespace"].replace("{actorId}", ACTOR_ID)

    # 1. Real logs: user u-1001 registers; user u-1002 has no email, so the handler raises.
    lambda_client = boto3.client("lambda", region_name=region)
    failed = []
    for user_id in ("u-1001", "u-1002", "u-1002"):
        # The default invocation type, RequestResponse, waits for the handler to finish.
        response = lambda_client.invoke(
            FunctionName=function_name,
            Payload=json.dumps({"user_id": user_id}),
        )
        # The invoke call itself succeeds when the handler raises; Lambda reports the error in FunctionError.
        if "FunctionError" in response:
            failed.append(response["ResponseMetadata"]["RequestId"])
    print(f"Invoked {function_name} 3 times; {len(failed)} failed on purpose (last request ID {failed[-1]}).")

    # 2. Past incidents become events; the semantic strategy extracts them into long-term records.
    incidents = json.loads((data / "past_incidents.json").read_text())["incidents"]
    # Records already there mean an earlier run seeded this memory; seeding again would add duplicates.
    records = _records(memory, memory_id, namespace)
    if records:
        print(f"Memory already holds {len(records)} records for actor {ACTOR_ID}; seeding skipped.")
    else:
        session_id = str(uuid.uuid4())  # AgentCore needs session IDs of at least 33 characters
        for incident in incidents:
            text = (
                f"Resolved incident {incident['id']} on {incident['date']} in {incident['service']}. "
                f"Symptom: {incident['symptom']} Root cause: {incident['root_cause']} Fix: {incident['fix']}"
            )
            # One event per incident, written as a single USER message: (text, role).
            memory.create_event(
                memory_id=memory_id,
                actor_id=ACTOR_ID,
                session_id=session_id,
                messages=[(text, "USER")],
            )
        print(f"Seeded {len(incidents)} past incidents as memory events for actor {ACTOR_ID}.")

    # 3. Extraction runs in the background; wait a bounded time, then fall back to a fixture.
    deadline = time.monotonic() + EXTRACTION_WAIT_SECONDS
    # Poll list_memory_records until every incident shows up in a record, or the deadline passes.
    while not _extracted(records, incidents) and time.monotonic() < deadline:
        time.sleep(POLL_SECONDS)
        records = _records(memory, memory_id, namespace)
    lab = SwarmLabData(
        memory_id,
        ACTOR_ID,
        namespace,
        function_name,
        outputs["FailingFunctionLogGroup"],
        failed[-1],  # the last failed request, whose traceback the logs investigator looks up
    )
    if _extracted(records, incidents):
        print(f"Memory extraction finished: {len(records)} long-term records in {namespace}.")
    else:
        # Extraction is still running: hand the lab saved records in the same shape, so it can go on.
        lab.fixture_records = json.loads((data / "fallback_records.json").read_text())["memoryRecordSummaries"]
        print(
            f"FIXTURE IN USE: extraction did not finish within {EXTRACTION_WAIT_SECONDS} s, so "
            f"recall_past_incidents also returns the {len(lab.fixture_records)} records in "
            "data/fallback_records.json. Rerun this cell later to use only real memory."
        )
    return lab


def _records(memory, memory_id, namespace):
    # MemoryClient passes list_memory_records straight to the boto3 data plane client, hence camelCase.
    return memory.list_memory_records(
        memoryId=memory_id,
        namespace=namespace,
        maxResults=100,
    )["memoryRecordSummaries"]


def _extracted(records, incidents):
    """True when every seeded service appears in at least one long-term record."""
    # Extraction rewrites the text, so compare loosely: lowercase, with hyphens read as spaces.
    texts = " ".join(r["content"]["text"] for r in records).lower().replace("-", " ")
    return all(i["service"].replace("-", " ") in texts for i in incidents)


def upload_receipts(bucket: str, region=None, folder="data/receipts", prefix="receipts/") -> list:
    """Upload the lab's receipt images to the bucket unless an identical copy is there; return the keys."""
    s3 = boto3.client("s3", region_name=region)
    keys = []
    for path in sorted(Path(folder).glob("*.png")):
        key, body = f"{prefix}{path.name}", path.read_bytes()
        try:  # an unencrypted or SSE-S3 single-part object's ETag is the MD5 of its bytes
            same = (
                s3.head_object(Bucket=bucket, Key=key)["ETag"].strip('"')  # S3 returns the ETag in quotes
                == hashlib.md5(body, usedforsecurity=False).hexdigest()
            )
        except ClientError as error:
            # head_object has no response body, so a missing key surfaces as the bare HTTP code 404.
            if error.response["Error"]["Code"] != "404":
                raise
            same = False
        if same:
            print(f"s3://{bucket}/{key} is already there; skipped.")
        else:
            s3.put_object(Bucket=bucket, Key=key, Body=body, ContentType="image/png")
            print(f"Uploaded s3://{bucket}/{key} ({len(body):,} bytes).")
        keys.append(key)
    return keys
