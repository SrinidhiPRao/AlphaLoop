import ast
import copy
import math
import random
import logging
from dataclasses import dataclass, field
from typing import Optional

import pandas as pd

from parser import AlphaExpressionParser
from backtester import ICBacktester
from generate_alpha import generate_alpha_expression

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Operator metadata
# ---------------------------------------------------------------------------

# Operators that take (series, window) — swappable with each other
TS_UNARY = [
    "Mean",
    "Med",
    "Sum",
    "Std",
    "Var",
    "Max",
    "Min",
    "Mad",
    "Delta",
    "WMA",
    "EMA",
    "Ref",
]

# Operators that take (series, series, window)
TS_BINARY = ["Cov", "Corr"]

# Operators that take one series (no window)
SCALAR_UNARY = ["xAbs", "xLog"]

# Operators that take two series (no window)
SCALAR_BINARY = ["Add", "Sub", "Mul", "Div", "Greater", "Less"]

VARIABLES = ["open", "high", "low", "close", "volume"]

WINDOW_MIN = 1
WINDOW_MAX = 50
WINDOW_STEP = 5  # nudge step for window mutations


# ---------------------------------------------------------------------------
# AST helpers
# ---------------------------------------------------------------------------


def _classify_func(name: str) -> str:
    if name in TS_UNARY:
        return "ts_unary"
    if name in TS_BINARY:
        return "ts_binary"
    if name in SCALAR_UNARY:
        return "scalar_unary"
    if name in SCALAR_BINARY:
        return "scalar_binary"
    return "unknown"


def _collect_nodes(tree: ast.Expression) -> list[ast.AST]:
    """Return all Call and Name nodes in the tree."""
    nodes = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.Call, ast.Name)):
            nodes.append(node)
    return nodes


def _ast_to_str(node: ast.AST) -> str:
    return ast.unparse(node)


# ---------------------------------------------------------------------------
# Mutation functions (operate on a deep-copied AST)
# ---------------------------------------------------------------------------


def mutate_swap_operator(tree: ast.Expression) -> Optional[str]:
    """Replace a time-series operator with another of the same arity."""
    candidates = [
        n
        for n in ast.walk(tree)
        if isinstance(n, ast.Call)
        and isinstance(n.func, ast.Name)
        and _classify_func(n.func.id)
        in ("ts_unary", "ts_binary", "scalar_unary", "scalar_binary")
    ]
    if not candidates:
        return None

    node = random.choice(candidates)
    kind = _classify_func(node.func.id)

    pool_map = {
        "ts_unary": TS_UNARY,
        "ts_binary": TS_BINARY,
        "scalar_unary": SCALAR_UNARY,
        "scalar_binary": SCALAR_BINARY,
    }
    pool = [op for op in pool_map[kind] if op != node.func.id]
    if not pool:
        return None

    node.func.id = random.choice(pool)
    return _ast_to_str(tree)


def mutate_swap_variable(tree: ast.Expression) -> Optional[str]:
    """Replace a leaf variable with another variable."""
    candidates = [
        n for n in ast.walk(tree) if isinstance(n, ast.Name) and n.id in VARIABLES
    ]
    if not candidates:
        return None

    node = random.choice(candidates)
    pool = [v for v in VARIABLES if v != node.id]
    node.id = random.choice(pool)
    return _ast_to_str(tree)


def mutate_window(tree: ast.Expression) -> Optional[str]:
    """Nudge an integer window constant by ±WINDOW_STEP."""
    candidates = [
        n
        for n in ast.walk(tree)
        if isinstance(n, ast.Constant) and isinstance(n.value, int)
    ]
    if not candidates:
        return None

    node = random.choice(candidates)
    delta = random.choice([-WINDOW_STEP, WINDOW_STEP])
    new_val = max(WINDOW_MIN, min(WINDOW_MAX, node.value + delta))
    node.value = new_val
    return _ast_to_str(tree)


