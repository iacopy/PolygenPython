"""
Polygen - Python implementation of the Polygen random text generator.

This module implements the core features of PML (Polygen Meta Language):
- Terminal and non-terminal symbols
- Productions with pipe-separated alternatives
- Subproductions (round brackets)
- Optional subproductions (square brackets) - 50% probability
- Concatenation (^) to suppress spaces
- Epsilon (_) for empty production
- Probability modifiers (+ and -)
- Labels and selection (.label)
- Capitalization (backslash)
- Comments (* ... *)
- Weak binding (::=) and strong binding (:=)
- Iteration (+)
- Emitted labels (#tag) - v2
- Include directive (@include) - v2
"""

import re
import os
import random
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Tuple, Set
from enum import Enum, auto


# =============================================================================
# LEXER
# =============================================================================

class TokenType(Enum):
    # Literals
    TERM = auto()           # lowercase word or quoted string
    NONTERM = auto()        # Capitalized identifier
    LABEL = auto()          # label identifier (after colon or dot)
    TAG = auto()            # #tag (emitted label)

    # Operators
    DEFINE = auto()         # ::=
    ASSIGN = auto()         # :=
    PIPE = auto()           # |
    SEMI = auto()           # ;
    COLON = auto()          # :
    COMMA = auto()          # ,
    DOT = auto()            # .
    CARET = auto()          # ^
    UNDERSCORE = auto()     # _
    BACKSLASH = auto()      # \
    PLUS = auto()           # +
    MINUS = auto()          # -
    GT = auto()             # >
    LT = auto()             # <

    # Brackets
    LPAREN = auto()         # (
    RPAREN = auto()         # )
    LBRACKET = auto()       # [
    RBRACKET = auto()       # ]
    LBRACE = auto()         # {
    RBRACE = auto()         # }
    DEEPOPEN = auto()       # >>
    DEEPCLOSE = auto()      # <<

    # Special
    EOF = auto()


@dataclass
class Token:
    type: TokenType
    value: str
    line: int
    col: int


class LexerError(Exception):
    def __init__(self, message: str, line: int, col: int):
        self.line = line
        self.col = col
        super().__init__(f"Lexer error at {line}:{col}: {message}")


