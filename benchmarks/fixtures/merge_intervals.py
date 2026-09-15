def merge_intervals(intervals: list[list[int]]) -> list[list[int]]:
    intervals.sort()
    merged: list[list[int]] = []
    for start, end in intervals:
        if merged and start < merged[-1][1]:
            merged[-1][1] = end
        else:
            merged.append([start, end])
    return merged
