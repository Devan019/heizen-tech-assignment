import { NextRequest, NextResponse } from "next/server";

export async function GET(request: NextRequest) {
  try {
    const upstreamRes = await fetch("http://localhost:3001/", {
      headers: {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "User-Agent": request.headers.get("user-agent") || "",
        "Cookie": request.headers.get("cookie") || "",
      },
      cache: "no-store",
    });

    const html = await upstreamRes.text();

    const responseHeaders = new Headers();
    upstreamRes.headers.forEach((val, key) => {
      const lower = key.toLowerCase();
      if (
        lower !== "x-frame-options" &&
        lower !== "content-security-policy" &&
        lower !== "content-length"
      ) {
        responseHeaders.set(key, val);
      }
    });

    responseHeaders.set("Content-Type", "text/html; charset=utf-8");
    responseHeaders.set("Access-Control-Allow-Origin", "*");

    return new NextResponse(html, {
      status: 200,
      headers: responseHeaders,
    });
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : String(err);
    return new NextResponse(
      `<!DOCTYPE html><html><body style="background:#0b0f19;color:#f87171;font-family:sans-serif;padding:24px;"><h3>Could not connect to Metabase on localhost:3001</h3><p>${msg}</p></body></html>`,
      {
        status: 502,
        headers: { "Content-Type": "text/html; charset=utf-8" },
      }
    );
  }
}
