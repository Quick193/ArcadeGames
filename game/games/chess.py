"""
games/chess.py  -  ChessScene  (Phase 8)
=========================================
Full chess engine ported from chess_game() in games.py.

Features preserved from original
----------------------------------
  All legal-move generation (P N B R Q K)
  Castling (K-side + Q-side) with rights tracking
  En passant
  Pawn promotion dialog (Q R B N)
  Check / checkmate / stalemate detection
  Alpha-beta minimax AI  (depth 1/2/3 = Easy/Medium/Hard)
  MVV-LVA move ordering
  Piece-square tables for all 6 piece types
  Eval bar (vs AI only) with smooth lerp
  Clock / timer with increment
  Board flip when playing Black
  Drag-and-drop  +  click-to-move
  Coordinate labels (a-h, 1-8)
  Last-move highlight
  Move history panel (scrollable, SAN)
  Captured-pieces display

New additions
-------------
  Proper BaseScene integration (no inner event loop)
  dt-based clock countdown
  Ctrl+Z undo  (pops 2 plies vs AI so player gets piece back)
  Stats / achievement recording on game end
"""

from copy import deepcopy
import math
import random
import pygame

from engine import (
    BaseScene, Theme, RenderManager, FontCache,
    draw_text, draw_card, draw_overlay, draw_button, draw_footer_hint,
)
from engine.engine import SCREEN_WIDTH as W, SCREEN_HEIGHT as H

# ─────────────────────────────────────────────────────────────
# Layout
# ─────────────────────────────────────────────────────────────
BOARD_SZ  = 512
SQ        = BOARD_SZ // 8          # 64 px per square
BOARD_X   = (W - BOARD_SZ - 250) // 2 + 30
BOARD_Y   = (H - BOARD_SZ) // 2
SIDE_X    = BOARD_X + BOARD_SZ + 28
SIDE_W    = 220
EVAL_X    = BOARD_X - 50           # left of board

LIGHT_SQ  = (240, 217, 181)
DARK_SQ   = (181, 136,  99)

TIMER_PRESETS = [
    ("No Timer",        0,  0),
    ("1+0  Bullet",     1,  0),
    ("3+2  Blitz",      3,  2),
    ("10+0 Rapid",     10,  0),
    ("30+0 Classical", 30,  0),
]


# ─────────────────────────────────────────────────────────────
# Pure chess logic  (module-level - easily unit-tested)
# ─────────────────────────────────────────────────────────────

def _init_board():
    b = [[None]*8 for _ in range(8)]
    b[0] = list('rnbqkbnr')
    b[1] = ['p']*8
    b[6] = ['P']*8
    b[7] = list('RNBQKBNR')
    return b


def _iw(p): return bool(p and p.isupper())
def _ib(p): return bool(p and p.islower())
def _sc(a, b): return bool(a and b and (_iw(a) == _iw(b)))   # same colour


def _pseudo(board, r, c, ep=None):
    """Return pseudo-legal destination squares for piece at (r,c)."""
    p = board[r][c]
    if not p:
        return []
    moves = []; pt = p.upper(); w = _iw(p)

    def add(nr, nc):
        if 0 <= nr < 8 and 0 <= nc < 8:
            t = board[nr][nc]
            if not _sc(p, t):
                moves.append((nr, nc))
                return t is None   # True = square was empty (keep sliding)
        return False

    if pt == 'P':
        d = -1 if w else 1; sr = 6 if w else 1
        if 0 <= r+d < 8 and not board[r+d][c]:
            moves.append((r+d, c))
            if r == sr and not board[r+2*d][c]:
                moves.append((r+2*d, c))
        for dc in (-1, 1):
            nr, nc = r+d, c+dc
            if 0 <= nr < 8 and 0 <= nc < 8:
                t = board[nr][nc]
                if t and not _sc(p, t):
                    moves.append((nr, nc))
                elif ep and (nr, nc) == ep:
                    moves.append((nr, nc))

    elif pt == 'N':
        for dr, dc in ((-2,-1),(-2,1),(-1,-2),(-1,2),(1,-2),(1,2),(2,-1),(2,1)):
            add(r+dr, c+dc)

    elif pt == 'B':
        for dr, dc in ((-1,-1),(-1,1),(1,-1),(1,1)):
            for i in range(1, 8):
                if not add(r+dr*i, c+dc*i): break

    elif pt == 'R':
        for dr, dc in ((-1,0),(1,0),(0,-1),(0,1)):
            for i in range(1, 8):
                if not add(r+dr*i, c+dc*i): break

    elif pt == 'Q':
        for dr, dc in ((-1,-1),(-1,1),(1,-1),(1,1),(-1,0),(1,0),(0,-1),(0,1)):
            for i in range(1, 8):
                if not add(r+dr*i, c+dc*i): break

    elif pt == 'K':
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if dr or dc: add(r+dr, c+dc)
        # Castling squares (rights checked later in _legal)
        cr = 7 if w else 0
        if r == cr and c == 4:
            if board[cr][7] and board[cr][7].upper()=='R' and not board[cr][5] and not board[cr][6]:
                moves.append((cr, 6))
            if board[cr][0] and board[cr][0].upper()=='R' and not board[cr][1] and not board[cr][2] and not board[cr][3]:
                moves.append((cr, 2))

    return moves


def _apply(board, fr, fc, tr, tc, ep=None, promo='Q'):
    """Apply move; returns (new_board, captured_piece, special_tag)."""
    b = deepcopy(board); p = b[fr][fc]; cap = b[tr][tc]; special = None

    # En passant capture
    if p and p.upper() == 'P' and ep and (tr, tc) == ep:
        cap = b[fr][tc]; b[fr][tc] = None; special = 'ep'

    # Castling - move rook
    if p and p.upper() == 'K' and abs(fc - tc) == 2:
        if tc == 6: b[tr][5] = b[tr][7]; b[tr][7] = None; special = 'ck'
        else:       b[tr][3] = b[tr][0]; b[tr][0] = None; special = 'cq'

    b[tr][tc] = p; b[fr][fc] = None

    # Promotion
    if p and p.upper() == 'P' and (tr == 0 or tr == 7):
        b[tr][tc] = promo.upper() if _iw(p) else promo.lower()
        special = 'promo'

    return b, cap, special


def _find_king(board, white):
    k = 'K' if white else 'k'
    for r in range(8):
        for c in range(8):
            if board[r][c] == k: return (r, c)
    return None


def _attacked(board, r, c, by_white):
    """Is square (r,c) attacked by the given colour?"""
    for rr in range(8):
        for cc in range(8):
            p = board[rr][cc]
            if not p or _iw(p) != by_white: continue
            if p.upper() == 'P':
                d = -1 if _iw(p) else 1
                if rr+d == r and abs(cc-c) == 1: return True
            else:
                if (r, c) in _pseudo(board, rr, cc): return True
    return False


def _in_check(board, white):
    kp = _find_king(board, white)
    return bool(kp and _attacked(board, kp[0], kp[1], not white))


def _legal(board, r, c, castling, ep):
    """Fully legal moves for piece at (r,c)."""
    p = board[r][c]
    if not p: return []
    w = _iw(p); result = []

    for (tr, tc) in _pseudo(board, r, c, ep):
        # Castling legality: check rights and that squares aren't attacked
        if p.upper() == 'K' and abs(c - tc) == 2:
            cr = 7 if w else 0
            key = ('K' if w else 'k') if tc == 6 else ('Q' if w else 'q')
            if not castling.get(key): continue
            mid = 5 if tc == 6 else 3
            if _attacked(board, cr, 4, not w) or _attacked(board, cr, mid, not w) or _attacked(board, cr, tc, not w):
                continue
        nb, _, _ = _apply(board, r, c, tr, tc, ep)
        if not _in_check(nb, w):
            result.append((tr, tc))

    return result


