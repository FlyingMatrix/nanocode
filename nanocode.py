#!/usr/bin/env python3
"""
    A lightweight CLI-based coding assistant for reading, editing, and automating tasks with LLMs
"""
import glob as globlib      # used for finding files and directories matching a pattern
import json                 # for parsing and generating json data
import os                   # providing operating system utilities
import re                   # regular expressions for pattern matching in strings
import subprocess           # for running shell commands or external programs
import ollama

# ------ ANSI styles and colors ------
from colorama import init   # for Windows / Anaconda
init()                      # enables ANSI support on Windows

RESET, BOLD, DIM = "\033[0m", "\033[1m", "\033[2m"
BLUE, CYAN, GREEN, YELLOW, RED = (
    "\033[34m",
    "\033[36m",
    "\033[32m",
    "\033[33m",
    "\033[31m",
)

# ------ tool function implementations ------
# read file with line numbers
def read(path, offset=0, limit=None):
    lines = open(path).readlines()

    if limit is None:
        limit = len(lines)

    selected_lines = lines[offset: offset + limit]

    read_lines = "".join(
        f"{offset + idx + 1:4}| {line}"
        for idx, line in enumerate(selected_lines)
    )

    return read_lines if read_lines else "(empty file)"

# write content to file
def write(path, content):
    with open(path, "w") as f:
        f.write(content)
    return "ok"

# replace string in file
def edit(path, old, new, all=False):
    with open(path) as f:
        text = f.read()

    if old not in text:
        return "error: old_string not found"

    count = text.count(old)

    if not all and count > 1:
        return f"error: old_string appears {count} times, must be unique (use all=true)"

    if all:
        replacement = text.replace(old, new)
    else:
        replacement = text.replace(old, new, 1)

    with open(path, "w") as f:
        f.write(replacement)

    return "ok"

# find files by pattern and sort from newest to oldest
def glob(pat, path=None):
    base = path or "."
    pattern = os.path.join(base, pat)

    files = globlib.glob(pattern, recursive=True)

    files = sorted(
        files,
        key=lambda f: os.path.getmtime(f) if os.path.isfile(f) else 0,
        reverse=True,
    )

    # convert to relative paths
    cwd = os.getcwd()
    rel_files = [os.path.relpath(f, cwd) for f in files]

    return "\n".join(rel_files) if rel_files else "(no matches)"

# search files for regular expression
def grep(pat, path="."):
    pattern = re.compile(pat)
    hits = []

    for filepath in globlib.glob(os.path.join(path, "**"), recursive=True):
        if not os.path.isfile(filepath):
            continue

        try:
            with open(filepath, errors="ignore") as f:
                for line_num, line in enumerate(f, 1):
                    if pattern.search(line):
                        hits.append(f"{filepath}:{line_num}:{line.rstrip()}")
                        if len(hits) >= 50:
                            return "\n".join(hits)
        except Exception:
            pass

    return "\n".join(hits) if hits else "(no matches)"

# run shell command
def bash(cmd):
    proc = subprocess.Popen(
        cmd,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )

    output_lines = []

    try:
        while True:
            line = proc.stdout.readline()
            if not line and proc.poll() is not None:
                break
            if line:
                print(f" {DIM}| {line.rstrip()}{RESET}", flush=True)
                output_lines.append(line)

        proc.wait(timeout=30)

    except subprocess.TimeoutExpired:
        proc.kill()
        output_lines.append("\n(timed out after 30s)")

    return "".join(output_lines).strip() or "(empty)"

# ------ tool definitions ------
"""
    TOOLS is a registry of tools with metadata and the actual callable function with a sturcture as below:

        TOOLS = {
            "tool_name": (description, parameters, function),
            ...
        }

        - each key is a tool name
        - each value is a tuple containing:
            > description (string)
            > mandatory and optional parameters
            > actual callable function
"""
TOOLS = {
    "read": (
        "Read file with line numbers (file path, not directory)",
        {"path": "string", "offset": "number?", "limit": "number?"},
        read,
    ),
    "write": (
        "Write content to file",
        {"path": "string", "content": "string"},
        write,
    ),
    "edit": (
        "Replace old with new in file (old must be unique unless all=true)",
        {"path": "string", "old": "string", "new": "string", "all": "boolean?"},
        edit,
    ),
    "glob": (
        "Find files by pattern, sorted by last modified time",
        {"pat": "string", "path": "string?"},
        glob,
    ),
    "grep": (
        "Search files for regular expression pattern",
        {"pat": "string", "path": "string?"},
        grep,
    ),
    "bash": (
        "Run shell command",
        {"cmd": "string"},
        bash,
    ),
}

def run_tool(name, args):
    try:
        func = TOOLS[name][2]
        result = func(**args)

        if result is None:
            return "(no output)"

        return str(result)
    except Exception as err:
        return f"error: {err}"
    
