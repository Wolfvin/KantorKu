'use client';

import { useMemo, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { useKantorkuStore } from '@/lib/kantorku/store';
import { DAGNode, DAGEdge, TodoItem } from '@/lib/kantorku/types';
import { GitBranch, Circle, CheckCircle2, XCircle, AlertTriangle, Clock, ArrowDown, Zap, ZoomIn, ZoomOut, Layers, AlertCircle } from 'lucide-react';

const STATUS_STYLES: Record<string, { color: string; border: string; bg: string; icon: string; text: string }> = {
  pending: { color: '#64748b', border: '#64748b40', bg: '#64748b10', icon: '⏳', text: 'Pending' },
  in_progress: { color: '#06b6d4', border: '#06b6d440', bg: '#06b6d410', icon: '⚡', text: 'In Progress' },
  done: { color: '#22c55e', border: '#22c55e40', bg: '#22c55e10', icon: '✅', text: 'Done' },
  failed: { color: '#ef4444', border: '#ef444440', bg: '#ef444410', icon: '❌', text: 'Failed' },
  blocked: { color: '#f59e0b', border: '#f59e0b40', bg: '#f59e0b10', icon: '🚫', text: 'Blocked' },
};

const EDGE_TYPE_COLORS: Record<string, string> = {
  depends_on: '#06b6d4',
  delegates_to: '#f59e0b',
  verifies: '#22c55e',
};

function StatusIcon({ status }: { status: string }) {
  const style = STATUS_STYLES[status] || STATUS_STYLES.pending;
  switch (status) {
    case 'in_progress':
      return <Zap className="h-3 w-3" style={{ color: style.color }} />;
    case 'done':
      return <CheckCircle2 className="h-3 w-3" style={{ color: style.color }} />;
    case 'failed':
      return <XCircle className="h-3 w-3" style={{ color: style.color }} />;
    case 'blocked':
      return <AlertTriangle className="h-3 w-3" style={{ color: style.color }} />;
    default:
      return <Clock className="h-3 w-3" style={{ color: style.color }} />;
  }
}

// Compute critical path (longest dependency chain)
function computeCriticalPath(nodes: DAGNode[], edges: DAGEdge[]): Set<string> {
  const nodeMap = new Map(nodes.map((n) => [n.id, n]));
  const adjList = new Map<string, string[]>();
  const inDegree = new Map<string, number>();

  nodes.forEach((n) => {
    adjList.set(n.id, []);
    inDegree.set(n.id, 0);
  });

  edges.forEach((e) => {
    if (nodeMap.has(e.from) && nodeMap.has(e.to)) {
      adjList.get(e.from)!.push(e.to);
      inDegree.set(e.to, (inDegree.get(e.to) || 0) + 1);
    }
  });

  // Topological sort with longest path tracking
  const longestPath = new Map<string, number>();
  const parent = new Map<string, string | null>();
  const queue: string[] = [];

  nodes.forEach((n) => {
    longestPath.set(n.id, 0);
    parent.set(n.id, null);
    if ((inDegree.get(n.id) || 0) === 0) {
      queue.push(n.id);
    }
  });

  let endNode = '';
  let maxLen = 0;
  const processed: string[] = [];

  while (queue.length > 0) {
    const curr = queue.shift()!;
    processed.push(curr);
    const currLen = longestPath.get(curr) || 0;
    if (currLen > maxLen) {
      maxLen = currLen;
      endNode = curr;
    }

    for (const next of adjList.get(curr) || []) {
      const newLen = currLen + 1;
      if (newLen > (longestPath.get(next) || 0)) {
        longestPath.set(next, newLen);
        parent.set(next, curr);
      }
      const newDeg = (inDegree.get(next) || 1) - 1;
      inDegree.set(next, newDeg);
      if (newDeg === 0) queue.push(next);
    }
  }

  // Trace back from endNode
  const criticalPath = new Set<string>();
  let current: string | null = endNode;
  while (current) {
    criticalPath.add(current);
    current = parent.get(current) ?? null;
  }

  return criticalPath;
}

export function DAGVisualizationPanel() {
  const { dagNodes, dagEdges, contract } = useKantorkuStore();
  const [expandedNode, setExpandedNode] = useState<string | null>(null);
  const [zoom, setZoom] = useState(1);

  // Build visualization from DAG if available, otherwise from contract todos
  const { nodes, edges } = useMemo(() => {
    if (dagNodes.length > 0) {
      return { nodes: dagNodes, edges: dagEdges };
    }
    // Fallback: build from contract todos
    if (contract && contract.todos.length > 0) {
      const todoNodes: DAGNode[] = contract.todos.map((todo: TodoItem, idx: number) => ({
        id: todo.id,
        label: todo.description,
        status: todo.status,
        assigned_to: todo.assigned_to,
        depth: idx,
      }));
      const todoEdges: DAGEdge[] = [];
      contract.todos.forEach((todo: TodoItem) => {
        todo.depends_on.forEach((depId: string) => {
          todoEdges.push({
            from: depId,
            to: todo.id,
            type: 'depends_on',
          });
        });
      });
      // Calculate depth based on dependencies
      const depthMap = new Map<string, number>();
      const calcDepth = (id: string): number => {
        if (depthMap.has(id)) return depthMap.get(id)!;
        const todo = contract.todos.find((t: TodoItem) => t.id === id);
        if (!todo || todo.depends_on.length === 0) {
          depthMap.set(id, 0);
          return 0;
        }
        const maxDep = Math.max(...todo.depends_on.map(calcDepth));
        depthMap.set(id, maxDep + 1);
        return maxDep + 1;
      };
      contract.todos.forEach((t: TodoItem) => calcDepth(t.id));
      todoNodes.forEach((n) => {
        n.depth = depthMap.get(n.id) || 0;
      });
      return { nodes: todoNodes, edges: todoEdges };
    }
    return { nodes: [], edges: [] };
  }, [dagNodes, dagEdges, contract]);

  // Group nodes by depth level
  const depthGroups = useMemo(() => {
    const groups: Map<number, DAGNode[]> = new Map();
    nodes.forEach((node) => {
      const depth = node.depth || 0;
      if (!groups.has(depth)) groups.set(depth, []);
      groups.get(depth)!.push(node);
    });
    return Array.from(groups.entries()).sort(([a], [b]) => a - b);
  }, [nodes]);

  // Build edge lookup for quick access
  const incomingEdges = useMemo(() => {
    const map: Map<string, DAGEdge[]> = new Map();
    edges.forEach((edge) => {
      if (!map.has(edge.to)) map.set(edge.to, []);
      map.get(edge.to)!.push(edge);
    });
    return map;
  }, [edges]);

  // Outgoing edges lookup
  const outgoingEdges = useMemo(() => {
    const map: Map<string, DAGEdge[]> = new Map();
    edges.forEach((edge) => {
      if (!map.has(edge.from)) map.set(edge.from, []);
      map.get(edge.from)!.push(edge);
    });
    return map;
  }, [edges]);

  // Critical path
  const criticalPath = useMemo(() => computeCriticalPath(nodes, edges), [nodes, edges]);

  // Status counts
  const statusCounts = useMemo(() => {
    const counts: Record<string, number> = {};
    nodes.forEach((n) => {
      counts[n.status] = (counts[n.status] || 0) + 1;
    });
    return counts;
  }, [nodes]);

  // Find todo details from contract
  const getTodoDetails = (nodeId: string) => {
    if (!contract) return null;
    return contract.todos.find((t) => t.id === nodeId) || null;
  };

  // Edge label lookup
  const edgeLabels = useMemo(() => {
    const labels: Map<string, DAGEdge> = new Map();
    edges.forEach((e) => {
      labels.set(`${e.from}->${e.to}`, e);
    });
    return labels;
  }, [edges]);

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Header */}
      <div className="flex-shrink-0 px-3 py-2 border-b border-slate-700/30 bg-slate-900/40">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-1.5">
            <GitBranch className="h-3.5 w-3.5 text-teal-400" />
            <span className="text-[10px] font-mono text-slate-400 uppercase">Task Dependency Graph</span>
            <Badge variant="outline" className="text-[8px] px-1 py-0 h-3.5 border-teal-500/30 text-teal-300 font-mono">
              {nodes.length} nodes
            </Badge>
          </div>
          {/* Zoom controls */}
          <div className="flex items-center gap-1">
            <Badge variant="outline" className="text-[8px] px-1 py-0 h-3.5 border-amber-500/30 text-amber-300 font-mono">
              🔥 {criticalPath.size} critical
            </Badge>
            <div className="flex items-center gap-0.5 border border-slate-700/50 rounded">
              <Button
                variant="ghost"
                size="sm"
                className="h-5 w-5 p-0 text-slate-500 hover:text-cyan-400"
                onClick={() => setZoom(Math.max(0.5, zoom - 0.1))}
              >
                <ZoomOut className="h-3 w-3" />
              </Button>
              <span className="text-[8px] text-slate-500 font-mono w-8 text-center">{(zoom * 100).toFixed(0)}%</span>
              <Button
                variant="ghost"
                size="sm"
                className="h-5 w-5 p-0 text-slate-500 hover:text-cyan-400"
                onClick={() => setZoom(Math.min(1.5, zoom + 0.1))}
              >
                <ZoomIn className="h-3 w-3" />
              </Button>
            </div>
          </div>
        </div>
        {/* Status summary */}
        {nodes.length > 0 && (
          <div className="flex items-center gap-2 mt-1.5">
            {Object.entries(statusCounts).map(([status, count]) => {
              const style = STATUS_STYLES[status] || STATUS_STYLES.pending;
              return (
                <Badge
                  key={status}
                  variant="outline"
                  className="text-[8px] px-1.5 py-0 h-4 font-mono"
                  style={{
                    borderColor: style.border,
                    color: style.color,
                    backgroundColor: style.bg,
                  }}
                >
                  {style.icon} {count} {style.text.toLowerCase()}
                </Badge>
              );
            })}
          </div>
        )}
      </div>

      {/* Graph Content */}
      <div className="flex-1 overflow-y-auto custom-scrollbar px-3 py-2 space-y-1">
        {nodes.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-slate-500">
            <GitBranch className="h-8 w-8 text-slate-600/50 mb-2" />
            <p className="text-[10px] text-center text-slate-600">
              No task graph available.<br />
              Start a contract to see dependencies.
            </p>
          </div>
        ) : (
          <div className="space-y-3 origin-top-left transition-transform duration-200" style={{ transform: `scale(${zoom})`, transformOrigin: 'top left' }}>
            {depthGroups.map(([depth, groupNodes]) => {
              const isParallel = groupNodes.length > 1;
              return (
                <div key={depth}>
                  {/* Depth Level Label */}
                  <div className="flex items-center gap-2 mb-1.5">
                    <div className="h-5 px-1.5 rounded bg-slate-800/60 border border-slate-700/30 flex items-center gap-1">
                      <span className="text-[9px] font-mono text-cyan-400">Depth {depth}</span>
                    </div>
                    {isParallel && (
                      <Badge variant="outline" className="text-[7px] px-1 py-0 h-3 border-violet-500/30 text-violet-300 font-mono">
                        <Layers className="h-2 w-2 mr-0.5" />
                        {groupNodes.length} parallel
                      </Badge>
                    )}
                    {depth > 0 && (
                      <div className="flex items-center gap-0.5 flex-1">
                        <div className="h-px flex-1 bg-slate-700/30" />
                        <ArrowDown className="h-3 w-3 text-slate-600" />
                      </div>
                    )}
                  </div>

                  {/* Edge labels between depths */}
                  {depth > 0 && (
                    <div className="ml-4 mb-1 flex flex-wrap gap-1">
                      {groupNodes.map((node) => {
                        const deps = incomingEdges.get(node.id) || [];
                        return deps.map((dep) => {
                          const edgeKey = `${dep.from}->${dep.to}`;
                          const edge = edgeLabels.get(edgeKey);
                          if (!edge) return null;
                          const color = EDGE_TYPE_COLORS[edge.type] || '#94a3b8';
                          return (
                            <div key={edgeKey} className="flex items-center gap-0.5">
                              <div className="h-0.5 w-3 rounded" style={{ backgroundColor: color }} />
                              <span className="text-[7px] font-mono" style={{ color }}>
                                {dep.from} → {dep.type}
                              </span>
                            </div>
                          );
                        });
                      })}
                    </div>
                  )}

                  {/* Nodes at this depth */}
                  <div className={`grid gap-1.5 ml-2 ${isParallel ? 'grid-cols-2' : ''}`}>
                    {groupNodes.map((node) => {
                      const style = STATUS_STYLES[node.status] || STATUS_STYLES.pending;
                      const deps = incomingEdges.get(node.id) || [];
                      const isCritical = criticalPath.has(node.id);
                      const isExpanded = expandedNode === node.id;
                      const todoDetails = getTodoDetails(node.id);

                      return (
                        <Card
                          key={node.id}
                          className={`bg-slate-800/40 backdrop-blur-sm transition-all duration-200 cursor-pointer ${
                            isCritical
                              ? 'border-amber-500/50 border-2 shadow-[0_0_8px_rgba(245,158,11,0.15)]'
                              : 'border-slate-700/20 hover:border-slate-600/50'
                          }`}
                          style={{
                            borderLeftWidth: '3px',
                            borderLeftColor: isCritical ? '#f59e0b' : style.color,
                          }}
                          onClick={() => setExpandedNode(isExpanded ? null : node.id)}
                        >
                          <CardContent className="p-2">
                            <div className="flex items-start gap-2">
                              <StatusIcon status={node.status} />
                              <div className="flex-1 min-w-0">
                                <div className="flex items-center gap-1.5 mb-0.5">
                                  <span className="text-[10px] font-mono text-white font-medium truncate">
                                    {node.id}
                                  </span>
                                  <Badge
                                    variant="outline"
                                    className="text-[7px] px-1 py-0 h-3 flex-shrink-0"
                                    style={{
                                      borderColor: style.border,
                                      color: style.color,
                                      backgroundColor: style.bg,
                                    }}
                                  >
                                    {style.text}
                                  </Badge>
                                  {isCritical && (
                                    <Badge
                                      variant="outline"
                                      className="text-[7px] px-1 py-0 h-3 border-amber-500/40 text-amber-300 bg-amber-500/10"
                                    >
                                      🔥 Critical
                                    </Badge>
                                  )}
                                </div>
                                <p className="text-[9px] text-slate-400 leading-tight break-words line-clamp-2">
                                  {node.label}
                                </p>
                                <div className="flex items-center gap-2 mt-1">
                                  {node.assigned_to && (
                                    <span className="text-[8px] text-cyan-400/70 font-mono">
                                      👤 {node.assigned_to}
                                    </span>
                                  )}
                                  {deps.length > 0 && (
                                    <span className="text-[8px] text-slate-600 font-mono">
                                      ← {deps.map((d) => d.from).join(', ')}
                                    </span>
                                  )}
                                </div>

                                {/* Expanded node details */}
                                {isExpanded && (
                                  <div className="mt-2 pt-1.5 border-t border-slate-700/20 space-y-1">
                                    <div className="grid grid-cols-2 gap-1">
                                      <div className="p-1 rounded bg-slate-900/60">
                                        <p className="text-[7px] text-slate-500 uppercase">Description</p>
                                        <p className="text-[8px] text-slate-300">{todoDetails?.description || node.label}</p>
                                      </div>
                                      <div className="p-1 rounded bg-slate-900/60">
                                        <p className="text-[7px] text-slate-500 uppercase">Worker</p>
                                        <p className="text-[8px] text-slate-300 font-mono">{todoDetails?.assigned_to || node.assigned_to || '—'}</p>
                                      </div>
                                      <div className="p-1 rounded bg-slate-900/60">
                                        <p className="text-[7px] text-slate-500 uppercase">Model</p>
                                        <p className="text-[8px] text-slate-300 font-mono truncate">{todoDetails?.assigned_to || '—'}</p>
                                      </div>
                                      <div className="p-1 rounded bg-slate-900/60">
                                        <p className="text-[7px] text-slate-500 uppercase">Status</p>
                                        <p className="text-[8px] font-mono" style={{ color: style.color }}>{style.text}</p>
                                      </div>
                                    </div>
                                    {todoDetails?.result && (
                                      <div className="p-1 rounded bg-slate-900/40">
                                        <p className="text-[7px] text-slate-500 uppercase">Result</p>
                                        <p className="text-[8px] text-green-300/80 break-words">{todoDetails.result}</p>
                                      </div>
                                    )}
                                    {todoDetails?.error && (
                                      <div className="p-1 rounded bg-red-500/5 border border-red-500/20">
                                        <p className="text-[7px] text-red-400 uppercase">Error</p>
                                        <p className="text-[8px] text-red-300 break-words">{todoDetails.error}</p>
                                      </div>
                                    )}
                                    {(todoDetails?.estimated_time_ms || todoDetails?.actual_time_ms) && (
                                      <div className="flex items-center gap-2">
                                        {todoDetails.estimated_time_ms && (
                                          <span className="text-[8px] text-slate-500 font-mono">Est: {todoDetails.estimated_time_ms}ms</span>
                                        )}
                                        {todoDetails.actual_time_ms && (
                                          <span className="text-[8px] text-cyan-400 font-mono">Actual: {todoDetails.actual_time_ms}ms</span>
                                        )}
                                      </div>
                                    )}
                                  </div>
                                )}
                              </div>
                            </div>
                          </CardContent>
                        </Card>
                      );
                    })}
                  </div>
                </div>
              );
            })}

            {/* Edge Legend */}
            {edges.length > 0 && (
              <div className="mt-3 p-2 rounded-lg bg-slate-800/30 border border-slate-700/15">
                <span className="text-[9px] font-mono text-slate-500 uppercase">Edge Types</span>
                <div className="flex flex-wrap gap-2 mt-1">
                  {['depends_on', 'delegates_to', 'verifies'].map((type) => {
                    const typeEdges = edges.filter((e) => e.type === type);
                    if (typeEdges.length === 0) return null;
                    return (
                      <div key={type} className="flex items-center gap-1">
                        <div className="h-0.5 w-4 rounded" style={{ backgroundColor: EDGE_TYPE_COLORS[type] }} />
                        <span className="text-[8px] font-mono" style={{ color: EDGE_TYPE_COLORS[type] }}>
                          {type} ({typeEdges.length})
                        </span>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