def _has_legal(board, white, castling, ep):
    for r in range(8):
        for c in range(8):
            p = board[r][c]
            if p and _iw(p) == white:
                if _legal(board, r, c, castling, ep): return True
    return False


def _status(board, white, castling, ep):
    check = _in_check(board, white)
    has   = _has_legal(board, white, castling, ep)
    if not has: return 'checkmate' if check else 'stalemate'
    return 'check' if check else 'ongoing'


# ─── Evaluation ────────────────────────────────────────────────

_MAT = {'P':100,'N':320,'B':330,'R':500,'Q':900,'K':20000}

_PST = {
    'P':[0,0,0,0,0,0,0,0,
         50,50,50,50,50,50,50,50,
         10,10,20,30,30,20,10,10,
         5,5,10,25,25,10,5,5,
         0,0,0,20,20,0,0,0,
         5,-5,-10,0,0,-10,-5,5,
         5,10,10,-20,-20,10,10,5,
         0,0,0,0,0,0,0,0],
    'N':[-50,-40,-30,-30,-30,-30,-40,-50,
         -40,-20,0,0,0,0,-20,-40,
         -30,0,10,15,15,10,0,-30,
         -30,5,15,20,20,15,5,-30,
         -30,0,15,20,20,15,0,-30,
         -30,5,10,15,15,10,5,-30,
         -40,-20,0,5,5,0,-20,-40,
         -50,-40,-30,-30,-30,-30,-40,-50],
    'B':[-20,-10,-10,-10,-10,-10,-10,-20,
         -10,0,0,0,0,0,0,-10,
         -10,0,5,10,10,5,0,-10,
         -10,5,5,10,10,5,5,-10,
         -10,0,10,10,10,10,0,-10,
         -10,10,10,10,10,10,10,-10,
         -10,5,0,0,0,0,5,-10,
         -20,-10,-10,-10,-10,-10,-10,-20],
    'R':[0,0,0,0,0,0,0,0,
         5,10,10,10,10,10,10,5,
         -5,0,0,0,0,0,0,-5,
         -5,0,0,0,0,0,0,-5,
         -5,0,0,0,0,0,0,-5,
         -5,0,0,0,0,0,0,-5,
         -5,0,0,0,0,0,0,-5,
         0,0,0,5,5,0,0,0],
    'Q':[-20,-10,-10,-5,-5,-10,-10,-20,
         -10,0,0,0,0,0,0,-10,
         -10,0,5,5,5,5,0,-10,
         -5,0,5,5,5,5,0,-5,
         0,0,5,5,5,5,0,-5,
         -10,5,5,5,5,5,0,-10,
         -10,0,5,0,0,0,0,-10,
         -20,-10,-10,-5,-5,-10,-10,-20],
    'K':[-30,-40,-40,-50,-50,-40,-40,-30,
         -30,-40,-40,-50,-50,-40,-40,-30,
         -30,-40,-40,-50,-50,-40,-40,-30,
         -30,-40,-40,-50,-50,-40,-40,-30,
         -20,-30,-30,-40,-40,-30,-30,-20,
         -10,-20,-20,-20,-20,-20,-20,-10,
         20,20,0,0,0,0,20,20,
         20,30,10,0,0,10,30,20],
}


def _evaluate(board):
    """Static material + positional evaluation. Returns score in pawn-units (white positive)."""
    score = 0
    white_mobility = 0; black_mobility = 0
    for r in range(8):
        for c in range(8):
            p = board[r][c]
            if not p: continue
            pt = p.upper()
            v   = _MAT.get(pt, 0)
            pst = _PST.get(pt, [0]*64)
            if _iw(p):
                score += v + pst[r*8+c]
                white_mobility += len(_pseudo_moves(board, r, c))
            else:
                score -= v + pst[(7-r)*8+c]
                black_mobility += len(_pseudo_moves(board, r, c))
    # Mobility bonus (5 cp per extra move)
    score += (white_mobility - black_mobility) * 5
    return score / 100.0


def _pseudo_moves(board, r, c):
    """Fast pseudo-legal move count for a piece (used in eval mobility)."""
    p = board[r][c]
    if not p: return []
    pt = p.upper(); white = _iw(p); dirs = []
    moves = []
    if pt == 'P':
        dr = -1 if white else 1
        if 0 <= r+dr < 8 and not board[r+dr][c]: moves.append((r+dr,c))
        for dc in (-1,1):
            if 0<=r+dr<8 and 0<=c+dc<8 and board[r+dr][c+dc] and _iw(board[r+dr][c+dc])!=white:
                moves.append((r+dr,c+dc))
    elif pt == 'N':
        for dr,dc in [(-2,-1),(-2,1),(-1,-2),(-1,2),(1,-2),(1,2),(2,-1),(2,1)]:
            nr,nc=r+dr,c+dc
            if 0<=nr<8 and 0<=nc<8 and (not board[nr][nc] or _iw(board[nr][nc])!=white):
                moves.append((nr,nc))
    elif pt in ('B','R','Q'):
        if pt in ('B','Q'): dirs += [(-1,-1),(-1,1),(1,-1),(1,1)]
        if pt in ('R','Q'): dirs += [(-1,0),(1,0),(0,-1),(0,1)]
        for dr,dc in dirs:
            nr,nc=r+dr,c+dc
            while 0<=nr<8 and 0<=nc<8:
                if board[nr][nc]:
                    if _iw(board[nr][nc])!=white: moves.append((nr,nc))
                    break
                moves.append((nr,nc)); nr+=dr; nc+=dc
    elif pt == 'K':
        for dr in (-1,0,1):
            for dc in (-1,0,1):
                if dr==dc==0: continue
                nr,nc=r+dr,c+dc
                if 0<=nr<8 and 0<=nc<8 and (not board[nr][nc] or _iw(board[nr][nc])!=white):
                    moves.append((nr,nc))
    return moves


def _minimax(board, depth, alpha, beta, maximising, castling, ep):
    if depth <= 0: return _evaluate(board)

    moves = []
    for r in range(8):
        for c in range(8):
            p = board[r][c]
            if p and _iw(p) == maximising:
                for m in _legal(board, r, c, castling, ep):
                    t = board[m[0]][m[1]]
                    sort_score = 0
                    if t:
                        vv = {'p':1,'n':3,'b':3,'r':5,'q':9,'k':0}.get(t.lower(), 0)
                        av = {'p':1,'n':2,'b':2,'r':3,'q':4,'k':5}.get(p.lower(), 0)
                        sort_score = 100 + vv*10 - av
                    moves.append(((r,c), m, sort_score))

    if not moves:
        # No moves: checkmate or stalemate.
        # Checkmate: the CURRENT player (maximising) has no escape.
        # If maximising=True  → White is mated  → very bad for White  → return large NEGATIVE
        # If maximising=False → Black is mated  → very good for White → return large POSITIVE
        if _in_check(board, maximising):
            return -(10000 + depth) if maximising else (10000 + depth)
        return 0  # stalemate

    moves.sort(key=lambda x: x[2], reverse=True)

    if maximising:
        best = float('-inf')
        for (fr,fc),(tr,tc),_ in moves:
            nb,_,_ = _apply(board, fr, fc, tr, tc, ep)
            v = _minimax(nb, depth-1, alpha, beta, False, castling, None)
            best = max(best, v); alpha = max(alpha, best)
            if beta <= alpha: break
        return best
    else:
        best = float('inf')
        for (fr,fc),(tr,tc),_ in moves:
            nb,_,_ = _apply(board, fr, fc, tr, tc, ep)
            v = _minimax(nb, depth-1, alpha, beta, True, castling, None)
            best = min(best, v); beta = min(beta, best)
            if beta <= alpha: break
        return best