class Lexer:
    def __init__(self, text: str):
        self.text = text
        self.pos = 0
        self.line = 1
        self.col = 1

    def peek(self, offset: int = 0) -> str:
        pos = self.pos + offset
        if pos < len(self.text):
            return self.text[pos]
        return ''

    def advance(self) -> str:
        ch = self.peek()
        self.pos += 1
        if ch == '\n':
            self.line += 1
            self.col = 1
        else:
            self.col += 1
        return ch

    def skip_whitespace(self):
        while self.peek() and self.peek() in ' \t\n\r':
            self.advance()

    def skip_comment(self) -> bool:
        """Skip (* ... *) comments. Returns True if a comment was skipped."""
        if self.peek() == '(' and self.peek(1) == '*':
            self.advance()  # (
            self.advance()  # *
            while self.pos < len(self.text):
                if self.peek() == '*' and self.peek(1) == ')':
                    self.advance()  # *
                    self.advance()  # )
                    return True
                self.advance()
            raise LexerError("Unterminated comment", self.line, self.col)
        return False

    def read_quoted_string(self) -> str:
        """Read a quoted string, handling escape sequences."""
        self.advance()  # opening quote
        result = []
        while self.peek() and self.peek() != '"':
            ch = self.advance()
            if ch == '\\':
                next_ch = self.advance()
                if next_ch == 'n':
                    result.append('\n')
                elif next_ch == 'r':
                    result.append('\r')
                elif next_ch == 't':
                    result.append('\t')
                elif next_ch == 'b':
                    result.append('\b')
                elif next_ch == '"':
                    result.append('"')
                elif next_ch == '\\':
                    result.append('\\')
                elif next_ch.isdigit():
                    # ASCII decimal code
                    digits = next_ch
                    while len(digits) < 3 and self.peek().isdigit():
                        digits += self.advance()
                    result.append(chr(int(digits)))
                else:
                    result.append(next_ch)
            else:
                result.append(ch)
        if not self.peek():
            raise LexerError("Unterminated string", self.line, self.col)
        self.advance()  # closing quote
        return ''.join(result)

    def read_identifier(self) -> Tuple[str, bool]:
        """Read an identifier. Returns (value, is_nonterm)."""
        result = []
        first_char = self.peek()
        is_nonterm = first_char.isupper()

        while self.peek() and (self.peek().isalnum() or self.peek() == "'"):
            result.append(self.advance())

        return ''.join(result), is_nonterm

    def tokenize(self) -> List[Token]:
        tokens = []

        while self.pos < len(self.text):
            self.skip_whitespace()

            # Skip comments
            while self.skip_comment():
                self.skip_whitespace()

            if self.pos >= len(self.text):
                break

            line, col = self.line, self.col
            ch = self.peek()

            # Two-character tokens
            if ch == ':' and self.peek(1) == ':' and self.peek(2) == '=':
                tokens.append(Token(TokenType.DEFINE, '::=', line, col))
                self.advance(); self.advance(); self.advance()
            elif ch == ':' and self.peek(1) == '=':
                tokens.append(Token(TokenType.ASSIGN, ':=', line, col))
                self.advance(); self.advance()
            elif ch == '>' and self.peek(1) == '>':
                tokens.append(Token(TokenType.DEEPOPEN, '>>', line, col))
                self.advance(); self.advance()
            elif ch == '<' and self.peek(1) == '<':
                tokens.append(Token(TokenType.DEEPCLOSE, '<<', line, col))
                self.advance(); self.advance()
            # Valid @include directives are expanded before lexing
            elif self.text.startswith('@include', self.pos):
                raise LexerError(
                    '@include must be on its own line, followed by a "quoted" path',
                    line, col
                )
            # Emitted label: #label (same lexical rule as labels)
            elif ch == '#':
                self.advance()  # consume #
                tag_name = []
                while self.peek().isalnum():
                    tag_name.append(self.advance())
                if not tag_name:
                    raise LexerError("Expected label name after #", line, col)
                tokens.append(Token(TokenType.TAG, ''.join(tag_name), line, col))
            # Single-character tokens
            elif ch == '|':
                tokens.append(Token(TokenType.PIPE, '|', line, col))
                self.advance()
            elif ch == ';':
                tokens.append(Token(TokenType.SEMI, ';', line, col))
                self.advance()
            elif ch == ':':
                tokens.append(Token(TokenType.COLON, ':', line, col))
                self.advance()
            elif ch == ',':
                tokens.append(Token(TokenType.COMMA, ',', line, col))
                self.advance()
            elif ch == '.':
                tokens.append(Token(TokenType.DOT, '.', line, col))
                self.advance()
            elif ch == '^':
                tokens.append(Token(TokenType.CARET, '^', line, col))
                self.advance()
            elif ch == '_':
                tokens.append(Token(TokenType.UNDERSCORE, '_', line, col))
                self.advance()
            elif ch == '\\':
                tokens.append(Token(TokenType.BACKSLASH, '\\', line, col))
                self.advance()
            elif ch == '+':
                tokens.append(Token(TokenType.PLUS, '+', line, col))
                self.advance()
            elif ch == '-':
                tokens.append(Token(TokenType.MINUS, '-', line, col))
                self.advance()
            elif ch == '>':
                tokens.append(Token(TokenType.GT, '>', line, col))
                self.advance()
            elif ch == '<':
                tokens.append(Token(TokenType.LT, '<', line, col))
                self.advance()
            elif ch == '(':
                tokens.append(Token(TokenType.LPAREN, '(', line, col))
                self.advance()
            elif ch == ')':
                tokens.append(Token(TokenType.RPAREN, ')', line, col))
                self.advance()
            elif ch == '[':
                tokens.append(Token(TokenType.LBRACKET, '[', line, col))
                self.advance()
            elif ch == ']':
                tokens.append(Token(TokenType.RBRACKET, ']', line, col))
                self.advance()
            elif ch == '{':
                tokens.append(Token(TokenType.LBRACE, '{', line, col))
                self.advance()
            elif ch == '}':
                tokens.append(Token(TokenType.RBRACE, '}', line, col))
                self.advance()
            # Quoted string
            elif ch == '"':
                value = self.read_quoted_string()
                tokens.append(Token(TokenType.TERM, value, line, col))
            # Identifier (terminal or non-terminal)
            elif ch.isalpha() or ch == "'":
                value, is_nonterm = self.read_identifier()
                if is_nonterm:
                    tokens.append(Token(TokenType.NONTERM, value, line, col))
                else:
                    tokens.append(Token(TokenType.TERM, value, line, col))
            # Numbers as terminals
            elif ch.isdigit():
                value, _ = self.read_identifier()
                tokens.append(Token(TokenType.TERM, value, line, col))
            else:
                raise LexerError(f"Illegal character: {ch!r}", line, col)

        tokens.append(Token(TokenType.EOF, '', self.line, self.col))
        return tokens


# =============================================================================
# AST NODES
# =============================================================================

@dataclass
class ASTNode:
    pass


@dataclass
class Terminal(ASTNode):
    value: str


@dataclass
class NonTerminal(ASTNode):
    name: str
    unfold: bool = False
    fold: bool = False
    line: int = 0
    col: int = 0


@dataclass
class Epsilon(ASTNode):
    pass


@dataclass
class Concat(ASTNode):
    """Concatenation marker - suppresses space."""
    pass


@dataclass
class Capitalize(ASTNode):
    """Capitalization marker - capitalizes next terminal."""
    pass


@dataclass
class Sequence(ASTNode):
    """A sequence of atoms, optionally with a label."""
    atoms: List[ASTNode]
    label: Optional[str] = None


@dataclass
class Production(ASTNode):
    """A single production with weight modifier and emitted labels."""
    sequence: Sequence
    weight: int = 0  # positive = +, negative = -
    emitted_labels: List[str] = field(default_factory=list)  # #tag1 #tag2 ...


@dataclass
class Productions(ASTNode):
    """A set of pipe-separated productions."""
    items: List[Production]


@dataclass
class SubProduction(ASTNode):
    """A subproduction in parentheses."""
    productions: Productions
    declarations: List['Declaration'] = field(default_factory=list)
    is_optional: bool = False  # [...]
    is_permutable: bool = False  # {...}
    is_iterable: bool = False  # (...)+
    is_deep_unfold: bool = False  # >> ... <<
    unfold: bool = False  # > prefix
    fold: bool = False  # < prefix


