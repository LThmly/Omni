/**
 * E-Ink Display Simulator - Main Simulator Class
 *
 * High-level API for simulating e-ink displays with Adafruit GFX compatibility.
 * Provides a clean interface for rendering to canvas elements.
 */
import type { Color, DisplayConfig, DrawingContext, GFXFont, TextBounds } from './types.js';
/**
 * Default display configuration for common e-ink displays.
 */
export declare const DEFAULT_CONFIG: DisplayConfig;
/**
 * E-Ink Display Simulator.
 *
 * Provides an Adafruit GFX-compatible API for rendering to HTML canvas.
 * Designed for pixel-perfect simulation of e-ink displays.
 *
 * @example
 * ```typescript
 * const canvas = document.getElementById('display') as HTMLCanvasElement;
 * const sim = new EinkSimulator(canvas, { width: 296, height: 128 });
 *
 * sim.clear();
 * sim.drawText('Hello', 10, 20, myFont);
 * sim.drawRect(0, 0, 100, 50);
 * ```
 */
export declare class EinkSimulator {
    private dc;
    private config;
    private currentFont;
    private textColor;
    /**
     * Create a new EinkSimulator.
     *
     * @param canvas - The HTML canvas element to render to
     * @param config - Display configuration options
     */
    constructor(canvas: HTMLCanvasElement, config?: Partial<DisplayConfig>);
    /**
     * Get the display width.
     */
    get width(): number;
    /**
     * Get the display height.
     */
    get height(): number;
    /**
     * Get the foreground (black) color.
     */
    get foreground(): Color;
    /**
     * Get the background (white) color.
     */
    get background(): Color;
    /**
     * Get the underlying drawing context.
     * Use this for advanced operations not covered by the high-level API.
     */
    getContext(): DrawingContext;
    /**
     * Clear the display with the background color.
     */
    clear(): void;
    /**
     * Fill the display with a specific color.
     */
    fill(color: Color): void;
    /**
     * Draw a single pixel.
     */
    drawPixel(x: number, y: number, color?: Color): void;
    /**
     * Draw a line from (x0, y0) to (x1, y1).
     */
    drawLine(x0: number, y0: number, x1: number, y1: number, color?: Color): void;
    /**
     * Draw a horizontal line.
     */
    drawHLine(x: number, y: number, w: number, color?: Color): void;
    /**
     * Draw a vertical line.
     */
    drawVLine(x: number, y: number, h: number, color?: Color): void;
    /**
     * Draw a rectangle outline.
     */
    drawRect(x: number, y: number, w: number, h: number, color?: Color): void;
    /**
     * Fill a rectangle.
     */
    fillRect(x: number, y: number, w: number, h: number, color?: Color): void;
    /**
     * Draw a rounded rectangle outline.
     */
    drawRoundRect(x: number, y: number, w: number, h: number, r: number, color?: Color): void;
    /**
     * Fill a rounded rectangle.
     */
    fillRoundRect(x: number, y: number, w: number, h: number, r: number, color?: Color): void;
    /**
     * Draw a circle outline.
     */
    drawCircle(x: number, y: number, r: number, color?: Color): void;
    /**
     * Fill a circle.
     */
    fillCircle(x: number, y: number, r: number, color?: Color): void;
    /**
     * Draw a triangle outline.
     */
    drawTriangle(x0: number, y0: number, x1: number, y1: number, x2: number, y2: number, color?: Color): void;
    /**
     * Fill a triangle.
     */
    fillTriangle(x0: number, y0: number, x1: number, y1: number, x2: number, y2: number, color?: Color): void;
    /**
     * Draw an XBitmap image.
     * XBitmap format uses LSB-first ordering, matching Adafruit GFX drawXBitmap().
     */
    drawXBitmap(x: number, y: number, bitmap: number[], w: number, h: number, color?: Color): void;
    /**
     * Draw an XBitmap image scaled to a target size.
     */
    drawXBitmapScaled(x: number, y: number, bitmap: number[], srcW: number, srcH: number, destW: number, destH: number, color?: Color): void;
    /**
     * Set the current font for text operations.
     * Pass null to use the built-in 5x7 font.
     */
    setFont(font: GFXFont | null): void;
    /**
     * Set the text color.
     */
    setTextColor(color: Color): void;
    /**
     * Draw text using a bitmap font.
     * Uses baseline positioning like Adafruit GFX.
     *
     * @param text - The text to draw
     * @param x - X position (left edge)
     * @param y - Y position (baseline for GFX fonts, top for built-in font)
     * @param font - Optional font override (uses current font if not specified)
     * @param color - Optional color override (uses text color if not specified)
     */
    drawText(text: string, x: number, y: number, font?: GFXFont, color?: Color): void;
    /**
     * Draw text centered horizontally within a given width.
     */
    drawTextCentered(text: string, x: number, y: number, width: number, font?: GFXFont, color?: Color): void;
    /**
     * Draw text right-aligned to a given x position.
     */
    drawTextRightAligned(text: string, rightX: number, y: number, font?: GFXFont, color?: Color): void;
    /**
     * Get the width of a text string.
     */
    getTextWidth(text: string, font?: GFXFont): number;
    /**
     * Get text bounds matching Adafruit GFX getTextBounds() behavior.
     */
    getTextBounds(text: string, font?: GFXFont): TextBounds;
    /**
     * Export the display as a PNG data URL.
     */
    toDataURL(): string;
    /**
     * Export the display as a Blob.
     */
    toBlob(): Promise<Blob>;
    /**
     * Download the display as a PNG file.
     */
    download(filename?: string): void;
    /**
     * Copy the display to the clipboard.
     */
    copyToClipboard(): Promise<void>;
    /**
     * Set the display scale using CSS transform.
     * This maintains pixel-perfect rendering at larger sizes.
     */
    setScale(scale: number): void;
}
export type { Color, DisplayConfig, DrawingContext, GFXFont, GFXGlyph, TextBounds, XBitmap } from './types.js';
export { drawPixel, drawLine, drawRect, fillRect, drawCircle, fillCircle, drawXBitmap } from './primitives.js';
export { drawText, drawGlyph, getTextWidth, getTextBounds } from './fonts.js';
//# sourceMappingURL=simulator.d.ts.map