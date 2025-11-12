# Sky Atlas Validator

[![CI](https://github.com/pppdns/validate-atlas/actions/workflows/ci.yml/badge.svg)](https://github.com/pppdns/validate-atlas/actions/workflows/ci.yml)

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

### Basic Usage

Add this to your workflow file (e.g., `.github/workflows/validate.yml`):

```yaml
name: Validate Atlas Documentation

on:
  push:
    branches:
      - main
  pull_request:
    branches:
      - main

jobs:
  validate:
    runs-on: ubuntu-latest
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
      
      - name: Validate Atlas Markdown
        uses: pppdns/validate-atlas@v1  # or use @main for latest
        with:
          file_path: docs/atlas.md
```

### Pull Request Validation with Comments

```yaml
name: Validate Atlas on Pull Request

on:
  pull_request:
    paths:
      - '**.md'

jobs:
  validate:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      pull-requests: write # Required for posting comments
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
      
      - name: Validate Atlas Markdown
        id: validate
        uses: pppdns/validate-atlas@main
        with:
          file_path: atlas.md
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

- Node.js 22 or higher
- npm

### Setup

```bash
git clone https://github.com/pppdns/validate-atlas.git
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

## Examples

See the [`.github/examples/`](.github/examples/) directory for complete workflow examples:

- [`basic-usage.yml`](.github/examples/basic-usage.yml) - Simple validation workflow
- [`pull-request.yml`](.github/examples/pull-request.yml) - PR validation with comments

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

ISC

## Author

Atlas Axis
