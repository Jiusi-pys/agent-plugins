const { test } = require('node:test');
const assert = require('node:assert/strict');
const { existsSync, readFileSync } = require('node:fs');
const path = require('node:path');

const root = path.resolve(__dirname, '..');
const plugin = path.join(root, 'plugins', 'epub-editor');

test('epub-editor is a Claude Code marketplace plugin', () => {
  const manifestPath = path.join(plugin, '.claude-plugin', 'plugin.json');
  assert.equal(existsSync(manifestPath), true, 'Claude Code manifest is present');
  assert.equal(existsSync(path.join(plugin, 'skills', 'epub-edit', 'SKILL.md')), true, 'EPUB edit skill is present');
  assert.equal(existsSync(path.join(plugin, 'scripts', 'epub_editor.py')), true, 'EPUB processor is present');

  const manifest = JSON.parse(readFileSync(manifestPath, 'utf8'));
  assert.equal(manifest.name, 'epub-editor');

  const marketplace = JSON.parse(readFileSync(path.join(root, '.claude-plugin', 'marketplace.json'), 'utf8'));
  const entry = marketplace.plugins.find(({ name }) => name === 'epub-editor');
  assert.ok(entry, 'marketplace lists epub-editor');
  assert.equal(entry.source, './plugins/epub-editor');
});
