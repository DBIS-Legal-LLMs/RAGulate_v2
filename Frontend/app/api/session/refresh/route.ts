import { NextRequest, NextResponse } from "next/server";
import { REFRESH_COOKIE_NAME } from "@/lib/auth-storage";
import { clearRefreshCookie, exchangeRefreshToken, isSecureRequest, setRefreshCookie } from "@/lib/session";

// Called by the browser when the access token is about to expire, was rejected, or is missing on page load.
// 401 means the session is over and the cookie is cleared; 502 means auth-service could not be asked, which
// leaves the session as it is.
export async function POST(request: NextRequest) {
  const secure = isSecureRequest(request.headers, request.nextUrl.protocol);
  const refreshToken = request.cookies.get(REFRESH_COOKIE_NAME)?.value;

  const outcome = refreshToken ? await exchangeRefreshToken(refreshToken) : ({ status: "invalid" } as const);
  if (outcome.status === "ok") {
    const response = NextResponse.json({ access_token: outcome.tokens.accessToken, user: outcome.tokens.user });
    setRefreshCookie((name, value, options) => response.cookies.set(name, value, options), outcome.tokens, secure);
    return response;
  }
  if (outcome.status === "invalid") {
    const response = NextResponse.json({ detail: "Invalid refresh token" }, { status: 401 });
    clearRefreshCookie((name, value, options) => response.cookies.set(name, value, options), secure);
    return response;
  }
  return NextResponse.json({ detail: "The login service is not reachable" }, { status: 502 });
}
