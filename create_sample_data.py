#!/usr/bin/env python
"""Script tạo dữ liệu mẫu cho hệ thống điểm danh."""

import os
import sys
import django
from datetime import datetime, date, time

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'FaceByAttendance.settings')
django.setup()

from main.models import (
    StaffInfo, Role, StaffRole, StudentInfo, 
    Classroom, StudentClassDetails, BlogPost
)

def create_sample_data():
    """Tạo dữ liệu mẫu."""
    
    print("Tạo dữ liệu mẫu...")
    
    # 1. Tạo vai trò
    print("Tạo vai trò...")
    roles_data = [
        'Admin',
        'Giảng viên',
        'Trợ giảng',
        'Quản lý'
    ]
    
    for role_name in roles_data:
        role, created = Role.objects.get_or_create(name=role_name)
        if created:
            print(f"   ✓ Tạo vai trò: {role_name}")
    
    # 2. Tạo giảng viên
    print("Tạo thông tin giảng viên...")
    staff_data = [
        {
            'id_staff': 'GV001',
            'staff_name': 'Nguyễn Văn An',
            'email': 'nguyenvanan@university.edu.vn',
            'phone': '0901234567',
            'address': '123 Đường ABC, Quận 1, TP.HCM',
            'birthday': date(1980, 5, 15),
            'password': 'password123'
        },
        {
            'id_staff': 'GV002', 
            'staff_name': 'Trần Thị Bình',
            'email': 'tranthibinh@university.edu.vn',
            'phone': '0907654321',
            'address': '456 Đường XYZ, Quận 3, TP.HCM',
            'birthday': date(1985, 8, 20),
            'password': 'password123'
        },
        {
            'id_staff': 'GV003',
            'staff_name': 'Lê Minh Cường',
            'email': 'leminhcuong@university.edu.vn', 
            'phone': '0912345678',
            'address': '789 Đường DEF, Quận 7, TP.HCM',
            'birthday': date(1978, 12, 10),
            'password': 'password123'
        }
    ]
    
    for staff_info in staff_data:
        staff, created = StaffInfo.objects.get_or_create(
            id_staff=staff_info['id_staff'],
            defaults=staff_info
        )
        if created:
            print(f"   ✓ Tạo giảng viên: {staff_info['staff_name']}")
            
            # Gán vai trò
            role = Role.objects.get(name='Giảng viên')
            StaffRole.objects.get_or_create(staff=staff, role=role)
    
    # 3. Tạo thông tin sinh viên (dựa trên dữ liệu có sẵn)
    print("Tạo thông tin sinh viên...")
    existing_students = ['1001', '1011', '1012', '10122025', '1111', '3011', '3012', '76']
    student_names = [
        'Nguyễn Văn A', 'Trần Thị B', 'Lê Minh C', 'Phạm Thị D',
        'Hoàng Văn E', 'Vũ Thị F', 'Đặng Minh G', 'Bùi Thị H'
    ]
    
    for i, student_id in enumerate(existing_students):
        student_data = {
            'id_student': student_id,
            'student_name': student_names[i],
            'email': f'student{student_id}@university.edu.vn',
            'phone': f'090{1000000 + i:07d}',
            'address': f'{100 + i} Đường Sinh Viên, Quận {(i % 12) + 1}, TP.HCM',
            'birthday': date(2000 + (i % 5), (i % 12) + 1, (i % 28) + 1),
            'PathImageFolder': f'main/Dataset/FaceData/processed/{student_id}',
            'password': 'student123'
        }
        
        student, created = StudentInfo.objects.get_or_create(
            id_student=student_id,
            defaults=student_data
        )
        if created:
            print(f"   ✓ Tạo sinh viên: {student_data['student_name']} ({student_id})")
    
    # 4. Tạo lớp học
    print("Tạo lớp học...")
    classroom_data = [
        {
            'name': 'Trí tuệ nhân tạo - AI2024',
            'begin_date': date(2024, 9, 1),
            'end_date': date(2024, 12, 31),
            'day_of_week_begin': 2,  # Thứ 3
            'begin_time': time(8, 0),
            'end_time': time(11, 0),
            'id_lecturer': StaffInfo.objects.get(id_staff='GV001')
        },
        {
            'name': 'Học máy - ML2024',
            'begin_date': date(2024, 9, 1), 
            'end_date': date(2024, 12, 31),
            'day_of_week_begin': 4,  # Thứ 5
            'begin_time': time(13, 30),
            'end_time': time(16, 30),
            'id_lecturer': StaffInfo.objects.get(id_staff='GV002')
        },
        {
            'name': 'Xử lý ảnh số - DIP2024',
            'begin_date': date(2024, 9, 1),
            'end_date': date(2024, 12, 31), 
            'day_of_week_begin': 6,  # Thứ 7
            'begin_time': time(9, 0),
            'end_time': time(12, 0),
            'id_lecturer': StaffInfo.objects.get(id_staff='GV003')
        }
    ]
    
    for classroom_info in classroom_data:
        classroom, created = Classroom.objects.get_or_create(
            name=classroom_info['name'],
            defaults=classroom_info
        )
        if created:
            print(f"   ✓ Tạo lớp: {classroom_info['name']}")
            
            # Đăng ký sinh viên vào lớp
            students = StudentInfo.objects.all()[:6]  # Lấy 6 sinh viên đầu
            for student in students:
                StudentClassDetails.objects.get_or_create(
                    id_classroom=classroom,
                    id_student=student
                )
    
    # 5. Tạo bài viết blog
    print("Tạo bài viết blog...")
    blog_posts = [
        {
            'title': 'Chào mừng đến với Hệ thống Điểm danh Khuôn mặt',
            'body': '''
            <h2>Giới thiệu Hệ thống</h2>
            <p>Hệ thống điểm danh bằng khuôn mặt là một giải pháp công nghệ tiên tiến, 
            sử dụng trí tuệ nhân tạo để tự động nhận diện và điểm danh sinh viên.</p>
            
            <h3>Tính năng chính:</h3>
            <ul>
                <li>Nhận diện khuôn mặt chính xác cao (>90%)</li>
                <li>Điểm danh nhanh chóng, tiết kiệm thời gian</li>
                <li>Báo cáo thống kê chi tiết</li>
                <li>Bảo mật thông tin sinh viên</li>
                <li>Giao diện thân thiện, dễ sử dụng</li>
            </ul>
            
            <p>Hệ thống đã được triển khai thành công và đang phục vụ hiệu quả 
            cho việc quản lý điểm danh tại trường đại học.</p>
            ''',
            'type': 'ALL'
        },
        {
            'title': 'Hướng dẫn sử dụng cho Sinh viên',
            'body': '''
            <h2>Cách thức điểm danh</h2>
            <p>Để thực hiện điểm danh bằng khuôn mặt, sinh viên cần:</p>
            
            <ol>
                <li><strong>Đứng trước camera:</strong> Đảm bảo khuôn mặt nằm trong khung hình</li>
                <li><strong>Ánh sáng đầy đủ:</strong> Tránh ánh sáng quá tối hoặc quá sáng</li>
                <li><strong>Nhìn thẳng camera:</strong> Không đeo khẩu trang, kính đen</li>
                <li><strong>Chờ xác nhận:</strong> Hệ thống sẽ hiển thị kết quả điểm danh</li>
            </ol>
            
            <h3>Lưu ý quan trọng:</h3>
            <ul>
                <li>Điểm danh trong khung giờ quy định</li>
                <li>Chỉ điểm danh tại phòng học được chỉ định</li>
                <li>Mang theo thẻ sinh viên để xác minh khi cần</li>
            </ul>
            ''',
            'type': 'SV'
        },
        {
            'title': 'Hướng dẫn cho Giảng viên',
            'body': '''
            <h2>Quản lý Điểm danh</h2>
            <p>Giảng viên có thể sử dụng các tính năng sau:</p>
            
            <h3>Xem báo cáo điểm danh:</h3>
            <ul>
                <li>Danh sách sinh viên có mặt/vắng mặt</li>
                <li>Thống kê theo buổi học, tuần, tháng</li>
                <li>Xuất báo cáo Excel</li>
            </ul>
            
            <h3>Quản lý lớp học:</h3>
            <ul>
                <li>Thêm/xóa sinh viên khỏi lớp</li>
                <li>Cập nhật thông tin lớp học</li>
                <li>Thiết lập thời gian điểm danh</li>
            </ul>
            
            <h3>Cài đặt hệ thống:</h3>
            <ul>
                <li>Cấu hình camera điểm danh</li>
                <li>Thiết lập ngưỡng nhận diện</li>
                <li>Quản lý dữ liệu khuôn mặt</li>
            </ul>
            ''',
            'type': 'GV'
        },
        {
            'title': 'Công nghệ FaceNet và Deep Learning',
            'body': '''
            <h2>Công nghệ đằng sau hệ thống</h2>
            <p>Hệ thống sử dụng công nghệ FaceNet - một mạng neural sâu được phát triển bởi Google.</p>
            
            <h3>FaceNet Architecture:</h3>
            <ul>
                <li><strong>Input:</strong> Ảnh khuôn mặt 160x160 pixels</li>
                <li><strong>Output:</strong> Vector embedding 512 chiều</li>
                <li><strong>Accuracy:</strong> 99.63% trên dataset LFW</li>
            </ul>
            
            <h3>Quy trình xử lý:</h3>
            <ol>
                <li>Phát hiện khuôn mặt (MTCNN)</li>
                <li>Chuẩn hóa và căn chỉnh</li>
                <li>Trích xuất đặc trưng (FaceNet)</li>
                <li>Phân loại (SVM Classifier)</li>
                <li>Chống giả mạo (Anti-spoofing)</li>
            </ol>
            
            <p>Hệ thống đạt độ chính xác cao và khả năng chống gian lận tốt.</p>
            ''',
            'type': 'ALL'
        },
        {
            'title': 'Thống kê và Báo cáo',
            'body': '''
            <h2>Dashboard Thống kê</h2>
            <p>Hệ thống cung cấp các báo cáo chi tiết về tình hình điểm danh:</p>
            
            <h3>Báo cáo theo thời gian:</h3>
            <ul>
                <li>Tỷ lệ có mặt theo ngày/tuần/tháng</li>
                <li>Xu hướng điểm danh của từng sinh viên</li>
                <li>So sánh giữa các lớp học</li>
            </ul>
            
            <h3>Báo cáo theo sinh viên:</h3>
            <ul>
                <li>Lịch sử điểm danh cá nhân</li>
                <li>Tỷ lệ vắng mặt/có mặt</li>
                <li>Cảnh báo sinh viên hay vắng</li>
            </ul>
            
            <h3>Báo cáo theo lớp:</h3>
            <ul>
                <li>Tổng quan tình hình lớp học</li>
                <li>Danh sách sinh viên cần quan tâm</li>
                <li>Hiệu quả giảng dạy</li>
            </ul>
            ''',
            'type': 'GV'
        }
    ]
    
    for post_data in blog_posts:
        post, created = BlogPost.objects.get_or_create(
            title=post_data['title'],
            defaults=post_data
        )
        if created:
            print(f"   ✓ Tạo bài viết: {post_data['title']}")
    
    print("\nHoàn tất tạo dữ liệu mẫu!")
    print("\nTruy cập:")
    print("   • Trang chính: http://127.0.0.1:8000/")
    print("   • Admin panel: http://127.0.0.1:8000/admin/")
    print("   • Username: admin")
    print("   • Password: (đã đặt ở bước trước)")

if __name__ == '__main__':
    create_sample_data()