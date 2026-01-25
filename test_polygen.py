"""
Test suite for Polygen Python implementation.
Tests the main features based on examples from the PML specification.
"""

import random
from polygen import Polygen, Lexer, Parser, LexerError, ParserError, GeneratorError


def test_basic_grammar():
    """Test basic grammar with simple alternatives."""
    print("=" * 60)
    print("TEST: Basic grammar")
    print("=" * 60)
    
    grammar = '''
    S ::= an apple | a mango | an orange ;
    '''
    
    pg = Polygen(grammar)
    print("Grammar:", grammar.strip())
    print("\nGenerated (10x):")
    for _ in range(10):
        print(f"  {pg.generate()}")
    print()


def test_nonterminal_references():
    """Test grammar with non-terminal references."""
    print("=" * 60)
    print("TEST: Non-terminal references")
    print("=" * 60)
    
    grammar = '''
    S ::= the Animal is eating Fruit ;
    Animal ::= cat | dog ;
    Fruit ::= an apple | a mango ;
    '''
    
    pg = Polygen(grammar)
    print("Grammar:", grammar.strip())
    print("\nGenerated (10x):")
    for _ in range(10):
        print(f"  {pg.generate()}")
    print()


def test_quoted_terminals():
    """Test quoted terminal symbols."""
    print("=" * 60)
    print("TEST: Quoted terminals")
    print("=" * 60)
    
    grammar = '''
    S ::= a Pet called "Pet" ;
    Pet ::= cat | pig | dog ;
    '''
    
    pg = Polygen(grammar)
    print("Grammar:", grammar.strip())
    print("\nGenerated (5x):")
    for _ in range(5):
        print(f"  {pg.generate()}")
    print()


def test_subproductions():
    """Test subproductions with round brackets."""
    print("=" * 60)
    print("TEST: Subproductions")
    print("=" * 60)
    
    grammar = '''
    S ::= an (apple | orange) is on the (table | desk) ;
    '''
    
    pg = Polygen(grammar)
    print("Grammar:", grammar.strip())
    print("\nGenerated (10x):")
    for _ in range(10):
        print(f"  {pg.generate()}")
    print()


def test_optional_subproductions():
    """Test optional subproductions with square brackets."""
    print("=" * 60)
    print("TEST: Optional subproductions")
    print("=" * 60)
    
    grammar = '''
    S ::= an (apple | orange) is on the (table | desk) [in the (living | dining) room] ;
    '''
    
    pg = Polygen(grammar)
    print("Grammar:", grammar.strip())
    print("\nGenerated (10x):")
    for _ in range(10):
        print(f"  {pg.generate()}")
    print()


def test_concatenation():
    """Test concatenation operator ^."""
    print("=" * 60)
    print("TEST: Concatenation (^)")
    print("=" * 60)
    
    grammar = '''
    S ::= "(" ^ (apple | orange) ^ ")" ;
    '''
    
    pg = Polygen(grammar)
    print("Grammar:", grammar.strip())
    print("\nGenerated (5x):")
    for _ in range(5):
        print(f"  {pg.generate()}")
    
    # Test syllable assembly
    grammar2 = '''
    S ::= "I" Verb ^ e Verb ^ ing ;
    Verb ::= lov | hat ;
    '''
    
    pg2 = Polygen(grammar2)
    print("\nSyllable assembly grammar:")
    print("Grammar:", grammar2.strip())
    print("\nGenerated (5x):")
    for _ in range(5):
        print(f"  {pg2.generate()}")
    print()


def test_epsilon():
    """Test epsilon (empty production)."""
    print("=" * 60)
    print("TEST: Epsilon (_)")
    print("=" * 60)
    
    grammar = '''
    S ::= ball | _ ;
    '''
    
    pg = Polygen(grammar)
    print("Grammar:", grammar.strip())
    print("\nGenerated (10x):")
    for _ in range(10):
        result = pg.generate()
        print(f"  '{result}'" if result else "  (empty)")
    print()


def test_probability_modifiers():
    """Test probability modifiers + and -."""
    print("=" * 60)
    print("TEST: Probability modifiers (+/-)")
    print("=" * 60)
    
    grammar = '''
    S ::= the cat is eating (+ an apple |- an orange | some meat |-- a lemon) ;
    '''
    
    pg = Polygen(grammar)
    print("Grammar:", grammar.strip())
    print("\nGenerated (20x) - 'apple' should appear most often:")
    results = {}
    for _ in range(100):
        result = pg.generate()
        key = result.split("eating ")[1] if "eating " in result else result
        results[key] = results.get(key, 0) + 1
    
    for item, count in sorted(results.items(), key=lambda x: -x[1]):
        print(f"  {item}: {count}x")
    print()


def test_capitalization():
    """Test capitalization operator \\."""
    print("=" * 60)
    print("TEST: Capitalization (\\)")
    print("=" * 60)
    
    grammar = r'''
    S ::= \ smith (is | "." \) Eulogy ^ "." ;
    Eulogy ::= rather a smart man | really a gentleman ;
    '''
    
    pg = Polygen(grammar)
    print("Grammar:", grammar.strip())
    print("\nGenerated (10x):")
    for _ in range(10):
        print(f"  {pg.generate()}")
    print()


