# Sky Atlas Validator

[![CI](https://github.com/Atlas-Axis/atlas-validator/actions/workflows/ci.yml/badge.svg)](https://github.com/Atlas-Axis/atlas-validator/actions/workflows/ci.yml)

Atlas Markdown Validator - Comprehensive validator for Atlas Markdown files with support for both CLI and GitHub Actions.

## Features

- ✅ **Complete Validation**: 8 comprehensive validation checks
- 🔄 **GitHub Actions Integration**: Use as a reusable action in your workflows
- 📍 **Inline Annotations**: Errors appear directly on PR files in GitHub
- 🎯 **Detailed Reports**: Clear error messages with examples and action steps

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

### Basic Usage

Add this to your workflow file (e.g., `.github/workflows/validate.yml`):

```yaml
name: Validate Atlas on Pull Request

on:
  pull_request:

jobs:
  validate:
    runs-on: ubuntu-latest
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Validate Atlas Markdown
        uses: Atlas-Axis/atlas-validator@main
        with:
          file_path: atlas.md  # or "Sky Atlas/Sky Atlas.md" for custom paths
```



### Understanding Validation Results

When the validator runs, results appear in three places:

#### 1. Check Status (Pass/Fail)
The GitHub check will show a ✅ (passed) or ❌ (failed) status next to your PR. A failed check will block the PR merge if you have required checks enabled.

#### 2. Inline Annotations
Validation errors appear as **inline annotations** directly on the affected lines in the "Files Changed" tab:
- Click on the "Files Changed" tab in your PR
- Look for red error markers on specific lines
- Click the markers to see detailed error messages with examples and fixes

#### 3. Job Summary
Click on the failed check to see a detailed report:
- Click "Details" next to the validator check
- Scroll down to see the full validation report
- The summary includes all errors with line numbers, examples, and suggested fixes

**Note:** The validator does not post PR comments. All validation feedback is provided through GitHub's native annotations and job summary features, which work reliably for all PRs including those from external forks.

### Inputs

| Input | Description | Required |
|-------|-------------|----------|
| `file_path` | Path to the Atlas Markdown file to validate | Yes |

### Outputs

| Output | Description |
|--------|-------------|
| `has_errors` | Whether validation found errors (`true`/`false`) |

## Troubleshooting

### Validation Errors Don't Appear

**Symptoms:** The check passes/fails but you don't see error details.

**Solution:** 
1. Click on "Details" next to the failed check to see the Job Summary with all errors
2. Go to "Files Changed" tab to see inline annotations on specific lines
3. Ensure you're using the latest version of the action: `@main` or a specific version tag

### Check Doesn't Run on PR

**Symptoms:** The validator doesn't run when you create a PR.

**Possible causes:**
1. The workflow file path filter doesn't match your file - check `paths:` in your workflow
2. The workflow file hasn't been merged to the base branch yet - merge it first
3. The repository has disabled GitHub Actions - check Settings → Actions

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
