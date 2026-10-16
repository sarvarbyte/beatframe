#!/usr/bin/env bash
# Beatframe Studio launcher.
#   ./studio.sh            start the app and open it in the browser
#   ./studio.sh --install  add the `studio` command and a "Beatframe Studio" app icon
set -e
DIR="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
cd "$DIR"
PORT=8000

if [ "$1" = "--install" ]; then
  mkdir -p "$HOME/.local/bin" "$HOME/.local/share/applications"
  chmod +x "$DIR/studio.sh"
  ln -sf "$DIR/studio.sh" "$HOME/.local/bin/studio"
  cat > "$HOME/.local/share/applications/beatframe-studio.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=Beatframe Studio
Comment=Script in, animated video out
Exec="$DIR/studio.sh"
Icon=$DIR/beatframe/web/static/icon.png
Terminal=true
Categories=AudioVideo;Video;
EOF
  update-desktop-database "$HOME/.local/share/applications" 2>/dev/null || true
  echo "✓ Installed."
  echo "  • Type 'studio' in a new terminal"
  echo "  • Or open the app menu and search 'Beatframe Studio' (you can pin it to the dock)"
  exit 0
fi

if [ ! -x "$DIR/.venv/bin/beatframe" ]; then
  echo "Beatframe is not installed in .venv yet. Run once:"
  echo "  cd \"$DIR\" && python3 -m venv .venv && .venv/bin/pip install -e ."
  read -r -p "Press Enter to close" _
  exit 1
fi

# already running? just open the browser
if "$DIR/.venv/bin/python" -c "import socket,sys; s=socket.socket(); sys.exit(0 if s.connect_ex(('127.0.0.1',$PORT))==0 else 1)"; then
  xdg-open "http://127.0.0.1:$PORT" >/dev/null 2>&1 &
  echo "Beatframe Studio is already running → http://127.0.0.1:$PORT"
  sleep 1
  exit 0
fi

echo "Starting Beatframe Studio… (close this window or press Ctrl+C to stop)"
exec "$DIR/.venv/bin/beatframe" web --projects "$DIR/projects" --port "$PORT"
