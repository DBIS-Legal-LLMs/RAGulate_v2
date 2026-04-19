"use client";

import { useEffect, useState, useRef } from "react";
import dynamic from "next/dynamic";
import { graphMLtoForceData } from "@/utils/graphml";
import { useTheme } from "@/app/components/theme-provider";

type GraphData = { nodes: any[]; links: any[] };

const ForceGraph2D = dynamic(() => import("react-force-graph-2d"), {
  ssr: false,
});

export function GraphBackground() {
  const { theme } = useTheme();
  const [data, setData] = useState<GraphData>({ nodes: [], links: [] });
  const [dimensions, setDimensions] = useState({ width: 0, height: 0 });
  const [linkColor, setLinkColor] = useState(() => {
    if (typeof window === "undefined") return "#000000";
    return document.documentElement.classList.contains("dark")
      ? "#8a8a8a"
      : "#000000";
  });
  const graphRef = useRef<any>(null);

  useEffect(() => {
    const update = () =>
      setDimensions({ width: window.innerWidth, height: window.innerHeight });
    update();
    window.addEventListener("resize", update);
    return () => window.removeEventListener("resize", update);
  }, []);

  useEffect(() => {
    if (!theme) return;
    const isDark =
      theme === "dark" ||
      (theme === "system" &&
        window.matchMedia("(prefers-color-scheme: dark)").matches);
    setLinkColor(isDark ? "#8a8a8a" : "#000000");
  }, [theme]);

  useEffect(() => {
    fetch("/graph_chunk_entity_relation.graphml")
      .then((r) => r.text())
      .then((xml) => setData(graphMLtoForceData(xml)))
      .catch(console.error);
  }, []);

  // Einmalig reinzoomen sobald Daten geladen sind
  useEffect(() => {
    if (data.nodes.length === 0) return;
    setTimeout(() => {
      graphRef.current?.zoom(5, 800); // ← Zoomlevel anpassen (2-8)
      graphRef.current?.centerAt(0, 0, 800);
    }, 600);
  }, [data]);

  return (
    <div className="absolute inset-0 z-0 pointer-events-none opacity-5 overflow-hidden">
      <ForceGraph2D
        ref={graphRef}
        graphData={data}
        width={dimensions.width}
        height={dimensions.height}
        linkColor={() => linkColor}
        nodeColor={() => linkColor}
        linkDirectionalParticles={1}
        linkDirectionalParticleSpeed={0.0002}
        linkDirectionalParticleColor={() => linkColor}
        enableZoomInteraction={false}
        enablePanInteraction={false}
        enableNodeDrag={false}
        nodeCanvasObjectMode={() => "replace"}
        nodeCanvasObject={(node: any, ctx) => {
          ctx.beginPath();
          ctx.arc(node.x, node.y, 2, 0, 2 * Math.PI);
          ctx.fillStyle = linkColor;
          ctx.globalAlpha = 0.6;
          ctx.fill();
          ctx.globalAlpha = 1;
        }}
      />
    </div>
  );
}
