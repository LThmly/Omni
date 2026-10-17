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
export function createDrawingContext(
  canvas: HTMLCanvasElement
): DrawingContext {
  const ctx = canvas.getContext('2d');
  if (!ctx) {
    throw new Error('Failed to get 2D rendering context');
  }
  ctx.imageSmoothingEnabled = false;
  return {
    ctx,
    width: canvas.width,
    height: canvas.height,
  };
}

/**
 * Draw a single pixel.
 */
export function drawPixel(
  dc: DrawingContext,
  x: number,
  y: number,
  color: Color
): void {
  dc.ctx.fillStyle = color;
  dc.ctx.fillRect(x, y, 1, 1);
}

/**
 * Draw a line from (x0, y0) to (x1, y1).
 * Uses 0.5 pixel offset for crisp 1px lines on canvas.
 */
export function drawLine(
  dc: DrawingContext,
  x0: number,
  y0: number,
  x1: number,
  y1: number,
  color: Color
): void {
  dc.ctx.strokeStyle = color;
  dc.ctx.lineWidth = 1;
  dc.ctx.beginPath();
  dc.ctx.moveTo(x0 + 0.5, y0 + 0.5);
  dc.ctx.lineTo(x1 + 0.5, y1 + 0.5);
  dc.ctx.stroke();
}

/**
 * Draw a horizontal line (optimized for speed).
 */
export function drawHLine(
  dc: DrawingContext,
  x: number,
  y: number,
  w: number,
  color: Color
): void {
  dc.ctx.fillStyle = color;
  dc.ctx.fillRect(x, y, w, 1);
}

/**
 * Draw a vertical line (optimized for speed).
 */
export function drawVLine(
  dc: DrawingContext,
  x: number,
  y: number,
  h: number,
  color: Color
): void {
  dc.ctx.fillStyle = color;
  dc.ctx.fillRect(x, y, 1, h);
}

/**
 * Draw a rectangle outline.
 */
export function drawRect(
  dc: DrawingContext,
  x: number,
  y: number,
  w: number,
  h: number,
  color: Color
): void {
  dc.ctx.strokeStyle = color;
  dc.ctx.lineWidth = 1;
  dc.ctx.strokeRect(x + 0.5, y + 0.5, w - 1, h - 1);
}

/**
 * Fill a rectangle.
 */
export function fillRect(
  dc: DrawingContext,
  x: number,
  y: number,
  w: number,
  h: number,
  color: Color
): void {
  dc.ctx.fillStyle = color;
  dc.ctx.fillRect(x, y, w, h);
}

/**
 * Draw a circle outline.
 */
export function drawCircle(
  dc: DrawingContext,
  x: number,
  y: number,
  r: number,
  color: Color
): void {
  dc.ctx.strokeStyle = color;
  dc.ctx.lineWidth = 1;
  dc.ctx.beginPath();
  dc.ctx.arc(x, y, r, 0, Math.PI * 2);
  dc.ctx.stroke();
}

/**
 * Fill a circle.
 */
export function fillCircle(
  dc: DrawingContext,
  x: number,
  y: number,
  r: number,
  color: Color
): void {
  dc.ctx.fillStyle = color;
  dc.ctx.beginPath();
  dc.ctx.arc(x, y, r, 0, Math.PI * 2);
  dc.ctx.fill();
}

/**
 * Draw a triangle outline.
 */
export function drawTriangle(
  dc: DrawingContext,
  x0: number,
  y0: number,
  x1: number,
  y1: number,
  x2: number,
  y2: number,
  color: Color
): void {
  dc.ctx.strokeStyle = color;
  dc.ctx.lineWidth = 1;
  dc.ctx.beginPath();
  dc.ctx.moveTo(x0 + 0.5, y0 + 0.5);
  dc.ctx.lineTo(x1 + 0.5, y1 + 0.5);
  dc.ctx.lineTo(x2 + 0.5, y2 + 0.5);
  dc.ctx.closePath();
  dc.ctx.stroke();
}

/**
 * Fill a triangle.
 */
