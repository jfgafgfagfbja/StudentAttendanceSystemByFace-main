#!/usr/bin/env python
"""
Script to set default passwords for all users for testing
"""
import os
import django
import sys

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'FaceByAttendance.settings')
django.setup()

from main.models import StudentInfo, StaffInfo
from django.contrib.auth.hashers import make_password

def setup_student_passwords():
    """Set default passwords for students"""
    print("=== Setting up Student Passwords ===")
    
    students = StudentInfo.objects.all()
    updated_count = 0
    
    for student in students:
        # Set password as student ID
        default_password = str(student.id_student)
        student.password = make_password(default_password)
        student.save()
        updated_count += 1
        print(f"✅ Student {student.id_student} ({student.student_name}): password = {default_password}")
    
    print(f"✅ Updated {updated_count} student passwords")
    return updated_count

def setup_lecturer_passwords():
    """Set default passwords for lecturers"""
    print("\n=== Setting up Lecturer Passwords ===")
    
    lecturers = StaffInfo.objects.filter(roles__name='Lecturer')
    updated_count = 0
    
    for lecturer in lecturers:
        # Set password as lecturer ID
        default_password = str(lecturer.id_staff)
        lecturer.password = make_password(default_password)
        lecturer.save()
        updated_count += 1
        print(f"✅ Lecturer {lecturer.id_staff} ({lecturer.staff_name}): password = {default_password}")
    
    print(f"✅ Updated {updated_count} lecturer passwords")
    return updated_count

def main():
    """Main setup function"""
    print("🔐 Setting up Default Passwords for Testing")
    print("=" * 60)
    
    student_count = setup_student_passwords()
    lecturer_count = setup_lecturer_passwords()
    
    print("\n" + "=" * 60)
    print("📊 Setup Complete:")
    print(f"   Students: {student_count} passwords updated")
    print(f"   Lecturers: {lecturer_count} passwords updated")
    print("\n💡 Password Pattern:")
    print("   - Student password = Student ID (e.g., 0076)")
    print("   - Lecturer password = Lecturer ID (e.g., GV_001)")
    print("\n🎯 Now you can test the 'View Current Password' feature!")

if __name__ == "__main__":
    main()