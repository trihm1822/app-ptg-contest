# Two Sum Problem

## Problem Statement
Cho một dãy số nguyên gồm $N$ phần tử $A_1, A_2, \dots, A_N$ và một số nguyên mục tiêu $S$. Hãy tìm một cặp chỉ số phân biệt $(i, j)$ sao cho $1 \le i < j \le N$ và $A_i + A_j = S$. Nếu có nhiều cặp thỏa mãn, in ra một cặp bất kỳ. Nếu không có cặp nào thỏa mãn, in ra `-1 -1`.

## Input Format
- Dòng đầu tiên chứa hai số nguyên $N$ và $S$ ($2 \le N \le 10^5, -10^9 \le S \le 10^9$).
- Dòng thứ hai chứa $N$ số nguyên $A_1, A_2, \dots, A_N$ ($-10^9 \le A_i \le 10^9$).

## Output Format
- In ra hai chỉ số $i$ và $j$ (1-indexed, $i < j$) cách nhau bởi một dấu cách, hoặc `-1 -1` nếu không tìm thấy.

## Constraints
- **Subtask 1 (30% số điểm):** $2 \le N \le 100$.
- **Subtask 2 (30% số điểm):** $2 \le N \le 5000$.
- **Subtask 3 (40% số điểm):** $2 \le N \le 10^5$.

## Sample 1
### Input
```text
5 9
2 7 11 15 1
```
### Output
```text
1 2
```

## Sample 2
### Input
```text
3 10
1 2 3
```
### Output
```text
-1 -1
```
