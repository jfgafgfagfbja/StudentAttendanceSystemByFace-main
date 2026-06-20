#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script huấn luyện model nhận diện khuôn mặt
FaceNet (pre-trained) + SVM Classifier
"""

import os
import sys
import math
import pickle
import argparse
import numpy as np
import tensorflow as tf
from pathlib import Path
from sklearn.svm import SVC
from datetime import datetime

# Thêm thư mục vào path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import facenet


class FaceRecognitionTrainer:
    """Trainer cho model FaceNet + SVM"""
    
    def __init__(self, 
                 data_dir='main/Dataset/FaceData/processed',
                 model_path='main/Models/20180402-114759.pb',
                 output_path='main/Models/facemodel.pkl',
                 batch_size=128,
                 image_size=160):
        self.data_dir = data_dir
        self.model_path = model_path
        self.output_path = output_path
        self.batch_size = batch_size
        self.image_size = image_size
        self.seed = 666
        
    def validate_inputs(self):
        """Kiểm tra đầu vào"""
        print("🔍 Kiểm tra đầu vào...")
        
        # Kiểm tra model
        if not os.path.exists(self.model_path):
            raise FileNotFoundError(f"❌ Không tìm thấy model: {self.model_path}")
        print(f"   ✓ Model: {self.model_path}")
        
        # Kiểm tra dữ liệu
        if not os.path.isdir(self.data_dir):
            raise FileNotFoundError(f"❌ Không tìm thấy thư mục dữ liệu: {self.data_dir}")
        
        dataset = facenet.get_dataset(self.data_dir)
        if not dataset:
            raise ValueError(f"❌ Không có dữ liệu trong: {self.data_dir}")
        
        print(f"   ✓ Dữ liệu: {self.data_dir}")
        print(f"   ✓ Số lớp: {len(dataset)}")
        
        total_images = sum(len(cls.image_paths) for cls in dataset)
        print(f"   ✓ Tổng ảnh: {total_images}")
        
        # Kiểm tra yêu cầu tối thiểu
        min_images = 5
        for cls in dataset:
            if len(cls.image_paths) < min_images:
                raise ValueError(
                    f"❌ Lớp '{cls.name}' có {len(cls.image_paths)} ảnh "
                    f"(tối thiểu {min_images} ảnh)"
                )
        
        print()
        return dataset
    
    def load_facenet_model(self, sess):
        """Load FaceNet pre-trained model"""
        print("📦 Load FaceNet model...")
        facenet.load_model(self.model_path)
        
        images_placeholder = tf.compat.v1.get_default_graph().get_tensor_by_name("input:0")
        embeddings = tf.compat.v1.get_default_graph().get_tensor_by_name("embeddings:0")
        phase_train_placeholder = tf.compat.v1.get_default_graph().get_tensor_by_name("phase_train:0")
        
        embedding_size = embeddings.get_shape()[1]
        print(f"   ✓ Embedding size: {embedding_size}")
        print()
        
        return images_placeholder, embeddings, phase_train_placeholder, embedding_size
    
    def get_embeddings(self, sess, images_placeholder, embeddings, phase_train_placeholder, 
                       paths, batch_size, image_size):
        """Tính embedding cho toàn bộ ảnh"""
        print("🧠 Tính embedding...")
        
        nrof_images = len(paths)
        nrof_batches = int(math.ceil(1.0 * nrof_images / batch_size))
        embedding_size = embeddings.get_shape()[1]
        emb_array = np.zeros((nrof_images, embedding_size))
        
        for i in range(nrof_batches):
            start_idx = i * batch_size
            end_idx = min((i + 1) * batch_size, nrof_images)
            paths_batch = paths[start_idx:end_idx]
            
            images = facenet.load_data(paths_batch, False, False, image_size)
            feed_dict = {
                images_placeholder: images,
                phase_train_placeholder: False
            }
            emb_array[start_idx:end_idx, :] = sess.run(embeddings, feed_dict=feed_dict)
            
            progress = (i + 1) / nrof_batches * 100
            print(f"   [{progress:5.1f}%] {end_idx}/{nrof_images} ảnh", end='\r')
        
        print(f"   ✓ Tính embedding cho {nrof_images} ảnh xong!")
        print()
        return emb_array
    
    def train_svm(self, embeddings, labels, dataset):
        """Huấn luyện SVM classifier"""
        print("🤖 Huấn luyện SVM classifier...")
        
        clf = SVC(kernel='linear', probability=True, verbose=1)
        clf.fit(embeddings, labels)
        
        print(f"   ✓ SVM training hoàn tất!")
        print()
        
        return clf
    
    def save_model(self, clf, dataset):
        """Lưu model"""
        print("💾 Lưu model...")
        
        class_names = [cls.name.replace('_', ' ') for cls in dataset]
        
        os.makedirs(os.path.dirname(self.output_path), exist_ok=True)
        with open(self.output_path, 'wb') as f:
            pickle.dump((clf, class_names), f)
        
        print(f"   ✓ Model đã lưu: {self.output_path}")
        print(f"   ✓ Số lớp: {len(class_names)}")
        print()
    
    def print_summary(self, dataset, embeddings):
        """In tóm tắt kết quả"""
        print("=" * 60)
        print("✅ HỌC TẬP MODEL THÀNH CÔNG!")
        print("=" * 60)
        print()
        print("📊 Tóm tắt:")
        print(f"  • Số lớp (sinh viên): {len(dataset)}")
        
        total_images = sum(len(cls.image_paths) for cls in dataset)
        print(f"  • Tổng ảnh: {total_images}")
        print(f"  • Embedding size: {embeddings.get_shape()[1]}")
        print(f"  • Model lưu tại: {self.output_path}")
        print()
        print("🎉 Sẵn sàng sử dụng!")
        print()
    
    def train(self):
        """Thực hiện training"""
        print("=" * 60)
        print("🚀 HUẤN LUYỆN MODEL NHẬN DIỆN KHUÔN MẶT")
        print("=" * 60)
        print()
        
        try:
            # Kiểm tra đầu vào
            dataset = self.validate_inputs()
            
            # Load model
            with tf.Graph().as_default():
                with tf.compat.v1.Session() as sess:
                    np.random.seed(self.seed)
                    
                    # Load FaceNet
                    images_ph, embeddings, phase_train_ph, emb_size = self.load_facenet_model(sess)
                    
                    # Lấy paths và labels
                    paths, labels = facenet.get_image_paths_and_labels(dataset)
                    
                    # Tính embedding
                    emb_array = self.get_embeddings(
                        sess, images_ph, embeddings, phase_train_ph,
                        paths, self.batch_size, self.image_size
                    )
                    
                    # Train SVM
                    clf = self.train_svm(emb_array, labels, dataset)
                    
                    # Save model
                    self.save_model(clf, dataset)
                    
                    # In tóm tắt
                    self.print_summary(dataset, embeddings)
            
            return True
            
        except Exception as e:
            print()
            print("=" * 60)
            print(f"❌ LỖI: {e}")
            print("=" * 60)
            import traceback
            traceback.print_exc()
            return False


def main():
    parser = argparse.ArgumentParser(
        description='Huấn luyện model FaceNet + SVM',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ví dụ sử dụng:
  python train_model.py
  python train_model.py --data-dir ./data/faces
  python train_model.py --batch-size 64
        """
    )
    
    parser.add_argument(
        '--data-dir',
        default='main/Dataset/FaceData/processed',
        help='Thư mục chứa dữ liệu (mặc định: main/Dataset/FaceData/processed)'
    )
    parser.add_argument(
        '--model-path',
        default='main/Models/20180402-114759.pb',
        help='Đường dẫn model FaceNet'
    )
    parser.add_argument(
        '--output',
        default='main/Models/facemodel.pkl',
        help='Đường dẫn lưu model SVM'
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=128,
        help='Batch size (mặc định: 128)'
    )
    parser.add_argument(
        '--image-size',
        type=int,
        default=160,
        help='Kích thước ảnh (mặc định: 160)'
    )
    
    args = parser.parse_args()
    
    trainer = FaceRecognitionTrainer(
        data_dir=args.data_dir,
        model_path=args.model_path,
        output_path=args.output,
        batch_size=args.batch_size,
        image_size=args.image_size
    )
    
    success = trainer.train()
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
