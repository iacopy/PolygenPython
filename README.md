# Polygen Python

Un'implementazione in Python di [Polygen](http://polygen.org), il generatore di testo casuale basato su grammatiche.

## Caratteristiche implementate

Questa implementazione supporta tutte le feature principali del linguaggio PML (Polygen Meta Language):

### Feature base
- ✅ Simboli terminali e non-terminali
- ✅ Produzioni con alternative separate da pipe (`|`)
- ✅ Subproduzioni tra parentesi tonde `(...)`
- ✅ Subproduzioni opzionali tra parentesi quadre `[...]` (50% probabilità)
- ✅ Concatenazione (`^`) per sopprimere gli spazi
- ✅ Epsilon (`_`) per produzioni vuote
- ✅ Modificatori di probabilità (`+` e `-`)
- ✅ Capitalizzazione (`\`)
- ✅ Commenti `(* ... *)`

### Label e selezione
- ✅ Label sulle produzioni (`label: production`)
- ✅ Selezione singola (`.label`)
- ✅ Selezione multipla con pesi `.(+l1|-l2|l3)`
- ✅ Reset selezione (`.`)

### Binding e scoping
- ✅ Binding debole `::=` (closure)
- ✅ Binding forte `:=` (suspension/assignment)
- ✅ Scoping locale con dichiarazioni nelle subproduzioni
- ✅ Ricorsione

### Feature avanzate
- ✅ Iterazione `(...)+`
- ✅ Permutazione `{...}`
- ✅ Generazione posizionale (`,`)
- ✅ Unfolding di subproduzioni tonde, opzionali e permutabili
- ✅ Unfolding di non-terminali `>Symbol`
- ✅ Deep unfolding `>>...<<`, inclusi i non-terminali
- ✅ Folding `<(...)` e `<Symbol`

## Feature non implementate

Le seguenti feature di **validazione statica** (Sezione 4 della spec) non sono implementate:

### Errori non rilevati

- Cyclic recursions (ricorsioni infinite)
- Recursive unfoldings (unfolding ricorsivi)
- Epsilon-productions che rendono la grammatica inutile

### Warning non implementati

- Livello 0: (nessuno attualmente)
- Livello 1: undefined `I` symbol, potential epsilon-productions, destructive selection
- Livello 2: useless permutation, useless unfolding
- Livello 3: unfolding a suspended symbol

Queste sono feature di robustezza e diagnostica, non di generazione. Il core della generazione è completo.

## Installazione

Non richiede dipendenze esterne per l'uso base. È sufficiente Python 3.7+.

```bash
# Copia il file polygen.py nella tua directory di lavoro
```

Per eseguire i test è necessario pytest:

```bash
pip install pytest
python -m pytest -v
```

## Utilizzo

### Da linea di comando

```bash
# Genera una frase da un file di grammatica
python polygen.py mia_grammatica.grm

# Genera 10 frasi
python polygen.py mia_grammatica.grm -n 10

# Mostra info sulla grammatica (simbolo I)
python polygen.py mia_grammatica.grm -i

# Usa un seed per risultati riproducibili
python polygen.py mia_grammatica.grm -S 42

# Parti da un simbolo diverso da S
python polygen.py mia_grammatica.grm -s MioSimbolo
```

### Come libreria Python

```python
from polygen import Polygen

# Da stringa
grammar = '''
S ::= hello | goodbye ;
'''
pg = Polygen(grammar)
print(pg.generate())  # "hello" o "goodbye"

# Da file
pg = Polygen.from_file('mia_grammatica.grm')
print(pg.generate())

# Genera da simbolo specifico
print(pg.generate(start_symbol='Frase'))

# Ottieni info (simbolo I)
print(pg.info())
```

## Sintassi delle grammatiche

### Definizioni base

```polygen
(* Questo è un commento *)

(* Definizione di un simbolo non-terminale *)
S ::= apple | orange | banana ;

(* I simboli che iniziano con maiuscola sono non-terminali *)
Frutto ::= mela | pera | banana ;

(* Le stringhe quotate permettono caratteri speciali *)
Simbolo ::= "Hello, World!" | "Ciao!" ;
```

### Subproduzioni

```polygen
(* Subproduzione tra parentesi tonde *)
S ::= an (apple | orange) is on the table ;

(* Subproduzione opzionale (50% probabilità) *)
S ::= i have [a very] big house ;
```

### Concatenazione

```polygen
(* ^ previene l'inserimento di spazi *)
S ::= "(" ^ word ^ ")" ;  (* produce "(word)" *)

(* Utile per costruire parole *)
S ::= walk ^ ing | run ^ ning ;  (* "walking" o "running" *)
```

### Epsilon (produzione vuota)

```polygen
S ::= something | _ ;  (* "something" o stringa vuota *)
```

### Probabilità

```polygen
(* + aumenta la probabilità, - la diminuisce *)
S ::= + likely | - unlikely | neutral ;
```

### Label e selezione

```polygen
(* Label per filtrare produzioni *)
Verbo ::= (inf: to) (eat | drink) (ing: ^ ing) ;

(* Selezione *)
S ::= Verbo.inf ;  (* "to eat" o "to drink" *)
S ::= Verbo.ing ;  (* "eating" o "drinking" *)
```

### Capitalizzazione

```polygen
(* \ capitalizza il prossimo terminale *)
S ::= \ hello world ;  (* "Hello world" *)
```

### Binding debole vs forte

```polygen
(* Binding debole: ogni uso genera indipendentemente *)
S ::= A and A ;
A ::= x | y ;  (* può produrre "x and y" *)

(* Binding forte: valore fissato al primo uso *)
S ::= B and B ;
B := x | y ;  (* produce solo "x and x" o "y and y" *)
```

### Scoping locale

```polygen
(* Dichiarazioni locali in una subproduzione *)
S ::= (X := a | b ; X and X) but A ;
A ::= a | b ;
(* X è fisso dentro la subproduzione, A varia *)
```

### Iterazione

```polygen
(* Ripete almeno una volta, poi 50% per ogni ripetizione *)
S ::= very (much ^ )+ better ;
(* "very much better", "very muchmuch better", etc. *)
```

### Permutazione

```polygen
(* Gli elementi tra {} vengono permutati casualmente *)
S ::= whether {is} {therefore} {he} ;
(* Genera tutte le permutazioni: "whether is therefore he",
   "whether therefore is he", etc. *)
```

### Generazione posizionale

```polygen
(* Elementi separati da virgola generano alternative sincronizzate *)
S ::= time,fruit flies like an,a arrow,banana ;
(* Produce: "time flies like an arrow" OPPURE "fruit flies like a banana" *)

(* Utile per concordanza di genere *)
S ::= he,she is a handsome,pretty act ^ or,ress ;
(* "he is a handsome actor" OPPURE "she is a pretty actress" *)
```

### Unfolding

L'operatore `>` appiattisce le alternative al livello della produzione
che lo contiene, modificandone la distribuzione di probabilità senza
cambiare i possibili risultati.

```polygen
(* Unfolding di subproduzioni tonde *)
S ::= >(walk | pass) through | look at | >(go | come | move) to ;
(* Tutti i verbi hanno la stessa probabilità. *)

(* Unfolding di un non-terminale *)
S ::= ugly cat | nice >Dog ;
Dog ::= poodle | beagle | terrier ;
(* Le quattro alternative risultano equiprobabili. *)

(* Un optional unfolded conserva anche l'alternativa epsilon. *)
S ::= >[a] x | y ;
(* Produce "a x", "x" oppure "y". *)

(* Le permutazioni vengono applicate prima dell'unfolding. *)
S ::= >{a | b} {c} ;
(* Produce "a c", "b c", "c a" oppure "c b". *)
```

Il deep unfolding `>>...<<` applica ricorsivamente l'unfolding al
contenuto. I non-terminali vengono espansi di un livello; le
subproduzioni contenute nelle loro definizioni restano raggruppate.

```polygen
S ::= >> A | b << ;
A ::= a | c ;
(* a, b e c sono equiprobabili. *)
```

Il prefisso `<` impedisce il deep unfolding dell'atomo seguente. Può
proteggere sia una subproduzione (`<(...)`) sia un non-terminale
(`<Symbol`).

```polygen
S ::= >> <A | b << ;
A ::= a | c ;
(* A e b restano due alternative: b ha probabilità 1/2,
   mentre a e c hanno probabilità 1/4 ciascuna. *)
```

### Selezione multipla con pesi

```polygen
(* Selezione di label multiple con probabilità diverse *)
S ::= Animal.(+big|--small) ;
Animal ::= big: elephant | big: whale | small: ant | small: bee ;
(* big è molto più probabile di small *)
```

## Esempi

Vedi la directory `examples/` per grammatiche di esempio:

- `italiano.grm` - Generatore di frasi italiane semplici
- `italiano_avanzato.grm` - Con concordanza di genere
- `fortune.grm` - Generatore di fortune cookie

## Credits

Basato sulle specifiche di Polygen Meta Language di Alvise Spanò.