@dataclass
class Selection(ASTNode):
    """Label selection: atom.label"""
    atom: ASTNode
    labels: List[Tuple[str, int]]  # [(label, weight), ...]
    reset: bool = False  # atom. (dot without label = reset)


@dataclass
class PositionalGroup(ASTNode):
    """Group of comma-separated atoms for positional generation."""
    atoms: List[ASTNode]


@dataclass
class Declaration(ASTNode):
    """A binding declaration."""
    name: str
    productions: Productions
    is_strong: bool = False  # := vs ::=
    line: int = 0
    col: int = 0


@dataclass
class Grammar(ASTNode):
    """The complete grammar."""
    declarations: List[Declaration]


# =============================================================================
# PARSER
# =============================================================================

class ParserError(Exception):
    def __init__(self, message: str, token: Token):
        self.token = token
        super().__init__(f"Parser error at {token.line}:{token.col}: {message}")


class Parser:
    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.pos = 0

    def peek(self, offset: int = 0) -> Token:
        pos = self.pos + offset
        if pos < len(self.tokens):
            return self.tokens[pos]
        return self.tokens[-1]  # EOF

    def advance(self) -> Token:
        token = self.peek()
        if self.pos < len(self.tokens) - 1:
            self.pos += 1
        return token

    def expect(self, type_: TokenType) -> Token:
        token = self.peek()
        if token.type != type_:
            raise ParserError(f"Expected {type_.name}, got {token.type.name}", token)
        return self.advance()

    def match(self, *types: TokenType) -> bool:
        return self.peek().type in types

    def parse(self) -> Grammar:
        """Parse the complete grammar."""
        declarations = self.parse_declarations()
        self.expect(TokenType.EOF)
        return Grammar(declarations)

    def parse_declarations(self) -> List[Declaration]:
        """Parse a series of declarations separated by semicolons."""
        declarations = []
        while self.match(TokenType.NONTERM):
            decl = self.parse_declaration()
            declarations.append(decl)
            self.expect(TokenType.SEMI)
        return declarations

    def parse_declaration(self) -> Declaration:
        """Parse a single declaration: Nonterm ::= | := Productions"""
        name_token = self.expect(TokenType.NONTERM)
        name = name_token.value

        is_strong = False
        if self.match(TokenType.DEFINE):
            self.advance()
        elif self.match(TokenType.ASSIGN):
            self.advance()
            is_strong = True
        else:
            raise ParserError("Expected ::= or :=", self.peek())

        productions = self.parse_productions()
        return Declaration(name, productions, is_strong, name_token.line, name_token.col)

    def parse_productions(self) -> Productions:
        """Parse pipe-separated productions."""
        items = [self.parse_production()]
        while self.match(TokenType.PIPE):
            self.advance()
            items.append(self.parse_production())
        return Productions(items)

    def parse_production(self) -> Production:
        """Parse a single production with optional +/- weight modifiers and emitted labels."""
        weight = 0
        while self.match(TokenType.PLUS, TokenType.MINUS):
            if self.advance().type == TokenType.PLUS:
                weight += 1
            else:
                weight -= 1

        sequence = self.parse_sequence()

        # Collect emitted labels (#tag1 #tag2 ...)
        emitted_labels = []
        while self.match(TokenType.TAG):
            emitted_labels.append(self.advance().value)

        return Production(sequence, weight, emitted_labels)

    def parse_sequence(self) -> Sequence:
        """Parse a sequence of atoms, optionally labeled."""
        label = None
        atoms = []

        # Check for label: prefix (can be NONTERM, TERM, or numeric like "1", "3")
        if self.match(TokenType.NONTERM, TokenType.TERM):
            # Lookahead to check if this is a label
            if self.peek(1).type == TokenType.COLON:
                label = self.advance().value
                self.advance()  # consume :

        # Parse atoms (possibly with comma groups)
        while self._is_atom_start():
            atom = self.parse_atom()

            # Check for comma-separated positional generation
            if self.match(TokenType.COMMA):
                group_atoms = [atom]
                while self.match(TokenType.COMMA):
                    self.advance()  # consume ,
                    if self._is_atom_start():
                        group_atoms.append(self.parse_atom())
                    else:
                        break
                if len(group_atoms) > 1:
                    atom = PositionalGroup(group_atoms)

            atoms.append(atom)

        return Sequence(atoms, label)

    def _is_atom_start(self) -> bool:
        """Check if current token can start an atom."""
        return self.match(
            TokenType.TERM, TokenType.NONTERM,
            TokenType.CARET, TokenType.UNDERSCORE, TokenType.BACKSLASH,
            TokenType.LPAREN, TokenType.LBRACKET, TokenType.LBRACE,
            TokenType.DEEPOPEN, TokenType.GT, TokenType.LT
        )

    def parse_atom(self) -> ASTNode:
        """Parse a single atom."""
        token = self.peek()

        # Unfold prefix
        unfold = False
        fold = False
        if self.match(TokenType.GT):
            self.advance()
            unfold = True
        elif self.match(TokenType.LT):
            self.advance()
            fold = True

        atom = None

        if self.match(TokenType.TERM):
            atom = Terminal(self.advance().value)
        elif self.match(TokenType.NONTERM):
            name_token = self.advance()
            atom = NonTerminal(name_token.value, unfold=unfold, fold=fold,
                               line=name_token.line, col=name_token.col)
            unfold = fold = False
        elif self.match(TokenType.CARET):
            self.advance()
            atom = Concat()
        elif self.match(TokenType.UNDERSCORE):
            self.advance()
            atom = Epsilon()
        elif self.match(TokenType.BACKSLASH):
            self.advance()
            atom = Capitalize()
        elif self.match(TokenType.LPAREN):
            atom = self.parse_subproduction(TokenType.LPAREN, TokenType.RPAREN)
            atom.unfold = unfold
            atom.fold = fold
            unfold = fold = False
        elif self.match(TokenType.LBRACKET):
            atom = self.parse_subproduction(TokenType.LBRACKET, TokenType.RBRACKET)
            atom.is_optional = True
            atom.unfold = unfold
            atom.fold = fold
            unfold = fold = False
        elif self.match(TokenType.LBRACE):
            atom = self.parse_subproduction(TokenType.LBRACE, TokenType.RBRACE)
            atom.is_permutable = True
            atom.unfold = unfold
            atom.fold = fold
            unfold = fold = False
        elif self.match(TokenType.DEEPOPEN):
            self.advance()
            declarations, productions = self.parse_sub_content()
            self.expect(TokenType.DEEPCLOSE)
            atom = SubProduction(productions, declarations, is_deep_unfold=True)
        else:
            raise ParserError(f"Unexpected token: {token.type.name}", token)

        # Handle iteration suffix: (...)+
        if isinstance(atom, SubProduction) and self.match(TokenType.PLUS):
            self.advance()
            atom.is_iterable = True

        # Handle selection suffix: .label or .
        while self.match(TokenType.DOT):
            self.advance()
            if self.match(TokenType.LPAREN):
                # .(label1|label2|...)
                self.advance()
                labels = self.parse_label_list()
                self.expect(TokenType.RPAREN)
                atom = Selection(atom, labels)
            elif self.match(TokenType.NONTERM, TokenType.TERM):
                # Simple .label (including numeric labels like .1, .3)
                label_token = self.advance()
                atom = Selection(atom, [(label_token.value, 0)])
            else:
                # Just . (selection reset)
                atom = Selection(atom, [], reset=True)

        return atom

    def parse_label_list(self) -> List[Tuple[str, int]]:
        """Parse a list of labels with optional weights: (+l1|-l2|l3)"""
        labels = []
        while True:
            weight = 0
            while self.match(TokenType.PLUS, TokenType.MINUS):
                if self.advance().type == TokenType.PLUS:
                    weight += 1
                else:
                    weight -= 1

            if self.match(TokenType.NONTERM, TokenType.TERM):
                labels.append((self.advance().value, weight))

            if not self.match(TokenType.PIPE):
                break
            self.advance()

        return labels

    def parse_subproduction(self, open_type: TokenType, close_type: TokenType) -> SubProduction:
        """Parse a subproduction within brackets."""
        self.expect(open_type)
        declarations, productions = self.parse_sub_content()
        self.expect(close_type)
        return SubProduction(productions, declarations)

    def parse_sub_content(self) -> Tuple[List[Declaration], Productions]:
        """Parse the content of a subproduction (optional declarations + productions)."""
        declarations = []

        # Check for local declarations
        while self.match(TokenType.NONTERM):
            # Lookahead to check if this is a declaration
            if self.peek(1).type in (TokenType.DEFINE, TokenType.ASSIGN):
                decl = self.parse_declaration()
                declarations.append(decl)
                self.expect(TokenType.SEMI)
            else:
                break

        productions = self.parse_productions()
        return declarations, productions


