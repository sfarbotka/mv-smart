#!/usr/bin/env python

from __future__ import generators

import sys
import os
import re
import argparse


PATTERN_TYPE_SIMPLE = 'Simple'
PATTERN_TYPE_REGEX_SUBSTITUTE = 'Regex (s///g)'
PATTERN_TYPE_REGEX_SIMPLE = 'Regex (simple)'  # Currently disabled


prog = os.path.split(sys.argv[0])[1]

help_description = """\
NAME
    %(prog)s -- smart file renaming

SYNOPSIS
    %(prog)s -n pattern [-f] FILE [FILE ...]
    %(prog)s -b pattern [-e pattern] [-f] FILE [FILE ...]
    %(prog)s --simple -n pattern [-f] FILE [FILE ...]
    %(prog)s --simple -b pattern [-e pattern] [-f] FILE [FILE ...]
    %(prog)s --regex-subs -n pattern [-f] FILE [FILE ...]
    %(prog)s --regex-subs -b pattern [-e pattern] [-f] FILE [FILE ...]

ARGUMENTS
""" % {'prog': prog}

help_epilog = """\

DESCRIPTION
    The %(prog)s utility renames listed files using two kind of patterns.

    If you specify '-n' argument, 'pattern' presents whole file name (base and extension).
    If you specify '-b' argument, 'pattern' presents only file base name (extension
    will not be renamed).
    If you specify '-e' argument, 'pattern' presents only file extension (base will not
    be renamed).
    If you specify both '-b' and '-e' argument, you can set pattern for base name and
    extension separately.

PATTERNS TYPES
    * Simple patterns *
    If you specify '--simple' argument or omit any patterns types arguments, you can
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

    * Regular expression *
    If you specify either '--regex-subs' or '--regex' arguments, you can use regular
    expression as 'pattern' arguments in for 's/<pattern>/<replace>/' or
    's/<pattern>/<replace>/g'. You can replace '/' with any other charater,
    i.e 's!<pattern>!<replace>!g'
    'g' means continue searchin/replacing after first replace.
    Regular expression matching operations similar to those found in Perl

    You can use special sequences in '<replace>':

        '\\b'    - to insert file name without extension
        '\e'    - to insert file extension
        '\\n'    - to insert file name with extension


EXAMPLES

    $ %(prog)s -n [n4].~[e] aaa1.txt bbb2.txt
        aaa1.txt -> 1.~txt
        bbb2.txt -> 2.~txt

    $ %(prog)s -b [c,,3]\ -\ [n] a.mp3 bbb.mp3
        a.mp3   -> 001 - a.mp3
        bbb.mp3 -> 002 - bbb.mp3

    $ %(prog)s -b [c10,5,4] -e txt a.dat b.dat c.dat
        a.dat -> 0010.txt
        b.dat -> 0015.txt
        c.dat -> 0020.txt

    $ %(prog)s --regex -n s/_/\ /g qwe_-_hello.mp3
        qwe_-_hello.mp3 -> qwe - hello.mp3

""" % {'prog': prog}


class PatternError(Exception):
    def __init__(self, pattern, msg):
        self.pattern = pattern
        self.message = msg

    def __str__(self):
        return '%s: %s' % (self.msg, self.pattern)


class EmptyNameError(Exception):
    def __init__(self, fname, msg='File can\'t have empty name'):
        self.message = msg
        self.fname = fname

    def __str__(self):
        return '%s: %s' % (self.message, self.fname)


class Matcher(object):
    def __init__(self, pattern):
        self.pattern = pattern

    def sub(self, string):
        raise NotImplementedError()


