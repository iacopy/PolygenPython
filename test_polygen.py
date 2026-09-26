"""
Test suite per Polygen Python con pytest.
Ogni test genera abbastanza volte da coprire tutte le possibilità,
poi verifica con assert che siano state generate tutte le opzioni attese.
"""

import random
import subprocess
import sys
from pathlib import Path
import pytest
from polygen import Polygen, LexerError, ParserError, GeneratorError, ValidationError


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def seeded():
    """Fixture per avere risultati riproducibili."""
    random.seed(42)


@pytest.fixture
def high_iterations():
    """Numero di iterazioni per coprire tutte le possibilità."""
    return 100


# =============================================================================
# TEST FEATURE BASE
# =============================================================================

class TestBasicFeatures:
    """Test delle feature base di Polygen."""

    def test_basic_alternatives(self, seeded):
        """Test grammatica base con alternative semplici."""
        grammar = 'S ::= an apple | a mango | an orange ;'
        pg = Polygen(grammar)

        generations = {pg.generate() for _ in range(50)}

        assert generations == {"an apple", "a mango", "an orange"}

    def test_nonterminal_references(self, seeded):
        """Test riferimenti a simboli non-terminali."""
        grammar = '''
        S ::= the Animal is eating Fruit ;
        Animal ::= cat | dog ;
        Fruit ::= an apple | a mango ;
        '''
        pg = Polygen(grammar)

        generations = {pg.generate() for _ in range(50)}

        assert generations == {
            "the cat is eating an apple",
            "the cat is eating a mango",
            "the dog is eating an apple",
            "the dog is eating a mango",
        }

    def test_quoted_terminals(self, seeded):
        """Test simboli terminali quotati."""
        grammar = '''
        S ::= a Pet called "Pet" ;
        Pet ::= cat | dog ;
        '''
        pg = Polygen(grammar)

        generations = {pg.generate() for _ in range(30)}

        assert generations == {"a cat called Pet", "a dog called Pet"}

    def test_subproductions(self, seeded):
        """Test subproduzioni tra parentesi tonde."""
        grammar = 'S ::= an (apple | orange) is on the (table | desk) ;'
        pg = Polygen(grammar)

        generations = {pg.generate() for _ in range(50)}

        assert generations == {
            "an apple is on the table",
            "an apple is on the desk",
            "an orange is on the table",
            "an orange is on the desk",
        }

    def test_optional_subproductions(self, seeded):
        """Test subproduzioni opzionali tra parentesi quadre."""
        grammar = 'S ::= hello [beautiful] world ;'
        pg = Polygen(grammar)

        generations = {pg.generate() for _ in range(50)}

        assert generations == {"hello world", "hello beautiful world"}

    def test_optional_with_alternatives(self, seeded):
        """Test opzionale con alternative interne."""
        grammar = 'S ::= a [very | quite] big house ;'
        pg = Polygen(grammar)

        generations = {pg.generate() for _ in range(50)}

        assert generations == {
            "a big house",
            "a very big house",
            "a quite big house",
        }


class TestConcatenation:
    """Test dell'operatore di concatenazione ^."""

    def test_basic_concatenation(self, seeded):
        """Test concatenazione base."""
        grammar = 'S ::= "(" ^ word ^ ")" ;'
        pg = Polygen(grammar)

        assert pg.generate() == "(word)"

    def test_syllable_assembly(self, seeded):
        """Test assemblaggio sillabe."""
        grammar = '''
        S ::= Verb ^ ing ;
        Verb ::= walk | talk | jump ;
        '''
        pg = Polygen(grammar)

        generations = {pg.generate() for _ in range(30)}

        # walk+ing=walking, talk+ing=talking, jump+ing=jumping
        assert generations == {"walking", "talking", "jumping"}

    def test_prefix_suffix(self, seeded):
        """Test con prefisso e suffisso."""
        grammar = '''
        S ::= "I" Verb ^ e Verb ^ ing ;
        Verb ::= lov | hat ;
        '''
        pg = Polygen(grammar)

        generations = {pg.generate() for _ in range(50)}

        assert generations == {
            "I love loving",
            "I love hating",
            "I hate loving",
            "I hate hating",
        }


