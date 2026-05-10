from __future__ import annotations

from pydantic import BaseModel, Field


class CreateGameRequest(BaseModel):
    width: int = Field(default=10, ge=5, le=50)
    height: int = Field(default=10, ge=5, le=50)
    mine_count: int = Field(default=10, ge=1)
    max_players: int = Field(default=1, ge=1, le=4)


class CreateGameResponse(BaseModel):
    game_code: str
    width: int
    height: int
    mine_count: int
    max_players: int


class GameInfoResponse(BaseModel):
    game_code: str
    width: int
    height: int
    mine_count: int
    max_players: int
    players_count: int
    game_over: bool
    won: bool
