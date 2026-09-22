# UT Deadline

Sáng 7h gửi bản tin 7 ngày tới, tối 7h gửi chuông báo 24h tới — lấy từ `courses.ut.edu.vn` (Moodle của UTH) rồi đẩy
vào Discord hoặc Telegram. Chạy bằng GitHub Actions, không cần server, không cần
máy bạn bật.

stdlib Python thuần, không cài gói nào.

```
⏰ 4 deadline trong 7 ngày tới:
• Bài tập tự học - Chương VI Phần 2 — Chủ nghĩa xã hội — 23:00 25/09 (3 ngày nữa)
• TEST CUỐI KỲ kết thúc — Kỹ thuật lập trình — 13:15 22/09 (5h nữa)
```

## Tự dựng bản của bạn

**Mỗi người một bản riêng.** Đừng dùng chung một repo: `MOODLE_TOKEN` mở được
tài khoản Moodle của chủ token, nên gộp chung là đưa chìa khóa tài khoản mình
cho người khác giữ.

### 1. Fork

Bấm **Fork** ở đầu trang. Vào tab **Actions** của bản fork, bấm **I understand
my workflows, go ahead and enable them** — GitHub tắt lịch chạy trên mọi fork
cho tới khi chủ fork bật.

### 2. Lấy token Moodle

Mở `courses.ut.edu.vn`, đăng nhập, F12 → Console, dán:

```js
(async () => {
  const u = prompt("Tên đăng nhập Moodle"), p = prompt("Mật khẩu");
  const r = await fetch("/login/token.php", {method:"POST",
    headers:{"Content-Type":"application/x-www-form-urlencoded"},
    body: new URLSearchParams({username:u, password:p, service:"moodle_mobile_app"})});
  const j = await r.json();
  console.log(j.token ? "TOKEN: " + j.token : j);
})()
```

Dùng `prompt()` để mật khẩu không nằm lại trong lịch sử console và không vào URL.

Copy phần sau `TOKEN: ` — 32 ký tự hex, không lấy chữ `TOKEN:`.

Hủy token về sau: `courses.ut.edu.vn/user/managetoken.php` → icon thùng rác.

### 3. Chọn nơi nhận

**Discord** — Chỉnh sửa kênh → Tích hợp → Webhook → Tạo → Sao chép URL.
Muốn riêng tư thì tự tạo một server chỉ có mình bạn; Discord không có webhook
cho tin nhắn riêng.

