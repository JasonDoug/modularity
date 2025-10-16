# Claude Code - Modularity Project Workflows

## GitHub Feature Branch & PR Workflow with CodeRabbit Review

### Phase End Ceremony - Complete Workflow

At the end of each development phase, follow this complete ceremony:

#### Step 1: Create Feature Branch
```bash
git checkout -b feature/descriptive-name
```

#### Step 2: Stage and Commit Changes
```bash
# Check what's changed
git status
git diff

# Stage all changes
git add .

# Create descriptive commit
git commit -m "Add feature: descriptive message

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

#### Step 3: Push to Remote
```bash
git push -u origin feature/descriptive-name
```

#### Step 4: Create Pull Request
```bash
# Using gh CLI - recommended method
gh pr create --title "Feature: Descriptive Title" --body "## Summary
- Bullet point summary of changes

## Test plan
- How to test these changes

🤖 Generated with [Claude Code](https://claude.com/claude-code)"

# This returns the PR number and URL
```

### Retrieving CodeRabbit Inline Comments - CRITICAL PROCESS

**IMPORTANT**: CodeRabbit posts TWO types of comments:
1. **Review Summary** - The main review body with summary statistics
2. **Inline Comments** - 10+ actionable/nitpick comments on specific code lines

#### The Correct Method to Get Inline Comments

**Use the GitHub API endpoint** (this is the reliable method):

```bash
gh api /repos/OWNER/REPO/pulls/PR_NUMBER/comments
```

Example:
```bash
gh api /repos/JasonDoug/modularity/pulls/1/comments
```

This returns JSON array of inline comment objects with:
- `path`: File path
- `line`: Line number
- `body`: Comment text with severity markers
- `diff_hunk`: Code context

#### Parsing the Output

```bash
# Pretty print JSON
gh api /repos/OWNER/REPO/pulls/PR_NUMBER/comments | python3 -m json.tool

# Extract just comment bodies
gh api /repos/OWNER/REPO/pulls/PR_NUMBER/comments | python3 -m json.tool | grep '"body":'

# Save to file for analysis
gh api /repos/OWNER/REPO/pulls/PR_NUMBER/comments > coderabbit_comments.json
```

#### What DOESN'T Work

❌ `gh pr view PR_NUMBER --comments` - Only shows review summary, NOT inline comments
❌ `gh pr view PR_NUMBER --json reviews` - Only gets review body
❌ `gh pr view PR_NUMBER --json reviewThreads` - Field doesn't exist
❌ Reading the PR description - Contains summary stats but not the actual inline issues

### Identifying Actionable vs Nitpick Comments

CodeRabbit review structure:
- **Actionable comments posted: X** - Critical/Major/Minor issues requiring fixes
- **Nitpick comments: Y** - Style suggestions, optimizations (lower priority)

Inline comments are marked with severity:
- "Potential issue | Critical" → Security vulnerabilities, data loss risks
- "Potential issue | Major" → Bugs, missing validation, race conditions
- "Potential issue | Minor" → Style issues, unused variables

### Complete Example from modularity Project

```bash
# 1. Created feature branch
git checkout -b feature/core-implementations

# 2. Committed all changes
git add .
git commit -m "Add Python SDK implementation

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"

# 3. Pushed to remote
git push -u origin feature/core-implementations

# 4. Created PR
gh pr create --title "Add Core Python Implementations" --body "## Summary
- Complete Python SDK with ecosystem_sdk package
- Registry service with Flask-based API
- CLI tool (modularity command)

🤖 Generated with [Claude Code](https://claude.com/claude-code)"

# 5. Retrieved CodeRabbit inline comments
gh api /repos/JasonDoug/modularity/pulls/1/comments > review.json

# 6. Identified 10 actionable issues:
# - 2 CRITICAL (SSRF, CORS)
# - 6 MAJOR (validation, race conditions, etc)
# - 2 MINOR (unused vars, formatting)
```

### Key Lessons Learned

1. **Always use the API method** for inline comments - it's the only reliable way
2. **Don't confuse summary stats with actual comments** - "10 actionable comments posted" means there are 10 inline comments to retrieve via API
3. **Check both actionable AND nitpick** - Actionable are high priority, nitpick for later
4. **Parse JSON carefully** - Each comment has path, line, and body fields
5. **Look for severity markers** - "Critical", "Major", "Minor" indicate priority

### Workflow Integration

When user says "check the CodeRabbit comments":
1. Use `gh api /repos/OWNER/REPO/pulls/PR_NUMBER/comments` immediately
2. Parse the JSON to extract all inline comments
3. Categorize by severity (Critical → Major → Minor)
4. Present structured list with file:line references
5. Wait for user direction on which issues to fix first

---

## Project Structure

```
modularity/
├── packages/
│   ├── sdk-python/          # Python SDK for ecosystem
│   ├── registry/            # Service discovery registry
│   └── cli/                 # modularity CLI tool
```

## Development Notes

- All "ecosystem" references renamed to "modularity" in CLI
- Entry point: `modularity=modularity_cli.cli:cli`
- Registry runs on port 5000 by default
- SDK supports polymorphic service architecture (standalone/embedded/service modes)
