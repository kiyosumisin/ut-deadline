"""Đẩy tin sang Discord webhook."""
import os, json, urllib.request

TEN = "discord"
# Discord núp sau Cloudflare và trả 403 cho UA mặc định của urllib. UA tự khai
# tên là qua, không cần giả làm trình duyệt.
UA = "UT-Deadline/1.0 (bao deadline ca nhan)"


def tin(ds):
    # <t:...:R> là timestamp Discord: tự hiện "còn 2 ngày" theo múi giờ người đọc.
    # Đây là thứ Telegram không có, nên hai bộ định dạng không gộp được.
    dong = [f"• [**{ten}**]({url}) — {mon} — <t:{han}:R>" if url
            else f"• **{ten}** — {mon} — <t:{han}:R>"
            for han, ten, mon, url in ds]
    # Đọc env tại chỗ chứ không ở đầu file, để tu_kiem() bật tắt được.
    ngay = os.environ.get("NGAY_TRUOC", "3")
    tag = os.environ.get("DISCORD_TAG", "").strip()
    return ((tag + " ") if tag else "") + \
        f"⏰ {len(ds)} deadline trong {ngay} ngày tới:\n" + "\n".join(dong)


def gui(ds, now):
    """Gửi nếu có webhook. True = đã gửi, False = chưa cấu hình nên bỏ qua.

    `now` không dùng ở đây — Discord tự tính "còn bao lâu" từ timestamp. Giữ
    tham số cho cùng chữ ký với bao_telegram để deadline.py lặp qua được.
    """
    hook = os.environ.get("DISCORD_WEBHOOK", "").strip()
    if not hook:
        return False
    urllib.request.urlopen(urllib.request.Request(
        hook, json.dumps({"content": tin(ds)}).encode(),
        {"Content-Type": "application/json", "User-Agent": UA}), timeout=30)
    return True


def tu_kiem():
    d = [(100, "A", "M1", "u1"), (200, "B", "M2", "")]
    assert "[**A**](u1)" in tin(d)
    assert "**B**" in tin(d) and "](" not in tin(d).split("\n")[2]   # không url -> in đậm
    assert "<t:100:R>" in tin(d)
    # Tag đứng đầu tin thì Discord mới đẩy thông báo; nằm giữa cũng ping nhưng
    # dòng đầu là thứ hiện trên màn hình khóa.
    os.environ["DISCORD_TAG"] = "<@1>"
    assert tin(d).startswith("<@1> ⏰")
    del os.environ["DISCORD_TAG"]
    assert tin(d).startswith("⏰")
    # Không có webhook thì phải nói là chưa gửi, đừng im lặng coi như xong.
    giu = os.environ.pop("DISCORD_WEBHOOK", None)
    try:
        assert gui(d, 0) is False
    finally:
        if giu is not None:
            os.environ["DISCORD_WEBHOOK"] = giu
