/**
 * E-Ink Display Simulator
 *
 * A web-based simulator for e-ink displays with pixel-perfect Adafruit GFX font rendering.
 * Designed for rapid UI prototyping without flashing hardware.
 *
 * @packageDocumentation
 */

// Main simulator class
export { EinkSimulator, DEFAULT_CONFIG } from './simulator.js';

// Types
export type {
  Color,
  DisplayConfig,
  DrawingContext,
  GFXFont,
  GFXGlyph,
  Point,
  Rect,
  TextBounds,
  XBitmap,
} from './types.js';

// Drawing primitives
export {
  createDrawingContext,
  drawPixel,
  drawLine,
  drawHLine,
  drawVLine,
  drawRect,
  fillRect,
  drawCircle,
  fillCircle,
  drawTriangle,
  fillTriangle,
  drawRoundRect,
  fillRoundRect,
  drawXBitmap,
  drawXBitmapScaled,
  clearDisplay,
} from './primitives.js';

// Font rendering
export {
  drawGlyph,
  drawText,
  getTextWidth,
  getTextBounds,
  getGlyph,
  hasChar,
  drawTextCentered,
  drawTextRightAligned,
  drawBuiltinChar,
  drawBuiltinText,
  getBuiltinTextWidth,
} from './fonts.js';
