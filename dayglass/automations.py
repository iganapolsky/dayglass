"""Local deterministic automations for Dayglass.

Replaces Screenpipe's runaway cloud pipes with on-demand or scheduled
local models (LM Studio on 127.0.0.1:1235 / :1234).
Cost: $0.00 / month forever. Zero token caps.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from dayglass.ask import complete
from dayglass.store import connect, insert_automation_run, recent_text, today_text

PROMPTS = {
    "day-recap": (
        "Analyze today's screen notes and provide a structured daily recap:\n"
        "1. Accomplishments (what got done)\n"
        "2. Key Workstreams & Active Projects\n"
        "3. Unfinished Work & Pending Tasks\n"
        "Keep the tone direct, factual, and concise."
    ),
    "automate-my-work": (
        "Review recent screen activity and identify any repetitive tasks, "
        "manual copy-pastes, recurring navigation steps, or multi-step manual workflows. "
        "Propose ONE concrete, testable local automation (e.g. bash script, Raycast extension, "
        "or shortcut) that saves time. Include the exact script/command if possible."
    ),
    "standup-prep": (
        "Based on recent screen history, generate a crisp 3-part engineering standup report:\n"
        "• Yesterday / Past work: key features, commits, PRs, or docs touched\n"
        "• Today: current work in progress and immediate next steps\n"
        "• Blockers / Risks: any errors, awaiting reviews, or environment issues\n"
        "Format as clean bullet points ready to copy-paste into Slack/Teams."
    ),
    "missed-todos": (
        "Scan recent screen activity (chat messages, emails, PR comments, terminal outputs, docs) "
        "for unfulfilled promises, action items, or things the user said they would do "
        "(e.g., 'I will check', 'TODO', 'follow up', 'send over'). "
        "List each missed or pending to-do with surrounding context."
    ),
    "blockers": (
        "Identify any blockers, runtime errors, test failures, compiler errors, or access issues "
        "visible in recent screen activity. Provide: "
        "1. What failed\n"
        "2. Probable root cause\n"
        "3. Recommended next action to unblock."
    ),
    "time-breakdown": (
        "Analyze today's screen activity timestamps and context to estimate how time was spent: "
        "group by category (Coding/IDE, Communication/Slack/Teams, Browser/Research, Admin/Meetings). "
        "Provide approximate percentage or time allocations and main focus areas."
    ),
    "meeting-prep": (
        "Extract context from recent screen notes and meetings for upcoming discussions. "
        "Summarize: "
        "1. Key context and decisions from recent interactions\n"
        "2. Open questions that need resolution\n"
        "3. Recommended talking points."
    ),
}


def run_automation(name: str, conn: sqlite3.Connection | None = None) -> tuple[str, str]:
    """Runs a named automation locally using LM Studio."""
    if name not in PROMPTS:
        available = ", ".join(PROMPTS.keys())
        raise ValueError(f"Unknown automation '{name}'. Available: {available}")

    if conn is None:
        conn = connect()

    # Get context: today's text if day-recap or standup-prep, else recent text
    if name in ("day-recap", "standup-prep", "time-breakdown"):
        context = today_text(conn)
        if not context.strip():
            context = recent_text(conn, limit=16)
    else:
        context = recent_text(conn, limit=16)

    if not context.strip():
        msg = "No screen notes recorded yet. Run: python3 -m dayglass capture"
        return name, msg

    instruction = PROMPTS[name]
    prompt = (
        f"{instruction}\n\n"
        f"--- SCREEN & ACTIVITY CONTEXT ---\n"
        f"{context[:24000]}\n"
        f"---------------------------------\n\n"
        f"Provide your answer below:"
    )

    answer = complete(prompt)
    insert_automation_run(conn, name, answer)
    return name, answer
