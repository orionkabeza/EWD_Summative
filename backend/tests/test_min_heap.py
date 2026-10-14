"""Tests for the hand-written MinHeap and top_k.
``sorted()`` is used here only as oracle to check our own implemention; the algorithm under test never call it.
"""
import random
import sys
from pathlib import Path
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.algorithms.min_heap import MinHeap #noqa:E402
from backend.algorithms.topk import top_k #noqa: E402


def drain(heap):
    out =[]
    while not heap.is_empty():
        out.append(heap.pop())
    return out

def test_pops_in_ascending_order():
    heap = MinHeap()
    for value in [5, 3, 8, 1, 9, 2, 7]:
        heap.push(value)
    assert drain(heap) == [1, 2, 3, 5, 7, 8, 9]


def test_peek_does_not_remove():
    heap = MinHeap()
    heap.push(4)
    heap.push(2)
    assert heap.peek() == 2
    assert len (heap) == 2

def test_empty_heap_raise():
    heap = MinHeap()
    with pytest.raises(IndexError):
        heap.pop()
    with pytest.raises(IndexError):
         heap.peek()
    with pytest.raises(IndexError):
        heap.replace_top(1)

def test_heap_property_holds_after_random_operation():
    rng = random.Random(7)
    heap = MinHeap()
    for _ in range(500):
        heap.push(rng.randint(0, 1000))
    items = list (heap._items) # copy: draining theheap empties the internal list
    assert all(items[(i-1) // 2] <= items[i] for i in range(1, len(items)))
    assert drain(heap) == sorted(items)


def test_replace_top_returns_old_minimum_and_keeps_order():
    heap = MinHeap()
    for value in [3, 6, 9]:
        heap.push(value)
    assert heap.replace_top(7) == 3
    assert drain(heap) == [6, 7, 9]


def test_custom_key():
    heap = MinHeap(key=lambda pair: pair[1])
    for pair in [("a", 3), ("b", 1), ("c", 2)]:
        heap.push(pair)
    assert [name for name, _ in drain(heap)] == ["b", "c", "a"]

def tst_top_k_basic():
    assert top_k ([4, 9, 1, 7, 3, 8], 3, key=lambda x: x) == [9, 8, 7]

def test_top_k_larger_then_n_returns_everything_ranked():
    assert top_k([2, 5, 1], 10, key=lambda x: x) == [5, 2, 1]

def test_top_k_zero_or_negative_or_empty():
    assert top_k([1, 2, 3], 0, key=lambda x: x) == []
    assert top_k([1, 2, 3], -2, key=lambda x: x) == []
    assert top_k([], 5, key=lambda x: x) ==[]

def test_top_k_ties_are_broken_by_tuple_key():
    rows = [{"id": 5, "n":10}, {"id": 2, "n": 10}, {"id": 9, "n": 10}, {"id": 1, "n": 3}]
    ranked = top_k(rows, 2, key=lambda r: (r["n"], -r["id"]))
    assert [r["id"] for r in ranked] == [2, 5]

def test_top_k_matches_sorted_oracle_on_random_data():
    rng = random.Random(11)
    for _ in range(50):
        data = [rng.randint(0, 200) for _ in range(rng.randint(0, 120))]
        k = rng.randint(1, 15)
        assert top_k(data, k, key=lambda x: x) == sorted(data, reverse=True)[:k]

