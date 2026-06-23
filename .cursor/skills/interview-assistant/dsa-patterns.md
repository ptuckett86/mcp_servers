# DSA Pattern Quick Reference

Use with `detect_pattern` MCP tool. Full signals live in `interview-mcp/knowledge/dsa_patterns.yaml`.

| Pattern | Key signals | Default approach |
|---------|-------------|------------------|
| Sliding Window | substring, contiguous, window | Two pointers, expand/shrink |
| Two Pointers | sorted, pair, palindrome | Left/right inward |
| Binary Search | sorted, monotonic, min/max | Halve search space |
| BFS | shortest path, level order | Queue + visited |
| DFS | tree, graph, explore all | Recursion/stack + visited |
| Topological Sort | prerequisites, DAG | Kahn BFS or DFS post-order |
| Union-Find | connected components, merge | Path compression + rank |
| Dynamic Programming | optimal substructure, count ways | State + recurrence |
| Heap | top k, k largest/smallest | Min/max heap size k |
| Backtracking | combinations, permutations | Choose, recurse, undo |
| Trie | prefix, dictionary | Character tree nodes |
| Monotonic Stack | next greater/smaller | Stack with order invariant |
| Graph Shortest Path | weighted edges | Dijkstra / Bellman-Ford |
| Interval Merging | overlap, schedule | Sort by start, merge |
| Matrix Marking | in-place, set zeros | First row/col as markers |
| Bit Manipulation | xor, single number | XOR cancel, bitmasks |

## Interview tips

1. **Brute force first** — state it, then optimize
2. **Name the pattern** — interviewers want to hear "sliding window because..."
3. **Edge cases** — empty, single, duplicates, max size
4. **Complexity** — always close with time and space Big-O
