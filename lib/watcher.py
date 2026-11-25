import glob
import json
import os
import time
from pathlib import Path
from typing import Dict, Optional, Set
from .notifier import Notifier
from .config import load_config


class TranscriptWatcher:
    """
    Watches active Antigravity conversation transcripts for:
    - User input requests (ask_question)
    - Permission prompts
    - Task completions
    """

    def __init__(self, base_brain_dir: Optional[str] = None):
        self.config = load_config()
        self.notifier = Notifier(self.config)
        self.base_dir = Path(base_brain_dir) if base_brain_dir else Path.home() / ".gemini" / "antigravity" / "brain"
        self.file_offsets: Dict[str, int] = {}
        self.notified_steps: Set[str] = set()

    def find_transcripts(self):
        """Find active transcript.jsonl files sorted by most recently modified."""
        pattern = str(self.base_dir / "*" / ".system_generated" / "logs" / "transcript.jsonl")
        files = glob.glob(pattern)
        pattern2 = str(self.base_dir / "*" / "transcript.jsonl")
        files.extend(glob.glob(pattern2))
        return sorted(files, key=lambda f: os.path.getmtime(f), reverse=True)

    def process_line(self, line: str, file_path: str):
        """Parse a transcript line and trigger notifications if needed."""
        try:
            record = json.loads(line)
        except Exception:
            return

        step_idx = record.get("step_index", 0)
        source = record.get("source", "")
        status = record.get("status", "")
        step_key = f"{file_path}:{step_idx}:{status}"

        if step_key in self.notified_steps:
            return

        tool_calls = record.get("tool_calls", [])
        if tool_calls:
            for tc in tool_calls:
                name = tc.get("name", "")
                args = tc.get("args", {})
                if name == "ask_question":
                    questions = args.get("questions", [])
                    q_text = ""
                    if isinstance(questions, list) and questions:
                        first = questions[0]
                        q_text = first.get("question", "") if isinstance(first, dict) else str(first)
                    self.notifier.notify_input_needed(question=q_text)
                    self.notified_steps.add(step_key)
                    return
                elif name == "run_command":
                    bypass = args.get("BypassSandbox", False)
                    if bypass or self.config.get("notify_on_all_commands", False):
                        summary = args.get("toolSummary", "") or args.get("CommandLine", "")[:50]
                        self.notifier.notify_permission_required(tool_name="run_command", detail=summary)
                        self.notified_steps.add(step_key)
                        return

        if source == "MODEL" and status == "DONE" and not tool_calls:
            content = record.get("content", "")
            if content and len(content.strip()) > 10:
                self.notifier.notify_task_completed(summary="Agent completed response.")
                self.notified_steps.add(step_key)

    def watch_loop(self, poll_interval: float = 1.0):
        """Main watching loop."""
        print(f"Monitoring Antigravity brain transcripts in: {self.base_dir}")
        print("Press Ctrl+C to terminate.")

        while True:
            try:
                active_files = self.find_transcripts()
                for fpath in active_files[:3]:
                    current_size = os.path.getsize(fpath)
                    last_offset = self.file_offsets.get(fpath, current_size)

                    if current_size > last_offset:
                        with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                            f.seek(last_offset)
                            for line in f:
                                line = line.strip()
                                if line:
                                    self.process_line(line, fpath)
                            self.file_offsets[fpath] = f.tell()
                    elif current_size < last_offset:
                        self.file_offsets[fpath] = 0

                time.sleep(poll_interval)
            except KeyboardInterrupt:
                print("\nMonitoring stopped.")
                break
            except Exception:
                time.sleep(poll_interval)
