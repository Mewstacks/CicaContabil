import assert from "node:assert/strict";
import test from "node:test";

import ExcelJS from "exceljs";

import { createReportingServer } from "./index.js";
import { chartSvg, renderXlsx, validateSnapshot } from "./report.js";

const snapshot = validateSnapshot({
  organizationId: "office-test",
  reportName: "DRE gerencial",
  generatedAt: "2026-09-23T14:00:00Z",
  sourceUpdatedAt: "2026-09-23T13:30:00Z",
  templateVersion: "dre-v1",
  periodLabel: "09/2026",
  preliminary: true,
  pendingNotes: ["Conta sem mapeamento"],
  filters: [{ label: "Empresa", value: "Empresa teste" }],
  rows: [{ label: "Receita", amount: "1234.50" }],
});

test("renders SVG with the validated report values", () => {
  const svg = chartSvg(snapshot);
  assert.match(svg, /<svg/);
  assert.match(svg, /Receita/);
});

test("rejects invalid report snapshots", () => {
  assert.throws(
    () => validateSnapshot({ ...snapshot, generatedAt: "not-a-date" }),
    /Data da fotografia inválida/,
  );
  assert.throws(
    () => validateSnapshot({ ...snapshot, rows: [{ label: "Receita", amount: "NaN" }] }),
    /Valor monetário inválido/,
  );
});

test("renders an XLSX container and protects spreadsheet text", async () => {
  const body = await renderXlsx(
    validateSnapshot({ ...snapshot, rows: [{ label: "=malicious", amount: "2.00" }] }),
  );
  assert.deepEqual(body.subarray(0, 2), Buffer.from("PK"));
  const workbook = new ExcelJS.Workbook();
  // ExcelJS 4.x declares an older non-generic Node Buffer; the bytes are unchanged.
  await workbook.xlsx.load(body as never);
  const cell = workbook.worksheets[0]?.getCell("A10");
  assert.equal(cell?.value, "'=malicious");
  assert.equal(typeof cell?.value, "string");
});

test("preserves a narrative and evidence as plain text", async () => {
  const workbook = new ExcelJS.Workbook();
  const body = await renderXlsx(
    validateSnapshot({
      ...snapshot,
      narrative: "Linha inicial\nLinha seguinte",
      evidence: [{ label: "Manual", reference: "R-1", detail: "Aprovado" }],
    }),
  );
  await workbook.xlsx.load(body as never);
  const values = workbook.worksheets[0]?.getSheetValues().flat().filter(Boolean).map(String);
  assert.ok(values?.includes("Linha inicial Linha seguinte"));
  assert.ok(values?.includes("Manual"));
  assert.ok(values?.includes("R-1"));
});

test("the loopback API accepts a UTF-8 BOM and returns an auditable hash", async () => {
  const server = createReportingServer({ sharedSecret: "test-secret" });
  await new Promise<void>((resolve) => server.listen(0, "127.0.0.1", resolve));
  try {
    const address = server.address();
    assert.ok(address && typeof address !== "string");
    const response = await fetch(`http://127.0.0.1:${address.port}/v1/render`, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-CICA-Reporting-Secret": "test-secret" },
      body: `\uFEFF${JSON.stringify({ format: "svg", snapshot })}`,
    });
    assert.equal(response.status, 200);
    assert.equal(response.headers.get("content-type"), "image/svg+xml");
    assert.match(response.headers.get("x-cica-report-hash") ?? "", /^[a-f0-9]{64}$/);
    assert.match(await response.text(), /<svg/);
  } finally {
    await new Promise<void>((resolve, reject) => server.close((error) => (error ? reject(error) : resolve())));
  }
});

test("the loopback API rejects missing or incorrect service authentication", async () => {
  const server = createReportingServer({ sharedSecret: "test-secret" });
  await new Promise<void>((resolve) => server.listen(0, "127.0.0.1", resolve));
  try {
    const address = server.address();
    assert.ok(address && typeof address !== "string");
    const response = await fetch(`http://127.0.0.1:${address.port}/v1/render`, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-CICA-Reporting-Secret": "wrong" },
      body: JSON.stringify({ format: "svg", snapshot }),
    });
    assert.equal(response.status, 401);
  } finally {
    await new Promise<void>((resolve, reject) => server.close((error) => (error ? reject(error) : resolve())));
  }
});

test("the loopback API accepts active and previous secrets only during rotation", async () => {
  const server = createReportingServer({
    sharedSecret: "new-secret",
    previousSharedSecret: "old-secret",
  });
  await new Promise<void>((resolve) => server.listen(0, "127.0.0.1", resolve));
  try {
    const address = server.address();
    assert.ok(address && typeof address !== "string");
    const requestWith = async (secret: string): Promise<number> => {
      const response = await fetch(`http://127.0.0.1:${address.port}/v1/render`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-CICA-Reporting-Secret": secret },
        body: "{}",
      });
      return response.status;
    };
    assert.equal(await requestWith("new-secret"), 400);
    assert.equal(await requestWith("old-secret"), 400);
    assert.equal(await requestWith("unknown-secret"), 401);
  } finally {
    await new Promise<void>((resolve, reject) => server.close((error) => (error ? reject(error) : resolve())));
  }
});

test("the renderer rejects an empty active secret", () => {
  assert.throws(() => createReportingServer({}), /CICA_REPORTING_SHARED_SECRET/);
});