class NameMatcher(Matcher):
    ptrn_string = r'^(?P<type>n|e|(ne))((?P<start>\d+)(-(?P<end>\d+))?)?$'
    ptrn = re.compile(ptrn_string)

    def __init__(self, pattern):
        Matcher.__init__(self, pattern)

        self.typ = None
        self.start = None
        self.end = None

        self.parse()

    def parse(self):
        m = NameMatcher.ptrn.match(self.pattern)
        typ = m.group('type')
        start = m.group('start')
        end = m.group('end')

        self.typ = typ
        self.start = 0 if start is None else int(start) - 1
        self.end = None if end is None else int(end)

    def _get_string(self, fname):
        if self.typ == 'ne':
            return fname

        n, e = os.path.splitext(fname)

        if self.typ == 'n':
            return n

        if len(e):
            e = e[1:]

        return e

    def sub(self, fname):
        s = self._get_string(fname)

        start = self.start
        end = self.end
        l = len(s)

        if start is not None and end is None:
            end = l

        if start < 0:
            start = 0

        if end <= start:
            return ''
        if start >= l:
            return ''
        if end > l:
            end = l

        ret = s[start:end]
        return ret


class CounterMatcher(Matcher):
    ptrn_string = r'^c((?P<start>\d+)?(,(?P<step>\d+)?(,(?P<digits>\d+))?)?)?$'
    ptrn = re.compile(ptrn_string)

    def __init__(self, pattern):
        Matcher.__init__(self, pattern)

        self.start = None
        self.step = None
        self.digits = None

        self.parse()

    def parse(self):
        m = CounterMatcher.ptrn.match(self.pattern)
        start = m.group('start')
        step = m.group('step')
        digits = m.group('digits')

        self.start = 1 if start is None else int(start)
        self.step = 1 if step is None else int(step)
        self.digits = 1 if digits is None else int(digits)

    def sub(self, fname):
        t = '%%0%dd' % self.digits

        ret = t % self.start
        self.start += self.step

        return ret


class MatcherFactory(object):
    _objects = [
        (NameMatcher.ptrn, NameMatcher),
        (CounterMatcher.ptrn, CounterMatcher),
    ]

    def get_matcher(self, pattern):
        for ro, cls in self._objects:
            if ro.match(pattern) is not None:
                return cls(pattern)

        raise PatternError(pattern, 'Pattern is not recognized')


class Substitutor(object):
    def _unescape(self, escaped):
        p = re.compile(r'\\(.)')
        ret = p.sub(r'\1', escaped)
        return ret

    def compile(self):
        raise NotImplementedError()

    def subs(self, fname):
        raise NotImplementedError()


class SimpleSubstitutor(Substitutor):
    def __init__(self, pattern):
        self.pattern = pattern
        self.out_s = None
        self.matchers = None

    def _parse_pattern(self):
        p = re.compile(r'((?<!\\)(?:\\\\)*)\[(?P<p>.+?)\]')  # extract all [something]
        groups = []
        for x in p.finditer(self.pattern):
            groups.append(x.group('p'))

        groups = tuple(groups)

        ps = self.pattern.replace('%', '%%')
        ps_out = p.sub(r'\1%s', ps)
        ps_out = self._unescape(ps_out)

        return ps_out, groups

    def _create_matchers(self, groups):
        factory = MatcherFactory()

        ret = tuple(factory.get_matcher(a) for a in groups)
        return ret

    def compile(self):
        self.out_s = None
        self.matchers = None

        ps, groups = self._parse_pattern()
        matchers = self._create_matchers(groups)

        self.out_s = ps
        self.matchers = matchers

    def subs(self, fname):
        vals = tuple(m.sub(fname) for m in self.matchers)
        newname = self.out_s % vals
        return newname


