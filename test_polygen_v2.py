"""
Test suite per le estensioni v2 di Polygen:
- Emitted labels (#label)
- Direttiva @include
"""

import random
import subprocess
import sys
from pathlib import Path
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


class TestExpandIncludes:
    def run_cli(self, *args, cwd=None):
        return subprocess.run(
            [sys.executable, str(Path(__file__).with_name('polygen.py')), *map(str, args)],
            capture_output=True, text=True, cwd=cwd, timeout=5)

    def test_single_include_preserves_pml(self, tmp_path):
        vocab = '(* vocabolario *)\nWord ::= a | b ;'
        (tmp_path / 'vocab.grm').write_text(vocab, encoding='utf-8')
        main = tmp_path / 'main.grm'
        main.write_text('(* prima *)\n@include "vocab.grm"\nS ::= >> <Word | >[c] << ;\n',
                        encoding='utf-8')
        result = self.run_cli(main, '--expand-includes')
        assert result.returncode == 0
        assert result.stderr == ''
        assert result.stdout == '(* prima *)\n' + vocab + '\nS ::= >> <Word | >[c] << ;\n'

    def test_nested_repeated_and_cyclic_includes(self, tmp_path):
        sub = tmp_path / 'lib'
        sub.mkdir()
        (sub / 'word.grm').write_text('Word ::= ciao | mondo ;', encoding='utf-8')
        (sub / 'mid.grm').write_text(
            '@include "word.grm"\n@include "../main.grm"\nPhrase := Word Word ;',
            encoding='utf-8')
        main = tmp_path / 'main.grm'
        main.write_text('@include "lib/mid.grm"\n@include "lib/word.grm"\nS ::= Phrase ;',
                        encoding='utf-8')
        output = tmp_path / 'complete.grm'
        result = self.run_cli(main, '--expand-includes', '-o', output, cwd=sub)
        assert result.returncode == 0
        assert result.stdout == result.stderr == ''
        assert output.read_text(encoding='utf-8') == (
            'Word ::= ciao | mondo ;\n\nPhrase := Word Word ;\n\nS ::= Phrase ;')
        original = Polygen.from_file(str(main))
        random.seed(123)
        expected = [original.generate() for _ in range(100)]
        # The export must work after all its dependencies have disappeared.
        for path in [main, sub / 'word.grm', sub / 'mid.grm']:
            path.unlink()
        expanded = Polygen.from_file(str(output))
        random.seed(123)
        assert [expanded.generate() for _ in range(100)] == expected

    def test_no_include_preserves_bytes_and_skips_pml_validation(self, tmp_path):
        source = b'(* comment *)\r\nS ::= >Missing ;\r\n'
        main = tmp_path / 'main.grm'
        main.write_bytes(source)
        output = tmp_path / 'complete.grm'
        result = self.run_cli(main, '--expand-includes', '--output', output)
        assert result.returncode == 0
        assert output.read_bytes() == source

    def test_commented_and_quoted_directives_are_unchanged(self, tmp_path):
        source = ('(*\n@include "missing.grm"\n*)\n'
                  'S ::= "hello\n@include \\"missing.grm\\"\nworld" ;\n')
        main = tmp_path / 'main.grm'
        main.write_text(source, encoding='utf-8')
        result = self.run_cli(main, '--expand-includes')
        assert result.returncode == 0
        assert result.stdout == source
        assert Polygen.from_file(str(main)).generate() == 'hello\n@include "missing.grm"\nworld'

    @pytest.mark.parametrize('source, message', [
        ('@include "missing.grm"\nS ::= a ;', 'Include file not found'),
        ('@include missing.grm\nS ::= a ;', 'own line'),
        ('S ::= a ; @include "vocab.grm"', 'own line'),
        ('@include "vocab.grm" trailing', 'own line'),
        ('@include "directory"\nS ::= a ;', 'Error:'),
        ('@include "invalid.grm"\nS ::= a ;', 'Error:'),
    ])
    def test_errors_do_not_publish_partial_output(self, tmp_path, source, message):
        source = '@include "vocab.grm"\n' + source
        main = tmp_path / 'main.grm'
        main.write_text(source, encoding='utf-8')
        (tmp_path / 'vocab.grm').write_text('Word ::= ciao ;', encoding='utf-8')
        (tmp_path / 'directory').mkdir()
        (tmp_path / 'invalid.grm').write_bytes(b'\xff')
        output = tmp_path / 'complete.grm'
        for args in [[], ['-o', output], ['-o', main, '--force']]:
            result = self.run_cli(main, '--expand-includes', *args)
            assert result.returncode == 1
            assert result.stdout == ''
            assert message in result.stderr
            assert not output.exists()
            assert main.read_text(encoding='utf-8') == source
        assert not list(tmp_path.glob('tmp*'))

    @pytest.mark.parametrize('destination', ['main.grm', 'vocab.grm', 'existing.grm'])
    def test_overwrite_requires_force(self, tmp_path, destination):
        main = tmp_path / 'main.grm'
        source = '@include "vocab.grm"\nS ::= Word ;'
        main.write_text(source, encoding='utf-8')
        (tmp_path / 'vocab.grm').write_text('Word ::= ciao ;', encoding='utf-8')
        (tmp_path / 'existing.grm').write_text('keep', encoding='utf-8')
        output = tmp_path / destination
        before = output.read_bytes()
        result = self.run_cli(main, '--expand-includes', '-o', output)
        assert result.returncode == 1
        assert '--force' in result.stderr
        assert result.stdout == ''
        assert output.read_bytes() == before
        result = self.run_cli(main, '--expand-includes', '-o', output, '--force')
        assert result.returncode == 0
        assert output.read_text(encoding='utf-8') == 'Word ::= ciao ;\nS ::= Word ;'
        assert not list(tmp_path.glob('tmp*'))

    def test_symlink_output_is_protected(self, tmp_path):
        main = tmp_path / 'main.grm'
        main.write_text('S ::= ciao ;', encoding='utf-8')
        output = tmp_path / 'alias.grm'
        output.symlink_to(main)
        result = self.run_cli(main, '--expand-includes', '-o', output)
        assert result.returncode == 1
        assert main.read_text(encoding='utf-8') == 'S ::= ciao ;'

    def test_include_alias_is_expanded_once(self, tmp_path):
        vocab = tmp_path / 'vocab.grm'
        vocab.write_text('Word ::= ciao ;', encoding='utf-8')
        (tmp_path / 'alias.grm').symlink_to(vocab)
        main = tmp_path / 'main.grm'
        main.write_text('@include "vocab.grm"\n@include "alias.grm"\nS ::= Word ;',
                        encoding='utf-8')
        result = self.run_cli(main, '--expand-includes')
        assert result.returncode == 0
        assert result.stdout == 'Word ::= ciao ;\n\nS ::= Word ;'
        assert Polygen.from_file(str(main)).generate() == 'ciao'

    def test_failed_output_write(self, tmp_path):
        main = tmp_path / 'main.grm'
        main.write_text('S ::= ciao ;', encoding='utf-8')
        output = tmp_path / 'missing' / 'complete.grm'
        result = self.run_cli(main, '--expand-includes', '-o', output)
        assert result.returncode == 1
        assert result.stdout == ''
        assert 'Error:' in result.stderr
        assert not output.exists()

    @pytest.mark.parametrize('options', [
        ['--check'], ['--info'], ['-n', '1'], ['--count=1'],
        ['-s', 'S'], ['--start=S'], ['-S', '0'], ['--seed=0'],
    ])
    def test_incompatible_modes_even_with_default_values(self, tmp_path, options):
        main = tmp_path / 'main.grm'
        main.write_text('S ::= ciao ;', encoding='utf-8')
        output = tmp_path / 'complete.grm'
        result = self.run_cli(main, '--expand-includes', '-o', output, *options)
        assert result.returncode == 2
        assert 'incompatible' in result.stderr
        assert result.stdout == ''
        assert not output.exists()

    @pytest.mark.parametrize('args, message', [
        (['--expand-includes'], 'requires a grammar file'),
        (['-o', 'out.grm'], 'require --expand-includes'),
        (['--force'], 'require --expand-includes'),
        (['--expand-includes', 'main.grm', '--force'], 'requires --output'),
    ])
    def test_missing_arguments(self, args, message):
        result = self.run_cli(*args)
        assert result.returncode == 2
        assert message in result.stderr
        assert result.stdout == ''

    def test_missing_input(self, tmp_path):
        result = self.run_cli(tmp_path / 'missing.grm', '--expand-includes')
        assert result.returncode == 1
        assert result.stdout == ''
        assert 'Error:' in result.stderr


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
