import { NextRequest, NextResponse } from "next/server";

interface ExtractedElement {
  tag: string;
  count: number;
  hasInlineStyles: boolean;
  attributes: string[];
}

interface CSSSource {
  type: "inline" | "external";
  href?: string;
  content: string;
}

interface JSSource {
  type: "inline" | "external";
  href?: string;
  content: string;
}

interface ExtractResult {
  url: string;
  title: string;
  html: string;
  cssSources: CSSSource[];
  allCss: string;
  jsSources: JSSource[];
  allJs: string;
  elements: ExtractedElement[];
  meta: {
    description?: string;
    keywords?: string;
    author?: string;
    viewport?: string;
    charset?: string;
  };
  stats: {
    totalElements: number;
    uniqueElements: number;
    inlineStyles: number;
    externalStylesheets: number;
    inlineStyleTags: number;
    inlineScripts: number;
    externalScripts: number;
    htmlSize: number;
    cssSize: number;
    jsSize: number;
  };
}

function resolveUrl(base: string, relative: string): string {
  try {
    return new URL(relative, base).href;
  } catch {
    return relative;
  }
}

function extractElements(html: string): ExtractedElement[] {
  const elementMap = new Map<
    string,
    { count: number; hasInlineStyles: boolean; attributes: Set<string> }
  >();

  const tagRegex = /<([a-zA-Z][a-zA-Z0-9]*)\b([^>]*)\/?>/g;
  let match;

  while ((match = tagRegex.exec(html)) !== null) {
    const tag = match[1].toLowerCase();
    const attrs = match[2];

    const existing = elementMap.get(tag) || {
      count: 0,
      hasInlineStyles: false,
      attributes: new Set<string>(),
    };

    existing.count++;

    if (/style\s*=/i.test(attrs)) {
      existing.hasInlineStyles = true;
    }

    const attrRegex = /\b([a-zA-Z][a-zA-Z0-9-]*)\s*=/g;
    let attrMatch;
    while ((attrMatch = attrRegex.exec(attrs)) !== null) {
      existing.attributes.add(attrMatch[1].toLowerCase());
    }

    elementMap.set(tag, existing);
  }

  return Array.from(elementMap.entries())
    .map(([tag, data]) => ({
      tag,
      count: data.count,
      hasInlineStyles: data.hasInlineStyles,
      attributes: Array.from(data.attributes).sort(),
    }))
    .sort((a, b) => b.count - a.count);
}

function extractInlineStyles(html: string): CSSSource[] {
  const sources: CSSSource[] = [];
  const styleRegex = /<style[^>]*>([\s\S]*?)<\/style>/gi;
  let match;

  while ((match = styleRegex.exec(html)) !== null) {
    const content = match[1].trim();
    if (content) {
      sources.push({
        type: "inline",
        content,
      });
    }
  }

  return sources;
}