class TestEpsilon:
    """Test della produzione vuota epsilon (_)."""

    def test_epsilon_alternative(self, seeded):
        """Test epsilon come alternativa."""
        grammar = 'S ::= ball | _ ;'
        pg = Polygen(grammar)

        generations = {pg.generate() for _ in range(50)}

        assert generations == {"ball", ""}

    def test_epsilon_equivalent_to_optional(self, seeded):
        """Test che epsilon sia equivalente a opzionale."""
        grammar1 = 'S ::= (ball | _) ;'
        grammar2 = 'S ::= [ball] ;'

        pg1 = Polygen(grammar1)
        pg2 = Polygen(grammar2)

        gen1 = {pg1.generate() for _ in range(50)}
        gen2 = {pg2.generate() for _ in range(50)}

        assert gen1 == gen2 == {"ball", ""}


class TestCapitalization:
    """Test dell'operatore di capitalizzazione \\."""

    def test_basic_capitalization(self, seeded):
        """Test capitalizzazione base."""
        grammar = r'S ::= \ hello world ;'
        pg = Polygen(grammar)

        assert pg.generate() == "Hello world"

    def test_capitalization_after_period(self, seeded):
        """Test capitalizzazione dopo punto."""
        grammar = r'''
        S ::= \ word (is | "." \) Adj ;
        Adj ::= nice | good ;
        '''
        pg = Polygen(grammar)

        generations = {pg.generate() for _ in range(50)}

        assert generations == {
            "Word is nice",
            "Word is good",
            "Word . Nice",
            "Word . Good",
        }


class TestComments:
    """Test dei commenti (* ... *)."""

    def test_comment_removal(self, seeded):
        """Test che i commenti vengano ignorati."""
        grammar = '''
        S ::= apple | orange (* | banana *) | mango ;
        (* this is ignored *)
        '''
        pg = Polygen(grammar)

        generations = {pg.generate() for _ in range(50)}

        assert "banana" not in generations
        assert generations == {"apple", "orange", "mango"}


# =============================================================================
# TEST PROBABILITA'
# =============================================================================

class TestProbabilityModifiers:
    """Test dei modificatori di probabilità + e -."""

    def test_plus_increases_probability(self, seeded):
        """Test che + aumenti la probabilità."""
        grammar = 'S ::= ++ likely | unlikely ;'
        pg = Polygen(grammar)

        results = [pg.generate() for _ in range(100)]
        likely_count = results.count("likely")

        # likely dovrebbe essere circa 3x più frequente
        assert likely_count > 60

    def test_minus_decreases_probability(self, seeded):
        """Test che - diminuisca la probabilità."""
        grammar = 'S ::= normal | -- rare ;'
        pg = Polygen(grammar)

        results = [pg.generate() for _ in range(100)]
        rare_count = results.count("rare")

        # rare dovrebbe essere circa 1/3
        assert rare_count < 40

    def test_combined_modifiers(self, seeded):
        """Test combinazione di + e -."""
        grammar = 'S ::= + high | medium | - low ;'
        pg = Polygen(grammar)

        counts = {"high": 0, "medium": 0, "low": 0}
        for _ in range(300):
            counts[pg.generate()] += 1

        # high > medium > low
        assert counts["high"] > counts["medium"] > counts["low"]


# =============================================================================
# TEST LABELS E SELEZIONE
# =============================================================================

class TestLabelsAndSelection:
    """Test delle label e della selezione."""

    def test_basic_label_selection(self, seeded):
        """Test selezione base con label."""
        grammar = '''
        S ::= Verb.inf | Verb.ing ;
        Verb ::= (inf: to) (eat | drink) (ing: ^ ing) ;
        '''
        pg = Polygen(grammar)

        generations = {pg.generate() for _ in range(50)}

        assert generations == {
            "to eat", "to drink",
            "eating", "drinking",
        }

    def test_nested_labels(self, seeded):
        """Test label annidate."""
        grammar = '''
        S ::= Word.m | Word.f ;
        Word ::= m: uomo | f: donna ;
        '''
        pg = Polygen(grammar)

        generations = {pg.generate() for _ in range(50)}

        assert generations == {"uomo", "donna"}

    def test_selection_reset(self, seeded):
        """Test reset della selezione con punto singolo."""
        grammar = '''
        S ::= A.x B. C ;
        A ::= x: ax | y: ay ;
        B ::= x: bx | y: by ;
        C ::= x: cx | y: cy ;
        '''
        pg = Polygen(grammar)

        generations = {pg.generate() for _ in range(100)}

        # A seleziona x, B resetta, C non ha selezione attiva
        # Quindi: A=ax, B=bx o by, C=cx o cy
        for g in generations:
            assert g.startswith("ax")

    def test_multiple_label_selection(self, seeded):
        """Test selezione multipla .(l1|l2)."""
        grammar = '''
        S ::= Animal.(big|small) ;
        Animal ::= big: elephant | big: whale | small: ant | small: bee ;
        '''
        pg = Polygen(grammar)

        generations = {pg.generate() for _ in range(100)}

        assert generations == {"elephant", "whale", "ant", "bee"}

    def test_weighted_label_selection(self, seeded):
        """Test selezione label con pesi."""
        grammar = '''
        S ::= Size.(++big|--small) ;
        Size ::= big: grande | small: piccolo ;
        '''
        pg = Polygen(grammar)

        results = [pg.generate() for _ in range(100)]
        grande_count = results.count("grande")

        # grande (big) dovrebbe essere molto più frequente
        assert grande_count > 70


