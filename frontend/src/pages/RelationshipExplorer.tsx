import React, { useEffect, useState, useRef, useMemo } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import { 
  GitFork, 
  Search, 
  Briefcase, 
  GraduationCap, 
  User, 
  ZoomIn, 
  ZoomOut, 
  RefreshCw,
  Cpu,
  Info,
  ChevronRight,
  Maximize2
} from 'lucide-react';
import { resumeService } from '../services/api';
import type { GraphNode, GraphLink } from '../types';

export const RelationshipExplorer: React.FC = () => {
  const [searchParams] = useSearchParams();
  const targetCandidateId = searchParams.get('id') || 'global';

  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  
  // Toggles for Node Type Filters
  const [filters, setFilters] = useState({
    candidate: true,
    skill: true,
    company: true,
    institution: true,
    project: true,
  });

  // Selected Node for overlay/side panel
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);

  // Zoom & Pan Viewport States
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [isPanning, setIsPanning] = useState(false);
  const [panStart, setPanStart] = useState({ x: 0, y: 0 });
  const [hoveredNodeId, setHoveredNodeId] = useState<string | null>(null);

  const fitGraphToViewport = (nodes: GraphNode[]) => {
    const rect = containerRef.current?.getBoundingClientRect();
    if (!rect || nodes.length === 0) return;

    const padding = 90;
    const xs = nodes.map(n => n.x || 0);
    const ys = nodes.map(n => n.y || 0);
    const minX = Math.min(...xs);
    const maxX = Math.max(...xs);
    const minY = Math.min(...ys);
    const maxY = Math.max(...ys);

    const graphWidth = Math.max(1, maxX - minX);
    const graphHeight = Math.max(1, maxY - minY);
    const scaleX = (rect.width - padding * 2) / graphWidth;
    const scaleY = (rect.height - padding * 2) / graphHeight;
    const nextZoom = Math.max(0.5, Math.min(1.2, Math.min(scaleX, scaleY)));

    const centerX = (minX + maxX) / 2;
    const centerY = (minY + maxY) / 2;

    setZoom(nextZoom);
    setPan({
      x: rect.width / 2 - centerX * nextZoom,
      y: rect.height / 2 - centerY * nextZoom,
    });
  };

  // Physics States
  const [nodes, setNodes] = useState<GraphNode[]>([]);
  const nodesRef = useRef<GraphNode[]>([]);
  const [links, setLinks] = useState<GraphLink[]>([]);
  const linksRef = useRef<GraphLink[]>([]);

  // Drag States
  const [draggedNodeId, setDraggedNodeId] = useState<string | null>(null);

  const containerRef = useRef<SVGSVGElement>(null);

  useEffect(() => {
    const loadGraph = async () => {
      setLoading(true);
      try {
        const data = await resumeService.getCandidateGraph(targetCandidateId);
        
        // Initialize positions with category grouping and extra spacing
        const categoryLayout = {
          candidate: { radius: 0, start: -Math.PI / 4, end: Math.PI / 4 },
          skill: { radius: 240, start: -Math.PI / 4, end: Math.PI / 4 },
          company: { radius: 260, start: Math.PI / 4, end: (3 * Math.PI) / 4 },
          institution: { radius: 260, start: (3 * Math.PI) / 4, end: (5 * Math.PI) / 4 },
          project: { radius: 300, start: (5 * Math.PI) / 4, end: (7 * Math.PI) / 4 },
        } as const;

        const typeCounts = data.nodes.reduce<Record<string, number>>((acc, node) => {
          acc[node.type] = (acc[node.type] || 0) + 1;
          return acc;
        }, {});

        const offsets: Record<string, number> = {
          candidate: 0,
          skill: 0,
          company: 0,
          institution: 0,
          project: 0,
        };

        const initializedNodes = data.nodes.map((n) => {
          const layout = categoryLayout[n.type] ?? categoryLayout.skill;
          const sectorSize = layout.end - layout.start;
          const indexInGroup = offsets[n.type] || 0;
          const groupCount = Math.max(1, typeCounts[n.type] || 1);
          const angle = layout.start + (indexInGroup / groupCount) * sectorSize + (Math.random() - 0.5) * 0.14;
          offsets[n.type] = indexInGroup + 1;
          const radius = layout.radius + (Math.random() * 40 - 20);

          return {
            ...n,
            x: n.type === 'candidate' && n.id === targetCandidateId ? 0 : Math.cos(angle) * radius,
            y: n.type === 'candidate' && n.id === targetCandidateId ? 0 : Math.sin(angle) * radius,
            vx: 0,
            vy: 0,
            fx: null,
            fy: null
          };
        });

        nodesRef.current = initializedNodes;
        linksRef.current = data.links;
        
        setNodes(initializedNodes);
        setLinks(data.links);
        fitGraphToViewport(initializedNodes);
        
        // Auto select first candidate node in case candidate ID is specified
        if (targetCandidateId !== 'global') {
          const candidateNode = initializedNodes.find(n => n.id === targetCandidateId);
          if (candidateNode) setSelectedNode(candidateNode);
        }
      } catch (err) {
        console.error('Failed to load graph data', err);
      } finally {
        setLoading(false);
      }
    };
    loadGraph();
  }, [targetCandidateId]);

  // physics loop simulation logic
  useEffect(() => {
    if (loading || nodesRef.current.length === 0) return;

    let animFrameId: number;

    const tick = () => {
      const currentNodes = [...nodesRef.current];
      const currentLinks = linksRef.current;

      const center = { x: 0, y: 0 };
      const nodeCount = currentNodes.length;
      const repulsionStrength = 2200 + nodeCount * 30;
      const attractionStrength = 0.045;
      const desiredLength = 100 + Math.min(80, nodeCount * 1.6);
      const gravity = 0.028;
      const damping = 0.82;

      // 1. Calculate Repulsion forces (push all nodes away from each other)
      for (let i = 0; i < currentNodes.length; i++) {
        const n1 = currentNodes[i];
        if (n1.id === draggedNodeId) continue;

        for (let j = 0; j < currentNodes.length; j++) {
          if (i === j) continue;
          const n2 = currentNodes[j];

          const dx = (n1.x || 0) - (n2.x || 0);
          const dy = (n1.y || 0) - (n2.y || 0);
          const distSq = dx * dx + dy * dy + 0.1;
          const dist = Math.sqrt(distSq);

          if (dist < 320) { // Limit repulsion radius
            const force = repulsionStrength / distSq;
            n1.vx = (n1.vx || 0) + (dx / dist) * force;
            n1.vy = (n1.vy || 0) + (dy / dist) * force;
          }
        }
      }

      // 2. Calculate Attraction forces (pull linked nodes together)
      currentLinks.forEach(link => {
        const sourceNode = currentNodes.find(n => n.id === (typeof link.source === 'object' ? (link.source as any).id : link.source));
        const targetNode = currentNodes.find(n => n.id === (typeof link.target === 'object' ? (link.target as any).id : link.target));

        if (!sourceNode || !targetNode) return;

        const dx = (targetNode.x || 0) - (sourceNode.x || 0);
        const dy = (targetNode.y || 0) - (sourceNode.y || 0);
        const dist = Math.sqrt(dx * dx + dy * dy) + 0.1;

        const force = attractionStrength * (dist - desiredLength);
        const fx = (dx / dist) * force;
        const fy = (dy / dist) * force;

        if (sourceNode.id !== draggedNodeId) {
          sourceNode.vx = (sourceNode.vx || 0) + fx;
          sourceNode.vy = (sourceNode.vy || 0) + fy;
        }
        if (targetNode.id !== draggedNodeId) {
          targetNode.vx = (targetNode.vx || 0) - fx;
          targetNode.vy = (targetNode.vy || 0) - fy;
        }
      });

      // 3. Gravity attraction to center & update coordinates
      currentNodes.forEach(node => {
        if (node.id === draggedNodeId) return;

        // Pull towards center
        const dx = center.x - (node.x || 0);
        const dy = center.y - (node.y || 0);
        node.vx = (node.vx || 0) + dx * gravity;
        node.vy = (node.vy || 0) + dy * gravity;

        // Apply velocities and dampening
        node.x = (node.x || 0) + (node.vx || 0);
        node.y = (node.y || 0) + (node.vy || 0);
        node.vx = (node.vx || 0) * damping;
        node.vy = (node.vy || 0) * damping;
      });

      nodesRef.current = currentNodes;
      setNodes([...currentNodes]);

      animFrameId = requestAnimationFrame(tick);
    };

    animFrameId = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(animFrameId);
  }, [loading, draggedNodeId]);

  // Recenter helper
  const handleRecenter = () => {
    fitGraphToViewport(nodesRef.current);
  };

  // Drag Handlers
  const handleNodeMouseDown = (e: React.MouseEvent, node: GraphNode) => {
    e.stopPropagation();
    setDraggedNodeId(node.id);
  };

  const handleSVGMouseMove = (e: React.MouseEvent) => {
    if (draggedNodeId) {
      // Node Dragging Physics Position update
      const rect = containerRef.current?.getBoundingClientRect();
      if (!rect) return;
      
      // Calculate coordinates scaled for active zoom/pan
      const mouseX = (e.clientX - rect.left - pan.x) / zoom;
      const mouseY = (e.clientY - rect.top - pan.y) / zoom;

      nodesRef.current = nodesRef.current.map(n => {
        if (n.id === draggedNodeId) {
          return { ...n, x: mouseX, y: mouseY, vx: 0, vy: 0 };
        }
        return n;
      });
    } else if (isPanning) {
      // Pan viewport update
      const dx = e.clientX - panStart.x;
      const dy = e.clientY - panStart.y;
      setPan({ x: pan.x + dx, y: pan.y + dy });
      setPanStart({ x: e.clientX, y: e.clientY });
    }
  };

  const handleSVGMouseUp = () => {
    setDraggedNodeId(null);
    setIsPanning(false);
  };

  const handleSVGMouseDown = (e: React.MouseEvent) => {
    setIsPanning(true);
    setPanStart({ x: e.clientX, y: e.clientY });
  };

  const handleZoom = (direction: 'in' | 'out') => {
    setZoom(prev => {
      const next = direction === 'in' ? prev + 0.14 : prev - 0.14;
      return Math.max(0.55, Math.min(1.8, next));
    });
  };

  const handleSVGWheel = (e: React.WheelEvent) => {
    e.preventDefault();
    const factor = e.deltaY > 0 ? -0.08 : 0.08;
    setZoom(prev => Math.max(0.55, Math.min(1.8, prev + factor)));
  };

  // Node Color Utilities
  const getNodeColor = (type: GraphNode['type']) => {
    switch (type) {
      case 'candidate': return '#a855f7'; // purple
      case 'skill': return '#22c55e';     // emerald
      case 'company': return '#38bdf8';   // cyan/technology
      case 'institution': return '#f59e0b'; // amber
      case 'project': return '#ec4899';   // fuchsia
      default: return '#9ca3af';
    }
  };

  const getNodeRadius = (node: GraphNode) => {
    const base = {
      candidate: 30,
      skill: 16,
      company: 18,
      institution: 18,
      project: 20,
    }[node.type] ?? 16;

    return Math.max(base, Math.min(40, Math.sqrt(node.val || 0) * 3 + 8));
  };

  const getNodeIcon = (type: GraphNode['type']) => {
    switch (type) {
      case 'candidate': return <User size={12} />;
      case 'company': return <Briefcase size={12} />;
      case 'institution': return <GraduationCap size={12} />;
      case 'skill': return <Cpu size={12} />;
      default: return <GitFork size={12} />;
    }
  };

  // Filter and search logic for active displays
  const visibleNodes = useMemo(() => {
    return nodes.filter(n => {
      // Category filter check
      if (n.type === 'candidate' && !filters.candidate) return false;
      if (n.type === 'skill' && !filters.skill) return false;
      if (n.type === 'company' && !filters.company) return false;
      if (n.type === 'institution' && !filters.institution) return false;
      if (n.type === 'project' && !filters.project) return false;

      // Text search match filter
      if (searchQuery.trim()) {
        return n.label.toLowerCase().includes(searchQuery.toLowerCase());
      }
      return true;
    });
  }, [nodes, filters, searchQuery]);

  const visibleLinks = useMemo(() => {
    return links.filter(link => {
      const srcId = typeof link.source === 'object' ? (link.source as any).id : link.source;
      const tgtId = typeof link.target === 'object' ? (link.target as any).id : link.target;
      return visibleNodes.some(n => n.id === srcId) && visibleNodes.some(n => n.id === tgtId);
    });
  }, [links, visibleNodes]);

  // Compute stats of connected links to selected node for sidebar display
  const connectedDetails = useMemo(() => {
    if (!selectedNode) return null;

    const connectedLinks = links.filter(link => {
      const srcId = typeof link.source === 'object' ? (link.source as any).id : link.source;
      const tgtId = typeof link.target === 'object' ? (link.target as any).id : link.target;
      return srcId === selectedNode.id || tgtId === selectedNode.id;
    });

    const targetNodes = connectedLinks.map(link => {
      const srcId = typeof link.source === 'object' ? (link.source as any).id : link.source;
      const tgtId = typeof link.target === 'object' ? (link.target as any).id : link.target;
      const oppositeId = srcId === selectedNode.id ? tgtId : srcId;
      return nodes.find(n => n.id === oppositeId);
    }).filter(Boolean) as GraphNode[];

    return {
      links: connectedLinks,
      nodes: targetNodes
    };
  }, [selectedNode, nodes, links]);

  return (
    <div className="space-y-6 flex flex-col min-h-[calc(100vh-10rem)] animate-in fade-in duration-300">
      
      {/* FILTER BUTTONS & QUICK CONTROL BAR */}
      <section className="glass-panel rounded-2xl p-4 flex flex-col md:flex-row items-center justify-between gap-4">
        
        {/* Search */}
        <div className="relative w-full md:max-w-xs">
          <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-500" size={15} />
          <input
            type="text"
            placeholder="Highlight graph nodes..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-slate-900 border border-dark-border focus:border-brand-500 rounded-xl py-2 pl-10 pr-4 text-xs text-slate-100 placeholder-slate-500 outline-none transition-colors"
          />
        </div>

        {/* Filters */}
        <div className="flex flex-wrap items-center gap-2">
          {Object.entries(filters).map(([type, enabled]) => (
            <button
              key={type}
              onClick={() => setFilters(prev => ({ ...prev, [type]: !enabled }))}
              className={`px-3 py-1.5 rounded-lg border text-[10px] font-bold uppercase tracking-wider transition-all duration-150 ${
                enabled 
                  ? 'bg-slate-800 border-slate-700 text-white shadow-sm'
                  : 'bg-slate-950 border-dark-border/40 text-slate-600'
              }`}
            >
              <span 
                className="inline-block w-1.5 h-1.5 rounded-full mr-1.5"
                style={{ backgroundColor: enabled ? getNodeColor(type as any) : '#4b5563' }}
              />
              {type}s
            </button>
          ))}
        </div>

        {/* Recenter & Zoom Actions */}
        <div className="flex items-center gap-1.5 bg-slate-900 p-1 rounded-xl border border-dark-border">
          <button 
            onClick={() => handleZoom('in')} 
            className="p-1.5 hover:bg-slate-850 rounded-lg text-slate-400 hover:text-white transition-colors"
            title="Zoom In"
          >
            <ZoomIn size={14} />
          </button>
          <button 
            onClick={() => handleZoom('out')} 
            className="p-1.5 hover:bg-slate-850 rounded-lg text-slate-400 hover:text-white transition-colors"
            title="Zoom Out"
          >
            <ZoomOut size={14} />
          </button>
          <button 
            onClick={handleRecenter} 
            className="p-1.5 hover:bg-slate-850 rounded-lg text-slate-400 hover:text-white transition-colors"
            title="Recenter"
          >
            <RefreshCw size={14} />
          </button>
        </div>

      </section>

      {/* GRAPH EXPLORER WORKSPACE AND SIDEBAR PANEL */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6 flex-1 items-stretch">
        
        {/* GRAPH SVG CANVAS (interactive pan & zoom) */}
        <div className="lg:col-span-3 glass-panel rounded-3xl relative overflow-hidden min-h-[450px] flex items-stretch border border-dark-border/80">
          
          <div className="absolute top-4 left-4 z-10 pointer-events-none">
            <span className="inline-flex items-center gap-1 bg-slate-950/80 backdrop-blur-md px-3 py-1.5 rounded-xl border border-dark-border text-[10px] text-slate-400 font-semibold shadow-md">
              <Info size={11} className="text-brand-500 animate-pulse" />
              <span>Left-click + Drag to pan canvas. Click + Hold node to move it. Scroll to zoom.</span>
            </span>
          </div>

          {loading ? (
            <div className="flex-1 flex flex-col items-center justify-center text-slate-500 animate-shimmer bg-dark-card" />
          ) : (
            <svg 
              ref={containerRef}
              className="w-full h-full cursor-grab active:cursor-grabbing select-none"
              onWheel={handleSVGWheel}
              onMouseMove={handleSVGMouseMove}
              onMouseUp={handleSVGMouseUp}
              onMouseLeave={handleSVGMouseUp}
              onMouseDown={handleSVGMouseDown}
            >
              {/* Arrow definitions for relationships */}
              <defs>
                <marker id="arrow" viewBox="0 0 10 10" refX="15" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                  <path d="M 0 0 L 10 5 L 0 10 z" fill="#1e293b" />
                </marker>
              </defs>

              {/* Viewport scaling and translation */}
              <g transform={`translate(${pan.x}, ${pan.y}) scale(${zoom})`} style={{ transition: 'transform 180ms ease-out' }}>
                
                {/* DRAW LINKS */}
                {visibleLinks.map((link, idx) => {
                  const sourceNode = nodes.find(n => n.id === (typeof link.source === 'object' ? (link.source as any).id : link.source));
                  const targetNode = nodes.find(n => n.id === (typeof link.target === 'object' ? (link.target as any).id : link.target));

                  if (!sourceNode || !targetNode) return null;

                  const isHighlighted = selectedNode && (sourceNode.id === selectedNode.id || targetNode.id === selectedNode.id);

                  return (
                    <g key={idx}>
                      <line
                        x1={sourceNode.x || 0}
                        y1={sourceNode.y || 0}
                        x2={targetNode.x || 0}
                        y2={targetNode.y || 0}
                        stroke={isHighlighted ? '#8b5cf6' : '#1e293b'}
                        strokeWidth={isHighlighted ? 2.5 : 1.2}
                        strokeOpacity={selectedNode ? (isHighlighted ? 1 : 0.15) : 0.6}
                        markerEnd="url(#arrow)"
                      />
                      {/* Optional Relationship Labels */}
                      {isHighlighted && (
                        <text
                          x={((sourceNode.x || 0) + (targetNode.x || 0)) / 2}
                          y={((sourceNode.y || 0) + (targetNode.y || 0)) / 2 - 4}
                          fill="#6b7280"
                          fontSize="7px"
                          fontWeight="bold"
                          textAnchor="middle"
                        >
                          {link.type}
                        </text>
                      )}
                    </g>
                  );
                })}

                {/* DRAW NODES */}
                {visibleNodes.map((node) => {
                  const isSelected = selectedNode?.id === node.id;
                  const isHovered = hoveredNodeId === node.id;
                  const isHighlighted = searchQuery.trim()
                    ? node.label.toLowerCase().includes(searchQuery.toLowerCase())
                    : true;
                  
                  const isConnectedToSelected = selectedNode && connectedDetails?.nodes.some(n => n.id === node.id);
                  const isFocus = isSelected || isConnectedToSelected || isHovered;

                  const opacity = selectedNode 
                    ? (isFocus ? 1 : 0.18) 
                    : (isHighlighted ? 1 : 0.32);

                  const nodeRadius = getNodeRadius(node);
                  const showLabel = isSelected || isHovered || node.type === 'candidate' || (node.type === 'project' && node.val && node.val > 30);

                  return (
                    <g 
                      key={node.id}
                      transform={`translate(${node.x || 0}, ${node.y || 0})`}
                      className="node-interactive"
                      onMouseDown={(e) => handleNodeMouseDown(e, node)}
                      onMouseEnter={() => setHoveredNodeId(node.id)}
                      onMouseLeave={() => setHoveredNodeId(null)}
                      onClick={(e) => {
                        e.stopPropagation();
                        setSelectedNode(node);
                      }}
                      style={{ opacity, cursor: 'pointer' }}
                    >
                      {/* Glow outline on selection */}
                      {isSelected && (
                        <circle 
                          r={nodeRadius + 6}
                          fill="none" 
                          stroke="#8b5cf6" 
                          strokeWidth="2.5" 
                          strokeDasharray="4,4"
                          className="animate-spin"
                          style={{ animationDuration: '8s' }}
                        />
                      )}

                      {/* Main Node bubble */}
                      <circle
                        r={nodeRadius}
                        fill={getNodeColor(node.type)}
                        fillOpacity={isSelected || isHovered ? 0.95 : 0.75}
                        stroke={isSelected ? '#ffffff' : '#0f172a'}
                        strokeWidth={isSelected ? 2.5 : 1.5}
                        style={{ filter: isSelected || isHovered ? 'drop-shadow(0 0 12px rgba(168, 85, 247, 0.35))' : undefined }}
                      />

                      {/* Extracted Icon initials in bubble center if candidate */}
                      {node.type === 'candidate' && (
                        <text
                          y="3"
                          fill="#ffffff"
                          fontSize="9px"
                          fontWeight="bold"
                          textAnchor="middle"
                          pointerEvents="none"
                        >
                          {node.label.split(' ').map(n=>n[0]).join('')}
                        </text>
                      )}

                      {/* Node text label below bubble */}
                      {showLabel && (
                        <text
                          y={nodeRadius + 14}
                          fill={isSelected ? '#ffffff' : '#cbd5e1'}
                          fontSize={isSelected || isHovered ? '10px' : '8px'}
                          fontWeight={isSelected || isHovered ? '700' : '500'}
                          textAnchor="middle"
                          pointerEvents="none"
                          className="bg-slate-950"
                        >
                          {node.label}
                        </text>
                      )}
                    </g>
                  );
                })}

              </g>
            </svg>
          )}

        </div>

        {/* SIDE DETAIL OVERLAY FOR SELECTED NODES */}
        <div className="lg:col-span-1 flex flex-col items-stretch">
          {selectedNode ? (
            <div className="glass-panel rounded-3xl p-5 flex flex-col justify-between flex-1 border border-dark-border/80 animate-in fade-in duration-200">
              
              <div className="space-y-5">
                
                {/* Close/Deselect button */}
                <div className="flex items-center justify-between border-b border-dark-border/40 pb-3">
                  <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">Node Inspector</span>
                  <button 
                    onClick={() => setSelectedNode(null)}
                    className="text-[10px] text-slate-400 hover:text-white font-semibold"
                  >
                    Clear Select
                  </button>
                </div>

                {/* Node bio info card */}
                <div className="space-y-3">
                  <div className="flex items-center gap-3">
                    <div 
                      className="w-10 h-10 rounded-xl flex items-center justify-center text-white"
                      style={{ backgroundColor: getNodeColor(selectedNode.type) }}
                    >
                      {getNodeIcon(selectedNode.type)}
                    </div>
                    <div>
                      <h4 className="text-sm font-extrabold text-white leading-tight">{selectedNode.label}</h4>
                      <span className="text-[9px] uppercase tracking-wider text-slate-400 font-semibold">{selectedNode.type} Node</span>
                    </div>
                  </div>
                </div>

                {/* Connected associations count / items */}
                <div className="space-y-3 pt-2">
                  <span className="text-[10px] uppercase text-slate-500 tracking-wider font-semibold block">Connected Relations ({connectedDetails?.links.length || 0})</span>
                  
                  <div className="space-y-2 max-h-[220px] overflow-y-auto pr-1">
                    {connectedDetails?.nodes.map((node, index) => {
                      const link = connectedDetails.links[index];
                      return (
                        <div 
                          key={node.id} 
                          className="p-2.5 rounded-xl bg-slate-900 border border-dark-border/60 hover:border-brand-500/20 flex items-center justify-between text-xs cursor-pointer transition-colors"
                          onClick={() => setSelectedNode(node)}
                        >
                          <div className="flex items-center gap-2 min-w-0">
                            <span 
                              className="w-1.5 h-1.5 rounded-full shrink-0" 
                              style={{ backgroundColor: getNodeColor(node.type) }}
                            />
                            <span className="font-semibold text-slate-200 truncate">{node.label}</span>
                          </div>
                          
                          <span className="text-[8px] bg-slate-800 text-slate-400 px-1.5 py-0.5 rounded font-bold uppercase tracking-wider shrink-0 ml-2">
                            {link?.type.replace('_', ' ')}
                          </span>
                        </div>
                      );
                    })}
                  </div>
                </div>

              </div>

              {/* Actions footer depending on node type */}
              <div className="pt-4 border-t border-dark-border/40">
                {selectedNode.type === 'candidate' ? (
                  <Link
                    to={`/candidate/${selectedNode.id}`}
                    className="w-full bg-brand-600 hover:bg-brand-700 text-white font-semibold text-xs py-2 px-4 rounded-xl flex items-center justify-center gap-1.5 transition-colors shadow-md shadow-brand-700/10"
                  >
                    <span>Inspect Profile</span>
                    <ChevronRight size={14} />
                  </Link>
                ) : (
                  <button
                    onClick={() => {
                      // Filter down search bar query to node label
                      setSearchQuery(selectedNode.label);
                    }}
                    className="w-full bg-slate-900 hover:bg-slate-800 text-slate-300 font-semibold text-xs py-2 px-4 rounded-xl border border-dark-border flex items-center justify-center gap-1.5 transition-colors"
                  >
                    <Maximize2 size={14} className="text-brand-500" />
                    <span>Focus Node Hub</span>
                  </button>
                )}
              </div>

            </div>
          ) : (
            <div className="glass-panel rounded-3xl p-6 flex flex-col items-center justify-center text-center flex-1 border border-dark-border/80">
              <GitFork size={32} className="text-slate-600 mb-3 animate-pulse" />
              <h4 className="text-xs font-bold text-white uppercase tracking-wider mb-1">Select an Entity</h4>
              <p className="text-[10px] text-slate-500 max-w-[160px] leading-relaxed">
                Click on any node in the relationship graph to inspect its properties and connected nodes.
              </p>
            </div>
          )}
        </div>

      </div>

    </div>
  );
};