class ValidationError(Exception):
    def __init__(self, message: str, line: Optional[int] = None, col: Optional[int] = None):
        location = f" at {line}:{col}" if line is not None and col is not None else ""
        super().__init__(f"Validation error{location}: {message}")


class Validator:
    """Check references and duplicate bindings in each lexical scope."""

    def validate(self, grammar: Grammar):
        self._validate_scope(grammar.declarations, {})

    def _validate_scope(self, declarations: List[Declaration], outer: Dict[str, Declaration]):
        local = {}
        for decl in declarations:
            if decl.name in local:
                raise ValidationError(f"Duplicate symbol: {decl.name}", decl.line, decl.col)
            local[decl.name] = decl

        visible = {**outer, **local}
        for decl in declarations:
            self._validate_productions(decl.productions, visible)
        return visible

    def _validate_productions(self, productions: Productions, visible: Dict[str, Declaration]):
        for production in productions.items:
            for atom in production.sequence.atoms:
                self._validate_atom(atom, visible)

    def _validate_atom(self, atom: ASTNode, visible: Dict[str, Declaration]):
        if isinstance(atom, NonTerminal):
            if atom.name not in visible:
                raise ValidationError(f"Undefined symbol: {atom.name}", atom.line, atom.col)
        elif isinstance(atom, SubProduction):
            local_visible = self._validate_scope(atom.declarations, visible)
            self._validate_productions(atom.productions, local_visible)
        elif isinstance(atom, Selection):
            self._validate_atom(atom.atom, visible)
        elif isinstance(atom, PositionalGroup):
            for item in atom.atoms:
                self._validate_atom(item, visible)