class RegexSubstitutor(Substitutor):
    _cpescape = re.compile(r'(\\[\\abfnrtve])')
    _cppredefined = re.compile(r'((?<!\\)(?:\\\\)*)\\(?P<x>[ben\\])')
    _cpsubstitute = re.compile(r's(?P<d>.)(?P<p>.+)(?P=d)(?P<r>.*)(?P=d)(?P<g>g)?')

    def __init__(self, pattern, pattern_type=PATTERN_TYPE_REGEX_SUBSTITUTE):
        self.pattern = pattern
        self.pattern_type = pattern_type
        self.pobject = None
        self.rstring = None
        self.go = None

    def _parse_simple_pattern(self):
        po = re.compile(r'^.+$')
        r = self.pattern
        g = False

        return po, r, g

    def _parse_substitute_pattern(self):
        m = self._cpsubstitute.match(self.pattern)
        if m is None:
            raise PatternError(self.pattern, 'Substitute regex pattern is not recognized')

        d = m.group('d')
        if self.pattern.count(d) > 3:
            raise PatternError(self.pattern,
                               'Substitute delimiter "%s" is used inside pattern' % d)

        p = m.group('p')
        r = m.group('r')
        g = m.group('g')

        try:
            po = re.compile(p)
        except re.error as e:
            raise PatternError(p, e.message)

        g = True if g is not None else False

        return po, r, g

    def _parse_pattern(self):
        if self.pattern_type == PATTERN_TYPE_REGEX_SIMPLE:
            po, r, g = self._parse_simple_pattern()
        else:
            po, r, g = self._parse_substitute_pattern()

        r = self._cpescape.sub(r'\\\1', r)
        return po, r, g

    def compile(self):
        self.pobject = None
        self.rstring = None
        self.go = None

        po, r, g = self._parse_pattern()

        self.pobject = po
        self.rstring = r
        self.go = g

    def _gen_predefined(self, groups, fname):
        b, e = os.path.splitext(fname)
        if len(e):
            e = e[1:]

        for g in groups:
            if g == 'b':
                yield b
            elif g == 'e':
                yield e
            elif g == 'n':
                yield fname
            else:
                yield g

    def _subs_predefined(self, s, fname):
        groups = []

        for x in self._cppredefined.finditer(s):
            groups.append(x.group('x'))

        groups = tuple(self._gen_predefined(groups, fname))

        s = s.replace('%', '%%')
        s = self._cppredefined.sub(r'\1%s', s)

        ret = s % groups
        return ret

    def subs(self, fname):
        count = 0 if self.go else 1

        rstring = self.rstring

        try:
            ret = self.pobject.sub(rstring, fname, count)
        except IndexError as e:
            raise PatternError(self.rstring, e.message)
        except re.error as e:
            raise PatternError(self.rstring, e.message)

        ret = self._subs_predefined(ret, fname)
        return ret


class SubstitutorBuilder(object):
    def __init__(self, pattern_type):
        self.pattern_type = pattern_type

    def build(self, pattern):
        if self.pattern_type == PATTERN_TYPE_SIMPLE:
            return SimpleSubstitutor(pattern)

        if self.pattern_type in [PATTERN_TYPE_REGEX_SIMPLE,
                                 PATTERN_TYPE_REGEX_SUBSTITUTE]:
            return RegexSubstitutor(pattern, self.pattern_type)

        raise KeyError('Unrecognized pattern type: %s' % self.pattern_type)

    @property
    def default_ext_pattern(self):
        if self.pattern_type == PATTERN_TYPE_SIMPLE:
            return '[e]'

        if self.pattern_type == PATTERN_TYPE_REGEX_SIMPLE:
            return r'\e'
        if self.pattern_type == PATTERN_TYPE_REGEX_SUBSTITUTE:
            return r's/^.+$/\e/'

    @property
    def default_base_pattern(self):
        if self.pattern_type == PATTERN_TYPE_SIMPLE:
            return '[n]'

        if self.pattern_type == PATTERN_TYPE_REGEX_SIMPLE:
            return r'\b'
        if self.pattern_type == PATTERN_TYPE_REGEX_SUBSTITUTE:
            return r's/^.+$/\b/'