def make_schema(): 
    result = []

    for name, (description, params, function) in TOOLS.items():
        properties = {}
        required = []

        for param_name, param_type in params.items():
            is_optional = param_type.endswith("?")
            base_type = param_type.rstrip("?")

            properties[param_name] = {
                "type": base_type 
            }

            if not is_optional:
                required.append(param_name)

        result.append({
            "type": "function",  
            "function": {
                "name": name,
                "description": description,
                "parameters": {  
                    "type": "object",
                    "properties": properties,
                    "required": required,
                },
            },
        })

    return result 

def call_model(model, messages, system_prompt):
    response = ollama.chat(
        model= model,
        messages=(
            [{"role": "system", "content": system_prompt}] if system_prompt else []
        ) + messages,
        tools=make_schema(),
        options={
            "num_predict": 8192
        }
    )
    # update messages
    content = response["message"]["content"]
    messages.append({
        "role": "assistant",
        "content": content
    })
    return response
    """
    Typical ollama.chat() response (non-streaming, may vary by version/config):
    {
        "model": "model-name",
        "created_at": "...",
        "message": {
            "role": "assistant",
            "content": "...",
            # Optional, only if tools are used:
            "tool_calls": [
                {
                    "id": "...",
                    "type": "function",
                    "function": {
                        "name": "...",
                        "arguments": {...}  # sometimes a JSON string
                    }
                }
            ]
        },
        "done": true,
        "done_reason": "stop",
        # Optional timing/debug fields:
        "total_duration": ...,
        "load_duration": ...,
        "prompt_eval_count": ...,
        "eval_count": ...
    }
    """

def separator():
    return f"{DIM}{'─' * min(os.get_terminal_size().columns, 80)}{RESET}"

def render_markdown(text):  # convert markdown-style bold text (**text**) into terminal bold formatting using ANSI escape codes
    return re.sub(r"\*\*(.+?)\*\*", f"{BOLD}\\1{RESET}", text)

def main():
    model ="qwen3:8b"
    print(f"{BOLD}{CYAN}nanocode{RESET} | {BOLD}{YELLOW}Ollama::{model}{RESET} | {BOLD}{GREEN}{os.path.relpath(os.getcwd())}{RESET}\n")
    messages = []
    try:
        cwd = os.getcwd()
    except Exception as e:
        cwd = "<unknown directory>"
        print(f"Warning: failed to get cwd: {e}")

    # system_prompt = f"Concise coding assistant. cwd: {cwd}"
    system_prompt = f"""
        You are an autonomous coding agent working inside a local repository.

        Context:
        - Current working directory: {cwd}

        Your goals:
        - Help the user understand, analyze, and modify the repository using available tools.

        Available tools:
        - glob: discover files and directory structure
        - read: read file contents
        - grep: search across files using patterns
        - edit: modify existing files
        - write: create or overwrite files
        - bash: execute shell commands

        Behavior rules:
        1. Use tools to explore the repository before answering when needed.
        2. Prefer reading source code over relying only on README or assumptions.
        3. For exploratory questions (e.g., "what does this repo do"), inspect multiple relevant files.
        4. Think step-by-step and make multiple tool calls if necessary.
        5. Avoid repeating identical tool calls with the same arguments.
        6. Stop using tools once you have enough information.

        Strategy:
        - Use glob to find relevant files (e.g., *.py)
        - Use read to inspect important files
        - Use grep to search for key functions or patterns

        Output rules:
        - If more information is needed, call tools.
        - If sufficient information is gathered, provide a clear and concise final answer.
        - Be concise but thorough.
        """

    while True:
        try:
            print(separator())
            user_input = input(f"{BOLD}{BLUE}❯❯{RESET} ").strip()
            print(separator())
            if not user_input:
                continue
            if user_input in ("/q", "exit"):
                break
            if user_input == "/c":
                messages = []
                print(f"{GREEN}❯❯ Cleared conversation{RESET}")
                continue
            
            messages.append({"role": "user", "content": user_input})

            # agentic loop
            while True:
                response = call_model(model, messages, system_prompt)
                message_block = response.get("message", {})

                # print assistant message
                if message_block.get("content"):
                    print(f"\n{CYAN}❯❯ {RESET}{render_markdown(message_block['content'])}")

                # append assistant message ONCE
                messages.append({
                    "role": "assistant",
                    "content": message_block.get("content", "")
                })

                # handle tool calls
                tool_calls = message_block.get("tool_calls")
                if not tool_calls:
                    break  

                for tool in tool_calls:
                    tool_name = tool["function"]["name"]
                    tool_args = tool["function"]["arguments"]

                    arg_preview = str(list(tool_args.values())[0])[:50] if tool_args else ""
                    print(f"\n{GREEN}❯❯ {tool_name.capitalize()}{RESET}({DIM}{arg_preview}{RESET})")

                    result = run_tool(tool_name, tool_args)
                    print(f"{GREEN}❯❯ {RESET}{DIM}{result}{RESET}")

                    messages.append({
                        "role": "tool",
                        "name": tool_name,
                        "content": str(result)
                    })

            print() # print out a blank line in the console

        except (KeyboardInterrupt, EOFError):
            break
        except Exception as err:
            print(f"{RED}❯❯ Error: {err}{RESET}") 


if __name__ == "__main__":
    main()
