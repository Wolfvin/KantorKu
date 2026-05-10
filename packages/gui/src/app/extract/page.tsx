"use client";

import { useState, useCallback, useMemo } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Code2,
  Paintbrush,
  Layers,
  Search,
  Copy,
  Check,
  ExternalLink,
  AlertCircle,
  Loader2,
  FileCode2,
  FileType,
  Braces,
  ChevronDown,
  ChevronRight,
  Zap,
  ArrowRight,
  Terminal,
  Eye,
  Maximize2,
  Smartphone,
  Monitor,
  Tablet,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import {
  PrismLight as SyntaxHighlighter,
} from "react-syntax-highlighter";
import { oneDark } from "react-syntax-highlighter/dist/esm/styles/prism";

interface ExtractResult {
  url: string;
  title: string;
  html: string;
  cssSources: {
    type: "inline" | "external";
    href?: string;
    content: string;
  }[];
  allCss: string;
  jsSources: {
    type: "inline" | "external";
    href?: string;
    content: string;
  }[];
  allJs: string;
  elements: {
    tag: string;
    count: number;
    hasInlineStyles: boolean;
    attributes: string[];
  }[];
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

function formatBytes(bytes: number): string {
  if (bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + " " + sizes[i];
}

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      const textarea = document.createElement("textarea");
      textarea.value = text;
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand("copy");
      document.body.removeChild(textarea);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  }, [text]);

  return (
    <Button
      variant="ghost"
      size="sm"
      onClick={handleCopy}
      className="h-7 gap-1.5 text-xs text-muted-foreground hover:text-foreground"
    >
      {copied ? (
        <>
          <Check className="size-3" /> Copied!
        </>
      ) : (
        <>
          <Copy className="size-3" /> Copy
        </>
      )}
    </Button>
  );
}

function StatsCard({
  icon: Icon,
  label,
  value,
  color,
}: {
  icon: React.ElementType;
  label: string;
  value: string | number;
  color: string;
}) {
  return (
    <div className="flex items-center gap-3 rounded-lg border bg-card p-3">
      <div
        className="flex size-9 items-center justify-center rounded-md"
        style={{ backgroundColor: `${color}15`, color }}
      >
        <Icon className="size-4" />
      </div>
      <div>
        <p className="text-xs text-muted-foreground">{label}</p>
        <p className="text-sm font-semibold">{value}</p>
      </div>
    </div>
  );
}

