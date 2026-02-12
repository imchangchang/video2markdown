#!/usr/bin/env python3
"""Markdown to PDF Converter

A simple tool to convert Markdown files to PDF.
Uses WeasyPrint for high-quality PDF generation with CSS styling.

Usage:
    python md2pdf.py input.md -o output.pdf
    python md2pdf.py input.md --style github  # Use GitHub-like styling
"""

import argparse
import sys
from pathlib import Path

try:
    import markdown
    from weasyprint import HTML, CSS
except ImportError as e:
    print(f"Error: Missing dependency - {e}")
    print("\nPlease install required packages:")
    print("    pip install markdown weasyprint")
    print("\nOr install from requirements.txt:")
    print("    pip install -r requirements.txt")
    print("\nNote: WeasyPrint may require system dependencies:")
    print("    Ubuntu/Debian: sudo apt-get install libpango-1.0-0 libharfbuzz0b libpangoft2-1.0-0")
    print("    macOS: brew install pango")
    sys.exit(1)


# Default CSS styles
DEFAULT_CSS = """
@page {
    size: A4;
    margin: 2.5cm;
    @bottom-center {
        content: counter(page);
        font-size: 9pt;
        color: #666;
    }
}

body {
    font-family: "Noto Sans CJK SC", "Source Han Sans SC", "WenQuanYi Micro Hei", 
                  "Microsoft YaHei", "PingFang SC", sans-serif;
    font-size: 11pt;
    line-height: 1.8;
    color: #333;
}

h1, h2, h3, h4, h5, h6 {
    font-weight: 600;
    margin-top: 1.5em;
    margin-bottom: 0.5em;
    color: #222;
}

h1 { font-size: 2em; border-bottom: 2px solid #eee; padding-bottom: 0.3em; }
h2 { font-size: 1.5em; border-bottom: 1px solid #eee; padding-bottom: 0.3em; }
h3 { font-size: 1.25em; }
h4 { font-size: 1em; }

p {
    margin: 0.8em 0;
    text-align: justify;
}

a {
    color: #0366d6;
    text-decoration: none;
}

a:hover {
    text-decoration: underline;
}

code {
    background-color: #f6f8fa;
    padding: 0.2em 0.4em;
    border-radius: 3px;
    font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace;
    font-size: 0.9em;
}

pre {
    background-color: #f6f8fa;
    padding: 1em;
    border-radius: 6px;
    overflow-x: auto;
    line-height: 1.45;
}

pre code {
    background: none;
    padding: 0;
}

blockquote {
    border-left: 4px solid #dfe2e5;
    padding-left: 1em;
    margin-left: 0;
    color: #6a737d;
}

img {
    max-width: 100%;
    height: auto;
}

table {
    border-collapse: collapse;
    width: 100%;
    margin: 1em 0;
}

th, td {
    border: 1px solid #dfe2e5;
    padding: 0.6em;
    text-align: left;
}

th {
    background-color: #f6f8fa;
    font-weight: 600;
}

ul, ol {
    padding-left: 2em;
    margin: 0.5em 0;
}

li {
    margin: 0.25em 0;
}

hr {
    border: none;
    border-top: 1px solid #e1e4e8;
    margin: 2em 0;
}
"""

