"""
AEGIS — Calculator Tool
Safe math expression evaluator for both modes.
"""

import re
import math


# Allowed names in the eval sandbox
SAFE_NAMES = {
    "abs": abs,
    "round": round,
    "min": min,
    "max": max,
    "sum": sum,
    "pow": pow,
    "int": int,
    "float": float,
    # math module functions
    "sqrt": math.sqrt,
    "log": math.log,
    "log10": math.log10,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "pi": math.pi,
    "e": math.e,
    "ceil": math.ceil,
    "floor": math.floor,
    "factorial": math.factorial,
}

# Regex to detect calculator-type queries
CALC_PATTERN = re.compile(
    r"^[\d\s\+\-\*/\.\(\)%\^]+$"  # pure math expression
    r"|"
    r"(?:calculate|compute|what is|solve|evaluate)\s+[\d\+\-\*/\.\(\)%\^ ]+",
    re.IGNORECASE,
)


def is_calc_query(query: str) -> bool:
    """Detect if a query is a math calculation."""
    return bool(CALC_PATTERN.search(query.strip()))


def extract_expression(query: str) -> str:
    """Extract the math expression from a natural-language query."""
    # Remove common prefixes
    cleaned = re.sub(
        r"^(calculate|compute|what is|solve|evaluate)\s+",
        "",
        query.strip(),
        flags=re.IGNORECASE,
    )
    # Replace ^ with ** for Python exponentiation
    cleaned = cleaned.replace("^", "**")
    return cleaned.strip()


def evaluate(expression: str) -> str:
    """Safely evaluate a math expression and return the result as a string."""
    expr = extract_expression(expression)
    try:
        # Evaluate in a restricted namespace (no builtins)
        result = eval(expr, {"__builtins__": {}}, SAFE_NAMES)  # noqa: S307
        return f"🔢 **Result:** `{expr}` = **{result}**"
    except ZeroDivisionError:
        return "❌ Error: Division by zero."
    except SyntaxError:
        return f"❌ Error: Invalid expression `{expr}`."
    except Exception as e:
        return f"❌ Error: {e}"
