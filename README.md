# Sky Atlas Validator

[![CI](https://github.com/Atlas-Axis/atlas-validator/actions/workflows/ci.yml/badge.svg)](https://github.com/Atlas-Axis/atlas-validator/actions/workflows/ci.yml)

Atlas Markdown Validator - Comprehensive validator for Atlas Markdown files with support for both CLI and GitHub Actions.

## Features

- ✅ **Complete Validation**: 8 comprehensive validation checks
- 🔄 **GitHub Actions Integration**: Use as a reusable action in your workflows
- 📍 **Inline Annotations**: Errors appear directly on PR files in GitHub
- 🎯 **Detailed Reports**: Clear error messages with examples and action steps
- 🚀 **Fast Execution**: Runs directly on Node.js (no Docker overhead)

## Validations Performed

1. **Title Line Format** - Validates exact pattern: `# {DocNo} - {Name} [{Type}]  <!-- UUID: {uuid} -->`
2. **Document Types** - Ensures document type is one of the 12 valid Atlas document types
3. **Heading Hierarchy** - Checks sequential heading levels (no skipping from # to ###)
4. **Blank Lines** - Validates required blank lines after titles and around extra fields
5. **Extra Fields** - Validates format, order, and presence of required fields (for Type Specification, Scenario, Scenario Variation documents)
6. **Document Numbering** - Validates patterns for all 12 document types (e.g., A.1, NR-1, .0.3.1)
7. **Nesting Rules** - Ensures valid parent-child type combinations
8. **UUID Validation** - Checks format (UUID v4), uniqueness, and warns about empty UUIDs

## Usage as GitHub Action

> **📢 Note:** If you're upgrading from an older version that used `pull_request`, see the [Migration Guide](#migration-guide) below.

### Basic Usage

Add this to your workflow file (e.g., `.github/workflows/validate.yml`):

```yaml
name: Validate Atlas on Pull Request

on:
  pull_request_target:
    paths:
      - "**.md"

jobs:
  validate:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      pull-requests: write # Required for posting comments

    steps:
      # Security: This checks out PR code but only reads markdown for validation
      # No code execution, build steps, or package installs are performed
      - name: Checkout PR code
        uses: actions/checkout@v4
        with:
          ref: ${{ github.event.pull_request.head.sha }}

      - name: Validate Atlas Markdown
        id: validate
        uses: Atlas-Axis/atlas-validator@main
        with:
          file_path: atlas.md  # or "Sky Atlas/Sky Atlas.md" for custom paths
        continue-on-error: true

      - name: Comment on PR
        if: steps.validate.outputs.has_errors == 'true'
        uses: actions/github-script@v7
        with:
          script: |
            const fs = require('fs');

            // Read the validation summary file
            let summary = '';
            try {
              summary = fs.readFileSync('validation-summary.md', 'utf8');
            } catch (error) {
              summary = '## ⚠️ Validation Summary Not Available\n\nUnable to read validation results.';
            }

            // Post comment with validation errors
            await github.rest.issues.createComment({
              owner: context.repo.owner,
              repo: context.repo.repo,
              issue_number: context.issue.number,
              body: summary
            });

      - name: Fail if validation errors
        if: steps.validate.outputs.has_errors == 'true'
        run: exit 1
```

**✅ This workflow works for both:**
- PRs from branches in the same repository
- PRs from external forks

### **🔒 Security Note:**

This workflow uses `pull_request_target` which runs with elevated permissions. GitHub's security tools may flag this pattern as potentially dangerous. However, **this is safe for validation workflows** because:

✅ **What makes this safe:**
- The validator only performs **static analysis** on markdown files (no code execution)
- The validator action code comes from a **trusted source** (`Atlas-Axis/atlas-validator@main`), not from the PR
- Markdown files are treated as **data only** - they are never executed or interpreted as code
- The workflow does not run `npm install`, build scripts, or execute any code from the PR
- File operations are read-only and limited to the specified markdown file

⚠️ **This pattern would be dangerous if:**
- Running `npm install`, `pip install`, or similar (executes package scripts from PR)
- Building or executing code from the PR
- Running tests that execute untrusted code
- Using dynamic `eval()` or imports on PR content

**Why we need `pull_request_target`:**
- Required for PR comments on external forks (has write permissions)
- The workflow file itself runs from the trusted base branch
- Only the markdown content (data) comes from the PR

### Inputs

| Input | Description | Required |
|-------|-------------|----------|
| `file_path` | Path to the Atlas Markdown file to validate | Yes |

### Outputs

| Output | Description |
|--------|-------------|
| `has_errors` | Whether validation found errors (`true`/`false`) |

### Annotation Features

When running in GitHub Actions, validation errors and warnings appear as **inline annotations** directly on your files in the Pull Request "Files Changed" view. This makes it easy to:

- See exactly where issues are in your document
- Click through to the specific line with the problem
- Review and fix issues without switching contexts

## Migration Guide

### Upgrading from `pull_request` to `pull_request_target`

If you're currently using this action with the `pull_request` trigger and experiencing issues with PRs from external forks, update your workflow:

**⚠️ BOTH changes below are REQUIRED - doing only one will not work!**

#### Change 1: Update the trigger

```yaml
# Before
on:
  pull_request:

# After
on:
  pull_request_target:
```

#### Change 2: Update the checkout step (CRITICAL!)

```yaml
# Before
- name: Checkout code
  uses: actions/checkout@v4

# After
- name: Checkout PR code
  uses: actions/checkout@v4
  with:
    ref: ${{ github.event.pull_request.head.sha }}  # ← DO NOT SKIP THIS!
```

**🚨 Why both changes are required:**
- **Only changing to `pull_request_target`** → Will validate the base branch (main) instead of the PR, so validation always passes ❌
- **Only adding the ref parameter** → Won't fix the permissions issue for external forks ❌  
- **Both changes together** → Validates the PR code AND works with external forks ✅

**📝 Deployment Note:** 

`pull_request_target` runs the workflow file from the **base branch**, not from the PR branch. This means:
- You must **merge the workflow changes to your base branch first**
- Then subsequent PRs will use the updated workflow
- If you update the workflow in a PR, that PR won't use the new workflow (future PRs will)

## Troubleshooting

### Validation Always Passes (Even When It Shouldn't)

**Symptoms:** After changing to `pull_request_target`, the validation passes even though you know there are errors in the PR.

**Cause:** You changed the trigger to `pull_request_target` but **forgot to update the checkout step**. Without the `ref` parameter, checkout defaults to the base branch, so it's validating the base branch code instead of the PR code.

**Solution:** Add the `ref` parameter to your checkout step:

```yaml
- name: Checkout PR code
  uses: actions/checkout@v4
  with:
    ref: ${{ github.event.pull_request.head.sha }}  # ← Add this line!
```

**Verify it's working:** Check the GitHub Actions logs. If it's working correctly, you should see validation errors. If it says "✅ Validation passed - no issues found" but you know there are errors, the checkout step is wrong.

### Workflow Doesn't Run After Changing to `pull_request_target`

**Symptoms:** After updating your workflow to use `pull_request_target`, the checks don't run on the PR where you made the change.

**Cause:** `pull_request_target` always uses the workflow file from the **base branch** (e.g., `main`), not from the PR branch. This is a security feature.

**Solution:** 
1. Merge the workflow changes to your base branch first
2. Future PRs will then use the updated workflow with `pull_request_target`
3. Alternatively, push the workflow changes directly to the base branch to test immediately

### Error: "Resource not accessible by integration" (403)

**Symptoms:** The workflow fails with a 403 error when trying to post a comment on the PR.

**Cause:** This happens when PRs come from external forks. By default, workflows triggered by `pull_request` from forks have read-only permissions for security reasons.

**Solution:** Make sure your workflow uses `pull_request_target` (as shown above) instead of `pull_request`. The key differences:

```yaml
# ❌ Won't work for external forks
on:
  pull_request:

# ✅ Works for both internal branches and external forks
on:
  pull_request_target:
```

And ensure you check out the PR's code explicitly:

```yaml
# ✅ Required for pull_request_target
- uses: actions/checkout@v4
  with:
    ref: ${{ github.event.pull_request.head.sha }}
```

### Validation Runs But Doesn't Comment

**Possible causes:**
1. The workflow doesn't have `pull-requests: write` permission - add it under `permissions:` in your workflow
2. The repository has restricted workflow permissions - go to **Settings → Actions → General → Workflow permissions** and ensure "Read and write permissions" is enabled
3. Using `pull_request` trigger with PRs from forks - switch to `pull_request_target` (see workflow above)

## Local CLI Usage

### Installation

```bash
npm install
```

### Running the Validator

```bash
npm run validate path/to/atlas.md
```

Or run directly with tsx:

```bash
npx tsx validate-atlas-markdown.ts path/to/atlas.md
```

Or make it executable:

```bash
chmod +x validate-atlas-markdown.ts
./validate-atlas-markdown.ts path/to/atlas.md
```

### Exit Codes

- `0` - No errors (warnings OK)
- `1` - Errors found

## Development

### Prerequisites

- Node.js 22
- npm

### Setup

```bash
git clone https://github.com/Atlas-Axis/atlas-validator.git
cd validate-atlas
npm install
```

### Testing

```bash
# Test the validator on a file
npx tsx validate-atlas-markdown.ts path/to/test.md

# Check TypeScript compilation
npx tsc --noEmit
```

## Author

Atlas Axis
