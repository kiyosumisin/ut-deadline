"""Đẩy tin sang Telegram bot."""
import os, json, datetime as dt, urllib.request

TEN = "telegram"
UA = "UT-Deadline/1.0 (bao deadline ca nhan)"
VN = dt.timezone(dt.timedelta(hours=7))   # chốt cứng, khỏi phụ thuộc tzdata máy chạy


def _esc(s):
    """Escape cho parse_mode HTML. Thiếu cái này là một dấu & trong tên môn
    làm hỏng cả khối tin, Telegram trả 400 chứ không gửi thiếu."""
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def tin(ds, now):
    # Telegram không có timestamp động như <t:...:R> của Discord -> tự tính
    # "còn bao lâu" và tự format giờ VN. Đây là thứ mất đi khi đổi nhà.
    dong = []
    for han, ten, mon, url in ds:
        gio = dt.datetime.fromtimestamp(han, VN).strftime("%H:%M %d/%m")
        con = max(0, han - now)
        khi = f"{con // 3600}h nữa" if con < 48 * 3600 else f"{con // 86400} ngày nữa"
        nhan = f'<a href="{_esc(url)}">{_esc(ten)}</a>' if url else f"<b>{_esc(ten)}</b>"
        dong.append(f"• {nhan} — {_esc(mon)} — {gio} ({khi})")
    ngay = os.environ.get("NGAY_TRUOC", "3")
    tag = os.environ.get("TELEGRAM_TAG", "").strip()
    return _esc((tag + " ") if tag else "") + \
        f"⏰ {len(ds)} deadline trong {_esc(ngay)} ngày tới:\n" + "\n".join(dong)


def gui(ds, now):
    """Gửi nếu có đủ token và chat_id. True = đã gửi, False = chưa cấu hình."""
    token = os.environ.get("TELEGRAM_TOKEN", "").strip()
    chat = os.environ.get("TELEGRAM_CHAT", "").strip()
    if not (token and chat):
        return False
    urllib.request.urlopen(urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendMessage",
        json.dumps({"chat_id": chat, "text": tin(ds, now),
                    "parse_mode": "HTML", "disable_web_page_preview": True}).encode(),
        {"Content-Type": "application/json", "User-Agent": UA}), timeout=30)
    return True


def tu_kiem():
    t = tin([(0, "A<b>&", "M&M", "u?x=1&y=2")], 0)
    assert "A&lt;b&gt;&amp;" in t and "M&amp;M" in t, t
    assert 'href="u?x=1&amp;y=2"' in t, t
    assert "<b>X</b>" in tin([(0, "X", "M", "")], 0)          # không url -> in đậm
    assert "2 ngày nữa" in tin([(86400 * 2, "X", "M", "")], 0)
    assert "47h nữa" in tin([(47 * 3600, "X", "M", "")], 0)   # sát mốc 48h
    assert "2h nữa" in tin([(7200, "X", "M", "")], 0)
    assert "0h nữa" in tin([(-500, "X", "M", "")], 0)         # đã qua hạn
    # Giờ phải là giờ VN chứ không theo máy chạy: 0 epoch = 07:00 01/01 ở UTC+7.
    assert "07:00 01/01" in tin([(0, "X", "M", "")], 0)
    # Thiếu một trong hai khóa cũng là chưa cấu hình, đừng gửi nửa vời.
    giu = {k: os.environ.pop(k, None) for k in ("TELEGRAM_TOKEN", "TELEGRAM_CHAT")}
    try:
        assert gui([], 0) is False
        os.environ["TELEGRAM_TOKEN"] = "x"
        assert gui([], 0) is False
    finally:
        os.environ.pop("TELEGRAM_TOKEN", None)
        for k, v in giu.items():
            if v is not None:
                os.environ[k] = v
