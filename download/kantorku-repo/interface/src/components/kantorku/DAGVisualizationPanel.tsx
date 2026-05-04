'use client';

import { useMemo, useState, useCallback, useRef, useEffect } from 'react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { useKantorkuStore } from '@/lib/kantorku/store';
import { DAGNode, DAGEdge, TodoItem } from '@/lib/kantorku/types';
import { GitBranch, CheckCircle2, XCircle, AlertTriangle, Clock, ZoomIn, ZoomOut, Layers, Move } from 'lucide-react';

const STATUS_STYLES: Record<string, { color: string; bg: string; text: string }> = {
  pending: { color: '#64748b', bg: '#64748b15', text: 'Pending' },
  in_progress: { color: '#06b6d4', bg: '#06b6d415', text: 'In Progress' },
  done: { color: '#22c55e', bg: '#22c55e15', text: 'Done' },
  failed: { color: '#ef4444', bg: '#ef444415', text: 'Failed' },
  blocked: { color: '#f59e0b', bg: '#f59e0b15', text: 'Blocked' },
};

const EDGE_TYPE_COLORS: Record<string, string> = {
  depends_on: '#06b6d4',
  delegates_to: '#f59e0b',
  verifies: '#22c55e',
};

// Compute critical path
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

  while (queue.length > 0) {
    const curr = queue.shift()!;
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

  const criticalPath = new Set<string>();
  let current: string | null = endNode;
  while (current) {
    criticalPath.add(current);
    current = parent.get(current) ?? null;
  }

  return criticalPath;
}

interface NodePosition {
  x: number;
  y: number;
  width: number;
  height: number;
  node: DAGNode;
}

