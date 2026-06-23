# Complexity Cheatsheet (Interview Narration)

Use with `analyze_complexity` and `lookup_snippet` MCP tools. Full snippets in [interview-snippets.md](interview-snippets.md).

## How to answer "What's the complexity?"

1. **Name n** — string length, nodes, edges, array size, word length L
2. **Count work** — loops, recursion visits, heap operations
3. **State time** — Big-O with justification in one sentence
4. **State space** — auxiliary structures + call stack
5. **Offer upgrade** — only if your solution is suboptimal

## Your snippets at a glance

| Problem | Pattern | Time | Space | Say this |
|---------|---------|------|-------|----------|
| String split | Parsing | O(n) | O(n) | One pass, build list |
| Balanced brackets (replace) | String reduce | O(n·k) | O(n) | Prefer stack O(n) |
| Balanced brackets (stack) | Stack | O(n) | O(n) | One pass, push/pop |
| Tree height | DFS | O(n) | O(h) | Visit each node; h = height |
| Graph distances | BFS | O(V+E) | O(V) | Not Dijkstra — unweighted |
| Level order | BFS | O(n) | O(w) | w = max level width |
| Contacts / trie | Trie | O(L) per op | O(chars) | Walk one char per step |
| Running median (insort) | Sorted list | O(n²) | O(n) | insort is O(n); use two heaps |
| Running median (heaps) | Two heaps | O(n log n) | O(n) | O(log n) per insert |
| Swap nodes | DFS | O(n) per query | O(h) | Visit all nodes each query |
| FizzBuzz | Loop | O(n) | O(1) | Constant per number |
| Enumerate + parse | Loop | O(n·m) | O(n·m) | Per row token count |

## Common follow-up traps

| They ask | You answer |
|----------|------------|
| "Is that Dijkstra?" | "No — BFS; edges are unweighted / equal weight." |
| "Can you do better on median?" | "Two heaps: O(n log n) vs O(n²) with list insort." |
| "Space on skewed tree?" | "O(n) stack depth, not O(log n)." |
| "Why not pop(0)?" | "List pop(0) is O(n); deque popleft is O(1)." |
| "Bracket solution optimal?" | "Replace scans repeatedly; stack is O(n) one pass." |

## Complexity rules of thumb

```
Single loop           → O(n)
Two nested loops      → O(n²)
Binary search         → O(log n)
Sort then scan        → O(n log n)
BFS / DFS on graph    → O(V + E)
Trie add/search       → O(L)
Heap insert × n       → O(n log n)
Recursion on tree     → O(n) time, O(h) space
```

## MCP tools for complexity

| Tool | When |
|------|------|
| `analyze_complexity` | Paste your code; get narration + heuristics |
| `lookup_snippet` | "trie contacts", "bfs graph", "running median" |

Always practice saying complexity **before** calling the tool, then verify.