def _position_eval(board, castling, ep, depth=3):
    """Run minimax at given depth from White's POV. Returns (score, mate_in).
    score in pawn-units; mate_in = +N (white mates in N), -N (black), None.

    Minimax returns +(10000+depth_remaining) when Black is mated (White wins),
    -(10000+depth_remaining) when White is mated (Black wins).
    """
    raw = _minimax(board, depth, float('-inf'), float('inf'), True, castling, ep)
    MATE_THRESH = 5000   # anything beyond ±5000 is a mate score, not material
    if abs(raw) >= MATE_THRESH:
        # depth_remaining at checkmate node
        depth_remaining = int(abs(raw)) - 10000
        # Half-moves from root to the checkmate = depth - depth_remaining
        half_moves = depth - depth_remaining
        moves_to_mate = max(1, math.ceil(half_moves / 2))
        mate_in = moves_to_mate if raw > 0 else -moves_to_mate
        bar_score = 20.0 if raw > 0 else -20.0   # peg bar to extreme
        return bar_score, mate_in
    return raw, None


def _ai_best_move(board, castling, ep, difficulty, ai_white):
    """Return best move for given side. Higher depth = stronger play."""
    depth = {'easy': 2, 'medium': 3, 'hard': 4}.get(difficulty, 2)
    rand_chance = {'easy': 0.35, 'medium': 0.08, 'hard': 0.0}.get(difficulty, 0.0)

    all_moves = []
    for r in range(8):
        for c in range(8):
            p = board[r][c]
            if p and _iw(p) == ai_white:
                for m in _legal(board, r, c, castling, ep):
                    all_moves.append(((r,c), m))

    if not all_moves:
        return None

    # Easy: occasionally pick a random legal move
    if rand_chance > 0 and random.random() < rand_chance:
        return random.choice(all_moves)

    random.shuffle(all_moves)   # shuffle for variety among equal moves
    best_val = float('-inf') if ai_white else float('inf')
    best = None
    alpha = float('-inf'); beta = float('inf')

    # Move ordering: captures first (faster alpha-beta pruning)
    def move_score(mv):
        (fr,fc),(tr,tc) = mv
        t = board[tr][tc]
        if t:
            vv = {'p':1,'n':3,'b':3,'r':5,'q':9}.get(t.lower(), 0)
            av = {'p':1,'n':2,'b':2,'r':3,'q':4}.get(board[fr][fc].lower(), 0)
            return 100 + vv*10 - av
        return 0
    all_moves.sort(key=move_score, reverse=True)

    for (fr,fc),(tr,tc) in all_moves:
        nb,_,_ = _apply(board, fr, fc, tr, tc, ep)
        val = _minimax(nb, depth-1, alpha, beta, not ai_white, castling, None)
        if ai_white:
            if best is None or val > best_val:
                best_val = val; best = ((fr,fc),(tr,tc))
            alpha = max(alpha, best_val)
        else:
            # AI is black, minimise
            if best is None or val < best_val:
                best_val = val; best = ((fr,fc),(tr,tc))
            beta = min(beta, best_val)
        if beta <= alpha: break

    return best


def _san(board, fr, fc, tr, tc, promo=None):
    p = board[fr][fc]
    if not p: return ''
    files = 'abcdefgh'; ranks = '87654321'
    end = files[tc] + ranks[tr]
    cap = bool(board[tr][tc])
    if p.upper()=='P' and abs(fc-tc)==1 and not cap: cap = True  # en passant
    pt = p.upper()
    if pt=='K' and abs(fc-tc)==2: return 'O-O' if tc > fc else 'O-O-O'
    if pt=='P':
        s = (files[fc]+'x'+end) if cap else end
        if promo: s += '='+promo.upper()
        return s
    return pt + ('x' if cap else '') + end


# ─────────────────────────────────────────────────────────────
# Piece drawing  (preserved exactly from draw_chess_piece)
# ─────────────────────────────────────────────────────────────

def _draw_piece(surface, pt, white, x, y, size):
    color   = (255, 255, 255) if white else ( 20,  20,  20)
    outline = ( 30,  30,  30) if white else ( 80,  80,  80)
    cx, cy  = x + size//2, y + size//2
    s       = size / 70

    def I(v):   return int(v * s)
    def poly(pts):
        pygame.draw.polygon(surface, color,   pts)
        pygame.draw.lines  (surface, outline, True, pts, 2)
    def ell(rect):
        pygame.draw.ellipse(surface, color,   rect)
        pygame.draw.ellipse(surface, outline, rect, 2)
    def rect(rx, ry, rw, rh):
        pygame.draw.rect(surface, color,   (rx, ry, rw, rh))
        pygame.draw.rect(surface, outline, (rx, ry, rw, rh), 1)

    if pt == 'P':
        poly([(cx-I(12),cy+I(20)),(cx+I(12),cy+I(20)),(cx+I(10),cy+I(16)),(cx-I(10),cy+I(16))])
        poly([(cx-I(8),cy+I(16)),(cx-I(4),cy-I(4)),(cx+I(4),cy-I(4)),(cx+I(8),cy+I(16))])
        rect(cx-I(6), cy-I(8), I(12), I(4))
        pygame.draw.circle(surface, color,   (cx, cy-I(12)), I(9))
        pygame.draw.circle(surface, outline, (cx, cy-I(12)), I(9), 2)

    elif pt == 'R':
        poly([(cx-I(15),cy+I(20)),(cx+I(15),cy+I(20)),(cx+I(13),cy+I(15)),(cx-I(13),cy+I(15))])
        rect(cx-I(11), cy-I(12), I(22), I(27))
        rect(cx-I(13), cy-I(18), I(26), I( 6))
        for bx in (-10, -2, 6):
            rect(cx+I(bx), cy-I(24), I(6), I(6))

    elif pt == 'N':
        poly([(cx-I(12),cy+I(20)),(cx+I(12),cy+I(20)),(cx+I(10),cy+I(15)),
              (cx+I( 6),cy+I(10)),(cx+I(14),cy-I( 5)),(cx+I(14),cy-I(12)),
              (cx+I( 6),cy-I(15)),(cx+I( 4),cy-I(22)),(cx-I( 2),cy-I(18)),
              (cx-I( 6),cy-I(12)),(cx-I(10),cy+I( 5)),(cx-I(10),cy+I(15))])
        ec = (255,255,255) if not white else (0,0,0)
        pygame.draw.circle(surface, ec, (cx+I(6), cy-I(12)), 1)

    elif pt == 'B':
        poly([(cx-I(12),cy+I(20)),(cx+I(12),cy+I(20)),(cx+I(10),cy+I(15)),(cx-I(10),cy+I(15))])
        ell((cx-I(9),  cy-I(12), I(18), I(27)))
        ell((cx-I(10), cy-I(22), I(20), I(25)))
        pygame.draw.line(surface, outline, (cx+I(2),cy-I(18)), (cx+I(8),cy-I(12)), 2)
        pygame.draw.circle(surface, color,   (cx, cy-I(24)), I(4))
        pygame.draw.circle(surface, outline, (cx, cy-I(24)), I(4), 1)

    elif pt == 'Q':
        poly([(cx-I(15),cy+I(20)),(cx+I(15),cy+I(20)),(cx+I(13),cy+I(15)),(cx-I(13),cy+I(15))])
        poly([(cx-I(11),cy+I(15)),(cx+I(11),cy+I(15)),(cx+I(6),cy-I(10)),(cx-I(6),cy-I(10))])
        for qx in (-12,-6,0,6,12):
            pygame.draw.line(surface, outline, (cx,cy-I(5)), (cx+I(qx),cy-I(18)), 2)
            pygame.draw.circle(surface, color,   (cx+I(qx), cy-I(18)), I(4))
            pygame.draw.circle(surface, outline, (cx+I(qx), cy-I(18)), I(4), 1)
        pygame.draw.circle(surface, color,   (cx, cy-I(24)), I(5))
        pygame.draw.circle(surface, outline, (cx, cy-I(24)), I(5), 2)

    elif pt == 'K':
        poly([(cx-I(15),cy+I(20)),(cx+I(15),cy+I(20)),(cx+I(13),cy+I(15)),(cx-I(13),cy+I(15))])
        rect(cx-I(11), cy-I(10), I(22), I(25))
        poly([(cx-I(14),cy-I(10)),(cx+I(14),cy-I(10)),(cx+I(10),cy-I(18)),(cx-I(10),cy-I(18))])
        rect(cx-I(2),  cy-I(28), I( 4), I(12))
        rect(cx-I(8),  cy-I(24), I(16), I( 4))



