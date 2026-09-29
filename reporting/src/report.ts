import { createHash } from "node:crypto";
import { Decimal } from "decimal.js";
import * as echarts from "echarts";
import ExcelJS from "exceljs";
import puppeteer from "puppeteer";

export type ReportFormat = "pdf" | "xlsx" | "svg";

export type Snapshot = {
  organizationId: string;
  reportName: string;
  generatedAt: string;
  periodLabel: string;
  preliminary: boolean;
  pendingNotes: string[];
  rows: Array<{ label: string; amount: string }>;
  templateVersion?: string;
  sourceUpdatedAt?: string;
  filters?: Array<{ label: string; value: string }>;
  narrative?: string;
  evidence?: Array<{ label: string; reference: string; detail: string }>;
};

function decimal(value: string): Decimal {
  if (!/^-?\d+(\.\d{1,2})?$/.test(value)) throw new Error("Valor monetário inválido.");
  return new Decimal(value);
}

function text(value: string, maximum: number): string {
  return value.replace(/[\u0000-\u001f\u007f]/g, " ").trim().slice(0, maximum);
}

function escapeHtml(value: string): string {
  const entities: Record<string, string> = {
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    "'": "&#39;",
    "\"": "&quot;",
  };
  return value.replace(/[&<>'"]/g, (character) => entities[character] ?? character);
}

function spreadsheetText(value: string): string {
  const safe = text(value, 240);
  return "=+-@".includes(safe[0] ?? "") ? `'${safe}` : safe;
}

function validTimestamp(value: string): string {
  if (!Number.isFinite(Date.parse(value))) throw new Error("Data da fotografia inválida.");
  return value;
}

export function validateSnapshot(value: unknown): Snapshot {
  if (typeof value !== "object" || value === null) throw new Error("Fotografia de relatório inválida.");
  const input = value as Partial<Snapshot>;
  if (
    typeof input.organizationId !== "string" ||
    typeof input.reportName !== "string" ||
    typeof input.generatedAt !== "string" ||
    typeof input.periodLabel !== "string" ||
    !Array.isArray(input.rows)
  ) {
    throw new Error("Fotografia de relatório incompleta.");
  }
  const rows = input.rows.map((row) => {
    if (typeof row?.label !== "string" || typeof row.amount !== "string") {
      throw new Error("Linha inválida.");
    }
    decimal(row.amount);
    return { label: text(row.label, 240), amount: row.amount };
  });
  const filters = Array.isArray(input.filters)
    ? input.filters
        .filter(
          (filter): filter is { label: string; value: string } =>
            typeof filter?.label === "string" && typeof filter.value === "string",
        )
        .slice(0, 20)
        .map((filter) => ({ label: text(filter.label, 120), value: text(filter.value, 240) }))
    : [];
  const evidence = Array.isArray(input.evidence)
    ? input.evidence
        .filter(
          (item): item is { label: string; reference: string; detail: string } =>
            typeof item?.label === "string" &&
            typeof item.reference === "string" &&
            typeof item.detail === "string",
        )
        .slice(0, 200)
        .map((item) => ({
          label: text(item.label, 240),
          reference: text(item.reference, 240),
          detail: text(item.detail, 1_000),
        }))
    : [];
  return {
    organizationId: text(input.organizationId, 80),
    reportName: text(input.reportName, 160),
    generatedAt: validTimestamp(input.generatedAt),
    periodLabel: text(input.periodLabel, 120),
    preliminary: Boolean(input.preliminary),
    pendingNotes: Array.isArray(input.pendingNotes)
      ? input.pendingNotes.filter((note): note is string => typeof note === "string").slice(0, 20).map((note) => text(note, 400))
      : [],
    rows,
    templateVersion: input.templateVersion ? text(input.templateVersion, 80) : undefined,
    sourceUpdatedAt: input.sourceUpdatedAt ? validTimestamp(input.sourceUpdatedAt) : undefined,
    filters,
    narrative: typeof input.narrative === "string" ? text(input.narrative, 20_000) : undefined,
    evidence,
  };
}

export function chartSvg(snapshot: Snapshot): string {
  const chart = echarts.init(null, null, { renderer: "svg", ssr: true, width: 720, height: 300 });
  chart.setOption({
    animation: false,
    grid: { left: 120, right: 32, top: 30, bottom: 30 },
    xAxis: { type: "value" },
    yAxis: { type: "category", data: snapshot.rows.map((row) => row.label), axisLabel: { width: 100, overflow: "truncate" } },
    series: [{ type: "bar", data: snapshot.rows.map((row) => decimal(row.amount).toNumber()), itemStyle: { color: "#205943" } }],
  });
  const svg = chart.renderToSVGString();
  chart.dispose();
  return svg;
}

export async function renderXlsx(snapshot: Snapshot): Promise<Buffer> {
  const workbook = new ExcelJS.Workbook();
  workbook.creator = "CICA";
  const sheet = workbook.addWorksheet("Relatório CICA");
  sheet.addRow([spreadsheetText(snapshot.reportName)]);
  sheet.addRow(["Período", spreadsheetText(snapshot.periodLabel)]);
  sheet.addRow(["Gerado em", snapshot.generatedAt]);
  sheet.addRow(["Situação", snapshot.preliminary ? "Preliminar" : "Atualizado"]);
  if (snapshot.templateVersion) sheet.addRow(["Versão do modelo", spreadsheetText(snapshot.templateVersion)]);
  if (snapshot.sourceUpdatedAt) sheet.addRow(["Fonte atualizada em", snapshot.sourceUpdatedAt]);
  (snapshot.filters ?? []).forEach((filter) =>
    sheet.addRow([spreadsheetText(filter.label), spreadsheetText(filter.value)]),
  );
  sheet.addRow([]);
  const headingRow = sheet.rowCount + 1;
  sheet.addRow(["Indicador", "Valor"]);
  snapshot.rows.forEach((row) => sheet.addRow([spreadsheetText(row.label), decimal(row.amount).toNumber()]));
  sheet.getRow(1).font = { bold: true, color: { argb: "FFFDF7" } };
  sheet.getRow(1).fill = { type: "pattern", pattern: "solid", fgColor: { argb: "205943" } };
  sheet.getRow(headingRow).font = { bold: true };
  sheet.getColumn(1).width = 42;
  sheet.getColumn(2).width = 20;
  sheet.getColumn(2).numFmt = 'R$ #,##0.00;[Red]-R$ #,##0.00';
  if (snapshot.pendingNotes.length) {
    sheet.addRow([]);
    sheet.addRow(["Pendências"]);
    snapshot.pendingNotes.forEach((note) => sheet.addRow([spreadsheetText(note)]));
  }
  if (snapshot.narrative) {
    sheet.addRow([]);
    sheet.addRow(["Análise"]);
    sheet.addRow([spreadsheetText(snapshot.narrative)]);
    sheet.getRow(sheet.rowCount).alignment = { vertical: "top", wrapText: true };
  }
  if ((snapshot.evidence ?? []).length) {
    sheet.addRow([]);
    sheet.addRow(["Fontes", "Referência", "Detalhe"]);
    snapshot.evidence?.forEach((item) =>
      sheet.addRow([
        spreadsheetText(item.label),
        spreadsheetText(item.reference),
        spreadsheetText(item.detail),
      ]),
    );
    sheet.getColumn(3).width = 62;
  }
  return Buffer.from(await workbook.xlsx.writeBuffer());
}

function reportMetadata(snapshot: Snapshot): string {
  const rows = [
    `<dt>Período</dt><dd>${escapeHtml(snapshot.periodLabel)}</dd>`,
    `<dt>Gerado em</dt><dd>${escapeHtml(snapshot.generatedAt)}</dd>`,
    ...(snapshot.sourceUpdatedAt ? [`<dt>Fonte atualizada em</dt><dd>${escapeHtml(snapshot.sourceUpdatedAt)}</dd>`] : []),
    ...(snapshot.templateVersion ? [`<dt>Versão do modelo</dt><dd>${escapeHtml(snapshot.templateVersion)}</dd>`] : []),
    ...(snapshot.filters ?? []).map(
      (filter) => `<dt>${escapeHtml(filter.label)}</dt><dd>${escapeHtml(filter.value)}</dd>`,
    ),
  ];
  return `<dl>${rows.join("")}</dl>`;
}

export async function renderPdf(snapshot: Snapshot): Promise<Buffer> {
  const chart = chartSvg(snapshot);
  const rows = snapshot.rows.map((row) => `<tr><td>${escapeHtml(row.label)}</td><td>R$ ${decimal(row.amount).toFixed(2)}</td></tr>`).join("");
  const pending = snapshot.pendingNotes.map((note) => `<li>${escapeHtml(note)}</li>`).join("");
  const narrative = snapshot.narrative ? `<section><h2>Análise</h2><p>${escapeHtml(snapshot.narrative).replace(/\n/g, "<br>")}</p></section>` : "";
  const evidence = (snapshot.evidence ?? []).map((item) => `<tr><td>${escapeHtml(item.label)}</td><td>${escapeHtml(item.reference)}</td><td>${escapeHtml(item.detail)}</td></tr>`).join("");
  const evidenceTable = evidence ? `<section><h2>Fontes</h2><table><thead><tr><th>Fonte</th><th>Referência</th><th>Detalhe</th></tr></thead><tbody>${evidence}</tbody></table></section>` : "";
  const html = `<!doctype html><html lang="pt-BR"><meta charset="utf-8"><style>body{font:14px Arial;color:#192d24;margin:36px}h1,h2{color:#153e32}h2{margin-top:24px;font-size:18px}p{line-height:1.5;white-space:normal}dl{display:grid;grid-template-columns:150px 1fr;gap:5px 14px}dt{font-weight:bold}dd{margin:0}table{border-collapse:collapse;width:100%}th,td{padding:9px;border-bottom:1px solid #7d8b7f;text-align:left;vertical-align:top}td:last-child{text-align:right}section table td:last-child{ text-align:left }.note{padding:12px;background:#fff0d6;color:#825019}</style><h1>${escapeHtml(snapshot.reportName)}</h1>${reportMetadata(snapshot)}${snapshot.preliminary ? `<section class="note"><strong>Relatório preliminar</strong><ul>${pending || "<li>Existem dados pendentes de atualização.</li>"}</ul></section>` : ""}${narrative}<table><thead><tr><th>Indicador</th><th>Valor</th></tr></thead><tbody>${rows}</tbody></table>${chart}${evidenceTable}</html>`;
  const executablePath = process.env.CICA_REPORTING_BROWSER_PATH?.trim() || undefined;
  const browser = await puppeteer.launch({ headless: true, executablePath, args: ["--disable-gpu"] });
  try {
    const page = await browser.newPage();
    await page.setRequestInterception(true);
    page.on("request", (request) => {
      void (request.url() === "about:blank" ? request.continue() : request.abort());
    });
    await page.setContent(html, { waitUntil: "load" });
    return Buffer.from(await page.pdf({ format: "A4", printBackground: true }));
  } finally {
    await browser.close();
  }
}

export async function render(snapshot: Snapshot, format: ReportFormat): Promise<{ contentType: string; body: Buffer }> {
  if (format === "xlsx") return { contentType: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", body: await renderXlsx(snapshot) };
  if (format === "svg") return { contentType: "image/svg+xml", body: Buffer.from(chartSvg(snapshot)) };
  return { contentType: "application/pdf", body: await renderPdf(snapshot) };
}

export function reportHash(body: Buffer): string {
  return createHash("sha256").update(body).digest("hex");
}
