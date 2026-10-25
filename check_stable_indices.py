import json
import sys
from collections import Counter

BITS_PER_ROW = 4096  # 512 bytes x 8
DETERMINISTIC_ROWS = set([0] + list(range(2, 13)) + [158, 159])


def find_key(obj, name):
    """遞迴找出名稱為 name 的欄位,找不到回傳 None。"""
    if isinstance(obj, dict):
        if name in obj:
            return obj[name]
        for v in obj.values():
            r = find_key(v, name)
            if r is not None:
                return r
    elif isinstance(obj, list):
        for v in obj:
            r = find_key(v, name)
            if r is not None:
                return r
    return None


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "demo_bundle/device/helper_data.json"
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    print("頂層欄位:", list(data.keys()) if isinstance(data, dict) else type(data))

    idx = find_key(data, "stable_indices")
    if idx is None:
        print("找不到 stable_indices,請把上面印出的欄位名稱貼給我。")
        return

    idx = [int(i) for i in idx]
    n = len(idx)
    print(f"stable_indices 數量: {n}(預期 2816)")
    print(f"最小/最大索引: {min(idx)} / {max(idx)}")

    rows = Counter(i // BITS_PER_ROW for i in idx)
    in_det = sum(c for r, c in rows.items() if r in DETERMINISTIC_ROWS)
    print(f"落在確定性列的位元: {in_det} / {n} ({in_det / n:.2%})")
    print(f"用到的不同列數: {len(rows)} / 160")
    print("每列使用數量前 10 名:", rows.most_common(10))

    if in_det == 0:
        print("結果:通過,選位已避開確定性列。")
    else:
        print("結果:不通過,仍有位元落在確定性列。")


if __name__ == "__main__":
    main()