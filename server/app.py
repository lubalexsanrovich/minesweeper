from __future__ import annotations

from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect

from server.manager import GameManager
from server.schemas import CreateGameRequest, CreateGameResponse, GameInfoResponse

app = FastAPI(title="Multiplayer Minesweeper")
manager = GameManager()


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.post("/games", response_model=CreateGameResponse)
async def create_game(payload: CreateGameRequest) -> CreateGameResponse:
    max_mines = payload.width * payload.height - 9
    if payload.mine_count > max_mines:
        raise HTTPException(
            status_code=400, detail="Too many mines for this board size"
        )

    session = manager.create_game(
        width=payload.width,
        height=payload.height,
        mine_count=payload.mine_count,
        max_players=payload.max_players,
    )

    return CreateGameResponse(
        game_code=session.code,
        width=session.board.width,
        height=session.board.height,
        mine_count=session.board.mine_count,
        max_players=session.max_players,
    )


@app.get("/games/{game_code}", response_model=GameInfoResponse)
async def get_game_info(game_code: str) -> GameInfoResponse:
    session = manager.get_game(game_code)
    if session is None:
        raise HTTPException(status_code=404, detail="Game not found")
    return GameInfoResponse(
        game_code=session.code,
        width=session.board.width,
        height=session.board.height,
        mine_count=session.board.mine_count,
        max_players=session.max_players,
        players_count=len(session.players),
        game_over=session.board.game_over,
        won=session.board.won,
    )


@app.websocket("/ws/games/{game_code}")
async def game_websocket(
    websocket: WebSocket,
    game_code: str,
    player_name: str = Query(default="Player"),
) -> None:
    code = game_code.upper()
    session = manager.get_game(code)
    if not session:
        await websocket.close(code=1008, reason="Game not found")
        return
    if session.is_full():
        await websocket.close(code=1008, reason="Game is full")
        return
    await websocket.accept()
    try:
        player_id = await session.add_player(websocket, player_name)
    except RuntimeError as error:
        await websocket.close(code=1008, reason=str(error))
        return

    await session.send_to_player(
        player_id,
        {
            "type": "joined",
            "game_code": code,
            "player_id": player_id,
        },
    )

    await session.broadcast(
        {
            "type": "player_joined",
            "game_code": code,
            "player_id": player_id,
            "player_name": player_name,
            "players": session.get_players_payload(),
        }
    )

    await session.send_to_player(player_id, session.make_state_payload())

    try:
        while True:
            payload = await websocket.receive_json()
            response = await session.apply_action(player_id, payload)
            if response["type"] == "error":
                await session.send_to_player(player_id, response)
            else:
                await session.broadcast(response)
    except WebSocketDisconnect:
        session.remove_player(player_id)
        await session.broadcast(
            {
                "type": "player_left",
                "game_code": code,
                "player_id": player_id,
                "players": session.get_players_payload(),
            }
        )