**Telegram** — chat với [@BotFather](https://t.me/BotFather) → `/newbot`. Nhắn
`/start` cho bot vừa tạo (bot không mở lời trước được), rồi mở
`https://api.telegram.org/bot<TOKEN>/getUpdates` và tìm `"chat":{"id":...`.

Đặt cả hai cũng được, mỗi lần chạy nhận hai tin giống nhau.

### 4. Nạp secret

Repo fork → **Settings** → **Secrets and variables** → **Actions** →
**New repository secret**:

| Name | Bắt buộc | Giá trị |
|---|---|---|
| `MOODLE_TOKEN` | ✅ | 32 ký tự hex ở bước 2 |
| `DISCORD_WEBHOOK` | — | URL webhook |
| `TELEGRAM_TOKEN` | — | chuỗi BotFather, dạng `123456789:AAH...` |
| `TELEGRAM_CHAT` | — | dãy số `chat_id` |
| `DISCORD_TAG` | — | tag bạn để đẩy thông báo, dạng `<@123456789012345678>` |
| `TELEGRAM_TAG` | — | tag trong tin Telegram |

Lấy ID Discord: Cài đặt → Nâng cao → bật **Chế độ nhà phát triển**, rồi chuột
phải avatar mình → **Sao chép ID người dùng**. Phải bọc trong `<@` và `>`, dán
trần dãy số thì Discord hiện ra text chứ không ping.

Phải có `MOODLE_TOKEN` và **ít nhất một** nơi nhận, không thì workflow báo đỏ
ngay thay vì lặng lẽ xanh.

### 5. Chạy

**Actions** → `deadline` → **Run workflow**. Log in `N deadline -> discord`.

Xong. 07:00 và 19:00 mỗi ngày nó tự chạy.

## Chỉnh

Sửa trong `.github/workflows/deadline.yml`:

| Biến | Mặc định | Nghĩa |
|---|---|---|
| `cron` | `0 0` và `0 12` | giờ chạy theo UTC = 07:00 và 19:00 giờ VN |
| `NGAY_TRUOC` | `7` sáng, `1` tối | nhìn trước bao nhiêu ngày |

Cửa sổ đổi theo nhịp: nhịp tối nhìn 1 ngày, nhịp sáng và bấm tay nhìn 7 ngày.

```yaml
NGAY_TRUOC: ${{ github.event.schedule == '0 12 * * *' && '1' || '7' }}
```

Chuỗi cron trong dòng đó phải khớp **từng ký tự** với dòng `cron` bên trên. Lệch
một dấu cách là so sánh trượt và mọi nhịp đều rơi về 7 — không báo lỗi gì cả, chỉ
im lặng sai. Log mỗi lần chạy có in cửa sổ thực tế để đối chiếu:
`2 deadline (cua so 1 ngay) -> discord`.

Hai tag nằm ở Secrets chứ không ở file này, xem bảng bước 4.

## Cấu trúc

```
deadline.py       gọi Moodle, lọc theo cửa sổ ngày, điều phối — phần dùng chung
bao_discord.py    định dạng và gửi Discord
bao_telegram.py   định dạng và gửi Telegram
```

Hai file gửi cùng chữ ký `gui(ds, now) -> bool`. Thêm nơi nhận mới = viết một
file nữa rồi bỏ vào `DICH` trong `deadline.py`.

Sender **không** import ngược `deadline.py` — vòng tròn là hỏng lúc khởi động.

Chạy test: `python deadline.py --tu-kiem`. Không cần token, không gọi mạng.
Workflow chạy nó trước mỗi lần gửi.

## Vài chỗ đã đo, đừng sửa mù

**Dùng `core_calendar_get_calendar_upcoming_view`, không dùng
`core_calendar_get_action_events_by_timesort`.** Hàm sau chỉ trả sự kiện còn
"việc để làm" nên cắt mất bài đã nộp, quiz sắp mở và điểm danh — ngay ở tầng
API, lọc phía client không cứu được. Đo 22/09/2026 trên tài khoản thật: hàm đó
ra 3 sự kiện, trang upcoming ra 7.

**Phải gửi `User-Agent`.** Cloudflare đứng trước cả Moodle lẫn Discord, chặn
UA rỗng / `python-urllib` / `curl` bằng trang "Just a moment..." kèm HTTP 403.
UA tự khai tên thì qua bình thường — nên không giả làm trình duyệt, để quản trị
viên soi log biết ngay đây là ai chạy cái gì.

**Không lọc theo `action.actionable`.** Moodle đặt nó `false` cho cả "đã nộp"
lẫn "chưa mở nộp" lẫn "không đủ quyền". Đoán sai là bot nuốt mất deadline thật
mà không ai biết — kiểu hỏng tệ nhất cho thứ cài để khỏi phải nhớ.

## Giới hạn đã biết

- Moodle cắt ở `calendar_maxevents` của site (mặc định 10 sự kiện). Nó trả theo
  thứ tự thời gian tăng dần nên hạn gấp nhất luôn còn; mất là mất mấy cái xa
  nhất. Quá 10 sự kiện trong `NGAY_TRUOC` ngày thì đổi sang
  `core_calendar_get_calendar_monthly_view`.
- Cron GitHub hay trễ 5–30 phút, lúc đông có khi bỏ một nhịp.
- GitHub tắt lịch sau 60 ngày repo không có commit. Vào Actions bấm Run
  workflow một phát là sống lại.
- Bot **không nhớ đã gửi gì**, mỗi lần chạy liệt kê lại toàn bộ cửa sổ. Nên một
  deadline xuất hiện trong 7 bản tin sáng cộng 2 bản tin tối. Cố ý: nhắc một lần
  rồi thôi thì đúng lúc bận là trôi mất.

## Riêng tư

Repo chỉ chứa code, không chứa khóa. Mọi thứ bí mật nằm trong GitHub Secrets,
được mã hóa và bị che trong log Actions.

`MOODLE_TOKEN` mở được tài khoản Moodle của bạn và không tự hết hạn. **Đừng
thêm ai làm collaborator** trên repo này — collaborator chạy được workflow bằng
chính token của bạn và đọc được dữ liệu của bạn. Muốn chia sẻ thì bảo họ fork.
