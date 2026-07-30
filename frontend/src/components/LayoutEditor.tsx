import React, { useState, useRef, useCallback, useEffect } from 'react';
import { Post } from '../types';
import html2canvas from 'html2canvas';
import { DndProvider, useDrag, useDrop } from 'react-dnd';
import { HTML5Backend } from 'react-dnd-html5-backend';

// ===== DESIGN SYSTEM =====
const COLORS = {
  primary: '#E1306C',
  primaryDark: '#B0245A',
  secondary: '#2196F3',
  success: '#4CAF50',
  warning: '#FF9800',
  danger: '#f44336',
  dark: '#222',
  darker: '#1a1a1a',
  light: '#f5f5f5',
  text: '#ffffff',
  textMuted: '#aaaaaa',
  border: '#444',
  canvasBg: '#2a2a2a',
};

const SPACING = {
  xs: '4px',
  sm: '8px',
  md: '12px',
  lg: '16px',
  xl: '24px',
};

const FONT = {
  size: '14px',
  sizeSmall: '12px',
  sizeLarge: '16px',
  family: "'Segoe UI', system-ui, -apple-system, sans-serif",
};

// ===== TYPES =====
interface LayoutItem {
  id: string;
  postId: string;
  x: number;
  y: number;
  width: number;
  height: number;
  type: 'image' | 'text';
  post?: Post;
  text?: string;
  fontFamily?: string;
  fontSize?: number;
  color?: string;
  backgroundColor?: string;
  borderColor?: string;
  borderWidth?: number;
  strokeColor?: string;
  strokeWidth?: number;
  rotation?: number;
  opacity?: number;
}

// ===== CONSTANTS =====
const PAGE_PRESETS: Record<string, { width: number; height: number; label: string }> = {
  a4: { width: 2480, height: 3508, label: 'A4' },
  letter: { width: 2550, height: 3300, label: 'Letter' },
  square: { width: 3000, height: 3000, label: 'Square' },
  hd: { width: 1920, height: 1080, label: 'HD' },
  '4k': { width: 3840, height: 2160, label: '4K' },
  custom: { width: 1920, height: 1080, label: 'Custom' },
};

const ITEM_TYPE = 'LAYOUT_ITEM';
const STORAGE_KEY = 'layout_editor_settings';

// ===== GRID OVERLAY =====
const GridOverlay: React.FC<{ size: number; width: number; height: number }> = ({ size, width, height }) => {
  const numCols = Math.floor(width / size);
  const numRows = Math.floor(height / size);
  return (
    <div style={{ position: 'absolute', top: 0, left: 0, width: '100%', height: '100%', pointerEvents: 'none' }}>
      <svg width="100%" height="100%" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <pattern id="gridPattern" width={size} height={size} patternUnits="userSpaceOnUse">
            <circle cx={size / 2} cy={size / 2} r="1" fill="#888" />
          </pattern>
        </defs>
        <rect width="100%" height="100%" fill="url(#gridPattern)" />
        <g fontSize="10" fill="#aaa" fontFamily="monospace">
          {Array.from({ length: numCols + 1 }, (_, i) => (
            <text key={`col-${i}`} x={i * size + 4} y={14}>{i * size}</text>
          ))}
          {Array.from({ length: numRows + 1 }, (_, i) => (
            <text key={`row-${i}`} x={4} y={i * size + 14}>{i * size}</text>
          ))}
        </g>
      </svg>
    </div>
  );
};

// ===== DRAGGABLE THUMBNAIL =====
const DraggableThumb: React.FC<{
  post: Post;
  isSelected: boolean;
  onToggle: (e?: React.MouseEvent) => void;
  onDoubleClick: () => void;
}> = ({ post, isSelected, onToggle, onDoubleClick }) => {
  const [{ isDragging }, drag] = useDrag(() => ({
    type: ITEM_TYPE,
    item: { postId: post.id, post },
    collect: (monitor) => ({
      isDragging: !!monitor.isDragging(),
    }),
  }));

  const thumbUrl = post.thumbnail || post.media[0] || '';
  return (
    <div
      ref={drag}
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: SPACING.sm,
        padding: SPACING.xs,
        background: isSelected ? COLORS.primary : 'transparent',
        borderRadius: '4px',
        opacity: isDragging ? 0.4 : 1,
        cursor: 'grab',
        border: isSelected ? `2px solid ${COLORS.primary}` : '2px solid transparent',
        touchAction: 'none',
      }}
      onClick={(e) => { e.stopPropagation(); onToggle(e); }}
      onDoubleClick={onDoubleClick}
    >
      <img src={thumbUrl} alt={post.id} style={{ width: '40px', height: '40px', objectFit: 'cover', borderRadius: '2px' }} />
      <span style={{ fontSize: FONT.sizeSmall, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{post.id}</span>
    </div>
  );
};

// ===== DROP ZONE =====
const DropZone: React.FC<{
  children: React.ReactNode;
  onDrop: (item: { post: Post; x: number; y: number }) => void;
}> = ({ children, onDrop }) => {
  const [{ isOver }, drop] = useDrop(() => ({
    accept: ITEM_TYPE,
    drop: (item: { post: Post }, monitor) => {
      const clientOffset = monitor.getClientOffset();
      if (!clientOffset) return;
      onDrop({ post: item.post, x: clientOffset.x - 100, y: clientOffset.y - 100 });
    },
    collect: (monitor) => ({
      isOver: !!monitor.isOver(),
    }),
  }));

  return (
    <div ref={drop} style={{ position: 'relative', width: '100%', height: '100%', background: isOver ? `rgba(225,48,108,0.1)` : 'transparent' }}>
      {children}
    </div>
  );
};

// ===== DETAIL MODAL =====
const DetailModal: React.FC<{ post: Post; onClose: () => void }> = ({ post, onClose }) => {
  const media = post.media || [];
  return (
    <div
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        width: '100%',
        height: '100%',
        background: 'rgba(0,0,0,0.85)',
        zIndex: 10000,
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        padding: SPACING.md,
      }}
      onClick={onClose}
    >
      <div
        style={{
          background: COLORS.dark,
          padding: SPACING.xl,
          borderRadius: '8px',
          maxWidth: '90vw',
          maxHeight: '90vh',
          overflow: 'auto',
          color: COLORS.text,
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <h3 style={{ marginTop: 0 }}>{post.id}</h3>
        <div style={{ marginBottom: SPACING.sm }}><strong>Date:</strong> {post.date}</div>
        {post.caption && <div style={{ marginBottom: SPACING.sm }}><strong>Caption:</strong> {post.caption}</div>}
        {post.url && (
          <div style={{ marginBottom: SPACING.sm }}>
            <a href={post.url} target="_blank" rel="noopener noreferrer" style={{ color: COLORS.primary, textDecoration: 'underline' }}>🔗 View on Instagram</a>
          </div>
        )}
        {post.comments && post.comments.length > 0 && (
          <div style={{ marginBottom: SPACING.sm }}>
            <strong>Comments ({post.comments.length}):</strong>
            <ul style={{ maxHeight: '150px', overflow: 'auto', paddingLeft: '20px', fontSize: FONT.sizeSmall }}>
              {post.comments.map((c, i) => <li key={i} style={{ marginBottom: '2px' }}>{c}</li>)}
            </ul>
          </div>
        )}
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: SPACING.sm }}>
          {media.map((src, i) => {
            if (src.endsWith('.mp4') || src.endsWith('.webm')) {
              return <video key={i} src={src} controls style={{ maxWidth: '200px', maxHeight: '200px' }} />;
            } else {
              return <img key={i} src={src} alt={`${post.id}-${i}`} style={{ maxWidth: '200px', maxHeight: '200px', objectFit: 'contain' }} />;
            }
          })}
        </div>
        <button
          onClick={onClose}
          style={{
            marginTop: SPACING.md,
            background: COLORS.border,
            border: 'none',
            color: COLORS.text,
            padding: `${SPACING.sm} ${SPACING.lg}`,
            borderRadius: '4px',
            cursor: 'pointer',
          }}
        >
          Close
        </button>
      </div>
    </div>
  );
};

