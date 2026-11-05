"""Side-by-side live panes for the events of a Strands `stream_async` loop.

By default every Strands Agent prints its stream to the same cell output, so when several
Agents work in one run their text interleaves. LivePanes splits that stream by Agent, one
bordered pane per Swarm or Graph node or Agent-as-tool specialist, so you can watch them work
side by side. It only displays events; it never runs anything.

The panes are one plain HTML output that is updated in place, so they need no widget extension
and stay in the saved notebook.

`show_conversations` draws the same panes once, from finished Agents' messages, for Agents whose
stream you cannot loop over, such as the Agents behind an A2A server.
"""

import html
import itertools
import json
import re
import time

from IPython.display import HTML, display
from markdown_it import MarkdownIt
from strands.multiagent import Status

# The border and status color of a pane in each state.
COLORS = {
    "Waiting": "#5f6b7a",
    "Running": "#006ce0",
    "Completed": "#037f0c",
    "Failed": "#d91515",
    "Stopped": "#5f6b7a",
    "Interrupted": "#8d6605",
}
REFRESH_SECONDS = 0.15
GRID_STYLE = "display:grid;gap:12px;width:100%;grid-template-columns:repeat(auto-fill, minmax(280px, 1fr))"
# Raw HTML in model text is escaped, never passed through.
MARKDOWN = MarkdownIt("commonmark", {"html": False}).enable(["table", "strikethrough"])
_ids = itertools.count(1)  # a unique HTML id for each LivePanes output
# Some models wrap their reasoning in <thinking> tags inside the text. Three patterns remove it:
# a closed block, a block still open at the end of the text (mid-stream), and any stray tag left over.
_THINKING_BLOCK = re.compile(r"<thinking\b[^>]*>.*?</thinking\s*>", re.IGNORECASE | re.DOTALL)
_OPEN_THINKING_BLOCK = re.compile(r"<thinking\b[^>]*>.*\Z", re.IGNORECASE | re.DOTALL)
_THINKING_TAG = re.compile(r"</?thinking\b[^>]*>", re.IGNORECASE)


def participant_text(text):
    """Remove model reasoning blocks before text is shown to a participant."""
    text = _THINKING_BLOCK.sub("", str(text))
    text = _OPEN_THINKING_BLOCK.sub("", text)
    return _THINKING_TAG.sub("", text)


class _Pane:
    def __init__(self, name, changed):
        self.name, self.changed = name, changed
        self.state, self.turns, self.text = "Waiting", 0, []

    def start(self):
        """Begin a turn. An Agent that runs again gets a Turn N separator in the same pane."""
        self.turns += 1
        if self.turns > 1:
            self.text.append(f"\n\n---\n\n**Turn {self.turns}**\n\n")
        self.state = "Running"
        self.changed(force=True)

    def write(self, text):
        if self.state != "Running":
            self.start()
        self.text.append(text)
        self.changed(force=False)

    def stop(self, state):
        self.state = state
        self.changed(force=True)

    def body(self):
        """Streaming text as escaped plain text; a finished pane's text rendered as Markdown."""
        # Sanitize the joined stream so tags split across separate events are handled together.
        text = participant_text("".join(self.text))
        if self.state == "Running":
            return f'<div style="white-space:pre-wrap;overflow-wrap:anywhere">{html.escape(text)}</div>'
        return f'<div style="overflow-wrap:anywhere">{MARKDOWN.render(text)}</div>'

    def html(self):
        color = COLORS[self.state]
        turns = f" (turn {self.turns})" if self.turns > 1 else ""
        return (
            f'<div style="border:1px solid {color};border-radius:6px;padding:10px 12px;min-width:0">'
            f'<div style="font-weight:bold">{html.escape(self.name)}</div>'
            f'<div style="color:{color};font-weight:bold;margin:2px 0 6px">{self.state}{turns}</div>'
            # column-reverse keeps a scrolling pane pinned to its newest text.
            '<div style="max-height:220px;overflow:auto;display:flex;flex-direction:column-reverse">'
            f"{self.body()}</div></div>"
        )