# =============================================================================
# TEST BINDING
# =============================================================================

class TestBinding:
    """Test del binding debole (::=) e forte (:=)."""

    def test_weak_binding_independent(self, seeded):
        """Test che binding debole generi indipendentemente."""
        grammar = '''
        S ::= Fruit and Fruit ;
        Fruit ::= apple | orange ;
        '''
        pg = Polygen(grammar)

        generations = {pg.generate() for _ in range(50)}

        # Dovrebbe generare tutte le combinazioni
        assert generations == {
            "apple and apple",
            "apple and orange",
            "orange and apple",
            "orange and orange",
        }

    def test_strong_binding_same_value(self, seeded):
        """Test che binding forte produca stesso valore."""
        grammar = '''
        S ::= Fruit and Fruit ;
        Fruit := apple | orange ;
        '''
        pg = Polygen(grammar)

        generations = {pg.generate() for _ in range(50)}

        # Dovrebbe generare solo valori uguali
        assert generations == {"apple and apple", "orange and orange"}

    def test_strong_binding_shared_across_scopes(self, seeded):
        """Il valore sospeso è condiviso da tutte le occorrenze nello scope."""
        grammar = '''
        S ::= (Fruit) and Other ;
        Other ::= Fruit ;
        Fruit := apple | orange ;
        '''
        pg = Polygen(grammar)

        generations = {pg.generate() for _ in range(50)}

        assert generations == {"apple and apple", "orange and orange"}

    def test_strong_binding_with_recursion(self, seeded):
        """Test binding forte con ricorsione."""
        grammar = '''
        S ::= A A ;
        A := a | a ^ A ;
        '''
        pg = Polygen(grammar)

        for _ in range(20):
            result = pg.generate()
            parts = result.split()
            # Le due parti devono essere uguali
            assert len(parts) == 2
            assert parts[0] == parts[1]


class TestLocalScoping:
    """Test dello scoping locale."""

    def test_local_declarations(self, seeded):
        """Test dichiarazioni locali in subproduzioni."""
        grammar = '''
        S ::= (X := a | b; X and X) or Outer ;
        Outer ::= a | b ;
        '''
        pg = Polygen(grammar)

        generations = {pg.generate() for _ in range(50)}

        # X è locale e forte, Outer è globale
        expected = {"a and a or a", "a and a or b", "b and b or a", "b and b or b"}
        assert generations == expected

    def test_shadowing(self, seeded):
        """Test shadowing di simboli."""
        grammar = '''
        S ::= (X ::= inner; X) and X ;
        X ::= outer ;
        '''
        pg = Polygen(grammar)

        generations = {pg.generate() for _ in range(20)}

        assert generations == {"inner and outer"}


# =============================================================================
# TEST ITERAZIONE E RICORSIONE
# =============================================================================

class TestIteration:
    """Test dell'iterazione (...)+."""

    def test_basic_iteration(self, seeded):
        """Test iterazione base."""
        grammar = 'S ::= (a ^)+ b ;'
        pg = Polygen(grammar)

        generations = {pg.generate() for _ in range(50)}

        # Deve generare ab, aab, aaab, etc.
        assert "ab" in generations
        assert all(g.endswith("b") and g[:-1].replace("a", "") == ""
                   for g in generations)

    def test_iteration_with_alternatives(self, seeded):
        """Test iterazione con alternative."""
        grammar = 'S ::= (a | b)+ ;'
        pg = Polygen(grammar)

        generations = {pg.generate() for _ in range(100)}

        # Deve generare combinazioni di a e b
        assert "a" in generations
        assert "b" in generations
        # Almeno alcune combinazioni
        assert any(len(g.split()) > 1 for g in generations)