// ===== TOOLBAR BUTTON =====
const ToolbarButton: React.FC<{
  onClick: () => void;
  icon: string;
  label: string;
  disabled?: boolean;
  variant?: 'primary' | 'secondary' | 'success' | 'warning' | 'danger' | 'default';
}> = ({ onClick, icon, label, disabled = false, variant = 'default' }) => {
  const bgColors = {
    primary: COLORS.primary,
    secondary: COLORS.secondary,
    success: COLORS.success,
    warning: COLORS.warning,
    danger: COLORS.danger,
    default: '#555',
  };
  const bg = bgColors[variant] || bgColors.default;
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      style={{
        background: bg,
        border: 'none',
        color: COLORS.text,
        padding: `${SPACING.sm} ${SPACING.md}`,
        borderRadius: '4px',
        cursor: disabled ? 'not-allowed' : 'pointer',
        opacity: disabled ? 0.5 : 1,
        display: 'flex',
        alignItems: 'center',
        gap: SPACING.xs,
        fontSize: FONT.size,
        fontFamily: FONT.family,
        whiteSpace: 'nowrap',
        minHeight: '44px',
        touchAction: 'manipulation',
      }}
    >
      <span style={{ fontSize: '18px' }}>{icon}</span>
      <span>{label}</span>
    </button>
  );
};

