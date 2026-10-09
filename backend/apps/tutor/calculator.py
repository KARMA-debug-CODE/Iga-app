"""The calculator Santa's model can call (the "calculate" tool), so the arithmetic in its answers is right.

Only numbers, + - * / ** %, parentheses, a few maths functions and constants are allowed. The expression is
parsed with Python's ast module and walked node by node; nothing ever reaches eval or exec, and sizes are
limited so no expression can use much time or memory. Whole numbers, fractions and decimals are worked out
exactly (1/3 + 1/6 = 1/2, 0.1 + 0.2 = 0.3); square roots, powers with fractions and trigonometry use
floating point and are rounded to 12 significant figures.
"""

import ast
import math
from fractions import Fraction

MAX_LENGTH = 200
MAX_NODES = 100
MAX_BITS = 700  # about 210 digits for an exact result
MAX_EXPONENT = 1000
MAX_FACTORIAL = 100

TOOL = {
    "type": "function",
    "function": {
        "name": "calculate",
        "description": (
            "Work out an arithmetic expression exactly. Use it for every calculation instead of doing it in your head. "
            "Supports + - * / ** (power) % (remainder), parentheses, sqrt, sin, cos, tan (radians; use radians(30) for "
            "degrees), asin, acos, atan, log (natural, or log(x, base)), log10, exp, abs, round, floor, ceil, factorial, "
            "gcd, lcm, pi and e."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "expression": {"type": "string", "description": "For example (3/4 + 2/5) * 12 or sqrt(2) * 5"},
            },
            "required": ["expression"],
        },
    },
}


class CalcError(ValueError):
    """The expression isn't allowed or has no answer (the message says why, in plain words)."""


CONSTANTS = {"pi": math.pi, "e": math.e, "tau": math.tau}


def _real(x):
    return float(x)


def _integer(x, name):
    if isinstance(x, Fraction) and x.denominator == 1:
        return x.numerator
    if isinstance(x, float) and x.is_integer():
        return int(x)
    raise CalcError(f"{name} needs whole numbers")


def _sqrt(x):
    if x < 0:
        raise CalcError("the square root of a negative number is not a real number")
    if isinstance(x, Fraction):
        top, bottom = math.isqrt(x.numerator), math.isqrt(x.denominator)
        if top * top == x.numerator and bottom * bottom == x.denominator:
            return Fraction(top, bottom)
    return math.sqrt(x)


def _log(x, base=None):
    if x <= 0 or (base is not None and (base <= 0 or base == 1)):
        raise CalcError("log needs a positive number (and a positive base other than 1)")
    return math.log(x) if base is None else math.log(x, base)


def _factorial(x):
    n = _integer(x, "factorial")
    if not 0 <= n <= MAX_FACTORIAL:
        raise CalcError(f"factorial works from 0 to {MAX_FACTORIAL}")
    return Fraction(math.factorial(n))


def _round(x, digits=None):
    if digits is None:
        return Fraction(round(x))
    places = _integer(digits, "round")
    if not -20 <= places <= 20:
        raise CalcError("round to at most 20 decimal places")
    return round(x, places) if isinstance(x, Fraction) else round(x, places)


def _whole(fn, name):
    return lambda *args: Fraction(fn(*(_integer(a, name) for a in args)))


def _inverse_trig(fn):
    def call(x):
        if fn in (math.asin, math.acos) and not -1 <= x <= 1:
            raise CalcError("asin and acos need a number between -1 and 1")
        return fn(_real(x))

    return call


# name -> (function, how many arguments it takes)
FUNCTIONS = {
    "sqrt": (_sqrt, (1,)),
    "sin": (lambda x: math.sin(_real(x)), (1,)),
    "cos": (lambda x: math.cos(_real(x)), (1,)),
    "tan": (lambda x: math.tan(_real(x)), (1,)),
    "asin": (_inverse_trig(math.asin), (1,)),
    "acos": (_inverse_trig(math.acos), (1,)),
    "atan": (_inverse_trig(math.atan), (1,)),
    "radians": (lambda x: math.radians(_real(x)), (1,)),
    "degrees": (lambda x: math.degrees(_real(x)), (1,)),
    "log": (_log, (1, 2)),
    "ln": (_log, (1,)),
    "log10": (lambda x: _log(x, 10), (1,)),
    "log2": (lambda x: _log(x, 2), (1,)),
    "exp": (lambda x: math.exp(_real(x)), (1,)),
    "abs": (abs, (1,)),
    "round": (_round, (1, 2)),
    "floor": (lambda x: Fraction(math.floor(x)), (1,)),
    "ceil": (lambda x: Fraction(math.ceil(x)), (1,)),
    "factorial": (_factorial, (1,)),
    "gcd": (_whole(math.gcd, "gcd"), (2,)),
    "lcm": (_whole(math.lcm, "lcm"), (2,)),
    "hypot": (lambda x, y: math.hypot(_real(x), _real(y)), (2,)),
}


def _check(value):
    """Keep results small enough to work with, and real."""
    if isinstance(value, Fraction):
        if max(value.numerator.bit_length(), value.denominator.bit_length()) > MAX_BITS:
            raise CalcError("the numbers get too large")
        return value
    if isinstance(value, complex) or math.isnan(value):
        raise CalcError("the answer is not a real number")
    if math.isinf(value):
        raise CalcError("the numbers get too large")
    return value


def _number(node):
    value = node.value
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise CalcError("only numbers are allowed")
    if isinstance(value, int):
        return _check(Fraction(value))
    text = repr(value)
    # A decimal like 0.1 is exactly one tenth; very large or small numbers stay in floating point.
    return Fraction(text) if "e" not in text and "inf" not in text and "nan" not in text else _check(value)