class Preprocessor:
    """Preprocesses the AST to handle syntactic transformations."""

    def __init__(self):
        self.declarations = {}  # name -> Declaration (for unfolding lookups)

    def process(self, grammar: Grammar) -> Grammar:
        """Process the grammar, expanding positional generation and unfolding."""
        # First pass: collect all declarations for lookup
        for decl in grammar.declarations:
            self.declarations[decl.name] = decl

        # Second pass: process declarations
        new_declarations = []
        for decl in grammar.declarations:
            new_prods = self.process_productions(decl.productions, in_deep_unfold=False)
            new_declarations.append(Declaration(decl.name, new_prods, decl.is_strong,
                                                decl.line, decl.col))

        return Grammar(new_declarations)

    def process_productions(self, prods: Productions, in_deep_unfold: bool = False) -> Productions:
        """Process productions, expanding positional groups and unfolding."""
        new_items = []
        for prod in prods.items:
            expanded = self.expand_production(prod, in_deep_unfold)
            new_items.extend(expanded)
        return Productions(new_items)

    def expand_production(self, prod: Production, in_deep_unfold: bool) -> List[Production]:
        """Expand a production, handling positional groups and unfolding."""
        seq = prod.sequence
        atoms = seq.atoms

        # First expand positional groups
        positional_expanded = self.expand_positional_in_sequence(
            atoms, seq.label, prod.weight, prod.emitted_labels, in_deep_unfold
        )

        # Then handle unfolding for each resulting production
        final_result = []
        for p in positional_expanded:
            unfolded = self.expand_unfolding_in_production(p, in_deep_unfold)
            final_result.extend(unfolded)

        return final_result

    def expand_positional_in_sequence(self, atoms: List[ASTNode], label: Optional[str],
                                       weight: int, emitted_labels: List[str],
                                       in_deep_unfold: bool) -> List[Production]:
        """Expand positional groups in a sequence."""
        # Find all positional groups
        groups = [(i, atom) for i, atom in enumerate(atoms) if isinstance(atom, PositionalGroup)]

        if not groups:
            # No positional groups, process atoms and return as single production
            new_atoms = [self.process_atom(a, in_deep_unfold) for a in atoms]
            return [Production(Sequence(new_atoms, label), weight, emitted_labels)]

        # Check all groups have same size
        group_size = len(groups[0][1].atoms)
        for idx, group in groups:
            if len(group.atoms) != group_size:
                raise GeneratorError(
                    f"Positional groups must have same size: expected {group_size}, got {len(group.atoms)}"
                )

        # Expand into group_size productions
        result = []
        for pos in range(group_size):
            new_atoms = []
            for i, atom in enumerate(atoms):
                if isinstance(atom, PositionalGroup):
                    new_atoms.append(self.process_atom(atom.atoms[pos], in_deep_unfold))
                else:
                    new_atoms.append(self.process_atom(atom, in_deep_unfold))
            result.append(Production(Sequence(new_atoms, label), weight, emitted_labels))

        return result

    def expand_unfolding_in_production(self, prod: Production, in_deep_unfold: bool) -> List[Production]:
        """Expand unfolding operators in a production, flattening productions."""
        seq = prod.sequence
        atoms = seq.atoms

        # Find the first atom that must be unfolded at this level.
        unfold_index = None
        for i, atom in enumerate(atoms):
            if (
                isinstance(atom, (SubProduction, NonTerminal))
                and atom.unfold
                and not atom.fold
            ):
                unfold_index = i
                break

        if unfold_index is None:
            # No unfolding needed at this level
            return [prod]

        # Get the atom to unfold
        atom = atoms[unfold_index]

        # Get the productions to unfold. A non-terminal reached through deep
        # unfolding is expanded by one level only, as required by the spec.
        preserve_permutation = False
        local_declarations = []
        if isinstance(atom, SubProduction):
            inner_prods = list(atom.productions.items)
            preserve_permutation = atom.is_permutable
            local_declarations = atom.declarations

            # [P] behaves like (P | _); unfolding must not lose epsilon.
            if atom.is_optional:
                inner_prods.append(Production(Sequence([Epsilon()])))
        else:
            decl = self.declarations.get(atom.name)
            if decl is None:
                return [prod]
            inner_prods = self.process_productions(
                decl.productions, in_deep_unfold=False
            ).items

        # Create new productions by distributing
        result = []
        prefix = atoms[:unfold_index]
        suffix = atoms[unfold_index + 1:]

        for inner_prod in inner_prods:
            inner_atoms = inner_prod.sequence.atoms
            inner_label = inner_prod.sequence.label

            # A one-production wrapper keeps the inner emitted labels at the
            # position of the unfolded atom, so that they still affect only
            # the atoms that follow it: unfolding must change probabilities,
            # not semantics.
            wrapper_prods = Productions([Production(
                Sequence(list(inner_atoms)), 0, list(inner_prod.emitted_labels)
            )])

            if preserve_permutation:
                # Permutation precedes unfolding. Keep a one-production
                # permutable wrapper so the generator can still swap it with
                # the other permutable atoms in the surrounding sequence.
                replacement = SubProduction(
                    wrapper_prods,
                    declarations=local_declarations,
                    is_permutable=True,
                )
                replacement_atoms = [replacement]
            elif inner_prod.emitted_labels:
                replacement_atoms = [SubProduction(wrapper_prods)]
            else:
                replacement_atoms = list(inner_atoms)

            new_atoms = list(prefix) + replacement_atoms + list(suffix)

            # Inherit label from inner if present, else from outer
            new_label = inner_label if inner_label else seq.label

            # Combine weights
            new_weight = prod.weight + inner_prod.weight

            new_prod = Production(
                Sequence(new_atoms, new_label), new_weight, prod.emitted_labels
            )

            # Recursively expand any remaining unfolding
            result.extend(self.expand_unfolding_in_production(new_prod, in_deep_unfold))

        return result

    def process_atom(self, atom: ASTNode, in_deep_unfold: bool = False) -> ASTNode:
        """Process an atom recursively."""
        if isinstance(atom, SubProduction):
            # Handle deep unfold
            new_in_deep = in_deep_unfold or atom.is_deep_unfold
            should_unfold = atom.unfold or (in_deep_unfold and not atom.fold)

            new_decls = []
            for decl in atom.declarations:
                new_prods = self.process_productions(decl.productions, new_in_deep)
                new_decls.append(Declaration(decl.name, new_prods, decl.is_strong,
                                             decl.line, decl.col))

            new_prods = self.process_productions(atom.productions, new_in_deep)

            return SubProduction(
                new_prods, new_decls,
                atom.is_optional, atom.is_permutable, atom.is_iterable,
                atom.is_deep_unfold, should_unfold, atom.fold
            )
        elif isinstance(atom, Selection):
            return Selection(self.process_atom(atom.atom, in_deep_unfold), atom.labels, atom.reset)
        elif isinstance(atom, PositionalGroup):
            return PositionalGroup([self.process_atom(a, in_deep_unfold) for a in atom.atoms])
        elif isinstance(atom, NonTerminal):
            should_unfold = atom.unfold or (in_deep_unfold and not atom.fold)
            return NonTerminal(atom.name, unfold=should_unfold, fold=atom.fold,
                               line=atom.line, col=atom.col)
        else:
            return atom


