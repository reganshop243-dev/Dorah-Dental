"""
Download static files for offline use
"""
import os
import requests
from pathlib import Path

def download_file(url, dest_path):
    """Download a file with progress"""
    try:
        response = requests.get(url, stream=True)
        if response.status_code == 200:
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            with open(dest_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            print(f"  Downloaded: {dest_path}")
            return True
        else:
            print(f"  Failed to download: {url}")
            return False
    except Exception as e:
        print(f"  Error downloading {url}: {e}")
        return False

def main():
    """Download all static files"""
    static_dir = Path('static')
    
    # Create directories
    (static_dir / 'css').mkdir(parents=True, exist_ok=True)
    (static_dir / 'js').mkdir(parents=True, exist_ok=True)
    (static_dir / 'webfonts').mkdir(parents=True, exist_ok=True)
    
    print("Downloading static files for offline use...")
    print("=" * 50)
    
    # Bootstrap 5.3.0
    print("Downloading Bootstrap CSS...")
    download_file(
        'https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css',
        static_dir / 'css/bootstrap.min.css'
    )
    
    print("Downloading Bootstrap JS...")
    download_file(
        'https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js',
        static_dir / 'js/bootstrap.bundle.min.js'
    )
    
    # Font Awesome 6.4.0
    print("Downloading Font Awesome CSS...")
    download_file(
        'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css',
        static_dir / 'css/font-awesome.min.css'
    )
    
    print("Downloading Font Awesome webfonts...")
    font_awesome_files = [
        'fa-solid-900.woff2',
        'fa-regular-400.woff2',
        'fa-brands-400.woff2',
        'fa-v4compatibility.woff2',
    ]
    
    for file in font_awesome_files:
        download_file(
            f'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/webfonts/{file}',
            static_dir / f'webfonts/{file}'
        )
    
    # jQuery 3.6.0
    print("Downloading jQuery...")
    download_file(
        'https://code.jquery.com/jquery-3.6.0.min.js',
        static_dir / 'js/jquery.min.js'
    )
    
    # Google Fonts (Poppins & Playfair Display)
    print("Downloading Google Fonts CSS...")
    download_file(
        'https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;700&family=Poppins:wght@300;400;500;600;700&display=swap',
        static_dir / 'css/google-fonts.css'
    )
    
    print("=" * 50)
    print("Static files downloaded successfully!")
    print(f"Files saved to: {static_dir.absolute()}")

if __name__ == '__main__':
    main()