GITHUB_CSS = """
@page {
    size: A4;
    margin: 2cm;
    @bottom-center {
        content: counter(page);
        font-size: 9pt;
        color: #666;
    }
}

body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, 
                  "Noto Sans CJK SC", "Microsoft YaHei", Arial, sans-serif;
    font-size: 16px;
    line-height: 1.6;
    color: #24292e;
    background: white;
}

h1, h2, h3, h4, h5, h6 {
    margin-top: 24px;
    margin-bottom: 16px;
    font-weight: 600;
    line-height: 1.25;
}

h1 { font-size: 2em; border-bottom: 1px solid #eaecef; padding-bottom: 0.3em; }
h2 { font-size: 1.5em; border-bottom: 1px solid #eaecef; padding-bottom: 0.3em; }
h3 { font-size: 1.25em; }
h4 { font-size: 1em; }
h5 { font-size: 0.875em; }
h6 { font-size: 0.85em; color: #6a737d; }

p {
    margin-top: 0;
    margin-bottom: 16px;
}

code {
    background-color: rgba(27, 31, 35, 0.05);
    border-radius: 3px;
    font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace;
    font-size: 85%;
    margin: 0;
    padding: 0.2em 0.4em;
}

pre {
    background-color: #f6f8fa;
    border-radius: 6px;
    font-size: 85%;
    line-height: 1.45;
    overflow: auto;
    padding: 16px;
}

pre code {
    background: transparent;
    border: 0;
    font-size: 100%;
    margin: 0;
    padding: 0;
    word-wrap: normal;
}

blockquote {
    border-left: 0.25em solid #dfe2e5;
    color: #6a737d;
    padding: 0 1em;
    margin: 0 0 16px 0;
}

blockquote > :first-child {
    margin-top: 0;
}

blockquote > :last-child {
    margin-bottom: 0;
}

img {
    border-style: none;
    max-width: 100%;
    box-sizing: border-box;
}

table {
    border-collapse: collapse;
    border-spacing: 0;
    display: block;
    overflow: auto;
    width: 100%;
}

table th, table td {
    border: 1px solid #dfe2e5;
    padding: 6px 13px;
}

table tr {
    background-color: #fff;
    border-top: 1px solid #c6cbd1;
}

table tr:nth-child(2n) {
    background-color: #f6f8fa;
}

ul, ol {
    padding-left: 2em;
    margin-top: 0;
    margin-bottom: 16px;
}

li + li {
    margin-top: 0.25em;
}

hr {
    border: 0;
    border-top: 1px solid #e1e4e8;
    margin: 24px 0;
    height: 0.25em;
    padding: 0;
    background: transparent;
}
"""


def convert_md_to_pdf(
    md_path: Path,
    output_path: Path,
    style: str = "default",
    extra_css: str = ""
) -> Path:
    """Convert Markdown file to PDF.
    
    Args:
        md_path: Path to input Markdown file
        output_path: Path to output PDF file
        style: CSS style name ("default" or "github")
        extra_css: Additional CSS to apply
        
    Returns:
        Path to generated PDF file
    """
    print(f"Reading: {md_path}")
    
    # Read Markdown content
    md_content = md_path.read_text(encoding="utf-8")
    
    # Convert Markdown to HTML
    md = markdown.Markdown(extensions=[
        'tables',
        'fenced_code',
        'toc',
        'nl2br',
    ])
    html_body = md.convert(md_content)
    
    # Wrap in full HTML document
    html_content = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{md_path.stem}</title>
</head>
<body>
{html_body}
</body>
</html>"""
    
    # Select CSS style
    if style == "github":
        base_css = GITHUB_CSS
    else:
        base_css = DEFAULT_CSS
    
    # Add extra CSS if provided
    if extra_css:
        base_css += "\n" + extra_css
    
    print(f"Generating PDF: {output_path}")
    
    # Convert to PDF
    html_doc = HTML(string=html_content, base_url=str(md_path.parent))
    css_doc = CSS(string=base_css)
    
    html_doc.write_pdf(output_path, stylesheets=[css_doc])
    
    print(f"✓ PDF generated: {output_path}")
    print(f"  Size: {output_path.stat().st_size / 1024:.1f} KB")
    
    return output_path


def main():
    parser = argparse.ArgumentParser(
        description="Convert Markdown to PDF",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    %(prog)s document.md                    # Output: document.pdf
    %(prog)s document.md -o output.pdf      # Specify output file
    %(prog)s document.md --style github     # Use GitHub-like styling
    %(prog)s doc.md --css custom.css        # Add custom CSS
        """
    )
    
    parser.add_argument("input", type=Path, help="Input Markdown file")
    parser.add_argument("-o", "--output", type=Path, help="Output PDF file (default: same name as input)")
    parser.add_argument("--style", choices=["default", "github"], default="default",
                        help="CSS style to use (default: default)")
    parser.add_argument("--css", type=Path, help="Path to additional CSS file")
    
    args = parser.parse_args()
    
    # Validate input
    if not args.input.exists():
        print(f"Error: File not found: {args.input}", file=sys.stderr)
        sys.exit(1)
    
    if not args.input.suffix.lower() in ('.md', '.markdown', '.txt'):
        print(f"Warning: Input file extension is {args.input.suffix}, expected .md or .markdown")
    
    # Determine output path
    if args.output:
        output_path = args.output
    else:
        output_path = args.input.with_suffix('.pdf')
    
    # Read extra CSS if provided
    extra_css = ""
    if args.css:
        if not args.css.exists():
            print(f"Error: CSS file not found: {args.css}", file=sys.stderr)
            sys.exit(1)
        extra_css = args.css.read_text(encoding="utf-8")
    
    try:
        convert_md_to_pdf(args.input, output_path, args.style, extra_css)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
