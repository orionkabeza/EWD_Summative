"""Top-K ranking with a bounded min-heap.


Problem: the dashboard needs "the K busiest pickup zones" and "the K most frequent routes" out of tens of thousands of grouped rows. Sorting all in n rows costs 0(n log n). A min-heap that never holds more than K items does it in 0(n log k): the root is always the *weakest* of the current top K, so a new item only has to beat the root to get in.

Pseudo-code
------------
    top-k(items, k, key):
        if k <= 0: return []
        heap <- empty min-heap ordered by key
        for item in items:
            if size (heap) < k:
                push(heap, item)
            else if key(item) > key key(peek(heap)):
                replace_top(heap, item)                   #evict it, one sift-down
        replace <- array of size(heap)
        for position from size(heap)-1 down to 0:         # pops come out smallest first,
            result[position] <- pop(heap)                 # so fill from the back
        return result                                     # strongest first

complexity: time 0(m log k), space 0(k) (plus the 0(k) result).
No sorted(), sort(), heapq or Counter is used.    
"""

from backend.algorithms.min_heap import MinHeap

def top_k(items, k, key):
    """Return the ``k`` items with the largest ``key``, strongest first.
    ``key(item)`` ,ay return a tuple to break ties, e.g. ``(trips, -zone_id)``.
    Items with a smaller key than the current k-th best are discarded as soon as they are seen, so memory never grows beyond k.
    """
    if k <= 0:
        return[]
    heap = MinHeap(key=key)
    for item in items:
        if len(heap) < k:
            heap.push(item)
        elif key(item) > key(heap.peek()):
            heap.replace_top(item)

    ranked = [None] * len(heap)
    for position in range(len(heap) -1, -1, -1):
        ranked[position] = heap.pop()
    return ranked




