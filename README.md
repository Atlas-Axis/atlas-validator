# validate-atlas

Atlas Markdown Validator - Standalone validator for Atlas Markdown files.

## Installation

```bash
npm install
```

## Usage

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

## Exit Codes

- `0` - No errors (warnings OK)
- `1` - Errors found