# =============================================================================
# GENERATOR
# =============================================================================

class GeneratorError(Exception):
    pass


@dataclass
class Environment:
    """Scoped environment for symbol bindings."""
    bindings: Dict[str, Tuple[Productions, bool, 'Environment']] = field(default_factory=dict)
    # name -> (productions, is_strong, closure_env)
    suspensions: Dict[str, Tuple[List[str], List[str]]] = field(default_factory=dict)
    # name -> cached (tokens, emitted_labels) for strong bindings. A suspension
    # is stored in the environment where the symbol is bound, so every
    # occurrence in that scope sees the same value.
    parent: Optional['Environment'] = None
    active_labels: Set[str] = field(default_factory=set)

    def bind(self, name: str, productions: Productions, is_strong: bool):
        self.bindings[name] = (productions, is_strong, self)

    def lookup(self, name: str) -> Optional[Tuple[Productions, bool, 'Environment']]:
        if name in self.bindings:
            return self.bindings[name]
        if self.parent:
            return self.parent.lookup(name)
        return None

    def child(self, labels: Optional[Set[str]] = None) -> 'Environment':
        """Create a child environment."""
        new_labels = labels if labels is not None else self.active_labels.copy()
        return Environment(parent=self, active_labels=new_labels)


class Generator:
    def __init__(self, grammar: Grammar, max_recursion: int = 100):
        self.grammar = grammar
        self.max_recursion = max_recursion
        self.recursion_depth = 0

    def generate(self, start_symbol: str = 'S') -> str:
        """Generate a random string starting from the given symbol."""
        # Build top-level environment
        env = Environment()
        for decl in self.grammar.declarations:
            env.bind(decl.name, decl.productions, decl.is_strong)

        # Generate from start symbol
        result, _ = self.generate_nonterm(start_symbol, env)
        return self._format_output(result)

    def _format_output(self, tokens: List[str]) -> str:
        """Format the token list into a final string."""
        result = []
        concat_next = False
        capitalize_next = False

        for token in tokens:
            if token == '\x00':  # Concat marker
                concat_next = True
            elif token == '\x01':  # Capitalize marker
                capitalize_next = True
            elif token:  # Non-empty token
                if capitalize_next:
                    token = token[0].upper() + token[1:] if token else token
                    capitalize_next = False

                if result and not concat_next:
                    result.append(' ')
                result.append(token)
                concat_next = False

        return ''.join(result).strip()

    def generate_nonterm(self, name: str, env: Environment) -> Tuple[List[str], List[str]]:
        """Generate from a non-terminal symbol. Returns (tokens, emitted_labels)."""
        self.recursion_depth += 1
        if self.recursion_depth > self.max_recursion:
            raise GeneratorError(f"Maximum recursion depth exceeded for symbol {name}")

        try:
            binding = env.lookup(name)
            if binding is None:
                raise GeneratorError(f"Undefined symbol: {name}")

            productions, is_strong, closure_env = binding

            # A suspended symbol replays both its text and its emitted labels
            if is_strong and name in closure_env.suspensions:
                return closure_env.suspensions[name]

            # Generate in closure environment with current labels
            gen_env = closure_env.child(env.active_labels)
            result, emitted = self.generate_productions(productions, gen_env)

            if is_strong:
                closure_env.suspensions[name] = (result, emitted)

            return result, emitted
        finally:
            self.recursion_depth -= 1

    def generate_productions(self, productions: Productions, env: Environment) -> Tuple[List[str], List[str]]:
        """Generate from a set of productions. Returns (tokens, emitted_labels)."""
        # Filter productions by active labels
        valid_prods = []
        for prod in productions.items:
            seq = prod.sequence
            if seq.label is None or seq.label in env.active_labels or not env.active_labels:
                valid_prods.append(prod)

        if not valid_prods:
            return [], []  # All filtered out (destructive selection)

        # Calculate weights
        weights = []
        min_weight = min(p.weight for p in valid_prods)
        for prod in valid_prods:
            # Normalize: shift so minimum is 1
            w = prod.weight - min_weight + 1
            weights.append(w)

        # Weighted random choice
        total = sum(weights)
        r = random.randint(1, total)
        cumulative = 0
        chosen = valid_prods[0]
        for prod, w in zip(valid_prods, weights):
            cumulative += w
            if r <= cumulative:
                chosen = prod
                break

        tokens, seq_emitted = self.generate_sequence(chosen.sequence, env)
        # Combine emitted labels from production definition and sequence generation
        all_emitted = chosen.emitted_labels + seq_emitted
        return tokens, all_emitted

    def generate_sequence(self, sequence: Sequence, env: Environment) -> Tuple[List[str], List[str]]:
        """Generate from a sequence of atoms. Returns (tokens, emitted_labels)."""
        atoms = sequence.atoms

        # Handle permutation: collect permutable atoms and shuffle their positions
        permutable_indices = []
        permutable_atoms = []
        for i, atom in enumerate(atoms):
            if isinstance(atom, SubProduction) and atom.is_permutable:
                permutable_indices.append(i)
                permutable_atoms.append(atom)

        if len(permutable_atoms) > 1:
            # Shuffle permutable atoms
            random.shuffle(permutable_atoms)
            # Create new atom list with shuffled permutables
            atoms = list(atoms)
            for i, idx in enumerate(permutable_indices):
                atoms[idx] = permutable_atoms[i]

        result = []
        all_emitted = []
        current_env = env

        for atom in atoms:
            tokens, emitted = self.generate_atom(atom, current_env)
            result.extend(tokens)
            all_emitted.extend(emitted)

            # Forward propagation: if this atom emitted labels, add them to env for subsequent atoms
            if emitted:
                new_labels = current_env.active_labels | set(emitted)
                current_env = current_env.child(new_labels)

        return result, all_emitted

    def generate_atom(self, atom: ASTNode, env: Environment) -> Tuple[List[str], List[str]]:
        """Generate from a single atom. Returns (tokens, emitted_labels)."""
        if isinstance(atom, Terminal):
            return [atom.value], []

        elif isinstance(atom, NonTerminal):
            return self.generate_nonterm(atom.name, env)

        elif isinstance(atom, Epsilon):
            return [], []

        elif isinstance(atom, Concat):
            return ['\x00'], []  # Special concat marker

        elif isinstance(atom, Capitalize):
            return ['\x01'], []  # Special capitalize marker

        elif isinstance(atom, SubProduction):
            return self.generate_subproduction(atom, env)

        elif isinstance(atom, Selection):
            return self.generate_selection(atom, env)

        else:
            raise GeneratorError(f"Unknown atom type: {type(atom)}")

    def generate_subproduction(self, sub: SubProduction, env: Environment) -> Tuple[List[str], List[str]]:
        """Generate from a subproduction. Returns (tokens, emitted_labels)."""
        # Handle optional: 50% chance of epsilon
        if sub.is_optional and random.random() < 0.5:
            return [], []

        # Create local environment with declarations
        local_env = env.child()
        for decl in sub.declarations:
            local_env.bind(decl.name, decl.productions, decl.is_strong)

        # Handle iteration
        if sub.is_iterable:
            result = []
            all_emitted = []
            # At least one iteration
            tokens, emitted = self.generate_productions(sub.productions, local_env)
            result.extend(tokens)
            all_emitted.extend(emitted)
            # 50% chance for each additional iteration
            while random.random() < 0.5:
                tokens, emitted = self.generate_productions(sub.productions, local_env)
                result.extend(tokens)
                all_emitted.extend(emitted)
            return result, all_emitted

        # Handle permutation - this is handled at sequence level, not here
        # Permutable subproductions are markers; actual permutation happens in generate_sequence

        # Normal generation
        return self.generate_productions(sub.productions, local_env)

    def generate_selection(self, sel: Selection, env: Environment) -> Tuple[List[str], List[str]]:
        """Generate from a selection. Returns (tokens, emitted_labels)."""
        if sel.reset:
            # Reset selection: clear active labels
            new_env = env.child(set())
            return self.generate_atom(sel.atom, new_env)

        if sel.labels:
            # Calculate weighted label selection
            weights = []
            min_weight = min(w for _, w in sel.labels) if sel.labels else 0
            for label, weight in sel.labels:
                w = weight - min_weight + 1
                weights.append(w)

            # Weighted random choice of label
            total = sum(weights)
            r = random.randint(1, total)
            cumulative = 0
            chosen_label = sel.labels[0][0]
            for (label, _), w in zip(sel.labels, weights):
                cumulative += w
                if r <= cumulative:
                    chosen_label = label
                    break

            # Add label to active set
            new_labels = env.active_labels | {chosen_label}
            new_env = env.child(new_labels)
            return self.generate_atom(sel.atom, new_env)

        return self.generate_atom(sel.atom, env)


