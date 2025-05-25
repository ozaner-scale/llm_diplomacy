#!/usr/bin/env python
"""Main entry point for the Diplomacy web application."""

import uvicorn
from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from typing import Optional, Dict, Any, List
import json
import uuid
from pathlib import Path
import re

from diplomacy.engine.game import Game
from diplomacy.engine.power import Power
from diplomacy.utils.constants import DEFAULT_GAME_RULES

# Create FastAPI app
app = FastAPI(title="Diplomacy Web", version="1.0.0")

# Setup templates and static files
templates_dir = Path(__file__).parent / "templates"
static_dir = Path(__file__).parent / "static"
templates_dir.mkdir(exist_ok=True)
static_dir.mkdir(exist_ok=True)

templates = Jinja2Templates(directory=str(templates_dir))
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# In-memory game storage (for single-player, will be replaced with better storage later)
games: Dict[str, Game] = {}
game_metadata: Dict[str, Dict[str, Any]] = {}

# Game rules with descriptions
RULE_DESCRIPTIONS = {
    "CIVIL_DISORDER": "Powers that don't submit orders will have default orders: units hold, retreats disband, builds waived",
    "CD_DUMMIES": "Dummy powers (bots) will process their turn immediately without waiting for orders",
    "NO_PRESS": "No communication between players (except with game master)",
    "SOLITAIRE": "Single-player game where you control all powers",
    "NO_DEADLINE": "No time limit for submitting orders",
    "REAL_TIME": "Game processes immediately when all orders are submitted",
    "ALWAYS_WAIT": "Always wait for deadline before processing (incompatible with REAL_TIME)",
    "BUILD_ANY": "Can build units at any owned supply center, not just home centers",
    "NO_CHECK": "Invalid orders are accepted and will fail during processing (like face-to-face play)",
    "IGNORE_ERRORS": "Order errors are silently ignored",
    "HOLD_WIN": "Must achieve victory conditions for two consecutive years to win",
    "SHARED_VICTORY": "Multiple powers can share victory if they meet conditions simultaneously",
    "POWER_CHOICE": "Players can choose which power to play",
    "START_MASTER": "Game won't start automatically - requires manual start",
    "DONT_SKIP_PHASES": "Play all phases even if no orders are needed",
}

