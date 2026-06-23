# Interview Snippets (Your Solutions)

Reference implementations with complexity talking points. Source of truth for MCP `lookup_snippet` is `interview-mcp/knowledge/snippets.yaml`.

## String to List

```python
lis = string.split("-")
```

**Time O(n), Space O(n)** — one scan, n = string length.

---

## Balanced Brackets

Your approach (replace until stable):

```python
def isBalanced(my_string):
    brackets = ['()', '{}', '[]']
    while any(x in my_string for x in brackets):
        for br in brackets:
            my_string = my_string.replace(br, '')
    return 'YES' if len(my_string) == 0 else 'NO'
```

**Time O(n·k), Space O(n)** — repeated full-string scans.

**Interview upgrade — stack O(n):**

```python
def isBalanced(s):
    stack, pairs = [], {')': '(', '}': '{', ']': '['}
    for ch in s:
        if ch in '({[':
            stack.append(ch)
        elif ch in ')}]':
            if not stack or stack.pop() != pairs[ch]:
                return 'NO'
    return 'YES' if not stack else 'NO'
```

---

## Binary Tree Height

```python
def height(root):
    if root is None:
        return -1
    return 1 + max(height(root.left), height(root.right))
```

**Time O(n), Space O(h)** — h = height; O(n) if skewed.

---

## Graph BFS Distances (not Dijkstra)

```python
# BFS from source s; edge weight 6 is constant per level
visited = set()
to_look = [(s, 0)]
while to_look:
    n, d = to_look.pop(0)  # prefer deque.popleft()
    # mark visited, set distances[n] = d
    # enqueue unvisited neighbors with d + 6
```

**Time O(V+E), Space O(V)** — call it BFS on unweighted graph.

---

## Level Order Traversal

```python
def levelOrder(root):
    q = Queue()
    q.add_queue(root)
    while not q.is_empty():
        node = q.remove_queue()
        print(node.info, end=' ')
        if node.left:  q.add_queue(node.left)
        if node.right: q.add_queue(node.right)
```

**Time O(n), Space O(w)** — w = widest level.

---

## Contacts (Trie)

```python
# memo = count of words with this prefix
def add(self, cursor, word):
    for letter in word:
        if cursor.children.get(letter) is None:
            cursor.children[letter] = Contacts()
        cursor = cursor.children[letter]
        cursor.memo += 1
    cursor.end_of_word = 1
```

**Time O(L) per add/find, Space O(total characters)**.

---

## Running Median

```python
import bisect

def runningMedian(a, p=[], q=[], l=0):
    for i in range(len(a)):
        l += 1
        bisect.insort(p, a[i])
        if l % 2 == 1:
            q.append(p[l // 2])
        else:
            q.append((p[l // 2] + p[l // 2 - 1]) / 2)
    return q
```

**Time O(n²), Space O(n)** — insort shifts O(n) per insert.

**Upgrade:** two heaps → **O(n log n)**.

---

## Swap Nodes at Depth

Swap children when `depth % h == 0`, then inorder walk.

**Time O(n) per query, Space O(h)** recursion.

---

## FizzBuzz

```python
def fizzBuzz(n):
    for i in range(1, n + 1):
        buzzes = []
        if i % 3 == 0: buzzes.append("Fizz")
        if i % 5 == 0: buzzes.append("Buzz")
        print("".join(buzzes) if buzzes else i)
```

**Time O(n), Space O(1)** excluding output.

---

## Python Idioms

```python
import random
random.choice([1, 2, 3])   # O(1)
random.random()            # O(1)

7 // 2  # floor division → 3

for i, m in enumerate(mon):  # O(len(mon))
    pass
```

---

## Adding more snippets

Edit `interview-mcp/knowledge/snippets.yaml` — no Python changes needed.
