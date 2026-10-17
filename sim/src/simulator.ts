/**
 * E-Ink Display Simulator - Main Simulator Class
 *
 * High-level API for simulating e-ink displays with Adafruit GFX compatibility.
 * Provides a clean interface for rendering to canvas elements.
 */

import type { Color, DisplayConfig, DrawingContext, GFXFont, TextBounds } from './types.js';
import {
  createDrawingContext,
  clearDisplay,
  drawPixel,
  drawLine,
  drawHLine,
  drawVLine,
  drawRect,
  fillRect,
  drawRoundRect,
  fillRoundRect,
  drawCircle,
  fillCircle,
  drawTriangle,
  fillTriangle,
  drawXBitmap,
  drawXBitmapScaled,
} from './primitives.js';
import {
  drawText,
  drawTextCentered,
  drawTextRightAligned,
  getTextWidth,
  getTextBounds,
  drawBuiltinText,
  getBuiltinTextWidth,
} from './fonts.js';

// Create local references for use inside class methods
// (avoids name collision with class methods of the same name)
const fontDrawText = drawText;
const fontDrawTextCentered = drawTextCentered;
const fontDrawTextRightAligned = drawTextRightAligned;
const fontGetTextWidth = getTextWidth;
const fontGetTextBounds = getTextBounds;
const fontDrawBuiltinText = drawBuiltinText;
const fontGetBuiltinTextWidth = getBuiltinTextWidth;

/**
 * Default display configuration for Adafruit 6382 (4.2" 400x300 Tri-Color B/W/Red SSD1683).
 */
export const DEFAULT_CONFIG: DisplayConfig = {
  width: 300,
  height: 400,
  foreground: '#000000',
  background: '#FFFFFF',
  accent: '#C40000',
};

/**
 * E-Ink Display Simulator.
 *
 * Provides an Adafruit GFX-compatible API for rendering to HTML canvas.
 * Designed for pixel-perfect simulation of e-ink displays.
 *
 * @example
 * ```typescript
 * const canvas = document.getElementById('display') as HTMLCanvasElement;
 * const sim = new EinkSimulator(canvas, { width: 400, height: 300 });
 *
 * sim.clear();
 * sim.fillText('Hello', 10, 20, myFont);
 * sim.drawRect(0, 0, 100, 50);
 * ```
 */
export class EinkSimulator {
  private dc: DrawingContext;
  private config: Required<DisplayConfig>;
  private currentFont: GFXFont | null = null;
  private textColor: Color;

  /**
   * Create a new EinkSimulator.
   *
   * @param canvas - The HTML canvas element to render to
   * @param config - Display configuration options
   */
  constructor(canvas: HTMLCanvasElement, config: Partial<DisplayConfig> = {}) {
    this.config = {
      width: config.width ?? DEFAULT_CONFIG.width!,
      height: config.height ?? DEFAULT_CONFIG.height!,
      foreground: config.foreground ?? DEFAULT_CONFIG.foreground!,
      background: config.background ?? DEFAULT_CONFIG.background!,
      accent: config.accent ?? DEFAULT_CONFIG.accent!,
    };

    // Set canvas size
    canvas.width = this.config.width;
    canvas.height = this.config.height;

    this.dc = createDrawingContext(canvas);
    this.textColor = this.config.foreground;
  }

  /**
   * Get the display width.
   */
  get width(): number {
    return this.config.width;
  }

  /**
   * Get the display height.
   */
  get height(): number {
    return this.config.height;
  }

  /**
   * Get the foreground (black) color.
   */
  get foreground(): Color {
    return this.config.foreground;
  }

  /**
   * Get the background (white) color.
   */
  get background(): Color {
    return this.config.background;
  }

  /**
   * Get the accent (red) color.
   */
  get accent(): Color {
    return this.config.accent;
  }

  /**
   * Get the underlying drawing context.
   * Use this for advanced operations not covered by the high-level API.
   */
  getContext(): DrawingContext {
    return this.dc;
  }

  /**
   * Clear the display with the background color.
   */
  clear(): void {
    clearDisplay(this.dc, this.config.background);
  }