// ===== MAIN COMPONENT =====
const LayoutEditor: React.FC<{ posts: Post[]; onBack: () => void }> = ({ posts, onBack }) => {
  // --- Load settings ---
  const loadSettings = () => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved) return JSON.parse(saved);
    } catch (e) { /* ignore */ }
    return {};
  };
  const saved = loadSettings();

  // --- State ---
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [items, setItems] = useState<LayoutItem[]>([]);
  const [dragTargetId, setDragTargetId] = useState<string | null>(null);
  const [dragOffset, setDragOffset] = useState<{ x: number; y: number } | null>(null);
  const [exportFormat, setExportFormat] = useState<'svg' | 'pdf' | 'png' | 'jpg'>('png');
  const [dpi, setDpi] = useState<number>(saved.dpi || 300);
  const [itemSize, setItemSize] = useState<number>(saved.itemSize || 200);
  const [isExporting, setIsExporting] = useState(false);
  const [selectedItemId, setSelectedItemId] = useState<string | null>(null);
  const [showGrid, setShowGrid] = useState<boolean>(saved.showGrid || false);
  const [gridSize, setGridSize] = useState<number>(saved.gridSize || 50);
  const [backgroundColor, setBackgroundColor] = useState<string>(saved.backgroundColor || '#000000');
  const [backgroundImage, setBackgroundImage] = useState<string>(saved.backgroundImage || '');
  const [backgroundType, setBackgroundType] = useState<'color' | 'transparent' | 'image'>(saved.backgroundType || 'color');
  const [pagePreset, setPagePreset] = useState<string>(saved.pagePreset || 'hd');
  const [customWidth, setCustomWidth] = useState<number>(saved.customWidth || 1920);
  const [customHeight, setCustomHeight] = useState<number>(saved.customHeight || 1080);
  const [sortBy, setSortBy] = useState<'date' | 'caption' | 'id'>(saved.sortBy || 'date');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>(saved.sortOrder || 'asc');
  const [detailPost, setDetailPost] = useState<Post | null>(null);
  const [overlapWarnings, setOverlapWarnings] = useState<string[]>([]);
  const [isDragSelecting, setIsDragSelecting] = useState<boolean>(false);
  const [dragSelectStart, setDragSelectStart] = useState<{ x: number; y: number } | null>(null);
  const [dragSelectEnd, setDragSelectEnd] = useState<{ x: number; y: number } | null>(null);

  // --- Resize state ---
  const [resizeTargetId, setResizeTargetId] = useState<string | null>(null);
  const [resizeStart, setResizeStart] = useState<{ x: number; y: number } | null>(null);
  const [resizeCorner, setResizeCorner] = useState<'se' | 'sw' | 'ne' | 'nw' | null>(null);

  // --- Logging ---
  const [logs, setLogs] = useState<string[]>([]);
  const addLog = (message: string) => {
    console.log(message);
    setLogs((prev) => [...prev, message]);
  };

  const [sidebarOpen, setSidebarOpen] = useState<boolean>(true);
  const containerRef = useRef<HTMLDivElement>(null);

  // --- Save settings ---
  useEffect(() => {
    const settings = { dpi, itemSize, showGrid, gridSize, backgroundColor, backgroundImage, backgroundType, pagePreset, customWidth, customHeight, sortBy, sortOrder };
    localStorage.setItem(STORAGE_KEY, JSON.stringify(settings));
  }, [dpi, itemSize, showGrid, gridSize, backgroundColor, backgroundImage, backgroundType, pagePreset, customWidth, customHeight, sortBy, sortOrder]);

  // --- Global mouseup reset for resize ---
  useEffect(() => {
    const handleGlobalMouseUp = () => {
      if (resizeTargetId || resizeStart || resizeCorner) {
        setResizeTargetId(null);
        setResizeStart(null);
        setResizeCorner(null);
        console.log('Global mouseup reset resize state');
      }
    };
    document.addEventListener('mouseup', handleGlobalMouseUp);
    return () => document.removeEventListener('mouseup', handleGlobalMouseUp);
  }, [resizeTargetId, resizeStart, resizeCorner]);

  // --- Derived ---
  const pageWidth = pagePreset === 'custom' ? customWidth : PAGE_PRESETS[pagePreset]?.width || 1920;
  const pageHeight = pagePreset === 'custom' ? customHeight : PAGE_PRESETS[pagePreset]?.height || 1080;

  // --- Helpers ---
  const genId = () => `${Date.now()}-${Math.random().toString(36).substr(2, 8)}`;

  const checkOverlaps = useCallback(() => {
    const warnings: string[] = [];
    for (let i = 0; i < items.length; i++) {
      for (let j = i + 1; j < items.length; j++) {
        const a = items[i];
        const b = items[j];
        if (a.x < b.x + b.width && a.x + a.width > b.x && a.y < b.y + b.height && a.y + a.height > b.y) {
          warnings.push(`"${a.postId}" overlaps with "${b.postId}"`);
        }
      }
    }
    setOverlapWarnings(warnings);
    return warnings;
  }, [items]);

  // --- Sorting ---
  const sortedPosts = useCallback(() => {
    const sorted = [...posts];
    sorted.sort((a, b) => {
      let valA: string | number = '';
      let valB: string | number = '';
      if (sortBy === 'date') { valA = a.date || ''; valB = b.date || ''; }
      else if (sortBy === 'caption') { valA = a.caption || ''; valB = b.caption || ''; }
      else { valA = a.id; valB = b.id; }
      if (valA < valB) return sortOrder === 'asc' ? -1 : 1;
      if (valA > valB) return sortOrder === 'asc' ? 1 : -1;
      return 0;
    });
    return sorted;
  }, [posts, sortBy, sortOrder]);

  // --- Selection ---
  const toggleSelect = (postId: string, e?: React.MouseEvent) => {
    if (e && (e.ctrlKey || e.metaKey)) {
      const newSet = new Set(selectedIds);
      if (newSet.has(postId)) newSet.delete(postId);
      else newSet.add(postId);
      setSelectedIds(newSet);
      return;
    }
    setSelectedIds(new Set([postId]));
  };

  const selectAll = () => {
    if (selectedIds.size === posts.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(posts.map((p: Post) => p.id)));
    }
  };

  const deselectAll = () => {
    setSelectedIds(new Set());
    setSelectedItemId(null);
  };

  // --- Add text ---
  const addTextBox = () => {
    const newItem: LayoutItem = {
      id: genId(),
      postId: `text-${Date.now()}`,
      x: 100 + Math.random() * 400,
      y: 100 + Math.random() * 300,
      width: 200,
      height: 60,
      type: 'text',
      text: 'Double-click to edit',
      fontFamily: 'Arial',
      fontSize: 24,
      color: '#ffffff',
      backgroundColor: 'transparent',
      borderColor: '#cccccc',
      borderWidth: 0,
      strokeColor: '#000000',
      strokeWidth: 0,
    };
    setItems([...items, newItem]);
    setSelectedItemId(newItem.id);
  };

  // --- Templates ---
  const applyTemplate = (templateName: 'grid' | 'masonry' | 'poster' | 'filmstrip' | 'featured') => {
    const selectedPosts = posts.filter((p: Post) => selectedIds.has(p.id));
    if (selectedPosts.length === 0) {
      alert('Select some posts first!');
      return;
    }

    const gap = 20;
    const margin = 30;
    const cols = 3;
    const W = pageWidth;
    const H = pageHeight;

    let slots: { x: number; y: number; width: number; height: number; label?: string }[] = [];

    if (templateName === 'grid') {
      const innerW = W - margin * 2;
      const innerH = H - margin * 2;
      const rows = Math.ceil(selectedPosts.length / cols);
      const slotW = (innerW - gap * (cols - 1)) / cols;
      const slotH = (innerH - gap * (rows - 1)) / rows;
      for (let i = 0; i < selectedPosts.length; i++) {
        const c = i % cols;
        const r = Math.floor(i / cols);
        slots.push({ x: margin + c * (slotW + gap), y: margin + r * (slotH + gap), width: slotW, height: slotH });
      }
    } else if (templateName === 'masonry') {
      const innerW = W - margin * 2;
      const colWidth = (innerW - gap * (cols - 1)) / cols;
      const colHeights = new Array(cols).fill(margin);
      for (let i = 0; i < selectedPosts.length; i++) {
        const col = colHeights.indexOf(Math.min(...colHeights));
        const h = colWidth * (0.7 + ((i % 5) / 10) * 1.5);
        slots.push({ x: margin + col * (colWidth + gap), y: colHeights[col], width: colWidth, height: h });
        colHeights[col] += h + gap;
      }
    } else if (templateName === 'poster') {
      const innerW = W - margin * 2;
      const innerH = H - margin * 2;
      const heroW = innerW * 0.55;
      const heroH = innerH * 0.65;
      slots.push({ x: margin, y: margin, width: heroW, height: heroH, label: 'hero' });
      const sideCols = 2;
      const sideRows = 3;
      const sideW = innerW - heroW - gap;
      const sideSlotW = (sideW - gap * (sideCols - 1)) / sideCols;
      const sideSlotH = (heroH - gap * (sideRows - 1)) / sideRows;
      for (let i = 0; i < 6; i++) {
        const c = i % sideCols;
        const r = Math.floor(i / sideCols);
        slots.push({ x: margin + heroW + gap + c * (sideSlotW + gap), y: margin + r * (sideSlotH + gap), width: sideSlotW, height: sideSlotH });
      }
      const stripCount = Math.min(5, Math.max(0, selectedPosts.length - 7));
      const stripH = innerH - heroH - gap;
      if (stripCount > 0) {
        const stripSlotW = (innerW - gap * (stripCount - 1)) / stripCount;
        for (let i = 0; i < stripCount; i++) {
          slots.push({ x: margin + i * (stripSlotW + gap), y: margin + heroH + gap, width: stripSlotW, height: stripH });
        }
      }
    } else if (templateName === 'filmstrip') {
      const innerW = W - margin * 2;
      const innerH = H - margin * 2;
      const frameW = (innerW - gap * (selectedPosts.length - 1)) / selectedPosts.length;
      for (let i = 0; i < selectedPosts.length; i++) {
        slots.push({ x: margin + i * (frameW + gap), y: margin, width: frameW, height: innerH });
      }
    } else if (templateName === 'featured') {
      const innerW = W - margin * 2;
      const innerH = H - margin * 2;
      const heroH = innerH * 0.72;
      slots.push({ x: margin, y: margin, width: innerW, height: heroH, label: 'featured' });
      const thumbCount = Math.min(6, selectedPosts.length - 1);
      if (thumbCount > 0) {
        const thumbH = innerH - heroH - gap;
        const thumbW = (innerW - gap * (thumbCount - 1)) / thumbCount;
        for (let i = 0; i < thumbCount; i++) {
          slots.push({ x: margin + i * (thumbW + gap), y: margin + heroH + gap, width: thumbW, height: thumbH });
        }
      }
    }

    const newItems: LayoutItem[] = slots.map((slot, i) => {
      const post = selectedPosts[i] || selectedPosts[0];
      return {
        id: genId(),
        postId: post.id,
        x: slot.x,
        y: slot.y,
        width: slot.width,
        height: slot.height,
        type: 'image',
        post,
      };
    });
    setItems([...items, ...newItems]);
    setTimeout(checkOverlaps, 100);
  };

  // --- Item dragging ---
  const onItemMouseDown = (e: React.MouseEvent, id: string) => {
    if (e.button !== 0) return;
    const rect = (e.target as HTMLElement).getBoundingClientRect();
    setDragTargetId(id);
    setDragOffset({ x: e.clientX - rect.left, y: e.clientY - rect.top });
    setSelectedItemId(id);
    const item = items.find(i => i.id === id);
    if (item && !e.ctrlKey && !e.metaKey) {
      setSelectedIds(new Set([item.postId]));
    }
  };

  // --- Canvas mouse handlers ---
  const onCanvasMouseDown = (e: React.MouseEvent) => {
    console.log("[MouseDown] fired");
    console.log("[MouseDown] target:", (e.target as HTMLElement).tagName, (e.target as HTMLElement).getAttribute("data-item-id"));
    if (e.button !== 0) return;
    if ((e.target as HTMLElement).closest('[data-item-id]')) return;
    deselectAll();
    const rect = containerRef.current?.getBoundingClientRect();
    if (!rect) return;
    setIsDragSelecting(true);
    setDragSelectStart({ x: e.clientX - rect.left, y: e.clientY - rect.top });
    setDragSelectEnd({ x: e.clientX - rect.left, y: e.clientY - rect.top });
  };

  const onCanvasMouseMove = (e: React.MouseEvent) => {
    console.log("[MouseMove] fired, resizeTargetId:", resizeTargetId, "resizeStart:", resizeStart, "resizeCorner:", resizeCorner);
    const rect = containerRef.current?.getBoundingClientRect();
    if (!rect) return;
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    // ---- Drag ----
    if (dragTargetId && dragOffset) {
      const deltaX = x - dragOffset.x;
      const deltaY = y - dragOffset.y;
      const snappedX = Math.round(deltaX / 10) * 10;
      const snappedY = Math.round(deltaY / 10) * 10;
      setItems(items.map((item) => {
        if (selectedIds.has(item.postId)) {
          return { ...item, x: Math.max(0, item.x + deltaX), y: Math.max(0, item.y + deltaY) };
        }
        return item;
      }));
      addLog(`Moved ${selectedIds.size} items to (${Math.round(snappedX)}, ${Math.round(snappedY)})`);
      return;
    }

    // ---- Resize ----
    if (resizeTargetId && resizeStart && resizeCorner) {
      const item = items.find(i => i.id === resizeTargetId);
      if (!item) return;
      let newWidth = item.width;
      let newHeight = item.height;
      const dx = x - resizeStart.x;
      const dy = y - resizeStart.y;
      switch (resizeCorner) {
        case 'se':
          newWidth = Math.max(20, item.width + dx);
          newHeight = Math.max(20, item.height + dy);
          break;
        case 'sw':
          newWidth = Math.max(20, item.width - dx);
          newHeight = Math.max(20, item.height + dy);
          break;
        case 'ne':
          newWidth = Math.max(20, item.width + dx);
          newHeight = Math.max(20, item.height - dy);
          break;
        case 'nw':
          newWidth = Math.max(20, item.width - dx);
          newHeight = Math.max(20, item.height - dy);
          break;
      }
      setItems(items.map(i =>
        i.id === resizeTargetId ? { ...i, width: newWidth, height: newHeight } : i
      ));
      addLog(`Resized item ${resizeTargetId} to ${Math.round(newWidth)}x${Math.round(newHeight)}`);
      return;
    }

    // ---- Drag select ----
    if (isDragSelecting && dragSelectStart) {
      setDragSelectEnd({ x, y });
    }
  };

  const onCanvasMouseUp = (_e: React.MouseEvent) => {
    console.log("[MouseUp] fired, dragTargetId:", dragTargetId, "isDragSelecting:", isDragSelecting);
    if (dragTargetId) {
      setDragTargetId(null);
      setDragOffset(null);
      setResizeTargetId(null);
      setResizeStart(null);
      setResizeCorner(null);
      return;
    }
    if (isDragSelecting && dragSelectStart && dragSelectEnd) {
      const x1 = Math.min(dragSelectStart.x, dragSelectEnd.x);
      const y1 = Math.min(dragSelectStart.y, dragSelectEnd.y);
      const x2 = Math.max(dragSelectStart.x, dragSelectEnd.x);
      const y2 = Math.max(dragSelectStart.y, dragSelectEnd.y);
      const newSelected = new Set(selectedIds);
      items.forEach(item => {
        if (item.x < x2 && item.x + item.width > x1 && item.y < y2 && item.y + item.height > y1) {
          newSelected.add(item.postId);
        }
      });
      setSelectedIds(newSelected);
    }
    setIsDragSelecting(false);
    setDragSelectStart(null);
    setDragSelectEnd(null);
    setResizeTargetId(null);
    setResizeStart(null);
    setResizeCorner(null);
  };

  // --- Drop from sidebar ---
  const handleDrop = (dropped: { post: Post; x: number; y: number }) => {
    const size = itemSize;
    const newItem: LayoutItem = {
      id: genId(),
      postId: dropped.post.id,
      x: Math.max(0, dropped.x),
      y: Math.max(0, dropped.y),
      width: size,
      height: size,
      type: 'image',
      post: dropped.post,
    };
    setItems([...items, newItem]);
    setTimeout(checkOverlaps, 100);
  };

  // --- Layout cleanup ---
  const alignSelected = (direction: 'left' | 'right' | 'top' | 'bottom' | 'center-h' | 'center-v') => {
    const selectedItems = items.filter(item => selectedIds.has(item.postId));
    if (selectedItems.length < 2) return;
    let minX = Math.min(...selectedItems.map(i => i.x));
    let maxX = Math.max(...selectedItems.map(i => i.x + i.width));
    let minY = Math.min(...selectedItems.map(i => i.y));
    let maxY = Math.max(...selectedItems.map(i => i.y + i.height));
    const centerX = (minX + maxX) / 2;
    const centerY = (minY + maxY) / 2;
    const newItems = items.map(item => {
      if (!selectedIds.has(item.postId)) return item;
      let newX = item.x;
      let newY = item.y;
      switch (direction) {
        case 'left': newX = minX; break;
        case 'right': newX = maxX - item.width; break;
        case 'top': newY = minY; break;
        case 'bottom': newY = maxY - item.height; break;
        case 'center-h': newX = centerX - item.width / 2; break;
        case 'center-v': newY = centerY - item.height / 2; break;
      }
      return { ...item, x: newX, y: newY };
    });
    setItems(newItems);
    setTimeout(checkOverlaps, 100);
  };

  const distributeSelected = (axis: 'horizontal' | 'vertical') => {
    const selectedItems = items.filter(item => selectedIds.has(item.postId));
    if (selectedItems.length < 3) return;
    const sorted = [...selectedItems].sort((a, b) => axis === 'horizontal' ? a.x - b.x : a.y - b.y);
    const first = sorted[0];
    const last = sorted[sorted.length - 1];
    const totalSpan = axis === 'horizontal' ? (last.x - first.x) : (last.y - first.y);
    const step = totalSpan / (sorted.length - 1);
    const newItems = items.map(item => {
      if (!selectedIds.has(item.postId)) return item;
      const idx = sorted.findIndex(i => i.id === item.id);
      if (idx === -1 || idx === 0 || idx === sorted.length - 1) return item;
      const pos = axis === 'horizontal' ? first.x + idx * step : first.y + idx * step;
      return { ...item, x: axis === 'horizontal' ? pos : item.x, y: axis === 'vertical' ? pos : item.y };
    });
    setItems(newItems);
    setTimeout(checkOverlaps, 100);
  };

  const snapToGrid = () => {
    if (!showGrid) {
      alert('Grid is off. Turn on Grid first.');
      return;
    }
    const newItems = items.map(item => ({
      ...item,
      x: Math.round(item.x / gridSize) * gridSize,
      y: Math.round(item.y / gridSize) * gridSize,
    }));
    setItems(newItems);
    setTimeout(checkOverlaps, 100);
  };

  const cleanupLayout = () => {
    if (showGrid) snapToGrid();
    const selectedItems = items.filter(item => selectedIds.has(item.postId));
    if (selectedItems.length > 1) {
      const minX = Math.min(...selectedItems.map(i => i.x));
      const minY = Math.min(...selectedItems.map(i => i.y));
      const newItems = items.map(item => {
        if (!selectedIds.has(item.postId)) return item;
        return { ...item, x: showGrid ? Math.round(minX / gridSize) * gridSize : minX, y: showGrid ? Math.round(minY / gridSize) * gridSize : minY };
      });
      setItems(newItems);
    }
    if (selectedItems.length > 2) {
      distributeSelected('horizontal');
      distributeSelected('vertical');
    }
    const warnings = checkOverlaps();
    if (warnings.length > 0) {
      alert('⚠️ Overlap detected:\n' + warnings.join('\n'));
    } else {
      alert('✅ Layout cleaned up successfully!');
    }
  };

  // --- Delete / Clear ---
  const deleteSelected = () => {
    if (!selectedItemId) return;
    setItems(items.filter((item) => item.id !== selectedItemId));
    setSelectedItemId(null);
    setTimeout(checkOverlaps, 100);
  };

  const updateSelected = (props: Partial<LayoutItem>) => {
    if (!selectedItemId) return;
    setItems(items.map((item) => {
      if (item.id === selectedItemId) {
        return { ...item, ...props };
      }
      return item;
    }));
  };

  const clearLayout = () => {
    if (items.length === 0) return;
    if (confirm('Clear all items from the layout?')) {
      setItems([]);
      setOverlapWarnings([]);
      deselectAll();
    }
  };

  // --- Export ---
  const exportPNG = async () => {
    setIsExporting(true);
    try {
      const scale = dpi / 96;
      const canvas = await html2canvas(containerRef.current!, {
        scale,
        useCORS: true,
        allowTaint: false,
        backgroundColor: backgroundType === 'transparent' ? undefined : backgroundColor,
        width: pageWidth,
        height: pageHeight,
      });
      canvas.toBlob((blob) => {
        if (!blob) return;
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `layout_${dpi}dpi.png`;
        a.click();
      }, 'image/png');
    } catch (e) { console.error(e); }
    finally { setIsExporting(false); }
  };

  const exportJPG = async () => {
    setIsExporting(true);
    try {
      const scale = dpi / 96;
      const canvas = await html2canvas(containerRef.current!, {
        scale,
        useCORS: true,
        allowTaint: false,
        backgroundColor: backgroundType === 'transparent' ? '#ffffff' : backgroundColor,
        width: pageWidth,
        height: pageHeight,
      });
      canvas.toBlob((blob) => {
        if (!blob) return;
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `layout_${dpi}dpi.jpg`;
        a.click();
      }, 'image/jpeg', 0.95);
    } catch (e) { console.error(e); }
    finally { setIsExporting(false); }
  };

  const exportSVG = () => {
    let svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${pageWidth}" height="${pageHeight}" viewBox="0 0 ${pageWidth} ${pageHeight}">`;
    if (backgroundType === 'color') {
      svg += `<rect width="100%" height="100%" fill="${backgroundColor}"/>`;
    } else if (backgroundType === 'image' && backgroundImage) {
      svg += `<image href="${backgroundImage}" width="100%" height="100%" preserveAspectRatio="xMidYMid slice"/>`;
    }
    items.forEach((item) => {
      if (item.type === 'image' && item.post) {
    console.log("[RenderLoop] Rendering image item", item.id, "handles inserted");
    const imgUrl = item.post.thumbnail || item.post.media[0] || '';
    // Define isSelected and borderStyle inside the block
    const isSelected = true;  // Force handles to always show
    const borderStyle = isSelected ? `3px solid ${COLORS.primary}` : 'none';
    return (
      <div
        key={item.id}
        data-item-id={item.id}
        style={{
          position: 'absolute',
          left: item.x,
          top: item.y,
          width: item.width,
          height: item.height,
          cursor: 'grab',
          border: borderStyle,
          overflow: 'hidden',
          background: '#fff',
        }}
        onMouseDown={(e) => { e.stopPropagation(); onItemMouseDown(e, item.id); }}
        onDoubleClick={() => item.post && openDetail(item.post)}
      >
        <img
          src={imgUrl}
          alt={item.postId}
          style={{ width: '100%', height: '100%', objectFit: 'contain', pointerEvents: 'none' }}
          onError={(e) => {
            (e.target as HTMLImageElement).src = "data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIyMDAiIGhlaWdodD0iMjAwIj48cmVjdCB3aWR0aD0iMTAwJSIgaGVpZ2h0PSIxMDAlIiBmaWxsPSIjMzMzIi8+PHRleHQgeD0iNTAlIiB5PSI1MCUiIGZvbnQtc2l6ZT0iMTgiIGZpbGw9IiM2NjYiIHRleHQtYW5jaG9yPSJtaWRkbGUiIGR5PSIuM2VtIj5ObyBJbWFnZTwvdGV4dD48L3N2Zz4=";
          }}
        />
        {/* Unconditional resize handles */}
        <div style={{ position: 'absolute', right: -6, bottom: -6, width: 12, height: 12, background: '#E1306C', border: '2px solid white', borderRadius: '2px', cursor: 'nwse-resize', zIndex: 10 }} />
        <div style={{ position: 'absolute', left: -6, bottom: -6, width: 12, height: 12, background: '#E1306C', border: '2px solid white', borderRadius: '2px', cursor: 'nesw-resize', zIndex: 10 }} />
        <div style={{ position: 'absolute', right: -6, top: -6, width: 12, height: 12, background: '#E1306C', border: '2px solid white', borderRadius: '2px', cursor: 'nesw-resize', zIndex: 10 }} />
        <div style={{ position: 'absolute', left: -6, top: -6, width: 12, height: 12, background: '#E1306C', border: '2px solid white', borderRadius: '2px', cursor: 'nwse-resize', zIndex: 10 }} />
        {/* Unconditional resize handles – always visible */}
        <div style={{ position: 'absolute', right: -6, bottom: -6, width: 12, height: 12, background: '#E1306C', border: '2px solid white', borderRadius: '2px', cursor: 'nwse-resize', zIndex: 10 }} />
        <div style={{ position: 'absolute', left: -6, bottom: -6, width: 12, height: 12, background: '#E1306C', border: '2px solid white', borderRadius: '2px', cursor: 'nesw-resize', zIndex: 10 }} />
        <div style={{ position: 'absolute', right: -6, top: -6, width: 12, height: 12, background: '#E1306C', border: '2px solid white', borderRadius: '2px', cursor: 'nesw-resize', zIndex: 10 }} />
        <div style={{ position: 'absolute', left: -6, top: -6, width: 12, height: 12, background: '#E1306C', border: '2px solid white', borderRadius: '2px', cursor: 'nwse-resize', zIndex: 10 }} />
      </div>
    );
  } else if (item.type === 'text' && item.text) {
        const strokeAttr = item.strokeWidth ? `stroke="${item.strokeColor || '#000000'}" stroke-width="${item.strokeWidth}"` : '';
        svg += `<text x="${item.x + 10}" y="${item.y + 40}" font-family="${item.fontFamily || 'Arial'}" font-size="${item.fontSize || 24}" fill="${item.color || '#ffffff'}" font-weight="bold" ${strokeAttr}>${item.text}</text>`;
      }
    });
    svg += '</svg>';
    const blob = new Blob([svg], { type: 'image/svg+xml' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'layout.svg';
    a.click();
  };

  const exportPDF = () => alert('PDF export uses server-side (coming soon)');

  const handleExport = () => {
    if (exportFormat === 'svg') exportSVG();
    else if (exportFormat === 'png') exportPNG();
    else if (exportFormat === 'jpg') exportJPG();
    else exportPDF();
  };

  const openDetail = (post: Post) => setDetailPost(post);
  const closeDetail = () => setDetailPost(null);

  // --- Render ---
  const selectedCount = selectedIds.size;

  return (
    <DndProvider backend={HTML5Backend}>
      <div style={{ width: '100vw', height: '100vh', background: COLORS.dark, color: COLORS.text, display: 'flex', flexDirection: 'column', fontFamily: FONT.family }}>
        {/* Toolbar */}
        <div style={{ background: COLORS.darker, padding: SPACING.sm, display: 'flex', flexWrap: 'wrap', gap: SPACING.xs, alignItems: 'center', borderBottom: `1px solid ${COLORS.border}`, minHeight: '56px', overflow: 'auto' }}>
          <ToolbarButton onClick={onBack} icon="←" label="Back" variant="default" />
          <ToolbarButton onClick={selectAll} icon="☐" label={selectedCount === posts.length ? 'Deselect All' : 'Select All'} variant="primary" />
          <span style={{ color: COLORS.textMuted, fontSize: FONT.sizeSmall }}>|</span>
          <ToolbarButton onClick={() => applyTemplate('grid')} icon="📐" label="Grid" variant="secondary" />
          <ToolbarButton onClick={() => applyTemplate('masonry')} icon="🧱" label="Masonry" variant="secondary" />
          <ToolbarButton onClick={() => applyTemplate('poster')} icon="🎬" label="Poster" variant="secondary" />
          <ToolbarButton onClick={() => applyTemplate('filmstrip')} icon="🎞️" label="Film" variant="secondary" />
          <ToolbarButton onClick={() => applyTemplate('featured')} icon="⭐" label="Featured" variant="secondary" />
          <span style={{ color: COLORS.textMuted, fontSize: FONT.sizeSmall }}>|</span>
          <ToolbarButton onClick={addTextBox} icon="➕" label="Text" variant="default" />
          <ToolbarButton onClick={deleteSelected} icon="🗑️" label="Delete" variant="danger" disabled={!selectedItemId} />
          <ToolbarButton onClick={clearLayout} icon="🧹" label="Clear" variant="danger" />
          <span style={{ color: COLORS.textMuted, fontSize: FONT.sizeSmall }}>|</span>
          <ToolbarButton onClick={() => setSidebarOpen(!sidebarOpen)} icon="☰" label={sidebarOpen ? 'Hide' : 'Show'} variant="default" />
          <span style={{ color: COLORS.textMuted, fontSize: FONT.sizeSmall }}>|</span>

          {/* Align / Distribute */}
          <ToolbarButton onClick={() => alignSelected('left')} icon="⬅" label="L" variant="default" />
          <ToolbarButton onClick={() => alignSelected('right')} icon="➡" label="R" variant="default" />
          <ToolbarButton onClick={() => alignSelected('top')} icon="⬆" label="T" variant="default" />
          <ToolbarButton onClick={() => alignSelected('bottom')} icon="⬇" label="B" variant="default" />
          <ToolbarButton onClick={() => alignSelected('center-h')} icon="↔" label="CH" variant="default" />
          <ToolbarButton onClick={() => alignSelected('center-v')} icon="↕" label="CV" variant="default" />
          <ToolbarButton onClick={() => distributeSelected('horizontal')} icon="⋮" label="DH" variant="default" />
          <ToolbarButton onClick={() => distributeSelected('vertical')} icon="⋯" label="DV" variant="default" />
          <ToolbarButton onClick={cleanupLayout} icon="🧹" label="Clean" variant="success" />
          <span style={{ color: COLORS.textMuted, fontSize: FONT.sizeSmall }}>|</span>

          {/* Grid */}
          <ToolbarButton onClick={() => setShowGrid(!showGrid)} icon="▦" label={showGrid ? 'Grid On' : 'Grid Off'} variant={showGrid ? 'success' : 'default'} />
          {showGrid && (
            <input type="number" value={gridSize} onChange={(e) => setGridSize(parseInt(e.target.value) || 50)} style={{ width: '60px', padding: SPACING.xs, background: COLORS.border, color: COLORS.text, border: 'none', borderRadius: '4px', fontSize: FONT.size }} />
          )}
          <ToolbarButton onClick={snapToGrid} icon="⊞" label="Snap" variant="secondary" />
          <span style={{ color: COLORS.textMuted, fontSize: FONT.sizeSmall }}>|</span>

          {/* Page / Background / Export */}
          <select value={pagePreset} onChange={(e) => setPagePreset(e.target.value)} style={{ background: COLORS.border, color: COLORS.text, border: 'none', padding: SPACING.xs, borderRadius: '4px', fontSize: FONT.size, height: '36px' }}>
            {Object.entries(PAGE_PRESETS).map(([key, val]) => (
              <option key={key} value={key}>{val.label}</option>
            ))}
          </select>
          {pagePreset === 'custom' && (
            <>
              <input type="number" value={customWidth} onChange={(e) => setCustomWidth(parseInt(e.target.value) || 1920)} style={{ width: '60px', background: COLORS.border, color: COLORS.text, border: 'none', padding: SPACING.xs, borderRadius: '4px' }} />
              <span>x</span>
              <input type="number" value={customHeight} onChange={(e) => setCustomHeight(parseInt(e.target.value) || 1080)} style={{ width: '60px', background: COLORS.border, color: COLORS.text, border: 'none', padding: SPACING.xs, borderRadius: '4px' }} />
            </>
          )}
          <span style={{ color: COLORS.textMuted, fontSize: FONT.sizeSmall }}>|</span>

          <select value={backgroundType} onChange={(e) => setBackgroundType(e.target.value as any)} style={{ background: COLORS.border, color: COLORS.text, border: 'none', padding: SPACING.xs, borderRadius: '4px', fontSize: FONT.size, height: '36px' }}>
            <option value="color">Color</option>
            <option value="transparent">Transparent</option>
            <option value="image">Image</option>
          </select>
          {backgroundType === 'color' && (
            <input type="color" value={backgroundColor} onChange={(e) => setBackgroundColor(e.target.value)} style={{ width: '36px', height: '36px', padding: 0, border: 'none', cursor: 'pointer' }} />
          )}
          {backgroundType === 'image' && (
            <input type="text" placeholder="Image URL" value={backgroundImage} onChange={(e) => setBackgroundImage(e.target.value)} style={{ flex: 1, minWidth: '120px', background: COLORS.border, color: COLORS.text, border: 'none', padding: SPACING.xs, borderRadius: '4px' }} />
          )}
          <span style={{ color: COLORS.textMuted, fontSize: FONT.sizeSmall }}>|</span>

          <select value={sortBy} onChange={(e) => setSortBy(e.target.value as any)} style={{ background: COLORS.border, color: COLORS.text, border: 'none', padding: SPACING.xs, borderRadius: '4px', fontSize: FONT.size, height: '36px' }}>
            <option value="date">Sort by Date</option>
            <option value="caption">Sort by Caption</option>
            <option value="id">Sort by ID</option>
          </select>
          <ToolbarButton onClick={() => setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')} icon={sortOrder === 'asc' ? '↑' : '↓'} label="Order" variant="default" />
          <span style={{ color: COLORS.textMuted, fontSize: FONT.sizeSmall }}>|</span>

          <select value={exportFormat} onChange={(e) => setExportFormat(e.target.value as any)} style={{ background: COLORS.border, color: COLORS.text, border: 'none', padding: SPACING.xs, borderRadius: '4px', fontSize: FONT.size, height: '36px' }}>
            <option value="png">PNG</option><option value="jpg">JPG</option><option value="svg">SVG</option><option value="pdf">PDF</option>
          </select>
          <input type="number" value={dpi} onChange={(e) => setDpi(parseInt(e.target.value))} min="72" max="1200" style={{ width: '60px', background: COLORS.border, color: COLORS.text, border: 'none', padding: SPACING.xs, borderRadius: '4px' }} />
          <span>DPI</span>
          <input type="number" value={itemSize} onChange={(e) => setItemSize(parseInt(e.target.value))} min="50" max="600" style={{ width: '60px', background: COLORS.border, color: COLORS.text, border: 'none', padding: SPACING.xs, borderRadius: '4px' }} />
          <span>px</span>
          <ToolbarButton onClick={handleExport} icon="⬇" label={isExporting ? 'Exporting...' : 'Export'} variant="warning" disabled={isExporting} />

          {selectedItemId && items.find(i => i.id === selectedItemId)?.type === 'text' && (
            <>
              <span style={{ color: COLORS.textMuted }}>|</span>
              <input type="color" value={items.find(i => i.id === selectedItemId)?.color || '#ffffff'} onChange={(e) => updateSelected({ color: e.target.value })} style={{ width: '36px', height: '36px', padding: 0, border: 'none', cursor: 'pointer' }} />
              <span style={{ fontSize: FONT.sizeSmall }}>Text</span>
              <input type="color" value={items.find(i => i.id === selectedItemId)?.strokeColor || '#000000'} onChange={(e) => updateSelected({ strokeColor: e.target.value })} style={{ width: '36px', height: '36px', padding: 0, border: 'none', cursor: 'pointer' }} />
              <span style={{ fontSize: FONT.sizeSmall }}>Outline</span>
              <input type="number" value={items.find(i => i.id === selectedItemId)?.strokeWidth || 0} onChange={(e) => updateSelected({ strokeWidth: parseInt(e.target.value) || 0 })} style={{ width: '50px', background: COLORS.border, color: COLORS.text, border: 'none', padding: SPACING.xs, borderRadius: '4px' }} />
            </>
          )}
        </div>

        {/* Log Panel */}
        <div style={{ background: COLORS.darker, padding: SPACING.sm, borderBottom: `1px solid ${COLORS.border}`, maxHeight: '80px', overflow: 'auto', fontSize: FONT.sizeSmall, color: COLORS.textMuted, display: 'flex', flexWrap: 'wrap', gap: SPACING.xs }}>
          {logs.map((log, idx) => (
            <span key={idx} style={{ background: COLORS.border, padding: '2px 6px', borderRadius: '4px' }}>{log}</span>
          ))}
        </div>

        {/* Overlap warnings */}
        {overlapWarnings.length > 0 && (
          <div style={{ background: COLORS.danger, color: COLORS.text, padding: SPACING.xs, fontSize: FONT.sizeSmall, display: 'flex', alignItems: 'center', gap: SPACING.sm }}>
            ⚠️ {overlapWarnings.length} overlap(s): {overlapWarnings.join('; ')}
          </div>
        )}

        {/* Main layout */}
        <div style={{ flex: 1, overflow: 'auto', padding: SPACING.sm, display: 'flex', gap: SPACING.sm }}>
          {/* Sidebar */}
          {sidebarOpen && (
            <div style={{ width: '200px', minWidth: '200px', background: COLORS.darker, padding: SPACING.sm, borderRadius: '8px', maxHeight: '80vh', overflow: 'auto' }}>
              <h4 style={{ margin: '0 0 SPACING.sm 0', fontSize: FONT.size, color: COLORS.textMuted }}>Selection ({selectedCount})</h4>
              {sortedPosts().map((post: Post) => (
                <DraggableThumb
                  key={post.id}
                  post={post}
                  isSelected={selectedIds.has(post.id)}
                  onToggle={(e) => toggleSelect(post.id, e)}
                  onDoubleClick={() => openDetail(post)}
                />
              ))}
            </div>
          )}

          {/* Canvas */}
          <div
            style={{ flex: 1, position: 'relative', background: COLORS.canvasBg, borderRadius: '8px', overflow: 'auto' }}
            onMouseMove={onCanvasMouseMove}
            onMouseUp={onCanvasMouseUp}
            onMouseLeave={onCanvasMouseUp}
          >
            <DropZone onDrop={handleDrop}>
              <div
                ref={containerRef}
                style={{
                  position: 'relative',
                  width: pageWidth,
                  height: pageHeight,
                  background: backgroundType === 'color' ? backgroundColor : (backgroundType === 'transparent' ? 'transparent' : 'inherit'),
                  margin: '0 auto',
                  cursor: 'default',
                }}
                onMouseDown={onCanvasMouseDown}
              >
                {showGrid && <GridOverlay size={gridSize} width={pageWidth} height={pageHeight} />}
                {backgroundType === 'image' && backgroundImage && (
                  <img src={backgroundImage} alt="Background" style={{ position: 'absolute', top: 0, left: 0, width: '100%', height: '100%', objectFit: 'cover', pointerEvents: 'none' }} />
                )}
                {isDragSelecting && dragSelectStart && dragSelectEnd && (
                  <div style={{
                    position: 'absolute',
                    left: Math.min(dragSelectStart.x, dragSelectEnd.x),
                    top: Math.min(dragSelectStart.y, dragSelectEnd.y),
                    width: Math.abs(dragSelectEnd.x - dragSelectStart.x),
                    height: Math.abs(dragSelectEnd.y - dragSelectStart.y),
                    border: `1px dashed ${COLORS.primary}`,
                    background: 'rgba(225,48,108,0.1)',
                    pointerEvents: 'none',
                  }} />
                )}
                {items.map((item) => {
                  const isSelected = selectedItemId === item.id || selectedIds.has(item.postId);
                  const borderStyle = isSelected ? `3px solid ${COLORS.primary}` : (item.borderWidth ? `${item.borderWidth}px solid ${item.borderColor || '#ccc'}` : 'none');

                  if (item.type === 'image' && item.post) {
    const imgUrl = item.post.thumbnail || item.post.media[0] || '';
    // Force isSelected to true so handles always show
    const isSelected = true;
    const borderStyle = isSelected ? `3px solid ${COLORS.primary}` : 'none';
    return (
      <div
        key={item.id}
        data-item-id={item.id}
        style={{
          position: 'absolute',
          left: item.x,
          top: item.y,
          width: item.width,
          height: item.height,
          cursor: 'grab',
          border: borderStyle,
          overflow: 'hidden',
          background: '#fff',
        }}
        onMouseDown={(e) => { e.stopPropagation(); onItemMouseDown(e, item.id); }}
        onDoubleClick={() => item.post && openDetail(item.post)}
      >
        <img
          src={imgUrl}
          alt={item.postId}
          style={{ width: '100%', height: '100%', objectFit: 'contain', pointerEvents: 'none' }}
          onError={(e) => {
            (e.target as HTMLImageElement).src = "data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIyMDAiIGhlaWdodD0iMjAwIj48cmVjdCB3aWR0aD0iMTAwJSIgaGVpZ2h0PSIxMDAlIiBmaWxsPSIjMzMzIi8+PHRleHQgeD0iNTAlIiB5PSI1MCUiIGZvbnQtc2l6ZT0iMTgiIGZpbGw9IiM2NjYiIHRleHQtYW5jaG9yPSJtaWRkbGUiIGR5PSIuM2VtIj5ObyBJbWFnZTwvdGV4dD48L3N2Zz4=";
          }}
        />
        {/* Unconditional resize handles */}
        <div style={{ position: 'absolute', right: -6, bottom: -6, width: 12, height: 12, background: '#E1306C', border: '2px solid white', borderRadius: '2px', cursor: 'nwse-resize', zIndex: 10 }} />
        <div style={{ position: 'absolute', left: -6, bottom: -6, width: 12, height: 12, background: '#E1306C', border: '2px solid white', borderRadius: '2px', cursor: 'nesw-resize', zIndex: 10 }} />
        <div style={{ position: 'absolute', right: -6, top: -6, width: 12, height: 12, background: '#E1306C', border: '2px solid white', borderRadius: '2px', cursor: 'nesw-resize', zIndex: 10 }} />
        <div style={{ position: 'absolute', left: -6, top: -6, width: 12, height: 12, background: '#E1306C', border: '2px solid white', borderRadius: '2px', cursor: 'nwse-resize', zIndex: 10 }} />
        {/* Unconditional resize handles */}
        <div style={{ position: 'absolute', right: -6, bottom: -6, width: 12, height: 12, background: '#E1306C', border: '2px solid white', borderRadius: '2px', cursor: 'nwse-resize', zIndex: 10 }} />
        <div style={{ position: 'absolute', left: -6, bottom: -6, width: 12, height: 12, background: '#E1306C', border: '2px solid white', borderRadius: '2px', cursor: 'nesw-resize', zIndex: 10 }} />
        <div style={{ position: 'absolute', right: -6, top: -6, width: 12, height: 12, background: '#E1306C', border: '2px solid white', borderRadius: '2px', cursor: 'nesw-resize', zIndex: 10 }} />
        <div style={{ position: 'absolute', left: -6, top: -6, width: 12, height: 12, background: '#E1306C', border: '2px solid white', borderRadius: '2px', cursor: 'nwse-resize', zIndex: 10 }} />
        {/* Unconditional resize handles – always visible */}
        <div style={{ position: 'absolute', right: -6, bottom: -6, width: 12, height: 12, background: '#E1306C', border: '2px solid white', borderRadius: '2px', cursor: 'nwse-resize', zIndex: 10 }} />
        <div style={{ position: 'absolute', left: -6, bottom: -6, width: 12, height: 12, background: '#E1306C', border: '2px solid white', borderRadius: '2px', cursor: 'nesw-resize', zIndex: 10 }} />
        <div style={{ position: 'absolute', right: -6, top: -6, width: 12, height: 12, background: '#E1306C', border: '2px solid white', borderRadius: '2px', cursor: 'nesw-resize', zIndex: 10 }} />
        <div style={{ position: 'absolute', left: -6, top: -6, width: 12, height: 12, background: '#E1306C', border: '2px solid white', borderRadius: '2px', cursor: 'nwse-resize', zIndex: 10 }} />
      </div>
    );
  } else if (item.type === 'text') {
                    return (
                      <div
                        key={item.id}
                        style={{
                          position: 'absolute',
                          left: item.x,
                          top: item.y,
                          width: item.width,
                          height: item.height,
                          cursor: 'grab',
                          border: borderStyle,
                          background: item.backgroundColor || 'transparent',
                          overflow: 'hidden',
                          padding: '4px',
                        }}
                        onMouseDown={(e) => { e.stopPropagation(); onItemMouseDown(e, item.id); }}
                        onDoubleClick={() => {
                          const newText = prompt('Edit text:', item.text || '');
                          if (newText !== null) updateSelected({ text: newText });
                        }}
                      >
                        <div style={{
                          fontFamily: item.fontFamily || 'Arial',
                          fontSize: item.fontSize || 24,
                          color: item.color || '#ffffff',
                          fontWeight: 'bold',
                          width: '100%',
                          height: '100%',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          textShadow: item.strokeWidth ? `0 0 ${item.strokeWidth}px ${item.strokeColor || '#000000'}` : 'none',
                        }}>
                          {item.text || 'Double-click to edit'}
                        </div>
                        {/* Resize handles for text */}
                        {isSelected && (
                          <>
                            <div
                              style={{
                                position: 'absolute',
                                right: -6,
                                bottom: -6,
                                width: 12,
                                height: 12,
                                background: COLORS.primary,
                                border: '2px solid white',
                                borderRadius: '2px',
                                cursor: 'nwse-resize',
                                zIndex: 10,
                              }}
                              onMouseDown={(e) => {
                                e.stopPropagation();
                                e.preventDefault();
                                console.log("[Resize] handle clicked for item", item.id); setResizeTargetId(item.id);
                                setResizeCorner('se');
                                setResizeStart({ x: e.clientX, y: e.clientY });
                              }}
                            />
                            <div
                              style={{
                                position: 'absolute',
                                left: -6,
                                bottom: -6,
                                width: 12,
                                height: 12,
                                background: COLORS.primary,
                                border: '2px solid white',
                                borderRadius: '2px',
                                cursor: 'nesw-resize',
                                zIndex: 10,
                              }}
                              onMouseDown={(e) => {
                                e.stopPropagation();
                                e.preventDefault();
                                console.log("[Resize] handle clicked for item", item.id); setResizeTargetId(item.id);
                                setResizeCorner('sw');
                                setResizeStart({ x: e.clientX, y: e.clientY });
                              }}
                            />
                            <div
                              style={{
                                position: 'absolute',
                                right: -6,
                                top: -6,
                                width: 12,
                                height: 12,
                                background: COLORS.primary,
                                border: '2px solid white',
                                borderRadius: '2px',
                                cursor: 'nesw-resize',
                                zIndex: 10,
                              }}
                              onMouseDown={(e) => {
                                e.stopPropagation();
                                e.preventDefault();
                                console.log("[Resize] handle clicked for item", item.id); setResizeTargetId(item.id);
                                setResizeCorner('ne');
                                setResizeStart({ x: e.clientX, y: e.clientY });
                              }}
                            />
                            <div
                              style={{
                                position: 'absolute',
                                left: -6,
                                top: -6,
                                width: 12,
                                height: 12,
                                background: COLORS.primary,
                                border: '2px solid white',
                                borderRadius: '2px',
                                cursor: 'nwse-resize',
                                zIndex: 10,
                              }}
                              onMouseDown={(e) => {
                                e.stopPropagation();
                                e.preventDefault();
                                console.log("[Resize] handle clicked for item", item.id); setResizeTargetId(item.id);
                                setResizeCorner('nw');
                                setResizeStart({ x: e.clientX, y: e.clientY });
                              }}
                            />
                          </>
                        )}
                      </div>
                    );
                  }
                  return null;
                })}
              </div>
            </DropZone>
          </div>
        </div>

        {/* Detail Modal */}
        {detailPost && <DetailModal post={detailPost} onClose={closeDetail} />}
      </div>
    </DndProvider>
  );
};

export default LayoutEditor;