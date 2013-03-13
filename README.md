mv-smart
=========
Smart file renaming

### SYNOPSIS
    mv-smart.py [--simple] -n pattern [-f] FILE [FILE ...]
    mv-smart.py [--simple] -b pattern [-e pattern] [-f] FILE [FILE ...]
    mv-smart.py --regex -n pattern [-f] FILE [FILE ...]
    mv-smart.py --regex -b pattern [-e pattern] [-f] FILE [FILE ...]

### DESCRIPTION

The `mv-smart.py` utility renames listed files using two kind of patterns.

If you specify `-n` argument, __pattern__ presents whole file name (base and extension).

If you specify `-b` argument, __pattern__ presents only file base name (extension
will not be renamed).

If you specify `-e` argument, __pattern__ presents only file extension (base will not
be renamed).

If you specify both `-b` and `-e` argument, you can set pattern for base name and
extension separately.

Files won't be ranamed until '-f' argument is specified.

### PATTERNS TYPES

**Simple patterns**

If you specify `--simple` argument or omit any patterns types arguments, you can
use next special sequences in 'pattern':

    '[n]', '[n3-7]'         - insert file name without extension, or substring with range
                              '3-7' based on file name without extension
    '[e]', '[e1-3]'         - insert file extension, or substring with range '3-7' based
                              on file extension
    '[ne]', '[ne1-3]'       - insert file name with extension, or substring with range
                              '1-3' based on file name with extension
    '[n3]', '[e3]', '[ne3]' - insert corresponding string starting from 3th character
    '[c]', '[c1,2,5]'       - insert counter. Default params are: start from 1
                              with step 1 and size of field has minimum 1 digit.
                             '1,2,5' means "Start from 1 with step 2 and field size 5"
You can escape any character (like '[', '\\') with preceding '\\' character.

**Regular expression**

If you specify '--regex' argument, you can use regular 
expression as 'pattern' arguments in formats:

    's/<pattern>/<replace>/', 's/<pattern>/<replace>/g'
    'n/<pattern>/<replace>/', 'n/<pattern>/<replace>/g'
    'b/<pattern>/<replace>/', 'b/<pattern>/<replace>/g'
    'e/<pattern>/<replace>/', 'e/<pattern>/<replace>/g'

's' means use whole file name with extension for search/replace. 'n' is the same as 's'.
'b' uses file name without extension, 'e' uses only file extension
You can replace '/' with any other charater, i.e `s!<pattern>!<replace>!g`

You can use special sequences in `replace`:

    '\b'    - to insert file name without extension
    '\e'    - to insert file extension
    '\n'    - to insert file name with extension


### EXAMPLES

`$ mv-smart.py -n [n4].~[e] aaa1.txt bbb2.txt`

    aaa1.txt -> 1.~txt
    bbb2.txt -> 2.~txt

`$ mv-smart.py -b [c,,3]\ -\ [n] a.mp3 bbb.mp3`

    a.mp3   -> 001 - a.mp3
    bbb.mp3 -> 002 - bbb.mp3

`$ mv-smart.py -b [c10,5,4] -e txt a.dat b.dat c.dat`

    a.dat -> 0010.txt
    b.dat -> 0015.txt
    c.dat -> 0020.txt

`$ mv-smart.py --regex -n s/_/\ /g qwe_-_hello.mp3`

    qwe_-_hello.mp3 -> qwe - hello.mp3

`$ mv-smart.py --regex -b n/^/./ -e e//bak/ song.mp3`

    song.mp3 -> .song.mp3.bak

