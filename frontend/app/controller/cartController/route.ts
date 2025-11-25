import { NextRequest, NextResponse } from 'next/server';
import fs from 'fs';
import path from 'path';
import { marked } from 'marked';
import sanitizeHtml from 'sanitize-html';

export async function GET(request: NextRequest) {
  try {
    // Path to the cart.md file (relative to the project root)
    const filePath = path.join(process.cwd(), '..', 'privacy', 'cart.md');

    // Read the markdown file
    const fileContent = fs.readFileSync(filePath, 'utf8');

    // Convert markdown to HTML
    const htmlContent = await marked.parse(fileContent);

    // Sanitize the HTML to prevent XSS
    const sanitizedHtml = sanitizeHtml(htmlContent, {
      allowedTags: ['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'br', 'strong', 'em', 'ul', 'ol', 'li', 'a'],
      allowedAttributes: {
        'a': ['href', 'target']
      }
    });

    return NextResponse.json({
      html: sanitizedHtml
    });
  } catch (error) {
    console.error('Error reading cart.md:', error);
    return NextResponse.json(
      { error: 'Failed to load cart information' },
      { status: 500 }
    );
  }
}