#!/usr/bin/env python3
"""Lấy deadline Moodle rồi đẩy sang mọi đích đã cấu hình. stdlib thuần.

Phần Moodle nằm ở đây vì cả hai đích dùng chung. Định dạng và cách gửi thì
mỗi nhà một kiểu nên tách riêng: bao_discord.py, bao_telegram.py.
"""
import os, sys, json, time, urllib.request, urllib.parse
import bao_discord, bao_telegram

DICH = (bao_discord, bao_telegram)

API = "https://courses.ut.edu.vn/webservice/rest/server.php"
# Cloudflare đứng trước Moodle chặn danh sách UA bot có sẵn (rỗng, python-urllib,
# curl) bằng trang "Just a moment..." kèm 403. Một UA tự khai tên thì qua bình thường
# — đo 22/09/2026. Nên KHÔNG giả làm Chrome: không cần, và nói thật thì khi quản trị
# viên soi log họ thấy ngay đây là ai, chạy cái gì, chứ không phải một trình duyệt lạ.
UA = "UT-Deadline/1.0 (doc lich ca nhan qua Moodle web service)"
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
    assert loc({"events": [{"timesort": 1, "name": "X"}]}, 0, 9) == [(1, "X", "", "")]
    try:
        loc({"exception": "x", "message": "hỏng"}, 0, 9)
    except SystemExit:
        pass
    else:
        raise AssertionError("lỗi Moodle phải dừng hẳn, không báo 0 deadline")


if __name__ == "__main__":
    if "--tu-kiem" in sys.argv:
        tu_kiem()
        for m in DICH:
            m.tu_kiem()
        print("tu kiem: ok"); sys.exit()

    # Kiểm cấu hình TRƯỚC khi gọi Moodle: hôm nào không có deadline mà đích lại
    # sai thì lặng lẽ xanh, tới hôm có việc mới lòi ra là chưa ai nhận được gì.
    if not any(os.environ.get(k, "").strip()
               for k in ("DISCORD_WEBHOOK", "TELEGRAM_TOKEN")):
        raise SystemExit("Chưa cấu hình đích nào: cần DISCORD_WEBHOOK, "
                         "hoặc TELEGRAM_TOKEN kèm TELEGRAM_CHAT.")

    now = int(time.time())
    ds = loc(goi(os.environ["MOODLE_TOKEN"]), now, now + NGAY_TRUOC * 86400)
    da_gui = [m.TEN for m in DICH if ds and m.gui(ds, now)]
    print(f"{len(ds)} deadline -> {', '.join(da_gui) or 'khong gui'}")
