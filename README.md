# Polygen Python

Un'implementazione in Python di [Polygen](http://polygen.org), il generatore di testo casuale basato su grammatiche.

È stato generato con Claude 4.5 Opus, con il prompt indicato suil file `prompt.txt`.
In pratica il prompt era:
```
Implementa il Polygen in Python, per lo meno le feature principali.
Ecco le specifiche:
<codice html>
```
Dove `<codice html>` è il codice presente a https://github.com/alvisespano/Polygen/blob/master/docs/polygen-spec_EN.html>

dalla riga `<html lang="en">` fino alla fine (quindi escluso il <!DOCTYPE html> e il commento della licenza).

## Caratteristiche implementate

Questa implementazione supporta le seguenti feature del linguaggio PML (Polygen Meta Language):

- ✅ Simboli terminali e non-terminali
- ✅ Produzioni con alternative separate da pipe (`|`)
- ✅ Subproduzioni tra parentesi tonde `(...)`
- ✅ Subproduzioni opzionali tra parentesi quadre `[...]` (50% probabilità)
- ✅ Concatenazione (`^`) per sopprimere gli spazi
- ✅ Epsilon (`_`) per produzioni vuote
- ✅ Modificatori di probabilità (`+` e `-`)
- ✅ Label e selezione (`.label`)
- ✅ Capitalizzazione (`\`)
- ✅ Commenti `(* ... *)`
- ✅ Binding debole `::=` (closure)
- ✅ Binding forte `:=` (suspension/assignment)
- ✅ Scoping locale con dichiarazioni nelle subproduzioni
- ✅ Iterazione `(...)+`
- ✅ Ricorsione

### Feature non ancora implementate

- ❌ Unfolding completo (`>` e `>>...<<`)
- ❌ Folding (`<`)
- ❌ Permutazione `{...}`
- ❌ Generazione posizionale (`,`)
- ❌ Selezione multipla con pesi `.( +l1 | -l2 )`

## Installazione

Non richiede dipendenze esterne. È sufficiente Python 3.7+.

```bash
# Copia il file polygen.py nella tua directory di lavoro
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

## Esempi

Vedi la directory `examples/` per grammatiche di esempio:

- `italiano.grm` - Generatore di frasi italiane semplici
- `italiano_avanzato.grm` - Con concordanza di genere
- `fortune.grm` - Generatore di fortune cookie

## Licenza

MIT License

## Credits

Basato sulle specifiche di Polygen Meta Language di Alvise Spanò.
