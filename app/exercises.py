EXERCISES = [
    {
        "title": "Sum an array safely",
        "description": "Write sum_values(values) to return the sum of every integer in values. Empty lists return 0.",
        "language": "python", "topic": "array_bounds", "difficulty": "beginner",
        "starter_code": "def sum_values(values):\n    # return the sum of values\n    pass",
        "tests": [{"input": "[1, 2, 3]", "expected": 6}, {"input": "[]", "expected": 0}],
        "target_errors": ["off_by_one", "array_bounds"],
    },
    {
        "title": "Find the largest value",
        "description": "Write largest(values) without using max(). Return None for an empty list.",
        "language": "python", "topic": "edge_cases", "difficulty": "beginner",
        "starter_code": "def largest(values):\n    # return the largest value or None\n    pass",
        "tests": [{"input": "[4, 1, 9, 2]", "expected": 9}, {"input": "[]", "expected": None}],
        "target_errors": ["edge_case", "initialization"],
    },
    {
        "title": "Count matching items",
        "description": "Write count_matches(values, target) and return how many values equal target.",
        "language": "python", "topic": "loops", "difficulty": "beginner",
        "starter_code": "def count_matches(values, target):\n    # return the count\n    pass",
        "tests": [{"input": "([1, 2, 2, 3], 2)", "expected": 2}, {"input": "([], 4)", "expected": 0}],
        "target_errors": ["wrong_condition", "counter_update"],
    },
    {
        "title": "Reverse a list",
        "description": "Write reverse_values(values) and return a reversed copy without changing the input.",
        "language": "python", "topic": "list_operations", "difficulty": "intermediate",
        "starter_code": "def reverse_values(values):\n    # return a reversed copy\n    pass",
        "tests": [{"input": "[1, 2, 3]", "expected": [3, 2, 1]}, {"input": "[7]", "expected": [7]}],
        "target_errors": ["mutation", "array_bounds"],
    },
]

LANGUAGE_STARTERS = {
    "javascript": "function sum_values(values) {\n  // return the sum of values\n  return 0;\n}",
    "cpp": "#include <vector>\nint sum_values(const std::vector<int>& values) {\n    // return the sum of values\n    return 0;\n}",
    "c": "int sum_values(const int values[], int n) {\n    // return the sum of values\n    return 0;\n}",
    "java": "static int sum_values(int[] values) {\n    // return the sum of values\n    return 0;\n}",
    "kotlin": "fun sum_values(values: IntArray): Int {\n    // return the sum of values\n    return 0\n}",
    "csharp": "static int sum_values(int[] values) {\n    // return the sum of values\n    return 0;\n}",
    "dart": "int sum_values(List<int> values) {\n  // return the sum of values\n  return 0;\n}",
    "r": "sum_values <- function(values) {\n  # return the sum of values\n  0\n}",
}

for _language, _starter in LANGUAGE_STARTERS.items():
    EXERCISES.append({
        "title": "Sum an array safely",
        "description": "Write the sum_values function to return the sum of every integer in values. Empty lists return 0.",
        "language": _language,
        "topic": "array_bounds",
        "difficulty": "beginner",
        "starter_code": _starter,
        "tests": [{"input": "[1, 2, 3]", "expected": 6}, {"input": "[]", "expected": 0}],
        "target_errors": ["off_by_one", "array_bounds"],
    })

EXERCISES.extend([
    {
        "title": "Two Sum with a single pass",
        "description": "Given an integer list and a target, return the two zero-based indices whose values add to target. Assume exactly one answer exists. Aim for O(n) time.",
        "language": "python", "topic": "big_tech", "difficulty": "intermediate",
        "starter_code": "def two_sum(values, target):\n    # return the two indices in one pass\n    pass",
        "tests": [{"input": "([2, 7, 11, 15], 9)", "expected": [0, 1]}, {"input": "([3, 2, 4], 6)", "expected": [1, 2]}],
        "target_errors": ["wrong_condition", "complexity", "indexing"],
    },
    {
        "title": "Longest substring without repeats",
        "description": "Return the length of the longest substring without repeating characters. Use a sliding-window approach rather than checking every substring.",
        "language": "python", "topic": "big_tech", "difficulty": "intermediate",
        "starter_code": "def longest_unique_length(text):\n    # return the length of the longest substring with unique characters\n    pass",
        "tests": [{"input": "'abcabcbb'", "expected": 3}, {"input": "'bbbbb'", "expected": 1}, {"input": "''", "expected": 0}],
        "target_errors": ["window_update", "edge_case", "complexity"],
    },
    {
        "title": "Merge overlapping intervals",
        "description": "Given intervals [start, end], merge all overlapping intervals and return the compacted list sorted by start time.",
        "language": "python", "topic": "big_tech", "difficulty": "advanced",
        "starter_code": "def merge_intervals(intervals):\n    # return merged intervals\n    pass",
        "tests": [{"input": "[[1,3],[2,6],[8,10],[9,12]]", "expected": [[1,6],[8,12]]}, {"input": "[]", "expected": []}],
        "target_errors": ["sorting", "edge_case", "interval_boundary"],
    },
])
