"""Unit tests for the manga brush's geometry (fast, no rendering).

These exist because two bugs in here were invisible to every gate and cost nine
render rounds each. Both were found by measuring a pixel and asking which prim
could have put ink there, never by a check that anything looked wrong:

  * ``_mul`` multiplied the affine as though the tuple were row-major while
    ``_tp`` reads it column-major. Pure rotations, pure translations and uniform
    scales all came out right, so nothing looked broken until a part was BOTH
    tilted and non-uniformly scaled -- which is every lock of hair, every brow
    and every fold on the page -- and then ``sx`` and ``sy`` swapped axes and a
    lock meant to hang down grew sideways out of the head.
  * ``flip`` was the only mirror and was used for eyes too. It mirrors the axis
    ACROSS the part (which way a lock curls); an eye has to mirror the axis ALONG
    it (which way it faces), and using ``flip`` for that moved the lash to the
    lower lid and, because the gaze shift keyed off the same flag, drove both
    irises toward the nose. A cross-eyed face out of one wrong letter.
"""
from __future__ import annotations

import math

from vcac.manga_ink import _D, _R, _T, _mul, _tp


def _pt(M, x, y):
    return _tp(M, [(x, y)])[0]


def _close(p, q, tol=1e-9):
    return all(abs(a - b) < tol for a, b in zip(p, q))


def test_tuple_is_column_major():
    # (a,b,c,d) means x' = a*x + c*y, y' = b*x + d*y, so b is the row that
    # answers to x and c to the row that answers to y
    assert _close(_pt(_R(90), 1, 0), (0.0, 1.0))
    assert _close(_pt(_R(90), 0, 1), (-1.0, 0.0))


def test_rotation_then_scale_keeps_length_on_its_own_axis():
    # the regression: a lock 74 long, 13 wide, swung to hang straight down
    T = _mul(_R(90), _D(74.0, 13.0))
    assert _close(_pt(T, 1.0, 0.0), (0.0, 74.0), 1e-9)      # length points DOWN
    assert _close(_pt(T, 0.0, 1.0), (-13.0, 0.0), 1e-9)     # width stays cross
    # and it is not a shear: the two axes remain perpendicular and keep their
    # own magnitudes whatever the tilt
    for deg in (0, 17, 45, 90, 133, 180, 271):
        M = _mul(_R(deg), _D(74.0, 13.0))
        a, b = _pt(M, 1, 0), _pt(M, 0, 1)
        assert abs(math.hypot(*a) - 74.0) < 1e-9
        assert abs(math.hypot(*b) - 13.0) < 1e-9
        assert abs(a[0] * b[0] + a[1] * b[1]) < 1e-9


def test_compose_applies_the_right_factor_first():
    # scale, then rotate, then move -- the order the template transform promises
    T = _mul(_mul(_T(10.0, 20.0), _R(90)), _D(2.0, 3.0))
    assert _close(_pt(T, 1, 0), (10.0, 22.0))
    assert _close(_pt(T, 0, 1), (7.0, 20.0))


def test_translation_never_rotates_a_supplied_offset():
    M = _mul(_T(5.0, 7.0), _R(90))
    assert _close(_pt(M, 1, 0), (5.0, 8.0))


def test_mx_mirrors_which_way_a_part_faces_flip_how_it_curls():
    eye = _mul(_T(-25.0, -45.0), _D(-9.2, 7.0))            # mx: sx negated
    assert _close(_pt(eye, 1, 0), (-34.2, -45.0))          # outer corner to the left
    assert _close(_pt(eye, 0, 1), (-25.0, -38.0))          # lash still on top
    lash = _mul(_T(-25.0, -45.0), _D(9.2, -7.0))           # flip: sy negated
    assert _close(_pt(lash, 1, 0), (-15.8, -45.0))         # faces the other way
    assert _close(_pt(lash, 0, 1), (-25.0, -52.0))         # and curls the other way
