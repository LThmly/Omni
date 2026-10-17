/**
 * E-Ink Display Simulator
 *
 * A web-based simulator for e-ink displays with pixel-perfect Adafruit GFX font rendering.
 * Designed for rapid UI prototyping without flashing hardware.
 *
 * @packageDocumentation
 */
export { EinkSimulator, DEFAULT_CONFIG } from './simulator.js';
export type { Color, DisplayConfig, DrawingContext, GFXFont, GFXGlyph, Point, Rect, TextBounds, XBitmap, } from './types.js';
export { createDrawingContext, drawPixel, drawLine, drawHLine, drawVLine, drawRect, fillRect, drawCircle, fillCircle, drawTriangle, fillTriangle, drawRoundRect, fillRoundRect, drawXBitmap, drawXBitmapScaled, clearDisplay, } from './primitives.js';
export { drawGlyph, drawText, getTextWidth, getTextBounds, getGlyph, hasChar, drawTextCentered, drawTextRightAligned, drawBuiltinChar, drawBuiltinText, getBuiltinTextWidth, } from './fonts.js';
//# sourceMappingURL=index.d.ts.map