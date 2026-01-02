import ast
import pandas as pd
import operators as ops


class AlphaExpressionParser(ast.NodeVisitor):
    def __init__(self, variables):
        """
        variables: dict[str, pd.Series]
        Example: {"close": close, "volume": volume}
        """
        self.variables = variables

        self.allowed_funcs = {
            "xAbs": ops.xAbs,
            "xLog": ops.xLog,
            "Add": ops.Add,
            "Sub": ops.Sub,
            "Mul": ops.Mul,
            "Div": ops.Div,
            "Greater": ops.Greater,
            "Less": ops.Less,
            "Ref": ops.Ref,
            "Mean": ops.Mean,
            "Med": ops.Med,
            "Sum": ops.Sum,
            "Std": ops.Std,
            "Var": ops.Var,
            "Max": ops.Max,
            "Min": ops.Min,
            "Mad": ops.Mad,
            "Delta": ops.Delta,
            "WMA": ops.WMA,
            "EMA": ops.EMA,
            "Cov": ops.Cov,
            "Corr": ops.Corr,
        }

    # ---------- Entry ----------
    def parse(self, expr: str) -> pd.Series:
        tree = ast.parse(expr, mode="eval")
        return self.visit(tree.body)

    # ---------- AST Nodes ----------
    def visit_Call(self, node):
        func_name = node.func.id

        if func_name not in self.allowed_funcs:
            raise ValueError(f"Function '{func_name}' is not allowed")

        func = self.allowed_funcs[func_name]
        args = [self.visit(arg) for arg in node.args]

        return func(*args)

    def visit_Name(self, node):
        if node.id not in self.variables:
            raise ValueError(f"Unknown variable '{node.id}'")
        return self.variables[node.id]

    def visit_Constant(self, node):
        if isinstance(node.value, (int, float)):
            return node.value
        raise ValueError("Only numeric constants allowed")

    def visit_Num(self, node):  # Python <3.8
        return node.n

    def generic_visit(self, node):
        raise ValueError(f"Unsupported syntax: {type(node).__name__}")
