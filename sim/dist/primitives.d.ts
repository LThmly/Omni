/**
 * E-Ink Display Simulator - Drawing Primitives
 *
 * Low-level drawing functions that mimic Adafruit GFX library behavior.
 * These functions operate directly on a CanvasRenderingContext2D.
 */
import type { Color, DrawingContext } from './types.js';
/**
 * Creates a drawing context wrapper around a canvas.
 */
export declare function createDrawingContext(canvas: HTMLCanvasElement): DrawingContext;
/**
 * Draw a single pixel.
 */
export declare function drawPixel(dc: DrawingContext, x: number, y: number, color: Color): void;
/**
 * Draw a line from (x0, y0) to (x1, y1).
 * Uses 0.5 pixel offset for crisp 1px lines on canvas.
 */
export declare function drawLine(dc: DrawingContext, x0: number, y0: number, x1: number, y1: number, color: Color): void;
/**
 * Draw a horizontal line (optimized for speed).
 */
export declare function drawHLine(dc: DrawingContext, x: number, y: number, w: number, color: Color): void;
/**
 * Draw a vertical line (optimized for speed).
 */
export declare function drawVLine(dc: DrawingContext, x: number, y: number, h: number, color: Color): void;
/**
 * Draw a rectangle outline.
 */
export declare function drawRect(dc: DrawingContext, x: number, y: number, w: number, h: number, color: Color): void;
/**
 * Fill a rectangle.
 */
export declare function fillRect(dc: DrawingContext, x: number, y: number, w: number, h: number, color: Color): void;
/**
 * Draw a circle outline.
 */
export declare function drawCircle(dc: DrawingContext, x: number, y: number, r: number, color: Color): void;
/**
 * Fill a circle.
 */
export declare function fillCircle(dc: DrawingContext, x: number, y: number, r: number, color: Color): void;
/**
 * Draw a triangle outline.
 */
export declare function drawTriangle(dc: DrawingContext, x0: number, y0: number, x1: number, y1: number, x2: number, y2: number, color: Color): void;
/**
 * Fill a triangle.
 */
export declare function fillTriangle(dc: DrawingContext, x0: number, y0: number, x1: number, y1: number, x2: number, y2: number, color: Color): void;
/**
 * Draw a rounded rectangle outline.
 */
export declare function drawRoundRect(dc: DrawingContext, x: number, y: number, w: number, h: number, r: number, color: Color): void;
/**
 * Fill a rounded rectangle (pill shape).
 */
export declare function fillRoundRect(dc: DrawingContext, x: number, y: number, w: number, h: number, r: number, color: Color): void;
/**
 * Draw an XBitmap image.
 * XBitmap format uses LSB-first ordering within each byte,
 * matching Adafruit GFX drawXBitmap() function.
 */
export declare function drawXBitmap(dc: DrawingContext, x: number, y: number, bitmap: number[], w: number, h: number, color: Color): void;
/**
 * Draw an XBitmap image scaled to a target size.
 * Uses nearest-neighbor sampling for pixel-perfect scaling.
 */
export declare function drawXBitmapScaled(dc: DrawingContext, x: number, y: number, bitmap: number[], srcW: number, srcH: number, destW: number, destH: number, color: Color): void;
/**
 * Clear the entire display with a color.
 */
export declare function clearDisplay(dc: DrawingContext, color: Color): void;
//# sourceMappingURL=primitives.d.ts.map