import type { WorkspaceId } from "./workspace";

export type Role = "administrator" | "trader" | "research" | "viewer";
export interface WorkspaceLayout { workspace: WorkspaceId; panels: string[]; updatedAt: string }

const key = (role: Role, workspace: WorkspaceId) => `cqrp.layout.${role}.${workspace}`;
export function saveLayout(role: Role, layout: WorkspaceLayout, storage: Storage = localStorage) { storage.setItem(key(role, layout.workspace), JSON.stringify(layout)); }
export function loadLayout(role: Role, workspace: WorkspaceId, fallback: string[], storage: Storage = localStorage): WorkspaceLayout {
  try { const value = storage.getItem(key(role, workspace)); if (value) return JSON.parse(value) as WorkspaceLayout; } catch { /* use deterministic default */ }
  return { workspace, panels: fallback, updatedAt: "" };
}
export function visibleWorkspaceIds(role: Role): WorkspaceId[] { return role === "viewer" ? ["trader", "portfolio"] : role === "research" ? ["trader", "research"] : ["trader", "portfolio", "research", "operations"]; }
