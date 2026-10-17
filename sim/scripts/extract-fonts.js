#!/usr/bin/env node
/**
 * Extract Adafruit GFX font data from C header files and output TypeScript.
 *
 * Usage:
 *   npx extract-fonts --config fonts.config.json
 *   npx extract-fonts --fonts-dir ./Fonts --fonts "MyFont12pt7b,MyFont24pt7b"
 *   node scripts/extract-fonts.js > src/generated/font-data.ts
 *
 * Options:
 *   --config       Path to JSON config file
 *   --fonts-dir    Directory containing Adafruit GFX font headers
 *   --custom-dir   Directory containing custom font headers (optional)
 *   --fonts        Comma-separated list of font names (without .h extension)
 *   --output       Output file path (default: stdout)
 *   --help         Show help message
 *
 * Config file format (fonts.config.json):
 *   {
 *     "fontsDir": "./path/to/Fonts",
 *     "customFontsDir": "./path/to/custom-fonts",
 *     "fonts": ["MyFont12pt7b", "MyFont24pt7b"],
 *     "output": "./src/generated/font-data.ts"
 *   }
 */

const fs = require('fs');
const path = require('path');

// Parse command line arguments
function parseArgs() {
  const args = process.argv.slice(2);
  const options = {
    config: null,
    fontsDir: null,
    customDir: null,
    fonts: null,
    output: null,
    help: false
  };

  for (let i = 0; i < args.length; i++) {
    const arg = args[i];
    switch (arg) {
      case '--config':
        options.config = args[++i];
        break;
      case '--fonts-dir':
        options.fontsDir = args[++i];
        break;
      case '--custom-dir':
        options.customDir = args[++i];
        break;
      case '--fonts':
        options.fonts = args[++i]?.split(',').map(s => s.trim()).filter(Boolean);
        break;
      case '--output':
        options.output = args[++i];
        break;
      case '--help':
      case '-h':
        options.help = true;
        break;
    }
  }

  return options;
}

function showHelp() {
  console.log(`
Extract Adafruit GFX font data from C header files.

Usage:
  npx extract-fonts --config fonts.config.json
  npx extract-fonts --fonts-dir ./Fonts --fonts "MyFont12pt7b,MyFont24pt7b"

Options:
  --config       Path to JSON config file
  --fonts-dir    Directory containing Adafruit GFX font headers
  --custom-dir   Directory containing custom font headers (optional)
  --fonts        Comma-separated list of font names (without .h extension)
  --output       Output file path (default: stdout)
  --help, -h     Show this help message

Config file format (fonts.config.json):
  {
    "fontsDir": "./path/to/Fonts",
    "customFontsDir": "./path/to/custom-fonts",
    "fonts": ["FreeSans9pt7b", "FreeMono12pt7b"],
    "output": "./src/generated/font-data.ts"
  }

Examples:
  # Using config file
  npx extract-fonts --config fonts.config.json

  # Using CLI arguments
  npx extract-fonts --fonts-dir ./Fonts --fonts "FreeSans9pt7b" --output ./src/fonts.ts

  # Output to stdout (for piping)
  npx extract-fonts --fonts-dir ./Fonts --fonts "FreeSans9pt7b" > fonts.ts
`);
}

/**
 * Load configuration from file or CLI args
 */
function loadConfig(options) {
  let config = {
    fontsDir: null,
    customFontsDir: null,
    fonts: [],
    output: null
  };

  // Load from config file if provided
  if (options.config) {
    const configPath = path.resolve(process.cwd(), options.config);
    if (!fs.existsSync(configPath)) {
      console.error(`Error: Config file not found: ${configPath}`);
      process.exit(1);
    }
    try {
      const fileConfig = JSON.parse(fs.readFileSync(configPath, 'utf8'));
      config = { ...config, ...fileConfig };
    } catch (e) {
      console.error(`Error parsing config file: ${e.message}`);
      process.exit(1);
    }
  }

  // CLI args override config file
  if (options.fontsDir) config.fontsDir = options.fontsDir;
  if (options.customDir) config.customFontsDir = options.customDir;
  if (options.fonts) config.fonts = options.fonts;
  if (options.output) config.output = options.output;

  // Resolve paths relative to config file or cwd
  const basePath = options.config ? path.dirname(path.resolve(process.cwd(), options.config)) : process.cwd();

  if (config.fontsDir) {
    config.fontsDir = path.resolve(basePath, config.fontsDir);
  }
  if (config.customFontsDir) {
    config.customFontsDir = path.resolve(basePath, config.customFontsDir);
  }
  if (config.output) {
    config.output = path.resolve(basePath, config.output);
  }

  return config;
}

