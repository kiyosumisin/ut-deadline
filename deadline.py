#!/usr/bin/env python3
"""Báo deadline Moodle sắp tới vào Discord và/hoặc Telegram. stdlib thuần."""
import os, sys, json, time, datetime as dt, urllib.request, urllib.parse

API = "https://courses.ut.edu.vn/webservice/rest/server.php"
# Cloudflare đứng trước Moodle chặn danh sách UA bot có sẵn (rỗng, python-urllib,
# curl) bằng trang "Just a moment..." kèm 403. Một UA tự khai tên thì qua bình thường
# — đo 22/09/2026. Nên KHÔNG giả làm Chrome: không cần, và nói thật thì khi quản trị
# viên soi log họ thấy ngay đây là ai, chạy cái gì, chứ không phải một trình duyệt lạ.
UA = "UT-Deadline/1.0 (doc lich ca nhan qua Moodle web service)"
NGAY_TRUOC = int(os.environ.get("NGAY_TRUOC", "3"))
VN = dt.timezone(dt.timedelta(hours=7))   # khỏi phụ thuộc tzdata của máy chạy


def goi(token):
    # KHÔNG dùng core_calendar_get_action_events_by_timesort: nó chỉ trả sự kiện
    # còn "việc để làm", nên bài đã nộp / quiz sắp mở / điểm danh bị cắt ngay ở
    # tầng API. Đo thật 22/09/2026: hàm đó ra 3, trang upcoming ra 7.
    # ponytail: upcoming_view bị chặn bởi calendar_maxevents của site (mặc định 10)
    # và trả theo thứ tự thời gian tăng dần -> cửa sổ vài ngày đầu luôn an toàn.
    # Quá 10 sự kiện trong NGAY_TRUOC ngày thì đổi sang core_calendar_get_calendar_monthly_view.
    # POST chứ không GET: token nằm trong body, không lọt vào log server hay history.
    q = urllib.parse.urlencode({
        "wstoken": token,
        "moodlewsrestformat": "json",
        "wsfunction": "core_calendar_get_calendar_upcoming_view",
        "courseid": 1, "categoryid": 0,
    })
    req = urllib.request.Request(API, q.encode(), {"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        raw = r.read()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # Cloudflare cũng có lúc trả 200 kèm trang chặn. Nói thẳng ra là bị chặn,
        # đừng để nó nổ thành lỗi parse khó hiểu.
        raise SystemExit("Không nhận được JSON, nhiều khả năng bị Cloudflare chặn: "
                         + raw[:200].decode("utf-8", "replace"))


def loc(d, tu, den):
    """Response -> [(hạn, tên bài, tên môn, url)] trong khoảng tu..den, đã sắp xếp."""
    # Moodle trả lỗi trong body 200 y như portal trường. Không check là im lặng sai.
    if "exception" in d:
        raise SystemExit("Moodle: " + str(d.get("message") or d["exception"]))
    # Hàm này trả cả cửa sổ lookahead của site (mặc định 21 ngày) -> tự cắt tại đây.
    # Không lọc theo loại sự kiện: điểm danh, quiz mở, quiz đóng đều là thứ lỡ thì mất.
    return sorted((e["timesort"], e["name"],
                   (e.get("course") or {}).get("fullname", ""), e.get("url", ""))
                  for e in d.get("events", []) if tu <= e["timesort"] <= den)


def dau_tin(ds, tag_env):
    # Đọc env tại chỗ chứ không ở đầu file, để tu_kiem() bật tắt được.
    tag = os.environ.get(tag_env, "").strip()
    return ((tag + " ") if tag else "") + \
        f"⏰ {len(ds)} deadline trong {NGAY_TRUOC} ngày tới:"


def tin_discord(ds):
    # <t:...:R> là timestamp Discord: tự hiện "còn 2 ngày" theo múi giờ người đọc.
    dong = [f"• [**{ten}**]({url}) — {mon} — <t:{han}:R>" if url
            else f"• **{ten}** — {mon} — <t:{han}:R>"
            for han, ten, mon, url in ds]
    return dau_tin(ds, "DISCORD_TAG") + "\n" + "\n".join(dong)


def _esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def tin_telegram(ds, now):
    # Telegram không có timestamp động như Discord -> tự tính "còn bao lâu" và
    # chốt cứng giờ VN. Đây là thứ mất đi khi đổi nhà, không có gì thay được.
    dong = []
    for han, ten, mon, url in ds:
        gio = dt.datetime.fromtimestamp(han, VN).strftime("%H:%M %d/%m")
        con = max(0, han - now)
        khi = f"{con // 3600}h nữa" if con < 48 * 3600 else f"{con // 86400} ngày nữa"
        nhan = f'<a href="{_esc(url)}">{_esc(ten)}</a>' if url else f"<b>{_esc(ten)}</b>"
        dong.append(f"• {nhan} — {_esc(mon)} — {gio} ({khi})")
    return _esc(dau_tin(ds, "TELEGRAM_TAG")) + "\n" + "\n".join(dong)


def _post(url, payload, headers=None):
    urllib.request.urlopen(urllib.request.Request(
        url, json.dumps(payload).encode(),
        {"Content-Type": "application/json", "User-Agent": UA, **(headers or {})}
    ), timeout=30)


def gui(ds, now):
    """Gửi tới mọi đích đã cấu hình. Trả về danh sách đích đã gửi."""
    hook = os.environ.get("DISCORD_WEBHOOK", "").strip()
    tg_token = os.environ.get("TELEGRAM_TOKEN", "").strip()
    tg_chat = os.environ.get("TELEGRAM_CHAT", "").strip()
    da_gui = []
    if hook:
        # Discord cũng núp sau Cloudflare và cũng trả 403 cho UA mặc định của urllib.
        _post(hook, {"content": tin_discord(ds)})
        da_gui.append("discord")
    if tg_token and tg_chat:
        _post(f"https://api.telegram.org/bot{tg_token}/sendMessage",
              {"chat_id": tg_chat, "text": tin_telegram(ds, now),
               "parse_mode": "HTML", "disable_web_page_preview": True})
        da_gui.append("telegram")
    if not da_gui:
        raise SystemExit("Chưa cấu hình đích nào: cần DISCORD_WEBHOOK, "
                         "hoặc TELEGRAM_TOKEN kèm TELEGRAM_CHAT.")
    return da_gui


def tu_kiem():
    assert loc({"events": []}, 0, 999) == []
    d = {"events": [
        {"timesort": 200, "name": "B", "course": {"fullname": "M2"}, "url": "u2"},
        {"timesort": 100, "name": "A", "course": {"fullname": "M1"}, "url": "u1"},
        {"timesort": 150, "name": "C", "course": {"fullname": "M3"}, "url": "u3",
         "action": {"actionable": False}},
        {"timesort": 900, "name": "XA", "course": {"fullname": "M4"}, "url": "u4"},
    ]}
    # actionable=False vẫn phải lọt qua: đó là bài ĐÃ NỘP hay bài CHƯA MỞ, không đoán.
    assert [x[1] for x in loc(d, 0, 300)] == ["A", "C", "B"], loc(d, 0, 300)
    assert [x[1] for x in loc(d, 0, 999)] == ["A", "C", "B", "XA"]   # ngoài cửa sổ thì cắt
    assert "[**A**](u1)" in tin_discord(loc(d, 0, 300))
    assert loc({"events": [{"timesort": 1, "name": "X"}]}, 0, 9) == [(1, "X", "", "")]
    assert "**X**" in tin_discord(loc({"events": [{"timesort": 1, "name": "X"}]}, 0, 9))
    # Tag đứng đầu tin thì mới đẩy thông báo; nằm giữa cũng ping nhưng dòng đầu
    # là thứ hiện trên màn hình khóa.
    os.environ["DISCORD_TAG"] = "<@1>"
    assert tin_discord(loc(d, 0, 300)).startswith("<@1> ⏰")
    del os.environ["DISCORD_TAG"]
    assert tin_discord(loc(d, 0, 300)).startswith("⏰")

    # Telegram: HTML nên < > & trong tên bài phải escape, không thì tin hỏng cả khối.
    tg = tin_telegram([(0, "A<b>&", "M&M", "u?x=1&y=2")], 0)
    assert "A&lt;b&gt;&amp;" in tg and "M&amp;M" in tg, tg
    assert 'href="u?x=1&amp;y=2"' in tg, tg
    assert "<b>X</b>" in tin_telegram([(0, "X", "M", "")], 0)   # không url -> in đậm
    assert "2 ngày nữa" in tin_telegram([(86400 * 2, "X", "M", "")], 0)
    assert "2h nữa" in tin_telegram([(7200, "X", "M", "")], 0)
    assert "47h nữa" in tin_telegram([(47 * 3600, "X", "M", "")], 0)   # sát mốc 48h
    assert "0h nữa" in tin_telegram([(-500, "X", "M", "")], 0)         # đã qua hạn

    try:
        loc({"exception": "x", "message": "hỏng"}, 0, 9)
    except SystemExit:
        pass
    else:
        raise AssertionError("lỗi Moodle phải dừng hẳn, không báo 0 deadline")

    # Không cấu hình đích nào thì phải kêu, đừng im lặng coi như đã gửi.
    giu = {k: os.environ.pop(k, None) for k in
           ("DISCORD_WEBHOOK", "TELEGRAM_TOKEN", "TELEGRAM_CHAT")}
    try:
        gui([], 0)
    except SystemExit:
        pass
    else:
        raise AssertionError("không có đích nào mà vẫn im lặng")
    finally:
        for k, v in giu.items():
            if v is not None:
                os.environ[k] = v
    print("tu kiem: ok")


if __name__ == "__main__":
    if "--tu-kiem" in sys.argv:
        tu_kiem(); sys.exit()
    now = int(time.time())
    ds = loc(goi(os.environ["MOODLE_TOKEN"]), now, now + NGAY_TRUOC * 86400)
    dich = gui(ds, now) if ds else []
    print(f"{len(ds)} deadline -> {', '.join(dich) or 'khong gui'}")
