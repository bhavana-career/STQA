"""Exercise 4: Statement vs. Branch Coverage Demonstration.

Demonstrates a classic control-flow graph (CFG) scenario where 100% statement
coverage is achieved with fewer tests, but leaves execution branches untested.
"""
from __future__ import annotations


def classify_number(n: int, flag: bool) -> str:
    """Classify a number based on conditional logic.

    Control Flow Graph:
    - Node 1: Entry
    - Node 2: Decision 1: `if n > 0:`
    - Node 3: Decision 2: `if flag:` (Nested under True branch of Decision 1)
    - Node 4: `result = "positive-flagged"`
    - Node 5: `result = "positive-unflagged"`
    - Node 6: `result = "non-positive"` (False branch of Decision 1)
    - Node 7: Exit: `return result`
    """
    result = "non-positive"  # Line 1 (Stmt 1)
    if n > 0:                # Line 2 (Branch 1: T / F)
        if flag:             # Line 3 (Branch 2: T / F)
            result = "positive-flagged"    # Line 4 (Stmt 2)
        else:
            result = "positive-unflagged"  # Line 5 (Stmt 3)
    return result            # Line 6 (Stmt 4)


# Test Suite A: 100% Statement Coverage, but ONLY 75% Branch Coverage
# Test Case 1: (n=5, flag=True)  -> Executes Lines 1, 2(T), 3(T), 4, 6
# Test Case 2: (n=5, flag=False) -> Executes Lines 1, 2(T), 3(F), 5, 6
# Notice that Branch 1 (False: n <= 0) was NEVER taken!
# Every statement (Lines 1, 2, 3, 4, 5, 6) was executed: 100% statement coverage!
# But Branch 1 False was completely missed!

# Test Suite B: 100% Statement AND 100% Branch Coverage
# Test Case 1: (n=5, flag=True)  -> Decision 1 True, Decision 2 True
# Test Case 2: (n=5, flag=False) -> Decision 1 True, Decision 2 False
# Test Case 3: (n=-1, flag=False)-> Decision 1 False (takes the False branch)