# ─────────────────────────────────────────────────────────────
# Annotation helpers
# ─────────────────────────────────────────────────────────────

def _draw_arrow_pixels(screen, fx, fy, tx, ty, color, width=8):
    """Draw a straight filled arrow from pixel (fx,fy) to (tx,ty)."""
    import math as _math
    dx = tx - fx; dy = ty - fy
    dist = _math.hypot(dx, dy)
    if dist < 4: return
    ux = dx/dist; uy = dy/dist
    tx2 = tx - ux*14; ty2 = ty - uy*14   # shorten for arrowhead
    surf = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
    pygame.draw.line(surf, color, (int(fx), int(fy)), (int(tx2), int(ty2)), width)
    # Arrowhead triangle
    pw = 14; ph = 18
    lx = tx - ux*ph + uy*pw/2
    ly = ty - uy*ph - ux*pw/2
    rx = tx - ux*ph - uy*pw/2
    ry = ty - uy*ph + ux*pw/2
    pygame.draw.polygon(surf, color, [(int(tx),int(ty)),(int(lx),int(ly)),(int(rx),int(ry))])
    screen.blit(surf, (0,0))


def _draw_board_arrow(screen, from_sq, to_sq, flip, color, SQ_size, BX, BY):
    """Draw an annotation arrow between two board squares.
    Knight moves get an L-shaped path; others are straight."""
    fr, fc = from_sq; tr, tc = to_sq
    dr = tr - fr; dc = tc - fc

    def sq_center(br, bc):
        sr = 7-br if flip else br
        sc = 7-bc if flip else bc
        return BX + sc*SQ_size + SQ_size//2, BY + sr*SQ_size + SQ_size//2

    fx, fy = sq_center(fr, fc)
    tx, ty = sq_center(tr, tc)

    # Detect knight move: |dr|+|dc|==3 with |dr|!=0 and |dc|!=0
    if abs(dr) + abs(dc) == 3 and abs(dr) in (1, 2) and abs(dc) in (1, 2):
        # Draw L-shaped: first horizontal segment, then vertical (or vice-versa)
        # Elbow is at the horizontal corner: same rank as dest, same file as source
        ex, ey = sq_center(fr, tc)   # elbow: row=from, col=to
        # Draw two arrow segments; arrowhead only on final segment
        surf = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        pygame.draw.line(surf, color, (int(fx), int(fy)), (int(ex), int(ey)), 8)
        screen.blit(surf, (0,0))
        _draw_arrow_pixels(screen, ex, ey, tx, ty, color)
    else:
        _draw_arrow_pixels(screen, fx, fy, tx, ty, color)


# ─────────────────────────────────────────────────────────────
# PGN-like save / load  (stored in data/chess_saves/)
# ─────────────────────────────────────────────────────────────

import os as _os, json as _json

_SAVE_DIR = _os.path.join(_os.path.dirname(__file__), '..', 'data', 'chess_saves')


def _save_game(scene) -> str:
    """Serialise game state to JSON and write to save slot. Returns path."""
    _os.makedirs(_SAVE_DIR, exist_ok=True)
    state = {
        "board":     scene._board,
        "turn":      scene._turn,
        "castling":  scene._castling,
        "ep":        list(scene._ep) if scene._ep else None,
        "history":   scene._history,
        "cap_w":     scene._cap_w,
        "cap_b":     scene._cap_b,
        "mode":      scene._mode,
        "pcolor":    scene._pcolor,
        "diff":      scene._diff,
        "timer_i":   scene._timer_i,
        "white_ms":  scene._white_ms,
        "black_ms":  scene._black_ms,
        "status":    scene._game_status,
    }
    path = _os.path.join(_SAVE_DIR, 'autosave.json')
    with open(path, 'w') as f:
        _json.dump(state, f, indent=2)
    return path


def _load_game(scene) -> bool:
    """Restore game state from JSON save. Returns True on success."""
    path = _os.path.join(_SAVE_DIR, 'autosave.json')
    if not _os.path.exists(path):
        return False
    try:
        with open(path) as f:
            s = _json.load(f)
        scene._board      = [list(row) for row in s["board"]]
        scene._turn       = s["turn"]
        scene._castling   = s["castling"]
        scene._ep         = tuple(s["ep"]) if s["ep"] else None
        scene._history    = s["history"]
        scene._cap_w      = s["cap_w"]
        scene._cap_b      = s["cap_b"]
        scene._mode       = s["mode"]
        scene._pcolor     = s["pcolor"]
        scene._diff       = s["diff"]
        scene._timer_i    = s["timer_i"]
        scene._white_ms   = s["white_ms"]
        scene._black_ms   = s["black_ms"]
        scene._game_status = s["status"]
        scene._selected   = None; scene._legal_sq = []
        scene._last_move  = None; scene._ai_pending = False
        scene._dragging   = None; scene._promo = None
        scene._arrows = []; scene._circles = []
        scene._rclick_start = None
        scene._mate_in = None
        return True
    except Exception:
        return False


# ─────────────────────────────────────────────────────────────
# ChessScene
# ─────────────────────────────────────────────────────────────