def rename(tuples, force):
    lens = list(len(a[2]) for a in tuples)
    maxlen = reduce(lambda x, y: y if x < y else x, lens, 0)

    template = '%%-%ds -> %%s' % maxlen
    for src, path, fold, fnew in tuples:
        print template % (fold, fnew)
        if force is True:
            dst = os.path.join(path, fnew)
            os.rename(src, dst)


def subs_fnames(sbuilder, pattern, fnames):
    s = sbuilder.build(pattern)
    s.compile()

    return list(s.subs(fname) for fname in fnames)


def merge_base_ext(fname, base, ext):
    lb = len(base)
    le = len(ext)

    if not lb and not le:
        raise EmptyNameError(fname)

    if not len(base):
        return '.%s' % ext
    if not len(ext):
        return base

    return '%s.%s' % (base, ext)


def subs(ne, n, e, files, pattern_type=PATTERN_TYPE_SIMPLE):
    path_name_iter = (os.path.split(f) for f in files)

    fpaths, fnames = zip(*path_name_iter)

    sbuilder = SubstitutorBuilder(pattern_type)

    if ne is not None:
        newnames = subs_fnames(sbuilder, ne, fnames)
    else:
        if e is None:
            e = sbuilder.default_ext_pattern
        if n is None:
            n = sbuilder.default_base_pattern

        bases = subs_fnames(sbuilder, n, fnames)
        exts = subs_fnames(sbuilder, e, fnames)

        print bases
        print exts
        newnames = list(merge_base_ext(*a) for a in zip(fnames, bases, exts))

    ret = zip(files, fpaths, fnames, newnames)
    return ret


def get_pattern_type(args):
    if args.regex or args.regex_subs:
        return PATTERN_TYPE_REGEX_SUBSTITUTE

    #if args.regex_simple:
    #    return PATTERN_TYPE_REGEX_SIMPLE

    return PATTERN_TYPE_SIMPLE


def parse_args():
    parser = argparse.ArgumentParser(description=help_description,
                                     epilog=help_epilog,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    gpatt = parser.add_argument_group('Patterns')
    gpatt.add_argument('-n', '--name-ext', metavar='PATTERN',
                       help='Pattern for file names with extentions')
    gpatt.add_argument('-b', '--name', metavar='PATTERN',
                       help='Pattern for file bases (no extentions)')
    gpatt.add_argument('-e', '--ext', metavar='PATTERN',
                       help='Pattern for file extentions')
    gptype0 = parser.add_argument_group('Pattern types')
    gptype = gptype0.add_mutually_exclusive_group()
    gptype.title = 'Patterns types'
    #gptype.add_argument('--regex-simple',
    #                    help='Parse pattern as simple regex', action='store_true')
    gptype.add_argument('--regex-subs',
                        help='Parse pattern as s///g regex', action='store_true')
    gptype.add_argument('--regex',
                        help='Same as --regex-subs', action='store_true')
    gptype.add_argument('--simple',
                        help='Simple pattern (default)', action='store_true')
    gother = parser.add_argument_group('Other arguments')
    gother.add_argument('-f', '--force',
                        help='Rename files', action='store_true')
    gother.add_argument('files',
                        help='Files to rename',
                        nargs='+', metavar='FILE')

    args = parser.parse_args()

    if not args.name_ext and not args.name and not args.ext:
        parser.error('You must specify either -n or one or both of -b and -e')

    if args.name_ext and (args.name or args.ext):
        parser.error('You can\'t specify -n with -b and/or -e')

    return args


def main():
    args = parse_args()
    pattern_type = get_pattern_type(args)

    try:
        tuples = subs(args.name_ext, args.name, args.ext, args.files, pattern_type)
    except PatternError as e:
        sys.stderr.write('%s: %s\n' % (e.message, e.pattern))
        return 2
    except EmptyNameError as e:
        sys.stderr.write('%s: %s\n' % (e.message, e.fname))
        return 2

    rename(tuples, args.force)
    return 0


if __name__ == '__main__':
    sys.exit(main())
