#  (C) Copyright Wieger Wesselink 2021. Distributed under the GPL-3.0-or-later
#  Software License, (See accompanying file LICENSE or copy at
#  https://www.gnu.org/licenses/gpl-3.0.txt)

import random
import time
from competitive_sudoku.sudoku import GameState, Move, SudokuBoard, TabooMove
import competitive_sudoku.sudokuai


class SudokuAI(competitive_sudoku.sudokuai.SudokuAI):
    """
    Sudoku AI that computes a move for a given sudoku configuration.
    """

    def __init__(self):
        super().__init__()
    
    def causes_loss(self, game_state: GameState, move: Move) -> bool:

            board = game_state.board
            (i, j) = move.square
            v = move.value

            # 1. Check row for duplicate
            for col in range(board.N):
                if col != j and board.get((i, col)) == v:
                    return True

            # 2. Check column for duplicate
            for row in range(board.N):
                if row != i and board.get((row, j)) == v:
                    return True

            # 3. Check block for duplicate
            B = int(board.N ** 0.5)
            bi = (i // B) * B
            bj = (j // B) * B

            for r in range(bi, bi+B):
                for c in range(bj, bj+B):
                    if (r, c) != (i, j) and board.get((r, c)) == v:
                        return True

            return False
        

    def generate_legal_moves(self, game_state: GameState):
            board = game_state.board
            N = board.N
            legal_moves = []

            for i in range(N):
                for j in range(N):

                    # 1. Empty cell:
                    if board.get((i, j)) != SudokuBoard.empty:
                        continue

                    # 2. Available cell near player
                    if (i, j) not in game_state.player_squares():
                        continue

                    for value in range(1, N+1):

                        # 3. Not taboo
                        if TabooMove((i, j), value) in game_state.taboo_moves:
                            continue

                        move = Move((i, j), value)

                        # 4. Simulate and see if it causes a loss
                        if not self.causes_loss(game_state, move):
                            legal_moves.append(move)

            return legal_moves

    def get_opponent_squares(self, game_state: GameState):
        if game_state.current_player == 1:
            return game_state.occupied_squares2
        else:
            return game_state.occupied_squares1

    def generate_legal_moves_for_opponent(self, game_state: GameState):
        # Temporarily swap the current player to the opponent
        original_player = game_state.current_player
        game_state.current_player = 3 - original_player  # switch player
        legal_moves = self.generate_legal_moves(game_state)
        game_state.current_player = original_player  # restore original player
        return legal_moves

    def evaluate(self, game_state: GameState) -> float:
        my_squares = game_state.player_squares()
        opponent_squares = self.get_opponent_squares(game_state)

        my_moves = len(self.generate_legal_moves(game_state))
        opponent_moves = len(self.generate_legal_moves_for_opponent(game_state))


        score = (len(my_squares) - len(opponent_squares)) * 10
        score += my_moves - opponent_moves
        return score



    # N.B. This is a very naive implementation.
    def compute_best_move(self, game_state: GameState) -> None:
        N = game_state.board.N

        # Check whether a cell is empty, a value in that cell is not taboo, and that cell is allowed
        score = self.evaluate(game_state)
        print(f"Current game state evaluation: {score}")

        all_moves = self.generate_legal_moves(game_state)
        if not all_moves:
            self.propose_move(Move((0, 0), 0))
            return
        move = random.choice(all_moves)
        self.propose_move(move)
        while True:
            time.sleep(0.2)
            self.propose_move(random.choice(all_moves))

