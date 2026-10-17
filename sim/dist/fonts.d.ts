/**
 * E-Ink Display Simulator - Font Rendering
 *
 * Pixel-perfect bitmap font rendering that matches Adafruit GFX library.
 * Supports fonts extracted from Adafruit GFX header files.
 */
import type { Color, DrawingContext, GFXFont, GFXGlyph, TextBounds } from './types.js';
/**
 * Draw a single glyph from a bitmap font.
 * Returns the horizontal advance (distance to move cursor for next character).
 */
export declare function drawGlyph(dc: DrawingContext, x: number, y: number, charCode: number, font: GFXFont, color: Color): number;
/**
 * Draw a string using a bitmap font.
 * Uses baseline positioning like Adafruit GFX setCursor/print.
 */
export declare function drawText(dc: DrawingContext, text: string, x: number, y: number, font: GFXFont, color: Color): void;
/**
 * Get the width of a text string in pixels.
 */
export declare function getTextWidth(text: string, font: GFXFont): number;
/**
 * Get the text bounds matching Adafruit GFX getTextBounds() behavior.
 * Returns width, height, and Y min/max offsets from baseline.
 */
export declare function getTextBounds(text: string, font: GFXFont): TextBounds;
/**
 * Get a glyph from a font by character code.
 * Returns undefined if the character is not in the font.
 */
export declare function getGlyph(font: GFXFont, charCode: number): GFXGlyph | undefined;
/**
 * Check if a font contains a specific character.
 */
export declare function hasChar(font: GFXFont, charCode: number): boolean;
/**
 * Draw text centered horizontally within a given width.
 */
export declare function drawTextCentered(dc: DrawingContext, text: string, x: number, y: number, width: number, font: GFXFont, color: Color): void;
/**
 * Draw text right-aligned to a given x position.
 */
export declare function drawTextRightAligned(dc: DrawingContext, text: string, rightX: number, y: number, font: GFXFont, color: Color): void;
/**
 * Draw a character using the built-in 5x7 font.
 * Uses top-left positioning (not baseline).
 */
export declare function drawBuiltinChar(dc: DrawingContext, x: number, y: number, char: string, color: Color): void;
/**
 * Draw a string using the built-in 5x7 font.
 * Uses top-left positioning. Character width is 6px (5px glyph + 1px spacing).
 */
export declare function drawBuiltinText(dc: DrawingContext, text: string, x: number, y: number, color: Color): void;
/**
 * Get the width of text using the built-in 5x7 font.
 */
export declare function getBuiltinTextWidth(text: string): number;
//# sourceMappingURL=fonts.d.ts.map