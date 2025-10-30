# Language & Code Style

## Language Guidelines

- **Always write code in English** - variable names, function names, class names
- **Always write comments in English** - regardless of user's input language
- **Exception**: Only use another language (e.g., Chinese) when user explicitly requests it

## Comment Guidelines

- **Minimize comments** - keep them to absolute minimum
- **Write self-explanatory code** - good naming is better than comments
- **Only comment when necessary**:
  - Complex algorithms or non-obvious logic
  - Important design decisions or trade-offs
  - Workarounds for bugs or limitations
- **Avoid redundant comments** - don't describe what code obviously does

## Examples

**Good** (self-explanatory):
```python
def calculate_total_price(items, tax_rate):
    subtotal = sum(item.price for item in items)
    return subtotal * (1 + tax_rate)
```

**Bad** (over-commented):
```python
# Calculate total price
def calc_price(items, rate):
    # Sum all item prices
    subtotal = sum(item.price for item in items)
    # Add tax
    return subtotal * (1 + rate)
```


# Claude Documentation Management

## Claude Documentation Location

- **Never put documentation in code directories** directly
- **Always place documentation in `claude/` directory**
- Keep code and documentation separate for better organization

## Creating Documentation

When a task is completed and documentation is needed:

- Create files in `claude/` directory
- Examples:
  - `claude/api-design.md` - API design decisions
  - `claude/setup-guide.md` - Setup instructions
  - `claude/architecture.md` - System architecture
  - `claude/troubleshooting.md` - Common issues and solutions

## README.md Guidelines
- **Minimal changes only** - except when creating it for the first time
- **Keep README concise** - basic project info, quick start, and links
- **Avoid large content additions** - put detailed docs in `claude/` instead

## Finding Documentation

- **Check `claude/` first** when you need to understand something
- Look for relevant `.md` files before asking questions
- Update existing docs rather than creating duplicates

## Example Structure

```
project/
├── src/
├── tests/
├── claude/
│   ├── api-design.md
│   ├── setup-guide.md
│   └── architecture.md
└── README.md
```


# Git Version Control Guidelines

## Commit Workflow (Required)

- **Always create a commit** after completing each change
- **Never use `git add .`** - only stage files related to the current change
- **Always check first** with `git status` before committing

## Standard Process

1. `git status` - Review modified files
2. `git diff` - Check what changed
3. `git add <file1> <file2>` - Stage only relevant files
4. `git commit -m "clear message"` - Commit with descriptive message

## Bug Fixing Exception
- **During interactive bug fixing** - ask for confirmation before committing
- Don't commit after each attempted fix
- Only commit once the bug is **confirmed fixed** by user
- This avoids cluttering history with incomplete fix attempts

## Best Practices

- One logical change per commit
- Write clear, concise commit messages
- Commit frequently with focused changes

## Example

```bash
git status
git diff
git add src/main.py tests/test_main.py
git commit -m "Add user authentication feature"
```

# Temporary Files Management

## Location

- **Always place temporary files in `./temp/` directory**
- Never scatter temp files throughout the project

## What Goes in temp/

- Intermediate process files
- Temporary test scripts
- Result/output files
- Debug files
- Scratch/experimental code
- Any file not meant for production

## Git Rules

- **Never commit temp files to Git**
- Ensure `temp/` is in `.gitignore`
- Add `/temp/` to `.gitignore` if not already present

## Organization

- Keep temp directory organized with subdirectories if needed
- Clean up old temp files periodically

## Example Structure

```
project/
├── src/
├── tests/
├── temp/
│   ├── test_output.json
│   ├── debug_script.py
│   ├── intermediate_results.csv
│   └── experiments/
└── .gitignore  (includes temp/)
```


# Python Package Management with uv

Use uv exclusively for Python package management in this project.

## Package Management Commands

- All Python dependencies **must be installed, synchronized, and locked** using uv
- Never use pip, pip-tools, poetry, or conda directly for dependency management

Use these commands:

- Install dependencies: `uv add <package>`
- Remove dependencies: `uv remove <package>`
- Sync dependencies: `uv sync`

## Running Python Code

- Run a Python script with `uv run <script-name>.py`
- Run Python tools like Pytest with `uv run pytest` or `uv run ruff`
- Launch a Python repl with `uv run python`

## Managing Scripts with PEP 723 Inline Metadata

- Run a Python script with inline metadata (dependencies defined at the top of the file) with: `uv run script.py`
- You can add or remove dependencies manually from the `dependencies =` section at the top of the script, or
- Or using uv CLI:
    - `uv add package-name --script script.py`
    - `uv remove package-name --script script.py`