# =============================================================================
# INCLUDE PREPROCESSING
# =============================================================================

INCLUDE_PATTERN = re.compile(r'^[ \t]*@include[ \t]+"([^"\n]+)"[ \t]*$', re.MULTILINE)

def preprocess_includes(source: str, base_path: Optional[str] = None,
                        included: Optional[Set[str]] = None) -> str:
    """
    Expand @include directives, recursively.

    A directive must stand on its own line: @include "path/to/file.grm".
    Relative paths are resolved from base_path (the current directory when
    base_path is None). Each file is included at most once, which also
    prevents include cycles.

    Args:
        source: The grammar source code
        base_path: Base directory for resolving relative paths
        included: Absolute paths of the files already included

    Returns:
        The source with all includes expanded
    """
    if included is None:
        included = set()

    def replace_include(match):
        filename = match.group(1)
        filepath = os.path.join(base_path or '', filename)
        abs_path = os.path.abspath(filepath)

        if abs_path in included:
            return ''
        included.add(abs_path)

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                included_source = f.read()
        except FileNotFoundError:
            line = source.count('\n', 0, match.start()) + 1
            raise LexerError(f"Include file not found: {filename}", line, 1)

        return preprocess_includes(included_source, os.path.dirname(abs_path), included)

    return INCLUDE_PATTERN.sub(replace_include, source)


