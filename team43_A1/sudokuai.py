#  (C) Copyright Wieger Wesselink 2021. Distributed under the GPL-3.0-or-later
#  Software License, (See accompanying file LICENSE or copy at
#  https://www.gnu.org/licenses/gpl-3.0.txt)
import copy
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

        for r in range(bi, bi + B):
            for c in range(bj, bj + B):
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

                for value in range(1, N + 1):
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

    def simulate_move(self, game_state: GameState, move: Move) -> GameState:
        """
        It returns game state after applying move
        """
        new_state = copy.deepcopy(game_state)
        new_state.board.put(move.square, move.value)
        new_state.moves.append(move)
        if not new_state.is_classic_game():
            if new_state.current_player == 1:
                new_state.occupied_squares1.append(move.square)
            else:
                new_state.occupied_squares2.append(move.square)
        new_state.current_player = 3 - new_state.current_player
        return new_state

    def count_completions(self, game_state: GameState, move: Move) -> tuple:
        """Conta righe, colonne e regioni completate da questa mossa"""
        board = game_state.board
        (i, j) = move.square
        N = board.N
        B = int(N ** 0.5)

        # Simula temporaneamente la mossa
        old_value = board.get((i, j))
        board.put((i, j), move.value)

        completions = 0

        # Check riga completa
        if all(board.get((i, c)) != SudokuBoard.empty for c in range(N)):
            completions += 1

        # Check colonna completa
        if all(board.get((r, j)) != SudokuBoard.empty for r in range(N)):
            completions += 1

        # Check regione completa
        bi = (i // B) * B
        bj = (j // B) * B
        region_complete = True
        for r in range(bi, bi + B):
            for c in range(bj, bj + B):
                if board.get((r, c)) == SudokuBoard.empty:
                    region_complete = False
                    break
            if not region_complete:
                break
        if region_complete:
            completions += 1

        # Ripristina
        board.put((i, j), old_value)

        # Punteggio: 0->0pts, 1->1pt, 2->3pts, 3->7pts
        points = [0, 1, 3, 7][completions]
        return completions, points

    def evaluate_move_quality(self, game_state: GameState, move: Move) -> float:
        """Valutazione euristica della qualità di una mossa"""
        score = 0.0

        # 1. Punti diretti dalle completion
        completions, points = self.count_completions(game_state, move)
        score += points * 100  # Molto importante!

        # 2. Controlla quante opzioni rimangono dopo questa mossa
        new_state = self.simulate_move(game_state, move)

        # 3. Preferisci mosse che riducono le opzioni dell'avversario
        # (simula cambio giocatore per contare le mosse dell'avversario)
        opponent_state = copy.deepcopy(new_state)
        opponent_state.current_player = 3 - opponent_state.current_player

        # 4. Piccolo bonus casuale per variare
        score += random.random() * 0.01

        return score

    def get_best_moves(self, game_state: GameState, all_moves: list, top_n: int) -> list:
        """Seleziona le top_n mosse migliori usando euristiche veloci"""
        if len(all_moves) <= top_n:
            return all_moves

        # Valuta tutte le mosse
        move_scores = []
        for move in all_moves:
            score = self.evaluate_move_quality(game_state, move)
            move_scores.append((score, move))

        # Ordina e prendi le migliori
        move_scores.sort(reverse=True)
        return [move for _, move in move_scores[:top_n]]

    def evaluate(self, game_state: GameState) -> float:
        """Valutazione semplificata per velocità"""
        my_squares = game_state.player_squares()
        opponent_squares = self.get_opponent_squares(game_state)

        # Differenza di territorio
        score = (len(my_squares) - len(opponent_squares)) * 10
        return score

    def minimax_alpha_beta(self, game_state: GameState, depth: int,
                           alpha: float, beta: float,
                           maximizing: bool,
                           start_time: float,
                           time_limit: float) -> tuple:
        # Check timeout
        elapsed = time.time() - start_time
        if elapsed > time_limit:
            return self.evaluate(game_state), None

        all_moves = self.generate_legal_moves(game_state)

        # Condizione terminale
        if not all_moves or depth == 0:
            score = self.evaluate(game_state)
            return score, None

        # OTTIMIZZAZIONE CHIAVE: Riduci il branching factor in modo intelligente
        # Più siamo profondi, meno mosse esploriamo
        if depth >= 4:
            max_moves = 8
        elif depth >= 3:
            max_moves = 12
        elif depth >= 2:
            max_moves = 15
        else:
            max_moves = 20

        # Seleziona le mosse migliori usando euristiche
        if len(all_moves) > max_moves:
            moves_to_explore = self.get_best_moves(game_state, all_moves, max_moves)
        else:
            moves_to_explore = all_moves

        best_move = None
        if maximizing:
            max_eval = float('-inf')
            for move in moves_to_explore:
                # Check timeout durante l'esplorazione
                if time.time() - start_time > time_limit:
                    break

                new_state = self.simulate_move(game_state, move)
                eval_score, _ = self.minimax_alpha_beta(
                    new_state, depth - 1,
                    alpha, beta,
                    False, start_time,
                    time_limit
                )
                if eval_score > max_eval:
                    max_eval = eval_score
                    best_move = move
                alpha = max(alpha, eval_score)
                if beta <= alpha:
                    break  # Alpha-beta pruning
            return max_eval, best_move
        else:
            min_eval = float('inf')
            for move in moves_to_explore:
                # Check timeout durante l'esplorazione
                if time.time() - start_time > time_limit:
                    break

                new_state = self.simulate_move(game_state, move)
                eval_score, _ = self.minimax_alpha_beta(
                    new_state, depth - 1,
                    alpha, beta,
                    True, start_time,
                    time_limit
                )
                if eval_score < min_eval:
                    min_eval = eval_score
                    best_move = move
                beta = min(beta, eval_score)
                if beta <= alpha:
                    break  # Alpha-beta pruning
            return min_eval, best_move

    def compute_best_move(self, game_state: GameState) -> None:
        all_moves = self.generate_legal_moves(game_state)

        print(f"Player: {game_state.current_player}")
        print(f"Legal moves available: {len(all_moves)}")

        if not all_moves:
            print("WARNING: No legal moves found!")
            return

        # PARAMETRI OTTIMIZZATI
        max_depth = 5  # Prova fino a depth 5
        start_time = time.time()
        time_limit = 0.4  # 400ms - bilanciamento tra sicurezza e performance

        best_move = all_moves[0]
        best_eval = float('-inf')

        # Iterative deepening
        for depth in range(1, max_depth + 1):
            try:
                elapsed = time.time() - start_time
                # Stop molto conservativo - 50% del tempo per sicurezza
                if elapsed > time_limit * 0.5:
                    print(f"Stopping before depth {depth} (elapsed: {elapsed:.3f}s)")
                    break

                print(f"Starting depth {depth}...")
                eval_score, move = self.minimax_alpha_beta(
                    game_state, depth,
                    float('-inf'), float('inf'),
                    True, start_time,
                    time_limit
                )

                elapsed = time.time() - start_time
                print(f"Depth {depth} completed in {elapsed:.3f}s")

                if move is not None:
                    best_move = move
                    best_eval = eval_score
                    print(f"Depth {depth}: move={move.square} -> {move.value}, eval={eval_score}")
                else:
                    print(f"Depth {depth}: No move returned (timeout)")
                    break

                # Interrompi se tempo quasi scaduto
                if elapsed > time_limit * 0.7:
                    print(f"Time limit approaching, stopping at depth {depth}")
                    break

            except Exception as e:
                print(f"ERROR at depth {depth}: {e}")
                import traceback
                traceback.print_exc()
                break

        print(f"Final: {best_move.square} -> {best_move.value}, eval: {best_eval}")
        self.propose_move(best_move)