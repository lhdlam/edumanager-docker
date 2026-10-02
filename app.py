import os
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, Response
from database import get_db, init_db

app = Flask(__name__)
app.secret_key = "edumanager_secret_key_@2026_secured"

ADMIN_USERNAME = "truonghuuphong"
ADMIN_PASSWORD = "Tina2012@"

THU_TRONG_TUAN = {2: 'Thứ 2', 3: 'Thứ 3', 4: 'Thứ 4', 5: 'Thứ 5', 6: 'Thứ 6', 7: 'Thứ 7', 8: 'Chủ nhật'}

# Custom Jinja filters
@app.template_filter('currency')
def currency_filter(value):
    if value is None or value == '':
        return "0"
    try:
        val = float(value)
        return f"{int(val):,}".replace(",", ".")
    except (ValueError, TypeError):
        return "0"

# ==============================================================================
# ROUTE: TRANG CHỦ (CHỈ XEM)
# ==============================================================================
@app.route('/')
def index():
    page = request.args.get('page', 'tkb')
    conn = get_db()
    cursor = conn.cursor()

    all_classes = [dict(row) for row in cursor.execute("SELECT * FROM lop_hoc ORDER BY id DESC").fetchall()]
    
    # Ca học
    cai_dat_ca_hoc = [dict(row) for row in cursor.execute("SELECT * FROM cai_dat_ca_hoc ORDER BY ca_id ASC").fetchall()]

    # TKB Data
    tkb_data = {}
    for row in cursor.execute("SELECT thu, ca_id, noi_dung FROM thoi_khoa_bieu").fetchall():
        tkb_data[(row['thu'], row['ca_id'])] = row['noi_dung'] or ''

    # Students (order by ma_hv ASC)
    students = [dict(row) for row in cursor.execute("SELECT * FROM hoc_vien ORDER BY ma_hv ASC").fetchall()]

    # Map students per class for modals
    class_students_map = {}
    for c in all_classes:
        ml = c['ma_lop']
        cur_hs = cursor.execute("""
            SELECT hv.* FROM hoc_vien hv 
            JOIN hoc_vien_lop hvl ON hv.ma_hv = hvl.ma_hv 
            WHERE hvl.ma_lop = ? 
            ORDER BY hv.ma_hv ASC
        """, (ml,)).fetchall()
        class_students_map[ml] = [dict(h) for h in cur_hs]

    # Điểm danh tab data
    sel_lop = request.args.get('filter_lop', (all_classes[0]['ma_lop'] if all_classes else ''))
    f_thang_input = request.args.get('filter_thang', datetime.now().strftime('%Y-%m'))
    try:
        dt_thang = datetime.strptime(f_thang_input, '%Y-%m')
        sel_thang = dt_thang.strftime('%m/%Y')
    except ValueError:
        sel_thang = datetime.now().strftime('%m/%Y')

    dd_students = []
    saved_dates = {f'ngay_{i}': '--/--' for i in range(1, 9)}
    attendance_map = {}

    if sel_lop:
        cur_dd_st = cursor.execute("""
            SELECT hv.* FROM hoc_vien hv 
            JOIN hoc_vien_lop hvl ON hv.ma_hv = hvl.ma_hv 
            WHERE hvl.ma_lop = ? AND hv.trang_thai = 'Đang học' 
            ORDER BY hv.ma_hv ASC
        """, (sel_lop,)).fetchall()
        dd_students = [dict(r) for r in cur_dd_st]

        row_ngay = cursor.execute("SELECT * FROM ngay_hoc WHERE ma_lop = ? AND thang = ?", (sel_lop, sel_thang)).fetchone()
        if row_ngay:
            saved_dates = dict(row_ngay)

        for shv in dd_students:
            r_dd = cursor.execute("SELECT trang_thai FROM diem_danh WHERE ma_hv = ? AND ma_lop = ? AND ngay_diem_danh = ?", (shv['ma_hv'], sel_lop, sel_thang)).fetchone()
            if r_dd and r_dd['trang_thai']:
                attendance_map[shv['ma_hv']] = r_dd['trang_thai'].split(',')
            else:
                attendance_map[shv['ma_hv']] = ['', '', '', '', '', '', '', '']

    # Học phí tab data
    fee_lop = request.args.get('fee_lop', (all_classes[0]['ma_lop'] if all_classes else ''))
    fee_thang_input = request.args.get('fee_thang', datetime.now().strftime('%Y-%m'))
    try:
        dt_f = datetime.strptime(fee_thang_input, '%Y-%m')
        fee_thang = dt_f.strftime('%m/%Y')
    except ValueError:
        fee_thang = datetime.now().strftime('%m/%Y')

    records = []
    if fee_lop:
        cur_rec = cursor.execute("""
            SELECT hv.ma_hv, hv.ho_ten, 
                   IFNULL(thp.hoc_phi_phai_dong, lh.hoc_phi) as hoc_phi_phai_dong, 
                   IFNULL(thp.da_dong, 0) as da_dong, 
                   thp.hinh_thuc 
            FROM hoc_vien hv 
            JOIN hoc_vien_lop hvl ON hv.ma_hv = hvl.ma_hv 
            JOIN lop_hoc lh ON hvl.ma_lop = lh.ma_lop
            LEFT JOIN thu_hoc_phi thp ON hv.ma_hv = thp.ma_hv AND thp.ma_lop = ? AND thp.thang_thu = ?
            WHERE hvl.ma_lop = ? AND hv.trang_thai = 'Đang học' 
            ORDER BY hv.ma_hv ASC
        """, (fee_lop, fee_thang, fee_lop)).fetchall()
        records = [dict(r) for r in cur_rec]

    conn.close()

    return render_template(
        'index.html',
        page=page,
        all_classes=all_classes,
        cai_dat_ca_hoc=cai_dat_ca_hoc,
        thu_trong_tuan=THU_TRONG_TUAN,
        tkb_data=tkb_data,
        students=students,
        class_students_map=class_students_map,
        sel_lop=sel_lop,
        f_thang_input=f_thang_input,
        sel_thang=sel_thang,
        saved_dates=saved_dates,
        attendance_map=attendance_map,
        fee_lop=fee_lop,
        fee_thang_input=fee_thang_input,
        records=records
    )

