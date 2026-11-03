"""测试：链接队列 —— 去重、持久化、弹出。"""

from douyin_catcher.queue import LinkQueue


def test_push_and_pop(tmp_path):
    q = LinkQueue(tmp_path / "queue.txt")
    assert q.push("https://v.douyin.com/aaa/") is True
    assert q.push("https://v.douyin.com/aaa/") is False  # 去重
    assert q.pop() == "https://v.douyin.com/aaa/"
    assert q.pop() is None


def test_persists_across_instances(tmp_path):
    q1 = LinkQueue(tmp_path / "queue.txt")
    q1.push("https://v.douyin.com/one/")
    q1.push("https://v.douyin.com/two/")
    q2 = LinkQueue(tmp_path / "queue.txt")
    assert q2.pop() == "https://v.douyin.com/one/"
    assert q2.pop() == "https://v.douyin.com/two/"


def test_dedupe_survives_restart(tmp_path):
    q1 = LinkQueue(tmp_path / "queue.txt")
    q1.push("https://v.douyin.com/x/")
    q2 = LinkQueue(tmp_path / "queue.txt")
    assert q2.push("https://v.douyin.com/x/") is False


def test_extract_link_from_share_text_on_push(tmp_path):
    q = LinkQueue(tmp_path / "queue.txt")
    q.push("8.97 复制打开抖音 https://v.douyin.com/abc/")
    assert q.pop() == "https://v.douyin.com/abc/"
