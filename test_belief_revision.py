import unittest
from app import (
    read_form,
    bob_would_have_to_believe,
    bob_is_consistent,
    read_bobs_beliefs,
    forms_without_priorities,
    revise_bobs_beliefs,
    show_bobs_belief_set
)


class LogicTests(unittest.TestCase):
    def test_entailment_with_all_connectives(self):
        # if p iff q, and p is true, then q must be true
        # q implies (r OR s)
        # but s is false
        # so resolution should force r
        beliefs=[
            read_form("p <-> q"),
            read_form("p"),
            read_form("q -> (r | s)"),
            read_form("!s")
        ]
        self.assertTrue(
            bob_would_have_to_believe(
                beliefs,
                read_form("r")
            )
        )

    def test_consistency_detection(self):
        # direct contradiction
        self.assertFalse(
            bob_is_consistent([
                read_form("p"),
                read_form("!p")
            ])
        )
        # this should still be consistent
        # q follows from p and p -> q
        self.assertTrue(
            bob_is_consistent([
                read_form("p -> q"),
                read_form("p"),
                read_form("q")
            ])
        )


class RevisionTests(unittest.TestCase):
    def test_bob_example(self):
        beliefs=read_bobs_beliefs("p\nq\nr")
        revised_beliefs=revise_bobs_beliefs(
            beliefs,
            read_form("!(q | r)")
        )
        self.assertEqual(
            show_bobs_belief_set(revised_beliefs),
            "Cn({p, ¬(q ∨ r)})"
        )

    def test_inconsistent_input_example(self):
        beliefs=read_bobs_beliefs(
            "p\nq\np -> !q"
        )
        self.assertFalse(
            bob_is_consistent(
                forms_without_priorities(beliefs)
            )
        )

    def test_revision_removes_conflict(self):
        beliefs=read_bobs_beliefs("p\nq")
        revised_beliefs=revise_bobs_beliefs(
            beliefs,
            read_form("!q")
        )
        self.assertEqual(
            show_bobs_belief_set(revised_beliefs),
            "Cn({p, ¬q})"
        )
        self.assertTrue(
            bob_is_consistent(
                forms_without_priorities(revised_beliefs)
            )
        )

    def test_success(self):
        # after revising with p,
        # Bob should definitely believe p
        beliefs=read_bobs_beliefs("p -> q")
        revised_beliefs=revise_bobs_beliefs(
            beliefs,
            read_form("p")
        )
        self.assertTrue(
            bob_would_have_to_believe(
                forms_without_priorities(revised_beliefs),
                read_form("p")
            )
        )

    def test_vacuity(self):
        # vacuity:
        # if the new belief does not conflict,
        # old beliefs should stay
        beliefs=read_bobs_beliefs("p -> q")
        revised_beliefs=revise_bobs_beliefs(
            beliefs,
            read_form("p")
        )
        self.assertEqual(
            show_bobs_belief_set(revised_beliefs),
            "Cn({(p → q), p})"
        )

    def test_extensionality(self):
        # !(p & q) should be logically equivalent
        # to (!p | !q)
        beliefs=read_bobs_beliefs(
            "p\np -> q"
        )
        left_revision=revise_bobs_beliefs(
            beliefs,
            read_form("!(p & q)")
        )
        right_revision=revise_bobs_beliefs(
            beliefs,
            read_form("!p | !q")
        )
        for formula in forms_without_priorities(left_revision):
            self.assertTrue(
                bob_would_have_to_believe(
                    forms_without_priorities(right_revision),
                    formula
                )
            )
        for formula in forms_without_priorities(right_revision):
            self.assertTrue(
                bob_would_have_to_believe(
                    forms_without_priorities(left_revision),
                    formula
                )
            )

if __name__=="__main__":
    # probably should add more parser edge case tests later
    unittest.main()