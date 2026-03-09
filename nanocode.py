#!/usr/bin/env python3
"""
    A lightweight CLI-based coding assistant for reading, editing, and automating tasks with LLMs
"""
import glob as globlib  # used for finding files and directories matching a pattern
import json             # for parsing and generating json data
import os               # providing operating system utilities
import re               # regular expressions for pattern matching in strings
import subprocess       # for running shell commands or external programs
import ollama

# ------ ANSI styles and colors ------
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
    pass

# run shell command
def bash(args):
    pass

# ------ tool definitions ------
TOOLS = {}


def main():
    model ="qwen3:8b"
    print(f"{BOLD}{CYAN}nanocode{RESET} | {BOLD}{YELLOW}Ollama::{model}{RESET} | {BOLD}{GREEN}{os.getcwd()}{RESET}\n")



if __name__ == "__main__":
    main()