/**
 * E-Ink Display Simulator - Type Definitions
 *
 * Core types for the Adafruit GFX-compatible display simulator.
 */
/**
 * Represents a single glyph in a bitmap font.
 * Matches the GFXglyph structure from Adafruit GFX library.
 */
export interface GFXGlyph {
    /** Offset into the bitmap array where this glyph's data starts */
    offset: number;
    /** Width of the glyph in pixels */
    width: number;
    /** Height of the glyph in pixels */
    height: number;
    /** Horizontal advance to next character position */
    xAdvance: number;
    /** X offset from cursor position to start drawing */
    xOffset: number;
    /** Y offset from baseline (negative = above baseline) */
    yOffset: number;
}
/**
 * Represents a complete bitmap font.
 * Matches the GFXfont structure from Adafruit GFX library.
 */
export interface GFXFont {
    /** Font name/identifier */
    name: string;
    /** Raw bitmap data containing all glyph pixels */
    bitmap: number[];
    /** Map of ASCII codes to glyph data */
    glyphs: Record<number, GFXGlyph>;
    /** First ASCII character code in font */
    first: number;
    /** Last ASCII character code in font */
    last: number;
    /** Line height (vertical advance between lines) */
    yAdvance: number;
}
/**
 * Text bounds information returned by getTextBounds().
 */
export interface TextBounds {
    /** Total width of the text in pixels */
    w: number;
    /** Total height of the text in pixels */
    h: number;
    /** Minimum Y offset (typically negative for chars above baseline) */
    yMin: number;
    /** Maximum Y offset */
    yMax: number;
}
/**
 * Display configuration options.
 */
export interface DisplayConfig {
    /** Display width in pixels */
    width: number;
    /** Display height in pixels */
    height: number;
    /** Foreground color (typically black for e-ink) */
    foreground?: string;
    /** Background color (typically white for e-ink) */
    background?: string;
}
/**
 * Color type - can be a CSS color string or hex value.
 */
export type Color = string;
/**
 * XBitmap image data format.
 * LSB-first within each byte, matching Adafruit GFX drawXBitmap format.
 */
export interface XBitmap {
    /** Raw bitmap data */
    data: number[];
    /** Image width in pixels */
    width: number;
    /** Image height in pixels */
    height: number;
}
/**
 * Point in 2D space.
 */
export interface Point {
    x: number;
    y: number;
}
/**
 * Rectangle definition.
 */
export interface Rect {
    x: number;
    y: number;
    width: number;
    height: number;
}
/**
 * Drawing context interface for canvas operations.
 * Abstracts the underlying canvas context.
 */
export interface DrawingContext {
    /** Canvas 2D rendering context */
    ctx: CanvasRenderingContext2D;
    /** Display width */
    width: number;
    /** Display height */
    height: number;
}
//# sourceMappingURL=types.d.ts.map