class TestRecursion:
    """Test della ricorsione."""

    @pytest.mark.parametrize('grammar, symbol', [
        ('S ::= S | A ; A ::= B ; B ::= S | A ;', 'B'),
        ('S ::= a | A ;\nA ::= B ;\nB ::= A ;', 'B'),
        ('S ::= (A ::= A ; A) ;', 'A'),
        ('S ::= (A ::= A ; A) ; A ::= end ;', 'A'),
        ('S ::= (A ::= end ; A) ; A ::= A ;', 'A'),
        ('S ::= (A ::= B ; B ::= A ; A) ;', 'B'),
    ])
    def test_closed_recursion_is_rejected(self, grammar, symbol):
        with pytest.raises(ValidationError, match=f'Non-terminating recursion: {symbol}'):
            Polygen(grammar)

    def test_closed_subcycle_reports_its_declaration(self):
        with pytest.raises(ValidationError, match=r'3:1: Non-terminating recursion: B'):
            Polygen('S ::= a | A ;\nA ::= B ;\nB ::= A ;')

    def test_local_cycle_reports_local_position(self):
        with pytest.raises(ValidationError, match=r'1:8: Non-terminating recursion: A'):
            Polygen('S ::= (A ::= A ; A) ;')

    @pytest.mark.parametrize('grammar', [
        'S ::= fine | ancora S ;',
        'S ::= A ; A ::= fine | ancora A ;',
        'S ::= [S] ;',
        'S ::= (A ::= fine | ancora A ; A) ;',
        'S ::= (A ::= local ; A) ; A ::= global | A ;',
        'S ::= _ ;',
    ])
    def test_recursion_with_exit_is_valid(self, grammar):
        Polygen(grammar)

    def test_basic_recursion(self, seeded):
        """Test ricorsione base."""
        grammar = '''
        S ::= Digit [^ S] ;
        Digit ::= 0 | 1 | 2 ;
        '''
        pg = Polygen(grammar)

        generations = set()
        for _ in range(100):
            result = pg.generate()
            generations.add(result)
            # Verifica che sia composto solo da cifre
            assert all(c in "012" for c in result)

        # Deve generare numeri di varie lunghezze
        lengths = {len(g) for g in generations}
        assert len(lengths) > 1


# =============================================================================
# TEST PERMUTAZIONE
# =============================================================================

class TestPermutation:
    """Test della permutazione {...}."""

    def test_basic_permutation(self, seeded):
        """Test permutazione base."""
        grammar = 'S ::= {a} {b} {c} ;'
        pg = Polygen(grammar)

        generations = {pg.generate() for _ in range(100)}

        # Tutte e 6 le permutazioni
        expected = {
            "a b c", "a c b", "b a c", "b c a", "c a b", "c b a"
        }
        assert generations == expected

    def test_permutation_with_fixed(self, seeded):
        """Test permutazione con elementi fissi."""
        grammar = 'S ::= start {x} {y} end ;'
        pg = Polygen(grammar)

        generations = {pg.generate() for _ in range(50)}

        assert generations == {"start x y end", "start y x end"}

    def test_nested_permutation(self, seeded):
        """Test permutazione con contenuto interno."""
        grammar = 'S ::= {(a | b)} {c} ;'
        pg = Polygen(grammar)

        generations = {pg.generate() for _ in range(50)}

        assert generations == {"a c", "b c", "c a", "c b"}


# =============================================================================
# TEST GENERAZIONE POSIZIONALE
# =============================================================================

class TestPositionalGeneration:
    """Test della generazione posizionale (,)."""

    def test_basic_positional(self, seeded):
        """Test generazione posizionale base."""
        grammar = 'S ::= a,b x,y ;'
        pg = Polygen(grammar)

        generations = {pg.generate() for _ in range(50)}

        # a va con x, b va con y
        assert generations == {"a x", "b y"}

    def test_time_flies(self, seeded):
        """Test esempio classico time/fruit flies."""
        grammar = 'S ::= time,fruit flies like an,a arrow,banana ;'
        pg = Polygen(grammar)

        generations = {pg.generate() for _ in range(50)}

        assert generations == {
            "time flies like an arrow",
            "fruit flies like a banana"
        }

    def test_gender_agreement(self, seeded):
        """Test concordanza di genere."""
        grammar = 'S ::= il,la bell ^ o,a gatt ^ o,a ;'
        pg = Polygen(grammar)

        generations = {pg.generate() for _ in range(50)}

        assert generations == {"il bello gatto", "la bella gatta"}


