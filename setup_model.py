#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script để setup và rebuild model nhận diện khuôn mặt
Hỗ trợ: 
  - Tạo cấu trúc thư mục
  - Chuẩn bị dữ liệu
  - Kiểm tra requirements
  - Huấn luyện model
"""

import os
import sys
import shutil
import argparse
from pathlib import Path

# Thêm thư mục hiện tại vào path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Cấu hình đường dẫn
BASE_DIR = Path(__file__).parent
DATASET_DIR = BASE_DIR / 'main' / 'Dataset' / 'FaceData' / 'processed'
MODELS_DIR = BASE_DIR / 'main' / 'Models'
FACENET_MODEL = MODELS_DIR / '20180402-114759.pb'
SVM_MODEL = MODELS_DIR / 'facemodel.pkl'


def setup_directories():
    """Tạo cấu trúc thư mục cần thiết"""
    print("📁 Tạo cấu trúc thư mục...")
    
    directories = [
        DATASET_DIR,
        MODELS_DIR,
    ]
    
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)
        print(f"   ✓ {directory}")
    
    print("✅ Cấu trúc thư mục đã sẵn sàng!\n")


def check_models():
    """Kiểm tra file models"""
    print("🔍 Kiểm tra file models...")
    
    if FACENET_MODEL.exists():
        size_mb = FACENET_MODEL.stat().st_size / (1024 * 1024)
        print(f"   ✓ FaceNet model: {FACENET_MODEL} ({size_mb:.1f}MB)")
    else:
        print(f"   ✗ Chưa tìm thấy FaceNet model: {FACENET_MODEL}")
        print(f"     → Tải model từ: https://github.com/davidsandberg/facenet")
        return False
    
    return True


def check_dataset():
    """Kiểm tra dữ liệu huấn luyện"""
    print("\n📊 Kiểm tra dữ liệu huấn luyện...")
    
    if not DATASET_DIR.exists():
        print(f"   ✗ Chưa tìm thấy thư mục: {DATASET_DIR}")
        return False
    
    student_dirs = [d for d in DATASET_DIR.iterdir() if d.is_dir()]
    
    if not student_dirs:
        print(f"   ⚠ Chưa có dữ liệu sinh viên")
        print(f"   → Vui lòng thêm ảnh vào: {DATASET_DIR}")
        print(f"   → Cấu trúc: {DATASET_DIR}/<student_id>/*.jpg")
        return False
    
    total_images = 0
    for student_dir in student_dirs:
        images = list(student_dir.glob('*.jpg')) + list(student_dir.glob('*.png'))
        total_images += len(images)
        print(f"   ✓ {student_dir.name}: {len(images)} ảnh")
    
    print(f"   📈 Tổng: {len(student_dirs)} sinh viên, {total_images} ảnh")
    return True


def clean_dataset():
    """Xóa dữ liệu cũ"""
    print("\n🧹 Xóa dữ liệu cũ...")
    
    if DATASET_DIR.exists():
        for item in DATASET_DIR.iterdir():
            if item.is_dir():
                shutil.rmtree(item)
                print(f"   ✓ Xóa: {item}")
    
    print("✅ Dữ liệu cũ đã xóa!\n")


def clean_model():
    """Xóa model SVM cũ"""
    print("🧹 Xóa model SVM cũ...")
    
    if SVM_MODEL.exists():
        SVM_MODEL.unlink()
        print(f"   ✓ Xóa: {SVM_MODEL}")
    
    print("✅ Model SVM cũ đã xóa!\n")


def import_sample_data():
    """Hướng dẫn import dữ liệu mẫu"""
    print("\n📸 Cách thêm dữ liệu sinh viên:\n")
    print("1. Tạo thư mục cho mỗi sinh viên:")
    print(f"   {DATASET_DIR}/<student_id>/")
    print()
    print("2. Thêm ảnh khuôn mặt (tối thiểu 20 ảnh/sinh viên):")
    print(f"   {DATASET_DIR}/SV001/image_1.jpg")
    print(f"   {DATASET_DIR}/SV001/image_2.jpg")
    print(f"   {DATASET_DIR}/SV001/image_3.jpg")
    print(f"   ...")
    print()
    print("3. Yêu cầu ảnh:")
    print("   - Định dạng: JPG hoặc PNG")
    print("   - Kích thước: >= 160x160 pixels")
    print("   - Nội dung: Khuôn mặt rõ ràng, sáng tốt")
    print("   - Số lượng: Tối thiểu 20-30 ảnh/sinh viên")
    print()


def main():
    parser = argparse.ArgumentParser(description='Setup model nhận diện khuôn mặt')
    parser.add_argument('--clean-dataset', action='store_true', help='Xóa toàn bộ dữ liệu cũ')
    parser.add_argument('--clean-model', action='store_true', help='Xóa model SVM cũ')
    parser.add_argument('--check-only', action='store_true', help='Chỉ kiểm tra, không setup')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("🚀 Setup Model Nhận Diện Khuôn Mặt")
    print("=" * 60)
    print()
    
    # Kiểm tra models
    if not check_models():
        print("\n❌ Lỗi: Thiếu FaceNet model!")
        return False
    
    if args.check_only:
        check_dataset()
        print()
        return True
    
    # Setup
    if args.clean_dataset:
        clean_dataset()
    
    if args.clean_model:
        clean_model()
    
    setup_directories()
    
    # Kiểm tra dữ liệu
    has_data = check_dataset()
    
    if not has_data:
        import_sample_data()
    
    print("\n" + "=" * 60)
    print("✅ Setup hoàn tất!")
    print("=" * 60)
    print("\n📝 Tiếp theo:")
    print("1. Thêm ảnh sinh viên vào:", DATASET_DIR)
    print("2. Chạy: python manage.py runserver")
    print("3. Truy cập Admin → Train Model")
    print()
    
    return True


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