export function DAGVisualizationPanel() {
  const { dagNodes, dagEdges, contract } = useKantorkuStore();
  const [selectedNode, setSelectedNode] = useState<string | null>(null);
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [isPanning, setIsPanning] = useState(false);
  const [panStart, setPanStart] = useState({ x: 0, y: 0 });
  const svgRef = useRef<SVGSVGElement>(null);

  // Build visualization from DAG or contract todos
  const { nodes, edges } = useMemo(() => {
    if (dagNodes.length > 0) {
      return { nodes: dagNodes, edges: dagEdges };
    }
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
          todoEdges.push({ from: depId, to: todo.id, type: 'depends_on' });
        });
      });
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
      todoNodes.forEach((n) => { n.depth = depthMap.get(n.id) || 0; });
      return { nodes: todoNodes, edges: todoEdges };
    }
    return { nodes: [], edges: [] };
  }, [dagNodes, dagEdges, contract]);

  // Layout: assign positions based on depth levels
  const nodePositions = useMemo((): NodePosition[] => {
    if (nodes.length === 0) return [];

    const depthGroups = new Map<number, DAGNode[]>();
    nodes.forEach((node) => {
      const depth = node.depth || 0;
      if (!depthGroups.has(depth)) depthGroups.set(depth, []);
      depthGroups.get(depth)!.push(node);
    });

    const nodeW = 180;
    const nodeH = 60;
    const hGap = 40;
    const vGap = 60;
    const padding = 40;
    const positions: NodePosition[] = [];

    const sortedDepths = Array.from(depthGroups.entries()).sort(([a], [b]) => a - b);

    sortedDepths.forEach(([depth, groupNodes]) => {
      const totalWidth = groupNodes.length * (nodeW + hGap) - hGap;
      const startX = padding + (depth * (nodeW + hGap * 2));

      groupNodes.forEach((node, idx) => {
        positions.push({
          x: startX,
          y: padding + idx * (nodeH + vGap),
          width: nodeW,
          height: nodeH,
          node,
        });
      });
    });

    return positions;
  }, [nodes]);

  // Build lookup map
  const posMap = useMemo(() => {
    const map = new Map<string, NodePosition>();
    nodePositions.forEach((p) => map.set(p.node.id, p));
    return map;
  }, [nodePositions]);

  // Critical path
  const criticalPath = useMemo(() => computeCriticalPath(nodes, edges), [nodes, edges]);

  // Status counts
  const statusCounts = useMemo(() => {
    const counts: Record<string, number> = {};
    nodes.forEach((n) => { counts[n.status] = (counts[n.status] || 0) + 1; });
    return counts;
  }, [nodes]);

  // SVG viewBox
  const svgSize = useMemo(() => {
    if (nodePositions.length === 0) return { width: 400, height: 300 };
    const maxX = Math.max(...nodePositions.map((p) => p.x + p.width)) + 60;
    const maxY = Math.max(...nodePositions.map((p) => p.y + p.height)) + 60;
    return { width: Math.max(maxX, 400), height: Math.max(maxY, 300) };
  }, [nodePositions]);

  // Get todo details from contract
  const getTodoDetails = (nodeId: string) => {
    if (!contract) return null;
    return contract.todos.find((t) => t.id === nodeId) || null;
  };

  // Pan handlers
  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    setIsPanning(true);
    setPanStart({ x: e.clientX - pan.x, y: e.clientY - pan.y });
  }, [pan]);

  const handleMouseMove = useCallback((e: React.MouseEvent) => {
    if (!isPanning) return;
    setPan({ x: e.clientX - panStart.x, y: e.clientY - panStart.y });
  }, [isPanning, panStart]);

  const handleMouseUp = useCallback(() => {
    setIsPanning(false);
  }, []);

  // Wheel zoom
  const handleWheel = useCallback((e: React.WheelEvent) => {
    e.preventDefault();
    const delta = e.deltaY > 0 ? -0.1 : 0.1;
    setZoom((z) => Math.max(0.3, Math.min(2, z + delta)));
  }, []);

  const selectedTodo = selectedNode ? getTodoDetails(selectedNode) : null;
  const selectedPos = selectedNode ? posMap.get(selectedNode) : null;

  if (nodes.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-slate-500">
        <GitBranch className="h-8 w-8 text-slate-600/50 mb-2" />
        <p className="text-[11px] text-center text-slate-600">
          No task graph available.<br />
          Start a contract to see dependencies.
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Header */}
      <div className="flex-shrink-0 px-3 py-2 border-b border-slate-700/30 bg-slate-900/40">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-1.5">
            <GitBranch className="h-3.5 w-3.5 text-teal-400" />
            <span className="text-[10px] font-mono text-slate-400 uppercase">Task DAG</span>
            <Badge variant="outline" className="text-[8px] px-1 py-0 h-3.5 border-teal-500/30 text-teal-300 font-mono">
              {nodes.length} nodes
            </Badge>
          </div>
          <div className="flex items-center gap-1">
            <Badge variant="outline" className="text-[8px] px-1 py-0 h-3.5 border-amber-500/30 text-amber-300 font-mono">
              🔥 {criticalPath.size} critical
            </Badge>
            <div className="flex items-center gap-0.5 border border-slate-700/50 rounded">
              <Button variant="ghost" size="sm" className="h-5 w-5 p-0 text-slate-500 hover:text-cyan-400" onClick={() => setZoom(Math.max(0.3, zoom - 0.15))} aria-label="Zoom out">
                <ZoomOut className="h-3 w-3" />
              </Button>
              <span className="text-[8px] text-slate-500 font-mono w-8 text-center">{(zoom * 100).toFixed(0)}%</span>
              <Button variant="ghost" size="sm" className="h-5 w-5 p-0 text-slate-500 hover:text-cyan-400" onClick={() => setZoom(Math.min(2, zoom + 0.15))} aria-label="Zoom in">
                <ZoomIn className="h-3 w-3" />
              </Button>
              <Button variant="ghost" size="sm" className="h-5 w-5 p-0 text-slate-500 hover:text-cyan-400" onClick={() => { setZoom(1); setPan({ x: 0, y: 0 }); }} aria-label="Reset view">
                <Move className="h-3 w-3" />
              </Button>
            </div>
          </div>
        </div>
        {/* Status summary */}
        <div className="flex items-center gap-2 mt-1.5">
          {Object.entries(statusCounts).map(([status, count]) => {
            const style = STATUS_STYLES[status] || STATUS_STYLES.pending;
            return (
              <Badge key={status} variant="outline" className="text-[8px] px-1.5 py-0 h-4 font-mono"
                style={{ borderColor: `${style.color}40`, color: style.color, backgroundColor: style.bg }}>
                {count} {style.text.toLowerCase()}
              </Badge>
            );
          })}
        </div>
      </div>

      {/* SVG Canvas */}
      <div className="flex-1 overflow-hidden relative cursor-grab active:cursor-grabbing" style={{ background: 'radial-gradient(circle at 50% 50%, #0f172a, #0a0e1a)' }}>
        <svg
          ref={svgRef}
          width="100%"
          height="100%"
          viewBox={`0 0 ${svgSize.width} ${svgSize.height}`}
          style={{ transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`, transformOrigin: '0 0', transition: isPanning ? 'none' : 'transform 0.1s ease' }}
          onMouseDown={handleMouseDown}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          onMouseLeave={handleMouseUp}
          onWheel={handleWheel}
          role="img"
          aria-label="Task dependency graph"
        >
          {/* Arrow marker definitions */}
          <defs>
            {Object.entries(EDGE_TYPE_COLORS).map(([type, color]) => (
              <marker key={type} id={`arrow-${type}`} markerWidth="8" markerHeight="6" refX="8" refY="3" orient="auto">
                <path d="M0,0 L8,3 L0,6" fill={color} />
              </marker>
            ))}
            <marker id="arrow-critical" markerWidth="8" markerHeight="6" refX="8" refY="3" orient="auto">
              <path d="M0,0 L8,3 L0,6" fill="#f59e0b" />
            </marker>
          </defs>

          {/* Grid pattern */}
          <defs>
            <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
              <path d="M 40 0 L 0 0 0 40" fill="none" stroke="#1e293b" strokeWidth="0.5" />
            </pattern>
          </defs>
          <rect width="100%" height="100%" fill="url(#grid)" opacity="0.5" />

          {/* Edges */}
          {edges.map((edge, idx) => {
            const fromPos = posMap.get(edge.from);
            const toPos = posMap.get(edge.to);
            if (!fromPos || !toPos) return null;

            const fromX = fromPos.x + fromPos.width;
            const fromY = fromPos.y + fromPos.height / 2;
            const toX = toPos.x;
            const toY = toPos.y + toPos.height / 2;

            const isCriticalEdge = criticalPath.has(edge.from) && criticalPath.has(edge.to);
            const color = isCriticalEdge ? '#f59e0b' : EDGE_TYPE_COLORS[edge.type] || '#94a3b8';
            const strokeWidth = isCriticalEdge ? 2.5 : 1.5;

            // Bezier curve
            const midX = (fromX + toX) / 2;
            const path = `M ${fromX} ${fromY} C ${midX} ${fromY}, ${midX} ${toY}, ${toX} ${toY}`;

            return (
              <path
                key={`edge-${idx}`}
                d={path}
                fill="none"
                stroke={color}
                strokeWidth={strokeWidth}
                strokeDasharray={isCriticalEdge ? '6,3' : 'none'}
                markerEnd={`url(#arrow-${isCriticalEdge ? 'critical' : edge.type})`}
                opacity={0.7}
              />
            );
          })}

          {/* Nodes */}
          {nodePositions.map((pos) => {
            const style = STATUS_STYLES[pos.node.status] || STATUS_STYLES.pending;
            const isCritical = criticalPath.has(pos.node.id);
            const isSelected = selectedNode === pos.node.id;
            const isInProgress = pos.node.status === 'in_progress';

            return (
              <g
                key={pos.node.id}
                onClick={(e) => { e.stopPropagation(); setSelectedNode(isSelected ? null : pos.node.id); }}
                style={{ cursor: 'pointer' }}
              >
                {/* Glow effect for in_progress */}
                {isInProgress && (
                  <rect
                    x={pos.x - 3}
                    y={pos.y - 3}
                    width={pos.width + 6}
                    height={pos.height + 6}
                    rx={10}
                    fill="none"
                    stroke={style.color}
                    strokeWidth={1.5}
                    opacity={0.4}
                  >
                    <animate attributeName="opacity" values="0.2;0.6;0.2" dur="2s" repeatCount="indefinite" />
                  </rect>
                )}

                {/* Critical path glow */}
                {isCritical && (
                  <rect
                    x={pos.x - 2}
                    y={pos.y - 2}
                    width={pos.width + 4}
                    height={pos.height + 4}
                    rx={9}
                    fill="none"
                    stroke="#f59e0b"
                    strokeWidth={1}
                    opacity={0.3}
                  />
                )}

                {/* Main rect */}
                <rect
                  x={pos.x}
                  y={pos.y}
                  width={pos.width}
                  height={pos.height}
                  rx={8}
                  fill={isSelected ? '#1e293b' : '#0f172a'}
                  stroke={isSelected ? style.color : isCritical ? '#f59e0b80' : `${style.color}60`}
                  strokeWidth={isSelected ? 2 : isCritical ? 1.5 : 1}
                />

                {/* Left accent bar */}
                <rect
                  x={pos.x}
                  y={pos.y + 8}
                  width={3}
                  height={pos.height - 16}
                  rx={1.5}
                  fill={isCritical ? '#f59e0b' : style.color}
                />

                {/* Status indicator */}
                <circle
                  cx={pos.x + 16}
                  cy={pos.y + 16}
                  r={5}
                  fill={style.bg}
                  stroke={style.color}
                  strokeWidth={1}
                />
                {pos.node.status === 'done' && (
                  <path d={`M${pos.x + 13},${pos.y + 16} L${pos.x + 15.5},${pos.y + 18.5} L${pos.x + 19},${pos.y + 13.5}`} fill="none" stroke={style.color} strokeWidth={1.5} />
                )}
                {pos.node.status === 'failed' && (
                  <path d={`M${pos.x + 13.5},${pos.y + 13.5} L${pos.x + 18.5},${pos.y + 18.5} M${pos.x + 18.5},${pos.y + 13.5} L${pos.x + 13.5},${pos.y + 18.5}`} fill="none" stroke={style.color} strokeWidth={1.5} />
                )}
                {pos.node.status === 'in_progress' && (
                  <circle cx={pos.x + 16} cy={pos.y + 16} r={2.5} fill={style.color}>
                    <animate attributeName="r" values="2;3.5;2" dur="1.5s" repeatCount="indefinite" />
                  </circle>
                )}
                {pos.node.status === 'pending' && (
                  <circle cx={pos.x + 16} cy={pos.y + 16} r={2} fill={style.color} opacity={0.5} />
                )}

                {/* Node ID */}
                <text
                  x={pos.x + 26}
                  y={pos.y + 18}
                  fill="white"
                  fontSize="10"
                  fontFamily="monospace"
                  fontWeight="600"
                >
                  {pos.node.id}
                </text>

                {/* Critical badge */}
                {isCritical && (
                  <text x={pos.x + pos.width - 8} y={pos.y + 14} fill="#f59e0b" fontSize="8" fontFamily="monospace">🔥</text>
                )}

                {/* Description (truncated) */}
                <text
                  x={pos.x + 26}
                  y={pos.y + 33}
                  fill="#94a3b8"
                  fontSize="8"
                  fontFamily="sans-serif"
                >
                  {pos.node.label.length > 22 ? pos.node.label.slice(0, 22) + '…' : pos.node.label}
                </text>

                {/* Worker assignment */}
                {pos.node.assigned_to && (
                  <text
                    x={pos.x + 26}
                    y={pos.y + 47}
                    fill="#06b6d4"
                    fontSize="8"
                    fontFamily="monospace"
                    opacity={0.7}
                  >
                    👤 {pos.node.assigned_to}
                  </text>
                )}
              </g>
            );
          })}
        </svg>

        {/* Node Detail Panel */}
        {selectedNode && selectedTodo && (
          <div className="absolute bottom-3 left-3 right-3 bg-slate-900/95 backdrop-blur-sm border border-slate-700/50 rounded-lg p-3 shadow-xl max-w-xs">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-1.5">
                <span className="text-[11px] font-mono text-white font-semibold">{selectedTodo.id}</span>
                <Badge variant="outline" className="text-[8px] px-1 py-0 h-3.5"
                  style={{ borderColor: `${STATUS_STYLES[selectedTodo.status]?.color}40`, color: STATUS_STYLES[selectedTodo.status]?.color }}>
                  {STATUS_STYLES[selectedTodo.status]?.text}
                </Badge>
              </div>
              <button onClick={() => setSelectedNode(null)} className="text-slate-500 hover:text-slate-300 text-xs" aria-label="Close details">✕</button>
            </div>
            <p className="text-[11px] text-slate-300 leading-relaxed mb-1.5">{selectedTodo.description}</p>
            <div className="grid grid-cols-2 gap-1.5">
              <div className="p-1.5 rounded bg-slate-800/60">
                <p className="text-[8px] text-slate-500 uppercase">Worker</p>
                <p className="text-[9px] text-cyan-300 font-mono">{selectedTodo.assigned_to || '—'}</p>
              </div>
              <div className="p-1.5 rounded bg-slate-800/60">
                <p className="text-[8px] text-slate-500 uppercase">Priority</p>
                <p className="text-[9px] text-slate-300 font-mono">{selectedTodo.priority || '—'}</p>
              </div>
              {selectedTodo.estimated_time_ms && (
                <div className="p-1.5 rounded bg-slate-800/60">
                  <p className="text-[8px] text-slate-500 uppercase">Estimated</p>
                  <p className="text-[9px] text-slate-300 font-mono">{selectedTodo.estimated_time_ms}ms</p>
                </div>
              )}
              {selectedTodo.actual_time_ms && (
                <div className="p-1.5 rounded bg-slate-800/60">
                  <p className="text-[8px] text-slate-500 uppercase">Actual</p>
                  <p className="text-[9px] text-cyan-300 font-mono">{selectedTodo.actual_time_ms}ms</p>
                </div>
              )}
            </div>
            {selectedTodo.error && (
              <div className="mt-1.5 p-1.5 rounded bg-red-500/10 border border-red-500/20">
                <p className="text-[8px] text-red-400 uppercase">Error</p>
                <p className="text-[9px] text-red-300 break-words">{selectedTodo.error}</p>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Legend */}
      <div className="flex-shrink-0 px-3 py-1.5 border-t border-slate-700/30 bg-slate-900/40">
        <div className="flex items-center gap-3 flex-wrap">
          <span className="text-[8px] font-mono text-slate-500 uppercase">Edge Types:</span>
          {Object.entries(EDGE_TYPE_COLORS).map(([type, color]) => {
            const typeCount = edges.filter((e) => e.type === type).length;
            if (typeCount === 0) return null;
            return (
              <div key={type} className="flex items-center gap-1">
                <div className="h-0.5 w-4 rounded" style={{ backgroundColor: color }} />
                <span className="text-[8px] font-mono" style={{ color }}>{type} ({typeCount})</span>
              </div>
            );
          })}
          {criticalPath.size > 1 && (
            <div className="flex items-center gap-1">
              <div className="h-0.5 w-4 rounded bg-amber-500" style={{ borderTop: '2px dashed #f59e0b' }} />
              <span className="text-[8px] font-mono text-amber-400">critical path</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
