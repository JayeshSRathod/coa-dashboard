import { describe, expect, it } from "vitest";
import { workspaceOrder, workspaces } from "./workspace";
import { visibleWorkspaceIds } from "./layout";
describe("CQRP workspaces", () => {
  it("defines four decision workflows", () => expect(workspaceOrder).toEqual(["trader", "portfolio", "research", "operations"]));
  it("keeps execution modes safe", () => { expect(workspaces.trader.kpis[0].value).toBe("PAPER"); expect(workspaces.operations.kpis[1].value).toBe("DISABLED"); });
  it("enforces role-based workspace visibility", () => expect(visibleWorkspaceIds("viewer")).toEqual(["trader", "portfolio"]));
});