def test_labels_selection():
    """Test labels and selection."""
    print("=" * 60)
    print("TEST: Labels and selection")
    print("=" * 60)
    
    grammar = '''
    S ::= Verb.inf | Verb.ing ;
    Verb ::= (inf: to) (eat | drink | jump) (ing: ^ ing) ;
    '''
    
    pg = Polygen(grammar)
    print("Grammar:", grammar.strip())
    print("\nGenerated (10x):")
    for _ in range(10):
        print(f"  {pg.generate()}")
    print()


def test_strong_binding():
    """Test strong binding := (suspension)."""
    print("=" * 60)
    print("TEST: Strong binding (:=)")
    print("=" * 60)
    
    grammar = '''
    S ::= Fruit and Fruit ;
    Fruit := an apple | a mango | an orange ;
    '''
    
    pg = Polygen(grammar)
    print("Grammar:", grammar.strip())
    print("Note: Both 'Fruit' should generate the same value")
    print("\nGenerated (10x):")
    for _ in range(10):
        print(f"  {pg.generate()}")
    print()


def test_weak_binding():
    """Test weak binding ::= (closure)."""
    print("=" * 60)
    print("TEST: Weak binding (::=)")
    print("=" * 60)
    
    grammar = '''
    S ::= Fruit and Fruit ;
    Fruit ::= an apple | a mango | an orange ;
    '''
    
    pg = Polygen(grammar)
    print("Grammar:", grammar.strip())
    print("Note: Each 'Fruit' generates independently")
    print("\nGenerated (10x):")
    for _ in range(10):
        print(f"  {pg.generate()}")
    print()


def test_iteration():
    """Test iteration with +."""
    print("=" * 60)
    print("TEST: Iteration (+)")
    print("=" * 60)
    
    grammar = '''
    S ::= she is s ^ (o ^)+ pretty ;
    '''
    
    pg = Polygen(grammar)
    print("Grammar:", grammar.strip())
    print("\nGenerated (10x):")
    for _ in range(10):
        print(f"  {pg.generate()}")
    print()


def test_recursion():
    """Test recursive definitions."""
    print("=" * 60)
    print("TEST: Recursion")
    print("=" * 60)
    
    grammar = '''
    S ::= Digit [^ S] ;
    Digit ::= 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 ;
    '''
    
    pg = Polygen(grammar)
    print("Grammar:", grammar.strip())
    print("\nGenerated (10x):")
    for _ in range(10):
        print(f"  {pg.generate()}")
    print()


def test_comments():
    """Test comments."""
    print("=" * 60)
    print("TEST: Comments")
    print("=" * 60)
    
    grammar = '''
    S ::= apple | orange (* | banana *) | mango ;
    (* this is a comment too *)
    '''
    
    pg = Polygen(grammar)
    print("Grammar:", grammar.strip())
    print("Note: 'banana' should never appear")
    print("\nGenerated (10x):")
    for _ in range(10):
        print(f"  {pg.generate()}")
    print()


def test_local_scope():
    """Test local scoping with declarations inside subproductions."""
    print("=" * 60)
    print("TEST: Local scoping")
    print("=" * 60)
    
    grammar = '''
    S ::= i am (X := Adj; X ^ "," maybe X) and Adj ;
    Adj ::= handsome | nice ;
    '''
    
    pg = Polygen(grammar)
    print("Grammar:", grammar.strip())
    print("Note: X is fixed within subproduction, Adj varies")
    print("\nGenerated (10x):")
    for _ in range(10):
        print(f"  {pg.generate()}")
    print()


def test_complex_grammar():
    """Test a more complex grammar."""
    print("=" * 60)
    print("TEST: Complex grammar - Random story")
    print("=" * 60)
    
    grammar = '''
    I ::= "Random Story Generator v1.0" ;
    
    S ::= \ Setting ^ "," the Hero Action ^ "." [\ then ^ "," Consequence ^ "."] ;
    
    Setting ::= once upon a time | in a faraway land | long ago ;
    
    Hero ::= (a | the) (brave | young | old | wise) (knight | wizard | princess | farmer) ;
    
    Action ::= Verb (a | the) Object [Prep Place] ;
    
    Verb ::= found | discovered | lost | saved | defeated ;
    
    Object ::= magical sword | ancient book | golden crown | mysterious map | dragon ;
    
    Prep ::= in | near | under | behind ;
    
    Place ::= the castle | the forest | the mountain | the village ;
    
    Consequence ::= everyone lived happily ever after 
                  | the kingdom was saved 
                  | a new adventure began
                  | peace returned to the land ;
    '''
    
    pg = Polygen(grammar)
    print("Info:", pg.info())
    print("\nGenerated stories (5x):")
    print("-" * 40)
    for _ in range(5):
        print(f"  {pg.generate()}")
        print()


def run_all_tests():
    """Run all tests."""
    random.seed(42)  # For reproducibility
    
    test_basic_grammar()
    test_nonterminal_references()
    test_quoted_terminals()
    test_subproductions()
    test_optional_subproductions()
    test_concatenation()
    test_epsilon()
    test_probability_modifiers()
    test_capitalization()
    test_labels_selection()
    test_strong_binding()
    test_weak_binding()
    test_iteration()
    test_recursion()
    test_comments()
    test_local_scope()
    test_complex_grammar()
    
    print("=" * 60)
    print("ALL TESTS COMPLETED!")
    print("=" * 60)


if __name__ == '__main__':
    run_all_tests()