# =============================================================================
# TEST UNFOLDING
# =============================================================================

class TestUnfolding:
    """Test dell'unfolding (>)."""

    @pytest.mark.parametrize('grammar, location', [
        ('S ::= >S ;', '1:8'),
        ('S ::= >A ;\nA ::= >B ;\nB ::= >S ;', '3:8'),
        ('S ::= (A ::= >A ; A) ;', '1:15'),
        ('S ::= (A ::= >B ; B ::= >A ; A) ;', '1:26'),
        ('S ::= >> A << ; A ::= >S ;', '1:24'),
        ('S ::= >> (A ::= S ; A) << ;', '1:17'),
    ])
    def test_recursive_unfolding_is_rejected(self, grammar, location):
        with pytest.raises(ValidationError, match=f'{location}: Recursive unfolding'):
            Polygen(grammar)

    def test_ordinary_recursion_is_not_unfolding(self):
        pg = Polygen('S ::= end | A ; A ::= S ;')
        assert pg.generate(max_recursion=10) == 'end'

    def test_local_unfolding_uses_local_declaration(self):
        pg = Polygen('S ::= (A ::= local ; >A) ; A ::= global ;')
        assert pg.generate() == 'local'

    def test_shadowed_global_is_not_a_recursive_unfolding(self):
        pg = Polygen('S ::= (A ::= local ; >A) ; A ::= >S ;')
        assert pg.generate() == 'local'

    def test_global_unfolding_keeps_its_lexical_scope(self):
        pg = Polygen('S ::= (X ::= local ; >A) ; A ::= >X ; X ::= global ;')
        assert pg.generate() == 'global'

    def test_folding_blocks_deep_unfolding_cycle(self):
        pg = Polygen('S ::= >> <A << ; A ::= >S | end ;')
        assert pg.generate(max_recursion=100) == 'end'

    def test_subproduction_unfolding(self, seeded):
        """Test unfolding di subproduzioni."""
        grammar = 'S ::= >(a | b) | c ;'
        pg = Polygen(grammar)

        counts = {"a": 0, "b": 0, "c": 0}
        for _ in range(300):
            counts[pg.generate()] += 1

        # Con unfolding, a, b, c dovrebbero essere circa uguali (~33%)
        assert all(80 < c < 120 for c in counts.values())

    def test_nonterm_unfolding(self, seeded):
        """Test unfolding di non-terminali."""
        grammar = '''
        S ::= x | >Y ;
        Y ::= a | b | c ;
        '''
        pg = Polygen(grammar)

        counts = {"x": 0, "a": 0, "b": 0, "c": 0}
        for _ in range(400):
            counts[pg.generate()] += 1

        # x, a, b, c dovrebbero essere circa uguali (~25%)
        assert all(70 < c < 130 for c in counts.values())

    def test_unfolding_preserves_context(self, seeded):
        """Test che unfolding preservi il contesto."""
        grammar = '''
        S ::= prefix >(a | b) suffix ;
        '''
        pg = Polygen(grammar)

        generations = {pg.generate() for _ in range(50)}

        assert generations == {"prefix a suffix", "prefix b suffix"}

    def test_optional_unfolding_preserves_epsilon(self, seeded):
        """Un optional unfolded mantiene l'alternativa epsilon."""
        grammar = 'S ::= >[a] x | y ;'
        pg = Polygen(grammar)

        generations = {pg.generate() for _ in range(100)}

        assert generations == {"a x", "x", "y"}

    def test_permutation_happens_before_unfolding(self, seeded):
        """Una subproduzione permutabile viene permutata prima dell'unfolding."""
        grammar = 'S ::= >{a | b} {c} ;'
        pg = Polygen(grammar)

        generations = {pg.generate() for _ in range(100)}

        assert generations == {"a c", "b c", "c a", "c b"}


