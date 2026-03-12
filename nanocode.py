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
def read(args):
    lines = open(args["path"]).readlines()
    offset = args.get("offset", 0)
    limit = args.get("limit", len(lines))
    selected_lines = lines[offset: offset+limit]
    read_lines = "".join(f"{offset+idx+1:4}| {line}" for idx, line in enumerate(selected_lines))
    return read_lines

# write content to file
def write(args):
    with open(args["path"], "w") as f:
        f.write(args["content"])
    return "ok"

# replace string in file
def edit(args):
    text = open(args["path"]).read()
    old, new = args["old"], args["new"]
    if old not in text:
        return "error: old_string not found"
    count = text.count(old)
    if not args.get("all") and count > 1:
        return f"error: old_string appears {count} times, must be unique (use all=true)"
    replacement = text.replace(old, new) if args.get("all") else text.replace(old, new, 1)
    with open(args["path"], "w") as f:
        f.write(replacement)
    return "ok"

# find files by pattern and sort from newest to oldest
def glob(args):
    pattern = (args.get("path", ".") + "/" + args["pat"]).replace("//", "/")
    files = globlib.glob(pattern, recursive=True)
    files = sorted(
        files,
        key=lambda f: os.path.getmtime(f) if os.path.isfile(f) else 0,
        reverse=True,   # newest files first
    )                   # files is a list of files sorted from newest to oldest
    return "\n".join(files) or "none"

# search files for regular expression
def grep(args):
    pattern = re.compile(args["pat"])
    hits = []
    for filepath in globlib.glob(args.get("path", ".") + "/**", recursive=True):    # list of file paths to search
        try:
            for line_num, line in enumerate(open(filepath), 1):
                 if pattern.search(line):                                           # check if the line matches the regular expression
                     hits.append(f"{filepath}:{line_num}:{line.rstrip()}")
        except Exception:
            pass
    return "\n".join(hits[:50]) or "none"

# run shell command
def bash(args):
    proc = subprocess.Popen(        # start a new subprocess
        args=args["cmd"],           # command to run
        shell=True,                 # run command through shell
        stdout=subprocess.PIPE,     # send the output of command into a pipe that Python can read
        stderr=subprocess.STDOUT,   # merge stderr into stdout
        text=True                   # output is returned as strings instead of bytes
    )
    output_lines = [] 
    try:
        while True:
            line = proc.stdout.readline()               # read one line of output from the command as it runs
            if not line and proc.poll() is not None:    # if no line was read and the process has finished -> exit the loop
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
        return TOOLS[name][2](args)
    except Exception as err:
        return f"error: {err}"
    
def make_schema():  # convert a simple internal TOOLS dictionary into a JSON schema specification for tool inputs
    result = []
    for name, (description, params, function) in TOOLS.items():
        properties = {}
        required = []
        for param_name, param_type in params.items():
            is_optional = param_type.endswith("?")
            base_type = param_type.rstrip("?")
            properties[param_name] = {
                "type": "integer" if base_type == "number" else base_type
            }
            if not is_optional:
                required.append(param_name)
    result.append(
            {
                "name": name,
                "description": description,
                "input_schema": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                },
            }
        )
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
    return response     # here, response is a dict

def separator():
    return f"{DIM}{'─' * min(os.get_terminal_size().columns, 80)}{RESET}"

def render_markdown(text):  # convert markdown-style bold text (**text**) into terminal bold formatting using ANSI escape codes
    return re.sub(r"\*\*(.+?)\*\*", f"{BOLD}\\1{RESET}", text)

def main():
    model ="qwen3:8b"
    print(f"{BOLD}{CYAN}nanocode{RESET} | {BOLD}{YELLOW}Ollama::{model}{RESET} | {BOLD}{GREEN}{os.getcwd()}{RESET}\n")
    messages = []
    try:
        cwd = os.getcwd()
    except Exception as e:
        cwd = "<unknown directory>"
        print(f"Warning: failed to get cwd: {e}")
    system_prompt = f"Concise coding assistant. cwd: {cwd}"

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



        except (KeyboardInterrupt, EOFError):
            break
        except Exception as err:
            print(f"{RED}❯❯ Error: {err}{RESET}") 

if __name__ == "__main__":
    main()
