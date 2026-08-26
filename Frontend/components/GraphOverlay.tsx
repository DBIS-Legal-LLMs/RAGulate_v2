"use client";

import { useEffect, useState } from "react";
import dynamic from "next/dynamic";
import { Button } from "@/components/ui/button";
import { graphMLtoForceData } from "@/utils/graphml";
import { useTheme } from "@/app/components/theme-provider";
import { useTranslation } from "react-i18next";

const BACKEND_URL = process.env.NEXT_PUBLIC_API_BACKEND || "http://134.60.71.197:8000";

type GraphData = {
  nodes: any[];
  links: any[];
};

const ForceGraph2D = dynamic(() => import("react-force-graph-2d"), {
  ssr: false,
});

export function GraphOverlay({
  open,
  onClose,
}: {
  open: boolean;
  onClose: () => void;
}) {
  const { theme } = useTheme();
  const { t } = useTranslation();

  const [data, setData] = useState<GraphData>({ nodes: [], links: [] });
  const [linkColor, setLinkColor] = useState(() => {
    if (typeof window === "undefined") return "#000000";
    return document.documentElement.classList.contains("dark")
      ? "#4b4b4b"
      : "#505050";
  });
  const [selectedNode, setSelectedNode] = useState<any | null>(null);
  const [dimensions, setDimensions] = useState({ width: 0, height: 0 });
  const [loading, setLoading] = useState(false);
  const [graphError, setGraphError] = useState<string | null>(null);

  /* -------------------- Dimensions -------------------- */
  useEffect(() => {
    const update = () => {
      setDimensions({
        width: window.innerWidth * 0.95,
        height: window.innerHeight * 0.85,
      });
    };

    update();
    window.addEventListener("resize", update);
    return () => window.removeEventListener("resize", update);
  }, []);

  /* -------------------- Theme -------------------- */
  useEffect(() => {
    if (!theme) return;
    const isDark =
      theme === "dark" ||
      (theme === "system" &&
        window.matchMedia("(prefers-color-scheme: dark)").matches);
    setLinkColor(isDark ? "#4b4b4b" : "#cfcfcf");
  }, [theme]);

  /* -------------------- Load Graph -------------------- */
  useEffect(() => {
    if (!open) return;

    const loadGraph = async () => {
      setLoading(true);
      setGraphError(null);
      setSelectedNode(null);

      try {
        // const res = await fetch(BACKEND_URL + "/api/graph") // TODO: Activate as soon as backend generates graph
        const res = await fetch("/graph_chunk_entity_relation.graphml");

        if (!res.ok) {
          throw new Error("Couldn't load graph");
        }

        const xml = await res.text();
        setData(graphMLtoForceData(xml));
      } catch (err) {
        console.error("Graph loading failed:", err);
        setGraphError("Couldn't load graph");
        setData({ nodes: [], links: [] });
      } finally {
        setLoading(false);
      }
    };

    loadGraph();
  }, [open]);

  if (!open) return null;

  /* -------------------- Render -------------------- */
  return (
    <div className="fixed inset-0 z-50 bg-black/40">
      <div className="absolute left-[2.5vw] top-[2.5vh] h-[95vh] w-[95vw] bg-sidebar dark:bg-sidebar shadow-xl rounded-lg">
        {/* Header */}
        <div className="flex items-center justify-between px-6 h-14">
          <div className="text-xl font-medium">{t("graph.title")}</div>
          <Button
            variant="ghost"
            onClick={onClose}
            className="dark:hover:text-black"
          >
            {t("graph.close")}
          </Button>
        </div>

        {/* Node details */}
        {selectedNode && (
          <div className="absolute right-4 top-16 bottom-4 w-96 overflow-auto rounded-lg border bg-white/90 dark:bg-gray-800/90 p-4 text-sm z-10">
            <div className="flex items-center justify-between mb-2">
              <div className="font-semibold truncate">
                {selectedNode.name ?? selectedNode.id ?? "Node details"}
              </div>
              <Button
                size="sm"
                variant="ghost"
                onClick={() => setSelectedNode(null)}
              >
                ×
              </Button>
            </div>
            <pre className="whitespace-pre-wrap break-words">
              {JSON.stringify(selectedNode, null, 2)}
            </pre>
          </div>
        )}

        {/* Graph Area */}
        <div className="h-[calc(100%-56px)] relative">
          {loading && (
            <div className="absolute inset-0 flex items-center justify-center text-gray-500">
              {t("graph.loading")}
            </div>
          )}

          {graphError && (
            <div className="absolute inset-0 flex items-center justify-center text-red-600 font-medium">
              {graphError}
            </div>
          )}

          {!loading && !graphError && (
            <ForceGraph2D
              graphData={data}
              nodeLabel="name"
              linkDirectionalParticles={1}
              linkDirectionalParticleSpeed={0.005}
              width={dimensions.width}
              height={dimensions.height}
              linkColor={() => linkColor}
              linkDirectionalParticleColor={() => linkColor}
              onNodeClick={(node: any) => setSelectedNode(node)}
              onBackgroundClick={() => setSelectedNode(null)}
            />
          )}
        </div>
      </div>
    </div>
  );
}
