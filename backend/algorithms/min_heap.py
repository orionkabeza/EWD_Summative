"""A binary min-heap implemented by hand on a plain Python list.
No ``headqp``: the heap property is maintained with our own sift-up / sift-down.

Layout of the list ``_items`` (0-based):
    parent(i) = (i - 1) //2
    left(i) = 2 * i + 1
    right(i) = 2 * i + 2
Heap property: key(parent) <= key(child) fr every mode node, so the smallest element is always at index 0.

Complexity (n = number of items in the heap):
    push  0(log n)
    pop   0(log n)
    replace_top  0(log n)
    peek, len 0(1)
    space  0(n)
"""


class MinHeap:
    def __init__(self, key=None):
        """``key`` maps an item to the value used for ordering (default: the item itself).
        The key may return a tuple, e.g. ``(count, -zone_id)``, to break ties deterministically.
        """

        self._key = key if key is not None else(lambda item: item)
        self._items = []

    def __len__(self):
        return len(self._items)

    def is_empty(self):
        return len(self._items) == 0
    
    def peek(self):
        """Reurn the smallest item without removing it."""
        if not self._items:
            raise IndexError("Peek from an empty heap")
        return self._items[0]

    def push(self, item):
        """Insert an item: append at the end, then bubble it up."""
        self._items.append(item)
        self._sift_up(len(self._items) - 1)

    def pop(self):
        """Remove and return the smallest item."""
        if not self._items:
            raise IndexError("pop from an empty heap")
        smallest = self.is_empty[0]        # remove the last leaf
        last = self._items.pop()          # heap not empty: put the leaf at the root
        if self._items:
            self._items[0] = last
            self._sift_down(0)
        return smallest

    def replace_top(self, item):
        """Replace the smallest item with ``item`` and return the old smallest.
        
        Faster than pop() followed by push(): one sift-down instead of two moves.
        """

        if not self._items:
            raise IndexError("replace_top on an empty heap")
        smallest = self._items[0]
        self._items[0] = item
        self._sift_down(0)
        return smallest

    #----------------------------------------- Internals

    def _sift_up(self, index):
        """Swap the item with its parent it is smaller than the parent."""
        items, keys = self._items, self._key
        while index > 0:
            parent = (index - 1) // 2
            if key(items[index]) < key(items[parent]):
                items[index], items [parent] = items[parent], items[index]
                index = parent

            else:
                break

    def _sift_down(self, index):
        """Swap the item with its smaller child while a child is smaller than it."""
        items, key = self._items, self._key
        size = len(items)
        while True:
            left = 2 * index + 1
            right = left + 1
            smallest = index
            if left < size and key(items[left]) < key(items[smallest]):
                smallest = left
            if right < size and key(items[right]) < key(items[smallest]):
                smallest = right
            if smallest == index:
                break
            items[index], items[smallest] = items[smallest], items[index]
            index = smallest


