"""Dataset folder module for loading and processing face images with Fourier Transform.

This module provides utilities for loading image datasets and computing Fourier Transform
features for image samples.
"""

import cv2
import numpy as np
import torch
from torchvision import datasets


def opencv_loader(path: str) -> np.ndarray:
    """Load an image from file using OpenCV.

    Args:
        path: Path to the image file.

    Returns:
        Image array loaded by cv2.imread, or None if image cannot be read.
    """
    return cv2.imread(path)


class DatasetFolderFT(datasets.ImageFolder):
    """Image dataset folder with Fourier Transform feature extraction.

    A custom ImageFolder dataset that extracts Fourier Transform features
    alongside original images for anti-spoofing tasks.

    Attributes:
        ft_width: Width for resizing Fourier Transform image.
        ft_height: Height for resizing Fourier Transform image.
    """

    def __init__(
        self,
        root: str,
        transform=None,
        target_transform=None,
        ft_width: int = 10,
        ft_height: int = 10,
        loader=None,
    ):
        """Initialize the dataset folder.

        Args:
            root: Root directory of the image dataset.
            transform: Optional transforms to be applied on images.
            target_transform: Optional transforms to be applied on targets.
            ft_width: Width of the resized Fourier Transform image.
            ft_height: Height of the resized Fourier Transform image.
            loader: Image loader function (defaults to opencv_loader).
        """
        if loader is None:
            loader = opencv_loader
        super().__init__(root, transform, target_transform, loader)
        self.root = root
        self.ft_width = ft_width
        self.ft_height = ft_height

    def __getitem__(self, index: int) -> tuple:
        """Get a sample from the dataset.

        Args:
            index: Index of the sample to retrieve.

        Returns:
            Tuple of (sample, ft_sample, target) where:
                - sample: Transformed image
                - ft_sample: Fourier Transform feature tensor
                - target: Class label

        Raises:
            AssertionError: If sample image is None.
        """
        path, target = self.samples[index]
        sample = self.loader(path)

        # Generate Fourier Transform features
        ft_sample = generate_ft(sample)

        if sample is None:
            raise ValueError(f"Failed to load image: {path}")
        if ft_sample is None:
            raise ValueError(f"Failed to compute FT features for: {path}")

        # Resize and convert to tensor
        ft_sample = cv2.resize(ft_sample, (self.ft_width, self.ft_height))
        ft_sample = torch.from_numpy(ft_sample).float()
        ft_sample = torch.unsqueeze(ft_sample, 0)

        # Apply transforms
        if self.transform is not None:
            try:
                sample = self.transform(sample)
            except Exception as err:
                raise ValueError(f"Transform error for {path}: {err}") from err

        if self.target_transform is not None:
            target = self.target_transform(target)

        return sample, ft_sample, target


def generate_ft(image: np.ndarray) -> np.ndarray:
    """Generate Fourier Transform magnitude features from an image.

    Computes the Fast Fourier Transform (FFT) of the grayscale image and
    normalizes the magnitude spectrum for use as a feature.

    Args:
        image: Input image array (BGR format expected).

    Returns:
        Normalized FFT magnitude spectrum as a 2D array.
    """
    # Convert to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Compute FFT and shift zero-frequency component to center
    f_transform = np.fft.fft2(gray)
    fshift = np.fft.fftshift(f_transform)

    # Compute magnitude spectrum with logarithmic scaling
    magnitude = np.log(np.abs(fshift) + 1)

    # Normalize to [0, 1] range
    min_val = magnitude.min()
    max_val = magnitude.max()
    normalized = (magnitude - min_val) / (max_val - min_val + 1e-6)

    return normalized