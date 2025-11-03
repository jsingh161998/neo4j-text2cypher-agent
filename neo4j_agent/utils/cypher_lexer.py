"""Custom Pygments lexer for Neo4j Cypher query language."""

import re

from pygments.lexer import RegexLexer, bygroups, words
from pygments.token import (
    Comment,
    Keyword,
    Name,
    Number,
    Operator,
    Punctuation,
    String,
    Text,
)


class CypherLexer(RegexLexer):
    """Custom Pygments lexer for Neo4j Cypher with proper token distinction."""

    name = "Cypher"
    aliases = ["cypher"]
    filenames = ["*.cypher", "*.cyp"]
    flags = re.IGNORECASE

    # Cypher keywords (comprehensive list)
    KEYWORDS = (
        "MATCH",
        "WHERE",
        "RETURN",
        "WITH",
        "CREATE",
        "MERGE",
        "DELETE",
        "DETACH",
        "SET",
        "REMOVE",
        "ORDER",
        "BY",
        "ASC",
        "DESC",
        "LIMIT",
        "SKIP",
        "OPTIONAL",
        "CALL",
        "YIELD",
        "UNION",
        "ALL",
        "AS",
        "DISTINCT",
        "CASE",
        "WHEN",
        "THEN",
        "ELSE",
        "END",
        "UNWIND",
        "FOREACH",
        "ON",
        "USING",
        "INDEX",
        "CONSTRAINT",
        "DROP",
        "CONTAINS",
        "STARTS",
        "ENDS",
        "IN",
        "IS",
        "NOT",
        "AND",
        "OR",
        "XOR",
        "true",
        "false",
        "null",
    )

    # Cypher functions (comprehensive list from Neo4j docs)
    FUNCTIONS = (
        # Aggregating functions
        "count",
        "sum",
        "avg",
        "min",
        "max",
        "collect",
        "stDev",
        "stDevP",
        "percentileCont",
        "percentileDisc",
        # List functions
        "keys",
        "labels",
        "nodes",
        "relationships",
        "range",
        "reduce",
        "size",
        "head",
        "last",
        "tail",
        "reverse",
        # String functions
        "toString",
        "toStringOrNull",
        "toInteger",
        "toIntegerOrNull",
        "toFloat",
        "toFloatOrNull",
        "toBoolean",
        "toBooleanOrNull",
        "replace",
        "substring",
        "left",
        "right",
        "trim",
        "ltrim",
        "rtrim",
        "toLower",
        "toUpper",
        "split",
        # Scalar functions
        "id",
        "elementId",
        "type",
        "length",
        "size",
        "properties",
        "coalesce",
        "timestamp",
        "exists",
        # Mathematical functions
        "abs",
        "ceil",
        "floor",
        "round",
        "sign",
        "rand",
        "sqrt",
        "log",
        "log10",
        "exp",
        "sin",
        "cos",
        "tan",
        "asin",
        "acos",
        "atan",
        "atan2",
        "pi",
        "radians",
        "degrees",
        # Temporal functions
        "date",
        "datetime",
        "time",
        "localtime",
        "localdatetime",
        "duration",
        # Spatial functions
        "point",
        "distance",
        # Predicate functions
        "all",
        "any",
        "none",
        "single",
        "isEmpty",
    )

    # Build case-insensitive function regex pattern
    functions_pattern = r"\b(" + "|".join(FUNCTIONS) + r")\b(?=\()"

    tokens = {
        "root": [
            # Comments
            (r"//.*$", Comment.Single),
            (r"/\*", Comment.Multiline, "multiline-comment"),
            # Functions (case-insensitive via class flags, must come before keywords)
            (functions_pattern, Name.Builtin),
            # Keywords (case insensitive via class flags)
            (words(KEYWORDS, prefix=r"\b", suffix=r"\b"), Keyword),
            # Relationship types inside brackets [:TYPE] - break into parts
            # Match [, :, TYPE, ] separately so brackets are punctuation
            (r"\[", Punctuation),  # Opening bracket
            (r"\]", Punctuation),  # Closing bracket
            # Labels and relationship type names - colon is keyword, name gets color
            (r"(:)(\w+)", bygroups(Keyword, Name.Class)),
            # Strings
            (r"'([^'\\]|\\.)*'", String.Single),
            (r'"([^"\\]|\\.)*"', String.Double),
            (r"`([^`\\]|\\.)*`", String.Backtick),
            # Numbers
            (r"\d+\.\d+", Number.Float),
            (r"\d+", Number.Integer),
            # Relationship arrows and operators (white)
            (r"<-\[|\]->|<-|->", Punctuation),
            (r"(<>|<=|>=|=~|<|>|=)", Operator),
            # Property access: variable.property (dot is keyword, property is Name.Attribute)
            (r"(\w+)(\.)(\w+)", bygroups(Name.Variable, Keyword, Name.Attribute)),
            # Property in object literal: property: value (property is Name.Attribute, colon is keyword)
            (r"(\w+)(:)(?=\s)", bygroups(Name.Attribute, Keyword)),
            # Standalone dot - treated as keyword (same color as clauses)
            (r"\.", Keyword),
            # Punctuation (parentheses, braces, comma, semicolon)
            (r"[(){},;]", Punctuation),
            # Variables (identifiers - neutral color)
            (r"\b[a-zA-Z_]\w*\b", Name.Variable),
            # Whitespace
            (r"\s+", Text),
        ],
        "multiline-comment": [
            (r"[^*/]+", Comment.Multiline),
            (r"\*/", Comment.Multiline, "#pop"),
            (r"[*/]", Comment.Multiline),
        ],
    }