def mutate_wrap_subexpr(tree: ast.Expression) -> Optional[str]:
    """Wrap a leaf variable in a ts_unary operator."""
    candidates = [
        n for n in ast.walk(tree) if isinstance(n, ast.Name) and n.id in VARIABLES
    ]
    if not candidates:
        return None

    # Pick a random variable node — but we need its *parent* to replace it.
    # Strategy: rebuild by unparsing, replace one occurrence.
    target = random.choice(candidates)
    op = random.choice(TS_UNARY)
    window = (
        random.randint(WINDOW_MIN // WINDOW_STEP, WINDOW_MAX // WINDOW_STEP)
        * WINDOW_STEP
    )
    window = max(WINDOW_MIN, window)

    original_var = target.id
    new_expr_fragment = f"{op}({original_var}, {window})"

    # Replace first occurrence of the bare variable name in the unparsed string
    expr_str = _ast_to_str(tree)

    # Find positions where `original_var` appears as a standalone name
    import re

    pattern = rf"\b{original_var}\b"
    matches = list(re.finditer(pattern, expr_str))
    if not matches:
        return None

    match = random.choice(matches)
    new_str = expr_str[: match.start()] + new_expr_fragment + expr_str[match.end() :]
    return new_str


MUTATIONS = [
    mutate_swap_operator,
    mutate_swap_variable,
    mutate_window,
    mutate_wrap_subexpr,
]


# ---------------------------------------------------------------------------
# Expression evaluation
# ---------------------------------------------------------------------------


def evaluate_expr(
    expr: str, variables: dict, backtester: ICBacktester
) -> Optional[float]:
    """Parse expression, compute IC mean. Returns None if invalid."""
    try:
        parser = AlphaExpressionParser(variables)
        alpha = parser.parse(expr)
        ic = backtester.compute_ic(alpha)
        if ic.empty or ic.isna().all():
            return None
        return float(ic.mean())
    except Exception as e:
        logger.debug(f"Invalid expression '{expr}': {e}")
        return None


def apply_mutation(expr: str) -> Optional[str]:
    """Apply a random mutation to the expression string. Returns None if unparseable."""
    try:
        tree = ast.parse(expr, mode="eval")
        tree_copy = copy.deepcopy(tree)
        mutation_fn = random.choice(MUTATIONS)
        return mutation_fn(tree_copy)
    except Exception as e:
        logger.debug(f"Mutation failed on '{expr}': {e}")
        return None


# ---------------------------------------------------------------------------
# RL Episode
# ---------------------------------------------------------------------------


@dataclass
class EpisodeResult:
    seed_expr: str
    seed_ic: Optional[float]
    best_expr: str
    best_ic: float
    history: list[tuple[str, float]] = field(default_factory=list)
    n_iterations: int = 0
    n_accepted: int = 0
    n_invalid: int = 0


def run_episode(
    seed_expr: str,
    variables: dict,
    backtester: ICBacktester,
    n_iterations: int = 100,
    use_annealing: bool = True,
    temp_start: float = 0.02,
    temp_end: float = 0.001,
) -> EpisodeResult:
    """
    Run one RL episode of local search starting from seed_expr.

    Acceptance policy:
      - Always accept improvements (IC increases)
      - With simulated annealing: accept worse solutions with probability
        exp(delta_ic / temperature), temperature decays linearly
      - Without annealing: pure hill climbing
    """
    seed_ic = evaluate_expr(seed_expr, variables, backtester)

    if seed_ic is None:
        logger.warning(f"Seed expression failed evaluation: {seed_expr}")
        # Still attempt search — seed might produce valid mutations
        seed_ic = -999.0

    current_expr = seed_expr
    current_ic = seed_ic if seed_ic != -999.0 else float("-inf")
    best_expr = current_expr
    best_ic = current_ic

    history = [(current_expr, current_ic)]
    n_accepted = 0
    n_invalid = 0

    for i in range(n_iterations):
        # Temperature schedule (linear decay)
        if use_annealing:
            t = temp_start + (temp_end - temp_start) * (i / n_iterations)
        else:
            t = 0.0

        candidate = apply_mutation(current_expr)
        if candidate is None:
            n_invalid += 1
            continue

        candidate_ic = evaluate_expr(candidate, variables, backtester)
        if candidate_ic is None:
            n_invalid += 1
            continue

        delta = candidate_ic - current_ic

        # Accept decision
        if delta > 0:
            accept = True
        elif use_annealing and t > 0:
            accept = random.random() < math.exp(delta / t)
        else:
            accept = False

        if accept:
            current_expr = candidate
            current_ic = candidate_ic
            n_accepted += 1
            history.append((current_expr, current_ic))

            if current_ic > best_ic:
                best_ic = current_ic
                best_expr = current_expr

    return EpisodeResult(
        seed_expr=seed_expr,
        seed_ic=seed_ic if seed_ic != -999.0 else None,
        best_expr=best_expr,
        best_ic=best_ic,
        history=history,
        n_iterations=n_iterations,
        n_accepted=n_accepted,
        n_invalid=n_invalid,
    )


# ---------------------------------------------------------------------------
# Full RL Loop
# ---------------------------------------------------------------------------


@dataclass
class RLResult:
    all_episodes: list[EpisodeResult]
    leaderboard: list[tuple[str, float]]  # sorted by IC desc


def run_rl_loop(
    variables: dict,
    backtester: ICBacktester,
    n_episodes: int = 5,
    n_iterations_per_episode: int = 100,
    use_annealing: bool = True,
    top_k: int = 10,
    seed_exprs: Optional[list[str]] = None,
) -> RLResult:
    """
    Full RL loop:
      1. Generate seed expressions (LLM or provided)
      2. Run local search episode from each seed
      3. Return leaderboard of best expressions by IC

    Args:
        variables:               dict of pd.Series (open, high, low, close, volume)
        backtester:              ICBacktester instance
        n_episodes:              number of LLM seeds / episodes to run
        n_iterations_per_episode: mutations per episode
        use_annealing:           whether to use simulated annealing
        top_k:                   how many results to return in leaderboard
        seed_exprs:              optional list of seed expressions (skips LLM calls)
    """
    all_episodes = []
    seen_exprs = set()

    for ep in range(n_episodes):
        print(f"\n{'='*60}")
        print(f"Episode {ep + 1}/{n_episodes}")
        print(f"{'='*60}")

        # --- Seed generation ---
        if seed_exprs and ep < len(seed_exprs):
            seed = seed_exprs[ep]
            print(f"Using provided seed: {seed}")
        else:
            print("Generating seed from LLM...")
            seed = generate_alpha_expression()
            print(f"LLM seed: {seed}")

        # --- Run episode ---
        result = run_episode(
            seed_expr=seed,
            variables=variables,
            backtester=backtester,
            n_iterations=n_iterations_per_episode,
            use_annealing=use_annealing,
        )

        print(
            f"Seed IC:  {result.seed_ic:.4f}"
            if result.seed_ic is not None
            else "Seed IC:  invalid"
        )
        print(f"Best IC:  {result.best_ic:.4f}")
        print(f"Best expr: {result.best_expr}")
        print(
            f"Accepted {result.n_accepted}/{result.n_iterations} mutations "
            f"({result.n_invalid} invalid)"
        )

        all_episodes.append(result)
        seen_exprs.add(result.best_expr)

    # --- Build leaderboard ---
    all_candidates = []
    for ep in all_episodes:
        for expr, ic in ep.history:
            if expr not in {e for e, _ in all_candidates}:
                all_candidates.append((expr, ic))

    leaderboard = sorted(all_candidates, key=lambda x: x[1], reverse=True)[:top_k]

    print(f"\n{'='*60}")
    print(f"LEADERBOARD (Top {top_k})")
    print(f"{'='*60}")
    for rank, (expr, ic) in enumerate(leaderboard, 1):
        print(f"{rank:>3}. IC={ic:.4f}  {expr}")

    return RLResult(all_episodes=all_episodes, leaderboard=leaderboard)
