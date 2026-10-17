/**
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

/**
 * E-Ink Display Simulator - Drawing Primitives
 *
 * Low-level drawing functions that mimic Adafruit GFX library behavior.
 * These functions operate directly on a CanvasRenderingContext2D.
 */
/**
 * Creates a drawing context wrapper around a canvas.
 */
function createDrawingContext(canvas) {
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
function drawPixel(dc, x, y, color) {
    dc.ctx.fillStyle = color;
    dc.ctx.fillRect(x, y, 1, 1);
}
/**
 * Draw a line from (x0, y0) to (x1, y1).
 * Uses 0.5 pixel offset for crisp 1px lines on canvas.
 */
function drawLine(dc, x0, y0, x1, y1, color) {
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
function drawHLine(dc, x, y, w, color) {
    dc.ctx.fillStyle = color;
    dc.ctx.fillRect(x, y, w, 1);
}
/**
 * Draw a vertical line (optimized for speed).
 */
function drawVLine(dc, x, y, h, color) {
    dc.ctx.fillStyle = color;
    dc.ctx.fillRect(x, y, 1, h);
}
/**
 * Draw a rectangle outline.
 */
function drawRect(dc, x, y, w, h, color) {
    dc.ctx.strokeStyle = color;
    dc.ctx.lineWidth = 1;
    dc.ctx.strokeRect(x + 0.5, y + 0.5, w - 1, h - 1);
}
/**
 * Fill a rectangle.
 */
function fillRect(dc, x, y, w, h, color) {
    dc.ctx.fillStyle = color;
    dc.ctx.fillRect(x, y, w, h);
}
/**
 * Draw a circle outline.
 */
function drawCircle(dc, x, y, r, color) {
    dc.ctx.strokeStyle = color;
    dc.ctx.lineWidth = 1;
    dc.ctx.beginPath();
    dc.ctx.arc(x, y, r, 0, Math.PI * 2);
    dc.ctx.stroke();
}
/**
 * Fill a circle.
 */
function fillCircle(dc, x, y, r, color) {
    dc.ctx.fillStyle = color;
    dc.ctx.beginPath();
    dc.ctx.arc(x, y, r, 0, Math.PI * 2);
    dc.ctx.fill();
}
/**
 * Draw a triangle outline.
 */
function drawTriangle(dc, x0, y0, x1, y1, x2, y2, color) {
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
function fillTriangle(dc, x0, y0, x1, y1, x2, y2, color) {
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
function drawRoundRect(dc, x, y, w, h, r, color) {
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
function fillRoundRect(dc, x, y, w, h, r, color) {
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
function drawXBitmap(dc, x, y, bitmap, w, h, color) {
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
function drawXBitmapScaled(dc, x, y, bitmap, srcW, srcH, destW, destH, color) {
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
function clearDisplay(dc, color) {
    fillRect(dc, 0, 0, dc.width, dc.height, color);
}


  // ═══════════════════════════════════════════════════════════════════════════
  // FONTS
  // ═══════════════════════════════════════════════════════════════════════════

/**
 * E-Ink Display Simulator - Font Rendering
 *
 * Pixel-perfect bitmap font rendering that matches Adafruit GFX library.
 * Supports fonts extracted from Adafruit GFX header files.
 */
/**
 * Draw a single glyph from a bitmap font.
 * Returns the horizontal advance (distance to move cursor for next character).
 */
function drawGlyph(dc, x, y, charCode, font, color) {
    const glyph = font.glyphs[charCode];
    if (!glyph || glyph.width === 0) {
        return glyph ? glyph.xAdvance : 0;
    }
    let bitIndex = 0;
    for (let row = 0; row < glyph.height; row++) {
        for (let col = 0; col < glyph.width; col++) {
            const byteIndex = glyph.offset + Math.floor(bitIndex / 8);
            const bit = 7 - (bitIndex % 8); // MSB first for GFX fonts
            if (font.bitmap[byteIndex] & (1 << bit)) {
                drawPixel(dc, x + glyph.xOffset + col, y + glyph.yOffset + row, color);
            }
            bitIndex++;
        }
    }
    return glyph.xAdvance;
}
/**
 * Draw a string using a bitmap font.
 * Uses baseline positioning like Adafruit GFX setCursor/print.
 */
function drawText(dc, text, x, y, font, color) {
    let cursorX = x;
    for (const char of text) {
        cursorX += drawGlyph(dc, cursorX, y, char.charCodeAt(0), font, color);
    }
}
/**
 * Get the width of a text string in pixels.
 */
function getTextWidth(text, font) {
    let width = 0;
    for (const char of text) {
        const glyph = font.glyphs[char.charCodeAt(0)];
        if (glyph) {
            width += glyph.xAdvance;
        }
    }
    return width;
}
/**
 * Get the text bounds matching Adafruit GFX getTextBounds() behavior.
 * Returns width, height, and Y min/max offsets from baseline.
 */
function getTextBounds(text, font) {
    let width = 0;
    let minY = 0;
    let maxY = 0;
    let first = true;
    for (const char of text) {
        const glyph = font.glyphs[char.charCodeAt(0)];
        if (glyph) {
            width += glyph.xAdvance;
            // yOffset is negative for characters above baseline
            const top = glyph.yOffset;
            const bottom = glyph.yOffset + glyph.height;
            if (first) {
                minY = top;
                maxY = bottom;
                first = false;
            }
            else {
                if (top < minY)
                    minY = top;
                if (bottom > maxY)
                    maxY = bottom;
            }
        }
    }
    return {
        w: width,
        h: maxY - minY, // Actual text height
        yMin: minY,
        yMax: maxY,
    };
}
/**
 * Get a glyph from a font by character code.
 * Returns undefined if the character is not in the font.
 */
function getGlyph(font, charCode) {
    return font.glyphs[charCode];
}
/**
 * Check if a font contains a specific character.
 */
function hasChar(font, charCode) {
    return charCode >= font.first && charCode <= font.last && font.glyphs[charCode] !== undefined;
}
/**
 * Draw text centered horizontally within a given width.
 */
function drawTextCentered(dc, text, x, y, width, font, color) {
    const textW = getTextWidth(text, font);
    const startX = x + Math.floor((width - textW) / 2);
    drawText(dc, text, startX, y, font, color);
}
/**
 * Draw text right-aligned to a given x position.
 */
function drawTextRightAligned(dc, text, rightX, y, font, color) {
    const textW = getTextWidth(text, font);
    drawText(dc, text, rightX - textW, y, font, color);
}
/**
 * Built-in 5x7 font character data.
 * This is the default Adafruit GFX font from glcdfont.c.
 * Uses top-left positioning instead of baseline.
 */
const BUILTIN_5X7_FONT = [
    0x00, 0x00, 0x00, 0x00, 0x00, // Space
    0x00, 0x00, 0x5F, 0x00, 0x00, // !
    0x00, 0x07, 0x00, 0x07, 0x00, // "
    0x14, 0x7F, 0x14, 0x7F, 0x14, // #
    0x24, 0x2A, 0x7F, 0x2A, 0x12, // $
    0x23, 0x13, 0x08, 0x64, 0x62, // %
    0x36, 0x49, 0x55, 0x22, 0x50, // &
    0x00, 0x05, 0x03, 0x00, 0x00, // '
    0x00, 0x1C, 0x22, 0x41, 0x00, // (
    0x00, 0x41, 0x22, 0x1C, 0x00, // )
    0x08, 0x2A, 0x1C, 0x2A, 0x08, // *
    0x08, 0x08, 0x3E, 0x08, 0x08, // +
    0x00, 0x50, 0x30, 0x00, 0x00, // ,
    0x08, 0x08, 0x08, 0x08, 0x08, // -
    0x00, 0x60, 0x60, 0x00, 0x00, // .
    0x20, 0x10, 0x08, 0x04, 0x02, // /
    0x3E, 0x51, 0x49, 0x45, 0x3E, // 0
    0x00, 0x42, 0x7F, 0x40, 0x00, // 1
    0x42, 0x61, 0x51, 0x49, 0x46, // 2
    0x21, 0x41, 0x45, 0x4B, 0x31, // 3
    0x18, 0x14, 0x12, 0x7F, 0x10, // 4
    0x27, 0x45, 0x45, 0x45, 0x39, // 5
    0x3C, 0x4A, 0x49, 0x49, 0x30, // 6
    0x01, 0x71, 0x09, 0x05, 0x03, // 7
    0x36, 0x49, 0x49, 0x49, 0x36, // 8
    0x06, 0x49, 0x49, 0x29, 0x1E, // 9
    0x00, 0x36, 0x36, 0x00, 0x00, // :
    0x00, 0x56, 0x36, 0x00, 0x00, // ;
    0x00, 0x08, 0x14, 0x22, 0x41, // <
    0x14, 0x14, 0x14, 0x14, 0x14, // =
    0x41, 0x22, 0x14, 0x08, 0x00, // >
    0x02, 0x01, 0x51, 0x09, 0x06, // ?
    0x32, 0x49, 0x79, 0x41, 0x3E, // @
    0x7E, 0x11, 0x11, 0x11, 0x7E, // A
    0x7F, 0x49, 0x49, 0x49, 0x36, // B
    0x3E, 0x41, 0x41, 0x41, 0x22, // C
    0x7F, 0x41, 0x41, 0x22, 0x1C, // D
    0x7F, 0x49, 0x49, 0x49, 0x41, // E
    0x7F, 0x09, 0x09, 0x01, 0x01, // F
    0x3E, 0x41, 0x41, 0x51, 0x32, // G
    0x7F, 0x08, 0x08, 0x08, 0x7F, // H
    0x00, 0x41, 0x7F, 0x41, 0x00, // I
    0x20, 0x40, 0x41, 0x3F, 0x01, // J
    0x7F, 0x08, 0x14, 0x22, 0x41, // K
    0x7F, 0x40, 0x40, 0x40, 0x40, // L
    0x7F, 0x02, 0x04, 0x02, 0x7F, // M
    0x7F, 0x04, 0x08, 0x10, 0x7F, // N
    0x3E, 0x41, 0x41, 0x41, 0x3E, // O
    0x7F, 0x09, 0x09, 0x09, 0x06, // P
    0x3E, 0x41, 0x51, 0x21, 0x5E, // Q
    0x7F, 0x09, 0x19, 0x29, 0x46, // R
    0x46, 0x49, 0x49, 0x49, 0x31, // S
    0x01, 0x01, 0x7F, 0x01, 0x01, // T
    0x3F, 0x40, 0x40, 0x40, 0x3F, // U
    0x1F, 0x20, 0x40, 0x20, 0x1F, // V
    0x7F, 0x20, 0x18, 0x20, 0x7F, // W
    0x63, 0x14, 0x08, 0x14, 0x63, // X
    0x03, 0x04, 0x78, 0x04, 0x03, // Y
    0x61, 0x51, 0x49, 0x45, 0x43, // Z
    0x00, 0x00, 0x7F, 0x41, 0x41, // [
    0x02, 0x04, 0x08, 0x10, 0x20, // backslash
    0x41, 0x41, 0x7F, 0x00, 0x00, // ]
    0x04, 0x02, 0x01, 0x02, 0x04, // ^
    0x40, 0x40, 0x40, 0x40, 0x40, // _
    0x00, 0x01, 0x02, 0x04, 0x00, // `
    0x20, 0x54, 0x54, 0x54, 0x78, // a
    0x7F, 0x48, 0x44, 0x44, 0x38, // b
    0x38, 0x44, 0x44, 0x44, 0x20, // c
    0x38, 0x44, 0x44, 0x48, 0x7F, // d
    0x38, 0x54, 0x54, 0x54, 0x18, // e
    0x08, 0x7E, 0x09, 0x01, 0x02, // f
    0x08, 0x14, 0x54, 0x54, 0x3C, // g
    0x7F, 0x08, 0x04, 0x04, 0x78, // h
    0x00, 0x44, 0x7D, 0x40, 0x00, // i
    0x20, 0x40, 0x44, 0x3D, 0x00, // j
    0x00, 0x7F, 0x10, 0x28, 0x44, // k
    0x00, 0x41, 0x7F, 0x40, 0x00, // l
    0x7C, 0x04, 0x18, 0x04, 0x78, // m
    0x7C, 0x08, 0x04, 0x04, 0x78, // n
    0x38, 0x44, 0x44, 0x44, 0x38, // o
    0x7C, 0x14, 0x14, 0x14, 0x08, // p
    0x08, 0x14, 0x14, 0x18, 0x7C, // q
    0x7C, 0x08, 0x04, 0x04, 0x08, // r
    0x48, 0x54, 0x54, 0x54, 0x20, // s
    0x04, 0x3F, 0x44, 0x40, 0x20, // t
    0x3C, 0x40, 0x40, 0x20, 0x7C, // u
    0x1C, 0x20, 0x40, 0x20, 0x1C, // v
    0x3C, 0x40, 0x30, 0x40, 0x3C, // w
    0x44, 0x28, 0x10, 0x28, 0x44, // x
    0x0C, 0x50, 0x50, 0x50, 0x3C, // y
    0x44, 0x64, 0x54, 0x4C, 0x44, // z
    0x00, 0x08, 0x36, 0x41, 0x00, // {
    0x00, 0x00, 0x7F, 0x00, 0x00, // |
    0x00, 0x41, 0x36, 0x08, 0x00, // }
    0x08, 0x08, 0x2A, 0x1C, 0x08, // ->
    0x08, 0x1C, 0x2A, 0x08, 0x08, // <-
];
/**
 * Draw a character using the built-in 5x7 font.
 * Uses top-left positioning (not baseline).
 */
function drawBuiltinChar(dc, x, y, char, color) {
    const code = char.charCodeAt(0);
    if (code < 0x20 || code > 0x7f)
        return;
    const index = (code - 0x20) * 5;
    for (let col = 0; col < 5; col++) {
        const column = BUILTIN_5X7_FONT[index + col];
        for (let row = 0; row < 7; row++) {
            if (column & (1 << row)) {
                drawPixel(dc, x + col, y + row, color);
            }
        }
    }
}
/**
 * Draw a string using the built-in 5x7 font.
 * Uses top-left positioning. Character width is 6px (5px glyph + 1px spacing).
 */
function drawBuiltinText(dc, text, x, y, color) {
    let cursorX = x;
    for (const char of text) {
        drawBuiltinChar(dc, cursorX, y, char, color);
        cursorX += 6; // 5px glyph + 1px spacing
    }
}
/**
 * Get the width of text using the built-in 5x7 font.
 */
function getBuiltinTextWidth(text) {
    return text.length * 6;
}


  // ═══════════════════════════════════════════════════════════════════════════
  // SIMULATOR
  // ═══════════════════════════════════════════════════════════════════════════

/**
 * E-Ink Display Simulator - Main Simulator Class
 *
 * High-level API for simulating e-ink displays with Adafruit GFX compatibility.
 * Provides a clean interface for rendering to canvas elements.
 */
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
const DEFAULT_CONFIG = {
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
 * sim.drawText('Hello', 10, 20, myFont);
 * sim.drawRect(0, 0, 100, 50);
 * ```
 */
class EinkSimulator {
    /**
     * Create a new EinkSimulator.
     *
     * @param canvas - The HTML canvas element to render to
     * @param config - Display configuration options
     */
    constructor(canvas, config = {}) {
        this.currentFont = null;
        this.config = {
            width: config.width ?? DEFAULT_CONFIG.width,
            height: config.height ?? DEFAULT_CONFIG.height,
            foreground: config.foreground ?? DEFAULT_CONFIG.foreground,
            background: config.background ?? DEFAULT_CONFIG.background,
            accent: config.accent ?? DEFAULT_CONFIG.accent,
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
    get width() {
        return this.config.width;
    }
    /**
     * Get the display height.
     */
    get height() {
        return this.config.height;
    }
    /**
     * Get the foreground (black) color.
     */
    get foreground() {
        return this.config.foreground;
    }
    /**
     * Get the background (white) color.
     */
    get background() {
        return this.config.background;
    }
    /**
     * Get the accent (red) color.
     */
    get accent() {
        return this.config.accent;
    }
    /**
     * Get the underlying drawing context.
     * Use this for advanced operations not covered by the high-level API.
     */
    getContext() {
        return this.dc;
    }
    /**
     * Clear the display with the background color.
     */
    clear() {
        clearDisplay(this.dc, this.config.background);
    }
    /**
     * Fill the display with a specific color.
     */
    fill(color) {
        clearDisplay(this.dc, color);
    }
    // ═══════════════════════════════════════════════════════════════════════════
    // PIXEL OPERATIONS
    // ═══════════════════════════════════════════════════════════════════════════
    /**
     * Draw a single pixel.
     */
    drawPixel(x, y, color) {
        drawPixel(this.dc, x, y, color ?? this.config.foreground);
    }
    // ═══════════════════════════════════════════════════════════════════════════
    // LINE OPERATIONS
    // ═══════════════════════════════════════════════════════════════════════════
    /**
     * Draw a line from (x0, y0) to (x1, y1).
     */
    drawLine(x0, y0, x1, y1, color) {
        drawLine(this.dc, x0, y0, x1, y1, color ?? this.config.foreground);
    }
    /**
     * Draw a horizontal line.
     */
    drawHLine(x, y, w, color) {
        drawHLine(this.dc, x, y, w, color ?? this.config.foreground);
    }
    /**
     * Draw a vertical line.
     */
    drawVLine(x, y, h, color) {
        drawVLine(this.dc, x, y, h, color ?? this.config.foreground);
    }
    // ═══════════════════════════════════════════════════════════════════════════
    // RECTANGLE OPERATIONS
    // ═══════════════════════════════════════════════════════════════════════════
    /**
     * Draw a rectangle outline.
     */
    drawRect(x, y, w, h, color) {
        drawRect(this.dc, x, y, w, h, color ?? this.config.foreground);
    }
    /**
     * Fill a rectangle.
     */
    fillRect(x, y, w, h, color) {
        fillRect(this.dc, x, y, w, h, color ?? this.config.foreground);
    }
    /**
     * Draw a rounded rectangle outline.
     */
    drawRoundRect(x, y, w, h, r, color) {
        drawRoundRect(this.dc, x, y, w, h, r, color ?? this.config.foreground);
    }
    /**
     * Fill a rounded rectangle.
     */
    fillRoundRect(x, y, w, h, r, color) {
        fillRoundRect(this.dc, x, y, w, h, r, color ?? this.config.foreground);
    }
    // ═══════════════════════════════════════════════════════════════════════════
    // CIRCLE OPERATIONS
    // ═══════════════════════════════════════════════════════════════════════════
    /**
     * Draw a circle outline.
     */
    drawCircle(x, y, r, color) {
        drawCircle(this.dc, x, y, r, color ?? this.config.foreground);
    }
    /**
     * Fill a circle.
     */
    fillCircle(x, y, r, color) {
        fillCircle(this.dc, x, y, r, color ?? this.config.foreground);
    }
    // ═══════════════════════════════════════════════════════════════════════════
    // TRIANGLE OPERATIONS
    // ═══════════════════════════════════════════════════════════════════════════
    /**
     * Draw a triangle outline.
     */
    drawTriangle(x0, y0, x1, y1, x2, y2, color) {
        drawTriangle(this.dc, x0, y0, x1, y1, x2, y2, color ?? this.config.foreground);
    }
    /**
     * Fill a triangle.
     */
    fillTriangle(x0, y0, x1, y1, x2, y2, color) {
        fillTriangle(this.dc, x0, y0, x1, y1, x2, y2, color ?? this.config.foreground);
    }
    // ═══════════════════════════════════════════════════════════════════════════
    // BITMAP OPERATIONS
    // ═══════════════════════════════════════════════════════════════════════════
    /**
     * Draw an XBitmap image.
     * XBitmap format uses LSB-first ordering, matching Adafruit GFX drawXBitmap().
     */
    drawXBitmap(x, y, bitmap, w, h, color) {
        drawXBitmap(this.dc, x, y, bitmap, w, h, color ?? this.config.foreground);
    }
    /**
     * Draw an XBitmap image scaled to a target size.
     */
    drawXBitmapScaled(x, y, bitmap, srcW, srcH, destW, destH, color) {
        drawXBitmapScaled(this.dc, x, y, bitmap, srcW, srcH, destW, destH, color ?? this.config.foreground);
    }
    // ═══════════════════════════════════════════════════════════════════════════
    // TEXT OPERATIONS (Bitmap Fonts)
    // ═══════════════════════════════════════════════════════════════════════════
    /**
     * Set the current font for text operations.
     * Pass null to use the built-in 5x7 font.
     */
    setFont(font) {
        this.currentFont = font;
    }
    /**
     * Set the text color.
     */
    setTextColor(color) {
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
    drawText(text, x, y, font, color) {
        const useFont = font ?? this.currentFont;
        const useColor = color ?? this.textColor;
        if (useFont) {
            fontDrawText(this.dc, text, x, y, useFont, useColor);
        }
        else {
            fontDrawBuiltinText(this.dc, text, x, y, useColor);
        }
    }
    /**
     * Draw text centered horizontally within a given width.
     */
    drawTextCentered(text, x, y, width, font, color) {
        const useFont = font ?? this.currentFont;
        const useColor = color ?? this.textColor;
        if (useFont) {
            fontDrawTextCentered(this.dc, text, x, y, width, useFont, useColor);
        }
        else {
            const textW = fontGetBuiltinTextWidth(text);
            const startX = x + Math.floor((width - textW) / 2);
            drawBuiltinText(this.dc, text, startX, y, useColor);
        }
    }
    /**
     * Draw text right-aligned to a given x position.
     */
    drawTextRightAligned(text, rightX, y, font, color) {
        const useFont = font ?? this.currentFont;
        const useColor = color ?? this.textColor;
        if (useFont) {
            fontDrawTextRightAligned(this.dc, text, rightX, y, useFont, useColor);
        }
        else {
            const textW = fontGetBuiltinTextWidth(text);
            drawBuiltinText(this.dc, text, rightX - textW, y, useColor);
        }
    }
    /**
     * Get the width of a text string.
     */
    getTextWidth(text, font) {
        const useFont = font ?? this.currentFont;
        if (useFont) {
            return fontGetTextWidth(text, useFont);
        }
        else {
            return fontGetBuiltinTextWidth(text);
        }
    }
    /**
     * Get text bounds matching Adafruit GFX getTextBounds() behavior.
     */
    getTextBounds(text, font) {
        const useFont = font ?? this.currentFont;
        if (useFont) {
            return fontGetTextBounds(text, useFont);
        }
        else {
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
    toDataURL() {
        return this.dc.ctx.canvas.toDataURL('image/png');
    }
    /**
     * Export the display as a Blob.
     */
    toBlob() {
        return new Promise((resolve, reject) => {
            this.dc.ctx.canvas.toBlob((blob) => {
                if (blob) {
                    resolve(blob);
                }
                else {
                    reject(new Error('Failed to create blob'));
                }
            }, 'image/png');
        });
    }
    /**
     * Download the display as a PNG file.
     */
    download(filename = 'eink-display.png') {
        const link = document.createElement('a');
        link.download = filename;
        link.href = this.toDataURL();
        link.click();
    }
    /**
     * Copy the display to the clipboard.
     */
    async copyToClipboard() {
        const blob = await this.toBlob();
        await navigator.clipboard.write([
            new ClipboardItem({ 'image/png': blob }),
        ]);
    }
    /**
     * Set the display scale using CSS transform.
     * This maintains pixel-perfect rendering at larger sizes.
     */
    setScale(scale) {
        const canvas = this.dc.ctx.canvas;
        canvas.style.width = `${this.config.width}px`;
        canvas.style.height = `${this.config.height}px`;
        canvas.style.transform = `scale(${scale})`;
        canvas.style.transformOrigin = 'top left';
        canvas.style.imageRendering = 'pixelated';
    }
}


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