class TestDeepUnfolding:
    """Test del deep unfolding (>> ... <<)."""

    def test_basic_deep_unfold(self, seeded):
        """Test deep unfolding base."""
        grammar = 'S ::= >> (a | (b | c)) << ;'
        pg = Polygen(grammar)

        generations = {pg.generate() for _ in range(50)}

        # Tutto appiattito
        assert generations == {"a", "b", "c"}

    def test_deep_unfold_nested(self, seeded):
        """Test deep unfolding annidato."""
        grammar = 'S ::= >> x (a | (b | c) y) << ;'
        pg = Polygen(grammar)

        generations = {pg.generate() for _ in range(50)}

        assert generations == {"x a", "x b y", "x c y"}

    def test_folding_prevents_unfold(self, seeded):
        """Test che < prevenga l'unfolding."""
        grammar = 'S ::= >> (a | <(b | c)) << ;'
        pg = Polygen(grammar)

        counts = {"a": 0, "b": 0, "c": 0}
        for _ in range(300):
            counts[pg.generate()] += 1

        # a dovrebbe essere ~50%, b+c ~50%
        assert 120 < counts["a"] < 180
        assert 120 < counts["b"] + counts["c"] < 180

    def test_deep_unfold_expands_nonterminal(self, seeded):
        """Il deep unfolding espande i non-terminali di un livello."""
        grammar = 'S ::= >> A | b << ; A ::= a | c ;'
        pg = Polygen(grammar)

        counts = {"a": 0, "b": 0, "c": 0}
        for _ in range(600):
            counts[pg.generate()] += 1

        # Dopo l'unfolding a, b e c sono alternative equiprobabili.
        assert all(160 < count < 240 for count in counts.values())

    def test_folding_prevents_nonterminal_unfold(self, seeded):
        """<Symbol impedisce l'espansione del simbolo nel deep unfolding."""
        grammar = 'S ::= >> <A | b << ; A ::= a | c ;'
        pg = Polygen(grammar)

        counts = {"a": 0, "b": 0, "c": 0}
        for _ in range(600):
            counts[pg.generate()] += 1

        # A e b restano due alternative; a e c dividono la quota di A.
        assert 250 < counts["b"] < 350
        assert 100 < counts["a"] < 200
        assert 100 < counts["c"] < 200


# =============================================================================
# TEST ERRORI
# =============================================================================

