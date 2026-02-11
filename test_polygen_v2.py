"""
Test delle nuove feature Polygen v2:
- Pesi numerici (#N)
- Etichette emesse (<-)
- @include
"""

import os
import random
import tempfile
import pytest
from polygen import Polygen, LexerError


@pytest.fixture
def seeded():
    random.seed(42)


class TestNumericWeights:
    """Test dei pesi numerici #N."""
    
    def test_basic_numeric_weight(self, seeded):
        """Test peso numerico base."""
        grammar = 'S ::= (#3 a | #1 b) ;'
        pg = Polygen(grammar)
        
        counts = {"a": 0, "b": 0}
        for _ in range(400):
            counts[pg.generate()] += 1
        
        # a dovrebbe essere ~75% (3/4), b ~25% (1/4)
        assert counts["a"] > counts["b"] * 2
    
    def test_mixed_weights(self, seeded):
        """Test pesi numerici misti con +/-."""
        # #5 e + dovrebbero coesistere (+ viene ignorato se c'è #)
        grammar = 'S ::= (#5 high | low) ;'
        pg = Polygen(grammar)
        
        counts = {"high": 0, "low": 0}
        for _ in range(600):
            counts[pg.generate()] += 1
        
        # high dovrebbe essere ~83% (5/6)
        assert counts["high"] > counts["low"] * 3
    
    def test_equal_numeric_weights(self, seeded):
        """Test pesi numerici uguali."""
        grammar = 'S ::= (#1 a | #1 b | #1 c) ;'
        pg = Polygen(grammar)
        
        counts = {"a": 0, "b": 0, "c": 0}
        for _ in range(300):
            counts[pg.generate()] += 1
        
        # Tutti circa uguali (~33%)
        assert all(80 < c < 120 for c in counts.values())


class TestEmittedLabels:
    """Test delle etichette emesse (<-)."""
    
    def test_basic_emit(self, seeded):
        """Test emissione base."""
        grammar = '''
        S ::= First Second ;
        First ::= a <-x | b <-y ;
        Second ::= x: one | y: two | fallback ;
        '''
        pg = Polygen(grammar)
        
        results = set()
        for _ in range(100):
            results.add(pg.generate())
        
        # a emette x -> Second può essere "one" o "fallback"
        # b emette y -> Second può essere "two" o "fallback"
        assert "a one" in results or "a fallback" in results
        assert "b two" in results or "b fallback" in results
        # Mai combinazioni incrociate (senza fallback)
        assert "a two" not in results
        assert "b one" not in results
    
    def test_multiple_emit(self, seeded):
        """Test emissione multipla."""
        grammar = '''
        S ::= Source Target ;
        Source ::= start <-a,b ;
        Target ::= a: ax | b: bx | c: cx ;
        '''
        pg = Polygen(grammar)
        
        results = set()
        for _ in range(100):
            results.add(pg.generate())
        
        # start emette sia a che b, quindi ax e bx sono validi
        assert "start ax" in results
        assert "start bx" in results
        assert "start cx" not in results  # c non è emesso
    
    def test_emit_forward_only(self, seeded):
        """Test che emissione influenzi solo elementi successivi."""
        # In questa grammatica, Second viene prima di First nell'ordine
        # ma First è definito prima - l'emissione di First NON deve 
        # influenzare Second che è già stato generato
        grammar = '''
        S ::= Second First ;
        First ::= a <-x | b ;
        Second ::= x: one | two ;
        '''
        pg = Polygen(grammar)
        
        # Second viene generato prima, quindi non vede l'emissione di First
        results = set()
        for _ in range(100):
            results.add(pg.generate())
        
        # Second può essere "one" o "two" indipendentemente da First
        assert any("one a" in r or "two a" in r for r in results)
        assert any("one b" in r or "two b" in r for r in results)


