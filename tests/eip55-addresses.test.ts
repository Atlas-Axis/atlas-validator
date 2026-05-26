import assert from 'node:assert/strict';
import { validate } from '../validate-atlas-markdown';

function atlasDocument(body: string): string {
  return `# A.1 - Example [Scope]  <!-- UUID: 8650a584-01f8-45d6-882b-c14eab9879c4 -->\n\n${body}\n`;
}

const checksummedAddress = '0x52908400098527886E0F7030069857D2E4169EE7';
const lowercaseAddress = checksummedAddress.toLowerCase();

const validIssues = validate(atlasDocument(`ForeignController: ${checksummedAddress}`));
assert.equal(
  validIssues.some((issue) => issue.message.includes('EIP-55')),
  false,
  'checksummed Ethereum addresses should not be reported',
);

const invalidIssues = validate(atlasDocument(`ForeignController: ${lowercaseAddress}`));
assert.ok(
  invalidIssues.some((issue) => issue.message.includes('EIP-55') && issue.found === lowercaseAddress),
  'lowercase Ethereum addresses should be reported as missing EIP-55 checksum casing',
);