class TestErrors:
    """Test della gestione errori."""

    def test_undefined_symbol(self):
        """Un simbolo non definito viene trovato prima di generare."""
        with pytest.raises(ValidationError, match=r"1:7: Undefined symbol: A"):
            Polygen('S ::= A ;')

    def test_undefined_symbol_in_unselected_branch(self):
        with pytest.raises(ValidationError, match=r"2:5: Undefined symbol: Missing"):
            Polygen('S ::= ok |\n    Missing ;')

    def test_undefined_symbol_in_local_declaration(self):
        with pytest.raises(ValidationError, match=r"1:14: Undefined symbol: Missing"):
            Polygen('S ::= (X ::= Missing ; X) ;')

    def test_duplicate_global_declaration(self):
        with pytest.raises(ValidationError, match=r"2:1: Duplicate symbol: S"):
            Polygen('S ::= first ;\nS ::= second ;')

    def test_duplicate_local_declaration(self):
        with pytest.raises(ValidationError, match=r"1:18: Duplicate symbol: X"):
            Polygen('S ::= (X ::= a ; X ::= b ; X) ;')

    def test_local_shadowing_is_valid(self):
        pg = Polygen('S ::= (X ::= inner ; X) X ; X ::= outer ;')
        assert pg.generate() == 'inner outer'

    def test_custom_start_symbol(self):
        pg = Polygen('Other ::= hello ;')
        assert pg.generate('Other') == 'hello'
        with pytest.raises(ValidationError, match="Undefined start symbol: S"):
            pg.generate()

    def test_check_command(self, tmp_path):
        grammar = tmp_path / 'sample.grm'
        grammar.write_text('S ::= a ;', encoding='utf-8')
        result = subprocess.run([sys.executable, str(Path(__file__).with_name('polygen.py')),
                                 str(grammar), '--check'], capture_output=True, text=True)
        assert result.returncode == 0
        assert result.stdout == 'Grammar references and definitions are valid\n'

        grammar.write_text('S ::= a | Missing ;', encoding='utf-8')
        result = subprocess.run([sys.executable, str(Path(__file__).with_name('polygen.py')),
                                 str(grammar), '--check'], capture_output=True, text=True)
        assert result.returncode == 1
        assert 'Undefined symbol: Missing' in result.stderr
        assert result.stdout == ''

    def test_check_rejects_recursive_unfolding(self, tmp_path):
        grammar = tmp_path / 'recursive.grm'
        grammar.write_text('S ::= >A ;\nA ::= >S ;', encoding='utf-8')
        command = [sys.executable, str(Path(__file__).with_name('polygen.py')), str(grammar)]
        for args in (['--check'], ['-n', '1']):
            result = subprocess.run(command + args, capture_output=True, text=True, timeout=5)
            assert result.returncode == 1
            assert 'Recursive unfolding: S' in result.stderr
            assert result.stdout == ''

        result = subprocess.run([sys.executable, str(Path(__file__).with_name('polygen.py')),
                                 str(grammar), '-n', '5'], capture_output=True, text=True)
        assert result.returncode == 1
        assert result.stdout == ''

    def test_check_rejects_nonterminating_generation(self, tmp_path):
        grammar = tmp_path / 'cycle.grm'
        grammar.write_text('S ::= a | A ;\nA ::= B ;\nB ::= A ;', encoding='utf-8')
        command = [sys.executable, str(Path(__file__).with_name('polygen.py')), str(grammar)]
        for args in (['--check'], ['-n', '1']):
            result = subprocess.run(command + args, capture_output=True, text=True, timeout=5)
            assert result.returncode == 1
            assert 'Non-terminating recursion: B' in result.stderr
            assert result.stdout == ''

    def test_lexer_error_illegal_char(self):
        """Test errore lessicale per carattere illegale."""
        grammar = 'S ::= hello § world ;'

        with pytest.raises(LexerError, match="Illegal character"):
            Polygen(grammar)

    def test_parser_error_unexpected_token(self):
        """Test errore sintattico per token inatteso."""
        grammar = 'S ::= a b ::= c ;'  # ::= nel posto sbagliato

        with pytest.raises(ParserError):
            Polygen(grammar)

    def test_mismatched_positional_groups(self):
        """Test errore per gruppi posizionali di dimensioni diverse."""
        grammar = 'S ::= a,b,c x,y ;'

        # L'errore viene sollevato durante il preprocessing (costruzione)
        with pytest.raises(GeneratorError, match="same size"):
            Polygen(grammar)


# =============================================================================
# TEST INFO SYMBOL
# =============================================================================

class TestInfoSymbol:
    """Test del simbolo I per info."""

    def test_info_symbol(self):
        """Test generazione da simbolo I."""
        grammar = '''
        I ::= "Test Grammar v1.0" ;
        S ::= hello ;
        '''
        pg = Polygen(grammar)

        assert pg.info() == "Test Grammar v1.0"

    def test_info_undefined(self):
        """Test info quando I non è definito."""
        grammar = 'S ::= hello ;'
        pg = Polygen(grammar)

        assert pg.info() == ""


# =============================================================================
# TEST INTEGRAZIONE
# =============================================================================

class TestIntegration:
    """Test di integrazione con grammatiche complesse."""

    def test_verb_conjugation(self, seeded):
        """Test coniugazione verbale complessa."""
        grammar = '''
        S ::= Conj.(S|P).sp ;
        Conj ::= (Pron Verb).1 | (Pron Verb).3 ;
        Pron ::= S: (1: "I" | 3: he) | P: (1: we | 3: they) ;
        Verb ::= eat (sp: (S: (3: ^ s))) ;
        '''
        pg = Polygen(grammar)

        generations = {pg.generate() for _ in range(100)}

        # Verifica alcune forme attese
        assert "I eat" in generations
        assert "he eats" in generations
        assert "we eat" in generations
        assert "they eat" in generations

    def test_story_generator(self, seeded):
        """Test generatore di storie."""
        grammar = r'''
        S ::= \ Setting ^ "," the Hero Action ^ "." ;
        Setting ::= once upon a time | long ago ;
        Hero ::= (brave | wise) (knight | wizard) ;
        Action ::= found the treasure | saved the kingdom ;
        '''
        pg = Polygen(grammar)

        for _ in range(10):
            result = pg.generate()
            # Verifica struttura base
            assert result[0].isupper()  # Capitalizzato
            assert result.endswith(".")  # Termina con punto
            assert "the" in result.lower()


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