function extractStylesheetLinks(html: string, baseUrl: string): string[] {
  const links: string[] = [];
  const linkRegex = /<link\b[^>]*rel\s*=\s*["']stylesheet["'][^>]*>/gi;
  let match;

  while ((match = linkRegex.exec(html)) !== null) {
    const linkTag = match[0];
    const hrefMatch = linkTag.match(/href\s*=\s*["']([^"']+)["']/i);
    if (hrefMatch) {
      links.push(resolveUrl(baseUrl, hrefMatch[1]));
    }
  }

  return links;
}

function extractInlineScripts(html: string): JSSource[] {
  const sources: JSSource[] = [];
  // Match <script> tags that are NOT external (no src attribute) and have content
  const scriptRegex = /<script\b(?![^>]*\bsrc\s*=)([^>]*)>([\s\S]*?)<\/script>/gi;
  let match;

  while ((match = scriptRegex.exec(html)) !== null) {
    const attrs = match[1];
    const content = match[2].trim();
    if (content) {
      // Detect type attribute
      const typeMatch = attrs.match(/type\s*=\s*["']([^"']+)["']/i);
      const scriptType = typeMatch ? typeMatch[1] : "text/javascript";

      // Skip non-JS types like application/json, text/template, etc.
      if (
        scriptType.includes("json") ||
        scriptType.includes("template") ||
        scriptType.includes("html")
      ) {
        continue;
      }

      sources.push({
        type: "inline",
        content,
      });
    }
  }

  return sources;
}

function extractExternalScriptLinks(html: string, baseUrl: string): string[] {
  const links: string[] = [];
  const scriptRegex = /<script\b[^>]*\bsrc\s*=\s*["']([^"']+)["'][^>]*>/gi;
  let match;

  while ((match = scriptRegex.exec(html)) !== null) {
    const src = match[1];
    links.push(resolveUrl(baseUrl, src));
  }

  return links;
}

function extractMeta(html: string): ExtractResult["meta"] {
  const meta: ExtractResult["meta"] = {};

  const descMatch = html.match(
    /<meta\s+name\s*=\s*["']description["']\s+content\s*=\s*["']([^"']+)["']/i
  );
  if (descMatch) meta.description = descMatch[1];

  const kwMatch = html.match(
    /<meta\s+name\s*=\s*["']keywords["']\s+content\s*=\s*["']([^"']+)["']/i
  );
  if (kwMatch) meta.keywords = kwMatch[1];

  const authorMatch = html.match(
    /<meta\s+name\s*=\s*["']author["']\s+content\s*=\s*["']([^"']+)["']/i
  );
  if (authorMatch) meta.author = authorMatch[1];

  const vpMatch = html.match(
    /<meta\s+name\s*=\s*["']viewport["']\s+content\s*=\s*["']([^"']+)["']/i
  );
  if (vpMatch) meta.viewport = vpMatch[1];

  const charsetMatch = html.match(/<meta\s+charset\s*=\s*["']([^"']+)["']/i);
  if (charsetMatch) meta.charset = charsetMatch[1];

  return meta;
}

function extractTitle(html: string): string {
  const titleMatch = html.match(/<title[^>]*>([\s\S]*?)<\/title>/i);
  return titleMatch ? titleMatch[1].trim() : "Untitled";
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { url } = body;

    if (!url || typeof url !== "string") {
      return NextResponse.json(
        { error: "URL is required" },
        { status: 400 }
      );
    }

    let parsedUrl: URL;
    try {
      parsedUrl = new URL(url);
    } catch {
      return NextResponse.json(
        { error: "Invalid URL format" },
        { status: 400 }
      );
    }

    if (!["http:", "https:"].includes(parsedUrl.protocol)) {
      return NextResponse.json(
        { error: "Only HTTP and HTTPS URLs are supported" },
        { status: 400 }
      );
    }

    const response = await fetch(url, {
      headers: {
        "User-Agent":
          "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        Accept:
          "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
      },
      signal: AbortSignal.timeout(15000),
    });

    if (!response.ok) {
      return NextResponse.json(
        { error: `Failed to fetch URL: HTTP ${response.status}` },
        { status: 422 }
      );
    }

    const html = await response.text();
    const baseUrl = parsedUrl.href;

    const title = extractTitle(html);
    const elements = extractElements(html);
    const inlineCssSources = extractInlineStyles(html);
    const meta = extractMeta(html);
    const stylesheetLinks = extractStylesheetLinks(html, baseUrl);

    // JS extraction
    const inlineJsSources = extractInlineScripts(html);
    const externalScriptLinks = extractExternalScriptLinks(html, baseUrl);

    // Fetch external CSS
    const externalCssSources: CSSSource[] = [];
    for (const href of stylesheetLinks) {
      try {
        const cssResponse = await fetch(href, {
          headers: {
            "User-Agent":
              "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
          },
          signal: AbortSignal.timeout(10000),
        });
        if (cssResponse.ok) {
          const content = await cssResponse.text();
          externalCssSources.push({
            type: "external",
            href,
            content,
          });
        }
      } catch {
        externalCssSources.push({
          type: "external",
          href,
          content: `/* Failed to fetch: ${href} */`,
        });
      }
    }

    // Fetch external JS
    const externalJsSources: JSSource[] = [];
    for (const href of externalScriptLinks) {
      try {
        const jsResponse = await fetch(href, {
          headers: {
            "User-Agent":
              "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
          },
          signal: AbortSignal.timeout(10000),
        });
        if (jsResponse.ok) {
          const content = await jsResponse.text();
          externalJsSources.push({
            type: "external",
            href,
            content,
          });
        }
      } catch {
        externalJsSources.push({
          type: "external",
          href,
          content: `// Failed to fetch: ${href}`,
        });
      }
    }

    const allCssSources = [...inlineCssSources, ...externalCssSources];
    const allCss = allCssSources
      .map((s) => {
        if (s.type === "external" && s.href) {
          return `/* ===== External: ${s.href} ===== */\n${s.content}`;
        }
        return `/* ===== Inline <style> ===== */\n${s.content}`;
      })
      .join("\n\n");

    const allJsSources = [...inlineJsSources, ...externalJsSources];
    const allJs = allJsSources
      .map((s) => {
        if (s.type === "external" && s.href) {
          return `// ===== External: ${s.href} =====\n${s.content}`;
        }
        return `// ===== Inline <script> =====\n${s.content}`;
      })
      .join("\n\n");

    const inlineStyleMatches = html.match(/style\s*=\s*["'][^"']*["']/gi);
    const inlineStylesCount = inlineStyleMatches
      ? inlineStyleMatches.length
      : 0;

    const result: ExtractResult = {
      url: baseUrl,
      title,
      html,
      cssSources: allCssSources,
      allCss,
      jsSources: allJsSources,
      allJs,
      elements,
      meta,
      stats: {
        totalElements: elements.reduce((sum, el) => sum + el.count, 0),
        uniqueElements: elements.length,
        inlineStyles: inlineStylesCount,
        externalStylesheets: stylesheetLinks.length,
        inlineStyleTags: inlineCssSources.length,
        inlineScripts: inlineJsSources.length,
        externalScripts: externalScriptLinks.length,
        htmlSize: new Blob([html]).size,
        cssSize: new Blob([allCss]).size,
        jsSize: new Blob([allJs]).size,
      },
    };

    return NextResponse.json(result);
  } catch (error) {
    console.error("Extract error:", error);
    const message =
      error instanceof Error ? error.message : "Internal server error";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