  /**
   * Fill the display with a specific color.
   */
  fill(color: Color): void {
    clearDisplay(this.dc, color);
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // PIXEL OPERATIONS
  // ═══════════════════════════════════════════════════════════════════════════

  /**
   * Draw a single pixel.
   */
  drawPixel(x: number, y: number, color?: Color): void {
    drawPixel(this.dc, x, y, color ?? this.config.foreground);
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // LINE OPERATIONS
  // ═══════════════════════════════════════════════════════════════════════════

  /**
   * Draw a line from (x0, y0) to (x1, y1).
   */
  drawLine(x0: number, y0: number, x1: number, y1: number, color?: Color): void {
    drawLine(this.dc, x0, y0, x1, y1, color ?? this.config.foreground);
  }

  /**
   * Draw a horizontal line.
   */
  drawHLine(x: number, y: number, w: number, color?: Color): void {
    drawHLine(this.dc, x, y, w, color ?? this.config.foreground);
  }

  /**
   * Draw a vertical line.
   */
  drawVLine(x: number, y: number, h: number, color?: Color): void {
    drawVLine(this.dc, x, y, h, color ?? this.config.foreground);
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // RECTANGLE OPERATIONS
  // ═══════════════════════════════════════════════════════════════════════════

  /**
   * Draw a rectangle outline.
   */
  drawRect(x: number, y: number, w: number, h: number, color?: Color): void {
    drawRect(this.dc, x, y, w, h, color ?? this.config.foreground);
  }

  /**
   * Fill a rectangle.
   */
  fillRect(x: number, y: number, w: number, h: number, color?: Color): void {
    fillRect(this.dc, x, y, w, h, color ?? this.config.foreground);
  }

  /**
   * Draw a rounded rectangle outline.
   */
  drawRoundRect(x: number, y: number, w: number, h: number, r: number, color?: Color): void {
    drawRoundRect(this.dc, x, y, w, h, r, color ?? this.config.foreground);
  }

  /**
   * Fill a rounded rectangle.
   */
  fillRoundRect(x: number, y: number, w: number, h: number, r: number, color?: Color): void {
    fillRoundRect(this.dc, x, y, w, h, r, color ?? this.config.foreground);
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // CIRCLE OPERATIONS
  // ═══════════════════════════════════════════════════════════════════════════

  /**
   * Draw a circle outline.
   */
  drawCircle(x: number, y: number, r: number, color?: Color): void {
    drawCircle(this.dc, x, y, r, color ?? this.config.foreground);
  }

  /**
   * Fill a circle.
   */
  fillCircle(x: number, y: number, r: number, color?: Color): void {
    fillCircle(this.dc, x, y, r, color ?? this.config.foreground);
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // TRIANGLE OPERATIONS
  // ═══════════════════════════════════════════════════════════════════════════

  /**
   * Draw a triangle outline.
   */
  drawTriangle(
    x0: number, y0: number,
    x1: number, y1: number,
    x2: number, y2: number,
    color?: Color
  ): void {
    drawTriangle(this.dc, x0, y0, x1, y1, x2, y2, color ?? this.config.foreground);
  }

  /**
   * Fill a triangle.
   */
  fillTriangle(
    x0: number, y0: number,
    x1: number, y1: number,
    x2: number, y2: number,
    color?: Color
  ): void {
    fillTriangle(this.dc, x0, y0, x1, y1, x2, y2, color ?? this.config.foreground);
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // BITMAP OPERATIONS
  // ═══════════════════════════════════════════════════════════════════════════

  /**
   * Draw an XBitmap image.
   * XBitmap format uses LSB-first ordering, matching Adafruit GFX drawXBitmap().
   */
  drawXBitmap(x: number, y: number, bitmap: number[], w: number, h: number, color?: Color): void {
    drawXBitmap(this.dc, x, y, bitmap, w, h, color ?? this.config.foreground);
  }

  /**
   * Draw an XBitmap image scaled to a target size.
   */
  drawXBitmapScaled(
    x: number, y: number,
    bitmap: number[],
    srcW: number, srcH: number,
    destW: number, destH: number,
    color?: Color
  ): void {
    drawXBitmapScaled(
      this.dc, x, y, bitmap, srcW, srcH, destW, destH, color ?? this.config.foreground
    );
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // TEXT OPERATIONS (Bitmap Fonts)
  // ═══════════════════════════════════════════════════════════════════════════

  /**
   * Set the current font for text operations.
   * Pass null to use the built-in 5x7 font.
   */
  setFont(font: GFXFont | null): void {
    this.currentFont = font;
  }

  /**
   * Set the text color.
   */
  setTextColor(color: Color): void {
    this.textColor = color;
  }

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
  drawText(text: string, x: number, y: number, font?: GFXFont, color?: Color): void {
    const useFont = font ?? this.currentFont;
    const useColor = color ?? this.textColor;

    if (useFont) {
      fontDrawText(this.dc, text, x, y, useFont, useColor);
    } else {
      fontDrawBuiltinText(this.dc, text, x, y, useColor);
    }
  }

  /**
   * Draw text centered horizontally within a given width.
   */
  drawTextCentered(text: string, x: number, y: number, width: number, font?: GFXFont, color?: Color): void {
    const useFont = font ?? this.currentFont;
    const useColor = color ?? this.textColor;

    if (useFont) {
      fontDrawTextCentered(this.dc, text, x, y, width, useFont, useColor);
    } else {
      const textW = fontGetBuiltinTextWidth(text);
      const startX = x + Math.floor((width - textW) / 2);
      drawBuiltinText(this.dc, text, startX, y, useColor);
    }
  }

  /**
   * Draw text right-aligned to a given x position.
   */
  drawTextRightAligned(text: string, rightX: number, y: number, font?: GFXFont, color?: Color): void {
    const useFont = font ?? this.currentFont;
    const useColor = color ?? this.textColor;

    if (useFont) {
      fontDrawTextRightAligned(this.dc, text, rightX, y, useFont, useColor);
    } else {
      const textW = fontGetBuiltinTextWidth(text);
      drawBuiltinText(this.dc, text, rightX - textW, y, useColor);
    }
  }

  /**
   * Get the width of a text string.
   */
  getTextWidth(text: string, font?: GFXFont): number {
    const useFont = font ?? this.currentFont;
    if (useFont) {
      return fontGetTextWidth(text, useFont);
    } else {
      return fontGetBuiltinTextWidth(text);
    }
  }

  /**
   * Get text bounds matching Adafruit GFX getTextBounds() behavior.
   */
  getTextBounds(text: string, font?: GFXFont): TextBounds {
    const useFont = font ?? this.currentFont;
    if (useFont) {
      return fontGetTextBounds(text, useFont);
    } else {
      // Built-in font is 7px tall, positioned at top
      return {
        w: fontGetBuiltinTextWidth(text),
        h: 7,
        yMin: 0,
        yMax: 7,
      };
    }
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // UTILITY METHODS
  // ═══════════════════════════════════════════════════════════════════════════

  /**
   * Export the display as a PNG data URL.
   */
  toDataURL(): string {
    return this.dc.ctx.canvas.toDataURL('image/png');
  }

  /**
   * Export the display as a Blob.
   */
  toBlob(): Promise<Blob> {
    return new Promise((resolve, reject) => {
      this.dc.ctx.canvas.toBlob((blob) => {
        if (blob) {
          resolve(blob);
        } else {
          reject(new Error('Failed to create blob'));
        }
      }, 'image/png');
    });
  }

  /**
   * Download the display as a PNG file.
   */
  download(filename = 'eink-display.png'): void {
    const link = document.createElement('a');
    link.download = filename;
    link.href = this.toDataURL();
    link.click();
  }

  /**
   * Copy the display to the clipboard.
   */
  async copyToClipboard(): Promise<void> {
    const blob = await this.toBlob();
    await navigator.clipboard.write([
      new ClipboardItem({ 'image/png': blob }),
    ]);
  }

  /**
   * Set the display scale using CSS transform.
   * This maintains pixel-perfect rendering at larger sizes.
   */
  setScale(scale: number): void {
    const canvas = this.dc.ctx.canvas;
    canvas.style.width = `${this.config.width}px`;
    canvas.style.height = `${this.config.height}px`;
    canvas.style.transform = `scale(${scale})`;
    canvas.style.transformOrigin = 'top left';
    canvas.style.imageRendering = 'pixelated';
  }
}

// Re-export types and utilities for convenience
export type { Color, DisplayConfig, DrawingContext, GFXFont, GFXGlyph, TextBounds, XBitmap } from './types.js';
export { drawPixel, drawLine, drawRect, fillRect, drawCircle, fillCircle, drawXBitmap } from './primitives.js';
export { drawText, drawGlyph, getTextWidth, getTextBounds } from './fonts.js';