# ==============================================================================
# XUẤT EXCEL
# ==============================================================================
@app.route('/export/classes')
def export_excel_classes():
    conn = get_db()
    cursor = conn.cursor()
    classes = cursor.execute("SELECT * FROM lop_hoc ORDER BY id DESC").fetchall()

    html = "\ufeff<table border='1'>"
    html += "<tr><th>Mã Lớp</th><th>Tên Lớp</th><th>Môn Học</th><th>Giáo Viên</th><th>Lịch Học</th><th>Học Phí</th><th>Số Học Viên</th></tr>"
    for c in classes:
        cnt = cursor.execute("SELECT COUNT(*) FROM hoc_vien_lop WHERE ma_lop = ?", (c['ma_lop'],)).fetchone()[0]
        html += f"<tr><td>{c['ma_lop']}</td><td>{c['ten_lop']}</td><td>{c['mon_hoc'] or ''}</td><td>{c['giao_vien'] or ''}</td><td>{c['lich_hoc'] or ''}</td><td>{c['hoc_phi'] or 0}</td><td>{cnt}</td></tr>"
    html += "</table>"
    conn.close()

    filename = f"Danh_Sach_Lop_Hoc_{datetime.now().strftime('%Y%m%d')}.xls"
    return Response(
        html,
        mimetype="application/vnd.ms-excel",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@app.route('/export/students')
def export_excel_students():
    ma_lop = request.args.get('ma_lop', '')
    conn = get_db()
    cursor = conn.cursor()

    row_lop = cursor.execute("SELECT ten_lop FROM lop_hoc WHERE ma_lop = ?", (ma_lop,)).fetchone()
    ten_lop = row_lop['ten_lop'] if row_lop else ma_lop

    hss = cursor.execute("""
        SELECT hv.* FROM hoc_vien hv 
        JOIN hoc_vien_lop hvl ON hv.ma_hv = hvl.ma_hv 
        WHERE hvl.ma_lop = ? 
        ORDER BY hv.ma_hv ASC
    """, (ma_lop,)).fetchall()

    html = "\ufeff<table border='1'>"
    html += f"<tr><th colspan='8' style='font-size:16px; font-weight:bold; text-align:center;'>DANH SÁCH HỌC VIÊN LỚP: {ten_lop} (MÃ: {ma_lop})</th></tr>"
    html += "<tr><th>STT</th><th>Mã HV</th><th>Họ và Tên</th><th>Ngày Sinh</th><th>SĐT</th><th>Lớp Chính Khóa</th><th>Ngày Bắt Đầu</th><th>Trạng thái</th></tr>"
    for idx, hs in enumerate(hss, start=1):
        html += f"<tr><td>{idx}</td><td>{hs['ma_hv']}</td><td>{hs['ho_ten']}</td><td>{hs['ngay_sinh'] or ''}</td><td>{hs['so_dien_thoai'] or ''}</td><td>{hs['lop_truong'] or ''}</td><td>{hs['ngay_bat_dau'] or ''}</td><td>{hs['trang_thai']}</td></tr>"
    html += "</table>"
    conn.close()

    filename = f"Danh_Sach_Hoc_Vien_Lop_{ma_lop}_{datetime.now().strftime('%Y%m%d')}.xls"
    return Response(
        html,
        mimetype="application/vnd.ms-excel",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

# ==============================================================================
# ROUTE: TRANG QUẢN TRỊ (ADMIN)
# ==============================================================================
@app.route('/admin', methods=['GET', 'POST'])
def admin():
    # Xử lý Đăng nhập
    if request.method == 'POST' and request.form.get('action') == 'login_attempt':
        u = request.form.get('username', '').strip()
        p = request.form.get('password', '').strip()
        if u == ADMIN_USERNAME and p == ADMIN_PASSWORD:
            session['logged_in'] = True
            return redirect(url_for('admin'))
        else:
            return render_template('admin.html', logged_in=False, error_msg="Sai tài khoản hoặc mật khẩu!")

    if not session.get('logged_in'):
        return render_template('admin.html', logged_in=False)

    msg = ''
    page = request.args.get('page', 'baocao')
    conn = get_db()
    cursor = conn.cursor()

    # XỬ LÝ POST ACTIONS
    if request.method == 'POST':
        action = request.form.get('action')

        # 1. Lưu TKB
        if action == 'save_tkb':
            for ca_id in range(1, 6):
                tg = request.form.get(f'thoi_gian_{ca_id}', '')
                ms = request.form.get(f'mau_sac_{ca_id}', '')
                cursor.execute("UPDATE cai_dat_ca_hoc SET thoi_gian = ?, mau_sac = ? WHERE ca_id = ?", (tg, ms, ca_id))
                for thu in range(2, 9):
                    nd = request.form.get(f'tkb_{thu}_{ca_id}', '')
                    cursor.execute("INSERT OR REPLACE INTO thoi_khoa_bieu (thu, ca_id, noi_dung) VALUES (?, ?, ?)", (thu, ca_id, nd))
            conn.commit()
            msg = "Đã lưu thông tin Thời khóa biểu động thành công!"

        # 2. Thêm Học viên
        elif action == 'add_hocvien':
            try:
                cursor.execute("""
                    INSERT INTO hoc_vien (ma_hv, ho_ten, ngay_sinh, lop_truong, so_dien_thoai, ngay_bat_dau, trang_thai) 
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    request.form.get('ma_hv', '').strip(),
                    request.form.get('ho_ten', '').strip(),
                    request.form.get('ngay_sinh', ''),
                    request.form.get('lop_truong', '').strip(),
                    request.form.get('so_dien_thoai', '').strip(),
                    request.form.get('ngay_bat_dau', ''),
                    request.form.get('trang_thai', 'Đang học')
                ))
                conn.commit()
                msg = "Thêm học viên thành công!"
            except Exception as e:
                msg = f"Lỗi khi thêm học viên: {e}"

        # 3. Sửa Học viên
        elif action == 'edit_hocvien':
            old_ma_hv = request.form.get('old_ma_hv', '').strip()
            new_ma_hv = request.form.get('ma_hv', '').strip()
            cursor.execute("""
                UPDATE hoc_vien 
                SET ma_hv=?, ho_ten=?, ngay_sinh=?, lop_truong=?, so_dien_thoai=?, ngay_bat_dau=?, trang_thai=? 
                WHERE ma_hv=?
            """, (
                new_ma_hv,
                request.form.get('ho_ten', '').strip(),
                request.form.get('ngay_sinh', ''),
                request.form.get('lop_truong', '').strip(),
                request.form.get('so_dien_thoai', '').strip(),
                request.form.get('ngay_bat_dau', ''),
                request.form.get('trang_thai', 'Đang học'),
                old_ma_hv
            ))
            if old_ma_hv != new_ma_hv:
                cursor.execute("UPDATE thu_hoc_phi SET ma_hv=? WHERE ma_hv=?", (new_ma_hv, old_ma_hv))
                cursor.execute("UPDATE diem_danh SET ma_hv=? WHERE ma_hv=?", (new_ma_hv, old_ma_hv))
                cursor.execute("UPDATE hoc_vien_lop SET ma_hv=? WHERE ma_hv=?", (new_ma_hv, old_ma_hv))
            conn.commit()
            msg = "Cập nhật thông tin học viên thành công!"

        # 4. Thêm Lớp học
        elif action == 'add_lophoc':
            try:
                cursor.execute("""
                    INSERT INTO lop_hoc (ma_lop, ten_lop, mon_hoc, lich_hoc, giao_vien, hoc_phi) 
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    request.form.get('ma_lop', '').strip(),
                    request.form.get('ten_lop', '').strip(),
                    request.form.get('mon_hoc', '').strip(),
                    request.form.get('lich_hoc', '').strip(),
                    request.form.get('giao_vien', '').strip(),
                    float(request.form.get('hoc_phi', 0) or 0)
                ))
                conn.commit()
                msg = "Cập nhật dữ liệu lớp học thành công!"
            except Exception as e:
                msg = f"Lỗi khi thêm lớp học: {e}"

        # 4.5. Sửa Lớp học
        elif action == 'edit_lophoc':
            old_ma_lop = request.form.get('old_ma_lop', '').strip()
            new_ma_lop = request.form.get('ma_lop', '').strip()
            cursor.execute("""
                UPDATE lop_hoc 
                SET ma_lop=?, ten_lop=?, mon_hoc=?, lich_hoc=?, giao_vien=?, hoc_phi=? 
                WHERE ma_lop=?
            """, (
                new_ma_lop,
                request.form.get('ten_lop', '').strip(),
                request.form.get('mon_hoc', '').strip(),
                request.form.get('lich_hoc', '').strip(),
                request.form.get('giao_vien', '').strip(),
                float(request.form.get('hoc_phi', 0) or 0),
                old_ma_lop
            ))
            if old_ma_lop != new_ma_lop:
                cursor.execute("UPDATE thu_hoc_phi SET ma_lop=? WHERE ma_lop=?", (new_ma_lop, old_ma_lop))
                cursor.execute("UPDATE diem_danh SET ma_lop=? WHERE ma_lop=?", (new_ma_lop, old_ma_lop))
                cursor.execute("UPDATE hoc_vien_lop SET ma_lop=? WHERE ma_lop=?", (new_ma_lop, old_ma_lop))
                cursor.execute("UPDATE ngay_hoc SET ma_lop=? WHERE ma_lop=?", (new_ma_lop, old_ma_lop))
            conn.commit()
            msg = "Cập nhật thông tin lớp học thành công!"

        # 5. Gán Học viên vào lớp
        elif action == 'add_to_class':
            ma_hv = request.form.get('ma_hv', '').strip()
            ma_lop = request.form.get('ma_lop', '').strip()
            check = cursor.execute("SELECT COUNT(*) FROM hoc_vien_lop WHERE ma_hv = ? AND ma_lop = ?", (ma_hv, ma_lop)).fetchone()[0]
            if check == 0:
                cursor.execute("INSERT INTO hoc_vien_lop (ma_hv, ma_lop) VALUES (?, ?)", (ma_hv, ma_lop))
                conn.commit()
                msg = "Đã xếp học viên vào danh sách lớp thành công!"
            else:
                msg = "Học viên này đã có sẵn trong danh sách lớp!"

        # 6. Lưu Điểm danh
        elif action == 'save_diemdanh':
            ml = request.form.get('ma_lop', '').strip()
            th = request.form.get('thang', '').strip()

            n_vals = [request.form.get(f'n{i}', '').strip() for i in range(1, 9)]
            chk_ngay = cursor.execute("SELECT id FROM ngay_hoc WHERE ma_lop = ? AND thang = ?", (ml, th)).fetchone()
            if chk_ngay:
                cursor.execute("""
                    UPDATE ngay_hoc 
                    SET ngay_1=?, ngay_2=?, ngay_3=?, ngay_4=?, ngay_5=?, ngay_6=?, ngay_7=?, ngay_8=? 
                    WHERE id=?
                """, (*n_vals, chk_ngay['id']))
            else:
                cursor.execute("""
                    INSERT INTO ngay_hoc (ma_lop, thang, ngay_1, ngay_2, ngay_3, ngay_4, ngay_5, ngay_6, ngay_7, ngay_8) 
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (ml, th, *n_vals))

            # Lưu từng học viên
            st_list = cursor.execute("""
                SELECT hv.ma_hv FROM hoc_vien hv 
                JOIN hoc_vien_lop hvl ON hv.ma_hv = hvl.ma_hv 
                WHERE hvl.ma_lop = ? AND hv.trang_thai = 'Đang học'
            """, (ml,)).fetchall()

            for shv in st_list:
                mhv = shv['ma_hv']
                arr_b = [request.form.get(f'dd_{mhv}_{b}', '').strip() for b in range(8)]
                chuoi = ','.join(arr_b)
                chk_dd = cursor.execute("SELECT id FROM diem_danh WHERE ma_hv = ? AND ma_lop = ? AND ngay_diem_danh = ?", (mhv, ml, th)).fetchone()
                if chk_dd:
                    cursor.execute("UPDATE diem_danh SET trang_thai=? WHERE id=?", (chuoi, chk_dd['id']))
                else:
                    cursor.execute("INSERT INTO diem_danh (ma_hv, ma_lop, ngay_diem_danh, trang_thai) VALUES (?, ?, ?, ?)", (mhv, ml, th, chuoi))
            
            conn.commit()
            msg = "Đã lưu bảng điểm danh thành công!"

        # 7. Lưu Học phí
        elif action == 'save_hocphi':
            mhv = request.form.get('ma_hv', '').strip()
            ml = request.form.get('ma_lop', '').strip()
            th = request.form.get('thang_thu', '').strip()
            phai_dong = float(request.form.get('phai_dong', 0) or 0)
            da_dong = float(request.form.get('da_dong', 0) or 0)
            hinh_thuc = request.form.get('hinh_thuc', '').strip()

            chk_hp = cursor.execute("SELECT id FROM thu_hoc_phi WHERE ma_hv = ? AND ma_lop = ? AND thang_thu = ?", (mhv, ml, th)).fetchone()
            if chk_hp:
                cursor.execute("""
                    UPDATE thu_hoc_phi 
                    SET hoc_phi_phai_dong=?, da_dong=?, hinh_thuc=? 
                    WHERE id=?
                """, (phai_dong, da_dong, hinh_thuc, chk_hp['id']))
            else:
                cursor.execute("""
                    INSERT INTO thu_hoc_phi (ma_hv, ma_lop, thang_thu, hoc_phi_phai_dong, da_dong, hinh_thuc) 
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (mhv, ml, th, phai_dong, da_dong, hinh_thuc))
            conn.commit()
            msg = "Đã cập nhật tình trạng đóng học phí!"

    # DỮ LIỆU CHUNG CHO ADMIN
    all_classes = [dict(r) for r in cursor.execute("SELECT * FROM lop_hoc ORDER BY id DESC").fetchall()]
    all_students = [dict(r) for r in cursor.execute("SELECT * FROM hoc_vien ORDER BY ma_hv ASC").fetchall()]
    cai_dat_ca_hoc = [dict(r) for r in cursor.execute("SELECT * FROM cai_dat_ca_hoc ORDER BY ca_id ASC").fetchall()]

    # TKB Map
    tkb_data = {}
    for row in cursor.execute("SELECT thu, ca_id, noi_dung FROM thoi_khoa_bieu").fetchall():
        tkb_data[(row['thu'], row['ca_id'])] = row['noi_dung'] or ''

    # Class students map
    class_students_map = {}
    for c in all_classes:
        ml = c['ma_lop']
        cur_hs = cursor.execute("""
            SELECT hv.* FROM hoc_vien hv 
            JOIN hoc_vien_lop hvl ON hv.ma_hv = hvl.ma_hv 
            WHERE hvl.ma_lop = ? 
            ORDER BY hv.ma_hv ASC
        """, (ml,)).fetchall()
        class_students_map[ml] = [dict(h) for h in cur_hs]

    # TAB 1: Báo cáo
    thang_bc = request.args.get('thang_bc', datetime.now().strftime('%Y-%m'))
    try:
        dt_bc = datetime.strptime(thang_bc, '%Y-%m')
        thang_thu_format = dt_bc.strftime('%m/%Y')
    except ValueError:
        thang_thu_format = datetime.now().strftime('%m/%Y')

    tong_hoc_vien = cursor.execute("SELECT COUNT(*) FROM hoc_vien WHERE trang_thai = 'Đang học'").fetchone()[0]
    row_dt = cursor.execute("SELECT SUM(da_dong) FROM thu_hoc_phi WHERE thang_thu = ?", (thang_thu_format,)).fetchone()[0]
    tong_doanh_thu = row_dt if row_dt else 0
    tong_chi_phi = tong_doanh_thu * 0.15
    loi_nhuan = tong_doanh_thu * 0.85

    chi_tiet_lop = []
    for lh in all_classes:
        ml = lh['ma_lop']
        si_so = cursor.execute("""
            SELECT COUNT(hvl.ma_hv) FROM hoc_vien_lop hvl 
            JOIN hoc_vien hv ON hvl.ma_hv = hv.ma_hv 
            WHERE hvl.ma_lop = ? AND hv.trang_thai = 'Đang học'
        """, (ml,)).fetchone()[0]
        dt_l = cursor.execute("SELECT SUM(da_dong) FROM thu_hoc_phi WHERE ma_lop = ? AND thang_thu = ?", (ml, thang_thu_format)).fetchone()[0]
        chi_tiet_lop.append({
            'ma_lop': ml,
            'ten_lop': lh['ten_lop'],
            'si_so': si_so,
            'doanh_thu_lop': (dt_l or 0)
        })

    # TAB 5: Điểm danh
    sel_lop = request.args.get('f_lop', (all_classes[0]['ma_lop'] if all_classes else ''))
    f_thang_input = request.args.get('f_thang', datetime.now().strftime('%Y-%m'))
    try:
        dt_th = datetime.strptime(f_thang_input, '%Y-%m')
        sel_thang = dt_th.strftime('%m/%Y')
    except ValueError:
        sel_thang = datetime.now().strftime('%m/%Y')

    d_dates = {f'ngay_{i}': '' for i in range(1, 9)}
    dd_students = []
    attendance_map = {}

    if sel_lop:
        r_ng = cursor.execute("SELECT * FROM ngay_hoc WHERE ma_lop = ? AND thang = ?", (sel_lop, sel_thang)).fetchone()
        if r_ng:
            d_dates = dict(r_ng)

        cur_dd = cursor.execute("""
            SELECT hv.* FROM hoc_vien hv 
            JOIN hoc_vien_lop hvl ON hv.ma_hv = hvl.ma_hv 
            WHERE hvl.ma_lop = ? AND hv.trang_thai = 'Đang học' 
            ORDER BY hv.ma_hv ASC
        """, (sel_lop,)).fetchall()
        dd_students = [dict(r) for r in cur_dd]

        for shv in dd_students:
            r_dd = cursor.execute("SELECT trang_thai FROM diem_danh WHERE ma_hv = ? AND ma_lop = ? AND ngay_diem_danh = ?", (shv['ma_hv'], sel_lop, sel_thang)).fetchone()
            if r_dd and r_dd['trang_thai']:
                attendance_map[shv['ma_hv']] = r_dd['trang_thai'].split(',')
            else:
                attendance_map[shv['ma_hv']] = ['', '', '', '', '', '', '', '']

    # TAB 6: Học phí
    fee_lop = request.args.get('fee_lop', (all_classes[0]['ma_lop'] if all_classes else ''))
    fee_thang_in = request.args.get('fee_thang', datetime.now().strftime('%Y-%m'))
    try:
        dt_fee = datetime.strptime(fee_thang_in, '%Y-%m')
        fee_thang = dt_fee.strftime('%m/%Y')
    except ValueError:
        fee_thang = datetime.now().strftime('%m/%Y')

    list_rec = []
    if fee_lop:
        # Lấy học phí mặc định của lớp
        r_fee = cursor.execute("SELECT hoc_phi FROM lop_hoc WHERE ma_lop = ?", (fee_lop,)).fetchone()
        hp_mac_dinh = r_fee['hoc_phi'] if r_fee else 0

        # Tự động đồng bộ hóa đơn cho học sinh đang học
        enrolled_hvs = cursor.execute("""
            SELECT hv.ma_hv FROM hoc_vien_lop hvl 
            JOIN hoc_vien hv ON hv.ma_hv = hvl.ma_hv 
            WHERE hvl.ma_lop = ? AND hv.trang_thai = 'Đang học'
        """, (fee_lop,)).fetchall()

        for eh in enrolled_hvs:
            mhv = eh['ma_hv']
            chk = cursor.execute("SELECT COUNT(*) FROM thu_hoc_phi WHERE ma_hv = ? AND ma_lop = ? AND thang_thu = ?", (mhv, fee_lop, fee_thang)).fetchone()[0]
            if chk == 0:
                cursor.execute("""
                    INSERT INTO thu_hoc_phi (ma_hv, ma_lop, thang_thu, hoc_phi_phai_dong, da_dong, hinh_thuc) 
                    VALUES (?, ?, ?, ?, 0, '')
                """, (mhv, fee_lop, fee_thang, hp_mac_dinh))
        conn.commit()

        cur_thp = cursor.execute("""
            SELECT thp.*, hv.ho_ten FROM thu_hoc_phi thp 
            JOIN hoc_vien hv ON thp.ma_hv = hv.ma_hv 
            WHERE thp.ma_lop = ? AND thp.thang_thu = ? 
            ORDER BY thp.ma_hv ASC
        """, (fee_lop, fee_thang)).fetchall()
        list_rec = [dict(r) for r in cur_thp]

    conn.close()

    return render_template(
        'admin.html',
        logged_in=True,
        msg=msg,
        page=page,
        thu_tuan=THU_TRONG_TUAN,
        all_classes=all_classes,
        all_students=all_students,
        cai_dat_ca_hoc=cai_dat_ca_hoc,
        tkb_data=tkb_data,
        class_students_map=class_students_map,
        thang_bc=thang_bc,
        thang_thu_format=thang_thu_format,
        tong_hoc_vien=tong_hoc_vien,
        tong_doanh_thu=tong_doanh_thu,
        tong_chi_phi=tong_chi_phi,
        loi_nhuan=loi_nhuan,
        chi_tiet_lop=chi_tiet_lop,
        sel_lop=sel_lop,
        f_thang_input=f_thang_input,
        sel_thang=sel_thang,
        d_dates=d_dates,
        students=dd_students,
        attendance_map=attendance_map,
        fee_lop=fee_lop,
        f_thang_fee=fee_thang_in,
        fee_thang=fee_thang,
        list_rec=list_rec
    )

@app.route('/admin/logout')
def admin_logout():
    session.pop('logged_in', None)
    return redirect(url_for('admin'))

@app.route('/admin/delete/<del_table>/<int:del_id>')
def admin_delete(del_table, del_id):
    if not session.get('logged_in'):
        return redirect(url_for('admin'))
    page = request.args.get('page', 'hocvien' if del_table == 'hv' else 'lophoc')
    conn = get_db()
    cursor = conn.cursor()
    tbl = 'hoc_vien' if del_table == 'hv' else 'lop_hoc'
    cursor.execute(f"DELETE FROM {tbl} WHERE id = ?", (del_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('admin', page=page))

# ==============================================================================
# ENTRY POINT
# ==============================================================================
if __name__ == '__main__':
    init_db()
    print("=" * 65)
    print("🚀 EDUMANAGER ĐANG CHẠY TẠI: http://localhost:3333")
    print(f"🔑 TÀI KHOẢN ADMIN: {ADMIN_USERNAME} / {ADMIN_PASSWORD}")
    print("=" * 65)
    app.run(host='0.0.0.0', port=3333, debug=False)
