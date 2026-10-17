#!/usr/bin/env node
/**
 * Bundle the compiled TypeScript into a single browser-ready JavaScript file.
 *
 * This script:
 * 1. Reads all compiled JS files from dist/
 * 2. Inlines imports to create a single file
 * 3. Wraps everything in an IIFE with exports on window.EinkSimulator
 */

const fs = require('fs');
const path = require('path');

const DIST_DIR = path.join(__dirname, '../dist');
const OUTPUT_FILE = path.join(DIST_DIR, 'eink-simulator.bundle.js');

// Read and process each compiled module
function readModule(filename) {
  const filepath = path.join(DIST_DIR, filename);
  if (!fs.existsSync(filepath)) {
    console.error(`Warning: ${filename} not found`);
    return '';
  }
  let content = fs.readFileSync(filepath, 'utf8');

  // Remove import statements (we'll inline everything)
  content = content.replace(/^import .* from ['"]\.\/.*['"];?\n?/gm, '');
  content = content.replace(/^import type .* from ['"]\.\/.*['"];?\n?/gm, '');

  // Remove re-export statements like: export { foo } from './module.js';
  content = content.replace(/^export \{[^}]*\} from ['"]\.\/.*['"];?\n?/gm, '');
  content = content.replace(/^export type \{[^}]*\} from ['"]\.\/.*['"];?\n?/gm, '');

  // Remove export keywords but keep the declarations
  content = content.replace(/^export (const|function|class|type|interface)/gm, '$1');
  content = content.replace(/^export \{[^}]*\};?\n?/gm, '');
  content = content.replace(/^export type \{[^}]*\};?\n?/gm, '');

  // Remove sourcemap comments
  content = content.replace(/\/\/# sourceMappingURL=.*\.map\n?/g, '');

  return content;
}

// Bundle all modules
const bundle = `/**
 * E-Ink Display Simulator
 * A web-based simulator for e-ink displays with Adafruit GFX font rendering.
 *
 * @license MIT
 */
(function(global) {
  'use strict';

  // ═══════════════════════════════════════════════════════════════════════════
  // PRIMITIVES
  // ═══════════════════════════════════════════════════════════════════════════

${readModule('primitives.js')}

  // ═══════════════════════════════════════════════════════════════════════════
  // FONTS
  // ═══════════════════════════════════════════════════════════════════════════

${readModule('fonts.js')}

  // ═══════════════════════════════════════════════════════════════════════════
  // SIMULATOR
  // ═══════════════════════════════════════════════════════════════════════════

${readModule('simulator.js')}

  // ═══════════════════════════════════════════════════════════════════════════
  // EXPORTS
  // ═══════════════════════════════════════════════════════════════════════════

  global.EinkSimulator = {
    // Main class
    EinkSimulator: EinkSimulator,
    DEFAULT_CONFIG: DEFAULT_CONFIG,

    // Drawing primitives
    createDrawingContext: createDrawingContext,
    drawPixel: drawPixel,
    drawLine: drawLine,
    drawHLine: drawHLine,
    drawVLine: drawVLine,
    drawRect: drawRect,
    fillRect: fillRect,
    drawCircle: drawCircle,
    fillCircle: fillCircle,
    drawTriangle: drawTriangle,
    fillTriangle: fillTriangle,
    drawRoundRect: drawRoundRect,
    fillRoundRect: fillRoundRect,
    drawXBitmap: drawXBitmap,
    drawXBitmapScaled: drawXBitmapScaled,
    clearDisplay: clearDisplay,

    // Font rendering
    drawGlyph: drawGlyph,
    drawText: drawText,
    getTextWidth: getTextWidth,
    getTextBounds: getTextBounds,
    getGlyph: getGlyph,
    hasChar: hasChar,
    drawTextCentered: drawTextCentered,
    drawTextRightAligned: drawTextRightAligned,
    drawBuiltinChar: drawBuiltinChar,
    drawBuiltinText: drawBuiltinText,
    getBuiltinTextWidth: getBuiltinTextWidth
  };

})(typeof window !== 'undefined' ? window : this);
`;

// Ensure dist directory exists
if (!fs.existsSync(DIST_DIR)) {
  fs.mkdirSync(DIST_DIR, { recursive: true });
}

// Write bundle
fs.writeFileSync(OUTPUT_FILE, bundle);
console.log(`Bundle written to ${OUTPUT_FILE}`);

// Calculate size
const stats = fs.statSync(OUTPUT_FILE);
console.log(`Bundle size: ${(stats.size / 1024).toFixed(1)} KB`);

// Also process font-data.js for browser use (strip exports/imports)
const GENERATED_DIR = path.join(DIST_DIR, 'generated');
const FONT_DATA_FILE = path.join(GENERATED_DIR, 'font-data.js');

if (fs.existsSync(FONT_DATA_FILE)) {
  let fontData = fs.readFileSync(FONT_DATA_FILE, 'utf8');

  // Remove import statements
  fontData = fontData.replace(/^import .* from ['"].*['"];?\n?/gm, '');
  fontData = fontData.replace(/^import type .* from ['"].*['"];?\n?/gm, '');

  // Remove export keywords but keep declarations
  fontData = fontData.replace(/^export (const|function|class)/gm, '$1');
  fontData = fontData.replace(/^export \{[^}]*\};?\n?/gm, '');

  // Convert 'const' to 'var' so font variables are globally accessible
  // (const at top-level of a non-module script doesn't create window properties)
  fontData = fontData.replace(/^const /gm, 'var ');

  // Remove sourcemap comments
  fontData = fontData.replace(/\/\/# sourceMappingURL=.*\.map\n?/g, '');

  fs.writeFileSync(FONT_DATA_FILE, fontData);
  console.log(`Font data processed: ${FONT_DATA_FILE}`);

  const fontStats = fs.statSync(FONT_DATA_FILE);
  console.log(`Font data size: ${(fontStats.size / 1024).toFixed(1)} KB`);
}
