import { timingSafeEqual } from "node:crypto";
import http from "node:http";

import { render, reportHash, type ReportFormat, validateSnapshot } from "./report.js";

function authorized(value: string | string[] | undefined, sharedSecrets: readonly string[]): boolean {
  if (!value || Array.isArray(value) || sharedSecrets.length === 0) return false;
  const received = Buffer.from(value, "utf8");
  let matched = false;
  for (const sharedSecret of sharedSecrets) {
    const expected = Buffer.from(sharedSecret, "utf8");
    const equal = received.length === expected.length && timingSafeEqual(received, expected);
    matched = matched || equal;
  }
  return matched;
}

function configuredSecrets(active: string, previous: string): string[] {
  const secrets = [active.trim(), previous.trim()].filter(Boolean);
  return [...new Set(secrets)];
}

export function createReportingServer(
  {
    sharedSecret = process.env.CICA_REPORTING_SHARED_SECRET ?? "",
    previousSharedSecret = process.env.CICA_REPORTING_PREVIOUS_SHARED_SECRET ?? "",
  }: { sharedSecret?: string; previousSharedSecret?: string } = {},
): http.Server {
  const sharedSecrets = configuredSecrets(sharedSecret, previousSharedSecret);
  if (sharedSecrets.length === 0) throw new Error("CICA_REPORTING_SHARED_SECRET ? obrigat?rio.");
  return http.createServer(async (request, response) => {
    if (request.method !== "POST" || request.url !== "/v1/render") {
      response.writeHead(404).end();
      return;
    }
    if (!authorized(request.headers["x-cica-reporting-secret"], sharedSecrets)) {
      response.writeHead(401).end();
      return;
    }
    try {
      const chunks: Buffer[] = [];
      for await (const chunk of request) chunks.push(Buffer.from(chunk));
      const rawBody = Buffer.concat(chunks).toString("utf8").replace(/^\uFEFF/, "");
      const input = JSON.parse(rawBody) as {
        format?: ReportFormat;
        snapshot?: unknown;
      };
      if (input.format !== "pdf" && input.format !== "xlsx" && input.format !== "svg") {
        throw new Error("Formato não suportado.");
      }
      const result = await render(validateSnapshot(input.snapshot), input.format);
      response.writeHead(200, {
        "Content-Type": result.contentType,
        "X-CICA-Report-Hash": reportHash(result.body),
      });
      response.end(result.body);
    } catch (error) {
      response.writeHead(400, { "Content-Type": "application/json" }).end(
        JSON.stringify({ error: error instanceof Error ? error.message : "Erro ao gerar relatório." }),
      );
    }
  });
}

if (process.argv[1]?.endsWith("index.ts")) {
  createReportingServer().listen(Number(process.env.PORT ?? 3080), "127.0.0.1");
}
