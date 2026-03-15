export async function GET() {
  const backendUrl = process.env.BACKEND_API_URL || "http://localhost:8000";

  try {
    const response = await fetch(`${backendUrl}/health`, {
      cache: "no-store",
    });
    const data = await response.json();
    return Response.json(data);
  } catch {
    return Response.json(
      { status: "error", message: "Backend unreachable" },
      { status: 503 }
    );
  }
}
