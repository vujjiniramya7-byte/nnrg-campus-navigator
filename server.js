const server = Bun.serve({
  port: 5000,
  fetch(req) {
    const url = new URL(req.url);
    let pathname = url.pathname;
    
    // API endpoint for real-time metrics
    if (pathname === "/api/metrics") {
      const data = {
        enrolled: "2,500+",
        placementRate: "95%",
        avgPackage: "₹53 LPA",
        partners: "50+",
        recentPlacements: [
          "TCS: 12 LPA",
          "ICICI: 8 LPA",
          "Cognizant: 10 LPA",
          "Microsoft: 53 LPA"
        ],
        admissionStatus: "Category-B / NRI Admissions Open",
        timestamp: 2026
      };
      return new Response(JSON.stringify(data), {
        headers: { "Content-Type": "application/json" }
      });
    }

    // Default to index.html for root path
    if (pathname === "/") {
      pathname = "/index.html";
    }
    
    // Block path traversal attacks
    if (pathname.includes("..")) {
      return new Response("Access Denied", { status: 403 });
    }

    const filepath = "." + pathname;
    const file = Bun.file(filepath);
    
    return file.exists().then(exists => {
      if (exists) {
        return new Response(file);
      } else {
        return new Response("404 Not Found", { status: 404 });
      }
    });
  },
});

console.log(`[Bun Server] Listening on http://localhost:${server.port}`);