function ElementRow({
  element,
}: {
  element: ExtractResult["elements"][0];
}) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div>
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex w-full items-center gap-2 rounded-md px-3 py-2 text-left transition-colors hover:bg-muted/50"
      >
        {element.attributes.length > 0 ? (
          expanded ? (
            <ChevronDown className="size-3.5 shrink-0 text-muted-foreground" />
          ) : (
            <ChevronRight className="size-3.5 shrink-0 text-muted-foreground" />
          )
        ) : (
          <span className="w-3.5" />
        )}
        <code className="min-w-[80px] text-sm font-mono font-medium text-orange-500 dark:text-orange-400">
          &lt;{element.tag}&gt;
        </code>
        <Badge variant="secondary" className="text-xs">
          {element.count}×
        </Badge>
        {element.hasInlineStyles && (
          <Badge
            variant="outline"
            className="border-purple-300 bg-purple-50 text-purple-700 dark:border-purple-700 dark:bg-purple-950/30 dark:text-purple-400"
          >
            inline styles
          </Badge>
        )}
      </button>
      <AnimatePresence>
        {expanded && element.attributes.length > 0 && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.15 }}
            className="overflow-hidden"
          >
            <div className="ml-7 flex flex-wrap gap-1.5 px-3 pb-2">
              {element.attributes.map((attr) => (
                <code
                  key={attr}
                  className="rounded bg-muted px-1.5 py-0.5 text-xs font-mono text-emerald-600 dark:text-emerald-400"
                >
                  {attr}
                </code>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

type PreviewDevice = "desktop" | "tablet" | "mobile";

function PreviewTab({ result }: { result: ExtractResult }) {
  const [device, setDevice] = useState<PreviewDevice>("desktop");

  const deviceWidths: Record<PreviewDevice, string> = {
    desktop: "100%",
    tablet: "768px",
    mobile: "375px",
  };

  const srcDoc = useMemo(() => {
    return result.html;
  }, [result.html]);

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between flex-wrap gap-2">
          <CardTitle className="text-sm font-medium">
            Live Preview
          </CardTitle>
          <div className="flex items-center gap-1">
            <Button
              variant={device === "desktop" ? "default" : "ghost"}
              size="sm"
              className="h-7 gap-1.5 text-xs"
              onClick={() => setDevice("desktop")}
            >
              <Monitor className="size-3.5" />
              Desktop
            </Button>
            <Button
              variant={device === "tablet" ? "default" : "ghost"}
              size="sm"
              className="h-7 gap-1.5 text-xs"
              onClick={() => setDevice("tablet")}
            >
              <Tablet className="size-3.5" />
              Tablet
            </Button>
            <Button
              variant={device === "mobile" ? "default" : "ghost"}
              size="sm"
              className="h-7 gap-1.5 text-xs"
              onClick={() => setDevice("mobile")}
            >
              <Smartphone className="size-3.5" />
              Mobile
            </Button>
          </div>
        </div>
        <p className="text-xs text-muted-foreground">
          Sandboxed preview — some features (scripts, external resources) may be blocked by browser security
        </p>
      </CardHeader>
      <CardContent className="pt-0">
        <div className="flex justify-center rounded-lg border bg-muted/30 p-4">
          <div
            className="transition-all duration-300 ease-in-out"
            style={{ width: deviceWidths[device], maxWidth: "100%" }}
          >
            <div className="rounded-md border bg-white overflow-hidden shadow-sm">
              {/* Browser chrome */}
              <div className="flex items-center gap-2 border-b bg-gray-100 px-3 py-1.5">
                <div className="flex gap-1">
                  <div className="size-2.5 rounded-full bg-red-400" />
                  <div className="size-2.5 rounded-full bg-yellow-400" />
                  <div className="size-2.5 rounded-full bg-green-400" />
                </div>
                <div className="flex-1 mx-2">
                  <div className="rounded bg-white border px-2 py-0.5 text-xs text-muted-foreground font-mono truncate">
                    {result.url}
                  </div>
                </div>
              </div>
              {/* iframe */}
              <iframe
                srcDoc={srcDoc}
                sandbox="allow-same-origin"
                className="w-full border-0"
                style={{
                  height: device === "mobile" ? "667px" : device === "tablet" ? "500px" : "600px",
                }}
                title="Page Preview"
              />
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

export default function Home() {
  const [url, setUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<ExtractResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleExtract = useCallback(async () => {
    if (!url.trim()) return;

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const res = await fetch("/api/extract", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url: url.trim() }),
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.error || "Failed to extract");
      }

      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setLoading(false);
    }
  }, [url]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "Enter" && !loading) {
        handleExtract();
      }
    },
    [handleExtract, loading]
  );

  return (
    <div className="min-h-screen flex flex-col bg-background">
      {/* Header */}
      <header className="border-b bg-card/50 backdrop-blur-sm sticky top-0 z-10">
        <div className="container mx-auto flex items-center gap-3 px-4 py-3">
          <div className="flex size-8 items-center justify-center rounded-lg bg-primary text-primary-foreground">
            <Code2 className="size-4" />
          </div>
          <div>
            <h1 className="text-base font-semibold leading-none">
              Web Source Extractor
            </h1>
            <p className="text-xs text-muted-foreground mt-0.5">
              Extract HTML, CSS, JS & Preview from any webpage
            </p>
          </div>
        </div>
      </header>

      <main className="flex-1 container mx-auto px-4 py-6 max-w-6xl">
        {/* Input Section */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3 }}
        >
          <Card className="border-2 shadow-sm">
            <CardContent className="pt-6">
              <div className="flex flex-col gap-3 sm:flex-row">
                <div className="relative flex-1">
                  <Search className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
                  <Input
                    value={url}
                    onChange={(e) => setUrl(e.target.value)}
                    onKeyDown={handleKeyDown}
                    placeholder="https://example.com"
                    className="pl-9 h-11 text-base"
                    disabled={loading}
                  />
                </div>
                <Button
                  onClick={handleExtract}
                  disabled={loading || !url.trim()}
                  className="h-11 px-6 gap-2 text-base"
                >
                  {loading ? (
                    <>
                      <Loader2 className="size-4 animate-spin" />
                      Extracting...
                    </>
                  ) : (
                    <>
                      <Zap className="size-4" />
                      Extract
                    </>
                  )}
                </Button>
              </div>

              {/* Quick examples */}
              <div className="mt-3 flex flex-wrap gap-2">
                <span className="text-xs text-muted-foreground self-center">
                  Try:
                </span>
                {[
                  "https://example.com",
                  "https://en.wikipedia.org",
                  "https://github.com",
                ].map((example) => (
                  <button
                    key={example}
                    onClick={() => setUrl(example)}
                    className="rounded-md border bg-muted/50 px-2 py-1 text-xs font-mono text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
                  >
                    {example}
                  </button>
                ))}
              </div>
            </CardContent>
          </Card>
        </motion.div>

        {/* Error */}
        <AnimatePresence>
          {error && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className="mt-4"
            >
              <div className="flex items-center gap-2 rounded-lg border border-destructive/50 bg-destructive/5 p-4 text-sm text-destructive">
                <AlertCircle className="size-4 shrink-0" />
                {error}
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Loading Skeleton */}
        <AnimatePresence>
          {loading && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="mt-6 space-y-4"
            >
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                {[1, 2, 3, 4].map((i) => (
                  <div
                    key={i}
                    className="h-20 animate-pulse rounded-lg border bg-muted/50"
                  />
                ))}
              </div>
              <div className="h-8 w-64 animate-pulse rounded-lg bg-muted/50" />
              <div className="h-96 animate-pulse rounded-lg border bg-muted/50" />
            </motion.div>
          )}
        </AnimatePresence>

        {/* Results */}
        <AnimatePresence>
          {result && !loading && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.4, delay: 0.1 }}
              className="mt-6 space-y-5"
            >
              {/* Page Info Bar */}
              <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <div className="flex items-center gap-2">
                  <FileCode2 className="size-4 text-muted-foreground" />
                  <span className="font-semibold text-sm truncate max-w-[300px] sm:max-w-[500px]">
                    {result.title}
                  </span>
                  <a
                    href={result.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
                  >
                    <ExternalLink className="size-3" />
                    Open
                  </a>
                </div>
                {result.meta.description && (
                  <p className="text-xs text-muted-foreground line-clamp-1 max-w-md">
                    {result.meta.description}
                  </p>
                )}
              </div>

              {/* Stats Grid */}
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                <StatsCard
                  icon={Braces}
                  label="Total Elements"
                  value={result.stats.totalElements.toLocaleString()}
                  color="#f97316"
                />
                <StatsCard
                  icon={Layers}
                  label="Unique Tags"
                  value={result.stats.uniqueElements}
                  color="#10b981"
                />
                <StatsCard
                  icon={Paintbrush}
                  label="CSS Sources"
                  value={
                    result.stats.inlineStyleTags +
                    result.stats.externalStylesheets
                  }
                  color="#8b5cf6"
                />
                <StatsCard
                  icon={Terminal}
                  label="JS Sources"
                  value={
                    result.stats.inlineScripts +
                    result.stats.externalScripts
                  }
                  color="#eab308"
                />
              </div>

              {/* Main Tabs */}
              <Tabs defaultValue="preview" className="w-full">
                <div className="w-full overflow-x-auto">
                  <TabsList className="w-full sm:w-auto min-w-max">
                    <TabsTrigger value="preview" className="gap-1.5">
                      <Eye className="size-3.5" />
                      Preview
                    </TabsTrigger>
                    <TabsTrigger value="html" className="gap-1.5">
                      <FileCode2 className="size-3.5" />
                      HTML
                    </TabsTrigger>
                    <TabsTrigger value="css" className="gap-1.5">
                      <Paintbrush className="size-3.5" />
                      CSS
                    </TabsTrigger>
                    <TabsTrigger value="js" className="gap-1.5">
                      <Terminal className="size-3.5" />
                      JS
                    </TabsTrigger>
                    <TabsTrigger value="elements" className="gap-1.5">
                      <Layers className="size-3.5" />
                      Elements
                    </TabsTrigger>
                    <TabsTrigger value="meta" className="gap-1.5">
                      <FileType className="size-3.5" />
                      Meta
                    </TabsTrigger>
                  </TabsList>
                </div>

                {/* Preview Tab */}
                <TabsContent value="preview">
                  <PreviewTab result={result} />
                </TabsContent>

                {/* HTML Tab */}
                <TabsContent value="html">
                  <Card>
                    <CardHeader className="pb-3">
                      <div className="flex items-center justify-between">
                        <CardTitle className="text-sm font-medium">
                          HTML Source Code
                        </CardTitle>
                        <CopyButton text={result.html} />
                      </div>
                      <p className="text-xs text-muted-foreground">
                        {result.html.split("\n").length.toLocaleString()} lines •{" "}
                        {formatBytes(result.stats.htmlSize)}
                      </p>
                    </CardHeader>
                    <CardContent className="pt-0">
                      <ScrollArea className="h-[600px] rounded-md border">
                        <SyntaxHighlighter
                          language="markup"
                          style={oneDark}
                          customStyle={{
                            margin: 0,
                            borderRadius: "0.375rem",
                            fontSize: "0.8125rem",
                            lineHeight: "1.6",
                          }}
                          showLineNumbers
                          wrapLines
                        >
                          {result.html}
                        </SyntaxHighlighter>
                      </ScrollArea>
                    </CardContent>
                  </Card>
                </TabsContent>

                {/* CSS Tab */}
                <TabsContent value="css">
                  <Card>
                    <CardHeader className="pb-3">
                      <div className="flex items-center justify-between">
                        <CardTitle className="text-sm font-medium">
                          All CSS
                        </CardTitle>
                        <CopyButton text={result.allCss} />
                      </div>
                      <p className="text-xs text-muted-foreground">
                        {result.stats.inlineStyleTags} inline{" "}
                        <code className="text-xs">&lt;style&gt;</code> tags •{" "}
                        {result.stats.externalStylesheets} external stylesheets •{" "}
                        {result.stats.inlineStyles} inline styles on elements •{" "}
                        {formatBytes(result.stats.cssSize)}
                      </p>
                    </CardHeader>
                    <CardContent className="pt-0">
                      {result.allCss ? (
                        <ScrollArea className="h-[600px] rounded-md border">
                          <SyntaxHighlighter
                            language="css"
                            style={oneDark}
                            customStyle={{
                              margin: 0,
                              borderRadius: "0.375rem",
                              fontSize: "0.8125rem",
                              lineHeight: "1.6",
                            }}
                            showLineNumbers
                            wrapLines
                          >
                            {result.allCss}
                          </SyntaxHighlighter>
                        </ScrollArea>
                      ) : (
                        <div className="flex flex-col items-center justify-center py-16 text-muted-foreground">
                          <Paintbrush className="size-10 mb-3 opacity-50" />
                          <p className="text-sm">No CSS found on this page</p>
                        </div>
                      )}
                    </CardContent>
                  </Card>

                  {/* CSS Sources Breakdown */}
                  {result.cssSources.length > 0 && (
                    <div className="mt-4 space-y-3">
                      <h3 className="text-sm font-medium">CSS Sources Breakdown</h3>
                      {result.cssSources.map((source, i) => (
                        <Card key={i} className="py-3">
                          <CardHeader className="pb-2 pt-0 px-4">
                            <div className="flex items-center justify-between">
                              <div className="flex items-center gap-2">
                                <Badge
                                  variant={
                                    source.type === "inline"
                                      ? "default"
                                      : "secondary"
                                  }
                                  className="text-xs"
                                >
                                  {source.type === "inline"
                                    ? "Inline <style>"
                                    : "External"}
                                </Badge>
                                {source.href && (
                                  <a
                                    href={source.href}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="text-xs text-muted-foreground hover:text-foreground truncate max-w-[400px] transition-colors"
                                  >
                                    {source.href}
                                  </a>
                                )}
                              </div>
                              <CopyButton text={source.content} />
                            </div>
                          </CardHeader>
                          <CardContent className="pt-0 px-4">
                            <ScrollArea className="max-h-[300px] rounded-md border">
                              <SyntaxHighlighter
                                language="css"
                                style={oneDark}
                                customStyle={{
                                  margin: 0,
                                  borderRadius: "0.375rem",
                                  fontSize: "0.75rem",
                                  lineHeight: "1.5",
                                }}
                                wrapLines
                              >
                                {source.content}
                              </SyntaxHighlighter>
                            </ScrollArea>
                          </CardContent>
                        </Card>
                      ))}
                    </div>
                  )}
                </TabsContent>

                {/* JS Tab */}
                <TabsContent value="js">
                  <Card>
                    <CardHeader className="pb-3">
                      <div className="flex items-center justify-between">
                        <CardTitle className="text-sm font-medium">
                          All JavaScript
                        </CardTitle>
                        <CopyButton text={result.allJs} />
                      </div>
                      <p className="text-xs text-muted-foreground">
                        {result.stats.inlineScripts} inline{" "}
                        <code className="text-xs">&lt;script&gt;</code> tags •{" "}
                        {result.stats.externalScripts} external scripts •{" "}
                        {formatBytes(result.stats.jsSize)}
                      </p>
                    </CardHeader>
                    <CardContent className="pt-0">
                      {result.allJs ? (
                        <ScrollArea className="h-[600px] rounded-md border">
                          <SyntaxHighlighter
                            language="javascript"
                            style={oneDark}
                            customStyle={{
                              margin: 0,
                              borderRadius: "0.375rem",
                              fontSize: "0.8125rem",
                              lineHeight: "1.6",
                            }}
                            showLineNumbers
                            wrapLines
                          >
                            {result.allJs}
                          </SyntaxHighlighter>
                        </ScrollArea>
                      ) : (
                        <div className="flex flex-col items-center justify-center py-16 text-muted-foreground">
                          <Terminal className="size-10 mb-3 opacity-50" />
                          <p className="text-sm">No JavaScript found on this page</p>
                        </div>
                      )}
                    </CardContent>
                  </Card>

                  {/* JS Sources Breakdown */}
                  {result.jsSources.length > 0 && (
                    <div className="mt-4 space-y-3">
                      <h3 className="text-sm font-medium">JS Sources Breakdown</h3>
                      {result.jsSources.map((source, i) => (
                        <Card key={i} className="py-3">
                          <CardHeader className="pb-2 pt-0 px-4">
                            <div className="flex items-center justify-between">
                              <div className="flex items-center gap-2">
                                <Badge
                                  variant={
                                    source.type === "inline"
                                      ? "default"
                                      : "secondary"
                                  }
                                  className="text-xs"
                                >
                                  {source.type === "inline"
                                    ? "Inline <script>"
                                    : "External"}
                                </Badge>
                                {source.href && (
                                  <a
                                    href={source.href}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="text-xs text-muted-foreground hover:text-foreground truncate max-w-[400px] transition-colors"
                                  >
                                    {source.href}
                                  </a>
                                )}
                              </div>
                              <CopyButton text={source.content} />
                            </div>
                          </CardHeader>
                          <CardContent className="pt-0 px-4">
                            <ScrollArea className="max-h-[300px] rounded-md border">
                              <SyntaxHighlighter
                                language="javascript"
                                style={oneDark}
                                customStyle={{
                                  margin: 0,
                                  borderRadius: "0.375rem",
                                  fontSize: "0.75rem",
                                  lineHeight: "1.5",
                                }}
                                wrapLines
                              >
                                {source.content}
                              </SyntaxHighlighter>
                            </ScrollArea>
                          </CardContent>
                        </Card>
                      ))}
                    </div>
                  )}
                </TabsContent>

                {/* Elements Tab */}
                <TabsContent value="elements">
                  <Card>
                    <CardHeader className="pb-3">
                      <div className="flex items-center justify-between">
                        <CardTitle className="text-sm font-medium">
                          HTML Elements Map
                        </CardTitle>
                      </div>
                      <p className="text-xs text-muted-foreground">
                        {result.stats.uniqueElements} unique tags •{" "}
                        {result.stats.totalElements.toLocaleString()} total
                        elements • {result.stats.inlineStyles} with inline styles
                      </p>
                    </CardHeader>
                    <CardContent className="pt-0">
                      <ScrollArea className="h-[600px] rounded-md border">
                        <div className="divide-y">
                          {result.elements.map((element) => (
                            <ElementRow
                              key={element.tag}
                              element={element}
                            />
                          ))}
                        </div>
                      </ScrollArea>
                    </CardContent>
                  </Card>
                </TabsContent>

                {/* Meta Tab */}
                <TabsContent value="meta">
                  <Card>
                    <CardHeader className="pb-3">
                      <CardTitle className="text-sm font-medium">
                        Page Metadata
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="pt-0">
                      <div className="space-y-4">
                        {[
                          { label: "Title", value: result.title },
                          { label: "URL", value: result.url },
                          {
                            label: "Description",
                            value: result.meta.description,
                          },
                          { label: "Keywords", value: result.meta.keywords },
                          { label: "Author", value: result.meta.author },
                          { label: "Viewport", value: result.meta.viewport },
                          { label: "Charset", value: result.meta.charset },
                        ]
                          .filter((item) => item.value)
                          .map((item) => (
                            <div key={item.label}>
                              <label className="text-xs font-medium text-muted-foreground">
                                {item.label}
                              </label>
                              <p className="mt-0.5 text-sm break-all">
                                {item.value}
                              </p>
                              <Separator className="mt-3" />
                            </div>
                          ))}

                        {/* Stats section */}
                        <div>
                          <label className="text-xs font-medium text-muted-foreground">
                            Size Breakdown
                          </label>
                          <div className="mt-2 grid grid-cols-3 gap-3">
                            <div className="rounded-lg border p-3 text-center">
                              <FileCode2 className="size-4 mx-auto mb-1 text-orange-500" />
                              <p className="text-xs text-muted-foreground">HTML</p>
                              <p className="text-sm font-semibold">{formatBytes(result.stats.htmlSize)}</p>
                            </div>
                            <div className="rounded-lg border p-3 text-center">
                              <Paintbrush className="size-4 mx-auto mb-1 text-purple-500" />
                              <p className="text-xs text-muted-foreground">CSS</p>
                              <p className="text-sm font-semibold">{formatBytes(result.stats.cssSize)}</p>
                            </div>
                            <div className="rounded-lg border p-3 text-center">
                              <Terminal className="size-4 mx-auto mb-1 text-yellow-500" />
                              <p className="text-xs text-muted-foreground">JS</p>
                              <p className="text-sm font-semibold">{formatBytes(result.stats.jsSize)}</p>
                            </div>
                          </div>
                        </div>

                        {/* Raw meta as code */}
                        <div>
                          <label className="text-xs font-medium text-muted-foreground">
                            Raw Meta JSON
                          </label>
                          <div className="mt-1 rounded-md border">
                            <SyntaxHighlighter
                              language="json"
                              style={oneDark}
                              customStyle={{
                                margin: 0,
                                borderRadius: "0.375rem",
                                fontSize: "0.75rem",
                              }}
                            >
                              {JSON.stringify(
                                { meta: result.meta, stats: result.stats },
                                null,
                                2
                              )}
                            </SyntaxHighlighter>
                          </div>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                </TabsContent>
              </Tabs>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Empty State */}
        {!result && !loading && !error && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.2 }}
            className="mt-20 flex flex-col items-center text-center"
          >
            <div className="flex size-16 items-center justify-center rounded-2xl bg-muted">
              <Code2 className="size-8 text-muted-foreground" />
            </div>
            <h2 className="mt-4 text-lg font-semibold">
              Paste a URL to get started
            </h2>
            <p className="mt-1 max-w-sm text-sm text-muted-foreground">
              Extract the full HTML source code, CSS stylesheets, JavaScript,
              and preview any website. Perfect for studying how websites are built.
            </p>
            <div className="mt-6 flex flex-col items-center gap-3 text-sm text-muted-foreground">
              <div className="flex items-center gap-2">
                <ArrowRight className="size-3.5" />
                <span>Live page preview with device switching</span>
              </div>
              <div className="flex items-center gap-2">
                <ArrowRight className="size-3.5" />
                <span>Full HTML source with syntax highlighting</span>
              </div>
              <div className="flex items-center gap-2">
                <ArrowRight className="size-3.5" />
                <span>All CSS — inline, embedded & external stylesheets</span>
              </div>
              <div className="flex items-center gap-2">
                <ArrowRight className="size-3.5" />
                <span>All JS — inline & external script sources</span>
              </div>
              <div className="flex items-center gap-2">
                <ArrowRight className="size-3.5" />
                <span>Element map with tag counts & attributes</span>
              </div>
              <div className="flex items-center gap-2">
                <ArrowRight className="size-3.5" />
                <span>Page metadata & size statistics</span>
              </div>
            </div>
          </motion.div>
        )}
      </main>

      {/* Footer */}
      <footer className="border-t mt-auto">
        <div className="container mx-auto px-4 py-4">
          <p className="text-center text-xs text-muted-foreground">
            Web Source Extractor — Study how websites are built, one page at a
            time.
          </p>
        </div>
      </footer>
    </div>
  );
}