class TestInclude:
    """Test della direttiva @include."""
    
    def test_basic_include(self, seeded):
        """Test include base."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create included file
            vocab_path = os.path.join(tmpdir, "vocab.grm")
            with open(vocab_path, "w") as f:
                f.write("Word ::= hello | world ;")
            
            # Create main file
            main_path = os.path.join(tmpdir, "main.grm")
            with open(main_path, "w") as f:
                f.write('@include "vocab.grm"\nS ::= Word Word ;')
            
            pg = Polygen.from_file(main_path)
            
            results = set()
            for _ in range(50):
                results.add(pg.generate())
            
            assert results == {
                "hello hello", "hello world",
                "world hello", "world world"
            }
    
    def test_nested_include(self, seeded):
        """Test include annidato."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create deepest file
            deep_path = os.path.join(tmpdir, "deep.grm")
            with open(deep_path, "w") as f:
                f.write("Deep ::= bottom ;")
            
            # Create middle file that includes deep
            mid_path = os.path.join(tmpdir, "mid.grm")
            with open(mid_path, "w") as f:
                f.write('@include "deep.grm"\nMid ::= middle Deep ;')
            
            # Create main file that includes mid
            main_path = os.path.join(tmpdir, "main.grm")
            with open(main_path, "w") as f:
                f.write('@include "mid.grm"\nS ::= top Mid ;')
            
            pg = Polygen.from_file(main_path)
            
            assert pg.generate() == "top middle bottom"
    
    def test_include_cycle_prevention(self, seeded):
        """Test che cicli di include non causino loop infiniti."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create files that include each other
            a_path = os.path.join(tmpdir, "a.grm")
            b_path = os.path.join(tmpdir, "b.grm")
            
            with open(a_path, "w") as f:
                f.write('@include "b.grm"\nA ::= from_a ;')
            with open(b_path, "w") as f:
                f.write('@include "a.grm"\nB ::= from_b ;')
            
            # Should not hang - cycles are detected
            pg = Polygen.from_file(a_path)
            # Just verify it parsed without infinite loop


class TestNumericLabels:
    """Test che label numerici funzionino ancora (retrocompatibilità)."""
    
    def test_numeric_labels_in_selection(self, seeded):
        """Test label numerici nella selezione."""
        grammar = '''
        S ::= (a | b).1 ;
        '''
        pg = Polygen(grammar)
        
        # .1 seleziona label "1", ma nessuna produzione ha quel label
        # quindi dovrebbe restituire vuoto o errore
        results = set()
        for _ in range(20):
            results.add(pg.generate())
        
        # Senza label matching, entrambe le produzioni sono valide
        assert "a" in results or "b" in results
    
    def test_numeric_labels_in_production(self, seeded):
        """Test label numerici nelle produzioni."""
        grammar = '''
        S ::= Word.1 ;
        Word ::= 1: one | 2: two | 3: three ;
        '''
        pg = Polygen(grammar)
        
        results = set()
        for _ in range(30):
            results.add(pg.generate())
        
        # .1 seleziona solo la produzione con label "1"
        assert results == {"one"}
    
    def test_verb_conjugation(self, seeded):
        """Test coniugazione verbale con label numerici."""
        grammar = '''
        S ::= Conj.(S|P).sp ;
        Conj ::= (Pron Verb).1 | (Pron Verb).3 ;
        Pron ::= S: (1: "I" | 3: he) | P: (1: we | 3: they) ;
        Verb ::= eat (sp: (S: (3: ^ s))) ;
        '''
        pg = Polygen(grammar)
        
        generations = set()
        for _ in range(100):
            generations.add(pg.generate())
        
        # Forme attese
        assert "I eat" in generations
        assert "he eats" in generations
        assert "we eat" in generations
        assert "they eat" in generations


class TestBackwardCompatibility:
    """Test che le grammatiche esistenti funzionino ancora."""
    
    def test_basic_grammar(self, seeded):
        """Test grammatica base."""
        grammar = 'S ::= a | b | c ;'
        pg = Polygen(grammar)
        
        results = {pg.generate() for _ in range(30)}
        assert results == {"a", "b", "c"}
    
    def test_plus_minus_weights(self, seeded):
        """Test che +/- funzionino ancora."""
        grammar = 'S ::= ++ likely | unlikely ;'
        pg = Polygen(grammar)
        
        results = [pg.generate() for _ in range(100)]
        assert results.count("likely") > results.count("unlikely") * 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])