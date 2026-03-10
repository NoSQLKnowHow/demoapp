export type SectionDefinition = {
  path: string;
  label: string;
  description: string;
};

export const sections: SectionDefinition[] = [
  { path: "/relational", label: "Relational", description: "Explore canonical relational tables." },
  { path: "/json", label: "JSON", description: "Work with JSON Duality Views and JSON collections." },
  { path: "/graph", label: "Graph", description: "Visualize infrastructure connectivity with property graphs." },
  { path: "/vector", label: "Vector", description: "Run semantic and keyword searches across vectorized content." },
  { path: "/data-entry", label: "Data Entry", description: "Capture new maintenance logs and inspection reports." },
  { path: "/prism", label: "Prism View", description: "See a unified projection of a single asset." }
];

export const defaultSectionPath = sections[0]?.path ?? "/relational";
