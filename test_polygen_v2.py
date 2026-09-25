"""
Test suite per le estensioni v2 di Polygen:
- Emitted labels (#label)
- Direttiva @include
"""

import random
import pytest
from polygen import Polygen, LexerError


def generations(grammar, n=200):
    pg = Polygen(grammar)
    return {pg.generate() for _ in range(n)}


@pytest.fixture(autouse=True)
def seeded():
    random.seed(42)


# =============================================================================
# TEST EMITTED LABELS
# =============================================================================

class TestEmittedLabels:
    """Test delle emitted labels (#label)."""

    def test_basic_emit(self):
        """La label emessa filtra le produzioni etichettate successive."""
        grammar = '''
        S ::= Source Target ;
        Source ::= start #on ;
        Target ::= on: yes | off: no ;
        '''
        assert generations(grammar) == {"start yes"}

    def test_multiple_emit(self):
        """Una produzione può emettere più label."""
        grammar = '''
        S ::= Source Target ;
        Source ::= begin #a #b ;
        Target ::= a: alpha | b: beta | c: gamma ;
        '''
        assert generations(grammar) == {"begin alpha", "begin beta"}

    def test_emit_forward_only(self):
        """Le label emesse non influenzano gli atomi precedenti."""
        grammar = '''
        S ::= Before Source After ;
        Before ::= x: bx | y: by ;
        Source ::= middle #x ;
        After ::= x: ax | y: ay ;
        '''
        assert generations(grammar) == {"bx middle ax", "by middle ax"}

    def test_place_influences_action(self):
        """Scenario realistico: il luogo vincola l'azione."""
        grammar = '''
        S ::= Luogo Azione ;
        Luogo ::= nella foresta #natura | in citta #urbano ;
        Azione ::= natura: cammina | urbano: prende un taxi | corre ;
        '''
        assert generations(grammar) == {
            "nella foresta cammina", "nella foresta corre",
            "in citta prende un taxi", "in citta corre",
        }

    def test_emit_in_subproduction(self):
        """Una subproduzione emette verso gli atomi che la seguono."""
        grammar = '''
        S ::= (here #mark) There ;
        There ::= mark: found | other: lost ;
        '''
        assert generations(grammar) == {"here found"}

    def test_numeric_label(self):
        """I tag seguono la stessa regola lessicale delle label."""
        grammar = '''
        S ::= Person Verb ;
        Person ::= he #3 | "I" #1 ;
        Verb ::= 1: eat | 3: eats ;
        '''
        assert generations(grammar) == {"he eats", "I eat"}

    def test_unfolding_preserves_emission(self):
        """L'unfolding cambia le probabilità, non l'effetto dei tag."""
        grammar = '''
        S ::= >Luogo Azione ;
        Luogo ::= foresta #natura | citta #urbano ;
        Azione ::= natura: cammina | urbano: taxi ;
        '''
        assert generations(grammar) == {"foresta cammina", "citta taxi"}

    def test_strong_binding_replays_emission(self):
        """Un simbolo sospeso riemette le sue label a ogni occorrenza."""
        grammar = '''
        S ::= X A ;
        A ::= X Azione ;
        X := foresta #natura | citta #urbano ;
        Azione ::= natura: cammina | urbano: taxi ;
        '''
        assert generations(grammar) == {
            "foresta foresta cammina", "citta citta taxi",
        }

    def test_tag_without_name(self):
        with pytest.raises(LexerError, match="label name after #"):
            Polygen('S ::= a # ;')


# =============================================================================
# TEST INCLUDE
# =============================================================================

class TestInclude:
    """Test della direttiva @include."""

    def test_basic_include(self, tmp_path):
        (tmp_path / "vocab.grm").write_text('Animal ::= cat | dog ;')
        main = tmp_path / "main.grm"
        main.write_text('@include "vocab.grm"\nS ::= the Animal ;')

        pg = Polygen.from_file(str(main))

        assert {pg.generate() for _ in range(50)} == {"the cat", "the dog"}

    def test_nested_include_relative_to_includer(self, tmp_path):
        """I path sono relativi al file che contiene la direttiva."""
        sub = tmp_path / "lib"
        sub.mkdir()
        (sub / "base.grm").write_text('Word ::= hello | world ;')
        (sub / "mid.grm").write_text('@include "base.grm"\nPhrase ::= Word Word ;')
        main = tmp_path / "main.grm"
        main.write_text('@include "lib/mid.grm"\nS ::= Phrase ;')

        pg = Polygen.from_file(str(main))

        assert {pg.generate() for _ in range(80)} == {
            "hello hello", "hello world", "world hello", "world world",
        }

    def test_include_cycle_prevention(self, tmp_path):
        (tmp_path / "a.grm").write_text('@include "b.grm"\nA ::= a ;')
        (tmp_path / "b.grm").write_text('@include "a.grm"\nB ::= b ;')
        main = tmp_path / "main.grm"
        main.write_text('@include "a.grm"\nS ::= A B ;')

        assert Polygen.from_file(str(main)).generate() == "a b"

    def test_include_file_not_found_reports_line(self, tmp_path):
        with pytest.raises(LexerError, match=r"at 3:1: Include file not found"):
            Polygen('S ::= x ;\n\n@include "nonexistent.grm"\n',
                    base_path=str(tmp_path))

    def test_malformed_include(self):
        with pytest.raises(LexerError, match="own line"):
            Polygen('S ::= x ; @include "vocab.grm"')

    def test_include_text_in_quoted_terminal(self):
        """Una stringa quotata non viene scambiata per una direttiva."""
        assert Polygen('S ::= "@include \'x.grm\'" ;').generate() == "@include 'x.grm'"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
