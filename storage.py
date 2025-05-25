import os
import json
from pathlib import Path
from diplomacy.engine.game import Game


class FileStorage:
    def __init__(self, storage_dir="game_data"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(exist_ok=True)
        self.games_dir = self.storage_dir / "games"
        self.metadata_dir = self.storage_dir / "metadata"
        self.games_dir.mkdir(exist_ok=True)
        self.metadata_dir.mkdir(exist_ok=True)

    async def save_game(self, game_id, game):
        game_file = self.games_dir / f"{game_id}.json"
        # Convert game to dictionary for JSON serialization
        game_dict = game.to_dict()
        with open(game_file, "w") as f:
            json.dump(game_dict, f, indent=2)

    async def load_game(self, game_id):
        game_file = self.games_dir / f"{game_id}.json"
        try:
            with open(game_file, "r") as f:
                game_dict = json.load(f)
            # Reconstruct game from dictionary
            return Game.from_dict(game_dict)
        except FileNotFoundError:
            return None

    async def save_metadata(self, game_id, metadata):
        metadata_file = self.metadata_dir / f"{game_id}.json"
        with open(metadata_file, "w") as f:
            json.dump(metadata, f)

    async def load_metadata(self, game_id):
        metadata_file = self.metadata_dir / f"{game_id}.json"
        try:
            with open(metadata_file, "r") as f:
                return json.load(f)
        except FileNotFoundError:
            return None

    async def list_games(self):
        games = {}
        for metadata_file in self.metadata_dir.glob("*.json"):
            game_id = metadata_file.stem
            metadata = await self.load_metadata(game_id)
            if metadata:
                games[game_id] = metadata
        return games


class VercelKVStorage:
    def __init__(self):
        # Import here to avoid dependency issues in development
        try:
            from vercel_kv_sdk import KV

            # vercel_kv_sdk automatically uses the environment variables:
            # VERCEL_KV_REST_API_URL and VERCEL_KV_REST_API_TOKEN
            self.kv = KV()
        except ImportError:
            print(
                "⚠️  Warning: vercel-kv-sdk package not available, falling back to file storage"
            )
            raise ImportError("vercel-kv-sdk not available")

    async def save_game(self, game_id, game):
        game_dict = game.to_dict()
        # vercel_kv_sdk uses synchronous methods
        self.kv.set(f"game:{game_id}", json.dumps(game_dict))

    async def load_game(self, game_id):
        try:
            game_data = self.kv.get(f"game:{game_id}")
            if game_data:
                game_dict = json.loads(game_data)
                return Game.from_dict(game_dict)
            return None
        except Exception:
            return None

    async def save_metadata(self, game_id, metadata):
        self.kv.set(f"metadata:{game_id}", json.dumps(metadata))

    async def load_metadata(self, game_id):
        try:
            metadata_data = self.kv.get(f"metadata:{game_id}")
            if metadata_data:
                return json.loads(metadata_data)
            return None
        except Exception:
            return None

    async def list_games(self):
        try:
            # Get all metadata keys
            keys = self.kv.keys("metadata:*")
            games = {}
            for key in keys:
                game_id = key.decode() if isinstance(key, bytes) else key
                game_id = game_id.replace("metadata:", "")
                metadata = await self.load_metadata(game_id)
                if metadata:
                    games[game_id] = metadata
            return games
        except Exception:
            return {}


def get_storage():
    if os.getenv("VERCEL") == "1":
        print("🚀 Using Vercel KV storage")
        try:
            return VercelKVStorage()
        except ImportError:
            print("📁 Falling back to file storage")
            return FileStorage()
    else:
        print("💾 Using file storage")
        return FileStorage()


storage = get_storage()
