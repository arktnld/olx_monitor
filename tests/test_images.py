"""
Tests for images service - local image storage and management
"""

from unittest.mock import patch, MagicMock
from pathlib import Path
import tempfile
import shutil

from services.images import (
    download_ad_images, get_local_images,
    delete_ad_images, has_local_images
)


class TestDownloadAdImages:
    """Tests for image downloading"""

    @patch('services.images.requests.get')
    @patch('services.images.IMAGES_DIR', new_callable=lambda: Path(tempfile.mkdtemp()))
    def test_downloads_images_successfully(self, mock_dir, mock_get):
        """Should download and save images to local storage"""
        # Setup mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b'fake image data'
        mock_get.return_value = mock_response

        try:
            mock_dir.mkdir(parents=True, exist_ok=True)

            urls = ['https://img.olx.com.br/image1.jpg', 'https://img.olx.com.br/image2.jpg']
            paths = download_ad_images(1, urls)

            assert len(paths) == 2
            assert mock_get.call_count == 2
        finally:
            shutil.rmtree(mock_dir, ignore_errors=True)

    @patch('services.images.requests.get')
    @patch('services.images.IMAGES_DIR', new_callable=lambda: Path(tempfile.mkdtemp()))
    def test_skips_existing_images(self, mock_dir, mock_get):
        """Should skip downloading if image already exists"""
        try:
            mock_dir.mkdir(parents=True, exist_ok=True)

            # Create existing image
            existing = mock_dir / '1_0.jpg'
            existing.write_bytes(b'existing')

            with patch('services.images.get_local_image_path', return_value=existing):
                urls = ['https://img.olx.com.br/image1.jpg']
                paths = download_ad_images(1, urls)

                assert len(paths) == 1
                mock_get.assert_not_called()
        finally:
            shutil.rmtree(mock_dir, ignore_errors=True)

    @patch('services.images.requests.get')
    @patch('services.images.IMAGES_DIR', new_callable=lambda: Path(tempfile.mkdtemp()))
    def test_handles_download_error(self, mock_dir, mock_get):
        """Should handle HTTP errors gracefully"""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        try:
            mock_dir.mkdir(parents=True, exist_ok=True)

            urls = ['https://img.olx.com.br/notfound.jpg']
            paths = download_ad_images(1, urls)

            assert len(paths) == 0
        finally:
            shutil.rmtree(mock_dir, ignore_errors=True)

    @patch('services.images.requests.get')
    @patch('services.images.IMAGES_DIR', new_callable=lambda: Path(tempfile.mkdtemp()))
    def test_handles_network_exception(self, mock_dir, mock_get):
        """Should handle network exceptions gracefully"""
        mock_get.side_effect = Exception("Network error")

        try:
            mock_dir.mkdir(parents=True, exist_ok=True)

            urls = ['https://img.olx.com.br/image.jpg']
            paths = download_ad_images(1, urls)

            assert len(paths) == 0
        finally:
            shutil.rmtree(mock_dir, ignore_errors=True)


class TestGetLocalImages:
    """Tests for retrieving local images"""

    @patch('services.images.IMAGES_DIR', new_callable=lambda: Path(tempfile.mkdtemp()))
    def test_returns_local_image_urls(self, mock_dir):
        """Should return list of local image URLs"""
        try:
            mock_dir.mkdir(parents=True, exist_ok=True)

            # Create fake images
            (mock_dir / '5_0.jpg').write_bytes(b'img0')
            (mock_dir / '5_1.jpg').write_bytes(b'img1')
            (mock_dir / '5_2.jpg').write_bytes(b'img2')

            images = get_local_images(5)

            assert len(images) == 3
            assert '/images/5_0.jpg' in images
            assert '/images/5_1.jpg' in images
            assert '/images/5_2.jpg' in images
        finally:
            shutil.rmtree(mock_dir, ignore_errors=True)

    @patch('services.images.IMAGES_DIR', new_callable=lambda: Path(tempfile.mkdtemp()))
    def test_stops_at_missing_index(self, mock_dir):
        """Should stop counting at first missing index"""
        try:
            mock_dir.mkdir(parents=True, exist_ok=True)

            # Create images with gap (0, 1, missing 2, 3)
            (mock_dir / '10_0.jpg').write_bytes(b'img0')
            (mock_dir / '10_1.jpg').write_bytes(b'img1')
            (mock_dir / '10_3.jpg').write_bytes(b'img3')  # Gap at 2

            images = get_local_images(10)

            # Should only find 0 and 1, stop at missing 2
            assert len(images) == 2
        finally:
            shutil.rmtree(mock_dir, ignore_errors=True)


class TestDeleteAdImages:
    """Tests for image deletion"""

    @patch('services.images.IMAGES_DIR', new_callable=lambda: Path(tempfile.mkdtemp()))
    def test_deletes_all_ad_images(self, mock_dir):
        """Should delete all images for an ad"""
        try:
            mock_dir.mkdir(parents=True, exist_ok=True)

            # Create fake images
            img0 = mock_dir / '7_0.jpg'
            img1 = mock_dir / '7_1.jpg'
            img0.write_bytes(b'img0')
            img1.write_bytes(b'img1')

            delete_ad_images(7)

            assert not img0.exists()
            assert not img1.exists()
        finally:
            shutil.rmtree(mock_dir, ignore_errors=True)

    @patch('services.images.IMAGES_DIR', new_callable=lambda: Path(tempfile.mkdtemp()))
    def test_handles_no_images_to_delete(self, mock_dir):
        """Should handle case when ad has no images"""
        try:
            mock_dir.mkdir(parents=True, exist_ok=True)

            # Should not raise exception
            delete_ad_images(999)
        finally:
            shutil.rmtree(mock_dir, ignore_errors=True)


class TestHasLocalImages:
    """Tests for checking image existence"""

    @patch('services.images.IMAGES_DIR', new_callable=lambda: Path(tempfile.mkdtemp()))
    def test_checks_if_first_image_exists(self, mock_dir):
        """Should return True when first image exists, False otherwise"""
        try:
            mock_dir.mkdir(parents=True, exist_ok=True)

            # No images yet
            assert has_local_images(8) is False

            # Create first image
            (mock_dir / '8_0.jpg').write_bytes(b'img')
            assert has_local_images(8) is True
        finally:
            shutil.rmtree(mock_dir, ignore_errors=True)
