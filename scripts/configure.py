"""Create local development configuration without overwriting an existing file."""

from pathlib import Path
import secrets

ROOT = Path(__file__).resolve().parents[1]

if __name__ == "__main__":
    path = ROOT / ".env"
    try:
        with path.open("x", encoding="utf-8") as stream:
            stream.write(f"POSTGRES_PASSWORD={secrets.token_hex(24)}\nDB_PORT=15432\nAPI_PORT=18000\n")
        print("Created local .env. Existing configuration is never overwritten.")
    except FileExistsError:
        print("Existing .env retained.")
    if 'AUTH_SECRET=' not in path.read_text(encoding='utf-8'):
        with path.open('a', encoding='utf-8') as stream:
            stream.write(f'\nAUTH_SECRET={secrets.token_hex(32)}\nWEB_PORT=18080\n')
        print('Added authentication configuration; database credentials retained.')