# =============================================================================
# PUBLIC API
# =============================================================================

class Polygen:
    """Main Polygen class for parsing and generating from grammars."""

    def __init__(self, source: str, base_path: Optional[str] = None):
        """
        Initialize Polygen with a grammar source.

        Args:
            source: The PML grammar source code
            base_path: Base directory for resolving @include paths
        """
        self.source = source
        self.base_path = base_path
        self.grammar = None
        self._parse()

    def _parse(self):
        """Parse the grammar source."""
        # Preprocess includes
        processed_source = preprocess_includes(self.source, self.base_path)

        lexer = Lexer(processed_source)
        tokens = lexer.tokenize()
        parser = Parser(tokens)
        self.grammar = parser.parse()
        Validator().validate(self.grammar)

        # Preprocess: expand positional generation
        preprocessor = Preprocessor()
        self.grammar = preprocessor.process(self.grammar)

    def validate(self, start_symbol: str = 'S'):
        """Check that the requested starting symbol can be generated."""
        if not any(decl.name == start_symbol for decl in self.grammar.declarations):
            raise ValidationError(f"Undefined start symbol: {start_symbol}")

    def generate(self, start_symbol: str = 'S', max_recursion: int = 100) -> str:
        """
        Generate a random string from the grammar.

        Args:
            start_symbol: The non-terminal symbol to start from (default: 'S')
            max_recursion: Maximum recursion depth (default: 100)

        Returns:
            The generated string
        """
        self.validate(start_symbol)
        generator = Generator(self.grammar, max_recursion)
        return generator.generate(start_symbol)

    def info(self) -> str:
        """
        Get the grammar info (generates from 'I' symbol if defined).

        Returns:
            The info string, or empty if 'I' is not defined
        """
        try:
            return self.generate('I')
        except ValidationError:
            return ""

    @classmethod
    def from_file(cls, path: str) -> 'Polygen':
        """
        Load a grammar from a file.

        Args:
            path: Path to the grammar file

        Returns:
            A Polygen instance
        """
        with open(path, 'r', encoding='utf-8') as f:
            source = f.read()
        base_path = os.path.dirname(os.path.abspath(path))
        return cls(source, base_path)


def main():
    """Command-line interface."""
    import sys
    import argparse

    parser = argparse.ArgumentParser(
        description='Polygen - Random text generator from grammars'
    )
    parser.add_argument('file', nargs='?', help='Grammar file to load')
    parser.add_argument('-n', '--count', type=int, default=1,
                       help='Number of sentences to generate')
    parser.add_argument('-s', '--start', default='S',
                       help='Starting symbol (default: S)')
    parser.add_argument('-i', '--info', action='store_true',
                       help='Show grammar info')
    parser.add_argument('--check', action='store_true',
                       help='Validate the grammar without generating text')
    parser.add_argument('-S', '--seed', type=int,
                       help='Random seed for reproducibility')

    args = parser.parse_args()

    if args.check and not args.file:
        parser.error('--check requires a grammar file')

    if args.seed is not None:
        random.seed(args.seed)

    if args.file:
        try:
            pg = Polygen.from_file(args.file)

            if args.check:
                pg.validate(args.start)
                print("Grammar references and definitions are valid")
            elif args.info:
                info = pg.info()
                if info:
                    print(info)
                else:
                    print("(No info defined)", file=sys.stderr)
            else:
                for _ in range(args.count):
                    print(pg.generate(args.start))

        except (LexerError, ParserError, ValidationError, GeneratorError) as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
        except FileNotFoundError:
            print(f"Error: File not found: {args.file}", file=sys.stderr)
            sys.exit(1)
    else:
        # Interactive demo
        demo_grammar = '''
S ::= the Animal is eating Fruit ;

Animal ::= cat | dog | rabbit ;
Fruit ::= an apple | a mango | an orange ;
'''
        print("Polygen Python Implementation")
        print("=" * 40)
        print("Demo grammar:")
        print(demo_grammar)
        print("Generated sentences:")
        print("-" * 40)

        pg = Polygen(demo_grammar)
        for _ in range(5):
            print(pg.generate())


if __name__ == '__main__':
    main()
