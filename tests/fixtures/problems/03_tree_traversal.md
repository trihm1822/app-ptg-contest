# Tree Diameter

## Problem Statement
Cho một cây gồm $N$ đỉnh được đánh số từ $1$ đến $N$ và $N-1$ cạnh vô hướng. Khoảng cách giữa hai đỉnh là số cạnh trên đường đi đơn ngắn nhất giữa chúng. Đường kính của cây là khoảng cách lớn nhất giữa hai đỉnh bất kỳ trên cây. Hãy tính đường kính của cây đã cho.

## Input Format
- Dòng đầu tiên chứa số nguyên dương $N$ ($1 \le N \le 2 \times 10^5$).
- $N-1$ dòng tiếp theo, mỗi dòng chứa hai số nguyên $u$ và $v$ ($1 \le u, v \le N, u \ne v$) mô tả một cạnh của cây. Đảm bảo dữ liệu tạo thành một cây hợp lệ.

## Output Format
- In ra một số nguyên duy nhất là đường kính của cây.

## Constraints
- **Subtask 1 (30% số điểm):** $1 \le N \le 1000$.
- **Subtask 2 (70% số điểm):** $1 \le N \le 2 \times 10^5$.

## Sample 1
### Input
```text
5
1 2
1 3
3 4
3 5
```
### Output
```text
3
```
*(Giải thích: Đường đi dài nhất là giữa đỉnh 2 và đỉnh 4: 2 - 1 - 3 - 4 có độ dài bằng 3).*