/**
 * Extract font data from a C header file.
 */
function extractFont(fontName, fontsDir, customFontsDir) {
  // Try custom fonts directory first, then library fonts
  let headerPath = null;

  if (customFontsDir) {
    const customPath = path.join(customFontsDir, `${fontName}.h`);
    if (fs.existsSync(customPath)) {
      headerPath = customPath;
    }
  }

  if (!headerPath && fontsDir) {
    const libPath = path.join(fontsDir, `${fontName}.h`);
    if (fs.existsSync(libPath)) {
      headerPath = libPath;
    }
  }

  if (!headerPath) {
    console.error(`Font file not found: ${fontName}`);
    console.error(`  Searched in: ${customFontsDir || '(no custom dir)'}`);
    console.error(`  Searched in: ${fontsDir || '(no fonts dir)'}`);
    return null;
  }

  const content = fs.readFileSync(headerPath, 'utf8');

  // Extract bitmap array
  const bitmapMatch = content.match(/const uint8_t \w+Bitmaps\[\]\s*PROGMEM\s*=\s*\{([^}]+)\}/s);
  if (!bitmapMatch) {
    console.error(`Could not find bitmap array in ${fontName}`);
    return null;
  }

  const bitmapData = bitmapMatch[1]
    .split(',')
    .map(s => s.trim())
    .filter(s => s.match(/^0x[0-9A-Fa-f]+$/))
    .map(s => parseInt(s, 16));

  // Extract glyph array
  const glyphMatch = content.match(/const GFXglyph \w+Glyphs\[\]\s*PROGMEM\s*=\s*\{([\s\S]+?)\};/);
  if (!glyphMatch) {
    console.error(`Could not find glyph array in ${fontName}`);
    return null;
  }

  const glyphLines = glyphMatch[1].match(/\{[^}]+\}/g);
  const glyphs = {};

  glyphLines.forEach((line, index) => {
    // Parse {offset, width, height, xAdvance, xOffset, yOffset}
    const values = line.match(/-?\d+/g);
    if (values && values.length >= 6) {
      const charCode = 0x20 + index; // ASCII starts at space (0x20)
      glyphs[charCode] = {
        offset: parseInt(values[0]),
        width: parseInt(values[1]),
        height: parseInt(values[2]),
        xAdvance: parseInt(values[3]),
        xOffset: parseInt(values[4]),
        yOffset: parseInt(values[5])
      };
    }
  });

  // Extract font metadata (first, last, yAdvance) and actual font variable name
  const fontMatch = content.match(/const GFXfont (\w+)\s*PROGMEM\s*=\s*\{[^,]+,[^,]+,\s*0x([0-9A-Fa-f]+),\s*0x([0-9A-Fa-f]+),\s*(\d+)\s*\}/);
  let actualFontName = fontName;
  let first = 0x20, last = 0x7E, yAdvance = 56;

  if (fontMatch) {
    actualFontName = fontMatch[1];
    first = parseInt(fontMatch[2], 16);
    last = parseInt(fontMatch[3], 16);
    yAdvance = parseInt(fontMatch[4]);
  }

  return {
    name: actualFontName,
    bitmap: bitmapData,
    glyphs: glyphs,
    first: first,
    last: last,
    yAdvance: yAdvance
  };
}

/**
 * Format font data as TypeScript.
 */
