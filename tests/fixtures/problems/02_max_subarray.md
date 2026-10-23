# Maximum Subarray Sum

## Problem Statement
Cho một dãy số nguyên gồm $N$ phần tử $A_1, A_2, \dots, A_N$. Hãy tìm đoạn con liên tiếp không rỗng có tổng các phần tử lớn nhất.

## Input Format
- Dòng đầu tiên chứa số nguyên dương $N$ ($1 \le N \le 2 \times 10^5$).
- Dòng thứ hai chứa $N$ số nguyên $A_1, A_2, \dots, A_N$ ($-10^9 \le A_i \le 10^9$).

## Output Format
- In ra một số nguyên duy nhất là tổng lớn nhất của đoạn con liên tiếp tìm được.

## Constraints
- **Subtask 1 (25% số điểm):** $1 \le N \le 100$.
- **Subtask 2 (35% số điểm):** $1 \le N \le 5000$.
- **Subtask 3 (40% số điểm):** $1 \le N \le 2 \times 10^5$.

## Sample 1
### Input
```text
8
-2 1 -3 4 -1 2 1 -5
```
### Output
```text
6
```
*(Giải thích: Đoạn con [4, -1, 2, 1] có tổng là 6).*

## Sample 2
### Input
```text
4
-5 -2 -8 -1
```
### Output
```text
-1
```