# Map information
MAP_INFO = {
    "standard": {
        "name": "Standard",
        "powers": [
            "AUSTRIA",
            "ENGLAND",
            "FRANCE",
            "GERMANY",
            "ITALY",
            "RUSSIA",
            "TURKEY",
        ],
        "description": "Classic 7-player Diplomacy map",
    },
    "standard_france_austria": {
        "name": "France vs Austria",
        "powers": ["FRANCE", "AUSTRIA"],
        "description": "2-player variant on standard map",
    },
    "standard_germany_italy": {
        "name": "Germany vs Italy",
        "powers": ["GERMANY", "ITALY"],
        "description": "2-player variant on standard map",
    },
}


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Home page showing list of games."""
    return templates.TemplateResponse(
        "index.html", {"request": request, "games": game_metadata}
    )


@app.get("/game/new", response_class=HTMLResponse)
async def new_game_form(request: Request):
    """Show form to create a new game."""
    return templates.TemplateResponse(
        "new_game.html",
        {"request": request, "maps": MAP_INFO, "rule_descriptions": RULE_DESCRIPTIONS},
    )


@app.post("/game/new")
async def create_game(
    request: Request,
    game_name: str = Form(...),
    map_name: str = Form("standard"),
    player_power: str = Form(""),
    rules: List[str] = Form([]),
):
    """Create a new game."""
    game_id = str(uuid.uuid4())[:8]

    # Always include CD_DUMMIES for bot behavior
    if "CD_DUMMIES" not in rules:
        rules.append("CD_DUMMIES")

    # Create game
    game = Game(game_id=game_id, map_name=map_name, rules=rules)

    # Set up powers
    map_powers = MAP_INFO.get(map_name, MAP_INFO["standard"])["powers"]

    if "SOLITAIRE" in rules:
        # Solitaire mode - player controls all powers
        for power_name in map_powers:
            power = game.get_power(power_name)
            power.set_controlled("player")
    else:
        # Regular game - player controls one power, others are dummies
        if not player_power or player_power not in map_powers:
            player_power = map_powers[0]  # Default to first power

        for power_name in map_powers:
            power = game.get_power(power_name)
            if power_name == player_power:
                power.set_controlled("player")
            else:
                # Set as dummy power (bot)
                power.set_controlled(None)

    # Start the game by setting it to active
    game.set_status("active")

    # Store game
    games[game_id] = game
    game_metadata[game_id] = {
        "id": game_id,
        "name": game_name,
        "map": map_name,
        "phase": game.phase,
        "status": game.status,
        "player_power": player_power if not "SOLITAIRE" in rules else "ALL",
    }

    return RedirectResponse(f"/game/{game_id}", status_code=303)


@app.get("/game/{game_id}", response_class=HTMLResponse)
async def view_game(request: Request, game_id: str):
    """View a game."""
    if game_id not in games:
        raise HTTPException(status_code=404, detail="Game not found")

    game = games[game_id]
    player_power = game_metadata[game_id].get("player_power", "ALL")

    # Validate player_power exists
    if player_power != "ALL" and player_power not in game.powers:
        # Fallback to first power if invalid
        player_power = list(game.powers.keys())[0]
        game_metadata[game_id]["player_power"] = player_power

    # Get map SVG content
    svg_path = (
        Path(__file__).parent / "diplomacy" / "maps" / "svg" / f"{game.map_name}.svg"
    )
    if svg_path.exists():
        with open(svg_path, "r", encoding="utf-8") as f:
            map_svg = f.read()
        # Add unit markers to the map
        map_svg = _add_units_to_svg(map_svg, game)
    else:
        map_svg = None

    # Get possible orders for the current phase
    possible_orders = {}
    if game.phase_type == "M":  # Movement phase
        possible_orders = game.get_all_possible_orders()

    # Get phase type
    phase_type = "M"  # Default to movement
    if hasattr(game, "phase_type"):
        phase_type = game.phase_type
    elif game.phase:
        phase_type = game.phase[-1]

    return templates.TemplateResponse(
        "game.html",
        {
            "request": request,
            "game": game,
            "game_id": game_id,
            "powers": game.powers,
            "current_phase": game.phase,
            "phase_type": phase_type,
            "map_data": json.dumps(_get_map_data(game)),
            "player_power": player_power,
            "map_svg": map_svg,
            "is_solitaire": "SOLITAIRE" in game.rules,
            "possible_orders": possible_orders,
        },
    )


@app.get("/maps/svg/{map_name}.svg")
async def get_map_svg(map_name: str):
    """Serve map SVG files."""
    svg_path = Path(__file__).parent / "diplomacy" / "maps" / "svg" / f"{map_name}.svg"
    if not svg_path.exists():
        raise HTTPException(status_code=404, detail="Map not found")

    with open(svg_path, "r", encoding="utf-8") as f:
        content = f.read()

    return Response(content=content, media_type="image/svg+xml")


@app.post("/game/{game_id}/orders/{power_name}")
async def submit_orders(
    request: Request, game_id: str, power_name: str, orders: str = Form("")
):
    """Submit orders for a power."""
    if game_id not in games:
        raise HTTPException(status_code=404, detail="Game not found")

    game = games[game_id]
    if power_name not in game.powers:
        raise HTTPException(status_code=404, detail="Power not found")

    # Parse and set orders
    order_list = [o.strip() for o in orders.split("\n") if o.strip()]
    game.set_orders(power_name, order_list)

    # Update metadata
    game_metadata[game_id]["phase"] = game.phase

    return RedirectResponse(f"/game/{game_id}", status_code=303)


@app.post("/game/{game_id}/process")
async def process_game(request: Request, game_id: str):
    """Process the current phase of the game."""
    if game_id not in games:
        raise HTTPException(status_code=404, detail="Game not found")

    game = games[game_id]

    # Process the game
    game.process()

    # Update metadata
    game_metadata[game_id]["phase"] = game.phase
    game_metadata[game_id]["status"] = game.status

    return RedirectResponse(f"/game/{game_id}", status_code=303)


def _get_map_data(game: Game) -> Dict[str, Any]:
    """Get map data for visualization."""
    return {
        "powers": {
            power_name: {
                "units": power.units,
                "centers": power.centers,
                "color": _get_power_color(power_name),
                "is_controlled": power.is_controlled(),
                "controller": power.get_controller() if power.is_controlled() else None,
            }
            for power_name, power in game.powers.items()
        },
        "phase": game.phase,
        "phase_type": game.phase_type,
        "possible_orders": game.get_all_possible_orders(),
    }


def _add_units_to_svg(svg_content: str, game: Game) -> str:
    """Add unit markers to the SVG map."""
    if not svg_content:
        return svg_content

    # Find the UnitLayer group in the SVG
    unit_layer_match = re.search(
        r'<g id="UnitLayer"[^>]*>.*?</g>', svg_content, re.DOTALL
    )
    if not unit_layer_match:
        return svg_content

    # Build unit markers
    unit_markers = []
    colors = _get_power_colors()

    for power_name, power in game.powers.items():
        color = colors.get(power_name, "#888888")

        for unit in power.units:
            unit_type = unit.split()[0]  # 'A' or 'F'
            location = unit.split()[1]  # e.g., 'PAR', 'LON'

            # Look for the province data in the SVG to get coordinates
            province_match = re.search(
                rf'<jdipNS:PROVINCE name="{location.lower()}"[^>]*>.*?'
                rf'<jdipNS:UNIT x="([^"]+)" y="([^"]+)"/>',
                svg_content,
                re.IGNORECASE | re.DOTALL,
            )

            if province_match:
                x = province_match.group(1)
                y = province_match.group(2)

                # Create unit marker
                if unit_type == "A":
                    marker = f'<use class="unit{power_name.lower()}" height="40" width="46" x="{float(x) - 11.5}" xlink:href="#Army" y="{float(y) - 6.5}"/>'
                else:  # Fleet
                    marker = f'<use class="unit{power_name.lower()}" height="40" width="46" x="{float(x) - 11.5}" xlink:href="#Fleet" y="{float(y) - 6.5}"/>'

                unit_markers.append(marker)

    # Replace the UnitLayer content
    if unit_markers:
        new_unit_layer = (
            f'<g id="UnitLayer">\n        '
            + "\n        ".join(unit_markers)
            + "\n    </g>"
        )
        svg_content = re.sub(
            r'<g id="UnitLayer"[^>]*>.*?</g>',
            new_unit_layer,
            svg_content,
            flags=re.DOTALL,
        )

    return svg_content


def _color_map_svg(svg_content: str, game: Game) -> str:
    """Apply colors to SVG territories based on ownership."""
    if not svg_content:
        return svg_content

    # Get power colors
    colors = _get_power_colors()

    # For each power, color their territories
    for power_name, power in game.powers.items():
        color = colors.get(power_name, "#888888")

        # Color home centers and owned centers
        for center in power.centers:
            # Try different patterns that might match territory IDs in the SVG
            patterns = [
                f'id="{center}"',
                f'id="{center.lower()}"',
                f'id="{center.upper()}"',
                f'class="{center}"',
                f'class="{center.lower()}"',
            ]

            for pattern in patterns:
                if pattern in svg_content:
                    # Find the element and add fill color
                    # Look for the element that contains this ID/class
                    element_pattern = rf"(<[^>]*{re.escape(pattern)}[^>]*>)"

                    def add_fill(match):
                        tag = match.group(1)
                        # If it already has a fill, replace it
                        if "fill=" in tag:
                            tag = re.sub(r'fill="[^"]*"', f'fill="{color}"', tag)
                        else:
                            # Add fill attribute before the closing >
                            tag = tag[:-1] + f' fill="{color}">'
                        return tag

                    svg_content = re.sub(element_pattern, add_fill, svg_content)

    return svg_content


def _get_power_colors() -> Dict[str, str]:
    """Get the color mapping for all powers."""
    return {
        "AUSTRIA": "#c48f85",
        "ENGLAND": "#8b4789",
        "FRANCE": "#4169E1",
        "GERMANY": "#696969",
        "ITALY": "#228B22",
        "RUSSIA": "#757d91",
        "TURKEY": "#b9a61c",
    }


def _get_power_color(power_name: str) -> str:
    """Get color for a power."""
    colors = _get_power_colors()
    return colors.get(power_name, "#888888")


if __name__ == "__main__":
    # For development
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