class ChessScene(BaseScene):
    GAME_ID = "chess"

    # ── Lifecycle ──────────────────────────────────────────────

    def on_enter(self):
        self._phase   = "mode"
        self._sel     = 0
        self._mode    = "ai"
        self._pcolor  = "white"
        self._diff    = "medium"
        self._timer_i = 0          # index into TIMER_PRESETS
        self._anim_t  = 0.0
        self._init_game()

    def _init_game(self):
        self._board     = _init_board()
        self._turn      = True     # True = White's turn
        self._castling  = {'K':True,'Q':True,'k':True,'q':True}
        self._ep        = None     # en-passant target square
        self._selected  = None
        self._legal_sq  = []
        self._last_move = None     # [(fr,fc),(tr,tc)]
        self._game_status = 'ongoing'
        self._history   = []       # SAN strings
        self._cap_w     = []       # captured white pieces
        self._cap_b     = []
        self._dragging  = None     # (r,c, mx,my)
        self._promo     = None     # {'from':..,'to':..,'white':bool}
        self._undo_stack = []
        # Eval bar (raw score or mate-in-N)
        self._eval_target  = 0.0
        self._eval_visual  = 0.0
        self._mate_in      = None   # None or int (positive = white mates)
        self._eval_dirty   = True   # recompute eval next frame
        # AI flag
        self._ai_pending   = False
        # Session timer (for stats)
        self._session_t    = 0.0
        self._hist_scroll  = 0
        # Clocks
        _, mins, inc = TIMER_PRESETS[self._timer_i]
        self._time_on  = mins > 0
        self._white_ms = mins * 60_000
        self._black_ms = mins * 60_000
        self._incr_ms  = inc  * 1_000
        # Board annotations: arrows = [(from_sq, to_sq, color)], circles = [(sq, color)]
        self._arrows:  list[tuple] = []
        self._circles: list[tuple] = []
        # Right-click drag state for annotation
        self._rclick_start: tuple | None = None   # board square where RMB pressed
        self._rclick_color = (255, 100, 100, 180) # red by default, shift=green, ctrl=blue
        self._save_msg: tuple[str,float] | None = None   # (text, seconds_remaining)

    def _snapshot(self):
        return dict(
            board=deepcopy(self._board), turn=self._turn,
            castling=dict(self._castling), ep=self._ep,
            cap_w=self._cap_w[:], cap_b=self._cap_b[:],
            history=self._history[:],
            white_ms=self._white_ms, black_ms=self._black_ms,
        )

    def _restore(self, snap):
        self._board     = snap['board']; self._turn  = snap['turn']
        self._castling  = snap['castling']; self._ep = snap['ep']
        self._cap_w     = snap['cap_w'];  self._cap_b = snap['cap_b']
        self._history   = snap['history']
        self._white_ms  = snap['white_ms']; self._black_ms = snap['black_ms']
        self._selected  = None; self._legal_sq = []
        self._last_move = None; self._ai_pending = False
        self._game_status = _status(self._board, self._turn, self._castling, self._ep)
        self._eval_dirty = True

    # ── Update ─────────────────────────────────────────────────

    def update(self, dt):
        self._anim_t += dt
        if self._phase != "game": return
        if self._game_status == 'ongoing': self._session_t += dt
        # Save/load message timer
        if self._save_msg:
            txt, rem = self._save_msg
            rem -= dt
            self._save_msg = (txt, rem) if rem > 0 else None

        # Clock countdown
        if self._time_on and self._game_status in ('ongoing','check'):
            ms = int(dt * 1000)
            if self._turn: self._white_ms = max(0, self._white_ms - ms)
            else:          self._black_ms = max(0, self._black_ms - ms)
            if self._white_ms <= 0 or self._black_ms <= 0:
                self._game_status = 'timeout'
                self._finish()
                return

        # Smooth eval bar — recompute only after each move (dirty flag)
        if getattr(self, '_eval_dirty', True):
            self._eval_dirty = False
            raw, mate = _position_eval(self._board, self._castling, self._ep, depth=2)
            self._mate_in     = mate
            self._eval_target = raw
        self._eval_visual += (self._eval_target - self._eval_visual) * min(1.0, dt * 4)

        # AI move
        if self._ai_pending and self._game_status in ('ongoing','check'):
            ai_white = (self._pcolor == 'black')   # AI plays the other colour
            if self._turn == ai_white:
                self._ai_pending = False
                move = _ai_best_move(self._board, self._castling, self._ep, self._diff, ai_white)
                if move:
                    (fr,fc),(tr,tc) = move
                    self._execute(fr, fc, tr, tc)

    # ── Draw ───────────────────────────────────────────────────

    def draw(self, screen):
        screen.blit(RenderManager.get_background(W, H), (0, 0))
        if   self._phase == "mode":       self._draw_menu(screen, "CHESS", ["Player vs Player","Player vs Computer"])
        elif self._phase == "color":      self._draw_menu(screen, "Your Color", ["White (Move First)","Black (Move Second)"])
        elif self._phase == "difficulty": self._draw_menu(screen, "AI Difficulty", ["Easy","Medium","Hard"])
        elif self._phase == "timer":      self._draw_timer(screen)
        else:                             self._draw_game(screen)

    def _draw_menu(self, screen, title, opts):
        draw_text(screen, title, FontCache.get("Segoe UI",48,bold=True),
                  Theme.TEXT_PRIMARY, W//2, 130, align="center")
        bf = FontCache.get("Segoe UI", 22)
        for i, opt in enumerate(opts):
            draw_button(screen, ((W-340)//2, 270+i*80, 340, 60), opt, bf,
                        i==self._sel, Theme.ACCENT_PURPLE, self._anim_t*60)
        draw_footer_hint(screen, "^v Select  |  Enter Confirm  |  Q Back", y_offset=26)

    def _draw_timer(self, screen):
        draw_text(screen, "Time Control", FontCache.get("Segoe UI",48,bold=True),
                  Theme.TEXT_PRIMARY, W//2, 120, align="center")
        bf = FontCache.get("Segoe UI", 21)
        for i,(label,_,_) in enumerate(TIMER_PRESETS):
            draw_button(screen, ((W-340)//2, 240+i*72, 340, 54), label, bf,
                        i==self._sel, Theme.ACCENT_PURPLE, self._anim_t*60)
        draw_footer_hint(screen, "^v Select  |  Enter Confirm  |  Q Back", y_offset=26)

    def _draw_game(self, screen):
        self._draw_board(screen)
        self._draw_sidebar(screen)
        if self._mode == "ai": self._draw_eval_bar(screen)
        if self._promo:
            self._draw_promotion(screen)
        elif self._game_status in ('checkmate','stalemate','timeout'):
            self._draw_end(screen)
        # Save / load toast
        if self._save_msg:
            txt, rem = self._save_msg
            alpha = min(255, int(rem * 255)) if rem < 0.5 else 255
            tf = FontCache.get("Segoe UI", 15, bold=True)
            tw, th = tf.size(txt)
            sx2 = (W - tw - 20) // 2; sy2 = BOARD_Y + BOARD_SZ + 32
            toast = pygame.Surface((tw+20, th+10), pygame.SRCALPHA)
            toast.fill((20,20,30,min(200, alpha)))
            screen.blit(toast, (sx2, sy2))
            draw_text(screen, txt, tf, (*Theme.ACCENT_GREEN, alpha), W//2, sy2+th//2+5, align="center")

    # ── Board drawing ───────────────────────────────────────────

    def _draw_board(self, screen):
        flip = (self._mode == "ai" and self._pcolor == "black")

        def to_board(sr, sc):
            """Screen row/col > board row/col."""
            return (7-sr, 7-sc) if flip else (sr, sc)

        draw_card(screen, (BOARD_X-8, BOARD_Y-8, BOARD_SZ+16, BOARD_SZ+16))

        for sr in range(8):
            for sc in range(8):
                br, bc = to_board(sr, sc)
                x = BOARD_X + sc*SQ;  y = BOARD_Y + sr*SQ
                light = (sr+sc)%2 == 0
                base  = LIGHT_SQ if light else DARK_SQ

                # Base square colour
                pygame.draw.rect(screen, base, (x, y, SQ, SQ))

                # Highlights: semi-transparent overlays drawn on top
                if self._last_move and (br,bc) in self._last_move:
                    hl = pygame.Surface((SQ, SQ), pygame.SRCALPHA)
                    hl.fill((255, 230, 60, 110))   # yellow, ~43% opacity
                    screen.blit(hl, (x, y))
                if self._selected and (br,bc) == self._selected:
                    hl = pygame.Surface((SQ, SQ), pygame.SRCALPHA)
                    hl.fill((80, 200, 80, 120))    # green, ~47% opacity
                    screen.blit(hl, (x, y))

                # Legal-move markers
                if (br,bc) in self._legal_sq:
                    if self._board[br][bc]:
                        # Corner brackets for captures
                        for ex, ey in [(x,y),(x+SQ-14,y),(x,y+SQ-14),(x+SQ-14,y+SQ-14)]:
                            pygame.draw.line(screen, Theme.ACCENT_ORANGE, (ex,ey), (ex+12,ey+12), 3)
                    else:
                        # Translucent dot for empty squares
                        dot = pygame.Surface((SQ,SQ), pygame.SRCALPHA)
                        pygame.draw.circle(dot, (0,0,0,55), (SQ//2,SQ//2), SQ//6)
                        screen.blit(dot, (x,y))

        # Pieces (skip dragged piece)
        for sr in range(8):
            for sc in range(8):
                br, bc = to_board(sr, sc)
                if self._dragging and (br,bc) == (self._dragging[0],self._dragging[1]):
                    continue
                p = self._board[br][bc]
                if p: _draw_piece(screen, p.upper(), _iw(p), BOARD_X+sc*SQ, BOARD_Y+sr*SQ, SQ)

        # Dragging piece - follows cursor
        if self._dragging:
            dr, dc, mx, my = self._dragging
            p = self._board[dr][dc]
            if p: _draw_piece(screen, p.upper(), _iw(p), mx-SQ//2, my-SQ//2, SQ)

        # Annotation: circles
        for (ar, ac), col in self._circles:
            asr = 7-ar if flip else ar
            asc = 7-ac if flip else ac
            ann = pygame.Surface((SQ, SQ), pygame.SRCALPHA)
            pygame.draw.circle(ann, (*col[:3], 180), (SQ//2, SQ//2), SQ//2-4, 4)
            screen.blit(ann, (BOARD_X+asc*SQ, BOARD_Y+asr*SQ))

        # Annotation: arrows (board-coord-aware, L-shape for knights)
        for from_sq, to_sq, col in self._arrows:
            _draw_board_arrow(screen, from_sq, to_sq, flip, (*col[:3], 180), SQ, BOARD_X, BOARD_Y)

        # In-progress RMB drag: show ghost arrow
        if self._rclick_start:
            mx2, my2 = pygame.mouse.get_pos()
            if BOARD_X <= mx2 < BOARD_X+BOARD_SZ and BOARD_Y <= my2 < BOARD_Y+BOARD_SZ:
                asc2=(mx2-BOARD_X)//SQ; asr2=(my2-BOARD_Y)//SQ
                ttr, ttc = to_board(asr2, asc2)
                sfr, sfc = self._rclick_start
                if (sfr, sfc) != (ttr, ttc):
                    _draw_board_arrow(screen, (sfr,sfc), (ttr,ttc), flip,
                                      (*self._rclick_color[:3], 100), SQ, BOARD_X, BOARD_Y)

        # Coordinate labels
        cf    = FontCache.get("Segoe UI", 11, bold=True)
        files = 'abcdefgh'; ranks = '87654321'
        for i in range(8):
            fc = files[7-i] if flip else files[i]
            rk = ranks[7-i] if flip else ranks[i]
            screen.blit(cf.render(rk, True, Theme.TEXT_MUTED),
                        (BOARD_X-20, BOARD_Y + i*SQ + SQ//2 - 6))
            screen.blit(cf.render(fc, True, Theme.TEXT_MUTED),
                        (BOARD_X + i*SQ + SQ//2 - 4, BOARD_Y + BOARD_SZ + 8))

        # Check highlight on king
        if self._game_status == 'check':
            kp = _find_king(self._board, self._turn)
            if kp:
                kr, kc = kp
                sr2 = 7-kr if flip else kr
                sc2 = 7-kc if flip else kc
                hl = pygame.Surface((SQ, SQ), pygame.SRCALPHA)
                pygame.draw.rect(hl, (220,60,60,110), (0,0,SQ,SQ), border_radius=4)
                screen.blit(hl, (BOARD_X+sc2*SQ, BOARD_Y+sr2*SQ))

        # Clocks above/below board
        if self._time_on:
            self._draw_clocks(screen, flip)

        draw_footer_hint(screen,
            "Drag pieces | RMB annotate (Shift=green Ctrl=blue) | C clear | Ctrl+Z Undo | Ctrl+S Save | Ctrl+L Load | N New | Q Menu",
            y_offset=26)

    def _draw_clocks(self, screen, flip):
        def fmt(ms):
            t = max(0, ms)//1000
            return f"{t//60:02d}:{t%60:02d}"

        # top clock = black (unless flipped)
        top_ms  = self._black_ms if not flip else self._white_ms
        bot_ms  = self._white_ms if not flip else self._black_ms
        top_active = not self._turn  if not flip else self._turn

        for ms, yy, active in [
            (top_ms, BOARD_Y - 52, top_active),
            (bot_ms, BOARD_Y + BOARD_SZ + 12, not top_active),
        ]:
            cw, ch = 220, 38
            cx2 = BOARD_X + BOARD_SZ//2 - cw//2
            draw_card(screen, (cx2, yy, cw, ch))
            if active:
                pygame.draw.rect(screen, Theme.ACCENT_PURPLE, (cx2,yy,cw,ch), 2, border_radius=12)
            color = Theme.ACCENT_RED if ms < 10_000 else Theme.TEXT_PRIMARY
            draw_text(screen, fmt(ms), FontCache.get("Segoe UI",22,bold=True),
                      color, cx2+cw//2, yy+ch//2, align="center")

    def _draw_sidebar(self, screen):
        sx, sy = SIDE_X, BOARD_Y

        # Turn indicator
        draw_card(screen, (sx, sy, SIDE_W, 60))
        draw_text(screen, "TURN", FontCache.get("Segoe UI",10,bold=True),
                  Theme.TEXT_MUTED, sx+14, sy+10)
        tc = Theme.TEXT_PRIMARY if self._turn else Theme.ACCENT_PURPLE
        draw_text(screen, "WHITE" if self._turn else "BLACK",
                  FontCache.get("Segoe UI",24,bold=True), tc, sx+14, sy+28)
        sy += 70

        # Captured pieces — show per-type counts in a compact grid
        draw_card(screen, (sx, sy, SIDE_W, 78))
        draw_text(screen, "CAPTURED", FontCache.get("Segoe UI",9,bold=True),
                  Theme.TEXT_MUTED, sx+14, sy+8)

        cf  = FontCache.get("Segoe UI", 11, bold=True)
        cf2 = FontCache.get("Segoe UI", 10)

        # White pieces captured by Black (shown in top row, dim white)
        from collections import Counter
        white_counts = Counter(p.upper() for p in self._cap_w)  # white pieces taken
        black_counts = Counter(p.upper() for p in self._cap_b)  # black pieces taken

        piece_order = ['Q','R','B','N','P']
        piece_names = {'Q':'Q','R':'R','B':'B','N':'N','P':'P'}

        for row_i, (counts, label, col) in enumerate([
            (white_counts, "W lost", (200,200,220)),
            (black_counts, "B lost", (160,120,80)),
        ]):
            rx = sx + 14
            ry = sy + 22 + row_i * 26
            draw_text(screen, label + ":", cf2, Theme.TEXT_MUTED, rx, ry)
            rx += 42
            if not counts:
                draw_text(screen, "none", cf2, Theme.TEXT_MUTED, rx, ry)
            else:
                for pt in piece_order:
                    n = counts.get(pt, 0)
                    if n:
                        txt = f"{pt}{n}" if n > 1 else pt
                        draw_text(screen, txt, cf, col, rx, ry)
                        rx += cf.size(txt)[0] + 5

        sy += 88

        # Move history
        hist_h = BOARD_Y + BOARD_SZ - sy - 48
        draw_card(screen, (sx, sy, SIDE_W, hist_h))
        draw_text(screen, "MOVES", FontCache.get("Segoe UI",9,bold=True),
                  Theme.TEXT_MUTED, sx+14, sy+8)

        mf        = FontCache.get("Segoe UI",11)
        row_h     = 17
        max_vis   = (hist_h - 26) // row_h
        total_rows = (len(self._history)+1)//2
        # Auto-scroll to bottom
        if total_rows > max_vis:
            self._hist_scroll = total_rows - max_vis

        clip = pygame.Rect(sx+8, sy+22, SIDE_W-16, hist_h-28)
        screen.set_clip(clip)
        for i in range(self._hist_scroll, min(self._hist_scroll+max_vis, total_rows)):
            wy = sy+22 + (i-self._hist_scroll)*row_h
            draw_text(screen, f"{i+1}.", mf, Theme.TEXT_MUTED, sx+14, wy)
            idx = i*2
            if idx   < len(self._history): draw_text(screen,self._history[idx],  mf,Theme.TEXT_PRIMARY,   sx+44, wy)
            if idx+1 < len(self._history): draw_text(screen,self._history[idx+1],mf,Theme.TEXT_SECONDARY, sx+100,wy)
        screen.set_clip(None)
        sy += hist_h + 8

        # Status tag
        tag = {"check":"CHECK","checkmate":"CHECKMATE","stalemate":"STALEMATE"}.get(self._game_status,"")
        if tag:
            draw_text(screen, tag, FontCache.get("Segoe UI",13,bold=True),
                      Theme.ACCENT_RED, sx+SIDE_W//2, sy+14, align="center")

    def _draw_eval_bar(self, screen):
        score = self._eval_visual
        black_pov = (self._pcolor == "black")
        rel  = -score if black_pov else score
        fill = (15,15,15) if black_pov else (235,235,235)
        bg   = (235,235,235) if black_pov else (15,15,15)
        clamped = max(-15, min(15, rel))
        norm = (clamped+15)/30
        bh = BOARD_SZ; fill_h = int((bh-4)*norm)
        mate = self._mate_in
        bc = Theme.ACCENT_ORANGE if mate else Theme.ACCENT_PURPLE
        pygame.draw.rect(screen, bc,  (EVAL_X-2, BOARD_Y-2, 30, bh+4), border_radius=4, width=1)
        pygame.draw.rect(screen, bg,  (EVAL_X,   BOARD_Y,   26, bh),   border_radius=2)
        if fill_h > 0:
            pygame.draw.rect(screen, fill, (EVAL_X, BOARD_Y+bh-fill_h, 26, fill_h), border_radius=2)
        # Numeric label
        ef = FontCache.get("Segoe UI",10,bold=True)
        if mate:
            # M+N = white mates in N, M-N = black mates in N
            sign = '+' if mate > 0 else '-'
            txt = f"M{sign}{abs(mate)}"
        else:
            txt = f"{rel:+.1f}"
        draw_text(screen, txt, ef, Theme.ACCENT_ORANGE if mate else Theme.TEXT_MUTED,
                  EVAL_X+13, BOARD_Y+bh+16, align="center")

    def _draw_promotion(self, screen):
        draw_overlay(screen, 200)
        pw, ph = 400, 240; px, py = (W-pw)//2, (H-ph)//2
        draw_card(screen, (px, py, pw, ph))
        draw_text(screen, "Promote Pawn", FontCache.get("Segoe UI",24,bold=True),
                  Theme.TEXT_PRIMARY, W//2, py+36, align="center")
        choices = ['Q','R','B','N']
        mx2, my2 = pygame.mouse.get_pos()
        for i, pc in enumerate(choices):
            bx = px + 44 + i*80; by = py+84; bs = 68
            if bx <= mx2 <= bx+bs and by <= my2 <= by+bs:
                pygame.draw.rect(screen, Theme.ACCENT_PURPLE, (bx-4,by-4,bs+8,bs+8), border_radius=8)
            pygame.draw.rect(screen, Theme.BG_PRIMARY, (bx,by,bs,bs), border_radius=6)
            _draw_piece(screen, pc, self._promo['white'], bx, by, bs)
            draw_text(screen, {'Q':'Queen','R':'Rook','B':'Bishop','N':'Knight'}[pc],
                      FontCache.get("Segoe UI",10), Theme.TEXT_MUTED, bx+bs//2, by+bs+6, align="center")
        draw_text(screen, "Click to choose",
                  FontCache.get("Segoe UI",12), Theme.TEXT_MUTED, W//2, py+204, align="center")

    def _draw_end(self, screen):
        draw_overlay(screen, 190)
        cw, ch = 440, 220; cx2, cy2 = (W-cw)//2, (H-ch)//2
        draw_card(screen, (cx2, cy2, cw, ch))
        st = self._game_status
        if st == 'checkmate':
            winner = "BLACK" if self._turn else "WHITE"
            title, color = f"{winner} WINS!", Theme.ACCENT_GREEN
        elif st == 'timeout':
            winner = "WHITE" if self._black_ms<=0 else "BLACK"
            title, color = f"{winner} WINS!", Theme.ACCENT_ORANGE
        else:
            title, color = "DRAW!", Theme.ACCENT_YELLOW
        draw_text(screen, title,  FontCache.get("Segoe UI",44,bold=True), color,       W//2, cy2+52,  align="center")
        sub = {"checkmate":"by Checkmate","stalemate":"by Stalemate","timeout":"on Time"}.get(st,"")
        draw_text(screen, sub,   FontCache.get("Segoe UI",18), Theme.TEXT_SECONDARY, W//2, cy2+106, align="center")
        draw_text(screen, "N New Game  |  Q Menu",
                  FontCache.get("Segoe UI",13), Theme.TEXT_MUTED, W//2, cy2+166, align="center")

    # ── Move execution ──────────────────────────────────────────

    def _execute(self, fr, fc, tr, tc, promo='Q'):
        """Apply a confirmed move and advance game state."""
        self._undo_stack.append(self._snapshot())

        # Build SAN before board changes
        p = self._board[fr][fc]
        is_promo = p and p.upper()=='P' and (tr==0 or tr==7)
        san = _san(self._board, fr, fc, tr, tc, promo if is_promo else None)

        nb, cap, special = _apply(self._board, fr, fc, tr, tc, self._ep, promo)

        # Track captures — white piece captured → goes in _cap_w; black → _cap_b
        if cap:
            if _iw(cap):
                self._cap_w.append(cap)
            else:
                self._cap_b.append(cap)

        # Update castling rights
        if p and p.upper()=='K':
            if _iw(p): self._castling['K']=self._castling['Q']=False
            else:      self._castling['k']=self._castling['q']=False
        elif p and p.upper()=='R':
            mp = {(7,7):'K',(7,0):'Q',(0,7):'k',(0,0):'q'}.get((fr,fc))
            if mp: self._castling[mp]=False

        # En passant target
        self._ep = ((fr+tr)//2, fc) if p and p.upper()=='P' and abs(fr-tr)==2 else None

        # Clock increment
        if self._time_on:
            if self._turn: self._white_ms += self._incr_ms
            else:          self._black_ms += self._incr_ms

        self._board     = nb
        self._turn      = not self._turn
        self._last_move = [(fr,fc),(tr,tc)]
        self._selected  = None
        self._legal_sq  = []
        # Clear annotations after each move (like chess.com)
        self._arrows.clear(); self._circles.clear()
        # Recompute eval bar next frame
        self._eval_dirty = True

        # Game status after move
        gs = _status(self._board, self._turn, self._castling, self._ep)
        if gs == 'checkmate': san += '#'
        elif gs == 'check':   san += '+'
        self._history.append(san)
        self._game_status = gs

        if gs in ('checkmate','stalemate'):
            self._finish()
        elif self._mode == 'ai':
            ai_white = (self._pcolor == 'black')
            if self._turn == ai_white:
                self._ai_pending = True

    def _finish(self):
        if self._game_status == 'checkmate':
            winner_white = not self._turn   # last mover won
            p1_won = (winner_white and self._pcolor=='white') or \
                     (not winner_white and self._pcolor=='black') if self._mode=='ai' \
                     else winner_white
        else:
            p1_won = False

        if self.stats:
            self.stats.record_game(self.GAME_ID, score=1 if p1_won else 0,
                won=p1_won, duration=self._session_t,
                extra={"moves": len(self._history)})
        if self.achievements:
            self.achievements.check_and_unlock({
                "game_id": self.GAME_ID, "won": p1_won,
                "moves_played": len(self._history),
                "total_games_played": self.stats.global_summary()["total_games"] if self.stats else 1,
                "total_wins": self.stats.global_summary()["total_wins"] if self.stats else int(p1_won),
            })

    # ── Input ───────────────────────────────────────────────────

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            self._key(event)
        elif self._phase == "game":
            self._mouse(event)

    def _key(self, event):
        k = event.key
        ctrl = bool(pygame.key.get_mods() & pygame.KMOD_CTRL)

        # Escape / Q — in game: clear annotations first, then exit on second press
        if k in (pygame.K_q, pygame.K_ESCAPE):
            if self._phase == "game":
                if (self._arrows or self._circles) and k == pygame.K_ESCAPE:
                    self._arrows.clear(); self._circles.clear()
                else:
                    self.engine.pop_scene()
            elif self._phase == "mode":
                self.engine.pop_scene()
            else:
                self._phase = "mode"; self._sel = 0
            return

        if self._phase == "mode":
            n=2
            if k==pygame.K_UP:    self._sel=(self._sel-1)%n
            if k==pygame.K_DOWN:  self._sel=(self._sel+1)%n
            if k==pygame.K_RETURN:
                self._mode = "human" if self._sel==0 else "ai"
                self._phase = "timer" if self._mode=="human" else "color"
                self._sel=0
        elif self._phase == "color":
            n=2
            if k==pygame.K_UP:    self._sel=(self._sel-1)%n
            if k==pygame.K_DOWN:  self._sel=(self._sel+1)%n
            if k==pygame.K_RETURN:
                self._pcolor = "white" if self._sel==0 else "black"
                self._phase="difficulty"; self._sel=1
        elif self._phase == "difficulty":
            n=3
            if k==pygame.K_UP:    self._sel=(self._sel-1)%n
            if k==pygame.K_DOWN:  self._sel=(self._sel+1)%n
            if k==pygame.K_RETURN:
                self._diff=["easy","medium","hard"][self._sel]
                self._phase="timer"; self._sel=0
        elif self._phase == "timer":
            n=len(TIMER_PRESETS)
            if k==pygame.K_UP:    self._sel=(self._sel-1)%n
            if k==pygame.K_DOWN:  self._sel=(self._sel+1)%n
            if k==pygame.K_RETURN:
                self._timer_i=self._sel
                self._init_game()
                self._phase="game"
                if self._mode=='ai' and self._pcolor=='black':
                    self._ai_pending=True
        elif self._phase == "game":
            if k==pygame.K_n:
                self._phase="mode"; self._sel=0; self._init_game()
            elif k==pygame.K_z and ctrl:
                # Undo 1 ply (PvP) or 2 plies (vs AI) to return to human's turn
                steps = 2 if self._mode=='ai' and len(self._undo_stack)>=2 else 1
                for _ in range(steps):
                    if self._undo_stack:
                        self._restore(self._undo_stack.pop())
            elif k==pygame.K_s and ctrl:
                _save_game(self)
                self._save_msg = ("Game saved!", 2.0)
            elif k==pygame.K_l and ctrl:
                if _load_game(self):
                    self._save_msg = ("Game loaded!", 2.0)
                else:
                    self._save_msg = ("No save found.", 2.0)
            elif k in (pygame.K_c, pygame.K_DELETE):
                # Clear all annotations
                self._arrows.clear(); self._circles.clear()

    def _mouse(self, event):
        # Promotion overlay intercepts all clicks
        if self._promo:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button==1:
                choices=['Q','R','B','N']
                pw,ph=400,240; px,py=(W-pw)//2,(H-ph)//2
                mx,my=event.pos
                for i,pc in enumerate(choices):
                    bx=px+44+i*80; by=py+84; bs=68
                    if bx<=mx<=bx+bs and by<=my<=by+bs:
                        pp=self._promo; self._promo=None
                        self._execute(pp['from'][0],pp['from'][1],pp['to'][0],pp['to'][1],pc)
                        break
            return

        if self._game_status not in ('ongoing','check'): return

        flip = (self._mode=='ai' and self._pcolor=='black')

        def to_board_sq(mx, my):
            if not (BOARD_X<=mx<BOARD_X+BOARD_SZ and BOARD_Y<=my<BOARD_Y+BOARD_SZ):
                return None
            sc=(mx-BOARD_X)//SQ; sr=(my-BOARD_Y)//SQ
            return (7-sr, 7-sc) if flip else (sr, sc)

        def is_my_piece(br, bc):
            """Can the human player interact with this square?"""
            p = self._board[br][bc]
            if not p: return False
            if self._mode=='human': return _iw(p)==self._turn
            return (_iw(p) and self._pcolor=='white' and self._turn) or \
                   (_ib(p) and self._pcolor=='black' and not self._turn)

        if event.type == pygame.MOUSEBUTTONDOWN and event.button==1:
            pos = to_board_sq(*event.pos)
            if pos is None: return
            br, bc = pos
            if is_my_piece(br, bc):
                if self._selected==(br,bc):
                    self._selected=None; self._legal_sq=[]
                else:
                    self._selected=(br,bc)
                    self._legal_sq=_legal(self._board,br,bc,self._castling,self._ep)
                    self._dragging=(br,bc,*event.pos)
            elif (br,bc) in self._legal_sq and self._selected:
                fr,fc=self._selected; p=self._board[fr][fc]
                if p and p.upper()=='P' and (br==0 or br==7):
                    self._promo={'from':(fr,fc),'to':(br,bc),'white':_iw(p)}
                    self._selected=None; self._legal_sq=[]
                else:
                    self._execute(fr,fc,br,bc)
                self._dragging=None
            else:
                self._selected=None; self._legal_sq=[]

        elif event.type==pygame.MOUSEMOTION and self._dragging:
            dr,dc,_,_=self._dragging
            self._dragging=(dr,dc,*event.pos)

        elif event.type==pygame.MOUSEBUTTONUP and event.button==1:
            if self._dragging:
                dr,dc,_,_=self._dragging; self._dragging=None
                pos=to_board_sq(*event.pos)
                if pos and pos in self._legal_sq:
                    br,bc=pos; p=self._board[dr][dc]
                    if p and p.upper()=='P' and (br==0 or br==7):
                        self._promo={'from':(dr,dc),'to':(br,bc),'white':_iw(p)}
                        self._selected=None; self._legal_sq=[]
                    else:
                        self._execute(dr,dc,br,bc)
                else:
                    # Dropped off-board or invalid - keep selection visible
                    pass

        # ── Right-click annotation ──────────────────────────────
        elif event.type==pygame.MOUSEBUTTONDOWN and event.button==3:
            pos=to_board_sq(*event.pos)
            if pos:
                mods = pygame.key.get_mods()
                if mods & pygame.KMOD_SHIFT:
                    self._rclick_color = (50, 200, 50)    # green
                elif mods & pygame.KMOD_CTRL:
                    self._rclick_color = (50, 100, 255)   # blue
                else:
                    self._rclick_color = (255, 80, 80)    # red
                self._rclick_start = pos

        elif event.type==pygame.MOUSEBUTTONUP and event.button==3:
            if self._rclick_start:
                end = to_board_sq(*event.pos)
                start = self._rclick_start; self._rclick_start = None
                if end:
                    col = self._rclick_color
                    if start == end:
                        # Toggle circle on the square
                        if any(c[0]==start for c in self._circles):
                            self._circles = [c for c in self._circles if c[0]!=start]
                        else:
                            self._circles.append((start, col))
                    else:
                        # Toggle arrow
                        if any(a[0]==start and a[1]==end for a in self._arrows):
                            self._arrows = [a for a in self._arrows if not(a[0]==start and a[1]==end)]
                        else:
                            self._arrows.append((start, end, col))


# ─────────────────────────────────────────────────────────────
# Plugin metadata
# ─────────────────────────────────────────────────────────────

GAME_META = {
    "id":          "chess",
    "name":        "Chess",
    "desc":        "Full chess with AI opponent",
    "color":       lambda: Theme.TEXT_SECONDARY,
    "scene_class": ChessScene,
}
