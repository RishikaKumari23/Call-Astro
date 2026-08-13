import { NextRequest, NextResponse } from "next/server";

// ---------------------------------------------------------------------------
// Basic Authentication — Vercel Edge Middleware
//
// Protects every route (including the root "/") with HTTP Basic Auth.
// Credentials are read from Vercel Environment Variables so they are
// NEVER hardcoded in source code.
//
// Required Vercel env vars (set in the Vercel dashboard):
//   BASIC_AUTH_USER     e.g.  astro
//   BASIC_AUTH_PASSWORD e.g.  mentor2024
// ---------------------------------------------------------------------------

export const config = {
  // Run on every route — excludes static assets so images/fonts still load
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};

export default function middleware(req: NextRequest) {
  const user = process.env.BASIC_AUTH_USER;
  const pass = process.env.BASIC_AUTH_PASSWORD;

  // If env vars aren't set, allow access (prevents locking yourself out during dev)
  if (!user || !pass) {
    return NextResponse.next();
  }

  const authHeader = req.headers.get("authorization");

  if (authHeader) {
    // Header format: "Basic <base64(user:pass)>"
    const encoded = authHeader.split(" ")[1];
    if (encoded) {
      const decoded = atob(encoded);
      const [reqUser, reqPass] = decoded.split(":");
      if (reqUser === user && reqPass === pass) {
        return NextResponse.next();
      }
    }
  }

  // No valid credentials — trigger the browser's native login dialog
  return new NextResponse("Authentication required", {
    status: 401,
    headers: {
      "WWW-Authenticate": 'Basic realm="Call-Astro — Restricted Access"',
    },
  });
}