export function fillTriangle(
  dc: DrawingContext,
  x0: number,
  y0: number,
  x1: number,
  y1: number,
  x2: number,
  y2: number,
  color: Color
): void {
  dc.ctx.fillStyle = color;
  dc.ctx.beginPath();
  dc.ctx.moveTo(x0, y0);
  dc.ctx.lineTo(x1, y1);
  dc.ctx.lineTo(x2, y2);
  dc.ctx.closePath();
  dc.ctx.fill();
}

/**
 * Draw a rounded rectangle outline.
 */
export function drawRoundRect(
  dc: DrawingContext,
  x: number,
  y: number,
  w: number,
  h: number,
  r: number,
  color: Color
): void {
  dc.ctx.strokeStyle = color;
  dc.ctx.lineWidth = 1;
  dc.ctx.beginPath();
  dc.ctx.moveTo(x + r, y);
  dc.ctx.lineTo(x + w - r, y);
  dc.ctx.arcTo(x + w, y, x + w, y + r, r);
  dc.ctx.lineTo(x + w, y + h - r);
  dc.ctx.arcTo(x + w, y + h, x + w - r, y + h, r);
  dc.ctx.lineTo(x + r, y + h);
  dc.ctx.arcTo(x, y + h, x, y + h - r, r);
  dc.ctx.lineTo(x, y + r);
  dc.ctx.arcTo(x, y, x + r, y, r);
  dc.ctx.stroke();
}

/**
 * Fill a rounded rectangle (pill shape).
 */
export function fillRoundRect(
  dc: DrawingContext,
  x: number,
  y: number,
  w: number,
  h: number,
  r: number,
  color: Color
): void {
  dc.ctx.fillStyle = color;
  dc.ctx.beginPath();
  dc.ctx.moveTo(x + r, y);
  dc.ctx.lineTo(x + w - r, y);
  dc.ctx.arcTo(x + w, y, x + w, y + r, r);
  dc.ctx.lineTo(x + w, y + h - r);
  dc.ctx.arcTo(x + w, y + h, x + w - r, y + h, r);
  dc.ctx.lineTo(x + r, y + h);
  dc.ctx.arcTo(x, y + h, x, y + h - r, r);
  dc.ctx.lineTo(x, y + r);
  dc.ctx.arcTo(x, y, x + r, y, r);
  dc.ctx.fill();
}

/**
 * Draw an XBitmap image.
 * XBitmap format uses LSB-first ordering within each byte,
 * matching Adafruit GFX drawXBitmap() function.
 */
export function drawXBitmap(
  dc: DrawingContext,
  x: number,
  y: number,
  bitmap: number[],
  w: number,
  h: number,
  color: Color
): void {
  const bytesPerRow = Math.ceil(w / 8);
  for (let row = 0; row < h; row++) {
    for (let col = 0; col < w; col++) {
      const byteIndex = row * bytesPerRow + Math.floor(col / 8);
      const bitIndex = col % 8;
      // XBitmap format: LSB is leftmost pixel
      if (bitmap[byteIndex] & (1 << bitIndex)) {
        drawPixel(dc, x + col, y + row, color);
      }
    }
  }
}

/**
 * Draw an XBitmap image scaled to a target size.
 * Uses nearest-neighbor sampling for pixel-perfect scaling.
 */
export function drawXBitmapScaled(
  dc: DrawingContext,
  x: number,
  y: number,
  bitmap: number[],
  srcW: number,
  srcH: number,
  destW: number,
  destH: number,
  color: Color
): void {
  const bytesPerRow = Math.ceil(srcW / 8);
  const scaleX = srcW / destW;
  const scaleY = srcH / destH;

  for (let destRow = 0; destRow < destH; destRow++) {
    for (let destCol = 0; destCol < destW; destCol++) {
      // Map destination pixel to source pixel
      const srcCol = Math.floor(destCol * scaleX);
      const srcRow = Math.floor(destRow * scaleY);

      const byteIndex = srcRow * bytesPerRow + Math.floor(srcCol / 8);
      const bitIndex = srcCol % 8;

      if (bitmap[byteIndex] & (1 << bitIndex)) {
        drawPixel(dc, x + destCol, y + destRow, color);
      }
    }
  }
}

/**
 * Clear the entire display with a color.
 */
export function clearDisplay(dc: DrawingContext, color: Color): void {
  fillRect(dc, 0, 0, dc.width, dc.height, color);
}
