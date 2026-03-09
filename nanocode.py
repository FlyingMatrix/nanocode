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
    pass

# find files by pattern
def glob(args):
    pass

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