function formatAsTypeScript(font) {
  if (!font) return '';

  const lines = [];
  lines.push(`export const ${font.name}: GFXFont = {`);
  lines.push(`  name: '${font.name}',`);

  // Bitmap array (format as hex for readability, 16 values per line)
  lines.push('  bitmap: [');
  for (let i = 0; i < font.bitmap.length; i += 16) {
    const chunk = font.bitmap.slice(i, i + 16);
    const hex = chunk.map(b => '0x' + b.toString(16).padStart(2, '0').toUpperCase()).join(', ');
    const isLast = i + 16 >= font.bitmap.length;
    lines.push(`    ${hex}${isLast ? '' : ','}`);
  }
  lines.push('  ],');

  // Glyphs object
  lines.push('  glyphs: {');
  const charCodes = Object.keys(font.glyphs).map(Number).sort((a, b) => a - b);
  charCodes.forEach((code, idx) => {
    const g = font.glyphs[code];
    const char = String.fromCharCode(code);
    const displayChar = code === 32 ? 'space' : code === 92 ? '\\\\' : char;
    const isLast = idx === charCodes.length - 1;
    lines.push(`    ${code}: { offset: ${g.offset}, width: ${g.width}, height: ${g.height}, xAdvance: ${g.xAdvance}, xOffset: ${g.xOffset}, yOffset: ${g.yOffset} }${isLast ? '' : ','} // '${displayChar}'`);
  });
  lines.push('  },');

  lines.push(`  first: ${font.first},`);
  lines.push(`  last: ${font.last},`);
  lines.push(`  yAdvance: ${font.yAdvance}`);
  lines.push('};');

  return lines.join('\n');
}

/**
 * Generate the complete TypeScript output
 */
function generateOutput(fonts, config) {
  const output = [];

  output.push('/**');
  output.push(' * Auto-generated font data for e-ink simulator');
  output.push(' * Generated by extract-fonts');
  output.push(' * Do not edit manually - regenerate from source header files');
  output.push(' */');
  output.push('');
  output.push("import type { GFXFont } from '../types.js';");
  output.push('');

  const extractedFonts = [];

  for (const fontName of config.fonts) {
    const font = extractFont(fontName, config.fontsDir, config.customFontsDir);
    if (font) {
      output.push(formatAsTypeScript(font));
      output.push('');
      extractedFonts.push(font.name);
      console.error(`Extracted ${fontName}: ${font.bitmap.length} bitmap bytes, ${Object.keys(font.glyphs).length} glyphs`);
    }
  }

  // Export all fonts as a collection
  if (extractedFonts.length > 0) {
    output.push('/** All available fonts */');
    output.push('export const FONTS = {');
    extractedFonts.forEach((name, idx) => {
      const isLast = idx === extractedFonts.length - 1;
      output.push(`  ${name}${isLast ? '' : ','}`);
    });
    output.push('} as const;');
  }

  return output.join('\n');
}

// Main execution
function main() {
  const options = parseArgs();

  if (options.help) {
    showHelp();
    process.exit(0);
  }

  const config = loadConfig(options);

  // Validate configuration
  if (!config.fonts || config.fonts.length === 0) {
    console.error('Error: No fonts specified. Use --fonts or provide a config file.');
    console.error('Run with --help for usage information.');
    process.exit(1);
  }

  if (!config.fontsDir && !config.customFontsDir) {
    console.error('Error: No font directories specified. Use --fonts-dir or --custom-dir.');
    console.error('Run with --help for usage information.');
    process.exit(1);
  }

  const output = generateOutput(config.fonts, config);

  if (config.output) {
    // Ensure output directory exists
    const outputDir = path.dirname(config.output);
    if (!fs.existsSync(outputDir)) {
      fs.mkdirSync(outputDir, { recursive: true });
    }
    fs.writeFileSync(config.output, output);
    console.error(`Output written to ${config.output}`);
  } else {
    // Output to stdout
    console.log(output);
  }
}

main();