def _power(base, exponent):
    if isinstance(exponent, Fraction) and exponent.denominator == 1:
        n = exponent.numerator
        if abs(n) > MAX_EXPONENT:
            raise CalcError(f"powers go up to {MAX_EXPONENT}")
        if isinstance(base, Fraction):
            if base == 0 and n < 0:
                raise CalcError("you can't divide by zero")
            size = max(base.numerator.bit_length(), base.denominator.bit_length()) * abs(n)
            if size <= MAX_BITS:
                return base**n
        try:
            return math.pow(_real(base), n)
        except OverflowError as exc:
            raise CalcError("the numbers get too large") from exc
    if base < 0:
        raise CalcError("a negative number to a fractional power is not a real number")
    if base == 0 and exponent < 0:
        raise CalcError("you can't divide by zero")
    try:
        result = math.pow(_real(base), _real(exponent))
    except OverflowError as exc:
        raise CalcError("the numbers get too large") from exc
    # 16 ** 0.5 is exactly 4: keep exact answers exact when they check out.
    if isinstance(base, Fraction) and isinstance(exponent, Fraction) and result.is_integer() and abs(result) < 2**53:
        whole = int(result)
        if exponent.denominator <= 64 and Fraction(whole) ** exponent.denominator == base**exponent.numerator:
            return Fraction(whole)
    return result


def _binary(op, a, b):
    exact = isinstance(a, Fraction) and isinstance(b, Fraction)
    if isinstance(op, ast.Add):
        return a + b if exact else _real(a) + _real(b)
    if isinstance(op, ast.Sub):
        return a - b if exact else _real(a) - _real(b)
    if isinstance(op, ast.Mult):
        return a * b if exact else _real(a) * _real(b)
    if isinstance(op, (ast.Div, ast.Mod)):
        if b == 0:
            raise CalcError("you can't divide by zero")
        if isinstance(op, ast.Div):
            return a / b if exact else _real(a) / _real(b)
        return a % b if exact else _real(a) % _real(b)
    if isinstance(op, ast.Pow):
        return _power(a, b)
    raise CalcError("only + - * / ** and % are allowed")


def _eval(node):
    if isinstance(node, ast.Expression):
        return _eval(node.body)
    if isinstance(node, ast.Constant):
        return _number(node)
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
        value = _eval(node.operand)
        return -value if isinstance(node.op, ast.USub) else value
    if isinstance(node, ast.BinOp):
        return _check(_binary(node.op, _eval(node.left), _eval(node.right)))
    if isinstance(node, ast.Name):
        if node.id in CONSTANTS:
            return CONSTANTS[node.id]
        raise CalcError(f"unknown name: {node.id}")
    if isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name) or node.func.id not in FUNCTIONS or node.keywords:
            raise CalcError("unknown function")
        function, counts = FUNCTIONS[node.func.id]
        if len(node.args) not in counts:
            raise CalcError(f"{node.func.id} takes {' or '.join(map(str, counts))} number(s)")
        try:
            return _check(function(*(_eval(arg) for arg in node.args)))
        except (OverflowError, ZeroDivisionError) as exc:
            raise CalcError("the numbers get too large") from exc
    raise CalcError("only numbers, + - * / ** %, brackets and maths functions are allowed")


def evaluate(expression):
    """The value of `expression` (a Fraction when exact, otherwise a float). Raises CalcError."""
    if not isinstance(expression, str) or not expression.strip():
        raise CalcError("write an expression, for example 3 * (4 + 5)")
    if len(expression) > MAX_LENGTH:
        raise CalcError(f"keep the expression under {MAX_LENGTH} characters")
    # Students and models write maths in many ways: 2^3, 3 × 4, 8 ÷ 2, 5 − 1.
    text = expression.replace("^", "**").replace("×", "*").replace("·", "*").replace("÷", "/").replace("−", "-")
    try:
        tree = ast.parse(text.strip(), mode="eval")
    except (SyntaxError, ValueError, RecursionError, MemoryError) as exc:
        raise CalcError("this is not a calculation I can read") from exc
    if sum(1 for _ in ast.walk(tree)) > MAX_NODES:
        raise CalcError("the expression is too long")
    try:
        return _eval(tree)
    except RecursionError as exc:
        raise CalcError("the expression is too long") from exc
    except (OverflowError, MemoryError) as exc:
        raise CalcError("the numbers get too large") from exc
    except (TypeError, ZeroDivisionError) as exc:
        raise CalcError("this is not a calculation I can do") from exc


def _decimal(value):
    text = f"{value:.12g}"
    return text.replace("e+", "e") if "e" in text else text


def format_value(value):
    """How a result is shown: 84, 0.3, 11/12 (≈ 0.916666666667) or 1.41421356237."""
    if isinstance(value, Fraction):
        if value.denominator == 1:
            return str(value.numerator)
        # A fraction whose bottom has only 2s and 5s is an exact decimal: 3/8 is 0.375.
        rest, twos, fives = value.denominator, 0, 0
        while rest % 2 == 0:
            rest, twos = rest // 2, twos + 1
        while rest % 5 == 0:
            rest, fives = rest // 5, fives + 1
        places = max(twos, fives)
        if rest == 1 and places <= 20:
            digits = str(abs(value.numerator * 10**places // value.denominator)).rjust(places + 1, "0")
            return f"{'-' if value < 0 else ''}{digits[:-places]}.{digits[-places:]}"
        return f"{value.numerator}/{value.denominator} (≈ {_decimal(float(value))})"
    return _decimal(value)


def calculate(expression):
    """The tool's answer for the model: the result, or a short reason it couldn't be worked out."""
    try:
        return format_value(evaluate(expression))
    except CalcError as exc:
        return f"error: {exc}"
