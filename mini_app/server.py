import json
import os
import mimetypes
from http.server import SimpleHTTPRequestHandler
from socketserver import TCPServer
from urllib.parse import urlparse, parse_qs
from urllib.request import urlopen
from urllib.error import URLError, HTTPError


PORT = int(os.environ.get("PORT", 8000))


class Handler(SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path == "/api/search":
            self.handle_search(parsed)
            return

        if parsed.path == "/":
            self.path = "/index.html"

        return super().do_GET()

    def handle_search(self, parsed):
        params = parse_qs(parsed.query)
        query = params.get("q", [""])[0].strip()

        if not query:
            self.send_json([])
            return

        url = (
            "https://itunes.apple.com/search"
            f"?term={query.replace(' ', '+')}"
            "&limit=8&media=music"
        )

        try:
            with urlopen(url, timeout=15) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (URLError, HTTPError, TimeoutError, json.JSONDecodeError):
            self.send_json([], status=502)
            return

        results = []
        for item in payload.get("results", []):
            preview = item.get("previewUrl")
            title = item.get("trackName")
            artist = item.get("artistName")
            artwork = item.get("artworkUrl100")

            if preview and title and artist:
                if artwork:
                    artwork = artwork.replace("100x100bb", "400x400bb")

                results.append(
                    {
                        "title": title,
                        "artist": artist,
                        "preview_url": preview,
                        "artwork_url": artwork,
                    }
                )

        self.send_json(results)

    def send_json(self, data, status=200):
        raw = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)


if __name__ == "__main__":
    mimetypes.add_type("application/javascript", ".js")
    with TCPServer(("", PORT), Handler) as httpd:
        print(f"Serving at port {PORT}")
        httpd.serve_forever()