class LivePanes:
    """Show each event of an Agent, Graph, or Swarm `stream_async` loop in the pane of its source."""

    def __init__(self):
        self.panes = {}
        self.top = None  # pane name of the Agent whose stream_async you loop over, if it is an Agent
        self.agent_tools = {}  # toolUseId of an Agent-as-tool call -> that specialist's pane name
        self.tool_names_shown = set()
        self.id = f"live-panes-{next(_ids)}"
        self.handle = None  # displayed on the first pane, so defining Agents shows nothing
        self.next_render = 0.0

    def pane(self, name):
        if name not in self.panes:
            self.panes[name] = _Pane(name, self._changed)
            self._changed(force=True)
        return self.panes[name]

    def _changed(self, force):
        """Redraw on every state change, and at most every REFRESH_SECONDS while text streams in."""
        if self.panes and (force or time.monotonic() >= self.next_render):
            grid = "".join(pane.html() for pane in self.panes.values())
            page = HTML(
                f'<div class="live-panes mathjax_ignore" id="{self.id}" style="{GRID_STYLE}">{grid}</div>'
            )
            # display_id=True returns a handle; update() then replaces that one output in place.
            if self.handle is None:
                self.handle = display(page, display_id=True)
            else:
                self.handle.update(page)
            self.next_render = time.monotonic() + REFRESH_SECONDS

    def show(self, event, name=None):
        """Show one event. Pass `name` when your own code streams several Agents into these panes (a
        Workflow): the event goes to that pane, and the Agent's final result completes only that pane."""
        kind = event.get("type", "")
        # Swarm and Graph wrap each node's Agent events in multiagent_* events that carry the node_id,
        # so the node_id names the pane. Any other event comes from a single Agent's own stream.
        if name is not None:
            self._agent_event(name, event)
            if "result" in event:
                self.pane(name).stop("Completed")
        elif kind == "multiagent_node_start":
            self.pane(event["node_id"]).start()
        elif kind == "multiagent_node_stream":
            self._agent_event(event["node_id"], event["event"])
        elif kind == "multiagent_node_stop":
            failed = event["node_result"].status == Status.FAILED
            self.pane(event["node_id"]).stop("Failed" if failed else "Completed")
        elif kind == "multiagent_node_cancel":
            self.pane(event["node_id"]).stop("Failed")
        elif kind == "multiagent_node_interrupt":  # the node waits for a human response
            self.pane(event["node_id"]).stop("Interrupted")
        elif kind == "multiagent_handoff":  # Swarm handoff or next Graph batch: those nodes are queued
            for node_id in event["to_node_ids"]:
                self.pane(node_id).stop("Waiting")
        elif kind == "multiagent_result":
            self._finish(event["result"].status == Status.COMPLETED)
        elif not kind.startswith("multiagent_"):
            self._agent_event(None, event)
            if "result" in event:
                self._finish(True)

    def _agent_event(self, name, event):
        """Show one Agent event in pane `name` (None: the top-level Agent, named on first output)."""
        if event.get("type") == "tool_stream" and isinstance(event["tool_stream_event"]["data"], dict):
            # An Agent used as a tool: its events arrive wrapped in the caller's tool_stream events.
            use = event["tool_stream_event"]["tool_use"]
            if use["toolUseId"] not in self.agent_tools:
                self.agent_tools[use["toolUseId"]] = use["name"]
                self.pane(use["name"]).start()
            self._agent_event(use["name"], event["tool_stream_event"]["data"])
            return
        # "data" events carry streamed text. Tool-input events repeat current_tool_use for every
        # chunk, so a tool name is written once, the first time its toolUseId appears.
        tool = event.get("current_tool_use") or {}
        new_tool = tool.get("toolUseId") and tool["toolUseId"] not in self.tool_names_shown
        if "data" in event or new_tool:
            if name is None:  # name the top-level Agent's pane once, from the event's agent if it has one
                self.top = self.top or getattr(event.get("agent"), "name", None) or "agent"
                name = self.top
            pane = self.pane(name)
            if "data" in event:
                pane.write(str(event["data"]))
            if new_tool:
                self.tool_names_shown.add(tool["toolUseId"])
                pane.write(f"\n[tool: {tool.get('name')}]\n")
        # force_stop: the event loop ended this Agent early, for example on an exception.
        if event.get("force_stop") and (name or self.top) in self.panes:
            self.panes[name or self.top].stop("Failed")
        # A specialist's pane completes when the caller's next message holds the toolResult for its call.
        for block in event.get("message", {}).get("content", []):
            result = block.get("toolResult")
            if result and result["toolUseId"] in self.agent_tools:
                done = self.pane(self.agent_tools[result["toolUseId"]])
                done.stop("Failed" if result.get("status") == "error" else "Completed")

    def _finish(self, completed):
        """At the final result: a pane still Running did not finish; a Waiting one never got its turn."""
        for pane in self.panes.values():
            if pane.state == "Running":
                pane.stop("Completed" if completed else "Failed")
            elif pane.state == "Waiting":
                pane.stop("Stopped")
        self._changed(force=True)  # the final state, even if no pane changed since the last throttled write


def show_conversations(agents):
    """Show the finished conversations of Agents whose stream you cannot loop over, one pane per Agent.

    `agents` maps a pane name to an Agent, for example the Agents behind an A2A server. Each pane lists
    the Agent's messages: the text it received and wrote, its tool calls, and their results.
    """
    panes = []
    for name, agent in agents.items():
        pane = _Pane(name, changed=lambda force: None)  # draws nothing itself; all panes display once below
        for message in agent.messages:
            for block in message["content"]:
                if "text" in block:
                    pane.write(f"**{message['role']}:** {block['text']}\n\n")
                elif "toolUse" in block:
                    use = block["toolUse"]
                    pane.write(f"`[tool: {use['name']}] {json.dumps(use['input'])}`\n\n")
                elif "toolResult" in block:
                    result = block["toolResult"]
                    text = " ".join(part.get("text", "") for part in result["content"])
                    pane.write(f"`[result: {result.get('status', 'success')}]` {text}\n\n")
        pane.stop("Completed")
        panes.append(pane.html())
    display(
        HTML(
            f'<div class="agent-conversations mathjax_ignore" style="{GRID_STYLE}">'
            f'{"".join(panes)}</div>'
        )
    )
