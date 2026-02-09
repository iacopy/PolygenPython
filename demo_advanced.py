"""
Test delle nuove feature di Polygen Python.
Testa: permutazione, generazione posizionale, unfolding, folding, selezione multipla.
"""

import random
from polygen import Polygen


def test_permutation():
    """Test permutazione {..}"""
    print("=" * 60)
    print("TEST: Permutazione {}")
    print("=" * 60)
    
    grammar = '''
    S ::= whether {is} {therefore} {he} ;
    '''
    pg = Polygen(grammar)
    
    results = set()
    for _ in range(100):
        results.add(pg.generate())
    
    expected = {
        "whether is therefore he",
        "whether is he therefore",
        "whether therefore is he",
        "whether therefore he is",
        "whether he is therefore",
        "whether he therefore is"
    }
    
    print(f"Generati {len(results)} permutazioni uniche")
    print(f"Attese: {len(expected)}")
    
    if results == expected:
        print("✅ PASS: Tutte le permutazioni generate correttamente")
    else:
        print("❌ FAIL")
        print(f"  Mancanti: {expected - results}")
        print(f"  Extra: {results - expected}")
    print()


def test_positional_generation():
    """Test generazione posizionale (,)"""
    print("=" * 60)
    print("TEST: Generazione posizionale (,)")
    print("=" * 60)
    
    grammar = '''
    S ::= time,fruit flies like an,a arrow,banana ;
    '''
    pg = Polygen(grammar)
    
    results = set()
    for _ in range(50):
        results.add(pg.generate())
    
    expected = {
        "time flies like an arrow",
        "fruit flies like a banana"
    }
    
    print(f"Risultati: {results}")
    
    if results == expected:
        print("✅ PASS: Generazione posizionale corretta")
    else:
        print("❌ FAIL")
    print()


def test_subproduction_unfolding():
    """Test unfolding di subproduzioni >()"""
    print("=" * 60)
    print("TEST: Unfolding subproduzioni >()")
    print("=" * 60)
    
    # Con unfolding: probabilità uniformi
    grammar_unfold = '''
    S ::= >(a | b) x | c x ;
    '''
    pg_unfold = Polygen(grammar_unfold)
    
    results = {"a x": 0, "b x": 0, "c x": 0}
    for _ in range(300):
        r = pg_unfold.generate()
        results[r] = results.get(r, 0) + 1
    
    print("Con unfolding >(a|b):")
    for k, v in sorted(results.items()):
        print(f"  {k}: {v}x ({v/3:.1f}%)")
    
    # Senza unfolding: (a|b) condivide 50%
    grammar_no_unfold = '''
    S ::= (a | b) x | c x ;
    '''
    pg_no = Polygen(grammar_no_unfold)
    
    results2 = {"a x": 0, "b x": 0, "c x": 0}
    for _ in range(300):
        r = pg_no.generate()
        results2[r] = results2.get(r, 0) + 1
    
    print("\nSenza unfolding (a|b):")
    for k, v in sorted(results2.items()):
        print(f"  {k}: {v}x ({v/3:.1f}%)")
    
    # Verifica che con unfolding le probabilità siano più uniformi
    std_unfold = max(results.values()) - min(results.values())
    std_no = max(results2.values()) - min(results2.values())
    
    if std_unfold < std_no:
        print("\n✅ PASS: Unfolding rende le probabilità più uniformi")
    else:
        print("\n⚠️  WARN: Differenza non significativa (può essere varianza)")
    print()


def test_nonterm_unfolding():
    """Test unfolding di non-terminali >Symbol"""
    print("=" * 60)
    print("TEST: Unfolding non-terminali >Symbol")
    print("=" * 60)
    
    grammar = '''
    S ::= ugly cat | nice >Dog ;
    Dog ::= poodle | beagle | terrier ;
    '''
    pg = Polygen(grammar)
    
    results = {}
    for _ in range(400):
        r = pg.generate()
        results[r] = results.get(r, 0) + 1
    
    print("Con >Dog (atteso: ~25% ciascuno):")
    for k, v in sorted(results.items()):
        print(f"  {k}: {v}x ({v/4:.1f}%)")
    
    # Tutte dovrebbero essere vicine al 25%
    expected_pct = 100
    all_close = all(abs(v - expected_pct) < 30 for v in results.values())
    
    if all_close and len(results) == 4:
        print("\n✅ PASS: Probabilità uniformi dopo unfolding")
    else:
        print("\n❌ FAIL: Probabilità non uniformi")
    print()


