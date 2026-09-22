#!/usr/bin/env python3
"""Báo deadline Moodle sắp tới vào Discord. stdlib thuần, không dependency."""
import os, sys, json, time, urllib.request, urllib.parse

API = "https://courses.ut.edu.vn/webservice/rest/server.php"
# Cloudflare đứng trước Moodle và chặn thẳng User-Agent "Python-urllib/..." bằng
# trang "Just a moment..." kèm HTTP 403 — token đúng cũng không tới nơi.
# Đo 22/09/2026: cùng request, chỉ đổi UA -> 403 thành 200. Đừng bỏ dòng này.
UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/141.0 Safari/537.36")
NGAY_TRUOC = int(os.environ.get("NGAY_TRUOC", "3"))


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


def tin(ds):
    # <t:...:R> là timestamp Discord: tự hiện "còn 2 ngày" theo múi giờ người đọc.
    dong = [f"• [**{ten}**]({url}) — {mon} — <t:{han}:R>" if url
            else f"• **{ten}** — {mon} — <t:{han}:R>"
            for han, ten, mon, url in ds]
    return f"⏰ {len(ds)} deadline trong {NGAY_TRUOC} ngày tới:\n" + "\n".join(dong)


def gui(hook, noi_dung):
    # Discord cũng núp sau Cloudflare và cũng trả 403 cho UA mặc định của urllib.
    # Cùng lý do với UA ở trên, khác nhà. Xóa một trong hai là hỏng một đầu.
    urllib.request.urlopen(urllib.request.Request(
        hook, json.dumps({"content": noi_dung}).encode(),
        {"Content-Type": "application/json", "User-Agent": UA}), timeout=30)


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
    assert "[**A**](u1)" in tin(loc(d, 0, 300))
    assert loc({"events": [{"timesort": 1, "name": "X"}]}, 0, 9) == [(1, "X", "", "")]
    assert "**X**" in tin(loc({"events": [{"timesort": 1, "name": "X"}]}, 0, 9))
    try:
        loc({"exception": "x", "message": "hỏng"}, 0, 9)
    except SystemExit:
        pass
    else:
        raise AssertionError("lỗi Moodle phải dừng hẳn, không báo 0 deadline")
    print("tu kiem: ok")


if __name__ == "__main__":
    if "--tu-kiem" in sys.argv:
        tu_kiem(); sys.exit()
    now = int(time.time())
    ds = loc(goi(os.environ["MOODLE_TOKEN"]), now, now + NGAY_TRUOC * 86400)
    if ds:
        gui(os.environ["DISCORD_WEBHOOK"], tin(ds))
    print(f"{len(ds)} deadline")
