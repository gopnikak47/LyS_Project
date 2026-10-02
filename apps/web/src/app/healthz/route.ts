// Health-check cho Docker/nginx: không phụ thuộc API hay i18n.
export const dynamic = "force-dynamic";

export function GET() {
  return Response.json({ status: "ok" });
}
