# -*- coding: utf-8 -*-

import pytest
import unittest

from parsimonious import Grammar, NodeVisitor, VisitationError, rule
from parsimonious.expressions import Literal
from parsimonious.nodes import Node


class HtmlFormatter(NodeVisitor):
    """Visitor that turns a parse tree into HTML fragments"""

    grammar = Grammar("""bold_open  = '(('""")  # just partial

    def visit_bold_open(self, node, visited_children):
        return '<b>'

    def visit_bold_close(self, node, visited_children):
        return '</b>'

    def visit_text(self, node, visited_children):
        """Return the text verbatim."""
        return node.text

    def visit_bold_text(self, node, visited_children):
        return ''.join(visited_children)


class ExplosiveFormatter(NodeVisitor):
    """Visitor which raises exceptions"""

    def visit_boom(self, node, visited_children):
        raise ValueError


class CoupledFormatter(NodeVisitor):
    @rule('bold_open text bold_close')
    def visit_bold_text(self, node, visited_children):
        return ''.join(visited_children)

    @rule('"(("')
    def visit_bold_open(self, node, visited_children):
        return '<b>'

    @rule('"))"')
    def visit_bold_close(self, node, visited_children):
        return '</b>'

    @rule('~"[a-zA-Z 0-9]*"')
    def visit_text(self, node, visited_children):
        """Return the text verbatim."""
        return node.text


class PrimalScream(Exception):
    pass

class NodeTest(unittest.TestCase):
    def test_visitor(self):
        """Assert a tree gets visited correctly."""
        grammar = Grammar(r'''
            bold_text  = bold_open text bold_close
            text       = ~'[a-zA-Z 0-9]*'
            bold_open  = '(('
            bold_close = '))'
        ''')
        text = '((o hai))'
        tree = Node(grammar['bold_text'], text, 0, 9,
                    [Node(grammar['bold_open'], text, 0, 2),
                    Node(grammar['text'], text, 2, 7),
                    Node(grammar['bold_close'], text, 7, 9)])
        assert grammar.parse(text) == tree
        result = HtmlFormatter().visit(tree)
        assert result == '<b>o hai</b>'

    def test_visitation_exception(self):
        self.assertRaises(VisitationError,
                    ExplosiveFormatter().visit,
                    Node(Literal(''), '', 0, 0))

    def test_str(self):
        """Test str and unicode of ``Node``."""
        n = Node(Literal('something', name='text'), 'o hai', 0, 5)
        good = '<Node called "text" matching "o hai">'
        assert str(n) == good

    def test_repr(self):
        """Test repr of ``Node``."""
        s = u'hai ö'
        boogie = u'böogie'
        n = Node(Literal(boogie), s, 0, 3, children=[
                Node(Literal(' '), s, 3, 4), Node(Literal(u'ö'), s, 4, 5)])
        assert repr(n) == str("""s = {hai_o}\nNode({boogie}, s, 0, 3, children=[Node({space}, s, 3, 4), Node({o}, s, 4, 5)])""").format(
                hai_o=repr(s),
                boogie=repr(Literal(boogie)),
                space=repr(Literal(" ")),
                o=repr(Literal(u"ö")),
            )

    def test_parse_shortcut(self):
        """Exercise the simple case in which the visitor takes care of parsing."""
        assert HtmlFormatter().parse('((') == '<b>'

    def test_match_shortcut(self):
        """Exercise the simple case in which the visitor takes care of matching."""
        assert HtmlFormatter().match('((other things') == '<b>'

    def test_rule_decorator(self):
        """Make sure the @rule decorator works."""
        assert CoupledFormatter().parse('((hi))') == '<b>hi</b>'

    @pytest.mark.skip(reason="I haven't got around to making this work yet.")
    def test_rule_decorator_subclassing(self):
        """Make sure we can subclass and override visitor methods without blowing
        away the rules attached to them."""
        class OverridingFormatter(CoupledFormatter):
            def visit_text(self, node, visited_children):
                """Return the text capitalized."""
                return node.text.upper()

            @rule('"not used"')
            def visit_useless(self, node, visited_children):
                """Get in the way. Tempt the metaclass to pave over the
                superclass's grammar with a new one."""

        assert OverridingFormatter().parse('((hi))') == '<b>HI</b>'

    def test_unwrapped_exceptions(self):
        class Screamer(NodeVisitor):
            grammar = Grammar("""greeting = 'howdy'""")
            unwrapped_exceptions = (PrimalScream,)

            def visit_greeting(self, thing, visited_children):
                raise PrimalScream('This should percolate up!')

        self.assertRaises(PrimalScream, Screamer().parse, 'howdy')

    def test_node_inequality(self):
        node = Node(Literal('12345'), 'o hai', 0, 5)
        assert node != 5
        assert node != None
        assert node != Node(Literal('23456'), 'o hai', 0, 5)
        assert not (node != Node(Literal('12345'), 'o hai', 0, 5))

    def test_generic_visit_NotImplementedError_unnamed_node(self):
        """
        Test that generic_visit provides informative error messages
        when visitors are not defined.

        Regression test for https://github.com/erikrose/parsimonious/issues/110
        """
        class MyVisitor(NodeVisitor):
            grammar = Grammar(r'''
                bar = "b" "a" "r"
            ''')
            unwrapped_exceptions = (NotImplementedError, )

        with self.assertRaises(NotImplementedError) as e:
            MyVisitor().parse('bar')
        assert 'No visitor method was defined for this expression: "b"' in str(e.exception)

    def test_generic_visit_NotImplementedError_named_node(self):
        """
        Test that generic_visit provides informative error messages
        when visitors are not defined.
        """
        class MyVisitor(NodeVisitor):
            grammar = Grammar(r'''
                bar = myrule myrule myrule
                myrule = ~"[bar]"
            ''')
            unwrapped_exceptions = (NotImplementedError, )

        with self.assertRaises(NotImplementedError) as e:
            MyVisitor().parse('bar')
        assert 'No visitor method was defined for this expression: myrule = ~"[bar]"' in str(e.exception)
