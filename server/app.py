from __future__ import annotations

import logging

from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect

from server.logging_config import event, get_system_logger
from server.manager import GameManager
from server.schemas import CreateGameRequest, CreateGameResponse, GameInfoResponse

app = FastAPI(title="Multiplayer Minesweeper")
manager = GameManager()
system_logger = get_system_logger()
event(system_logger, "application_initiallized")


@app.get("/health")
async def health() -> dict:
    return {
        "status": "ok",
    }


@app.post("/games", response_model=CreateGameResponse)
async def create_game(payload: CreateGameRequest) -> CreateGameResponse:
    event(
        system_logger,
        "create_game_request",
        width=payload.width,
        height=payload.height,
        mine_count=payload.mine_count,
        max_players=payload.max_players,
        mode=str(payload.mode),
    )

    max_mines = payload.width * payload.height - 9
    if payload.mine_count > max_mines:
        event(
            system_logger,
            "create_game_rejected",
            level=logging.WARNING,
            reason="too_many_mines",
            width=payload.width,
            height=payload.height,
            mine_count=payload.mine_count,
            max_mines=max_mines,
        )
        raise HTTPException(
            status_code=400,
            detail="Too many mines for this board size",
        )

    session = manager.create_game(
        width=payload.width,
        height=payload.height,
        mine_count=payload.mine_count,
        max_players=payload.max_players,
        mode=payload.mode,
    )

    event(
        system_logger,
        "game_created_http_response",
        game_code=session.code,
        width=session.board.width,
        height=session.board.height,
        mine_count=session.board.mine_count,
        max_players=session.max_players,
        mode=str(session.mode),
    )
    return CreateGameResponse(
        game_code=session.code,
        width=session.board.width,
        height=session.board.height,
        mine_count=session.board.mine_count,
        max_players=session.max_players,
        mode=session.mode,
    )


@app.get("/games/{game_code}", response_model=GameInfoResponse)
async def get_game_info(game_code: str) -> GameInfoResponse:
    session = manager.get_game(game_code)

    if session is None:
        event(
            system_logger,
            "game_info_not_found",
            level=logging.WARNING,
            game_code=game_code.upper(),
        )
        raise HTTPException(
            status_code=404,
            detail="Game not found",
        )
    state = session.engine.state

    event(
        system_logger,
        "game_info_requested",
        game_code=session.code,
        players_count=len(state.players),
        active_players_count=state.active_players_count(),
        status=str(state.status),
    )

    return GameInfoResponse(
        game_code=session.code,
        width=session.board.width,
        height=session.board.height,
        mine_count=session.board.mine_count,
        max_players=session.max_players,
        mode=session.mode,
        status=state.status,
        players_count=len(session.players),
        active_players_count=state.active_players_count(),
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

    event(
        system_logger,
        "websocket_connect_attempt",
        game_code=code,
        player_name=player_name,
    )

    session = manager.get_game(code)

    if session is None:
        event(
            system_logger,
            "websocket_rejected",
            level=logging.WARNING,
            game_code=code,
            player_name=player_name,
            reason="game_not_found",
        )
        await websocket.close(code=1008, reason="Game not found")
        return

    if session.is_full():
        event(
            system_logger,
            "websocket_rejected",
            level=logging.WARNING,
            game_code=code,
            player_name=player_name,
            reason="game_is_full",
        )
        await websocket.close(code=1008, reason="Game is full")
        return

    await websocket.accept()

    try:
        player_id = await session.add_player(websocket, player_name)
    except RuntimeError as error:
        event(
            system_logger,
            "websocket_add_players_failed",
            level=logging.WARNING,
            game_code=code,
            player_name=player_name,
            reason=str(error),
        )
        await websocket.close(code=1008, reason=str(error))
        return

    event(
        system_logger,
        "websocket_accepted",
        game_code=code,
        player_id=player_id,
        player_name=player_name,
    )

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
            await session.apply_action(player_id, payload)

    except WebSocketDisconnect:
        event(
            system_logger,
            "websocket_disconnected",
            game_code=code,
            player_id=player_id,
            player_name=player_name,
        )
        session.disconnect_player(player_id)
        await session.broadcast(
            {
                "type": "player_left",
                "game_code": code,
                "player_id": player_id,
                "players": session.get_players_payload(),
            }
        )
        await session.broadcast(session.make_state_payload())