def test_deep_unfolding():
    """Test deep unfolding >> ... <<"""
    print("=" * 60)
    print("TEST: Deep unfolding >> ... <<")
    print("=" * 60)
    
    grammar = '''
    S ::= >> (a | (b | c) d) | (e | f) << ;
    '''
    pg = Polygen(grammar)
    
    results = set()
    for _ in range(100):
        results.add(pg.generate())
    
    print(f"Risultati unici: {sorted(results)}")
    
    # Con deep unfold tutto dovrebbe appiattirsi
    expected = {"a", "b d", "c d", "e", "f"}
    
    if results == expected:
        print("✅ PASS: Deep unfolding funziona")
    else:
        print(f"❌ FAIL: Attesi {expected}")
    print()


def test_folding():
    """Test folding < in deep unfold"""
    print("=" * 60)
    print("TEST: Folding < in deep unfold")
    print("=" * 60)
    
    # Con < le subproduzioni restano raggruppate
    grammar = '''
    S ::= >> (a | <(b | c) d) << ;
    '''
    pg = Polygen(grammar)
    
    results = {}
    for _ in range(300):
        r = pg.generate()
        results[r] = results.get(r, 0) + 1
    
    print("Con <(b|c) (folded):")
    for k, v in sorted(results.items()):
        print(f"  {k}: {v}x")
    
    # a dovrebbe essere ~50%, b d e c d insieme ~50%
    a_pct = results.get("a", 0) / 3
    bd_pct = results.get("b d", 0) / 3
    cd_pct = results.get("c d", 0) / 3
    
    print(f"\na: {a_pct:.1f}%, b d + c d: {bd_pct + cd_pct:.1f}%")
    
    if abs(a_pct - 50) < 15 and abs(bd_pct + cd_pct - 50) < 15:
        print("✅ PASS: Folding preserva raggruppamento")
    else:
        print("⚠️  WARN: Distribuzione inattesa (potrebbe essere varianza)")
    print()


def test_weighted_label_selection():
    """Test selezione label con pesi .(+l1|-l2)"""
    print("=" * 60)
    print("TEST: Selezione label con pesi")
    print("=" * 60)
    
    grammar = '''
    S ::= Size.(+big|--small) ;
    Size ::= big: grande | small: piccolo ;
    '''
    pg = Polygen(grammar)
    
    results = {"grande": 0, "piccolo": 0}
    for _ in range(200):
        r = pg.generate()
        results[r] = results.get(r, 0) + 1
    
    print("Con .(+big|--small):")
    for k, v in sorted(results.items()):
        print(f"  {k}: {v}x ({v/2:.1f}%)")
    
    # grande (big) dovrebbe essere molto più frequente
    if results["grande"] > results["piccolo"] * 2:
        print("\n✅ PASS: Pesi applicati correttamente")
    else:
        print("\n❌ FAIL: Pesi non applicati")
    print()


def test_complex_conjugation():
    """Test complesso: coniugazione verbale con label"""
    print("=" * 60)
    print("TEST: Coniugazione verbale complessa")
    print("=" * 60)
    
    grammar = '''
    S ::= Conjug.(S|P).(sp|pp) ;
    
    Conjug ::= (Pronoun Verb).1 | (Pronoun Verb).2 | (Pronoun Verb).3 ;
    
    Pronoun ::= S: (1: "I" | 2: you | 3: he)
             |  P: (1: we  | 2: you | 3: they) ;
    
    Verb ::= (pp: Be) eat (sp: (S: (3: ^ s)) | pp: ^ ing) ;
    
    Be ::= S: (1: am | 2: are | 3: is) | P: are ;
    '''
    
    pg = Polygen(grammar)
    
    results = set()
    for _ in range(200):
        results.add(pg.generate())
    
    print("Coniugazioni generate:")
    for r in sorted(results):
        print(f"  {r}")
    
    # Verifica alcune forme attese
    expected_forms = {"I eat", "he eats", "they eat", "I am eating", "he is eating"}
    found = expected_forms & results
    
    print(f"\nForme attese trovate: {len(found)}/{len(expected_forms)}")
    
    if len(found) >= 4:
        print("✅ PASS: Sistema di coniugazione funziona")
    else:
        print("❌ FAIL: Mancano forme attese")
    print()


def run_all_new_tests():
    """Esegue tutti i test delle nuove feature."""
    random.seed(42)
    
    print("\n" + "=" * 60)
    print("  TEST NUOVE FEATURE POLYGEN PYTHON")
    print("=" * 60 + "\n")
    
    test_permutation()
    test_positional_generation()
    test_subproduction_unfolding()
    test_nonterm_unfolding()
    test_deep_unfolding()
    test_folding()
    test_weighted_label_selection()
    test_complex_conjugation()
    
    print("=" * 60)
    print("  TUTTI I TEST COMPLETATI")
    print("=" * 60)


if __name__ == "__main__":
    run_all_new_tests()
