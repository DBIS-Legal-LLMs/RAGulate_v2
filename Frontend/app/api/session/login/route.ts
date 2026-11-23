import { NextRequest, NextResponse } from "next/server";
import { isSecureRequest, loginWithPassword, setRefreshCookie, toSessionTokens } from "@/lib/session";

// Logs in against auth-service. The access token goes to the page in the response body; the refresh token is
// stored in an httpOnly cookie and never appears in a response body.
export async function POST(request: NextRequest) {
  const { username, password } = (await request.json().catch(() => ({}))) as { username?: string; password?: string };
  if (!username || !password) {
    return NextResponse.json({ detail: "Username and password are required" }, { status: 422 });
  }

  const upstream = await loginWithPassword(username, password).catch(() => null);
  if (!upstream) {
    return NextResponse.json({ detail: "The login service is not reachable" }, { status: 502 });
  }
  if (!upstream.ok) {
    // pass auth-service's own status and message through (wrong password, validation, ...)
    return new NextResponse(await upstream.text(), {
      status: upstream.status,
      headers: { "Content-Type": upstream.headers.get("Content-Type") ?? "application/json" },
    });
  }

  const tokens = toSessionTokens(await upstream.json());
  const response = NextResponse.json({ access_token: tokens.accessToken, user: tokens.user });
  setRefreshCookie((name, value, options) => response.cookies.set(name, value, options), tokens, isSecureRequest(request.headers, request.nextUrl.protocol));
  return response;
}
